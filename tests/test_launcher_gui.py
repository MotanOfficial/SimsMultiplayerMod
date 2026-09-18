"""Regression tests for the launcher GUI (tools/launcher).

Only run when Tk is available (it creates a hidden root). Exercises the
deferred-error callbacks that previously crashed with the classic Python
"cannot access free variable 'exc'" bug: exceptions captured inside an
``except ... as exc:`` block were referenced by a lambda that ran later on
the Tk thread, after CPython had deleted the exception variable.
"""

import json
import os
import sys
import tempfile
import time
import unittest

try:
    import tkinter as tk
    _HAS_TK = True
except Exception:  # pragma: no cover - headless environments
    _HAS_TK = False

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if _HAS_TK:
    from tools import launcher
    from tools import lobby


@unittest.skipUnless(_HAS_TK, "Tk is not available on this machine")
class LauncherGuiTests(unittest.TestCase):
    def _app(self):
        root = tk.Tk()
        root.withdraw()
        app = launcher.LauncherApp(root)
        self.addCleanup(root.destroy)
        return app

    def test_host_ip_dropdown_lists_local_adapters(self):
        app = self._app()
        values = list(app.lan_ip_combo["values"])
        self.assertTrue(values, "LAN IP dropdown should list at least one adapter")
        for ip in values:
            parts = ip.split(".")
            self.assertEqual(len(parts), 4)

    def test_join_error_surfaces_real_message_not_free_variable(self):
        app = self._app()
        original = lobby.receive_save_file

        def boom(host, port, **kwargs):
            raise RuntimeError("connect() returned False; is the lobby running?")

        lobby.receive_save_file = boom
        self.addCleanup(setattr, lobby, "receive_save_file", original)
        app.var_join_ip.set("10.0.0.1")
        app.var_join_port.set("8765")
        app._join_lobby()
        deadline = 15
        text = ""
        for _ in range(deadline * 10):
            app.root.update()
            text = app.log_view.get("1.0", "end")
            if "Could not receive the save" in text:
                break
            time.sleep(0.1)
        self.assertIn("Join failed", app.join_status.cget("text"))
        self.assertIn("Could not receive the save", text)
        self.assertNotIn("free variable 'exc'", text)
        self.assertIn("normal", app.btn_join.cget("state"))

    def test_host_start_button_uses_inmemory_player_count(self):
        app = self._app()
        # unsynced + no players -> disabled even though a stale status file
        # might still exist on disk (regression: the old code re-read the file)
        app.synced = False
        app._connected_players = 0
        app._update_host_start_button()
        self.assertEqual(app.btn_host_start.cget("state"), "disabled")
        # synced + player connected in-memory -> enabled
        app.synced = True
        app._connected_players = 1
        app._update_host_start_button()
        self.assertEqual(app.btn_host_start.cget("state"), "normal")
        # player leaves (in-memory only; no file dependency) -> disabled again
        app._connected_players = 0
        app._update_host_start_button()
        self.assertEqual(app.btn_host_start.cget("state"), "disabled")

    def test_join_line_surfaces_save_progress_and_errors(self):
        app = self._app()
        app._join_line("[MP][SAVE] SAVE_PUSH slot.save 2/4 (more)")
        self.assertIn("2/4", app.join_status.cget("text"))
        self.assertEqual(app.join_progress["value"], 50)
        app._join_line("[MP][SAVE] Saved 'slot.save' -> C:\\saves\\slot.save")
        self.assertIn("Saved", app.join_status.cget("text"))
        self.assertEqual(app.join_progress["value"], 100)
        app._join_line("[MP][ERROR] Save write failed: OSError: disk full")
        self.assertIn("Save failed", app.join_status.cget("text"))
        self.assertIn("disk full", app.join_detail.cget("text"))
        self.assertIn("disk full", app.log_view.get("1.0", "end"))

    def test_join_line_drops_alarm_noise_from_status_card(self):
        # The launcher client can never arm the game alarm; that ERROR must
        # stay in the activity log and never overwrite the save-progress card.
        app = self._app()
        app._join_line("[MP][SAVE] SAVE_PUSH slot.save 1/4 (more)")
        phase = app.join_status.cget("text")
        self.assertIn("1/4", phase)
        app._join_line("[MP][ERROR] sync alarm unavailable; will retry on next tick/command")
        self.assertEqual(app.join_status.cget("text"), phase)
        self.assertIn("sync alarm unavailable", app.log_view.get("1.0", "end"))

    def test_share_line_tracks_chunk_progress(self):
        app = self._app()
        app.selected_save = os.path.join("C:\\", "saves", "Slot_00000003.save")
        app._share_line("[MP][SAVE] SAVE_ACK Slot_00000003.save ok=True reached=1 seq=3/4")
        self.assertIn("3/4", app.sync_status.cget("text"))
        self.assertEqual(app.share_progress["value"], 75)
        app._share_line("[MP][ERROR] sync alarm unavailable; will retry on next tick/command")
        self.assertIn("3/4", app.sync_status.cget("text"))

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
        self.assertEqual(result["project_root"], launcher.ROOT)
        self.assertTrue(
            os.path.isfile(os.path.join(result["scripts"], "simmp_client", "sims4_plugin.py"))
        )


if __name__ == "__main__":
    unittest.main()