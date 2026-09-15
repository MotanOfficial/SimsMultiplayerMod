import unittest

from simmp_client import presence
from simmp_client.hooks import game_hooks
from simmp_client.state.session import LocalSession


class PresenceHelperTests(unittest.TestCase):
    def test_build_presence_fields(self):
        payload = presence.build_presence(7, 12, timestamp=5.5)
        self.assertEqual(payload["zone_id"], 7)
        self.assertEqual(payload["lot_id"], 12)
        self.assertEqual(payload["timestamp"], 5.5)

    def test_build_presence_default_timestamp(self):
        payload = presence.build_presence(1, 2)
        self.assertIsInstance(payload["timestamp"], float)

    def test_format_presence(self):
        line = presence.format_presence({"zone_id": 7, "lot_id": 12, "timestamp": 5.5})
        self.assertIn("zone=7", line)
        self.assertIn("lot=12", line)
        self.assertIn("ago", line)
        self.assertEqual(presence.format_presence(None), "-")


class GameHooksOfflineTests(unittest.TestCase):
    def test_hooks_noop_outside_game(self):
        self.assertIsNone(game_hooks.add_repeating_real_time_alarm(object(), 0.5, lambda *a: None))
        self.assertIsNone(game_hooks.add_one_off_real_time_alarm(object(), 1.0, lambda *a: None))
        self.assertIsNone(game_hooks.sample_current_zone())
        self.assertIsNone(game_hooks.cancel_alarm(None))


class LocalSessionPresenceTtlTests(unittest.TestCase):
    def test_stale_presence_entries_are_purged(self):
        session = LocalSession()
        session.presence_ttl = 0.1
        session.apply_presence({"player_id": 1000, "room_id": "lobby", "zone_id": 7, "lot_id": 12, "timestamp": 5.5})
        session.apply_presence({"player_id": 1001, "room_id": "lobby", "zone_id": 9, "lot_id": 15, "timestamp": 6.5})
        session._presence_seen[1000] = 0.0  # arrived long ago
        # 1001 was seen just now (defaults to recent time.time()).
        session.purge_stale_presence()
        self.assertEqual(list(session.presence.keys()), [1001])

    def test_toggle_ttl_off_keeps_all(self):
        session = LocalSession()
        session.presence_ttl = 0.0
        session.apply_presence({"player_id": 1000, "room_id": "lobby", "zone_id": 7, "lot_id": 12, "timestamp": 5.5})
        session._presence_seen[1000] = 0.0
        session.purge_stale_presence()
        self.assertIn(1000, session.presence)

    def test_room_state_reset_wipes_seen_tracking(self):
        session = LocalSession()
        session.apply_presence({"player_id": 1000, "room_id": "lobby", "zone_id": 7, "lot_id": 12, "timestamp": 5.5})
        session.apply_room_state({"room_id": "alpha", "players": []})
        self.assertEqual(session._presence_seen, {})
        self.assertEqual(session.presence, {})

    def test_player_left_clears_seen_tracking(self):
        session = LocalSession()
        session.apply_presence({"player_id": 1000, "room_id": "lobby", "zone_id": 7, "lot_id": 12, "timestamp": 5.5})
        session.apply_player_left({"player_id": 1000, "room_id": "lobby", "reason": "disconnected"})
        self.assertNotIn(1000, session._presence_seen)
        self.assertNotIn(1000, session.presence)


if __name__ == "__main__":
    unittest.main()