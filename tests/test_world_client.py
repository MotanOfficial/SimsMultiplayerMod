import asyncio
import time
import unittest
from unittest import mock

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


class WorldClientTests(unittest.TestCase):
    def run_flow(self, coro):
        asyncio.run(coro)

    @staticmethod
    async def _connected(client):
        return await _wait_until(
            lambda: (client.process_incoming() or True) and client.session.player_id is not None,
            timeout=5.0,
        )

    def test_claim_delta_and_mirror(self):
        async def flow(server, port):
            alice = MultiplayerClient(client_name="Alice")
            bob = MultiplayerClient(client_name="Bob")
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                self.assertTrue(await self._connected(alice))
                self.assertTrue(await self._connected(bob))

                alice_pid = alice.session.player_id

                # Alice claims the sofa; her OWNERSHIP_ACK lands in the mirror.
                self.assertTrue(alice.claim_object("sofa"))
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.world.get("sofa") is not None
                    and alice.session.world.get("sofa").owner == alice_pid,
                    timeout=5.0,
                ), "Alice never reflected her own claim")

                # Bob reflects the broadcast OBJECT_OWNERSHIP.
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and bob.session.world.get("sofa") is not None
                    and bob.session.world.get("sofa").owner == alice_pid,
                    timeout=5.0,
                ), "Bob never saw the ownership broadcast")

                # Alice pushes a position delta; Bob's mirror merges it.
                self.assertTrue(alice.update_object("sofa", {"x": 1.0, "y": 2.0, "z": 3.0}))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and bob.session.world.get("sofa").fields.get("x") == 1.0,
                    timeout=5.0,
                ), "Bob never merged the WORLD_DELTA")

                # Bob's world has exactly the sofa at seq >= 1.
                self.assertEqual(bob.session.world.count(), 1)
                self.assertGreaterEqual(bob.session.world.last_seq, 1)
            finally:
                alice.disconnect()
                bob.disconnect()

        self.run_flow(_with_server(flow))

    def test_second_claim_locked_and_unclaimed_update_rejected(self):
        async def flow(server, port):
            alice = MultiplayerClient(client_name="Alice")
            bob_log = []
            bob = MultiplayerClient(client_name="Bob", notify=bob_log.append)
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                self.assertTrue(await self._connected(alice))
                self.assertTrue(await self._connected(bob))

                self.assertTrue(alice.claim_object("sofa"))
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.world.get("sofa") is not None,
                    timeout=5.0,
                ))

                # Bob cannot claim a locked object: server replies ERROR.
                self.assertTrue(bob.claim_object("sofa"))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and any("OBJECT_LOCKED" in line for line in bob_log),
                    timeout=5.0,
                ), "Bob never saw the OBJECT_LOCKED error")

                # The deny bookkeeping clears Bob's in-flight guard and backs
                # him off so he does not ping the server every world tick.
                self.assertNotIn("sofa", bob._claimed_in_flight)
                self.assertGreater(bob._claim_denied_until.get("sofa", 0), time.time())

                # Once Alice releases, the owner-null broadcast re-enables Bob
                # to claim it on a later world tick.
                self.assertTrue(alice.release_object("sofa"))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and bob._claim_denied_until.get("sofa", None) is None,
                    timeout=5.0,
                ), "Bob's claim backoff was never cleared on release")

                # Updating an object that was never claimed is rejected too.
                self.assertTrue(bob.update_object("table", {"x": 0.0}))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and any("OBJECT_NOT_FOUND" in line for line in bob_log),
                    timeout=5.0,
                ), "Bob never saw the OBJECT_NOT_FOUND error")
            finally:
                alice.disconnect()
                bob.disconnect()

        self.run_flow(_with_server(flow))

    def test_auto_claim_and_push_with_sampler(self):
        """The world tick claims unowned sampled keys, then pushes deltas."""
        async def flow(server, port):
            alice_log = []
            alice = MultiplayerClient(client_name="Alice", notify=alice_log.append)
            bob = MultiplayerClient(client_name="Bob")
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                self.assertTrue(await self._connected(alice))
                self.assertTrue(await self._connected(bob))

                alice_pid = alice.session.player_id
                alice_log[:] = []

                def fake_sampler():
                    return [{"key": "sim:42", "fields": {"x": 1.0, "y": 0.0, "z": 2.0}}]

                alice.set_world_sampler(fake_sampler)
                alice.world_sync = True
                alice.world_interval = 0.0

                # First tick: the unowned key gets auto-claimed.
                alice._maybe_send_world_update()
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.world.get("sim:42") is not None
                    and alice.session.world.get("sim:42").owner == alice_pid,
                    timeout=5.0,
                ), "Alice never reflected her auto-claim")

                # Exactly one claim request reaches the server; the ack clears
                # the in-flight guard, so the mirror check alone prevents
                # re-claiming on later ticks.
                self.assertEqual(
                    sum("Requested ownership" in line for line in alice_log), 1
                )

                # Second tick: ownership held, so fields are pushed to Bob.
                alice._maybe_send_world_update()
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and bob.session.world.get("sim:42") is not None
                    and bob.session.world.get("sim:42").fields.get("x") == 1.0,
                    timeout=5.0,
                ), "Bob never merged Alice's auto-synced world delta")

                # A further tick still does not re-claim the owned key.
                alice._maybe_send_world_update()
                self.assertEqual(
                    sum("Requested ownership" in line for line in alice_log), 1
                )
            finally:
                alice.disconnect()
                bob.disconnect()

        self.run_flow(_with_server(flow))

    def test_lot_objects_do_not_auto_claim_on_first_sight(self):
        """Furniture must not be claimed by whoever loads first."""
        client = MultiplayerClient(client_name="Alice")
        client.engine = type("E", (), {"connected": True, "send_object_claim": lambda *a, **k: True, "send_object_update": lambda *a, **k: True, "send_object_gone": lambda *a, **k: True})()
        client.session.player_id = 1000
        client.world_sync = True
        client.world_interval = 0.0
        samples = [{"key": "obj:9@1_2_3", "fields": {"x": 1.0}}]
        client.set_world_sampler(lambda: samples)
        with mock.patch("simmp_client.connectivity.game_hooks.current_zone_running_state") as zone:
            zone.return_value = type("Z", (), {"running": True, "zone_id": 7})()
            client._maybe_send_world_update()
        self.assertEqual(client._claimed_in_flight, set())
        self.assertIn("obj:9@1_2_3", client._last_obj_fields)
        # A local edit (field change) should claim.
        samples[0] = {"key": "obj:9@1_2_3", "fields": {"x": 2.0}}
        client._last_world_sent = 0.0
        with mock.patch("simmp_client.connectivity.game_hooks.current_zone_running_state") as zone:
            zone.return_value = type("Z", (), {"running": True, "zone_id": 7})()
            client._maybe_send_world_update()
        self.assertIn("obj:9@1_2_3", client._claimed_in_flight)


    def test_sim_exclusive_ownership_host_drives(self):
        """Household sims are single-owner: the host drives, peers mirror."""
        async def flow(server, port):
            alice_log = []
            alice = MultiplayerClient(client_name="Alice", notify=alice_log.append)
            bob_log = []
            bob = MultiplayerClient(client_name="Bob", notify=bob_log.append)
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                self.assertTrue(await self._connected(alice))
                self.assertTrue(await self._connected(bob))
                alice_pid = alice.session.player_id
                bob_pid = bob.session.player_id

                # Alice claims sim:42 first (host drives it).
                self.assertTrue(alice.claim_object("sim:42"))
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.world.get("sim:42") is not None
                    and alice.session.world.get("sim:42").owner == alice_pid,
                    timeout=5.0,
                ), "Alice never became owner of sim:42")

                # Bob is locked out of the sim (mirrors instead of driving).
                self.assertTrue(bob.claim_object("sim:42"))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and any("OBJECT_LOCKED" in line for line in bob_log),
                    timeout=5.0,
                ), "Bob should be locked out of a host-owned sim")
                self.assertEqual(
                    bob.session.world.get("sim:42").owner,
                    alice_pid,
                    "Bob must see the host as the sim's single owner",
                )
                self.assertFalse(
                    bob.session.world.get("sim:42").is_owned_by(bob_pid),
                    "Bob must not be (co-)owner of the host's sim",
                )

                # A lost sim claim backs off permanently: Bob must not ping
                # the room every world tick (re-enabled only by owner=null).
                self.assertEqual(
                    bob._claim_denied_until.get("sim:42"),
                    float("inf"),
                    "Bob's denied sim claim must back off permanently",
                )
                bob_log[:] = []
                bob.world_sync = True
                bob.world_interval = 0.0
                bob.set_world_sampler(lambda: [{"key": "sim:42", "fields": {}, "rev": 0}])
                bob._maybe_send_world_update()
                self.assertFalse(
                    any("Requested ownership of object 'sim:42'" in line for line in bob_log),
                    "Bob must not re-claim a host-owned sim",
                )

                # Bob cannot push deltas on a sim he does not own.
                bob_log[:] = []
                self.assertTrue(bob.update_object("sim:42", {"x": 9.0}))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and any("OBJECT_LOCKED" in line for line in bob_log),
                    timeout=5.0,
                ), "Bob should be locked pushing a delta on the host's sim")

                # Releasing hands the sim over so Bob can drive it.
                self.assertTrue(alice.release_object("sim:42"))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and bob.session.world.get("sim:42") is not None
                    and bob.session.world.get("sim:42").owner is None,
                    timeout=5.0,
                ), "Alice's release never reached Bob")
                self.assertTrue(bob.claim_object("sim:42"))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and bob.session.world.get("sim:42").owner == bob_pid,
                    timeout=5.0,
                ), "Bob should drive the sim after release")
            finally:
                alice.disconnect()
                bob.disconnect()

        self.run_flow(_with_server(flow))

    def test_remote_world_entries_reach_applier(self):
        """The world applier gets remote-owned entries, never our own."""
        async def flow(server, port):
            alice_calls = []
            bob_calls = []
            alice = MultiplayerClient(client_name="Alice")
            bob = MultiplayerClient(client_name="Bob", )
            alice.set_world_applier(lambda entries: alice_calls.append(list(entries)))
            bob.set_world_applier(lambda entries: bob_calls.append(list(entries)))
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                self.assertTrue(await self._connected(alice))
                self.assertTrue(await self._connected(bob))

                alice_pid = alice.session.player_id

                self.assertTrue(alice.claim_object("sim:77"))
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.world.get("sim:77") is not None
                    and alice.session.world.get("sim:77").owner == alice_pid,
                    timeout=5.0,
                ))
                self.assertTrue(alice.update_object("sim:77", {"x": 5.0, "y": 6.0, "z": 7.0}))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and any(
                        any(entry["key"] == "sim:77" and entry["fields"].get("x") == 5.0
                            for entry in call)
                        for call in bob_calls
                    ),
                    timeout=5.0,
                ), "Bob's applier never saw the remote sim entry")

                saw = next(call for call in bob_calls
                           if any(entry["key"] == "sim:77" for entry in call))
                entry = next(e for e in saw if e["key"] == "sim:77")
                self.assertEqual(entry["fields"]["x"], 5.0)

                self.assertFalse(
                    any(any(e["key"] == "sim:77" for e in call) for call in alice_calls)
                )
            finally:
                alice.disconnect()
                bob.disconnect()

        self.run_flow(_with_server(flow))

    def test_autonomy_reconcile_receives_remote_owner_keys(self):
        """The autonomy reconciler is called with correct remote-owner keys."""
        async def flow(server, port):
            reconcile_calls = []
            alice = MultiplayerClient(client_name="Alice")
            bob = MultiplayerClient(client_name="Bob")
            bob.set_autonomy_reconciler(
                lambda keys, pid, zone: reconcile_calls.append(
                    (frozenset(keys), pid, zone)
                )
            )
            try:
                self.assertTrue(alice.connect("127.0.0.1", port))
                self.assertTrue(bob.connect("127.0.0.1", port))
                self.assertTrue(await self._connected(alice))
                self.assertTrue(await self._connected(bob))

                alice_pid = alice.session.player_id

                self.assertTrue(alice.claim_object("sim:55"))
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.world.get("sim:55") is not None
                    and alice.session.world.get("sim:55").owner == alice_pid,
                    timeout=5.0,
                ))
                self.assertTrue(alice.update_object("sim:55", {"x": 1.0}))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and any(call[0] == frozenset({"sim:55"}) for call in reconcile_calls),
                    timeout=5.0,
                ), "Bob's reconciler never saw sim:55 in remote_owner_keys")

                reconcile_calls.clear()
                self.assertTrue(alice.release_object("sim:55"))
                self.assertTrue(await _wait_until(
                    lambda: (bob.process_incoming() or True)
                    and any(call[0] == frozenset() for call in reconcile_calls),
                    timeout=5.0,
                ), "Bob's reconciler never cleared after ownership release")

                reconcile_calls.clear()
                bob.autonomy_suppression = False
                self.assertTrue(alice.claim_object("sim:55"))
                self.assertTrue(await _wait_until(
                    lambda: (alice.process_incoming() or True)
                    and alice.session.world.get("sim:55") is not None,
                    timeout=5.0,
                ))
                self.assertTrue(alice.update_object("sim:55", {"x": 2.0}))
                for _ in range(10):
                    bob.process_incoming()
                    time.sleep(0.05)
                self.assertFalse(reconcile_calls)
            finally:
                bob.autonomy_suppression = True
                alice.disconnect()
                bob.disconnect()

        self.run_flow(_with_server(flow))


if __name__ == "__main__":
    unittest.main()