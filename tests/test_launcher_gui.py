"""Regression tests for the launcher backend (LauncherBridge in tools/launcher_*).

Runs headless - no QML window and no display needed; the bridge is a plain
QObject. Exercises the deferred-error and save-progress callbacks that
previously crashed with the classic Python "cannot access free variable 'exc'"
bug: exceptions captured inside an ``except ... as exc:`` block were referenced
by a lambda that ran later on another thread, after CPython had deleted the
exception variable.
"""

import json
import os
import re
import sys
import tempfile
import time
import unittest

try:
    from PySide6.QtCore import QCoreApplication
    _HAS_QTCORE = True
except Exception:  # pragma: no cover - PySide6 not installed
    _HAS_QTCORE = False

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if _HAS_QTCORE:
    import tools.launcher_common as launcher_common
    from tools import launcher
    from tools.launcher_bridge import LauncherBridge


@unittest.skipUnless(_HAS_QTCORE, "PySide6 is not available on this machine")
class LauncherGuiTests(unittest.TestCase):
    def _app(self):
        bridge = LauncherBridge()
        self.addCleanup(bridge.shutdown)
        self.logs = []
        self.cards = []
        bridge.logAppended.connect(lambda *a: self.logs.append(a))
        bridge.cardStatus.connect(lambda *a: self.cards.append(a))
        return bridge

    def last_card(self, card_id):
        found = [c for c in self.cards if c[0] == card_id]
        return found[-1] if found else None

    def logged(self):
        return "\n".join(x[0] for x in self.logs)

    def test_launcher_imports_ok(self):
        # The Qt bridge must import without touching QML, and expose the slots
        # the UI binds against.
        bridge = LauncherBridge()
        self.addCleanup(bridge.shutdown)
        for name in ("startLobby", "stopLobby", "shareSave", "joinLobby",
                     "startGameHost", "startGameJoin", "installMod", "shutdown",
                     "lanIpSelected", "copyIp"):
            self.assertTrue(callable(getattr(bridge, name, None)), name)

    def test_join_error_surfaces_real_message_not_free_variable(self):
        app = self._app()
        from tools import lobby
        original = lobby.receive_save_file

        def boom(host, port, **kwargs):
            raise RuntimeError("connect() returned False; is the lobby running?")

        lobby.receive_save_file = boom
        self.addCleanup(setattr, lobby, "receive_save_file", original)
        app.joinIp = "10.0.0.1"
        app.joinPort = "8765"
        app.joinLobby()
        core = QCoreApplication.instance() or QCoreApplication([])
        deadline = time.time() + 15
        while time.time() < deadline:
            core.processEvents()
            time.sleep(0.05)
            text = self.logged()
            if "Could not receive the save" in text:
                break
        card = self.last_card("join")
        card = self.last_card("join")
        self.assertIsNotNone(card)
        self.assertEqual(card[1], "Join failed")
        self.assertIn("Could not receive the save", text)
        self.assertIn("connect() returned False", card[2])
        self.assertNotIn("free variable 'exc'", text)
        self.assertFalse(app.joining)

    def test_host_start_uses_inmemory_player_count(self):
        app = self._app()
        # unsynced -> disabled even if players are connected
        app._synced = False
        app._set_players(0)
        app._update_host_start_button()
        self.assertFalse(app.canHostStart)
        # synced -> enabled even with zero lobby TCP clients (they disconnect
        # when either side presses Start to launch the game)
        app._synced = True
        app._set_players(0)
        app._update_host_start_button()
        self.assertTrue(app.canHostStart)
        app._set_players(1)
        app._update_host_start_button()
        self.assertTrue(app.canHostStart)

    def test_join_line_surfaces_save_progress_and_errors(self):
        app = self._app()
        app._join_line("[MP][SAVE] SAVE_PUSH slot.save 2/4 (more)")
        card = self.last_card("join")
        self.assertIn("2/4", card[1])
        self.assertEqual(card[5], True)  # show_bar
        self.assertEqual(card[4], 50)    # progress
        app._join_line("[MP][SAVE] Saved 'slot.save' -> C:\\saves\\slot.save")
        card = self.last_card("join")
        self.assertIn("Saved", card[1])
        self.assertEqual(card[4], 100)   # progress
        app._join_line("[MP][ERROR] Save write failed: OSError: disk full")
        card = self.last_card("join")
        self.assertEqual(card[1], "Save failed")
        self.assertIn("disk full", card[2])
        self.assertIn("disk full", self.logged())

    def test_join_line_drops_alarm_noise_from_status_card(self):
        # The launcher client can never arm the game alarm; that ERROR must
        # stay in the activity log and never overwrite the save-progress card.
        app = self._app()
        app._join_line("[MP][SAVE] SAVE_PUSH slot.save 1/4 (more)")
        phase = self.last_card("join")[1]
        self.assertIn("1/4", phase)
        app._join_line("[MP][ERROR] sync alarm unavailable; will retry on next tick/command")
        self.assertEqual(self.last_card("join")[1], phase)
        self.assertIn("sync alarm unavailable", self.logged())

    def test_share_line_tracks_chunk_progress(self):
        app = self._app()
        app._selected_save = os.path.join("C:\\", "saves", "Slot_00000003.save")
        app._share_line("[MP][SAVE] SAVE_ACK Slot_00000003.save ok=True reached=1 seq=3/4")
        card = self.last_card("share")
        self.assertIn("3/4", card[1])
        self.assertEqual(card[4], 75)    # progress
        self.assertEqual(card[5], True)  # show_bar
        app._share_line("[MP][ERROR] sync alarm unavailable; will retry on next tick/command")
        self.assertIn("3/4", self.last_card("share")[1])

    def test_selftest_install_lands_full_mod(self):
        # _run_selftest drives the same code path as the "Install mod" button
        # (scripts/bundle-root resolution + build_script_mod.cmd_dev) without
        # needing a display; the frozen .exe runs it via SIM4_MP_SELFTEST.
        dest = tempfile.mkdtemp()
        launcher._run_selftest(dest)
        with open(os.path.join(dest, "result.json"), encoding="utf-8") as handle:
            result = json.load(handle)
        self.assertTrue(result.get("ok"), result)
        self.assertTrue(result["project_root"])
        self.assertEqual(result["root"], launcher_common.ROOT)
        self.assertTrue(
            os.path.isfile(os.path.join(result["scripts"], "simmp_client", "sims4_plugin.py"))
        )



    def test_write_config_deep_primary_host_vs_joiner(self):
        import shutil

        app = self._app()
        mods = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(mods, ignore_errors=True))
        app._mods = mods
        # mkdtemp lives under Temp; force the canonical writer to use our dir.
        app._canonical_mods_folder = lambda: mods
        app._write_config("127.0.0.1", 8765, "Alice", role="host")
        path = os.path.join(mods, "Sims4Multiplayer.json")
        with open(path, encoding="utf-8") as handle:
            host_cfg = json.load(handle)
        self.assertTrue(host_cfg["deep_hooks"])
        self.assertTrue(host_cfg["want_host"])
        self.assertFalse(host_cfg["world_sync"])
        self.assertTrue(host_cfg["interaction_sync"])
        self.assertFalse(host_cfg["sync_funds"])
        self.assertFalse(host_cfg["build_sync"])
        app._write_config("10.0.0.2", 8765, "Bob", role="join")
        with open(path, encoding="utf-8") as handle:
            join_cfg = json.load(handle)
        self.assertTrue(join_cfg["deep_hooks"])
        self.assertFalse(join_cfg["want_host"])
        self.assertEqual(join_cfg["name"], "Bob")

    def test_write_config_rejects_temp_mods_path(self):
        import shutil

        app = self._app()
        # Leaf must be "Mods" and not under Temp or tests/.
        real_mods = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_scratch_ea", "Mods")
        os.makedirs(real_mods, exist_ok=True)
        self.addCleanup(
            lambda: shutil.rmtree(os.path.dirname(real_mods), ignore_errors=True)
        )
        app._mods = os.path.join(tempfile.gettempdir(), "tmpe07yk3zi_fake")
        from launcher_common import RUNTIME

        saved = RUNTIME.mods_folder
        RUNTIME.mods_folder = lambda: real_mods
        self.addCleanup(lambda: setattr(RUNTIME, "mods_folder", saved))
        app._write_config("127.0.0.1", 8799, "Motan", role="host")
        path = os.path.join(real_mods, "Sims4Multiplayer.json")
        self.assertTrue(os.path.isfile(path), "config must land in real Mods, not Temp")
        with open(path, encoding="utf-8") as handle:
            cfg = json.load(handle)
        self.assertTrue(cfg["auto_connect"])
        self.assertTrue(cfg["deep_hooks"])
        self.assertEqual(cfg["port"], 8799)

    def _plant_mod_scripts(self, mods, with_preconnect=True):
        for path in [
            os.path.join(mods, "Sims4Multiplayer", "Scripts", "simmp_client", "sims4_plugin.py"),
            os.path.join(mods, "Sims4Multiplayer", "Scripts", "simmp_client", "connectivity.py"),
            os.path.join(mods, "Sims4Multiplayer", "Scripts", "simmp_client", "deep", "__init__.py"),
            os.path.join(mods, "Sims4Multiplayer", "Scripts", "simmp_client", "deep", "interactions.py"),
            os.path.join(mods, "Sims4Multiplayer", "Scripts", "simmp", "messages.py"),
            os.path.join(mods, "Sims4Multiplayer", "Scripts", "simmp", "deep", "messages.py"),
        ]:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            body = "# stub\n"
            if path.endswith("sims4_plugin.py") and with_preconnect:
                body = "def schedule_auto_connect():\n    pass\nbegin_preconnect_gate = True\n"
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(body)

    def test_preflight_blocks_missing_mod_scripts(self):
        import shutil

        app = self._app()
        mods = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_scratch_preflight_mods", "Mods")
        os.makedirs(mods, exist_ok=True)
        self.addCleanup(
            lambda: shutil.rmtree(os.path.dirname(mods), ignore_errors=True)
        )
        app._canonical_mods_folder = lambda: mods
        app._write_config("127.0.0.1", 8765, "Alice", role="join")
        ok, errors = app._preflight_launch("join", "127.0.0.1", 8765, "Alice")
        self.assertFalse(ok)
        self.assertTrue(any("Mod scripts incomplete" in e for e in errors))

    def test_preflight_ok_when_mod_and_config_ready(self):
        import shutil

        app = self._app()
        mods = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_scratch_preflight_ok", "Mods")
        os.makedirs(mods, exist_ok=True)
        self.addCleanup(
            lambda: shutil.rmtree(os.path.dirname(mods), ignore_errors=True)
        )
        app._canonical_mods_folder = lambda: mods
        self._plant_mod_scripts(mods)
        app._write_config("10.0.0.2", 8799, "Bob", role="join")
        ok, errors = app._preflight_launch("join", "10.0.0.2", 8799, "Bob")
        self.assertTrue(ok, errors)
        self.assertEqual(errors, [])

    def test_launch_game_blocked_without_preflight(self):
        import shutil
        from unittest import mock

        app = self._app()
        mods = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_scratch_preflight_block", "Mods")
        os.makedirs(mods, exist_ok=True)
        self.addCleanup(
            lambda: shutil.rmtree(os.path.dirname(mods), ignore_errors=True)
        )
        app._canonical_mods_folder = lambda: mods
        app._game = ""
        with mock.patch("subprocess.Popen") as popen, mock.patch("os.startfile") as startfile:
            launched = app._launch_game("join", "127.0.0.1", 8765)
        self.assertFalse(launched)
        popen.assert_not_called()
        startfile.assert_not_called()
        self.assertIn("Launch blocked", self.logged())


if __name__ == "__main__":
    unittest.main()