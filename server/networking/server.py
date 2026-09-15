"""Async TCP server that accepts simmp clients and routes messages."""

import asyncio
import json
import logging
import os
import time

from simmp import framing, messages as msg
from simmp.constants import MAX_FRAME_BYTES
from simmp.validation import ProtocolError, validate_message
from server.networking.connection import Connection, ConnectionClosed
from server.protocol.handlers import Handlers
from server.state.session import Session
from server.travel.coordinator import TravelCoordinator


class MPServer:
    def __init__(
        self,
        host,
        port,
        logger=None,
        stale_timeout=15.0,
        presence_ttl=30.0,
        reap_interval=5.0,
        interaction_cooldown=5.0,
        interaction_max_duration=300.0,
        ghost_ownership_ttl=60.0,
        status_file=None,
    ):
        self.host = host
        self.port = port
        self.logger = logger or logging.getLogger("simmp.server")
        self.session = Session()
        self.handlers = Handlers(self)
        self.travel = TravelCoordinator(self, logger=self.logger)
        self.connections = set()
        self._server = None
        self.stale_timeout = stale_timeout
        self.presence_ttl = presence_ttl
        self.interaction_cooldown = interaction_cooldown
        self.interaction_max_duration = interaction_max_duration
        self.ghost_ownership_ttl = ghost_ownership_ttl
        self._reap_interval = reap_interval
        self._reaper_task = None
        self.status_file = status_file
        self._status_task = None
        self._started_at = time.time()

    async def start(self):
        self._server = await asyncio.start_server(
            self._on_connection,
            self.host,
            self.port,
            limit=MAX_FRAME_BYTES + 4,
        )
        sock = self._server.sockets[0]
        self.host, self.port = sock.getsockname()[:2]
        self.logger.info("[MP][NET] Listening on %s:%s", self.host, self.port)
        self._reaper_task = asyncio.get_running_loop().create_task(self._reaper())
        if self.status_file:
            self._status_task = asyncio.get_running_loop().create_task(self._status_writer())
        return self

    async def serve_forever(self):
        await self._server.serve_forever()

    async def stop(self):
        if self._status_task is not None:
            task = self._status_task
            self._status_task = None
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), timeout=2)
            except Exception:
                pass
        self._write_status()
        if self._reaper_task is not None:
            task = self._reaper_task
            self._reaper_task = None
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), timeout=2)
            except Exception:
                pass
        if self._server is not None:
            self._server.close()
            try:
                await asyncio.wait_for(self._server.wait_closed(), timeout=3)
            except Exception:
                pass
        for conn in list(self.connections):
            await conn.close()

    async def broadcast_room(self, room_id, message, exclude=None):
        room = self.session.get_room(room_id)
        if room is None:
            return
        exclude = exclude or set()
        tasks = []
        for player in list(room.members.values()):
            if player.player_id in exclude:
                continue
            tasks.append(self._safe_send(player, message))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_zone(self, room_id, zone_id, message, exclude=None):
        """Broadcast to room members in `zone_id` (unknown-zone members get it too).

        Zone-scoped delivery: each receiver sees only the replicated world of
        the zone they are currently in. Members who have not reported a zone
        yet (join bootstrap, still gated) receive everything until their first
        zone is known.
        """
        room = self.session.get_room(room_id)
        if room is None:
            return
        exclude = exclude or set()
        tasks = []
        for player in list(room.members.values()):
            if player.player_id in exclude:
                continue
            if self.session.player_zone(player) not in (None, zone_id):
                continue
            tasks.append(self._safe_send(player, message))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_send(self, player, message):
        try:
            await player.connection.send(message)
        except ConnectionClosed as exc:
            self.logger.warning("[MP][NET] Failed to deliver to player %s: %s", player.player_id, exc)

    async def _on_connection(self, reader, writer):
        conn = Connection(reader, writer, self.logger)
        self.connections.add(conn)
        self.logger.info("[MP][NET] Connection from %s", conn.peer_address())
        try:
            while True:
                frame = await framing.read_frame(reader, limit=MAX_FRAME_BYTES)
                if frame is None:
                    break
                conn.last_activity = time.monotonic()
                await self._dispatch(conn, frame)
        except framing.FrameError as exc:
            self.logger.warning("[MP][ERROR] Malformed frame from %s: %s", conn.peer_address(), exc)
            try:
                await conn.send(msg.make_error("MALFORMED", str(exc)))
            except ConnectionClosed:
                pass
        except ConnectionClosed:
            pass
        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger.exception("[MP][ERROR] Handler error for connection %s", conn.peer_address())
        finally:
            self.connections.discard(conn)
            await self._on_disconnect(conn)
            await conn.close()

    async def _dispatch(self, conn, frame):
        try:
            validate_message(frame)
        except ProtocolError as exc:
            self.logger.warning(
                "[MP][ERROR] Rejected %s from player %s: %s",
                frame.get("type"),
                conn.player_id,
                exc,
            )
            try:
                await conn.send(msg.make_error(exc.code, str(exc)))
            except ConnectionClosed:
                pass
            return

        handler = self.handlers.get(frame["type"])
        if handler is None:
            self.logger.warning("[MP][ERROR] No handler for %s from player %s", frame["type"], conn.player_id)
            try:
                await conn.send(msg.make_error("UNKNOWN_TYPE", "no handler for %s" % frame["type"]))
            except ConnectionClosed:
                pass
            return
        await handler(conn, frame)

    def _status_snapshot(self):
        """Compact JSONable state for external tools (GUI/dev console)."""
        players = []
        rooms = []
        for room in self.session.rooms.values():
            members = [player.as_dict() for player in room.members.values()]
            entry = {"room_id": room.room_id, "players": members}
            clock = self.session.clock_snapshot(room.room_id)
            if clock is not None:
                entry["clock"] = clock
            rooms.append(entry)
        for player in self.session.players.values():
            players.append(
                {
                    "player_id": player.player_id,
                    "name": player.name,
                    "connected": player.connected,
                    "room_id": player.room_id,
                    "joined_at": player.joined_at,
                    "presence": player.presence,
                }
            )
        return {
            "since": self._started_at,
            "server_time": time.time(),
            "host": self.host,
            "port": self.port,
            "connections": len(self.connections),
            "rooms": rooms,
            "players": players,
        }

    def _write_status(self):
        if not self.status_file:
            return
        try:
            directory = os.path.dirname(os.path.abspath(self.status_file))
            temp = os.path.join(directory, ".simmp-status.tmp")
            with open(temp, "w", encoding="utf-8") as handle:
                json.dump(self._status_snapshot(), handle, sort_keys=True)
            os.replace(temp, self.status_file)
        except Exception:
            pass

    async def _status_writer(self):
        """Rewrite the status file every second so UIs see changes quickly."""
        try:
            while True:
                self._write_status()
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            return

    async def _on_disconnect(self, conn):
        if conn.player_id is None:
            return
        result = self.session.disconnect_player(conn.player_id, conn)
        if result is None:
            # Identity was re-adopted by another connection; nothing to tear down.
            return
        room_id, name, player_id = result
        self.logger.info("[MP][NET] Player %s (%s) disconnected", player_id, name)
        self.travel.cancel_on_disconnect(player_id)
        # Ownership is intentionally NOT released here: the player becomes a
        # ghost for `ghost_ownership_ttl` seconds, so a quick reconnect with
        # the same client_id resumes world ownership and held interactions
        # exactly as they were. The reaper evicts ghosts after the TTL.
        if room_id:
            await self.broadcast_room(
                room_id,
                msg.make_player_left(player_id, room_id, "disconnected"),
                exclude={player_id},
            )
            # A mid-session disconnect auto-pauses the room: the disconnected
            # player stays a participant (ghost) and is not ready, so the clock
            # gate broadcasts PAUSED until they rejoin and signal readiness.
            await self.handlers.sync_clock(room_id)

    async def _reaper(self):
        """Periodic housekeeping: close idle connections and expire presence."""
        try:
            while True:
                await asyncio.sleep(self._reap_interval)
                now = time.monotonic()
                for conn in list(self.connections):
                    if conn.closed:
                        continue
                    if now - conn.last_activity > self.stale_timeout:
                        self.logger.info(
                            "[MP][NET] Closing connection %s (idle %.1fs)",
                            conn.peer_address(),
                            now - conn.last_activity,
                        )
                        await conn.close()
                self.session.expire_presence(self.presence_ttl)
                for (room_id, zone_id), released in self.session.expire_interactions(
                    self.interaction_max_duration, self.interaction_cooldown
                ).items():
                    for key, cooldown_until in released:
                        self.logger.info(
                            "[MP][SYNC] Auto-released interaction on %r in room %s zone %s (duration exceeded)",
                            key,
                            room_id,
                            zone_id,
                        )
                        await self.broadcast_zone(
                            room_id,
                            zone_id,
                            msg.make_interaction_free(room_id, key, cooldown_until, zone_id=zone_id),
                        )
                released = self.session.expire_ghosts(
                    self.ghost_ownership_ttl, self.interaction_cooldown
                )
                for room_id, zone_id, key, cooldown_until in released["interactions"]:
                        self.logger.info(
                            "[MP][SYNC] Released ghost interaction on %r in room %s zone %s (identity evicted)",
                            key,
                            room_id,
                            zone_id,
                        )
                        await self.broadcast_zone(
                            room_id,
                            zone_id,
                            msg.make_interaction_free(room_id, key, cooldown_until, zone_id=zone_id),
                        )
                for room_id, zone_id, key, player_id in released["world"]:
                    self.logger.info(
                        "[MP][SYNC] Released ghost-owned object %r in room %s zone %s (identity evicted)",
                        key,
                        room_id,
                        zone_id,
                    )
                    await self.broadcast_zone(
                        room_id,
                        zone_id,
                        msg.make_object_ownership(
                            room_id, key, None, player_id=player_id, zone_id=zone_id
                        ),
                        exclude={player_id},
                    )
                for player_id in released["players"]:
                    self.logger.info("[MP][NET] Evicted ghost player %s", player_id)
                if released["players"]:
                    # A reconnected-eligible slot vanished: re-evaluate the
                    # clock gate so remaining players can resume playing.
                    for room_id in list(self.session.rooms.keys()):
                        await self.handlers.sync_clock(room_id)
        except asyncio.CancelledError:
            return