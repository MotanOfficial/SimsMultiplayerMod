"""Open sim-profile UI relay."""

from __future__ import division

from simmp.deep import KIND_OPEN_SIM_PROFILE_UI, WrapperMessage
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


def install_relationship_hooks():
    try:
        from server_commands import relationship_commands
    except Exception:
        return False

    fn = getattr(relationship_commands, "open_sim_profile_ui", None)
    if fn is None:
        return False

    @Override(fn, role=Role.JOINER)
    def _profile_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            profile = _as_int(args[0] if args else kwargs.get("profile_sim"))
            actor = _as_int(args[1] if len(args) > 1 else kwargs.get("actor_sim"))
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_OPEN_SIM_PROFILE_UI,
            {
                "profile_sim": profile,
                "actor_sim": actor,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        return None

    return True


@MessageHandler(KIND_OPEN_SIM_PROFILE_UI)
def _host_open_sim_profile_ui(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from server_commands import relationship_commands

        relationship_commands.open_sim_profile_ui(
            int(body.get("profile_sim") or 0),
            int(body.get("actor_sim") or 0),
        )
    except Exception:
        return
