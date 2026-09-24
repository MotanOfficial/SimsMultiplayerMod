"""Ghost powers ultimate progress relay."""

from __future__ import division

from simmp.deep import KIND_GET_ULTIMATE_PROGRESS, WrapperMessage
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
        return int(getattr(value, "id", getattr(value, "value", value)))
    except Exception:
        return default


def install_ghost_powers_hooks():
    try:
        from sims.ghost_powers import ghost_powers_commands
    except Exception:
        return False

    fn = getattr(ghost_powers_commands, "get_ultimate_progress", None)
    if fn is None:
        return False

    @Override(fn, role=Role.JOINER)
    def _progress_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            sim_id = _as_int(args[0] if args else kwargs.get("sim_id"))
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_GET_ULTIMATE_PROGRESS,
            {"sim_id": sim_id, "player_id": int(SESSION.player_id or 0)},
        )
        return None

    return True


@MessageHandler(KIND_GET_ULTIMATE_PROGRESS)
def _host_get_ultimate_progress(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from sims.ghost_powers import ghost_powers_commands

        ghost_powers_commands.get_ultimate_progress(int(body.get("sim_id") or 0))
    except Exception:
        return
