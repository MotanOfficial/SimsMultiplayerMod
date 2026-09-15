"""Zone-scoped world/ownership/interaction tests.

Split-zone behavior: world objects, claims and interactions are partitioned
per (room, zone). Players see and control only the zone they are currently in;
a zone change (TIME_READY in a new zone) auto-releases the departed player's
holdings in the old zone. Players without a known zone receive everything
(join bootstrap, gated until ready).
"""

import asyncio
import time
import unittest

from simmp import messages as msg
from server.networking.server import MPServer

from tests.test_server import FakeClient


class ZoneScopingTests(unittest.TestCase):
    async def _join_hello(self, server_port, name):
        client = await FakeClient.connect(server_port, name)
        await client.send(msg.make_hello(name, "t"))
        player_id = (await client.wait_for_type("WELCOME"))["payload"]["player_id"]
        await client.wait_for_type("ROOM_STATE")
        return client, player_id

    async def _join_zone(self, server_port, name, zone_id):
        client, player_id = await self._join_hello(server_port, name)
        await client.wait_for_type("WORLD_STATE")
        await client.wait_for_type("INTERACTION_STATE")
        await client.send(msg.make_time_ready(zone_id))
        world = await self._world_state_for_zone(client, zone_id)
        await client.wait_for_type("INTERACTION_STATE")
        return client, player_id, world

    async def _world_state_for_zone(self, client, zone_id, timeout=5.0):
        deadline = time.monotonic() + timeout
        while True:
            if time.monotonic() > deadline:
                self.fail("no WORLD_STATE for zone %s" % zone_id)
            frame = await client.wait_for_type("WORLD_STATE", timeout=2)
            if frame["payload"].get("zone_id") == zone_id:
                return frame

    async def _gate_open(self, client, timeout=5.0):
        deadline = time.monotonic() + timeout
        while True:
            if time.monotonic() > deadline:
                self.fail("room gate never opened")
            sync = await client.wait_for_type("TIME_SYNC", timeout=2)
            if not sync["payload"].get("gate"):
                return sync

    async def _assert_no_message(self, client, message_type, window=0.25):
        before = len(client.messages)
        await asyncio.sleep(window)
        for message in client.messages[before:]:
            if message["type"] == message_type:
                self.fail("unexpected %s delivered to %s" % (message_type, client.name))

    def test_isolated_zones_share_no_world(self):
        async def flow():
            server = MPServer("127.0.0.1", 0, interaction_cooldown=0.2)
            await server.start()
            try:
                alice, alice_pid, _ = await self._join_zone(server.port, "Alice", 100)
                bob, bob_pid, _ = await self._join_zone(server.port, "Bob", 200)
                await alice.wait_for_type("PLAYER_JOINED")

                # Alice claims "sofa" in zone 100; nobody else is in 100, so
                # Bob (zone 200) must NOT receive the ownership broadcast.
                await alice.send(msg.make_object_claim("sofa", zone_id=100))
                ack = await alice.wait_for_type("OBJECT_CLAIM_ACK")
                self.assertEqual(ack["payload"]["owner"], alice_pid)
                await self._assert_no_message(bob, "OBJECT_OWNERSHIP")

                # The same key in Bob's zone 200 is a separate partition: claim succeeds.
                await bob.send(msg.make_object_claim("sofa", zone_id=200))
                b_ack = await bob.wait_for_type("OBJECT_CLAIM_ACK")
                self.assertEqual(b_ack["payload"]["owner"], bob_pid)

                # Alice's zone-100 delta never crosses into zone 200.
                await alice.send(
                    msg.make_object_update([{"key": "sofa", "fields": {"x": 1.0}, "rev": 1}], zone_id=100)
                )
                await asyncio.sleep(0.3)
                self.assertFalse(
                    any(m["type"] == "WORLD_DELTA" for m in alice.messages)
                )
                self.assertFalse(any(m["type"] == "WORLD_DELTA" for m in bob.messages))

                # Both partitions keep their own ownership server-side.
                self.assertEqual(
                    server.session.get_world_object("lobby", "sofa", zone_id=100).owner, alice_pid
                )
                self.assertEqual(
                    server.session.get_world_object("lobby", "sofa", zone_id=200).owner, bob_pid
                )
            finally:
                await server.stop()

        asyncio.run(flow())

    def test_unknown_zone_receives_all_bootstrap(self):
        async def flow():
            server = MPServer("127.0.0.1", 0)
            await server.start()
            try:
                alice, alice_pid, _ = await self._join_zone(server.port, "Alice", 100)

                # Dana connects but never readies: her zone is unknown, so the
                # server routes zone-scoped traffic to her too (join bootstrap).
                dana, _ = await self._join_hello(server.port, "Dana")
                await alice.wait_for_type("PLAYER_JOINED")

                await alice.send(msg.make_object_claim("lamp", zone_id=100))
                await alice.wait_for_type("OBJECT_CLAIM_ACK")
                received = await dana.wait_for_type("OBJECT_OWNERSHIP")
                self.assertEqual(received["payload"]["key"], "lamp")
                self.assertEqual(received["payload"]["owner"], alice_pid)
                self.assertEqual(received["payload"].get("zone_id"), 100)
            finally:
                await server.stop()

        asyncio.run(flow())

    def test_same_zone_shares_and_flip_releases(self):
        async def flow():
            server = MPServer("127.0.0.1", 0, interaction_cooldown=0.2)
            await server.start()
            try:
                alice, alice_pid, _ = await self._join_zone(server.port, "Alice", 100)
                bob, bob_pid, _ = await self._join_zone(server.port, "Bob", 100)
                await self._gate_open(alice)

                # Alice claims + interacts in zone 100; both players are in 100.
                await alice.send(msg.make_object_claim("sofa", zone_id=100))
                await alice.wait_for_type("OBJECT_CLAIM_ACK")
                bob_own = await bob.wait_for_type("OBJECT_OWNERSHIP")
                self.assertEqual(bob_own["payload"]["key"], "sofa")
                self.assertEqual(bob_own["payload"]["owner"], alice_pid)
                self.assertEqual(bob_own["payload"].get("zone_id"), 100)

                await alice.send(msg.make_interaction_request("sofa", "Read", zone_id=100))
                await alice.wait_for_type("INTERACTION_START")
                bob_start = await bob.wait_for_type("INTERACTION_START")
                self.assertEqual(bob_start["payload"].get("zone_id"), 100)
                self.assertEqual(bob_start["payload"]["player_id"], alice_pid)

                # Alice travels to zone 200: holdings in 100 are auto-released
                # and rebroadcast to members still in 100; Alice's mirror flips.
                await alice.send(msg.make_time_ready(200))
                await self._world_state_for_zone(alice, 200)
                await alice.wait_for_type("INTERACTION_STATE")
                rel = await bob.wait_for_type("OBJECT_OWNERSHIP")
                self.assertIsNone(rel["payload"]["owner"])
                self.assertEqual(rel["payload"].get("zone_id"), 100)
                free = await bob.wait_for_type("INTERACTION_FREE")
                self.assertEqual(free["payload"].get("zone_id"), 100)

                # Released ownership is claimable again in zone 100.
                await bob.send(msg.make_object_claim("sofa", zone_id=100))
                b_ack = await bob.wait_for_type("OBJECT_CLAIM_ACK")
                self.assertEqual(b_ack["payload"]["owner"], bob_pid)
            finally:
                await server.stop()

        asyncio.run(flow())


if __name__ == "__main__":
    unittest.main()