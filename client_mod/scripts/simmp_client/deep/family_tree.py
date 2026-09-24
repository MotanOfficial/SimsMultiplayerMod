"""Family-tree pack show-UI relay (distinct from genealogy)."""

from __future__ import division

from simmp.deep import KIND_FAMILY_TREE_SHOW, WrapperMessage
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


def install_family_tree_hooks():
    try:
        from family_tree import family_tree_commands
    except Exception:
        try:
            from server_commands import family_tree_commands
        except Exception:
            return False

    fn = getattr(family_tree_commands, "family_tree_show_family_tree", None)
    if fn is None:
        return False

    @Override(fn, role=Role.JOINER)
    def _show_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            sim_id = _as_int(args[0] if args else kwargs.get("sim_id"))
            pov = _as_int(args[1] if len(args) > 1 else kwargs.get("pov_sim_id"))
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_FAMILY_TREE_SHOW,
            {
                "sim_id": sim_id,
                "pov_sim_id": pov,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        return None

    return True


@MessageHandler(KIND_FAMILY_TREE_SHOW)
def _host_family_tree_show(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        try:
            from family_tree import family_tree_commands
        except Exception:
            from server_commands import family_tree_commands

        family_tree_commands.family_tree_show_family_tree(
            int(body.get("sim_id") or 0),
            int(body.get("pov_sim_id") or 0),
        )
    except Exception:
        return
