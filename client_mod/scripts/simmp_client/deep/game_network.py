"""Relay native Sims distributor / UI messages via omega.send (joiner side).

Host side fans Client.send_message traffic to joiners as GameNetworkMessage,
except a small set of local-only UI message ids (pie menus, dialogs, …) and
per-client ViewUpdate ops (active-sim selection, focus, …).

Joiners must still deliver those local ViewUpdate ops to their own omega —
blanket suppression (pre-M44) left the skewer unable to switch sims and
blocked pie-menu control because active_sim never stuck on the laptop.
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


# Per-client UI ops: keep on joiner local send_message, strip from host fan-out
# and from joiner receive injection. Mirrors open-source LOCAL_ONLY_OPS.
_LOCAL_ONLY_OP_NAMES = (
    "FOCUS",
    "HOVERTIP_CREATED",
    "SET_SIM_ACTIVE",
    "SET_VFX_MASK",
    "CLIENT_CREATE",
    "CLIENT_DELETE",
    "SET_GAME_TIME",
    "LIVE_DRAG_START",
    "LIVE_DRAG_END",
    "LIVE_DRAG_CANCEL",
    "SELECT_CAREER_UI",
    "SHOW_BILLS_DIALOG",
    "OPEN_INVENTORY",
    "NOTEBOOK_VIEW",
    "TAKE_PHOTO",
    "SEND_UI_MESSAGE",
)


def _local_only_op_types():
    try:
        from protocolbuffers.DistributorOps_pb2 import Operation
    except Exception:
        return set()
    return _collect_named_consts(Operation, _LOCAL_ONLY_OP_NAMES)


def _filter_view_update_ops(raw, keep=None, drop=None):
    """Rewrite a ViewUpdate protobuf, keeping or dropping ops by type.

    Returns serialized bytes, or None when nothing remains. On parse failure
    returns the original ``raw`` unchanged.
    """
    if not keep and not drop:
        return raw
    try:
        from protocolbuffers import Distributor_pb2
    except Exception:
        return raw
    try:
        msg = Distributor_pb2.ViewUpdate()
        msg.ParseFromString(raw)
    except Exception:
        return raw
    keep = set(keep or ())
    drop = set(drop or ())
    try:
        for entry in list(msg.entries):
            ops = entry.operation_list.operations
            kept = []
            for op in list(ops):
                op_type = int(getattr(op, "type", -1))
                if keep and op_type not in keep:
                    continue
                if drop and op_type in drop:
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
            local_ops = _local_only_op_types()
            if local_ops:
                filtered = _filter_view_update_ops(payload, drop=local_ops)
                if filtered is None:
                    return
                payload = filtered
        _omega_send(client.id, int(msg_id), payload)
    except Exception:
        return


def install_client_send_message_hooks():
    """Patch Client.send_message for host fan-out and joiner local UI passthrough.

    Called after sims4 modules are importable. Safe no-op outside the game.
    """
    try:
        from server.client import Client
        from protocolbuffers import Consts_pb2
    except Exception:
        return False

    from simmp_client.deep.override import Override, Role

    # Per-player UI messages: never broadcast; always allow joiner local send.
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
    view_id = getattr(Consts_pb2, "MSG_OBJECTS_VIEW_UPDATE", None)
    view_id_i = int(view_id) if view_id is not None else None

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
        if view_id_i is not None and msg_id_i == view_id_i:
            local_ops = _local_only_op_types()
            if local_ops:
                filtered = _filter_view_update_ops(raw, drop=local_ops)
                if filtered is None:
                    return result
                raw = filtered
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
        msg_id_i = int(msg_id)
        if msg_id_i in LOCAL_ONLY_MSG_IDS:
            return original(self, msg_id, msg_pb)
        # Local UI ViewUpdates (active sim, focus, …) must reach omega or the
        # skewer cannot switch and pie menus use sim_id=0 / host's sim.
        if view_id_i is not None and msg_id_i == view_id_i:
            local_ops = _local_only_op_types()
            if not local_ops:
                return None
            try:
                raw = (
                    msg_pb.SerializeToString()
                    if hasattr(msg_pb, "SerializeToString")
                    else bytes(msg_pb)
                )
            except Exception:
                return None
            filtered = _filter_view_update_ops(raw, keep=local_ops)
            if filtered is None:
                return None
            try:
                _omega_send(self.id, msg_id_i, filtered)
            except Exception:
                return None
            return None
        # Suppress simulation traffic; host owns world state.
        return None

    return True


def send_message_over_network(msg_id, msg_pb, target_player_id):
    """Host helper: ship a native Sims message to one joiner."""
    try:
        raw = msg_pb.SerializeToString()
    except Exception:
        raw = bytes(msg_pb)
    return SESSION.send_game_network(msg_id, raw, target_player_id)
