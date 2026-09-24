"""Genealogy show-family-tree relay.

Joiners relay genealogy UI intent; host rebuilds SHOW_FAMILY_TREE via the
original command so Distributor fans through GameNetwork.
"""

from __future__ import division

from simmp.deep import KIND_GENEALOGY_SHOW_FAMILY_TREE, WrapperMessage
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


def install_genealogy_hooks():
    try:
        from server_commands import genealogy_commands
    except Exception:
        return False

    show_fn = getattr(genealogy_commands, "genealogy_show_family_tree", None)
    if show_fn is None:
        return False

    @Override(show_fn, role=Role.JOINER)
    def _show_family_tree_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            sim_info_id = _as_int(args[0] if args else kwargs.get("sim_info_id"))
            antecedent = _as_int(
                args[1] if len(args) > 1 else kwargs.get("antecedent_depth"), 8
            )
            descendant = _as_int(
                args[2] if len(args) > 2 else kwargs.get("descendant_depth"), 2
            )
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_GENEALOGY_SHOW_FAMILY_TREE,
            {
                "sim_info_id": sim_info_id,
                "antecedent_depth": antecedent,
                "descendant_depth": descendant,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        return None

    return True


@MessageHandler(KIND_GENEALOGY_SHOW_FAMILY_TREE)
def _host_genealogy_show_family_tree(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from server_commands import genealogy_commands

        genealogy_commands.genealogy_show_family_tree(
            int(body.get("sim_info_id") or 0),
            int(body.get("antecedent_depth") or 0),
            int(body.get("descendant_depth") or 0),
        )
    except Exception:
        return
