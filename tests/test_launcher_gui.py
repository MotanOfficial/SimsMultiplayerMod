"""Regression tests for the launcher GUI (tools/launcher).

Only run when Tk is available (it creates a hidden root). Exercises the
deferred-error callbacks that previously crashed with the classic Python
"cannot access free variable 'exc'" bug: exceptions captured inside an
``except ... as exc:`` block were referenced by a lambda that ran later on
the Tk thread, after CPython had deleted the exception variable.
"""

import os
import sys
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


if __name__ == "__main__":
    unittest.main()