import asyncio
import time
import unittest

from simmp_client.connectivity import MultiplayerClient
from server.networking.server import MPServer
from tests.test_client_engine import _wait_until


class ReconnectOwnershipTests(unittest.TestCase):
    def run_flow(self, coro):
        asyncio.run(coro)

    @staticmethod
    async def _connected(client):
        return await _wait_until(
            lambda: (client.process_incoming() or True) and client.session.player_id is not None,
            timeout=5.0,
        )

    def test_server_ghost_hold_restores_state_on_reconnect(self):
        async def flow():
            server = MPServer("127.0.0.1", 0, interaction_cooldown=5.0, ghost_ownership_ttl=60.0)
            await server.start()
            bob = MultiplayerClient(client_name="Bob", presence_interval=60.0)
            alice = MultiplayerClient(client_name="Alice", client_id="ALICE-1", presence_interval=60.0)
            try:
                bob.connect("127.0.0.1", server.port)
                alice.connect("127.0.0.1", server.port)
                self.assertTrue(await self._connected(alice))
                self.assertTrue(await self._connected(bob))
                alice_pid = alice.session.player_id

                alice.claim_object("sofa")
                alice.propose_interaction("sofa", "Read")
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.world.get("sofa") is not None
                    and alice.session.world.get("sofa").owner == alice_pid
                    and alice.session.interactions.get("sofa") is not None,
                    timeout=5.0,
                ), "Alice never acquired sofa ownership + interaction")
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and bob.session.world.get("sofa") is not None
                    and bob.session.interactions.get("sofa") is not None,
                    timeout=5.0,
                ), "Bob never mirrored the state")

                # Drop + reconnect with the same client_id. The server keeps
                # the ghost's ownership, and the resume snapshots show it.
                self.assertTrue(alice.reconnect())
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.player_id == alice_pid
                    and alice.session.world.get("sofa") is not None
                    and alice.session.world.get("sofa").owner == alice_pid
                    and alice.session.interactions.get("sofa") is not None,
                    timeout=5.0,
                ), "ownership/interaction not restored after reconnect")
                bob.process_incoming()
                self.assertEqual(
                    bob.session.interactions.cooldown_until("sofa"),
                    0,
                    "reconnect must not have released the interaction",
                )
                self.assertIsNotNone(
                    bob.session.interactions.get("sofa"),
                    "Bob's interaction mirror lost the entry during the ghost window",
                )
            finally:
                alice.disconnect()
                bob.disconnect()
                await server.stop()

        self.run_flow(flow())

    def test_client_reclaims_when_server_state_is_lost(self):
        async def flow():
            first = MPServer("127.0.0.1", 0, interaction_cooldown=5.0, ghost_ownership_ttl=0.1, reap_interval=0.05)
            await first.start()
            alice = MultiplayerClient(client_name="Alice", client_id="ALICE-1", presence_interval=60.0)
            try:
                alice.connect("127.0.0.1", first.port)
                self.assertTrue(await self._connected(alice))
                alice_pid = alice.session.player_id
                alice.claim_object("sofa")
                alice.propose_interaction("sofa", "Read")
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.world.get("sofa") is not None
                    and alice.session.interactions.get("sofa") is not None,
                    timeout=5.0,
                ), "Alice never acquired state on the first server")
            finally:
                alice.disconnect()
                await first.stop()

            # A brand-new server replaced the old one: no ghost to resume, so
            # the client's captured 'owned/held' state must be re-claimed.
            second = MPServer("127.0.0.1", 0, interaction_cooldown=5.0)
            await second.start()
            try:
                alice._capture_dropped_state()
                self.assertTrue(alice._reclaim_pending)
                alice.connect("127.0.0.1", second.port)
                self.assertTrue(await self._connected(alice))
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.player_id is not None
                    and alice.session.world.get("sofa") is not None
                    and alice.session.world.get("sofa").owner == alice.session.player_id
                    and alice.session.interactions.get("sofa") is not None,
                    timeout=5.0,
                ), "client fallback reclaim never re-established the state")
                self.assertFalse(alice._reclaim_pending)
            finally:
                alice.disconnect()
                await second.stop()

        self.run_flow(flow())

    def test_auto_reconnect_after_server_restart_with_backoff_and_reclaim(self):
        async def flow():
            first = MPServer("127.0.0.1", 0, interaction_cooldown=5.0)
            await first.start()
            alice = MultiplayerClient(client_name="Alice", client_id="ALICE-1", presence_interval=60.0)
            try:
                alice.connect("127.0.0.1", first.port)
                self.assertTrue(await self._connected(alice))
                alice.claim_object("sofa")
                alice.propose_interaction("sofa", "Read")
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.world.get("sofa") is not None
                    and alice.session.world.get("sofa").owner == alice.session.player_id
                    and alice.session.interactions.get("sofa") is not None,
                    timeout=5.0,
                ), "Alice never acquired state on the first server")
                alice.engine._connect_timeout = 0.4
                alice.reconnect_backoff_min = 0.15
                alice.reconnect_backoff_max = 30.0
            finally:
                await first.stop()

            # The drop needs the engine thread to notice the EOF, then the
            # alarm marks the session down and captures what we held.
            await asyncio.sleep(0.3)
            alice._on_alarm()
            self.assertFalse(alice.session.connected)
            self.assertTrue(alice._reclaim_pending, "drop capture did not run")

            # With the server still down, driving the alarm grows the backoff.
            attempts_seen = set()
            for _ in range(15):
                alice._on_alarm()
                attempts_seen.add(alice._reconnect_attempt)
                await asyncio.sleep(0.1)
            self.assertGreaterEqual(
                alice._reconnect_attempt, 2,
                "auto-reconnect should keep backing off while the server is down",
            )
            self.assertGreater(
                alice._next_reconnect_at, time.time() - 0.1,
                "a backoff deadline should be scheduled after a failed attempt",
            )

            # A replacement server on the same port appears; the client keeps
            # retrying and, once re-connected, the fallback reclaim restores
            # the sofa ownership + interaction (identity was lost with the
            # old server, so this is a fresh player_id).
            second = MPServer("127.0.0.1", first.port)
            await second.start()
            try:
                def connected_and_reclaimed():
                    alice.process_incoming()
                    alice._on_alarm()
                    return (
                        alice.session.connected
                        and alice.session.player_id is not None
                        and alice.session.world.get("sofa") is not None
                        and alice.session.world.get("sofa").owner == alice.session.player_id
                        and alice.session.interactions.get("sofa") is not None
                        and not alice._reclaim_pending
                    )

                self.assertTrue(await _wait_until(connected_and_reclaimed, timeout=15.0),
                                "auto-reconnect never re-established the state")
                self.assertEqual(alice._reconnect_attempt, 0,
                                 "backoff counter should reset after a successful reconnect")
            finally:
                alice.disconnect()
                await second.stop()

        self.run_flow(flow())


if __name__ == "__main__":
    unittest.main()