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

    def test_ensure_alarm_grace_after_restart(self):
        # After a stale restart, _last_alarm_tick is still old. ensure_alarm
        # must not immediately cancel the freshly armed handle.
        lines = []
        client = MultiplayerClient(notify=lines.append)
        client._preconnect_gate = True
        handle = object()

        def _arm(*_a, **_k):
            return handle

        with mock.patch.object(game_hooks, "add_one_off_real_time_alarm", side_effect=_arm), mock.patch.object(
            game_hooks, "add_repeating_real_time_alarm", return_value=None
        ), mock.patch.object(game_hooks, "cancel_alarm") as cancel:
            client._start_alarm()
            self.assertIs(client._alarm_handle, handle)
            client._last_alarm_tick = 1.0  # ancient
            client._alarm_started_at = 1000.0
            with mock.patch("simmp_client.connectivity.time") as fake_time:
                fake_time.time.return_value = 1001.0  # within grace
                client.ensure_alarm()
            cancel.assert_not_called()
            self.assertIs(client._alarm_handle, handle)
            with mock.patch("simmp_client.connectivity.time") as fake_time:
                fake_time.time.return_value = 1005.0  # past grace, still no tick
                client.ensure_alarm()
            cancel.assert_called()
            self.assertEqual(
                len([ln for ln in lines if "stale; restarting" in ln]), 1
            )


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
    """Auto-connect must keep the target until TCP succeeds — a nested
    one-shot that returned a handle but never fired used to clear config
    permanently until the player typed mp.autoconnect."""

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

    def test_schedule_keeps_config_until_tcp(self):
        client = mock.Mock()
        with mock.patch.object(sims4_plugin, "_apply_config", return_value=client):
            self.assertTrue(sims4_plugin.schedule_auto_connect())
        self.assertIsNotNone(sims4_plugin._auto_connect_config)
        client.begin_preconnect_gate.assert_called()

    def test_try_pending_connect_clears_on_success(self):
        client = mock.Mock()
        client.engine = None
        client._pending_connect_host = "127.0.0.1"
        client._pending_connect_port = 8799
        client.connect.return_value = True
        sys.modules["simmp_client.commands.cheat_commands"].get_client = lambda: client
        self.assertTrue(sims4_plugin.try_pending_connect(client))
        self.assertIsNone(sims4_plugin._auto_connect_config)
        client.connect.assert_called_once_with("127.0.0.1", 8799)

    def test_schedule_arms_preconnect_gate(self):
        client = mock.Mock()
        with mock.patch.object(sims4_plugin, "_apply_config", return_value=client):
            self.assertTrue(sims4_plugin.schedule_auto_connect())
        client.begin_preconnect_gate.assert_called()


if __name__ == "__main__":
    unittest.main()