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

    def test_funds_sync_echo_of_last_applied_is_ignored(self):
        client = self._client()
        applied = []

        def applier(balance):
            applied.append(balance)
            return balance

        client.set_funds_applier(applier)
        client._handle_message(msg.make_funds_sync(4250))
        client._handle_message(msg.make_funds_sync(4250))  # echo
        client._handle_message(msg.make_funds_sync(4400))
        self.assertEqual(applied, [4250, 4400])

    def test_object_gone_handler_removes_mirror_then_defers_destroy(self):
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
        client.object_gone_delay = 0.0
        client._handle_message(msg.make_object_gone("obj:9@100_200_300"))
        self.assertEqual(removed, [], "destroy must be deferred, not immediate")
        self.assertEqual(client.session.world.count(), 0)
        client._maybe_flush_pending_removals()
        self.assertEqual(removed, ["obj:9@100_200_300"])
        self.assertEqual(client._pending_removals, {})

    def test_deferred_destroy_cancelled_when_object_reappears(self):
        client = self._client()
        client.session.room_id = "lobby"
        # The moved object is re-published a grid cell away while the old key
        # is still buffered; the destroy must be cancelled.
        client.session.world.apply_full(
            "lobby",
            None,
            [{"key": "obj:9@101_200_300", "owner": 1000, "fields": {"x": 1.01}}],
        )
        removed = []
        client.set_object_gone_applier(lambda keys: removed.extend(keys))
        client.object_gone_delay = 0.0
        client._handle_message(msg.make_object_gone("obj:9@100_200_300"))
        client._maybe_flush_pending_removals()
        self.assertEqual(removed, [])

    def test_deferred_destroy_survives_unrelated_reappearance(self):
        client = self._client()
        client.session.room_id = "lobby"
        # A *different* definition far away must not cancel the delete.
        client.session.world.apply_full(
            "lobby",
            None,
            [{"key": "obj:88@900_900_900", "owner": 1000, "fields": {"x": 9.0}}],
        )
        removed = []
        client.set_object_gone_applier(lambda keys: removed.extend(keys))
        client.object_gone_delay = 0.0
        client._handle_message(msg.make_object_gone("obj:9@100_200_300"))
        client._maybe_flush_pending_removals()
        self.assertEqual(removed, ["obj:9@100_200_300"])

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


class WorldUpdateChunkingTests(unittest.TestCase):
    """A real lot owns more objects than one OBJECT_UPDATE may carry.

    Regression: an oversize batch was rejected as MALFORMED, which aborted
    the whole sync tick (`sync tick failed`). Updates must be chunked to the
    protocol limit instead.
    """

    def _client(self):
        client = MultiplayerClient(client_name="Alice")
        client.engine = FakeEngine()
        client.world_sync = True
        client.world_interval = 0.0
        client._last_world_sent = 0.0
        client.session.player_id = 1000
        client.session.room_id = "lobby"
        return client

    def test_many_owned_objects_split_into_valid_chunks(self):
        from simmp.constants import MAX_OBJECT_UPDATE_OBJECTS

        client = self._client()
        total = MAX_OBJECT_UPDATE_OBJECTS * 2 + 3
        objects = [
            {"key": "obj:%d@%d_0_0" % (i, i), "fields": {"x": float(i)}}
            for i in range(total)
        ]
        client.session.world.apply_full(
            "lobby", None,
            [{"key": o["key"], "owner": 1000, "fields": {}} for o in objects],
        )
        client.set_world_sampler(lambda: list(objects))
        with _zone_state(True, 42):
            client._maybe_send_world_update()

        self.assertEqual(len(client.engine.update_calls), 3)
        sent = 0
        for chunk, _zone in client.engine.update_calls:
            self.assertLessEqual(len(chunk), MAX_OBJECT_UPDATE_OBJECTS)
            sent += len(chunk)
            # The real builder validates; this would raise ProtocolError if
            # the chunk exceeded the limit.
            msg.make_object_update(chunk)
        self.assertEqual(sent, total)


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


class SyncHealthTests(unittest.TestCase):
    """Field-debugging visibility for silent-peer lockouts.

    Regression coverage for the "world held by a peer that never replicates"
    incident: hundreds of denials and zero incoming world updates used to
    look like a healthy idle session in client.log.
    """

    def _client(self):
        client = MultiplayerClient(client_name="Alice")
        client.engine = FakeEngine()
        lines = []
        client._notify = lines.append
        return client, lines

    @staticmethod
    def _health(lines):
        return [line for line in lines if "world sync health" in line]

    def _deny(self, client, key):
        client._handle_message(
            msg.make_error("OBJECT_LOCKED", "object %r is locked by player 1002" % key, ref=key)
        )

    def test_denials_are_tallied_and_summarized(self):
        client, lines = self._client()
        self._deny(client, "sofa")
        self.assertEqual(client._denied_claims, 1)
        client._maybe_log_sync_health()
        health = self._health(lines)
        self.assertEqual(len(health), 1)
        self.assertIn("1 claim(s) denied", health[0])
        self.assertIn("no world update ever received", health[0])

    def test_summary_does_not_repeat_within_the_interval(self):
        client, lines = self._client()
        self._deny(client, "sofa")
        client._maybe_log_sync_health()
        client._maybe_log_sync_health()
        self.assertEqual(len(self._health(lines)), 1, "the health line is throttled")

    def test_summary_reports_age_of_last_world_update(self):
        client, lines = self._client()
        client._handle_message(
            msg.make_world_delta("lobby", 1, [{"key": "obj:9@1_2_3", "fields": {"x": 1.0}}])
        )
        self.assertIsNotNone(client._last_world_delta_at)
        self._deny(client, "sofa")
        client._maybe_log_sync_health()
        health = self._health(lines)
        self.assertEqual(len(health), 1)
        self.assertIn("last world update 0s ago", health[0])

    def test_healthy_session_never_logs_health_lines(self):
        client, lines = self._client()
        client._handle_message(
            msg.make_world_delta("lobby", 1, [{"key": "obj:9@1_2_3", "fields": {"x": 1.0}}])
        )
        client._maybe_log_sync_health()
        self.assertEqual(self._health(lines), [], "no denials -> no health line")

    def test_disconnect_resets_the_denial_tally(self):
        client, lines = self._client()
        self._deny(client, "sofa")
        client._denied_summary_sent = client._denied_claims
        client.engine = None  # disconnect() stops the engine; the fake has none
        client.disconnect()
        self.assertEqual(client._denied_claims, 0)
        self.assertEqual(client._denied_summary_sent, 0)
        del lines[:]
        self._deny(client, "sofa")
        client._maybe_log_sync_health()
        self.assertEqual(len(self._health(lines)), 1, "a fresh session summarizes from zero")

