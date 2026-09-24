"""Deep session role + protobuf relay over the existing simmp JSON transport."""

from __future__ import division

import base64

from simmp.deep import (
    KIND_GAME_NETWORK,
    WrapperMessage,
    decode_wrapper,
    encode_wrapper,
)
from simmp import messages as msg

from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override


class DeepSession(object):
    """Tracks host/joiner role and routes WrapperMessage blobs via DEEP_RELAY."""

    def __init__(self):
        self.enabled = False
        self.is_host = False
        self.host_player_id = None
        self.player_id = None
        self._send = None  # callable(message_dict)
        self._on_role_changed = None

    def bind(self, send_fn, player_id=None, on_role_changed=None):
        self._send = send_fn
        self.player_id = player_id
        self._on_role_changed = on_role_changed

    def set_player_id(self, player_id):
        self.player_id = player_id

    def activate(self, is_host, host_player_id=None):
        self.enabled = True
        self.is_host = bool(is_host)
        if host_player_id is not None:
            self.host_player_id = host_player_id
        Override.install_all(self.is_host)
        if self._on_role_changed is not None:
            self._on_role_changed(self.is_host)

    def deactivate(self):
        Override.uninstall_all()
        self.enabled = False
        self.is_host = False
        self.host_player_id = None

    def apply_deep_host(self, host_player_id):
        self.host_player_id = host_player_id if host_player_id else None
        if not self.enabled:
            return
        am_host = self.player_id is not None and self.host_player_id == self.player_id
        if am_host != self.is_host:
            Override.uninstall_all()
            self.is_host = am_host
            Override.install_all(self.is_host)
            if self._on_role_changed is not None:
                self._on_role_changed(self.is_host)

    def claim_host(self):
        if self._send is None:
            return False
        self._send(msg.make_session_role("host"))
        return True

    def claim_joiner(self):
        if self._send is None:
            return False
        self._send(msg.make_session_role("joiner"))
        return True

    def send_wrapper(self, wrapper, route="host", target_player_id=None):
        if self._send is None or not self.enabled:
            return False
        if not isinstance(wrapper, WrapperMessage):
            raise TypeError("wrapper must be WrapperMessage")
        if self.player_id is not None:
            wrapper.client_id = int(self.player_id)
        raw = encode_wrapper(wrapper)
        blob = base64.b64encode(raw).decode("ascii")
        self._send(
            msg.make_deep_relay(
                blob,
                route,
                target_player_id=target_player_id,
                player_id=self.player_id,
                kind=wrapper.kind,
            )
        )
        return True

    def send_game_network(self, msg_id, msg_bytes, target_player_id):
        wrapper = WrapperMessage(
            target_client=int(target_player_id),
            client_id=int(self.player_id or 0),
            kind=KIND_GAME_NETWORK,
            body={"msg_id": int(msg_id), "msg": bytes(msg_bytes)},
        )
        return self.send_wrapper(wrapper, route="player", target_player_id=target_player_id)

    def handle_protocol_message(self, message):
        """Consume DEEP_HOST / DEEP_RELAY / SESSION_ROLE frames. Returns True if handled."""
        mtype = message.get("type")
        payload = message.get("payload") or {}
        if mtype == "DEEP_HOST":
            self.apply_deep_host(payload.get("host_player_id"))
            return True
        if mtype == "SESSION_ROLE":
            role = payload.get("role")
            if role == "host":
                self.apply_deep_host(payload.get("player_id") or self.player_id)
                if not self.enabled:
                    self.activate(True, host_player_id=self.host_player_id)
            elif role == "joiner":
                if not self.enabled:
                    self.activate(False, host_player_id=self.host_player_id)
                else:
                    self.apply_deep_host(self.host_player_id)
            return True
        if mtype == "DEEP_RELAY":
            blob = payload.get("blob")
            if not blob:
                return True
            try:
                raw = base64.b64decode(blob.encode("ascii"))
                wrapper = decode_wrapper(raw)
            except Exception:
                return True
            MessageHandler.dispatch(wrapper)
            return True
        if mtype == "ROOM_STATE" and "host_player_id" in payload:
            self.apply_deep_host(payload.get("host_player_id"))
            return False  # still let normal ROOM_STATE handling run
        return False


# Process-wide session used by Override-installed hooks.
SESSION = DeepSession()
