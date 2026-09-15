"""Client-side tests for the live-world sync: money, object-gone detection,
and the TIME_UNREADY flow. All unit-grade (no real server or game)."""

import unittest
from unittest import mock

from simmp import messages as msg
from simmp_client.connectivity import MultiplayerClient


class FakeEngine(object):
    def __init__(self):
        self.connected = True
        self.gone_calls = []
        self.funds_calls = []
        self.update_calls = []
        self.claim_calls = []

    def send_object_gone(self, key):
        self.gone_calls.append(key)
        return True

    def send_funds_sync(self, balance):
        self.funds_calls.append(balance)
        return True

    def send_object_update(self, objects, zone_id=None):
        self.update_calls.append((objects, zone_id))
        return True

    def send_object_claim(self, key, zone_id=None):
        self.claim_calls.append(key)
        return True


def _zone_state(running, zone_id):
    return mock.patch(
        "simmp_client.connectivity.game_hooks.current_zone_running_state",
        return_value=mock.Mock(
            running=running, zone_id=zone_id, loading=False, has_clock=True, state="RUNNING"
        ),
    )


class FundsClientTests(unittest.TestCase):
    def _client(self):
        client = MultiplayerClient(client_name="Alice")
        client.engine = FakeEngine()
        return client

    def test_funds_sync_handler_applies_and_sets_baseline(self):
        client = self._client()
        applied = []
        client.set_funds_applier(applied.append)
        client._handle_message(msg.make_funds_sync(4250))
        self.assertEqual(applied, [4250])
        self.assertEqual(client._funds_baseline, 4250)

    def test_object_gone_handler_applies_and_removes_from_mirror(self):
        client = self._client()
        client.session.room_id = "lobby"
        client.session.world.apply_full(
            "lobby",
            None,
            [{"key": "obj:9@100_200_300", "owner": 1000, "fields": {"x": 1.0}}],
        )
        self.assertEqual(client.session.world.count(), 1)
        removed = []
        client.set_object_gone_applier(lambda keys: removed.extend(keys))
        client._handle_message(msg.make_object_gone("obj:9@100_200_300"))
        self.assertEqual(removed, ["obj:9@100_200_300"])
        self.assertEqual(client.session.world.count(), 0)

    def test_baseline_absorbs_first_sample(self):
        client = self._client()
        client.set_funds_sampler(lambda: 1000)
        client._maybe_sync_funds()
        self.assertEqual(client._funds_baseline, 1000)
        self.assertEqual(client.engine.funds_calls, [])

    def test_change_is_broadcast_once_then_throttled(self):
        client = self._client()
        balance = [1000]

        def sampler():
            return balance[0]

        client.set_funds_sampler(sampler)
        client._maybe_sync_funds()
        self.assertEqual(client._funds_baseline, 1000)

        balance[0] = 1005
        client._maybe_sync_funds()
        self.assertEqual(client.engine.funds_calls, [1005])
        self.assertEqual(client._funds_baseline, 1005)

        # Immediately after a send the interval gate holds: no duplicate.
        client._maybe_sync_funds()
        self.assertEqual(client.engine.funds_calls, [1005])

    def test_no_broadcast_without_change(self):
        client = self._client()
        client.set_funds_sampler(lambda: 25000)
        client._maybe_sync_funds()
        client._last_funds_sent = 0.0  # bypass the interval throttle
        client._maybe_sync_funds()
        self.assertEqual(client.engine.funds_calls, [])

    def test_applier_defensive_failure_keeps_client_alive(self):
        client = self._client()

        def bad_applier(balance):
            raise RuntimeError("game exploded")

        client.set_funds_applier(bad_applier)
        client._handle_message(msg.make_funds_sync(9000))
        self.assertEqual(client._funds_baseline, 9000)


class ObjectGoneClientTests(unittest.TestCase):
    def _client(self):
        client = MultiplayerClient(client_name="Alice")
        client.engine = FakeEngine()
        client.world_sync = True
        client.world_interval = 0.0
        client._last_world_sent = 0.0
        return client

    def _seed_owned(self, client, key):
        client.session.room_id = "lobby"
        client.session.world.apply_full(
            "lobby", None, [{"key": key, "owner": client.session.player_id or 1000, "fields": {}}]
        )

    def test_gone_after_two_missing_ticks(self):
        client = self._client()
        self._seed_owned(client, "obj:9@100_200_300")
        state = [{"key": "obj:9@100_200_300", "fields": {"x": 1.0}}]
        client.set_world_sampler(lambda: list(state))
        with _zone_state(True, 42):
            client._maybe_send_world_update()  # tick 1: seen
            self.assertEqual(client.engine.gone_calls, [])
            state.clear()  # missing from tick 2 onward
            client._maybe_send_world_update()  # tick 2: streak 1
            self.assertEqual(client.engine.gone_calls, [])
            client._maybe_send_world_update()  # tick 3: gone
        self.assertEqual(client.engine.gone_calls, ["obj:9@100_200_300"])
        self.assertNotIn("obj:9@100_200_300", set(client.session.world.keys()))

    def test_sim_keys_never_broadcast_gone(self):
        client = self._client()
        client._world_seen_last = {"sim:4242"}
        client.set_world_sampler(lambda: [])
        with _zone_state(True, 43):
            client._maybe_send_world_update()
            client._maybe_send_world_update()
        self.assertEqual(client.engine.gone_calls, [])

    def test_gone_suppressed_while_zone_not_running(self):
        client = self._client()
        self._seed_owned(client, "obj:9@1_2_3")
        client.set_world_sampler(lambda: [])
        with _zone_state(False, 44):
            client._maybe_send_world_update()
            client._maybe_send_world_update()
            client._maybe_send_world_update()
        self.assertEqual(client.engine.gone_calls, [])

    def test_zone_change_resets_tracking(self):
        client = self._client()
        client.set_world_sampler(lambda: [])
        with _zone_state(True, 100):
            client._maybe_send_world_update()
        self.assertEqual(client._world_tracked_zone, 100)
        self.assertEqual(client._world_seen_last, set())
        with _zone_state(True, 101):
            client._maybe_send_world_update()
        self.assertEqual(client._world_tracked_zone, 101)


class TimeUnreadyClientTests(unittest.TestCase):
    class FakeEngine(object):
        def __init__(self):
            self.connected = True
            self.ready_calls = []
            self.unready_calls = []

        def send_time_ready(self, zone_id):
            self.ready_calls.append(zone_id)
            return True

        def send_time_unready(self):
            self.unready_calls.append(True)
            return True

    def _client(self):
        client = MultiplayerClient(client_name="Alice")
        client.engine = self.FakeEngine()
        client.time_ready_sent = True
        client.time_unready_sent = False
        return client

    def test_unready_sent_once_when_zone_stops_running(self):
        client = self._client()
        with _zone_state(False, 999):
            client._maybe_sync_clock()
            client._maybe_sync_clock()
        self.assertEqual(client.engine.unready_calls, [True])
        self.assertTrue(client.time_unready_sent)
        self.assertFalse(client.time_ready_sent)

    def test_re_ready_resets_unready_flag(self):
        client = self._client()
        client.time_ready_sent = False
        client.time_unready_sent = True
        with _zone_state(True, 100):
            client._maybe_sync_clock()
        self.assertFalse(client.time_unready_sent)
        self.assertEqual(client.engine.ready_calls, [100])
        self.assertTrue(client.time_ready_sent)


class WorldMirrorRemovalTests(unittest.TestCase):
    def test_apply_removal_drops_key(self):
        from simmp_client.state.world import WorldMirror

        mirror = WorldMirror()
        mirror.apply_full("lobby", 5, [{"key": "obj:9@1_2_3", "owner": 1000, "fields": {}}])
        mirror.apply_removal("obj:9@1_2_3", 5)
        self.assertEqual(mirror.count(), 0)

    def test_apply_removal_ignores_other_zone(self):
        from simmp_client.state.world import WorldMirror

        mirror = WorldMirror()
        mirror.apply_full("lobby", 5, [{"key": "obj:9@1_2_3", "owner": 1000, "fields": {}}])
        mirror.apply_removal("obj:9@1_2_3", 6)
        self.assertEqual(mirror.count(), 1)