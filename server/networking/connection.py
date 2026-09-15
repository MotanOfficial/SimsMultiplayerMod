"""Per-connection wrapper around an asyncio stream."""

import asyncio
import time

from simmp import framing
from simmp.constants import MAX_FRAME_BYTES  # noqa: F401


class ConnectionClosed(Exception):
    pass


class Connection:
    def __init__(self, reader, writer, logger):
        self._reader = reader
        self._writer = writer
        self._logger = logger
        self.player_id = None
        self.name = None
        self.room_id = None
        self.closed = False
        self.last_activity = time.monotonic()

    @property
    def reader(self):
        return self._reader

    def peer_address(self):
        try:
            return self._writer.get_extra_info("peername")
        except Exception:
            return None

    async def send(self, message):
        if self.closed:
            raise ConnectionClosed("connection closed")
        try:
            self._writer.write(framing.encode(message))
            await self._writer.drain()
        except (ConnectionError, OSError) as exc:
            self.closed = True
            raise ConnectionClosed(str(exc)) from exc

    async def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self._writer.close()
        except Exception:
            pass
        try:
            await asyncio.wait_for(self._writer.wait_closed(), timeout=2)
        except Exception:
            pass