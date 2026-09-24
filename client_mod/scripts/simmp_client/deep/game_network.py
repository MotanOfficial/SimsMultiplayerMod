"""Relay native Sims distributor / UI messages via omega.send (joiner side).

Host side fans Client.send_message traffic to joiners as GameNetworkMessage.
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

    # Local-only message ids that joiners may still emit (camera, etc.).
    # Keep this list small; the deep path is host-authoritative.
    LOCAL_ONLY_MSG_IDS = set()
    for name in (
        "MSG_ID_NONE",
    ):
        value = getattr(Consts_pb2, name, None)
        if value is not None:
            LOCAL_ONLY_MSG_IDS.add(value)

    @Override(Client.send_message, role=Role.HOST)
    def _send_message_host(original, self, msg_id, msg_pb):
        if not getattr(self, "active", True):
            return None
        result = original(self, msg_id, msg_pb)
        if not SESSION.enabled or not SESSION.is_host:
            return result
        # Fan out to every joiner currently known via DEEP_RELAY broadcast of
        # opaque bytes. Target=0 with route=broadcast; each joiner injects.
        try:
            raw = msg_pb.SerializeToString() if hasattr(msg_pb, "SerializeToString") else bytes(msg_pb)
        except Exception:
            return result
        from simmp.deep import WrapperMessage

        wrapper = WrapperMessage(
            target_client=0,
            client_id=int(SESSION.player_id or 0),
            kind=KIND_GAME_NETWORK,
            body={"msg_id": int(msg_id), "msg": raw},
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
