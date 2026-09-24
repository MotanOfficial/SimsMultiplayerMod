"""Travel-group show-extend-vacation relay.

End/extend vacation already live in ``travel.py`` (P9). This module only adds
the show-extend dialog request path.
"""

from __future__ import division

from simmp.deep import KIND_SHOW_EXTEND_VACATION, WrapperMessage
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


def install_travel_group_hooks():
    try:
        from server_commands import travel_group_commands
    except Exception:
        return False

    show_fn = getattr(travel_group_commands, "show_extend_vacation", None)
    if show_fn is None:
        show_fn = getattr(travel_group_commands, "show_extend_vacation_dialog", None)
    if show_fn is None:
        return False

    @Override(show_fn, role=Role.JOINER)
    def _show_extend_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_SHOW_EXTEND_VACATION,
            {"player_id": int(SESSION.player_id or 0)},
        )
        return None

    return True


@MessageHandler(KIND_SHOW_EXTEND_VACATION)
def _host_show_extend_vacation(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    info = sim_select.get_active_sim_for_player(player_id) if player_id else None
    if info is None:
        return
    try:
        try:
            from server_commands import travel_group_commands

            show_fn = getattr(travel_group_commands, "show_extend_vacation", None)
            if show_fn is None:
                show_fn = getattr(travel_group_commands, "show_extend_vacation_dialog", None)
            if show_fn is not None:
                show_fn()
                return
        except Exception:
            pass
        group = getattr(info, "travel_group", None)
        if group is None:
            household = getattr(info, "household", None)
            if household is not None:
                group = household.get_travel_group()
        if group is None:
            return
        msg = group.create_extend_vacation_dialog_msg()
        if msg is None:
            return
        from distributor import shared_messages
        from protocolbuffers import Consts_pb2
        from distributor.system import Distributor

        op = shared_messages.create_message_op(msg, Consts_pb2.MSG_EXTEND_VACATION)
        Distributor.instance().add_op_with_no_owner(op)
    except Exception:
        return
