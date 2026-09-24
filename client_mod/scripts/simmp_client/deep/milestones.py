"""Lifetime / developmental milestones panel relay."""

from __future__ import division

from simmp.deep import KIND_SHOW_LIFETIME_MILESTONES_PANEL, WrapperMessage
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


def _as_int(value, default=-1):
    if value is None:
        return default
    try:
        return int(getattr(value, "id", getattr(value, "value", value)))
    except Exception:
        return default


def install_milestone_hooks():
    try:
        from developmental_milestones import developmental_milestone_commands
    except Exception:
        return False

    show_fn = getattr(
        developmental_milestone_commands, "show_lifetime_milestones_panel", None
    )
    if show_fn is None:
        return False

    @Override(show_fn, role=Role.JOINER)
    def _show_milestones_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            opt_sim = _as_int(args[0] if args else kwargs.get("opt_sim"), -1)
            category_id = _as_int(
                args[1] if len(args) > 1 else kwargs.get("category_id"), -1
            )
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_SHOW_LIFETIME_MILESTONES_PANEL,
            {
                "opt_sim": opt_sim,
                "category_id": category_id,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        return None

    return True


@MessageHandler(KIND_SHOW_LIFETIME_MILESTONES_PANEL)
def _host_show_lifetime_milestones_panel(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from developmental_milestones import developmental_milestone_commands

        opt_sim = int(body.get("opt_sim") if body.get("opt_sim") is not None else -1)
        category_id = int(
            body.get("category_id") if body.get("category_id") is not None else -1
        )
        if opt_sim < 0 and category_id < 0:
            developmental_milestone_commands.show_lifetime_milestones_panel()
        elif category_id < 0:
            developmental_milestone_commands.show_lifetime_milestones_panel(opt_sim)
        else:
            developmental_milestone_commands.show_lifetime_milestones_panel(
                None if opt_sim < 0 else opt_sim, category_id
            )
    except Exception:
        return
