"""Calendar favorite-entry relay."""

from __future__ import division

from simmp.deep import KIND_SET_FAVORITE_CALENDAR_ENTRY, WrapperMessage
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION


def _relay_to_host(kind, body):
    wrapper = WrapperMessage(
        target_client=int(SESSION.host_player_id or 0),
        kind=kind,
        body=body,
    )
    return SESSION.send_wrapper(wrapper, route="host")


def _as_int(value, default=0):
    if value is None:
        return default
    try:
        return int(getattr(value, "value", value))
    except Exception:
        return default


def _as_bool(value):
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in ("1", "true", "yes", "on")


def install_calendar_hooks():
    try:
        from server_commands import calendar_commands
    except Exception:
        return False

    fn = getattr(calendar_commands, "set_favorite_calendar_entry", None)
    if fn is None:
        return False

    @Override(fn, role=Role.JOINER)
    def _favorite_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            event_id = _as_int(args[0] if args else kwargs.get("event_id"))
            is_fav = _as_bool(args[1] if len(args) > 1 else kwargs.get("is_favorite", False))
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_SET_FAVORITE_CALENDAR_ENTRY,
            {
                "event_id": event_id,
                "is_favorite": is_fav,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        return None

    return True


@MessageHandler(KIND_SET_FAVORITE_CALENDAR_ENTRY)
def _host_set_favorite_calendar(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services

        services.calendar_service().set_favorited_calendar_entry(
            int(body.get("event_id") or 0),
            bool(body.get("is_favorite")),
        )
    except Exception:
        return
