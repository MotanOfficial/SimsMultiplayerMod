"""Relay native Sims distributor / UI messages via omega.send (joiner side).

Host side fans Client.send_message traffic to joiners as GameNetworkMessage,
except a small set of local-only UI message ids (pie menus, dialogs, …).

ViewUpdates are fanned intact — stripping individual ops (M40) corrupted the
protobuf payload and left joiners looking permanently paused / missing objects.
"""

from simmp.deep import KIND_GAME_NETWORK
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.session import SESSION


def _omega_send(client_id, msg_id, payload):
    import omega

    omega.send(client_id, msg_id, payload)


def _collect_named_consts(module, names):
    values = set()
    for name in names:
        value = getattr(module, name, None)
        if value is not None:
            values.add(int(value))
    return values


# Op types joiners should ignore when injecting a host ViewUpdate. Filtered on
# the RECEIVE side so we never mutate the host's outbound protobuf.
_JOINER_IGNORE_OP_NAMES = (
    "SET_SIM_ACTIVE",
    "FOCUS",
)


@MessageHandler(KIND_GAME_NETWORK)
def _on_game_network(wrapper):
    """Joiner: inject host-authored native protocol bytes into the local client."""
    try:
        import services
        from protocolbuffers import Consts_pb2
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
        payload = bytes(raw)
        view_id = getattr(Consts_pb2, "MSG_OBJECTS_VIEW_UPDATE", None)
        if view_id is not None and int(msg_id) == int(view_id):
            filtered = _filter_view_update_ops(payload)
            if filtered is None:
                return
            payload = filtered
        _omega_send(client.id, int(msg_id), payload)
    except Exception:
        return


def _filter_view_update_ops(raw):
    """Drop per-client UI ops from a ViewUpdate without corrupting other ops.

    Returns serialized bytes, or None when nothing remains.
    """
    try:
        from protocolbuffers import Distributor_pb2
        from protocolbuffers.DistributorOps_pb2 import Operation
    except Exception:
        return raw
    ignore = _collect_named_consts(Operation, _JOINER_IGNORE_OP_NAMES)
    if not ignore:
        return raw
    try:
        msg = Distributor_pb2.ViewUpdate()
        msg.ParseFromString(raw)
    except Exception:
        return raw
    try:
        for entry in list(msg.entries):
            ops = entry.operation_list.operations
            kept = []
            for op in list(ops):
                if int(getattr(op, "type", -1)) in ignore:
                    continue
                kept.append(op.SerializeToString())
            del ops[:]
            for blob in kept:
                new_op = ops.add()
                new_op.ParseFromString(blob)
            if not ops:
                msg.entries.remove(entry)
        if not msg.entries:
            return None
        return msg.SerializeToString()
    except Exception:
        return raw


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
        try:
            raw = (
                msg_pb.SerializeToString()
                if hasattr(msg_pb, "SerializeToString")
                else bytes(msg_pb)
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
