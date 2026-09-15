"""Frame encoding for the simmp protocol.

Wire format: 4-byte big-endian payload length followed by a UTF-8 JSON
body. The framing is intentionally small and version-independent so it can
be replaced with a binary codec later without changing the rest of the
project.
"""

try:
    import asyncio
except ImportError:  # the game's embedded Python has no asyncio
    asyncio = None
import json
import struct

from simmp.constants import MAX_FRAME_BYTES

_HEADER = struct.Struct(">I")
_HEADER_SIZE = _HEADER.size


class FrameError(ValueError):
    """Raised when a frame cannot be encoded or decoded."""


def encode(message, limit=MAX_FRAME_BYTES):
    data = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(data) > limit:
        raise FrameError("frame of %s bytes exceeds limit of %s" % (len(data), limit))
    return _HEADER.pack(len(data)) + data


def decode(data):
    if len(data) < _HEADER_SIZE:
        raise FrameError("frame shorter than header")
    (length,) = _HEADER.unpack_from(data)
    if length != len(data) - _HEADER_SIZE:
        raise FrameError("length header %s does not match body of %s bytes" % (length, len(data) - _HEADER_SIZE))
    if length > MAX_FRAME_BYTES:
        raise FrameError("frame of %s bytes exceeds limit" % length)
    try:
        body = data[_HEADER_SIZE:]
        message = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FrameError("invalid JSON frame: %s" % exc) from exc
    if not isinstance(message, dict):
        raise FrameError("frame JSON must be an object")
    return message


async def read_frame(reader, limit=MAX_FRAME_BYTES):
    if asyncio is None:
        raise FrameError("asyncio is not available in this interpreter")
    try:
        header = await reader.readexactly(_HEADER_SIZE)
    except asyncio.IncompleteReadError:
        return None
    except (ConnectionError, OSError):
        return None

    (length,) = _HEADER.unpack(header)
    if length > limit:
        raise FrameError("frame of %s bytes exceeds limit of %s" % (length, limit))

    try:
        body = await reader.readexactly(length)
    except asyncio.IncompleteReadError:
        return None
    except (ConnectionError, OSError):
        return None

    try:
        message = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FrameError("invalid JSON frame: %s" % exc) from exc
    if not isinstance(message, dict):
        raise FrameError("frame JSON must be an object")
    return message


class FrameDecoder:
    """Incremental synchronous frame decoder for threaded socket clients.

    The game's embedded Python ships no `asyncio`, so the client engine reads
    raw socket bytes and feeds them here; `feed()` returns every complete
    message decoded from the bytes given so far, buffering partial frames.
    """

    def __init__(self, limit=MAX_FRAME_BYTES):
        self._buffer = b""
        self._limit = limit

    def feed(self, data):
        self._buffer += data
        messages = []
        while len(self._buffer) >= _HEADER_SIZE:
            (length,) = _HEADER.unpack_from(self._buffer)
            if length > self._limit:
                self._buffer = b""
                raise FrameError("frame of %s bytes exceeds limit of %s" % (length, self._limit))
            if len(self._buffer) < _HEADER_SIZE + length:
                break
            body = self._buffer[_HEADER_SIZE:_HEADER_SIZE + length]
            self._buffer = self._buffer[_HEADER_SIZE + length:]
            try:
                message = json.loads(body.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise FrameError("invalid JSON frame: %s" % exc) from exc
            if not isinstance(message, dict):
                raise FrameError("frame JSON must be an object")
            messages.append(message)
        return messages