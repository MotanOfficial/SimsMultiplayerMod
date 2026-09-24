"""Solve-motive (auto-satisfy need) relay."""

from __future__ import division

from simmp.deep import KIND_SOLVE_MOTIVE, WrapperMessage
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


def install_statistics_hooks():
    try:
        from server_commands import statistic_commands
    except Exception:
        return False

    fn = getattr(statistic_commands, "solve_motive", None)
    if fn is None:
        return False

    @Override(fn, role=Role.JOINER)
    def _solve_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            stat_type = args[0] if args else kwargs.get("stat_type")
            opt_sim = args[1] if len(args) > 1 else kwargs.get("opt_sim")
            if opt_sim is None:
                try:
                    import services
                    sim_id = int(services.active_sim_info().id)
                except Exception:
                    sim_id = 0
            else:
                sim_id = _as_int(opt_sim)
            st = -1 if stat_type is None else _as_int(stat_type, -1)
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_SOLVE_MOTIVE,
            {
                "sim_id": sim_id,
                "stat_type": st,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        return None

    return True


@MessageHandler(KIND_SOLVE_MOTIVE)
def _host_solve_motive(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from server_commands import statistic_commands

        st = body.get("stat_type", -1)
        sim_id = int(body.get("sim_id") or 0)
        if st is None or int(st) == -1:
            statistic_commands.solve_motive(None, sim_id)
        else:
            statistic_commands.solve_motive(int(st), sim_id)
    except Exception:
        return
