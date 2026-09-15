"""Central constants for the simmp protocol (version 4)."""

PROTOCOL_VERSION = 4

DEFAULT_ROOM_ID = "lobby"

MAX_FRAME_BYTES = 1 << 20
MAX_STRING_LENGTH = 512
MAX_NAME_LENGTH = 64
MAX_ROOM_ID_LENGTH = 64
MAX_EVENT_TYPE_LENGTH = 128
MAX_CLIENT_ID_LENGTH = 64
MAX_OBJECT_KEY_LENGTH = 64
MAX_OBJECT_FIELDS = 32
MAX_OBJECT_UPDATE_OBJECTS = 16
MAX_OBJECT_VALUE_STRING = 256
MAX_INTERACTION_TYPE_LENGTH = 128
MAX_SAVE_SLOT_LENGTH = 128
# One SAVE_PUSH chunk, in raw bytes before base64. Kept well below
# MAX_FRAME_BYTES (1 MiB) so the base64 + JSON envelope still fits.
MAX_SAVE_CHUNK_BYTES = 512 * 1024
MAX_SAVE_CHUNK_BASE64_LENGTH = ((MAX_SAVE_CHUNK_BYTES + 2) // 3) * 4
MAX_SAVE_CHUNKS = 20000
MAX_SAVE_BYTES = 512 * 1024 * 1024

# Wire values for the shared clock (`TIME_SYNC`/`TIME_SPEED`). These mirror
# the int values of the game's `ClockSpeedMode` enum (PAUSED=0..SPEED3=3).
CLOCK_SPEED_PAUSED = 0
CLOCK_SPEED_NORMAL = 1
CLOCK_SPEED_2 = 2
CLOCK_SPEED_3 = 3
MIN_CLOCK_SPEED = 0
MAX_CLOCK_SPEED = 3

HELLO = "HELLO"
WELCOME = "WELCOME"
PING = "PING"
PONG = "PONG"
JOIN_ROOM = "JOIN_ROOM"
ROOM_STATE = "ROOM_STATE"
PLAYER_JOINED = "PLAYER_JOINED"
PLAYER_LEFT = "PLAYER_LEFT"
EVENT = "EVENT"
EVENT_ACK = "EVENT_ACK"
PRESENCE = "PRESENCE"
TRAVEL_REQUEST = "TRAVEL_REQUEST"
TRAVEL_INVITE = "TRAVEL_INVITE"
TRAVEL_RESPONSE = "TRAVEL_RESPONSE"
TRAVEL_BEGIN = "TRAVEL_BEGIN"
TRAVEL_READY = "TRAVEL_READY"
TRAVEL_COMPLETE = "TRAVEL_COMPLETE"
TRAVEL_ABORT = "TRAVEL_ABORT"
CLOCK_SYNC = "CLOCK_SYNC"
OBJECT_UPDATE = "OBJECT_UPDATE"
OBJECT_CLAIM = "OBJECT_CLAIM"
OBJECT_RELEASE = "OBJECT_RELEASE"
WORLD_STATE = "WORLD_STATE"
WORLD_DELTA = "WORLD_DELTA"
OBJECT_OWNERSHIP = "OBJECT_OWNERSHIP"
OBJECT_CLAIM_ACK = "OBJECT_CLAIM_ACK"
INTERACTION_REQUEST = "INTERACTION_REQUEST"
INTERACTION_END = "INTERACTION_END"
INTERACTION_START = "INTERACTION_START"
INTERACTION_FREE = "INTERACTION_FREE"
INTERACTION_STATE = "INTERACTION_STATE"
SAVE_PUSH = "SAVE_PUSH"
SAVE_ACK = "SAVE_ACK"
SAVE_REQUEST = "SAVE_REQUEST"
TIME_SYNC = "TIME_SYNC"
TIME_READY = "TIME_READY"
TIME_SPEED = "TIME_SPEED"
ERROR = "ERROR"

MESSAGE_TYPES = frozenset(
    [
        HELLO,
        WELCOME,
        PING,
        PONG,
        JOIN_ROOM,
        ROOM_STATE,
        PLAYER_JOINED,
        PLAYER_LEFT,
        EVENT,
        EVENT_ACK,
        PRESENCE,
        TRAVEL_REQUEST,
        TRAVEL_INVITE,
        TRAVEL_RESPONSE,
        TRAVEL_BEGIN,
        TRAVEL_READY,
        TRAVEL_COMPLETE,
        TRAVEL_ABORT,
        CLOCK_SYNC,
        OBJECT_UPDATE,
        OBJECT_CLAIM,
        OBJECT_RELEASE,
        WORLD_STATE,
        WORLD_DELTA,
        OBJECT_OWNERSHIP,
        OBJECT_CLAIM_ACK,
        INTERACTION_REQUEST,
        INTERACTION_END,
        INTERACTION_START,
        INTERACTION_FREE,
        INTERACTION_STATE,
        SAVE_PUSH,
        SAVE_ACK,
        SAVE_REQUEST,
        TIME_SYNC,
        TIME_READY,
        TIME_SPEED,
        ERROR,
    ]
)

REQUIRED_PAYLOAD_FIELDS = {
    HELLO: ("client_name", "client_version", "protocol_version"),
    WELCOME: ("player_id", "protocol_version", "server_time", "room_id"),
    PING: ("client_time",),
    PONG: ("client_time", "server_time"),
    JOIN_ROOM: ("room_id",),
    ROOM_STATE: ("room_id", "players"),
    PLAYER_JOINED: ("player_id", "name", "room_id"),
    PLAYER_LEFT: ("player_id", "room_id", "reason"),
    EVENT: ("event_type", "data", "seq"),
    EVENT_ACK: ("seq", "room_id"),
    PRESENCE: ("zone_id", "lot_id", "timestamp"),
    TRAVEL_REQUEST: ("zone_id",),
    TRAVEL_INVITE: ("zone_id", "requester_id", "requester_name"),
    TRAVEL_RESPONSE: ("accepted",),
    TRAVEL_BEGIN: ("zone_id",),
    TRAVEL_READY: ("zone_id",),
    TRAVEL_COMPLETE: ("zone_id",),
    TRAVEL_ABORT: ("reason",),
    CLOCK_SYNC: ("zone_id", "absolute_ticks", "real_time", "clock_speed"),
    OBJECT_UPDATE: ("objects",),
    OBJECT_CLAIM: ("key",),
    OBJECT_RELEASE: ("key",),
    WORLD_STATE: ("room_id", "objects"),
    WORLD_DELTA: ("room_id", "seq", "updates"),
    OBJECT_OWNERSHIP: ("room_id", "key", "owner"),
    OBJECT_CLAIM_ACK: ("key", "owner"),
    INTERACTION_REQUEST: ("object_key", "interaction"),
    INTERACTION_END: ("object_key",),
    INTERACTION_START: ("room_id", "object_key", "interaction", "player_id", "started_at"),
    INTERACTION_FREE: ("room_id", "object_key", "cooldown_until"),
    INTERACTION_STATE: ("room_id", "interactions"),
    SAVE_PUSH: ("slot", "seq", "total", "size", "data"),
    SAVE_ACK: ("slot", "ok", "reached"),
    SAVE_REQUEST: (),
    TIME_SYNC: ("speed",),
    TIME_READY: ("zone_id",),
    TIME_SPEED: ("speed",),
    ERROR: ("code", "message"),
}

# Fields a message MAY carry in addition to its required set. These are
# server-stamped (origin player/room identity) or client-supplied optional
# data (client_id) and may be omitted on the wire.
OPTIONAL_PAYLOAD_FIELDS = {
    HELLO: ("client_id",),
    EVENT: ("player_id",),
    PRESENCE: ("player_id", "room_id"),
    TRAVEL_REQUEST: ("player_id",),
    TRAVEL_RESPONSE: ("reason",),
    CLOCK_SYNC: ("player_id",),
    OBJECT_UPDATE: ("player_id", "room_id", "zone_id"),
    OBJECT_CLAIM: ("zone_id",),
    OBJECT_RELEASE: ("zone_id",),
    WORLD_STATE: ("zone_id",),
    WORLD_DELTA: ("player_id", "zone_id"),
    OBJECT_OWNERSHIP: ("player_id", "zone_id"),
    INTERACTION_REQUEST: ("args", "affordance_id", "affordance", "target", "zone_id"),
    INTERACTION_END: ("zone_id",),
    INTERACTION_START: ("args", "affordance_id", "affordance", "target", "zone_id"),
    INTERACTION_FREE: ("zone_id",),
    INTERACTION_STATE: ("zone_id",),
    SAVE_PUSH: ("origin",),
    SAVE_ACK: ("message",),
    TIME_SYNC: ("ticks", "player_id", "gate"),
    TIME_READY: ("player_id",),
    TIME_SPEED: ("ticks", "player_id"),
    ERROR: ("ref",),
}

ALLOWED_TOP_LEVEL_KEYS = frozenset(["version", "type", "request_id", "payload"])