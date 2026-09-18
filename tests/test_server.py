import asyncio
import json
import struct
import time
import unittest

from simmp import framing, messages as msg
from simmp.constants import MAX_FRAME_BYTES, PROTOCOL_VERSION
from server.networking.server import MPServer


class FakeClient:
    def __init__(self, reader, writer, name):
        self._reader = reader
        self._writer = writer
        self.name = name
        self.messages = []

    @classmethod
    async def connect(cls, port, name):
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        return cls(reader, writer, name)

    async def send(self, message):
        self._writer.write(framing.encode(message))
        await self._writer.drain()

    async def recv(self, timeout=5.0):
        message = await asyncio.wait_for(framing.read_frame(self._reader), timeout)
        if message is None:
            raise RuntimeError("connection closed")
        self.messages.append(message)
        return message

    async def wait_for_type(self, message_type, timeout=5.0):
        return await asyncio.wait_for(self._recv_type(message_type), timeout)

    async def _recv_type(self, message_type):
        while True:
            message = await self.recv()
            if message["type"] == message_type:
                return message

    async def recv_until(self, predicate, timeout=5.0):
        """Keep reading frames until `predicate(frame)` is true.

        Frames that do not match are retained in `self.messages`, so
        `predicate` can inspect the accumulated history.
        """
        async def _pump():
            while True:
                message = await self.recv()
                if predicate(message):
                    return message

        return await asyncio.wait_for(_pump(), timeout)

    async def close(self):
        try:
            self._writer.close()
        except Exception:
            pass
        try:
            await asyncio.wait_for(self._writer.wait_closed(), timeout=2)
        except Exception:
            pass


async def _with_server(callback):
    server = MPServer("127.0.0.1", 0)
    await server.start()
    try:
        await callback(server, server.port)
    finally:
        await server.stop()


class ServerFlowTests(unittest.TestCase):
    def run_flow(self, coro):
        asyncio.run(coro)

    def test_welcome_room_state_event_broadcast_ping_disconnect(self):
        async def flow(server, port):
            alice = await FakeClient.connect(port, "Alice")
            await alice.send(msg.make_hello("Alice", "t"))

            welcome = await alice.wait_for_type("WELCOME")
            self.assertEqual(welcome["payload"]["player_id"], 1000)
            self.assertEqual(welcome["payload"]["room_id"], "lobby")
            self.assertEqual(welcome["payload"]["protocol_version"], PROTOCOL_VERSION)

            state = await alice.wait_for_type("ROOM_STATE")
            self.assertEqual([p["name"] for p in state["payload"]["players"]], ["Alice"])

            bob = await FakeClient.connect(port, "Bob")
            await bob.send(msg.make_hello("Bob", "t"))

            bob_welcome = await bob.wait_for_type("WELCOME")
            self.assertGreater(bob_welcome["payload"]["player_id"], 1000)
            bob_state = await bob.wait_for_type("ROOM_STATE")
            self.assertEqual({p["name"] for p in bob_state["payload"]["players"]}, {"Alice", "Bob"})

            joined = await alice.wait_for_type("PLAYER_JOINED")
            self.assertEqual(joined["payload"]["name"], "Bob")
            self.assertEqual(joined["payload"]["room_id"], "lobby")

            await alice.send(msg.make_event("test", "hello"))
            event = await bob.wait_for_type("EVENT")
            self.assertEqual(event["payload"]["event_type"], "test")
            self.assertEqual(event["payload"]["data"], "hello")
            ack = await alice.wait_for_type("EVENT_ACK")
            self.assertEqual(ack["payload"]["seq"], 0)
            self.assertEqual(ack["payload"]["room_id"], "lobby")

            await asyncio.sleep(0.2)
            self.assertFalse(any(m["type"] == "EVENT" for m in alice.messages))

            await bob.send(msg.make_ping(1.25))
            pong = await bob.wait_for_type("PONG")
            self.assertEqual(pong["payload"]["client_time"], 1.25)
            self.assertIsInstance(pong["payload"]["server_time"], (int, float))

            await alice.close()
            left = await bob.wait_for_type("PLAYER_LEFT")
            self.assertEqual(left["payload"]["player_id"], 1000)
            self.assertEqual(left["payload"]["reason"], "disconnected")

        self.run_flow(_with_server(flow))

    def test_join_room_moves_members_and_notifies(self):
        async def flow(server, port):
            alice = await FakeClient.connect(port, "Alice")
            await alice.send(msg.make_hello("Alice", "t"))
            await alice.wait_for_type("WELCOME")
            await alice.wait_for_type("ROOM_STATE")

            bob = await FakeClient.connect(port, "Bob")
            await bob.send(msg.make_hello("Bob", "t"))
            bob_welcome = await bob.wait_for_type("WELCOME")
            bob_lobby_state = await bob.wait_for_type("ROOM_STATE")
            self.assertEqual({p["name"] for p in bob_lobby_state["payload"]["players"]}, {"Alice", "Bob"})
            await alice.wait_for_type("PLAYER_JOINED")

            await bob.send(msg.make_join_room("alpha"))
            bob_state = await bob.wait_for_type("ROOM_STATE")
            self.assertEqual(bob_state["payload"]["room_id"], "alpha")
            self.assertEqual(len(bob_state["payload"]["players"]), 1)

            left = await alice.wait_for_type("PLAYER_LEFT")
            self.assertEqual(left["payload"]["player_id"], bob_welcome["payload"]["player_id"])
            self.assertEqual(left["payload"]["room_id"], "lobby")
            self.assertEqual(left["payload"]["reason"], "left_room")

            await alice.send(msg.make_join_room("alpha"))
            alice_state = await alice.wait_for_type("ROOM_STATE")
            self.assertEqual(alice_state["payload"]["room_id"], "alpha")
            self.assertEqual({p["name"] for p in alice_state["payload"]["players"]}, {"Alice", "Bob"})

            bob_joined = await bob.wait_for_type("PLAYER_JOINED")
            self.assertEqual(bob_joined["payload"]["name"], "Alice")
            self.assertEqual(bob_joined["payload"]["room_id"], "alpha")

            await alice.send(msg.make_event("test", "in-alpha"))
            event = await bob.wait_for_type("EVENT")
            self.assertEqual(event["payload"]["data"], "in-alpha")

        self.run_flow(_with_server(flow))

    def test_event_seq_dedup_ack_and_presence_relay(self):
        async def flow(server, port):
            alice = await FakeClient.connect(port, "Alice")
            await alice.send(msg.make_hello("Alice", "t"))
            alice_pid = (await alice.wait_for_type("WELCOME"))["payload"]["player_id"]
            await alice.wait_for_type("ROOM_STATE")

            bob = await FakeClient.connect(port, "Bob")
            await bob.send(msg.make_hello("Bob", "t"))
            await bob.wait_for_type("WELCOME")
            await bob.wait_for_type("ROOM_STATE")

            # A normal sequenced event: relayed to Bob + acked to Alice.
            await alice.send(msg.make_event("test", "one", seq=1))
            event = await bob.wait_for_type("EVENT")
            self.assertEqual(event["payload"]["seq"], 1)
            self.assertEqual(event["payload"]["player_id"], alice_pid)
            ack = await alice.wait_for_type("EVENT_ACK")
            self.assertEqual(ack["payload"]["seq"], 1)

            # A duplicate resend: acked again but NOT re-broadcast.
            await alice.send(msg.make_event("test", "one", seq=1))
            duplicate_ack = await alice.wait_for_type("EVENT_ACK")
            self.assertEqual(duplicate_ack["payload"]["seq"], 1)
            await asyncio.sleep(0.2)
            self.assertEqual(
                [m for m in bob.messages if m["type"] == "EVENT" and m["payload"]["seq"] == 1],
                [event],
            )

            # Presence: server stamps identity and relays within the room.
            await alice.send(msg.make_presence(7, 12, timestamp=5.5))
            presence = await bob.wait_for_type("PRESENCE")
            self.assertEqual(presence["payload"]["player_id"], alice_pid)
            self.assertEqual(presence["payload"]["room_id"], "lobby")
            self.assertEqual(presence["payload"]["zone_id"], 7)
            self.assertEqual(presence["payload"]["lot_id"], 12)
            self.assertEqual(presence["payload"]["timestamp"], 5.5)
            self.assertTrue(server.session.get_player(alice_pid).presence is not None)

            # Presence is room-scoped: no echo back to the sender.
            await asyncio.sleep(0.2)
            self.assertFalse(any(m["type"] == "PRESENCE" for m in alice.messages))

        self.run_flow(_with_server(flow))

    def test_client_id_resume_keeps_identity_room_and_dedup(self):
        async def flow(server, port):
            # First session: joins a custom room, sends one sequenced event.
            alice1 = await FakeClient.connect(port, "Alice")
            await alice1.send(msg.make_hello("Alice", "t", client_id="AAA"))
            pid = (await alice1.wait_for_type("WELCOME"))["payload"]["player_id"]
            await alice1.wait_for_type("ROOM_STATE")
            await alice1.send(msg.make_join_room("alpha"))
            state = await alice1.wait_for_type("ROOM_STATE")
            self.assertEqual(state["payload"]["room_id"], "alpha")

            bob = await FakeClient.connect(port, "Bob")
            await bob.send(msg.make_hello("Bob", "t"))
            await bob.wait_for_type("WELCOME")
            await bob.wait_for_type("ROOM_STATE")
            await bob.send(msg.make_join_room("alpha"))
            await bob.wait_for_type("ROOM_STATE")
            await alice1.wait_for_type("PLAYER_JOINED")

            await alice1.send(msg.make_event("test", "dedupe-me", seq=5))
            first = await bob.wait_for_type("EVENT")
            self.assertEqual(first["payload"]["seq"], 5)
            self.assertEqual(first["payload"]["player_id"], pid)

            # Close the connection; the identity persists as a ghost player.
            await alice1.close()
            left = await bob.wait_for_type("PLAYER_LEFT")
            self.assertEqual(left["payload"]["player_id"], pid)
            self.assertEqual(left["payload"]["room_id"], "alpha")

            # Reconnect with the same client_id: SAME player_id, SAME room.
            alice2 = await FakeClient.connect(port, "Alice")
            await alice2.send(msg.make_hello("Alice", "t", client_id="AAA"))
            welcome = await alice2.wait_for_type("WELCOME")
            self.assertEqual(welcome["payload"]["player_id"], pid)
            self.assertEqual(welcome["payload"]["room_id"], "alpha")
            state = await alice2.wait_for_type("ROOM_STATE")
            self.assertEqual({p["name"] for p in state["payload"]["players"]}, {"Alice", "Bob"})
            rejoin = await bob.wait_for_type("PLAYER_JOINED")
            self.assertEqual(rejoin["payload"]["player_id"], pid)

            # A resend of the already-relayed seq 5 is acked but NOT relayed
            # again - dedup state survived the reconnect.
            await alice2.send(msg.make_event("test", "dedupe-me", seq=5))
            ack = await alice2.wait_for_type("EVENT_ACK")
            self.assertEqual(ack["payload"]["seq"], 5)
            await asyncio.sleep(0.2)
            self.assertEqual(
                [m for m in bob.messages if m["type"] == "EVENT" and m["payload"]["seq"] == 5],
                [first],
            )

            # New sequences flow normally after the resume.
            await alice2.send(msg.make_event("test", "fresh", seq=6))
            fresh = await bob.wait_for_type("EVENT")
            self.assertEqual(fresh["payload"]["seq"], 6)
            self.assertEqual(fresh["payload"]["data"], "fresh")

        self.run_flow(_with_server(flow))

    def test_client_id_takeover_closes_stale_connection(self):
        async def flow(server, port):
            first = await FakeClient.connect(port, "Alice")
            await first.send(msg.make_hello("Alice", "t", client_id="BBB"))
            pid = (await first.wait_for_type("WELCOME"))["payload"]["player_id"]

            second = await FakeClient.connect(port, "Alice")
            await second.send(msg.make_hello("Alice", "t", client_id="BBB"))
            welcome = await second.wait_for_type("WELCOME")
            self.assertEqual(welcome["payload"]["player_id"], pid)

            # The stale first connection must have been closed by the server.
            with self.assertRaises(RuntimeError):
                while True:
                    await asyncio.wait_for(first.recv(), 5.0)

        self.run_flow(_with_server(flow))

    def test_server_rejects_bad_messages(self):
        async def flow(server, port):
            eve = await FakeClient.connect(port, "Eve")

            unknown = {"version": PROTOCOL_VERSION, "type": "NAUGHTY", "request_id": "r", "payload": {}}
            await eve.send(unknown)
            error = await eve.wait_for_type("ERROR")
            self.assertEqual(error["payload"]["code"], "UNKNOWN_TYPE")

            await eve.send(msg.make_join_room("lobby"))
            error = await eve.wait_for_type("ERROR")
            self.assertEqual(error["payload"]["code"], "NOT_REGISTERED")

            bad_hello = msg.make_hello("Eve", "t")
            bad_hello["payload"]["protocol_version"] = 99
            await eve.send(bad_hello)
            error = await eve.wait_for_type("ERROR")
            self.assertEqual(error["payload"]["code"], "INCOMPATIBLE_VERSION")

            await eve.send(msg.make_hello("Eve", "t"))
            welcome = await eve.wait_for_type("WELCOME")
            self.assertIsNotNone(welcome)

            bad_event = {"version": PROTOCOL_VERSION, "type": "EVENT", "request_id": "r", "payload": {"event_type": "x"}}
            await eve.send(bad_event)
            error = await eve.wait_for_type("ERROR")
            self.assertEqual(error["payload"]["code"], "MALFORMED")

        self.run_flow(_with_server(flow))

    def test_server_reaps_idle_connections_and_keeps_active(self):
        async def flow():
            server = MPServer("127.0.0.1", 0, stale_timeout=0.2, reap_interval=0.05)
            await server.start()
            try:
                alice = await FakeClient.connect(server.port, "Alice")
                await alice.send(msg.make_hello("Alice", "t"))
                alice_pid = (await alice.wait_for_type("WELCOME"))["payload"]["player_id"]
                await alice.wait_for_type("ROOM_STATE")

                bob = await FakeClient.connect(server.port, "Bob")
                await bob.send(msg.make_hello("Bob", "t"))
                await bob.wait_for_type("WELCOME")
                await bob.wait_for_type("ROOM_STATE")
                await alice.wait_for_type("PLAYER_JOINED")

                # Bob keeps sending heartbeats so his last_activity keeps
                # refreshing and he must NOT be reaped.
                async def keep_alive():
                    while True:
                        await bob.send(msg.make_ping(0.0))
                        await asyncio.sleep(0.03)

                keeper = asyncio.get_running_loop().create_task(keep_alive())
                try:
                    # Alice sits silent past stale_timeout and must be reaped.
                    left = await bob.wait_for_type("PLAYER_LEFT", timeout=5.0)
                    self.assertEqual(left["payload"]["player_id"], alice_pid)
                    self.assertEqual(left["payload"]["reason"], "disconnected")

                    # Bob is still connected thanks to his heartbeats.
                    # (Stale PONGs from the keep-alive pings may still be
                    # queued, so resend until a fresh timestamp is echoed.)
                    deadline = time.monotonic() + 5
                    while True:
                        await bob.send(msg.make_ping(9.9))
                        pong = await asyncio.wait_for(bob.recv(), 5)
                        if pong["type"] == "PONG" and pong["payload"]["client_time"] == 9.9:
                            break
                        if time.monotonic() > deadline:
                            self.fail("no PONG echoed the fresh timestamp")
                finally:
                    keeper.cancel()
            finally:
                await server.stop()

        asyncio.run(flow())

    def test_server_expires_stale_cached_presence(self):
        async def flow():
            server = MPServer("127.0.0.1", 0, presence_ttl=0.2, reap_interval=0.05)
            await server.start()
            try:
                alice = await FakeClient.connect(server.port, "Alice")
                await alice.send(msg.make_hello("Alice", "t"))
                alice_pid = (await alice.wait_for_type("WELCOME"))["payload"]["player_id"]
                await alice.wait_for_type("ROOM_STATE")

                await alice.send(msg.make_presence(7, 12, timestamp=5.5))
                presence_deadline = time.monotonic() + 2
                while server.session.get_player(alice_pid).presence is None:
                    if time.monotonic() > presence_deadline:
                        self.fail("presence was never cached")
                    await asyncio.sleep(0.01)
                self.assertIsNotNone(server.session.get_player(alice_pid).presence)

                # After the TTL elapses the cached presence must be pruned.
                await asyncio.sleep(0.6)
                self.assertIsNone(server.session.get_player(alice_pid).presence)
            finally:
                await server.stop()

        asyncio.run(flow())

    def test_world_claim_update_lock_release(self):
        async def flow():
            server = MPServer("127.0.0.1", 0)
            await server.start()
            try:
                alice = await FakeClient.connect(server.port, "Alice")
                await alice.send(msg.make_hello("Alice", "t"))
                alice_pid = (await alice.wait_for_type("WELCOME"))["payload"]["player_id"]
                await alice.wait_for_type("ROOM_STATE")
                world = await alice.wait_for_type("WORLD_STATE")
                self.assertEqual(world["payload"]["objects"], [])

                bob = await FakeClient.connect(server.port, "Bob")
                await bob.send(msg.make_hello("Bob", "t"))
                bob_pid = (await bob.wait_for_type("WELCOME"))["payload"]["player_id"]
                await bob.wait_for_type("ROOM_STATE")
                await bob.wait_for_type("WORLD_STATE")
                await alice.wait_for_type("PLAYER_JOINED")

                # Alice claims the sofa; Bob is notified; Alice gets the ack.
                await alice.send(msg.make_object_claim("sofa"))
                ack = await alice.wait_for_type("OBJECT_CLAIM_ACK")
                self.assertEqual(ack["payload"]["key"], "sofa")
                self.assertEqual(ack["payload"]["owner"], alice_pid)
                owned = await bob.wait_for_type("OBJECT_OWNERSHIP")
                self.assertEqual(owned["payload"]["key"], "sofa")
                self.assertEqual(owned["payload"]["owner"], alice_pid)

                # Bob tries to claim -> OBJECT_LOCKED.
                await bob.send(msg.make_object_claim("sofa"))
                error = await bob.wait_for_type("ERROR")
                self.assertEqual(error["payload"]["code"], "OBJECT_LOCKED")

                # Alice pushes a delta; Bob sees the WORLD_DELTA, no echo back.
                await alice.send(msg.make_object_update([{"key": "sofa", "fields": {"x": 1.0}, "rev": 1}]))
                delta = await bob.wait_for_type("WORLD_DELTA")
                self.assertEqual(delta["payload"]["seq"], 1)
                self.assertEqual(delta["payload"]["updates"][0]["key"], "sofa")
                self.assertEqual(delta["payload"]["updates"][0]["fields"]["x"], 1.0)
                self.assertEqual(delta["payload"]["player_id"], alice_pid)
                await asyncio.sleep(0.2)
                self.assertFalse(any(m["type"] == "WORLD_DELTA" for m in alice.messages))

                # Updating an unclaimed object is rejected.
                await bob.send(msg.make_object_update([{"key": "table", "fields": {"x": 0.0}, "rev": 1}]))
                error = await bob.wait_for_type("ERROR")
                self.assertEqual(error["payload"]["code"], "OBJECT_NOT_FOUND")

                # Alice sees her own claim reflected in a late WORLD_STATE.
                carol = await FakeClient.connect(server.port, "Carol")
                await carol.send(msg.make_hello("Carol", "t"))
                await carol.wait_for_type("WELCOME")
                await carol.wait_for_type("ROOM_STATE")
                carol_world = await carol.wait_for_type("WORLD_STATE")
                self.assertEqual(
                    carol_world["payload"]["objects"],
                    [{"key": "sofa", "owner": alice_pid, "fields": {"x": 1.0}}],
                )

                # Alice releases; Bob (and Carol) see owner -> null.
                await alice.send(msg.make_object_release("sofa"))
                ack = await alice.wait_for_type("OBJECT_CLAIM_ACK")
                self.assertIsNone(ack["payload"]["owner"])
                rel = await bob.wait_for_type("OBJECT_OWNERSHIP")
                self.assertEqual(rel["payload"]["key"], "sofa")
                self.assertIsNone(rel["payload"]["owner"])
            finally:
                await server.stop()

        asyncio.run(flow())

    def test_interaction_fcfs_cooldown_and_state(self):
        async def flow():
            server = MPServer("127.0.0.1", 0, interaction_cooldown=0.2, interaction_max_duration=60.0)
            await server.start()
            try:
                alice = await FakeClient.connect(server.port, "Alice")
                await alice.send(msg.make_hello("Alice", "t"))
                alice_pid = (await alice.wait_for_type("WELCOME"))["payload"]["player_id"]
                await alice.wait_for_type("ROOM_STATE")
                await alice.wait_for_type("WORLD_STATE")
                await alice.wait_for_type("INTERACTION_STATE")

                bob = await FakeClient.connect(server.port, "Bob")
                await bob.send(msg.make_hello("Bob", "t"))
                bob_pid = (await bob.wait_for_type("WELCOME"))["payload"]["player_id"]
                await bob.wait_for_type("ROOM_STATE")
                await bob.wait_for_type("WORLD_STATE")
                await bob.wait_for_type("INTERACTION_STATE")
                await alice.wait_for_type("PLAYER_JOINED")

                # Alice proposes; BOTH peers see the echoed INTERACTION_START.
                await alice.send(
                    msg.make_interaction_request(
                        "sofa",
                        "Read",
                        {"book": "Tome"},
                        affordance="Read",
                        affordance_id=9001,
                        target="sim:7",
                    )
                )
                alice_start = await alice.wait_for_type("INTERACTION_START")
                self.assertEqual(alice_start["payload"]["object_key"], "sofa")
                self.assertEqual(alice_start["payload"]["player_id"], alice_pid)
                self.assertEqual(alice_start["payload"]["args"], {"book": "Tome"})
                self.assertEqual(alice_start["payload"]["affordance"], "Read")
                self.assertEqual(alice_start["payload"]["affordance_id"], 9001)
                self.assertEqual(alice_start["payload"]["target"], "sim:7")
                bob_start = await bob.wait_for_type("INTERACTION_START")
                self.assertEqual(bob_start["payload"]["object_key"], "sofa")
                self.assertEqual(bob_start["payload"]["player_id"], alice_pid)
                self.assertEqual(bob_start["payload"]["affordance"], "Read")

                # Bob's proposal for the busy key -> INTERACTION_BUSY + ref.
                await bob.send(msg.make_interaction_request("sofa", "Sit"))
                error = await bob.wait_for_type("ERROR")
                self.assertEqual(error["payload"]["code"], "INTERACTION_BUSY")
                self.assertEqual(error["payload"]["ref"], "sofa")

                # A late joiner sees the interaction in the INTERACTION_STATE snapshot.
                carol = await FakeClient.connect(server.port, "Carol")
                await carol.send(msg.make_hello("Carol", "t"))
                await carol.wait_for_type("WELCOME")
                await carol.wait_for_type("ROOM_STATE")
                await carol.wait_for_type("WORLD_STATE")
                state = await carol.wait_for_type("INTERACTION_STATE")
                self.assertEqual(
                    state["payload"]["interactions"],
                    [{
                        "object_key": "sofa",
                        "player_id": alice_pid,
                        "interaction": "Read",
                        "started_at": alice_start["payload"]["started_at"],
                        "args": {"book": "Tome"},
                        "affordance": "Read",
                        "affordance_id": 9001,
                        "target": "sim:7",
                    }],
                )

                # Alice ends; everyone gets INTERACTION_FREE with cooldown_until.
                await alice.send(msg.make_interaction_end("sofa"))
                alice_free = await alice.wait_for_type("INTERACTION_FREE")
                self.assertEqual(alice_free["payload"]["object_key"], "sofa")
                self.assertGreater(alice_free["payload"]["cooldown_until"], time.time())
                await bob.wait_for_type("INTERACTION_FREE")

                # During the cooldown Bob is rejected, then can start after it.
                await bob.send(msg.make_interaction_request("sofa", "Sit"))
                error = await bob.wait_for_type("ERROR")
                self.assertEqual(error["payload"]["code"], "INTERACTION_COOLDOWN")
                self.assertEqual(error["payload"]["ref"], "sofa")
                await asyncio.sleep(0.3)
                await bob.send(msg.make_interaction_request("sofa", "Sit"))
                bob_start = await bob.wait_for_type("INTERACTION_START")
                self.assertEqual(bob_start["payload"]["player_id"], bob_pid)

                # Ending an interaction someone else holds -> INTERACTION_NOT_HELD.
                await alice.send(msg.make_interaction_end("sofa"))
                error = await alice.wait_for_type("ERROR")
                self.assertEqual(error["payload"]["code"], "INTERACTION_NOT_HELD")
                self.assertEqual(error["payload"]["ref"], "sofa")
            finally:
                await server.stop()

        asyncio.run(flow())

    def test_interaction_watchdog_releases_overdue(self):
        async def flow():
            server = MPServer("127.0.0.1", 0, interaction_max_duration=0.3, reap_interval=0.05)
            await server.start()
            try:
                alice = await FakeClient.connect(server.port, "Alice")
                await alice.send(msg.make_hello("Alice", "t"))
                await alice.wait_for_type("WELCOME")
                await alice.wait_for_type("ROOM_STATE")
                await alice.wait_for_type("WORLD_STATE")
                await alice.wait_for_type("INTERACTION_STATE")

                await alice.send(msg.make_interaction_request("sofa", "Read"))
                await alice.wait_for_type("INTERACTION_START")

                # Alice never sends END; the reaper auto-releases after
                # interaction_max_duration and broadcasts INTERACTION_FREE.
                released = await alice.wait_for_type("INTERACTION_FREE", timeout=5.0)
                self.assertEqual(released["payload"]["object_key"], "sofa")
                self.assertGreater(released["payload"]["cooldown_until"], time.time())
            finally:
                await server.stop()

        asyncio.run(flow())

    def test_ghost_ownership_survives_reconnect_and_takeover(self):
        async def flow():
            server = MPServer(
                "127.0.0.1", 0, interaction_cooldown=5.0, ghost_ownership_ttl=60.0, reap_interval=0.05
            )
            await server.start()
            try:
                alice = await FakeClient.connect(server.port, "Alice")
                await alice.send(msg.make_hello("Alice", "t", client_id="ALICE"))
                alice_pid = (await alice.wait_for_type("WELCOME"))["payload"]["player_id"]
                await alice.wait_for_type("ROOM_STATE")
                await alice.wait_for_type("WORLD_STATE")
                await alice.wait_for_type("INTERACTION_STATE")

                bob = await FakeClient.connect(server.port, "Bob")
                await bob.send(msg.make_hello("Bob", "t"))
                bob_pid = (await bob.wait_for_type("WELCOME"))["payload"]["player_id"]
                await bob.wait_for_type("ROOM_STATE")
                await bob.wait_for_type("WORLD_STATE")
                await bob.wait_for_type("INTERACTION_STATE")
                await alice.wait_for_type("PLAYER_JOINED")

                await alice.send(msg.make_object_claim("sofa"))
                await alice.wait_for_type("OBJECT_CLAIM_ACK")
                await bob.wait_for_type("OBJECT_OWNERSHIP")
                await alice.send(msg.make_interaction_request("sofa", "Read"))
                await alice.wait_for_type("INTERACTION_START")
                await bob.wait_for_type("INTERACTION_START")

                # Drop Alice's socket. During the ghost period NO release is
                # broadcast: ownership and the held interaction stay reserved.
                before_drop = len(bob.messages)
                alice._writer.close()
                await alice._writer.wait_closed()
                left = await bob.wait_for_type("PLAYER_LEFT")
                self.assertEqual(left["payload"]["player_id"], alice_pid)
                await asyncio.sleep(0.2)
                self.assertFalse(any(
                    m["type"] in ("OBJECT_OWNERSHIP", "INTERACTION_FREE")
                    and m["payload"]["room_id"] == "lobby"
                    for m in bob.messages[before_drop:]
                ), "ghost period must not release ownership")

                # Same client_id returns -> identity resumes with state intact.
                alice2 = await FakeClient.connect(server.port, "Alice")
                await alice2.send(msg.make_hello("Alice", "t", client_id="ALICE"))
                await alice2.wait_for_type("WELCOME")
                await alice2.wait_for_type("ROOM_STATE")
                world = await alice2.wait_for_type("WORLD_STATE")
                self.assertIn(
                    {"key": "sofa", "owner": alice_pid},
                    [{"key": o["key"], "owner": o["owner"]} for o in world["payload"]["objects"]],
                )
                inter = await alice2.wait_for_type("INTERACTION_STATE")
                self.assertTrue(any(
                    e["object_key"] == "sofa" and e["player_id"] == alice_pid and e["interaction"] == "Read"
                    for e in inter["payload"]["interactions"]
                ), "resumed interaction state missing")
                alice2._writer.close()
            finally:
                await server.stop()

        asyncio.run(flow())

    def test_ghost_eviction_releases_ownership_then_fresh_resume(self):
        async def flow():
            server = MPServer(
                "127.0.0.1", 0, interaction_cooldown=5.0, ghost_ownership_ttl=0.2, reap_interval=0.05
            )
            await server.start()
            try:
                alice = await FakeClient.connect(server.port, "Alice")
                await alice.send(msg.make_hello("Alice", "t", client_id="ALICE"))
                alice_pid = (await alice.wait_for_type("WELCOME"))["payload"]["player_id"]
                await alice.wait_for_type("ROOM_STATE")
                await alice.wait_for_type("WORLD_STATE")
                await alice.wait_for_type("INTERACTION_STATE")

                bob = await FakeClient.connect(server.port, "Bob")
                await bob.send(msg.make_hello("Bob", "t"))
                bob_pid = (await bob.wait_for_type("WELCOME"))["payload"]["player_id"]
                await bob.wait_for_type("ROOM_STATE")
                await bob.wait_for_type("WORLD_STATE")
                await bob.wait_for_type("INTERACTION_STATE")
                await alice.wait_for_type("PLAYER_JOINED")

                await alice.send(msg.make_object_claim("sofa"))
                await alice.wait_for_type("OBJECT_CLAIM_ACK")
                await bob.wait_for_type("OBJECT_OWNERSHIP")
                await alice.send(msg.make_interaction_request("sofa", "Read"))
                await alice.wait_for_type("INTERACTION_START")
                await bob.wait_for_type("INTERACTION_START")

                alice._writer.close()
                await alice._writer.wait_closed()
                await bob.wait_for_type("PLAYER_LEFT")

                # The reaper evicts the ghost after 0.2s and broadcasts both
                # releases (interaction free first, then ownership null).
                def ghost_released(frame):
                    null_ownership = frame["type"] == "OBJECT_OWNERSHIP" and frame["payload"].get("owner") is None
                    free_seen = any(
                        m["type"] == "INTERACTION_FREE" and m["payload"]["room_id"] == "lobby"
                        for m in bob.messages
                    )
                    return null_ownership and free_seen

                await bob.recv_until(ghost_released, timeout=5.0)

                ownership = next(
                    m for m in bob.messages
                    if m["type"] == "OBJECT_OWNERSHIP" and m["payload"].get("owner") is None
                )
                self.assertEqual(ownership["payload"]["key"], "sofa")
                released = next(
                    m for m in bob.messages
                    if m["type"] == "INTERACTION_FREE" and m["payload"]["room_id"] == "lobby"
                )
                self.assertEqual(released["payload"]["object_key"], "sofa")

                await bob.send(msg.make_object_claim("sofa"))
                ack = await bob.wait_for_type("OBJECT_CLAIM_ACK", timeout=5.0)
                self.assertEqual(ack["payload"]["owner"], bob_pid)

                # A much-later reconnect with the same client_id starts fresh
                # (the identity was forgotten with the ghost).
                alice3 = await FakeClient.connect(server.port, "Alice")
                await alice3.send(msg.make_hello("Alice", "t", client_id="ALICE"))
                welcome = await alice3.wait_for_type("WELCOME")
                self.assertNotEqual(welcome["payload"]["player_id"], alice_pid)
                alice3._writer.close()
            finally:
                await server.stop()

        asyncio.run(flow())

    def test_oversized_and_garbage_frames_do_not_crash_server(self):
        async def flow():
            server = MPServer("127.0.0.1", 0)
            await server.start()
            try:
                # A frame whose declared length exceeds MAX_FRAME_BYTES is
                # rejected before its body is even read: MALFORMED reply, and
                # the connection loop keeps running (then EOF on close).
                reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
                writer.write(struct.pack(">I", MAX_FRAME_BYTES + 1) + b"{}")
                await writer.drain()
                reply = await asyncio.wait_for(framing.read_frame(reader), 5.0)
                self.assertEqual(reply["type"], "ERROR")
                self.assertEqual(reply["payload"]["code"], "MALFORMED")
                writer.close()
                await writer.wait_closed()

                # Garbage JSON (invalid body) also gets a MALFORMED reply.
                reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
                body = b'{"a":'
                writer.write(struct.pack(">I", len(body)) + body)
                await writer.drain()
                reply = await asyncio.wait_for(framing.read_frame(reader), 5.0)
                self.assertEqual(reply["type"], "ERROR")
                self.assertEqual(reply["payload"]["code"], "MALFORMED")
                writer.close()
                await writer.wait_closed()

                # A structurally-valid but huge WORLD_STATE (built by hand to bypass the
                # builder's object-count check) is still bounded by the
                # frame-size gate and rejected the same way.
                big_objects = [
                    {"key": "obj%05d" % i, "owner": None, "fields": {"v": "x" * 256}}
                    for i in range(30000)
                ]
                big = {
                    "type": "WORLD_STATE",
                    "version": PROTOCOL_VERSION,
                    "request_id": "manual",
                    "payload": {"room_id": "lobby", "objects": big_objects},
                }
                reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
                payload_bytes = json.dumps(big, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self.assertGreater(len(payload_bytes), MAX_FRAME_BYTES)
                writer.write(struct.pack(">I", len(payload_bytes)) + payload_bytes)
                await writer.drain()
                reply = await asyncio.wait_for(framing.read_frame(reader), 5.0)
                self.assertEqual(reply["type"], "ERROR")
                self.assertEqual(reply["payload"]["code"], "MALFORMED")
                writer.close()
                await writer.wait_closed()

                # The server is still healthy and accepts a fresh client.
                client = await FakeClient.connect(server.port, "Survivor")
                await client.send(msg.make_hello("Survivor", "t"))
                welcome = await client.wait_for_type("WELCOME")
                self.assertIsNotNone(welcome["payload"]["player_id"])
                client._writer.close()
            finally:
                await server.stop()

        asyncio.run(flow())


if __name__ == "__main__":
    unittest.main()
class SavePushFlowTests(unittest.TestCase):
    def run_flow(self, coro):
        asyncio.run(coro)

    def test_save_push_relayed_and_acked(self):
        async def flow(server, port):
            alice = await FakeClient.connect(port, "Alice")
            await alice.send(msg.make_hello("Alice", "t"))
            await alice.wait_for_type("WELCOME")

            bob = await FakeClient.connect(port, "Bob")
            await bob.send(msg.make_hello("Bob", "t"))
            await bob.wait_for_type("WELCOME")
            await alice.recv_until(lambda m: m["type"] == "PLAYER_JOINED")

            payload = b"\x00\x01\x02\xff" * 64
            await alice.send(msg.make_save_push("slot_00000001.save", 1, 2, len(payload) * 2, payload))

            chunk = await bob.wait_for_type("SAVE_PUSH")
            self.assertEqual(chunk["payload"]["slot"], "slot_00000001.save")
            self.assertEqual(chunk["payload"]["seq"], 1)
            self.assertEqual(chunk["payload"]["total"], 2)
            self.assertEqual(chunk["payload"]["origin"], 1000)
            import base64
            self.assertEqual(base64.b64decode(chunk["payload"]["data"]), payload)

            ack = await alice.wait_for_type("SAVE_ACK")
            self.assertEqual(ack["payload"]["slot"], "slot_00000001.save")
            self.assertTrue(ack["payload"]["ok"])
            self.assertEqual(ack["payload"]["reached"], 1)
            self.assertEqual(ack["payload"]["seq"], 1)
            self.assertEqual(ack["payload"]["total"], 2)

        self.run_flow(_with_server(flow))

    def test_save_push_solo_ack_reached_zero(self):
        async def flow(server, port):
            alice = await FakeClient.connect(port, "Alice")
            await alice.send(msg.make_hello("Alice", "t"))
            await alice.wait_for_type("WELCOME")

            await alice.send(msg.make_save_push("slot_00000001.save", 1, 1, 3, b"\x01\x02\x03"))
            ack = await alice.wait_for_type("SAVE_ACK")
            self.assertTrue(ack["payload"]["ok"])
            self.assertEqual(ack["payload"]["reached"], 0)
            self.assertEqual(ack["payload"]["seq"], 1)
            self.assertEqual(ack["payload"]["total"], 1)
            self.assertFalse(any(m["type"] == "SAVE_PUSH" for m in alice.messages))

        self.run_flow(_with_server(flow))

    def test_save_push_requires_registration(self):
        async def flow(server, port):
            alice = await FakeClient.connect(port, "Alice")
            await alice.send(msg.make_save_push("slot_00000001.save", 1, 1, 0, b""))
            error = await alice.wait_for_type("ERROR")
            self.assertEqual(error["payload"]["code"], "NOT_REGISTERED")

        self.run_flow(_with_server(flow))


class StatusFileTests(unittest.TestCase):
    def run_flow(self, coro):
        asyncio.run(coro)

    def test_status_file_contains_players_and_rooms(self):
        import os
        import tempfile

        async def _wait_status(path, predicate, timeout=3.0):
            deadline = time.time() + timeout
            while True:
                with open(path, "r", encoding="utf-8") as handle:
                    snapshot = json.load(handle)
                if predicate(snapshot):
                    return snapshot
                if time.time() > deadline:
                    raise AssertionError("status file never satisfied predicate")
                await asyncio.sleep(0.1)

        async def flow():
            directory = tempfile.mkdtemp()
            status_path = os.path.join(directory, "status.json")
            server = MPServer("127.0.0.1", 0, status_file=status_path)
            await server.start()
            try:
                alice = await FakeClient.connect(server.port, "Alice")
                await alice.send(msg.make_hello("Alice", "t"))
                await alice.wait_for_type("WELCOME")
                snapshot = await _wait_status(status_path, lambda s: s["connections"] == 1)
                self.assertEqual(snapshot["host"], "127.0.0.1")
                self.assertEqual(snapshot["connections"], 1)
                self.assertEqual([p["name"] for p in snapshot["players"]], ["Alice"])
                self.assertEqual([p["name"] for p in snapshot["rooms"][0]["players"]], ["Alice"])
                await alice.close()
                snapshot = await _wait_status(status_path, lambda s: s["connections"] == 0)
                self.assertEqual(snapshot["connections"], 0)
            finally:
                await server.stop()

        self.run_flow(flow())


class LiveFlowTests(unittest.TestCase):
    def run_flow(self, coro):
        asyncio.run(coro)

    def test_funds_sync_echoes_including_sender(self):
        async def flow(server, port):
            alice = await FakeClient.connect(port, "Alice")
            await alice.send(msg.make_hello("Alice", "t"))
            await alice.wait_for_type("WELCOME")

            bob = await FakeClient.connect(port, "Bob")
            await bob.send(msg.make_hello("Bob", "t"))
            await bob.wait_for_type("WELCOME")
            await alice.recv_until(lambda m: m["type"] == "PLAYER_JOINED")

            await alice.send(msg.make_funds_sync(25000, player_id=None))
            alice_sync = await alice.wait_for_type("FUNDS_SYNC")
            bob_sync = await bob.wait_for_type("FUNDS_SYNC")
            self.assertEqual(alice_sync["payload"]["balance"], 25000)
            self.assertEqual(bob_sync["payload"]["balance"], 25000)
            self.assertEqual(
                server.session.get_room_funds("lobby")["balance"], 25000
            )

        self.run_flow(_with_server(flow))

    def test_object_gone_owned_relayed_and_catalog_removed(self):
        async def flow(server, port):
            alice = await FakeClient.connect(port, "Alice")
            await alice.send(msg.make_hello("Alice", "t"))
            await alice.wait_for_type("WELCOME")

            bob = await FakeClient.connect(port, "Bob")
            await bob.send(msg.make_hello("Bob", "t"))
            await bob.wait_for_type("WELCOME")
            await alice.recv_until(lambda m: m["type"] == "PLAYER_JOINED")

            # Alice claims and populates the object.
            await alice.send(msg.make_object_claim("obj:9@1_2_3"))
            await alice.wait_for_type("OBJECT_CLAIM_ACK")
            await bob.wait_for_type("OBJECT_OWNERSHIP")
            await alice.send(msg.make_object_update([{"key": "obj:9@1_2_3", "fields": {"x": 1.0}, "rev": 1}]))
            await bob.wait_for_type("WORLD_DELTA")

            # Non-owner (Bob) cannot delete: lock error, catalog intact, no relay.
            await bob.send(msg.make_object_gone("obj:9@1_2_3"))
            error = await bob.wait_for_type("ERROR")
            self.assertEqual(error["payload"]["code"], "OBJECT_LOCKED")
            self.assertIn(
                "obj:9@1_2_3",
                [o["key"] for o in server.session.get_world_objects("lobby")],
            )
            await asyncio.sleep(0.2)
            self.assertFalse(any(m["type"] == "OBJECT_GONE" for m in alice.messages))

            # Owner removes it: relayed to Bob, catalog entry dropped.
            await alice.send(msg.make_object_gone("obj:9@1_2_3"))
            relay = await bob.wait_for_type("OBJECT_GONE")
            self.assertEqual(relay["payload"]["key"], "obj:9@1_2_3")
            await asyncio.sleep(0.2)
            self.assertNotIn(
                "obj:9@1_2_3",
                [o["key"] for o in server.session.get_world_objects("lobby")],
            )
            self.assertFalse(any(m["type"] == "OBJECT_GONE" for m in alice.messages))

        self.run_flow(_with_server(flow))

    def test_time_unready_re_gates_room(self):
        async def drain_until(client, gate_value):
            """Read TIME_SYNCs until one matches `gate` == gate_value."""
            while True:
                sync = await client.wait_for_type("TIME_SYNC")
                if sync["payload"].get("gate") is gate_value:
                    return sync

        async def flow(server, port):
            alice = await FakeClient.connect(port, "Alice")
            await alice.send(msg.make_hello("Alice", "t"))
            await alice.wait_for_type("WELCOME")

            bob = await FakeClient.connect(port, "Bob")
            await bob.send(msg.make_hello("Bob", "t"))
            await bob.wait_for_type("WELCOME")
            await alice.recv_until(lambda m: m["type"] == "PLAYER_JOINED")

            # Both ready -> gate opens.
            await alice.send(msg.make_time_ready(100))
            await bob.send(msg.make_time_ready(100))
            a_open = await drain_until(alice, False)
            b_open = await drain_until(bob, False)
            self.assertEqual(a_open["payload"]["speed"], 1)
            self.assertEqual(b_open["payload"]["speed"], 1)

            # Bob goes to CAS/a menu -> whole room pauses until he re-readies.
            await bob.send(msg.make_time_unready())
            a_gated = await drain_until(alice, True)
            b_gated = await drain_until(bob, True)
            self.assertEqual(a_gated["payload"]["speed"], 0)
            self.assertEqual(b_gated["payload"]["speed"], 0)

            # Re-ready re-opens the gate.
            await bob.send(msg.make_time_ready(100))
            a_reopen = await drain_until(alice, False)
            b_reopen = await drain_until(bob, False)
            self.assertEqual(a_reopen["payload"]["speed"], 1)
            self.assertEqual(b_reopen["payload"]["speed"], 1)

        self.run_flow(_time_server(flow))


async def _time_server(flow):
    server = MPServer("127.0.0.1", 0)
    await server.start()
    try:
        await flow(server, server.port)
    finally:
        await server.stop()
