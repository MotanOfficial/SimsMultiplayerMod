"""simmp - shared multiplayer protocol for the Sims 4 multiplayer mod.

This package is shared between the server and the Sims 4 client mod.
Keep it dependency-free and compatible with the Python version shipped
inside The Sims 4 (3.7.x).
"""

from simmp.constants import (  # noqa: F401
    PROTOCOL_VERSION,
    DEFAULT_ROOM_ID,
    MAX_FRAME_BYTES,
    MESSAGE_TYPES,
    HELLO,
    WELCOME,
    PING,
    PONG,
    JOIN_ROOM,
    ROOM_STATE,
    PLAYER_JOINED,
    PLAYER_LEFT,
    EVENT,
    ERROR,
)
from simmp.validation import ProtocolError, validate_message  # noqa: F401
from simmp import framing  # noqa: F401