import asyncio
import time
import unittest

from simmp import messages as msg
from simmp_client.connectivity import MultiplayerClient
from server.networking.server import MPServer
from tests.test_client_engine import _wait_until


async def _with_server(callback):
    server = MPServer("127.0.0.1", 0)
    await server.start()
    try:
        await callback(server, server.port)
    finally:
        await server.stop()


class TravelClientTests(unittest.TestCase):
    def run_flow(self, coro):
        asyncio.run(coro)

    def test_travel_request_invite_autoaccept_begin_ready_complete(self):
        async def flow(server, port):
            alice_lines = []
            bob_lines = []
            alice = MultiplayerClient(client_name="Alice", notify=alice_lines.append)
            bob = MultiplayerClient(client_name="Bob", notify=bob_lines.append)
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True) and alice.session.player_id is not None,
                    timeout=5.0,
                ))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True) and bob.session.player_id is not None,
                    timeout=5.0,
                ))

                self.assertTrue(alice.request_travel(4242))

                # Bob auto-accepts (auto_accept_travel default True) and both
                # clients reach the "traveling" state when TRAVEL_BEGIN lands.
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True) and bob.session.travel_state == "invited",
                    timeout=5.0,
                ), "Bob never saw the invite")
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True) and alice.session.travel_state == "traveling",
                    timeout=5.0,
                ), "Alice never saw TRAVEL_BEGIN")
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True) and bob.session.travel_state == "traveling",
                    timeout=5.0,
                ), "Bob never saw TRAVEL_BEGIN")
                self.assertEqual(bob.session.travel_zone_id, 4242)

                # Simulate each client arriving at the zone (in the real game
                # the presence poller sends this when the zone is running).
                self.assertTrue(alice.confirm_travel_ready())
                self.assertTrue(bob.confirm_travel_ready())

                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True) and alice.session.travel_state == "idle"
                    and alice.session.travel_request_id is None,
                    timeout=5.0,
                ), "Alice never saw TRAVEL_COMPLETE")
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True) and bob.session.travel_state == "idle"
                    and bob.session.travel_zone_id is None,
                    timeout=5.0,
                ), "Bob never saw TRAVEL_COMPLETE")

                self.assertTrue(any("COMPLETE" in line for line in bob_lines),
                                "no COMPLETE logged on Bob's side")
            finally:
                alice.disconnect()
                bob.disconnect()

        self.run_flow(_with_server(flow))

    def test_travel_decline_via_autoaccept_off(self):
        async def flow(server, port):
            alice_lines = []
            bob_lines = []
            alice = MultiplayerClient(client_name="Alice", notify=alice_lines.append)
            bob = MultiplayerClient(client_name="Bob", notify=bob_lines.append)
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                ok = await _wait_until(
                    lambda: (alice.process_incoming() or True) and alice.session.player_id is not None
                    and (bob.process_incoming() or True) and bob.session.player_id is not None,
                    timeout=8.0,
                )
                self.assertTrue(ok)
                bob.auto_accept_travel = False

                self.assertTrue(alice.request_travel(4242))
                # Bob must actually process the invite: the client declines it
                # inline and the state returns to idle, so watch for the log.
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and any("declined" in line.lower() for line in bob_lines),
                    timeout=8.0,
                ), "Bob never processed the travel invite")
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and any("ABORTED" in line for line in alice_lines),
                    timeout=5.0,
                ), "Alice did not see the abort")

                self.assertFalse(any("BEGIN" in line for line in bob_lines))
            finally:
                alice.disconnect()
                bob.disconnect()

        self.run_flow(_with_server(flow))

    def test_travel_controller_deferral_responds_later_with_abort(self):
        async def flow(server, port):
            alice_lines = []
            bob_lines = []
            alice = MultiplayerClient(client_name="Alice", notify=alice_lines.append)
            bob = MultiplayerClient(client_name="Bob", notify=bob_lines.append)
            decisions = []
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                ok = await _wait_until(
                    lambda: (alice.process_incoming() or True) and alice.session.player_id is not None
                    and (bob.process_incoming() or True) and bob.session.player_id is not None,
                    timeout=8.0,
                )
                self.assertTrue(ok)
                bob.auto_accept_travel = False

                def controller(request_id, zone_id):
                    decisions.append((request_id, zone_id))
                    return None

                bob.travel_controller = controller

                self.assertTrue(alice.request_travel(4242))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True) and len(decisions) > 0,
                    timeout=8.0,
                ), "travel controller never consulted")
                self.assertEqual(bob.session.travel_state, "invited")
                self.assertFalse(
                    any("declined" in line.lower() for line in bob_lines),
                    "deferred decision must not auto-decline",
                )

                # The dialog's respond callback says no -> abort round-trip.
                bob.respond_travel(bob.session.travel_request_id, False)
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True) and (bob.process_incoming() or True)
                    and "ABORTED" in "\n".join(alice_lines)
                    and bob.session.travel_state == "idle",
                    timeout=5.0,
                ), "abort round-trip never completed")
                self.assertEqual(bob.session.travel_state, "idle")
            finally:
                alice.disconnect()
                bob.disconnect()

        self.run_flow(_with_server(flow))

    def test_clock_sync_mirrors_into_session(self):
        async def flow(server, port):
            received = []
            client = MultiplayerClient(client_name="Otto", notify=received.append)
            eve = None
            try:
                self.assertTrue(client.connect("127.0.0.1", port))
                self.assertTrue(await _wait_until(
                    lambda: (client.process_incoming() or True) and client.session.player_id is not None,
                    timeout=5.0,
                ))

                eve = await _raw_connect(port, "Eve")
                await eve.send(msg.make_clock_sync(555, 250000, 999.5, 3))
                self.assertTrue(await _wait_until(
                    lambda: (client.process_incoming() or True) and "absolute_ticks" in client.session.clock_sync,
                    timeout=5.0,
                ))
                self.assertEqual(client.session.clock_sync["absolute_ticks"], 250000)
                self.assertEqual(client.session.clock_sync["zone_id"], 555)
            finally:
                if eve is not None:
                    await eve.close()
                client.disconnect()

        self.run_flow(_with_server(flow))


async def _raw_connect(port, name):
    from tests.test_server import FakeClient

    eve = await FakeClient.connect(port, name)
    await eve.send(msg.make_hello(name, "t"))
    await eve.wait_for_type("WELCOME")
    await eve.wait_for_type("ROOM_STATE")
    return eve


if __name__ == "__main__":
    unittest.main()