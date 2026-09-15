import asyncio
import time
import unittest

from simmp_client.connectivity import MultiplayerClient
from server.networking.server import MPServer
from tests.test_client_engine import _wait_until


async def _with_server(callback, **kwargs):
    server = MPServer("127.0.0.1", 0, **kwargs)
    await server.start()
    try:
        await callback(server, server.port)
    finally:
        await server.stop()


class InteractionClientTests(unittest.TestCase):
    def run_flow(self, coro):
        asyncio.run(coro)

    @staticmethod
    async def _connected(client):
        return await _wait_until(
            lambda: (client.process_incoming() or True) and client.session.player_id is not None,
            timeout=5.0,
        )

    @staticmethod
    def _mirror_entry(client, key):
        return client.session.interactions.get(key)

    def test_propose_busy_end_and_cooldown(self):
        async def flow(server, port):
            alice = MultiplayerClient(client_name="Alice")
            bob_log = []
            bob = MultiplayerClient(client_name="Bob", notify=bob_log.append)
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                self.assertTrue(await self._connected(alice))
                self.assertTrue(await self._connected(bob))

                alice_pid = alice.session.player_id

                # Alice proposes an interaction; her echo marks the mirror.
                self.assertTrue(alice.propose_interaction("sofa", "Read"))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and self._mirror_entry(bob, "sofa") is not None
                    and self._mirror_entry(bob, "sofa")["player_id"] == alice_pid,
                    timeout=5.0,
                ), "Bob never saw the interaction start")
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and self._mirror_entry(alice, "sofa") is not None
                    and self._mirror_entry(alice, "sofa")["player_id"] == alice_pid,
                    timeout=5.0,
                ), "Alice never saw her own echoed start")

                # Bob's proposal on the busy key is denied (with backoff).
                self.assertTrue(bob.propose_interaction("sofa", "Sit"))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and any("INTERACTION_BUSY" in line for line in bob_log),
                    timeout=5.0,
                ), "Bob never saw the busy error")

                # Alice ends; both mirrors clear and record the cooldown.
                self.assertTrue(alice.end_interaction("sofa"))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and self._mirror_entry(bob, "sofa") is None
                    and bob.session.interactions.cooldown_until("sofa") > time.time() - 1,
                    timeout=5.0,
                ), "Bob never saw the release")
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and self._mirror_entry(alice, "sofa") is None,
                    timeout=5.0,
                ), "Alice never saw her own release")
            finally:
                alice.disconnect()
                bob.disconnect()

        self.run_flow(_with_server(flow, interaction_cooldown=0.5))

    def test_auto_interaction_sampler_reconciles(self):
        async def flow(server, port):
            alice = MultiplayerClient(client_name="Alice", presence_interval=60.0)
            bob = MultiplayerClient(client_name="Bob", presence_interval=60.0)
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                self.assertTrue(await self._connected(alice))
                self.assertTrue(await self._connected(bob))

                # A game hook reports that Alice's sim just started reading.
                state = {
                    "key": "sofa",
                    "interaction": "Read",
                    "affordance": "Read",
                    "affordance_id": 9001,
                    "target": "sim:7",
                }
                alice.set_interaction_sampler(lambda: [state])
                alice.interaction_interval = 0.1

                # The tick (driven as if by the repeating real-time alarm)
                # proposes it; Alice's echo and Bob's broadcast both land,
                # carrying the affordance identity + aim.
                alice._last_interaction_tick = 0
                alice._maybe_send_interactions()
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.interactions.get("sofa") is not None,
                    timeout=5.0,
                ), "Alice never proposed the sampled interaction")
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and self._mirror_entry(bob, "sofa") is not None,
                    timeout=5.0,
                ), "Bob never saw the sampled interaction")
                bob_entry = self._mirror_entry(bob, "sofa")
                self.assertEqual(bob_entry["affordance"], "Read")
                self.assertEqual(bob_entry["affordance_id"], 9001)
                self.assertEqual(bob_entry["target"], "sim:7")

                # Alice's sim stops interacting; the next tick ends it.
                state.clear()
                alice._last_interaction_tick = 0
                alice._maybe_send_interactions()
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.interactions.get("sofa") is None,
                    timeout=5.0,
                ), "Alice never ended the finished interaction")
            finally:
                alice.disconnect()
                bob.disconnect()

        self.run_flow(_with_server(flow, interaction_cooldown=0.1))


def test_interaction_applier_receives_only_remote_entries(self):
        async def flow(server, port):
            alice = MultiplayerClient(client_name="Alice", presence_interval=60.0)
            bob = MultiplayerClient(client_name="Bob", presence_interval=60.0)
            alice_applied = []
            bob_applied = []
            alice.set_interaction_applier(alice_applied.append)
            bob.set_interaction_applier(bob_applied.append)
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                self.assertTrue(await self._connected(alice))
                self.assertTrue(await self._connected(bob))

                # Alice proposes with full execution hints.
                self.assertTrue(alice.propose_interaction(
                    "sim:42",
                    "Read",
                    affordance="Read",
                    affordance_id=9001,
                    target="sim:7",
                ))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and self._mirror_entry(bob, "sim:42") is not None
                    and len(bob_applied) > 0,
                    timeout=5.0,
                ), "Bob's applier never saw Alice's interaction")

                # Bob's applier got the entry, but Alice's applier never saw
                # her own interaction (her local game already runs it).
                bob_entry = bob_applied[-1]
                self.assertEqual(bob_entry["key"], "sim:42")
                self.assertEqual(bob_entry["affordance"], "Read")
                self.assertEqual(bob_entry["affordance_id"], 9001)
                self.assertEqual(bob_entry["target"], "sim:7")
                self.assertEqual(alice_applied, [])
            finally:
                alice.disconnect()
                bob.disconnect()

        self.run_flow(_with_server(flow, interaction_cooldown=0.2))


if __name__ == "__main__":
    unittest.main()