import asyncio
import json
import os
import tempfile
import time
import unittest
from unittest import mock

from simmp import messages as msg
from simmp.constants import PROTOCOL_VERSION
from simmp.validation import ProtocolError, validate_message
from simmp_client.connectivity import MultiplayerClient
from server.networking.server import MPServer
from tests.test_server import FakeClient


class TimeValidationTests(unittest.TestCase):
    def assert_protocol_error(self, message, code):
        with self.assertRaises(ProtocolError) as catch:
            validate_message(message)
        self.assertEqual(catch.exception.code, code)

    def test_time_messages_pass_validation(self):
        for message in [
            msg.make_time_sync(0),
            msg.make_time_sync(1, ticks=1234),
            msg.make_time_sync(3, ticks=5, player_id=7),
            msg.make_time_ready(42),
            msg.make_time_speed(2),
            msg.make_time_speed(0, ticks=99),
            msg.make_time_speed(3, player_id=4),
        ]:
            result = validate_message(message)
            self.assertIs(result, message)

    def test_time_sync_speed_range(self):
        for bad in (4, -1, True, "1", 1.5):
            message = msg.make_time_sync(1)
            message["payload"]["speed"] = bad
            self.assert_protocol_error(message, "MALFORMED")

    def test_time_speed_speed_range(self):
        for bad in (5, -2, True, "0"):
            message = msg.make_time_speed(1)
            message["payload"]["speed"] = bad
            self.assert_protocol_error(message, "MALFORMED")

    def test_time_sync_ticks_negative_rejected(self):
        message = {
            "version": PROTOCOL_VERSION,
            "type": "TIME_SYNC",
            "request_id": "r",
            "payload": {"speed": 1, "ticks": -1},
        }
        self.assert_protocol_error(message, "MALFORMED")

    def test_time_ready_missing_zone_rejected(self):
        message = msg.make_time_ready(1)
        del message["payload"]["zone_id"]
        self.assert_protocol_error(message, "MALFORMED")


class TimeServerFlowTests(unittest.TestCase):
    def run_flow(self, coro):
        asyncio.run(coro)

    @staticmethod
    async def _hello(port, name, client_id=None):
        client = await FakeClient.connect(port, name)
        await client.send(msg.make_hello(name, "t", client_id=client_id))
        await client.wait_for_type("WELCOME")
        await client.wait_for_type("ROOM_STATE")
        return client

    async def _sync(self, client, timeout=5.0):
        return await client.wait_for_type("TIME_SYNC", timeout=timeout)

    async def _last_sync(self, client, settle=0.2, timeout=5.0):
        """Consume all pending TIME_SYNC frames and return the last one.

        The room clock broadcasts to the whole room on every transition, so a
        client outstanding multiple TIME_SYNCs (e.g. a stale PAUSED followed
        by RUN). This waits until `settle` seconds of silence and returns the
        authoritative final state.
        """
        last = None
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                break
            try:
                frame = await asyncio.wait_for(
                    client.wait_for_type("TIME_SYNC"), timeout=min(settle, remaining)
                )
            except asyncio.TimeoutError:
                break
            last = frame
        if last is None:
            raise RuntimeError("no TIME_SYNC received")
        return last

    def test_joining_client_is_paused_until_everyone_ready(self):
        async def flow(server, port):
            alice = await self._hello(port, "Alice")
            sync = await self._last_sync(alice)
            self.assertEqual(sync["payload"]["speed"], 0, "lone client still gated")

            bob = await self._hello(port, "Bob")
            sync = await self._last_sync(bob)
            self.assertEqual(sync["payload"]["speed"], 0, "new client must join paused")
            sync = await self._last_sync(alice)
            self.assertEqual(sync["payload"]["speed"], 0, "Alice saw gate close for Bob")

            await alice.send(msg.make_time_ready(100))
            sync = await self._last_sync(alice)
            self.assertEqual(sync["payload"]["speed"], 0, "still gated: Bob not ready")
            sync = await self._last_sync(bob)
            self.assertEqual(sync["payload"]["speed"], 0)

            await bob.send(msg.make_time_ready(100))
            a_sync = await self._last_sync(alice)
            b_sync = await self._last_sync(bob)
            self.assertEqual(a_sync["payload"]["speed"], 1, "gate opened: default normal")
            self.assertEqual(b_sync["payload"]["speed"], 1)

            await alice.close()
            await bob.close()

        self.run_flow(_time_server(flow))

    def test_gated_speed_change_is_stored_then_applied(self):
        async def flow(server, port):
            alice = await self._hello(port, "Alice")
            await self._last_sync(alice)
            bob = await self._hello(port, "Bob")
            await self._last_sync(bob)
            await self._last_sync(alice)

            # Alice is ready; Bob has not readied yet: the gate is closed.
            await alice.send(msg.make_time_ready(100))
            await self._last_sync(alice)
            await self._last_sync(bob)

            # Alice wants fast speed but Bob is not ready: the server keeps
            # broadcasting PAUSED and stores the desire for when the gate opens.
            await alice.send(msg.make_time_speed(3))
            a_sync = await self._last_sync(alice)
            self.assertEqual(a_sync["payload"]["speed"], 0, "gate still closed")
            self.assertEqual(server.session.get_room("lobby").clock["desired"], 3)
            self.assertEqual(server.session.get_room("lobby").clock["by_player"], 1000)

            await bob.send(msg.make_time_ready(100))
            b_sync = await self._last_sync(bob)
            self.assertEqual(b_sync["payload"]["speed"], 3, "stored speed applied on gate open")
            a_sync = await self._last_sync(alice)
            self.assertEqual(a_sync["payload"]["speed"], 3)

            await alice.close()
            await bob.close()

        self.run_flow(_time_server(flow))

    def test_disconnect_auto_pauses_and_stored_speed_resumes(self):
        async def flow(server, port):
            alice = await self._hello(port, "Alice")
            await self._last_sync(alice)
            bob = await self._hello(port, "Bob", client_id="BOB-STABLE")
            await self._last_sync(bob)
            await self._last_sync(alice)

            await alice.send(msg.make_time_ready(100))
            await self._last_sync(alice)
            await bob.send(msg.make_time_ready(100))
            await self._last_sync(alice)
            await self._last_sync(bob)

            # Alice sets fast speed; server relays it to the whole room.
            await alice.send(msg.make_time_speed(2))
            a_sync = await self._last_sync(alice)
            b_sync = await self._last_sync(bob)
            self.assertEqual(a_sync["payload"]["speed"], 2)
            self.assertEqual(b_sync["payload"]["speed"], 2)
            self.assertEqual(a_sync["payload"]["player_id"], b_sync["payload"]["player_id"])
            self.assertIsNotNone(a_sync["payload"]["player_id"])

            # Bob disconnects mid-session: the room auto-pauses for Alice.
            await bob.close()
            a_sync = await self._last_sync(alice)
            self.assertEqual(a_sync["payload"]["speed"], 0, "disconnect auto-pauses the room")

            # When Bob rejoins and readies, the room resumes at the stored speed.
            bob2 = await FakeClient.connect(port, "Bob")
            await bob2.send(msg.make_hello("Bob", "t", client_id="BOB-STABLE"))
            await bob2.wait_for_type("WELCOME")
            await bob2.wait_for_type("ROOM_STATE")
            b_sync = await self._last_sync(bob2)
            self.assertEqual(b_sync["payload"]["speed"], 0, "rejoin still gated")
            a_sync = await self._last_sync(alice)
            self.assertEqual(a_sync["payload"]["speed"], 0)

            await bob2.send(msg.make_time_ready(100))
            a_sync = await self._last_sync(alice)
            b_sync = await self._last_sync(bob2)
            self.assertEqual(a_sync["payload"]["speed"], 2, "resumed at stored speed")
            self.assertEqual(b_sync["payload"]["speed"], 2)

            await alice.close()
            await bob2.close()

        self.run_flow(_time_server(flow))

    def test_status_file_includes_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            status_file = os.path.join(directory, "status.json")
            server = MPServer("127.0.0.1", 0, status_file=status_file)

            async def flow(server, port):
                alice = await self._hello(port, "Alice")
                await self._last_sync(alice)
                await alice.send(msg.make_time_speed(2))
                await self._last_sync(alice)
                server._write_status()
                with open(status_file, encoding="utf-8") as handle:
                    payload = json.load(handle)
                clock = payload["rooms"][0].get("clock")
                self.assertIsNotNone(clock)
                self.assertEqual(clock["desired"], 2)
                self.assertEqual(clock["speed"], 0, "gated while not ready: speed forced to 0")
                self.assertTrue(clock["gate"])

                await alice.close()

            self.run_flow(_time_server(flow, server))

    def test_session_clock_state_flags(self):
        async def flow(server, port):
            alice = await self._hello(port, "Alice")
            await self._last_sync(alice)
            self.assertEqual(server.session.min_players, 2)
            self.assertFalse(server.session.clock_gate_open("lobby"))
            self.assertTrue(server.session.clock_snapshot("lobby")["gate"])

            await alice.send(msg.make_time_ready(100))
            sync = await self._last_sync(alice)
            # Solo TIME_READY must NOT open the gate when min_players=2.
            self.assertEqual(sync["payload"]["speed"], 0)
            self.assertFalse(server.session.clock_gate_open("lobby"))
            snapshot = server.session.clock_snapshot("lobby")
            self.assertTrue(snapshot["gate"])
            self.assertEqual(snapshot["ready"], [1000], "Alice is player 1000")

            await alice.close()

        self.run_flow(_time_server(flow))

    def test_lobby_clients_do_not_block_clock_gate(self):
        from server.state.session import Session

        session = Session(min_players=2)

        class _Conn(object):
            pass

        lobby = session.create_player(_Conn(), "LobbyGUI")
        lobby.is_lobby = True
        lobby.room_id = "lobby"
        a = session.create_player(_Conn(), "Alice")
        a.room_id = "lobby"
        a.clock_ready = True
        b = session.create_player(_Conn(), "Bob")
        b.room_id = "lobby"
        b.clock_ready = True
        room = session.get_or_create_room("lobby")
        for player in (lobby, a, b):
            room.members[player.player_id] = player
        self.assertTrue(session.clock_gate_open("lobby"))
        self.assertEqual(
            [p.name for p in session._room_participants("lobby")],
            ["Alice", "Bob"],
        )

    def test_solo_ready_opens_gate_when_min_players_one(self):
        async def flow(server, port):
            alice = await self._hello(port, "Alice")
            await self._last_sync(alice)
            await alice.send(msg.make_time_ready(100))
            sync = await self._last_sync(alice)
            self.assertEqual(sync["payload"]["speed"], 1)
            self.assertTrue(server.session.clock_gate_open("lobby"))
            self.assertFalse(server.session.clock_snapshot("lobby")["gate"])
            await alice.close()

        server = MPServer("127.0.0.1", 0, min_players=1)
        self.run_flow(_time_server(flow, server))

    def test_gate_opens_when_second_player_connects_and_ready(self):
        async def flow(server, port):
            alice = await self._hello(port, "Alice")
            await self._last_sync(alice)
            await alice.send(msg.make_time_ready(100))
            sync = await self._last_sync(alice)
            self.assertEqual(sync["payload"]["speed"], 0, "solo ready keeps gate closed")
            self.assertFalse(server.session.clock_gate_open("lobby"))

            bob = await self._hello(port, "Bob")
            await self._last_sync(bob)
            await self._last_sync(alice)
            self.assertFalse(server.session.clock_gate_open("lobby"), "Bob not ready yet")

            await bob.send(msg.make_time_ready(100))
            a_sync = await self._last_sync(alice)
            b_sync = await self._last_sync(bob)
            self.assertEqual(a_sync["payload"]["speed"], 1)
            self.assertEqual(b_sync["payload"]["speed"], 1)
            self.assertTrue(server.session.clock_gate_open("lobby"))
            self.assertFalse(server.session.clock_snapshot("lobby")["gate"])

            await alice.close()
            await bob.close()

        self.run_flow(_time_server(flow))

    def test_zone_change_re_gates_room_until_everyone_arrives(self):
        async def flow(server, port):
            alice = await self._hello(port, "Alice")
            await self._last_sync(alice)
            bob = await self._hello(port, "Bob")
            await self._last_sync(bob)
            await self._last_sync(alice)

            await alice.send(msg.make_time_ready(100))
            await bob.send(msg.make_time_ready(100))
            a_sync = await self._last_sync(alice)
            b_sync = await self._last_sync(bob)
            self.assertEqual(a_sync["payload"]["speed"], 1, "both ready in zone 100")
            self.assertEqual(b_sync["payload"]["speed"], 1)

            await bob.send(msg.make_time_ready(200))
            a_sync = await self._last_sync(alice)
            b_sync = await self._last_sync(bob)
            self.assertEqual(a_sync["payload"]["speed"], 0, "zone flip re-gates: Alice paused")
            self.assertEqual(b_sync["payload"]["speed"], 0, "only Bob re-readied in new zone")

            await alice.send(msg.make_time_ready(200))
            a_sync = await self._last_sync(alice)
            b_sync = await self._last_sync(bob)
            self.assertEqual(a_sync["payload"]["speed"], 1, "both ready in zone 200: open again")
            self.assertEqual(b_sync["payload"]["speed"], 1)

            await alice.close()
            await bob.close()

        self.run_flow(_time_server(flow))


class TimeClientTickTests(unittest.TestCase):
    class FakeEngine(object):
        def __init__(self):
            self.connected = True
            self.ready_calls = []
            self.speed_calls = []

        def send_time_ready(self, zone_id):
            self.ready_calls.append(zone_id)
            return True

        def send_time_speed(self, speed, ticks=None):
            self.speed_calls.append((speed, ticks))
            return True

    def _client(self):
        client = MultiplayerClient(client_name="Alice")
        client.engine = self.FakeEngine()
        client.time_gate = False
        client.time_ready_sent = True
        client.time_speed = 1
        client._last_clock_tick = time.time()  # settled; no clock-rate gate hop
        return client

    def _zone_state(self, zone_id):
        return mock.patch(
            "simmp_client.connectivity.game_hooks.current_zone_running_state",
            return_value=mock.Mock(running=True, zone_id=zone_id, loading=False, has_clock=True, state="RUNNING"),
        )

    def test_zone_flip_resends_time_ready(self):
        client = self._client()
        client.zone_ready_id = 100
        with self._zone_state(200), mock.patch(
            "simmp_client.connectivity.game_hooks.get_clock_speed", return_value=1
        ):
            client._maybe_sync_clock()
        self.assertEqual(client.engine.ready_calls, [200])
        self.assertEqual(client.zone_ready_id, 200)
        self.assertTrue(client.time_ready_sent)

    def test_same_zone_does_not_resend(self):
        client = self._client()
        client.zone_ready_id = 100
        with self._zone_state(100), mock.patch(
            "simmp_client.connectivity.game_hooks.get_clock_speed", return_value=1
        ):
            client._maybe_sync_clock()
        self.assertEqual(client.engine.ready_calls, [])

    def test_gated_tick_forces_pause_ignoring_echo_window(self):
        # Regression: while a peer is still joining (gate closed) the local
        # game must be re-paused on every tick, even inside an echo window
        # left over from the player's own last speed change.
        client = self._client()
        client.time_gate = True
        client.zone_ready_id = 100
        client._clock_echo_until = time_far_future()
        with self._zone_state(100), mock.patch(
            "simmp_client.connectivity.game_hooks.get_clock_speed", return_value=1
        ), mock.patch(
            "simmp_client.connectivity.game_hooks.set_clock_speed", return_value=0
        ) as setter:
            client._maybe_sync_clock()
        setter.assert_called_once_with(0)

    def test_players_short_true_until_min_players_connected(self):
        client = MultiplayerClient(client_name="Alice")
        client.min_players = 2
        client.session.room_players = {1: {"connected": True}}
        self.assertTrue(client._players_short())
        client.session.room_players = {1: {"connected": True}, 2: {"connected": True}}
        self.assertFalse(client._players_short())
        client.session.room_players = {1: {"connected": True}, 2: {"connected": False}}
        self.assertTrue(client._players_short())
        client.min_players = 1
        self.assertFalse(client._players_short())
        # Lobby GUI seats do not count toward min_players.
        client.min_players = 2
        client.session.room_players = {
            1: {"connected": True},
            2: {"connected": True, "lobby": True},
        }
        self.assertTrue(client._players_short())

    def test_alone_holds_paused_until_peer_connects(self):
        # Regression: the first player to load into a co-op session must not
        # start playing while the server gate is open but no peer has joined.
        client = self._client()
        client.min_players = 2
        client.session.room_players = {1000: {"connected": True}}
        with self._zone_state(100), mock.patch(
            "simmp_client.connectivity.game_hooks.get_clock_speed", return_value=1
        ), mock.patch(
            "simmp_client.connectivity.game_hooks.set_clock_speed", return_value=0
        ) as setter:
            client._maybe_sync_clock()
        setter.assert_called_once_with(0)

    def test_players_short_pauses_every_tick_inside_clock_interval(self):
        # Regression from field logs: clock_interval (1.5s) used to throttle
        # re-pause, so the game could play while waiting for a peer.
        client = self._client()
        client.min_players = 2
        client.session.room_players = {1000: {"connected": True}}
        client._last_clock_tick = time.time() + 999  # inside throttle window
        with self._zone_state(100), mock.patch(
            "simmp_client.connectivity.game_hooks.get_clock_speed", return_value=1
        ), mock.patch(
            "simmp_client.connectivity.game_hooks.set_clock_speed", return_value=0
        ) as setter:
            client._maybe_sync_clock()
            client._maybe_sync_clock()
        self.assertEqual(setter.call_count, 2)
        setter.assert_called_with(0)

    def test_disconnected_zone_running_force_pauses(self):
        client = MultiplayerClient(client_name="Alice")
        client.min_players = 2
        client.engine = mock.Mock(connected=False)
        with self._zone_state(100), mock.patch(
            "simmp_client.connectivity.game_hooks.get_clock_speed", return_value=1
        ), mock.patch(
            "simmp_client.connectivity.game_hooks.set_clock_speed", return_value=0
        ) as setter:
            client._maybe_sync_clock()
        setter.assert_called_once_with(0)

    def test_peer_present_releases_the_hold(self):
        client = self._client()
        client.min_players = 2
        client.session.room_players = {1000: {"connected": True}, 1001: {"connected": True}}
        with self._zone_state(100), mock.patch(
            "simmp_client.connectivity.game_hooks.get_clock_speed", return_value=1
        ), mock.patch(
            "simmp_client.connectivity.game_hooks.set_clock_speed", return_value=1
        ) as setter:
            client._maybe_sync_clock()
        setter.assert_not_called()

    def test_welcome_resets_zone_ready_id(self):
        client = MultiplayerClient(client_name="Alice")
        client.time_ready_sent = True
        client.zone_ready_id = 100
        client.time_gate = False
        client._handle_message(msg.make_welcome(1, "lobby", 1.0))
        self.assertFalse(client.time_ready_sent)
        self.assertIsNone(client.zone_ready_id)
        self.assertTrue(client.time_gate)


class TimeClientHandlerTests(unittest.TestCase):
    def test_time_sync_opens_gate_and_applies_speed(self):
        client = MultiplayerClient(client_name="Alice")
        client.min_players = 1
        with mock.patch("simmp_client.connectivity.game_hooks.set_clock_speed", return_value=1) as setter:
            client._handle_message(msg.make_time_sync(1, ticks=42))
        self.assertFalse(client.time_gate)
        self.assertEqual(client.time_speed, 1)
        setter.assert_called_once_with(1)

    def test_time_sync_holds_pause_while_min_players_short(self):
        # Regression from field logs: server opens the gate for a solo ready
        # player, TIME_SYNC speed=1 arrives, and the first client unpaused
        # while still waiting for the peer (min_players=2).
        client = MultiplayerClient(client_name="Alice")
        client.min_players = 2
        client.session.room_players = {1000: {"connected": True}}
        with mock.patch("simmp_client.connectivity.game_hooks.set_clock_speed", return_value=0) as setter:
            client._handle_message(msg.make_time_sync(1, ticks=42))
            # Coop-hold must also block any later apply of speed>0.
            client._apply_room_speed(1)
        self.assertFalse(client.time_gate)
        self.assertEqual(client.time_speed, 1)
        self.assertTrue(client._coop_hold)
        self.assertGreaterEqual(setter.call_count, 2)
        setter.assert_called_with(0)

    def test_time_sync_closes_gate_and_pauses(self):
        client = MultiplayerClient(client_name="Alice")
        client.time_gate = False
        client.time_speed = 1
        with mock.patch("simmp_client.connectivity.game_hooks.set_clock_speed", return_value=0) as setter:
            client._handle_message(msg.make_time_sync(0))
        self.assertTrue(client.time_gate)
        self.assertEqual(client.time_speed, 0)
        setter.assert_called_once_with(0)

    def test_time_sync_applies_even_inside_echo_window(self):
        # Echo window used to update time_speed without applying the clock —
        # joiners showed "paused" while still moving. Authoritative TIME_SYNC
        # must always change the local clock when it differs.
        client = MultiplayerClient(client_name="Alice")
        client.min_players = 1
        client._clock_echo_until = time_far_future()
        with mock.patch(
            "simmp_client.connectivity.game_hooks.get_clock_speed", return_value=1
        ), mock.patch(
            "simmp_client.connectivity.game_hooks.set_clock_speed", return_value=2
        ) as setter:
            client._handle_message(msg.make_time_sync(2))
        self.assertEqual(client.time_speed, 2)
        self.assertFalse(client.time_gate)
        setter.assert_called_once_with(2)

    def test_gated_time_sync_pauses_even_inside_echo_window(self):
        # Regression: a player who just hit play set an echo window. If a peer
        # is still joining, the gate-closing TIME_SYNC must still pause them
        # immediately - the echo window may never delay a PAUSE.
        client = MultiplayerClient(client_name="Alice")
        client.time_gate = False
        client.time_speed = 1
        client._clock_echo_until = time_far_future()
        with mock.patch("simmp_client.connectivity.game_hooks.set_clock_speed", return_value=0) as setter:
            client._handle_message(msg.make_time_sync(0))
        self.assertTrue(client.time_gate)
        self.assertEqual(client.time_speed, 0)
        setter.assert_called_once_with(0)

    def test_clock_apply_disabled_keeps_state_but_no_apply(self):
        client = MultiplayerClient(client_name="Alice")
        client.set_clock_apply_enabled(False)
        with mock.patch("simmp_client.connectivity.game_hooks.set_clock_speed") as setter:
            client._handle_message(msg.make_time_sync(2))
        self.assertEqual(client.time_speed, 2)
        setter.assert_not_called()

    def test_welcome_resets_ready_flag(self):
        client = MultiplayerClient(client_name="Alice")
        client.time_ready_sent = True
        client.time_gate = False
        client._handle_message(msg.make_welcome(1, "lobby", 1.0))
        self.assertFalse(client.time_ready_sent)
        self.assertTrue(client.time_gate)


def time_far_future():
    import time

    return time.time() + 999999


async def _time_server(flow, server=None):
    if server is None:
        server = MPServer("127.0.0.1", 0)
    await server.start()
    try:
        await flow(server, server.port)
    finally:
        await server.stop()


if __name__ == "__main__":
    unittest.main()