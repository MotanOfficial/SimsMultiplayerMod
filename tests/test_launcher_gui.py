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


if __name__ == "__main__":
    unittest.main()