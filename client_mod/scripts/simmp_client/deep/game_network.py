"""Relay native Sims distributor / UI messages via omega.send (joiner side).

Host side fans Client.send_message traffic to joiners as GameNetworkMessage,
except local-only UI (pie menus, active-sim focus, dialogs, …) which must stay
on the machine that opened them.
"""

from simmp.deep import KIND_GAME_NETWORK
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.session import SESSION


def _omega_send(client_id, msg_id, payload):
    import omega

    omega.send(client_id, msg_id, payload)


@MessageHandler(KIND_GAME_NETWORK)
def _on_game_network(wrapper):
    """Joiner: inject host-authored native protocol bytes into the local client."""
    try:
        import services
    except Exception:
        return
    body = wrapper.body or {}
    msg_id = body.get("msg_id")
    raw = body.get("msg") or b""
    if msg_id is None:
        return
    client = services.get_first_client()
    if client is None:
        return
    try:
        _omega_send(client.id, int(msg_id), bytes(raw))
    except Exception:
        return


def _collect_named_consts(module, names):
    values = set()
    for name in names:
        value = getattr(module, name, None)
        if value is not None:
            values.add(int(value))
    return values


def _strip_local_only_view_ops(msg_pb, local_op_types):
    """Drop per-client UI ops (active sim, focus, …) from a ViewUpdate copy.

    Returns the filtered protobuf, or None when nothing remains to fan out.
    """
    if not local_op_types:
        return msg_pb
    try:
        entries = getattr(msg_pb, "entries", None)
        if not entries:
            return msg_pb
        # Mutate a clone so the host's local UI still receives every op.
        clone = msg_pb.__class__()
        clone.CopyFrom(msg_pb)
        for entry in list(clone.entries):
            ops = getattr(getattr(entry, "operation_list", None), "operations", None)
            if not ops:
                continue
            keep = []
            for op in list(ops):
                op_type = int(getattr(op, "type", -1))
                if op_type in local_op_types:
                    continue
                keep.append(op)
            del ops[:]
            ops.extend(keep)
            if not ops:
                clone.entries.remove(entry)
        if not clone.entries:
            return None
        return clone
    except Exception:
        return msg_pb


def install_client_send_message_hooks():
    """Patch Client.send_message for host fan-out and joiner suppression.

    Called after sims4 modules are importable. Safe no-op outside the game.
    """
    try:
        from server.client import Client
        from protocolbuffers import Consts_pb2
    except Exception:
        return False

    from simmp_client.deep.override import Override, Role

    # Per-player UI: never broadcast these msg ids. Targeted relays (pie menu
    # for a joiner request, dialog close, …) still use send_message_over_network.
    LOCAL_ONLY_MSG_IDS = _collect_named_consts(
        Consts_pb2,
        (
            "MSG_OBJECT_IS_INTERACTABLE",
            "MSG_PIE_MENU_CREATE",
            "MSG_PHONE_MENU_CREATE",
            "MSG_UI_DIALOG_SHOW",
            "MSG_GAME_SAVE_LOCK_UNLOCK",
            "MSG_SHOW_SIM_PROFILE",
        ),
    )

    local_op_types = set()
    try:
        from protocolbuffers.DistributorOps_pb2 import Operation

        local_op_types = _collect_named_consts(
            Operation,
            (
                "FOCUS",
                "HOVERTIP_CREATED",
                "SET_SIM_ACTIVE",
                # Native SetGameTime fan-out left joiners frozen on pause (M40).
                "SET_GAME_TIME",
                "CLIENT_CREATE",
                "CLIENT_DELETE",
                "LIVE_DRAG_START",
                "LIVE_DRAG_END",
                "LIVE_DRAG_CANCEL",
                "OPEN_INVENTORY",
                "SEND_UI_MESSAGE",
            ),
        )
    except Exception:
        local_op_types = set()

    view_update_id = getattr(Consts_pb2, "MSG_OBJECTS_VIEW_UPDATE", None)

    @Override(Client.send_message, role=Role.HOST)
    def _send_message_host(original, self, msg_id, msg_pb):
        if not getattr(self, "active", True):
            return None
        result = original(self, msg_id, msg_pb)
        if not SESSION.enabled or not SESSION.is_host:
            return result
        msg_id_i = int(msg_id)
        if msg_id_i in LOCAL_ONLY_MSG_IDS:
            return result
        payload = msg_pb
        if view_update_id is not None and msg_id_i == int(view_update_id):
            payload = _strip_local_only_view_ops(msg_pb, local_op_types)
            if payload is None:
                return result
        try:
            raw = (
                payload.SerializeToString()
                if hasattr(payload, "SerializeToString")
                else bytes(payload)
            )
        except Exception:
            return result
        from simmp.deep import WrapperMessage

        wrapper = WrapperMessage(
            target_client=0,
            client_id=int(SESSION.player_id or 0),
            kind=KIND_GAME_NETWORK,
            body={"msg_id": msg_id_i, "msg": raw},
        )
        SESSION.send_wrapper(wrapper, route="broadcast")
        return result

    @Override(Client.send_message, role=Role.JOINER)
    def _send_message_joiner(original, self, msg_id, msg_pb):
        if not getattr(self, "active", True):
            return None
        if int(msg_id) in LOCAL_ONLY_MSG_IDS:
            return original(self, msg_id, msg_pb)
        # Suppress most joiner→engine traffic; host owns simulation/UI ops.
        return None

    return True


def send_message_over_network(msg_id, msg_pb, target_player_id):
    """Host helper: ship a native Sims message to one joiner."""
    try:
        raw = msg_pb.SerializeToString()
    except Exception:
        raw = bytes(msg_pb)
    return SESSION.send_game_network(msg_id, raw, target_player_id)
