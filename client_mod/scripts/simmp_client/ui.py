"""In-game UI shims: toast notifications and the travel-invite dialog (M6).

Every `sims4`/`services`/`ui` import is lazy and guarded, so this module is
importable and unit-testable on a normal Python 3.7+ interpreter. Offline (or
when the game's dialog service is absent, e.g. in the main menu) `available()`
is False and the show methods return False without raising.

The dialog/toast rendering itself can only be verified inside the game; the
tests cover the fallback semantics and the wiring.
"""

GAME_TITLE = "Sims 4 Multiplayer"


def available():
    """True if the game's UI dialog service is reachable right now.

    Requires an actively-running zone (no toasts in the main menu)."""
    return _dialog_service() is not None


def _dialog_service():
    try:
        import services

        zone = services.current_zone()
        if zone is None or not zone.is_zone_running:
            return None
        service = services.get_ui_dialog_service(0)
        return service
    except Exception:
        return None


def _localized(text):
    try:
        from sims4.localization import LocalizationHelperTuning

        return LocalizationHelperTuning.get_raw_text(text)
    except Exception:
        return text


def show_notification(text, title=None):
    """Show a toast notification. Returns True when a dialog was shown."""
    service = _dialog_service()
    if service is None:
        return False
    try:
        from ui.ui_dialog import UiDialogNotification

        dialog = service.create_dialog(
            UiDialogNotification,
            None,
            text=_localized(text),
            title=_localized(title or GAME_TITLE),
        )
        dialog.show_dialog()
        return True
    except Exception:
        return False


def show_travel_invite(request_id, zone_id, requester_name, on_decision):
    """Show an accept/decline travel dialog (UiDialogOkCancel).

    `on_decision(request_id, accepted)` is called with the button chosen
    (never from the engine thread: the game always runs dialogs on the game
    thread). Returns True when a dialog was shown.
    """
    service = _dialog_service()
    if service is None:
        return False
    try:
        from ui.ui_dialog import UiDialogOkCancel, UiDialogResponse

        dialog = service.create_dialog(
            UiDialogOkCancel,
            None,
            text=_localized(
                "Player %s wants to travel with you to zone %s. Join?"
                % (requester_name, zone_id)
            ),
            title=_localized(GAME_TITLE),
            ok_text=_localized("Travel"),
            cancel_text=_localized("Decline"),
        )
        dialog.add_listener(_make_invite_listener(request_id, on_decision))
        dialog.show_dialog()
        return True
    except Exception:
        return False


def _make_invite_listener(request_id, on_decision):
    from ui.ui_dialog import UiDialogResponse

    def _listener(dialog_enum, response):
        accepted = str(response) == str(UiDialogResponse.Ok)
        try:
            on_decision(request_id, accepted)
        except Exception:
            pass

    return _listener


class GameUI:
    """Switches between console and in-game presentations.

    `note(line)` always routes to the console callback. `toast(text)` and
    `travel_invite(...)` are no-ops (returning False) whenever the dialog
    service is unavailable or `enabled` is off, so the game keeps working in
    the main menu and with `ui_dialogs: false`.
    """

    def __init__(self, enabled=True, console=None):
        self.enabled = enabled
        self.console = console

    def note(self, line):
        if self.console is not None:
            try:
                self.console(line)
            except Exception:
                pass

    def toast(self, text, title=None):
        if not self.enabled:
            return False
        return show_notification(text, title=title)

    def travel_invite(self, request_id, zone_id, requester_name, on_decision):
        if not self.enabled:
            return False
        return show_travel_invite(request_id, zone_id, requester_name, on_decision)