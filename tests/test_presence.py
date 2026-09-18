import sys
import types
import unittest
from unittest import mock

from simmp_client import presence
from simmp_client import sims4_plugin
from simmp_client.connectivity import MultiplayerClient
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

    def test_alarm_unavailable_is_throttled(self):
        # Outside the game the alarm can never be created; `process_incoming`
        # (and thus `_start_alarm`) runs many times per second in the launcher,
        # so the ERROR must be logged once, not once per retry.
        lines = []
        client = MultiplayerClient(notify=lines.append)
        with mock.patch.object(
            game_hooks,
            "add_one_off_real_time_alarm",
            return_value=None,
        ):
            for _ in range(25):
                client._start_alarm()
        alarm_errors = [line for line in lines if "sync alarm unavailable" in line]
        self.assertEqual(len(alarm_errors), 1, "alarm failure was logged on every retry")
        # after the throttle window elapses, one more line is allowed
        client._last_alarm_fail_log = 0.0
        client._start_alarm()
        alarm_errors = [line for line in lines if "sync alarm unavailable" in line]
        self.assertEqual(len(alarm_errors), 2)
        client._last_alarm_fail_log = 0.0
        for _ in range(5):
            client._start_alarm()
        alarm_errors = [line for line in lines if "sync alarm unavailable" in line]
        self.assertEqual(len(alarm_errors), 3)
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


class AutoConnectScheduleTests(unittest.TestCase):
    """The stored auto-connect config must survive a failed schedule so the
    first mp.* command can retry instead of silently never connecting."""

    def setUp(self):
        fake = types.ModuleType("simmp_client.commands.cheat_commands")
        package = types.ModuleType("simmp_client.commands")
        package.cheat_commands = fake
        self._saved = {
            "simmp_client.commands": sys.modules.get("simmp_client.commands"),
            "simmp_client.commands.cheat_commands": sys.modules.get(
                "simmp_client.commands.cheat_commands"
            ),
        }
        sys.modules["simmp_client.commands"] = package
        sys.modules["simmp_client.commands.cheat_commands"] = fake
        sims4_plugin._auto_connect_config = {"host": "h", "port": 1}

    def tearDown(self):
        for name, module in self._saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        sims4_plugin._auto_connect_config = None

    def test_successful_schedule_consumes_config(self):
        with mock.patch.object(sims4_plugin, "_apply_config", return_value=object()), \
                mock.patch.object(
                    game_hooks, "add_one_off_real_time_alarm", return_value="handle"
                ):
            self.assertTrue(sims4_plugin.schedule_auto_connect())
        self.assertIsNone(sims4_plugin._auto_connect_config)

    def test_failed_schedule_keeps_config_for_retry(self):
        with mock.patch.object(sims4_plugin, "_apply_config", return_value=object()), \
                mock.patch.object(
                    game_hooks, "add_one_off_real_time_alarm", return_value=None
                ):
            self.assertFalse(sims4_plugin.schedule_auto_connect())
        self.assertIsNotNone(sims4_plugin._auto_connect_config)


if __name__ == "__main__":
    unittest.main()