import unittest

from simmp_client import ui


class UIFallbackTests(unittest.TestCase):
    """The game-API code paths cannot run on a dev interpreter (no `sims4`
    package), so these tests lock the offline fallback semantics that keep the
    client working in the main menu and under `ui_dialogs: false`."""

    def test_available_is_false_offline(self):
        self.assertFalse(ui.available())

    def test_show_notification_returns_false_offline(self):
        self.assertFalse(ui.show_notification("hello", title="title"))

    def test_show_travel_invite_returns_false_and_never_decides(self):
        called = []
        shown = ui.show_travel_invite(5, 4242, "Alice", lambda rid, ok: called.append(rid))
        self.assertFalse(shown)
        self.assertEqual(called, [], "decision callback must not fire when no dialog was shown")

    def test_gameui_note_always_uses_console(self):
        lines = []
        game_ui = ui.GameUI(enabled=True, console=lines.append)
        game_ui.note("[MP][ERROR] something")
        self.assertEqual(lines, ["[MP][ERROR] something"])

    def test_gameui_toast_respects_enabled_flag_offline(self):
        lines = []
        game_ui = ui.GameUI(enabled=False, console=lines.append)
        self.assertFalse(game_ui.toast("hidden"))
        game_ui.enabled = True
        self.assertFalse(game_ui.toast("offline"), "offline toasts must fall back gracefully")

    def test_gameui_travel_invite_respects_enabled_flag_offline(self):
        called = []
        game_ui = ui.GameUI(enabled=False)
        self.assertFalse(game_ui.travel_invite(1, 4242, "Alice", lambda rid, ok: called.append(rid)))
        game_ui.enabled = True
        self.assertFalse(game_ui.travel_invite(1, 4242, "Alice", lambda rid, ok: called.append(rid)))
        self.assertEqual(called, [])


if __name__ == "__main__":
    unittest.main()