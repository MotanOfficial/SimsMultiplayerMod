"""Fame allow-toggle relay (Get Famous).

Joiners relay set_allow_fame; host applies force_allow_fame on the target sim.
"""

from __future__ import division

from simmp.deep import KIND_SET_ALLOW_FAME, WrapperMessage
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION
from simmp_client.deep import sim_select


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
        return int(getattr(value, "id", getattr(value, "value", value)))
    except Exception:
        return default


def _as_bool(value):
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in ("1", "true", "yes", "on")


def install_fame_hooks():
    try:
        from fame import fame_commands
    except Exception:
        return False

    set_fn = getattr(fame_commands, "set_allow_fame", None)
    if set_fn is None:
        return False

    @Override(set_fn, role=Role.JOINER)
    def _set_allow_fame_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            allow_fame = _as_bool(args[0] if args else kwargs.get("allow_fame"))
            opt_sim = _as_int(args[1] if len(args) > 1 else kwargs.get("opt_sim"), -1)
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_SET_ALLOW_FAME,
            {
                "allow_fame": allow_fame,
                "opt_sim": opt_sim,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        return None

    return True


def _resolve_sim_info(opt_sim, player_id):
    try:
        import services

        if opt_sim is not None and int(opt_sim) >= 0:
            info = services.sim_info_manager().get(int(opt_sim))
            if info is not None:
                return info
        if player_id:
            active = sim_select.get_active_sim_for_player(player_id)
            if active is not None:
                return active
        client = services.get_first_client()
        if client is not None and getattr(client, "active_sim_info", None) is not None:
            return client.active_sim_info
    except Exception:
        return None
    return None


@MessageHandler(KIND_SET_ALLOW_FAME)
def _host_set_allow_fame(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    info = _resolve_sim_info(body.get("opt_sim"), body.get("player_id"))
    if info is None:
        return
    try:
        info.force_allow_fame(bool(body.get("allow_fame")))
    except Exception:
        return
