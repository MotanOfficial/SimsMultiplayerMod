"""Message builders for the simmp protocol.

Every message created here is validated before it is returned, so protocol
code can never emit a malformed message.
"""

import base64
import os
import time

from simmp.constants import PROTOCOL_VERSION
from simmp.validation import validate_message


def request_id():
    return os.urandom(16).hex()


def build_message(msg_type, payload=None, request_id_value=None):
    message = {
        "version": PROTOCOL_VERSION,
        "type": msg_type,
        "request_id": request_id_value if request_id_value is not None else request_id(),
        "payload": payload if payload is not None else {},
    }
    validate_message(message)
    return message


def make_hello(client_name, client_version, client_id=None, want_host=None, lobby=None):
    payload = {
        "client_name": client_name,
        "client_version": client_version,
        "protocol_version": PROTOCOL_VERSION,
    }
    if client_id is not None:
        payload["client_id"] = client_id
    if want_host is not None:
        payload["want_host"] = bool(want_host)
    if lobby is not None:
        payload["lobby"] = bool(lobby)
    return build_message("HELLO", payload)


def make_welcome(player_id, room_id, server_time):
    return build_message(
        "WELCOME",
        {
            "player_id": player_id,
            "protocol_version": PROTOCOL_VERSION,
            "server_time": server_time,
            "room_id": room_id,
        },
    )


def make_ping(client_time=None):
    return build_message("PING", {"client_time": client_time if client_time is not None else time.time()})


def make_pong(client_time, server_time):
    return build_message("PONG", {"client_time": client_time, "server_time": server_time})


def make_join_room(room_id):
    return build_message("JOIN_ROOM", {"room_id": room_id})


def make_room_state(room_id, players, host_player_id=None):
    payload = {"room_id": room_id, "players": players}
    if host_player_id is not None:
        payload["host_player_id"] = host_player_id
    return build_message("ROOM_STATE", payload)


def make_player_joined(player_id, name, room_id, lobby=False):
    payload = {"player_id": player_id, "name": name, "room_id": room_id}
    if lobby:
        payload["lobby"] = True
    return build_message("PLAYER_JOINED", payload)


def make_player_left(player_id, room_id, reason):
    return build_message("PLAYER_LEFT", {"player_id": player_id, "room_id": room_id, "reason": reason})


def make_event(event_type, data=None, seq=0, player_id=None):
    payload = {"event_type": event_type, "data": data, "seq": seq}
    if player_id is not None:
        payload["player_id"] = player_id
    return build_message("EVENT", payload)


def make_event_ack(seq, room_id):
    return build_message("EVENT_ACK", {"seq": seq, "room_id": room_id})


def make_presence(zone_id, lot_id, timestamp=None, player_id=None, room_id=None):
    payload = {
        "zone_id": zone_id,
        "lot_id": lot_id,
        "timestamp": timestamp if timestamp is not None else time.time(),
    }
    if player_id is not None:
        payload["player_id"] = player_id
    if room_id is not None:
        payload["room_id"] = room_id
    return build_message("PRESENCE", payload)


def make_travel_request(zone_id, request_id_value=None):
    return build_message("TRAVEL_REQUEST", {"zone_id": zone_id}, request_id_value=request_id_value)


def make_travel_invite(zone_id, requester_id, requester_name, request_id_value=None):
    return build_message(
        "TRAVEL_INVITE",
        {
            "zone_id": zone_id,
            "requester_id": requester_id,
            "requester_name": requester_name,
        },
        request_id_value=request_id_value,
    )


def make_travel_response(accepted, reason=None, request_id_value=None):
    payload = {"accepted": accepted}
    if reason is not None:
        payload["reason"] = reason
    return build_message("TRAVEL_RESPONSE", payload, request_id_value=request_id_value)


def make_travel_begin(zone_id, request_id_value=None):
    return build_message("TRAVEL_BEGIN", {"zone_id": zone_id}, request_id_value=request_id_value)


def make_travel_ready(zone_id, request_id_value=None):
    return build_message("TRAVEL_READY", {"zone_id": zone_id}, request_id_value=request_id_value)


def make_travel_complete(zone_id, request_id_value=None):
    return build_message("TRAVEL_COMPLETE", {"zone_id": zone_id}, request_id_value=request_id_value)


def make_travel_abort(reason, request_id_value=None):
    return build_message("TRAVEL_ABORT", {"reason": reason}, request_id_value=request_id_value)


def make_clock_sync(zone_id, absolute_ticks, real_time, clock_speed, player_id=None):
    payload = {
        "zone_id": zone_id,
        "absolute_ticks": absolute_ticks,
        "real_time": real_time,
        "clock_speed": clock_speed,
    }
    if player_id is not None:
        payload["player_id"] = player_id
    return build_message("CLOCK_SYNC", payload)


def make_object_update(objects, player_id=None, room_id=None, zone_id=None):
    """`objects` is [{"key": str, "fields": {str: value}, "rev": int}]."""
    payload = {"objects": objects}
    if player_id is not None:
        payload["player_id"] = player_id
    if room_id is not None:
        payload["room_id"] = room_id
    if zone_id is not None:
        payload["zone_id"] = zone_id
    return build_message("OBJECT_UPDATE", payload)


def make_object_claim(key, zone_id=None):
    payload = {"key": key}
    if zone_id is not None:
        payload["zone_id"] = zone_id
    return build_message("OBJECT_CLAIM", payload)


def make_object_release(key, zone_id=None):
    payload = {"key": key}
    if zone_id is not None:
        payload["zone_id"] = zone_id
    return build_message("OBJECT_RELEASE", payload)


def make_world_state(room_id, objects, zone_id=None, part=None, total=None):
    """A full world snapshot, optionally one part of a chunked snapshot.

    A real lot owns more objects than one frame may carry, so a large snapshot
    is sent as `total` numbered parts (0-based `part`); the client clears its
    mirror on part 0 and merges the rest. Small snapshots omit both fields.
    """
    payload = {"room_id": room_id, "objects": objects}
    if zone_id is not None:
        payload["zone_id"] = zone_id
    if part is not None and total is not None:
        payload["part"] = part
        payload["total"] = total
    return build_message("WORLD_STATE", payload)


def make_world_delta(room_id, seq, updates, player_id=None, zone_id=None):
    """`updates` is [{"key": str, "fields": {str: value}}]."""
    payload = {"room_id": room_id, "seq": seq, "updates": updates}
    if player_id is not None:
        payload["player_id"] = player_id
    if zone_id is not None:
        payload["zone_id"] = zone_id
    return build_message("WORLD_DELTA", payload)


def make_object_ownership(room_id, key, owner, player_id=None, zone_id=None):
    """`owner` is the single driving player_id (int) or None when released."""
    payload = {"room_id": room_id, "key": key, "owner": owner}
    if player_id is not None:
        payload["player_id"] = player_id
    if zone_id is not None:
        payload["zone_id"] = zone_id
    return build_message("OBJECT_OWNERSHIP", payload)


def make_object_claim_ack(key, owner):
    payload = {"key": key, "owner": owner}
    return build_message("OBJECT_CLAIM_ACK", payload)


def make_interaction_request(object_key, interaction, args=None, affordance=None, affordance_id=None, target=None, zone_id=None):
    payload = {"object_key": object_key, "interaction": interaction}
    if args is not None:
        payload["args"] = args
    if affordance is not None:
        payload["affordance"] = affordance
    if affordance_id is not None:
        payload["affordance_id"] = affordance_id
    if target is not None:
        payload["target"] = target
    if zone_id is not None:
        payload["zone_id"] = zone_id
    return build_message("INTERACTION_REQUEST", payload)


def make_interaction_end(object_key, zone_id=None):
    payload = {"object_key": object_key}
    if zone_id is not None:
        payload["zone_id"] = zone_id
    return build_message("INTERACTION_END", payload)


def make_interaction_start(room_id, object_key, interaction, player_id, started_at, args=None, affordance=None, affordance_id=None, target=None, zone_id=None):
    payload = {
        "room_id": room_id,
        "object_key": object_key,
        "interaction": interaction,
        "player_id": player_id,
        "started_at": started_at,
    }
    if args is not None:
        payload["args"] = args
    if affordance is not None:
        payload["affordance"] = affordance
    if affordance_id is not None:
        payload["affordance_id"] = affordance_id
    if target is not None:
        payload["target"] = target
    if zone_id is not None:
        payload["zone_id"] = zone_id
    return build_message("INTERACTION_START", payload)


def make_interaction_free(room_id, object_key, cooldown_until, zone_id=None):
    payload = {"room_id": room_id, "object_key": object_key, "cooldown_until": cooldown_until}
    if zone_id is not None:
        payload["zone_id"] = zone_id
    return build_message("INTERACTION_FREE", payload)


def make_interaction_state(room_id, interactions, zone_id=None):
    """`interactions` is [{"object_key": str, "player_id": int, "interaction": str, "started_at": float}]."""
    payload = {"room_id": room_id, "interactions": interactions}
    if zone_id is not None:
        payload["zone_id"] = zone_id
    return build_message("INTERACTION_STATE", payload)


def make_save_push(slot, seq, total, size, data, origin=None):
    """Push one chunk of a shared save file.

    `data` is one base64 chunk of `raw_bytes`; `total` is the chunk count,
    `size` the overall file size and `seq` is 1..total. Reassembly happens on
    the receiving client (`save_transfer.SaveInbox`). `origin` is stamped by
    the server, never by the sender.
    """
    payload = {
        "slot": slot,
        "seq": seq,
        "total": total,
        "size": size,
        "data": base64.b64encode(data).decode("ascii"),
    }
    if origin is not None:
        payload["origin"] = origin
    return build_message("SAVE_PUSH", payload)


def make_save_ack(slot, ok, reached, seq=None, total=None, message=None):
    payload = {"slot": slot, "ok": bool(ok), "reached": reached}
    if seq is not None:
        payload["seq"] = seq
    if total is not None:
        payload["total"] = total
    if message is not None:
        payload["message"] = message
    return build_message("SAVE_ACK", payload)


def make_save_request():
    """Ask the server to replay the room's cached save (if the host shared
    one while this client was not yet connected)."""
    return build_message("SAVE_REQUEST", {})


def make_object_gone(key):
    """Notify the room that a lot object has been removed (build/buy delete).

    `key` is a ``obj:<def>:<grid>`` world key as produced by the lot object
    sampler. Peers destroy their local copy of the same object and drop the
    mirror entry.
    """
    return build_message("OBJECT_GONE", {"key": key})


def make_funds_sync(balance, player_id=None):
    """Share the household simoleon balance (echo-style, room-wide).

    `balance` is the absolute household funds amount the sender converged to.
    Peers apply it absolutely so all sides end up on the same number. The
    server stamps `player_id` when relaying.
    """
    payload = {"balance": int(balance)}
    if player_id is not None:
        payload["player_id"] = player_id
    return build_message("FUNDS_SYNC", payload)


def make_time_unready():
    """Signal that the caller is no longer in a playable zone (CAS screen,
    manage worlds, main menu). The server re-gates the room PAUSED until the
    caller returns and sends TIME_READY again."""
    return build_message("TIME_UNREADY", {})


def make_time_sync(speed, ticks=None, player_id=None, gate=None):
    """Authoritative room clock state (sent by the server to clients).

    `speed` is a ClockSpeedMode int (0=paused..3). ``gate`` is an explicit
    bool indicating whether the room is paused by the readiness gate.
    Old servers that omit it cause the client to fall back to ``speed == 0``
    inference. ``ticks`` is an optional game-time reference.
    """
    payload = {"speed": speed}
    if ticks is not None:
        payload["ticks"] = ticks
    if player_id is not None:
        payload["player_id"] = player_id
    if gate is not None:
        payload["gate"] = bool(gate)
    return build_message("TIME_SYNC", payload)


def make_time_ready(zone_id):
    """Signal from a client that it is loaded in a zone and ready to play."""
    return build_message("TIME_READY", {"zone_id": zone_id})


def make_time_speed(speed, ticks=None, player_id=None):
    """A client's desired clock speed (last change wins in the room)."""
    payload = {"speed": speed}
    if ticks is not None:
        payload["ticks"] = ticks
    if player_id is not None:
        payload["player_id"] = player_id
    return build_message("TIME_SPEED", payload)


def make_error(code, message, ref=None):
    payload = {"code": code, "message": message}
    if ref is not None:
        payload["ref"] = ref
    return build_message("ERROR", payload)


def make_session_role(role, player_id=None):
    payload = {"role": role}
    if player_id is not None:
        payload["player_id"] = player_id
    return build_message("SESSION_ROLE", payload)


def make_deep_host(host_player_id, room_id=None):
    payload = {"host_player_id": host_player_id}
    if room_id is not None:
        payload["room_id"] = room_id
    return build_message("DEEP_HOST", payload)


def make_deep_relay(blob, route, target_player_id=None, player_id=None, kind=None):
    payload = {"blob": blob, "route": route}
    if target_player_id is not None:
        payload["target_player_id"] = target_player_id
    if player_id is not None:
        payload["player_id"] = player_id
    if kind is not None:
        payload["kind"] = kind
    return build_message("DEEP_RELAY", payload)

