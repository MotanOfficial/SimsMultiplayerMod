"""Message validation for the simmp protocol.

Every message that crosses the wire is validated here - on the server side
before it is trusted, and on the client side before it is processed.
"""

from simmp.constants import (
    ALLOWED_TOP_LEVEL_KEYS,
    MAX_CLIENT_ID_LENGTH,
    MAX_CLOCK_SPEED,
    MAX_EVENT_TYPE_LENGTH,
    MAX_FUNDS_BALANCE,
    MAX_INTERACTION_TYPE_LENGTH,
    MAX_NAME_LENGTH,
    MAX_OBJECT_FIELDS,
    MAX_OBJECT_KEY_LENGTH,
    MAX_OBJECT_UPDATE_OBJECTS,
    MAX_OBJECT_VALUE_STRING,
    MAX_ROOM_ID_LENGTH,
    MAX_SAVE_BYTES,
    MAX_SAVE_CHUNKS,
    MAX_SAVE_CHUNK_BASE64_LENGTH,
    MAX_SAVE_CHUNK_BYTES,
    MAX_SAVE_SLOT_LENGTH,
    MAX_STRING_LENGTH,
    MIN_CLOCK_SPEED,
    MESSAGE_TYPES,
    OPTIONAL_PAYLOAD_FIELDS,
    PROTOCOL_VERSION,
    REQUIRED_PAYLOAD_FIELDS,
)

INT_FIELDS = frozenset(
    ["player_id", "protocol_version", "seq", "zone_id", "lot_id", "requester_id", "absolute_ticks", "clock_speed", "affordance_id", "origin", "total", "size", "reached", "speed", "ticks"]
)
FLOAT_FIELDS = frozenset(
    ["client_time", "server_time", "timestamp", "real_time", "started_at", "cooldown_until"]
)
STR_FIELDS = frozenset(
    [
        "client_name",
        "client_version",
        "client_id",
        "room_id",
        "event_type",
        "code",
        "message",
        "name",
        "reason",
        "requester_name",
        "key",
        "object_key",
        "interaction",
        "ref",
        "affordance",
        "target",
        "slot",
        "data",
    ]
)

_ERROR_KEYS = ("code", "message")


class ProtocolError(ValueError):
    """A message failed validation. Carries a stable machine-readable code."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def require(condition, code, message):
    if not condition:
        raise ProtocolError(code, message)


def validate_message(message):
    require(isinstance(message, dict), "MALFORMED", "message must be a JSON object")

    unknown_top = set(message.keys()) - ALLOWED_TOP_LEVEL_KEYS
    require(not unknown_top, "MALFORMED", "unknown top-level field(s): %s" % sorted(unknown_top))

    require("version" in message, "MALFORMED", "missing 'version'")
    require(isinstance(message["version"], int), "MALFORMED", "'version' must be an integer")
    require(
        message["version"] == PROTOCOL_VERSION,
        "INCOMPATIBLE_VERSION",
        "unsupported protocol version %s (server speaks %s)"
        % (message["version"], PROTOCOL_VERSION),
    )

    require("type" in message, "MALFORMED", "missing 'type'")
    require(message["type"] in MESSAGE_TYPES, "UNKNOWN_TYPE", "unknown message type %r" % message["type"])

    require("payload" in message, "MALFORMED", "missing 'payload'")
    require(isinstance(message["payload"], dict), "MALFORMED", "'payload' must be an object")

    request_id = message.get("request_id")
    require(
        request_id is None or isinstance(request_id, str),
        "MALFORMED",
        "'request_id' must be a string or null",
    )
    require("request_id" in message, "MALFORMED", "missing 'request_id'")

    payload = message["payload"]
    required = REQUIRED_PAYLOAD_FIELDS[message["type"]]
    for field in required:
        require(field in payload, "MALFORMED", "payload missing %r" % field)

    allowed = set(required).union(OPTIONAL_PAYLOAD_FIELDS.get(message["type"], ()))
    unknown_payload = set(payload.keys()) - allowed
    require(not unknown_payload, "MALFORMED", "unknown payload field(s): %s" % sorted(unknown_payload))

    _validate_field_types(message["type"], payload)
    return message


def _validate_field_types(msg_type, payload):
    for field, value in payload.items():
        if msg_type == "EVENT" and field == "data":
            continue
        if field == "args" and msg_type in ("INTERACTION_REQUEST", "INTERACTION_START"):
            require(isinstance(value, dict), "MALFORMED", "'args' must be an object")
            require(len(value) <= MAX_OBJECT_FIELDS, "MALFORMED", "'args' has too many keys")
            for name, arg_value in value.items():
                require(
                    isinstance(name, str) and 0 < len(name) <= MAX_OBJECT_KEY_LENGTH,
                    "MALFORMED",
                    "arg name must be a non-empty string <= %s chars" % MAX_OBJECT_KEY_LENGTH,
                )
                require(_is_primitive(arg_value), "MALFORMED", "arg values must be primitive JSON")
                if isinstance(arg_value, str):
                    require(
                        len(arg_value) <= MAX_OBJECT_VALUE_STRING,
                        "MALFORMED",
                        "arg string exceeds %s chars" % MAX_OBJECT_VALUE_STRING,
                    )
            continue
        if field == "owner":
            require(
                value is None or (isinstance(value, int) and not isinstance(value, bool)),
                "MALFORMED",
                "'owner' must be an int player_id or null",
            )
            continue
        if field in INT_FIELDS:
            require(isinstance(value, int) and not isinstance(value, bool), "MALFORMED", "%r must be an int" % field)
        elif field in FLOAT_FIELDS:
            require(isinstance(value, (int, float)), "MALFORMED", "%r must be a number" % field)
        elif field in STR_FIELDS:
            require(isinstance(value, str), "MALFORMED", "%r must be a string" % field)

    limit = {
        "client_name": MAX_NAME_LENGTH,
        "client_version": MAX_STRING_LENGTH,
        "client_id": MAX_CLIENT_ID_LENGTH,
        "name": MAX_NAME_LENGTH,
        "room_id": MAX_ROOM_ID_LENGTH,
        "event_type": MAX_EVENT_TYPE_LENGTH,
        "code": MAX_STRING_LENGTH,
        "message": MAX_STRING_LENGTH,
        "reason": MAX_STRING_LENGTH,
        "requester_name": MAX_NAME_LENGTH,
        "key": MAX_OBJECT_KEY_LENGTH,
        "object_key": MAX_OBJECT_KEY_LENGTH,
        "interaction": MAX_INTERACTION_TYPE_LENGTH,
        "ref": MAX_OBJECT_KEY_LENGTH,
        "slot": MAX_SAVE_SLOT_LENGTH,
        "data": MAX_SAVE_CHUNK_BASE64_LENGTH,
    }
    for field, size in limit.items():
        if field in payload and isinstance(payload[field], str):
            require(
                len(payload[field]) <= size,
                "MALFORMED",
                "%r exceeds %s chars" % (field, size),
            )
            if field in ("key", "object_key"):
                require(0 < len(payload[field]), "MALFORMED", "'%s' must be non-empty" % field)
            if field == "interaction":
                require(0 < len(payload[field]), "MALFORMED", "'interaction' must be non-empty")

    if msg_type == "TRAVEL_RESPONSE":
        require(
            isinstance(payload["accepted"], bool),
            "MALFORMED",
            "'accepted' must be a boolean",
        )

    if payload.get("protocol_version") is not None and msg_type == "HELLO":
        require(
            isinstance(payload["protocol_version"], int) and payload["protocol_version"] == PROTOCOL_VERSION,
            "INCOMPATIBLE_VERSION",
            "client protocol version %s not supported" % payload["protocol_version"],
        )

    if msg_type == "ROOM_STATE":
        players = payload["players"]
        require(isinstance(players, list), "MALFORMED", "'players' must be a list")
        for player in players:
            require(isinstance(player, dict), "MALFORMED", "player entry must be an object")
            for key in ("player_id", "name", "connected"):
                require(key in player, "MALFORMED", "player entry missing %r" % key)
            require(isinstance(player["player_id"], int), "MALFORMED", "player_id must be an int")
            require(isinstance(player["name"], str), "MALFORMED", "name must be a string")
            require(
                isinstance(player["connected"], bool),
                "MALFORMED",
                "connected must be a boolean",
            )

    if msg_type == "OBJECT_UPDATE":
        _validate_object_entries(payload["objects"], require_rev=True)

    if msg_type == "WORLD_STATE":
        _validate_object_entries(payload["objects"], require_rev=False, require_owner=True)
        if "part" in payload or "total" in payload:
            require(
                "part" in payload and "total" in payload,
                "MALFORMED",
                "chunked WORLD_STATE needs both 'part' and 'total'",
            )
            part = payload["part"]
            total = payload["total"]
            require(
                isinstance(part, int) and not isinstance(part, bool) and part >= 0,
                "MALFORMED",
                "'part' must be a non-negative int",
            )
            require(
                isinstance(total, int) and not isinstance(total, bool) and total >= 1,
                "MALFORMED",
                "'total' must be a positive int",
            )
            require(part < total, "MALFORMED", "'part' must be less than 'total'")

    if msg_type == "WORLD_DELTA":
        require(payload["seq"] >= 1, "MALFORMED", "'seq' must be >= 1")
        _validate_object_entries(payload["updates"], require_rev=False, label="updates")

    if msg_type == "OBJECT_OWNERSHIP":
        co_owners = payload.get("co_owners")
        if co_owners is not None:
            require(isinstance(co_owners, list), "MALFORMED", "'co_owners' must be a list of ints")
            require(
                all(isinstance(pid, int) and not isinstance(pid, bool) for pid in co_owners),
                "MALFORMED",
                "'co_owners' entries must be int player_ids",
            )

    if msg_type == "OBJECT_CLAIM_ACK":
        co_owners = payload.get("co_owners")
        if co_owners is not None:
            require(isinstance(co_owners, list), "MALFORMED", "'co_owners' must be a list of ints")
            require(
                all(isinstance(pid, int) and not isinstance(pid, bool) for pid in co_owners),
                "MALFORMED",
                "'co_owners' entries must be int player_ids",
            )

    if msg_type == "INTERACTION_STATE":
        interactions = payload["interactions"]
        require(isinstance(interactions, list), "MALFORMED", "'interactions' must be a list")
        for interaction in interactions:
            require(isinstance(interaction, dict), "MALFORMED", "interaction entry must be an object")
            for field in ("object_key", "player_id", "interaction", "started_at"):
                require(field in interaction, "MALFORMED", "interaction entry missing %r" % field)
            require(
                isinstance(interaction["object_key"], str)
                and 0 < len(interaction["object_key"]) <= MAX_OBJECT_KEY_LENGTH,
                "MALFORMED",
                "object_key must be a non-empty string",
            )
            require(
                isinstance(interaction["player_id"], int) and not isinstance(interaction["player_id"], bool),
                "MALFORMED",
                "player_id must be an int",
            )
            require(
                isinstance(interaction["interaction"], str)
                and 0 < len(interaction["interaction"]) <= MAX_INTERACTION_TYPE_LENGTH,
                "MALFORMED",
                "interaction must be a non-empty string",
            )
            require(
                isinstance(interaction["started_at"], (int, float)),
                "MALFORMED",
                "started_at must be a number",
            )
            if "args" in interaction:
                require(isinstance(interaction["args"], dict), "MALFORMED", "'args' must be an object")
                for arg_value in interaction["args"].values():
                    require(_is_primitive(arg_value), "MALFORMED", "arg values must be primitive JSON")
            _validate_interaction_optional(interaction)

    if msg_type in ("INTERACTION_REQUEST", "INTERACTION_START"):
        _validate_interaction_optional(payload)

    if msg_type == "SAVE_PUSH":
        slot = payload["slot"]
        require(0 < len(slot) <= MAX_SAVE_SLOT_LENGTH, "MALFORMED", "'slot' must be a non-empty filename")
        require(not any(ch in slot for ch in "/\\\x00:"), "MALFORMED", "'slot' must be a bare filename without path separators")
        require(payload["seq"] >= 1, "MALFORMED", "'seq' must be >= 1")
        require(payload["total"] >= 1 and payload["total"] <= MAX_SAVE_CHUNKS, "MALFORMED", "'total' must be 1..%s" % MAX_SAVE_CHUNKS)
        require(payload["size"] >= 0 and payload["size"] <= MAX_SAVE_BYTES, "MALFORMED", "'size' must be 0..%s" % MAX_SAVE_BYTES)
        require(payload["seq"] <= payload["total"], "MALFORMED", "'seq' must be <= 'total'")
        data = payload["data"]
        if data:
            require(len(data) % 4 == 0 and (len(data) // 4) * 3 <= MAX_SAVE_CHUNK_BYTES + 2, "MALFORMED", "bad base64 length")
    if msg_type == "SAVE_ACK":
        require(payload["reached"] >= 0, "MALFORMED", "'reached' must be >= 0")

    if msg_type == "FUNDS_SYNC":
        balance = payload["balance"]
        require(
            isinstance(balance, int) and not isinstance(balance, bool)
            and 0 <= balance <= MAX_FUNDS_BALANCE,
            "MALFORMED",
            "'balance' must be an int simoleon balance in 0..%s" % MAX_FUNDS_BALANCE,
        )

    if msg_type in ("TIME_SYNC", "TIME_SPEED"):
        speed = payload["speed"]
        require(
            isinstance(speed, int) and not isinstance(speed, bool)
            and MIN_CLOCK_SPEED <= speed <= MAX_CLOCK_SPEED,
            "MALFORMED",
            "'speed' must be an int clock speed in %s..%s" % (MIN_CLOCK_SPEED, MAX_CLOCK_SPEED),
        )
    if msg_type == "TIME_SYNC" and payload.get("gate") is not None:
        require(
            isinstance(payload["gate"], bool),
            "MALFORMED",
            "'gate' must be a bool",
        )
    if msg_type == "TIME_SYNC" and payload.get("ticks") is not None:
        require(
            isinstance(payload["ticks"], int) and not isinstance(payload["ticks"], bool) and payload["ticks"] >= 0,
            "MALFORMED",
            "'ticks' must be a non-negative int",
        )


def _validate_interaction_optional(entry):
    """Optional execution hints on an interaction are typed but not required.

    `affordance_id` is the tuning instance id of the super interaction the
    player clicked (stable across clients); `affordance` is its display name
    and `target` the object/sim key it is aimed at. All three are best-effort:
    the receiving client degrades to label-only mirroring when they are absent
    or cannot be resolved locally.
    """
    aff_id = entry.get("affordance_id")
    if aff_id is not None:
        require(
            isinstance(aff_id, int) and not isinstance(aff_id, bool) and aff_id >= 0,
            "MALFORMED",
            "'affordance_id' must be a non-negative int",
        )
    for field in ("affordance", "target"):
        value = entry.get(field)
        if value is not None:
            require(isinstance(value, str), "MALFORMED", "%r must be a string" % field)
            require(
                0 < len(value) <= MAX_INTERACTION_TYPE_LENGTH if field == "affordance" else 0 < len(value) <= MAX_OBJECT_KEY_LENGTH,
                "MALFORMED",
                "%r exceeds allowed length" % field,
            )


def _validate_object_entries(entries, require_rev=False, require_owner=False, label="objects"):
    require(isinstance(entries, list), "MALFORMED", "'%s' must be a list" % label)
    if label == "objects":
        require(
            len(entries) <= MAX_OBJECT_UPDATE_OBJECTS,
            "MALFORMED",
            "too many objects in one message",
        )
    for entry in entries:
        require(isinstance(entry, dict), "MALFORMED", "%s entry must be an object" % label)
        require(isinstance(entry.get("key"), str) and 0 < len(entry["key"]) <= MAX_OBJECT_KEY_LENGTH,
                "MALFORMED", "entry 'key' must be a non-empty string <= %s chars" % MAX_OBJECT_KEY_LENGTH)
        if require_rev:
            require(
                isinstance(entry.get("rev"), int) and not isinstance(entry["rev"], bool),
                "MALFORMED",
                "entry missing integer 'rev'",
            )
        if require_owner:
            require("owner" in entry, "MALFORMED", "entry missing 'owner'")
            owner = entry.get("owner")
            require(
                owner is None or (isinstance(owner, int) and not isinstance(owner, bool)),
                "MALFORMED",
                "entry 'owner' must be an int player_id or null",
            )
            co_owners = entry.get("co_owners")
            if co_owners is not None:
                require(
                    isinstance(co_owners, list)
                    and all(isinstance(pid, int) and not isinstance(pid, bool) for pid in co_owners),
                    "MALFORMED",
                    "entry 'co_owners' must be a list of int player_ids",
                )
        fields = entry.get("fields")
        require(isinstance(fields, dict), "MALFORMED", "entry 'fields' must be an object")
        require(len(fields) <= MAX_OBJECT_FIELDS, "MALFORMED", "too many fields on an object")
        for name, value in fields.items():
            require(
                isinstance(name, str) and 0 < len(name) <= MAX_OBJECT_KEY_LENGTH,
                "MALFORMED",
                "field name must be a non-empty string <= %s chars" % MAX_OBJECT_KEY_LENGTH,
            )
            require(_is_primitive(value), "MALFORMED", "field values must be primitive JSON")
            if isinstance(value, str):
                require(
                    len(value) <= MAX_OBJECT_VALUE_STRING,
                    "MALFORMED",
                    "field string exceeds %s chars" % MAX_OBJECT_VALUE_STRING,
                )


def _is_primitive(value):
    return value is None or isinstance(value, (bool, int, float, str))