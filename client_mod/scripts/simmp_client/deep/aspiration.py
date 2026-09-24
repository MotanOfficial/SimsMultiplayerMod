"""Primary aspiration track relay."""

from __future__ import division

from simmp.deep import KIND_SET_PRIMARY_ASPIRATION_TRACK, WrapperMessage
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
        return int(getattr(value, "guid64", getattr(value, "id", getattr(value, "value", value))))
    except Exception:
        return default


def install_aspiration_hooks():
    try:
        from server_commands import aspiration_commands
    except Exception:
        return False

    fn = getattr(aspiration_commands, "set_primary_track", None)
    if fn is None:
        return False

    @Override(fn, role=Role.JOINER)
    def _set_primary_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            track = _as_int(args[0] if args else kwargs.get("aspiration_track"))
            sim_id = _as_int(args[1] if len(args) > 1 else kwargs.get("sim_id"))
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_SET_PRIMARY_ASPIRATION_TRACK,
            {
                "aspiration_track": track,
                "sim_id": sim_id,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        return None

    return True


@MessageHandler(KIND_SET_PRIMARY_ASPIRATION_TRACK)
def _host_set_primary_track(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services
        from sims4.resources import Types

        info = services.sim_info_manager().get(int(body.get("sim_id") or 0))
        if info is None:
            return
        track_id = int(body.get("aspiration_track") or 0)
        track = services.get_instance_manager(Types.ASPIRATION_TRACK).get(track_id)
        if track is None:
            return
        info.primary_aspiration = track
    except Exception:
        return
