"""Custom schedule get-schedule relay (getaways)."""

from __future__ import division

from simmp.deep import KIND_GET_CUSTOM_SCHEDULE, WrapperMessage
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


def install_custom_schedule_hooks():
    try:
        from custom_schedules import custom_schedule_commands
    except Exception:
        return False

    fn = getattr(custom_schedule_commands, "get_schedule", None)
    if fn is None:
        return False

    @Override(fn, role=Role.JOINER)
    def _get_schedule_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            zone_id = _as_int(args[0] if args else kwargs.get("zone_id"))
            name = args[1] if len(args) > 1 else kwargs.get("name")
            premade = args[2] if len(args) > 2 else kwargs.get("premade_name_hash")
            name_s = str(name) if name is not None else ""
            premade_s = str(premade) if premade is not None else ""
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_GET_CUSTOM_SCHEDULE,
            {
                "zone_id": zone_id,
                "name": name_s,
                "premade_name_hash": premade_s,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        return None

    return True


@MessageHandler(KIND_GET_CUSTOM_SCHEDULE)
def _host_get_custom_schedule(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from custom_schedules import custom_schedule_commands

        name = body.get("name") or None
        premade = body.get("premade_name_hash") or None
        if name == "":
            name = None
        if premade == "":
            premade = None
        custom_schedule_commands.get_schedule(
            int(body.get("zone_id") or 0), name, premade
        )
    except Exception:
        return
