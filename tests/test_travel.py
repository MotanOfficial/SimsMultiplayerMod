import asyncio
import unittest

from simmp import messages as msg
from server.networking.server import MPServer
from tests.test_server import FakeClient, _with_server


class TravelServerTests(unittest.TestCase):
    def run_flow(self, coro):
        asyncio.run(coro)

    async def _connect_pair(self, port):
        alice = await FakeClient.connect(port, "Alice")
        await alice.send(msg.make_hello("Alice", "t"))
        alice_pid = (await alice.wait_for_type("WELCOME"))["payload"]["player_id"]
        await alice.wait_for_type("ROOM_STATE")

        bob = await FakeClient.connect(port, "Bob")
        await bob.send(msg.make_hello("Bob", "t"))
        bob_pid = (await bob.wait_for_type("WELCOME"))["payload"]["player_id"]
        await bob.wait_for_type("ROOM_STATE")
        await alice.wait_for_type("PLAYER_JOINED")
        return alice, bob, alice_pid, bob_pid

    def test_travel_invite_accept_begin_ready_complete(self):
        async def flow(server, port):
            alice, bob, alice_pid, bob_pid = await self._connect_pair(port)

            await alice.send(msg.make_travel_request(12345, request_id_value="req-1"))
            invite = await bob.wait_for_type("TRAVEL_INVITE")
            self.assertEqual(invite["request_id"], "req-1")
            self.assertEqual(invite["payload"]["zone_id"], 12345)
            self.assertEqual(invite["payload"]["requester_id"], alice_pid)
            self.assertEqual(invite["payload"]["requester_name"], "Alice")

            await bob.send(msg.make_travel_response(True, request_id_value="req-1"))

            begin_alice = await alice.wait_for_type("TRAVEL_BEGIN")
            begin_bob = await bob.wait_for_type("TRAVEL_BEGIN")
            self.assertEqual(begin_alice["request_id"], "req-1")
            self.assertEqual(begin_alice["payload"]["zone_id"], 12345)
            self.assertEqual(begin_bob["payload"]["zone_id"], 12345)

            await alice.send(msg.make_travel_ready(12345, request_id_value="req-1"))
            await bob.send(msg.make_travel_ready(12345, request_id_value="req-1"))

            complete_alice = await alice.wait_for_type("TRAVEL_COMPLETE")
            complete_bob = await bob.wait_for_type("TRAVEL_COMPLETE")
            self.assertEqual(complete_alice["request_id"], "req-1")
            self.assertEqual(complete_alice["payload"]["zone_id"], 12345)
            self.assertEqual(complete_bob["payload"]["zone_id"], 12345)

        self.run_flow(_with_server(flow))

    def test_travel_solo_begins_immediately(self):
        async def flow(server, port):
            alice = await FakeClient.connect(port, "Alice")
            await alice.send(msg.make_hello("Alice", "t"))
            await alice.wait_for_type("WELCOME")
            await alice.wait_for_type("ROOM_STATE")

            await alice.send(msg.make_travel_request(999, request_id_value="solo"))
            begin = await alice.wait_for_type("TRAVEL_BEGIN")
            self.assertEqual(begin["request_id"], "solo")
            self.assertEqual(begin["payload"]["zone_id"], 999)

            await alice.send(msg.make_travel_ready(999, request_id_value="solo"))
            complete = await alice.wait_for_type("TRAVEL_COMPLETE")
            self.assertEqual(complete["payload"]["zone_id"], 999)

        self.run_flow(_with_server(flow))

    def test_travel_decline_aborts(self):
        async def flow(server, port):
            alice, bob, _, _ = await self._connect_pair(port)

            await alice.send(msg.make_travel_request(12345, request_id_value="req-d"))
            await bob.wait_for_type("TRAVEL_INVITE")
            await bob.send(msg.make_travel_response(False, reason="no thanks", request_id_value="req-d"))

            abort_alice = await alice.wait_for_type("TRAVEL_ABORT")
            abort_bob = await bob.wait_for_type("TRAVEL_ABORT")
            self.assertEqual(abort_alice["request_id"], "req-d")
            self.assertIn("no thanks", abort_alice["payload"]["reason"])
            self.assertEqual(abort_bob["payload"]["reason"], abort_alice["payload"]["reason"])

            await asyncio.sleep(0.2)
            self.assertFalse(any(m["type"] == "TRAVEL_BEGIN" for m in bob.messages))

        self.run_flow(_with_server(flow))

    def test_travel_invite_timeout_aborts(self):
        async def flow(server, port):
            server.travel.invite_timeout = 0.2
            alice, bob, _, _ = await self._connect_pair(port)

            await alice.send(msg.make_travel_request(12345, request_id_value="req-t"))
            await bob.wait_for_type("TRAVEL_INVITE")
            abort = await alice.wait_for_type("TRAVEL_ABORT", timeout=5.0)
            self.assertEqual(abort["payload"]["reason"], "invite timeout")

        self.run_flow(_with_server(flow))

    def test_travel_ready_timeout_aborts(self):
        async def flow(server, port):
            server.travel.ready_timeout = 0.2
            alice, bob, _, _ = await self._connect_pair(port)

            await alice.send(msg.make_travel_request(12345, request_id_value="req-r"))
            await bob.wait_for_type("TRAVEL_INVITE")
            await bob.send(msg.make_travel_response(True, request_id_value="req-r"))
            await alice.wait_for_type("TRAVEL_BEGIN")

            abort = await alice.wait_for_type("TRAVEL_ABORT", timeout=5.0)
            self.assertEqual(abort["payload"]["reason"], "ready timeout")

        self.run_flow(_with_server(flow))

    def test_travel_full_room_ready_timeout_aborts_when_others_silent(self):
        async def flow(server, port):
            server.travel.ready_timeout = 0.2
            alice, bob, _, _ = await self._connect_pair(port)

            await alice.send(msg.make_travel_request(12345, request_id_value="req-r2"))
            await bob.wait_for_type("TRAVEL_INVITE")
            await bob.send(msg.make_travel_response(True, request_id_value="req-r2"))
            await alice.wait_for_type("TRAVEL_BEGIN")

            # Alice reports ready but Bob stays silent -> still aborts.
            await alice.send(msg.make_travel_ready(12345, request_id_value="req-r2"))
            abort = await alice.wait_for_type("TRAVEL_ABORT", timeout=5.0)
            self.assertEqual(abort["payload"]["reason"], "ready timeout")

        self.run_flow(_with_server(flow))

    def test_travel_member_disconnect_aborts(self):
        async def flow(server, port):
            alice, bob, _, _ = await self._connect_pair(port)

            await alice.send(msg.make_travel_request(12345, request_id_value="req-dc"))
            await bob.wait_for_type("TRAVEL_INVITE")
            await bob.close()
            abort = await alice.wait_for_type("TRAVEL_ABORT", timeout=5.0)
            self.assertEqual(abort["payload"]["reason"], "member disconnected")

        self.run_flow(_with_server(flow))

    def test_travel_wrong_zone_ready_aborts(self):
        async def flow(server, port):
            alice, bob, _, _ = await self._connect_pair(port)

            await alice.send(msg.make_travel_request(12345, request_id_value="req-w"))
            await bob.wait_for_type("TRAVEL_INVITE")
            await bob.send(msg.make_travel_response(True, request_id_value="req-w"))
            await alice.wait_for_type("TRAVEL_BEGIN")

            await alice.send(msg.make_travel_ready(54321, request_id_value="req-w"))
            abort = await alice.wait_for_type("TRAVEL_ABORT", timeout=5.0)
            self.assertIn("wrong zone", abort["payload"]["reason"])

        self.run_flow(_with_server(flow))

    def test_travel_request_requires_registration(self):
        async def flow(server, port):
            stranger = await FakeClient.connect(port, "Stranger")
            await stranger.send(msg.make_travel_request(1))
            error = await stranger.wait_for_type("ERROR")
            self.assertEqual(error["payload"]["code"], "NOT_REGISTERED")

        self.run_flow(_with_server(flow))

    def test_clock_sync_relayed_with_origin(self):
        async def flow(server, port):
            alice, bob, alice_pid, _ = await self._connect_pair(port)

            await alice.send(msg.make_clock_sync(12345, 1000000, 12345678.5, 1))
            sync = await bob.wait_for_type("CLOCK_SYNC")
            self.assertEqual(sync["payload"]["player_id"], alice_pid)
            self.assertEqual(sync["payload"]["zone_id"], 12345)
            self.assertEqual(sync["payload"]["absolute_ticks"], 1000000)
            self.assertEqual(sync["payload"]["real_time"], 12345678.5)
            self.assertEqual(sync["payload"]["clock_speed"], 1)

        self.run_flow(_with_server(flow))


if __name__ == "__main__":
    unittest.main()