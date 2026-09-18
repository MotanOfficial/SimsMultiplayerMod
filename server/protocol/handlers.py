"""Per-message handlers for the server side of the simmp protocol."""

import base64
import os
import tempfile
import time

from simmp import messages as msg
from simmp.constants import (
    CLOCK_SPEED_PAUSED,
    DEFAULT_ROOM_ID,
    MAX_SAVE_CHUNK_BYTES,
    PROTOCOL_VERSION,
)

ERR_ALREADY_REGISTERED = "ALREADY_REGISTERED"
ERR_NOT_REGISTERED = "NOT_REGISTERED"
ERR_UNKNOWN_ROOM = "UNKNOWN_ROOM"
ERR_OBJECT_LOCKED = "OBJECT_LOCKED"
ERR_OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"
ERR_INTERACTION_BUSY = "INTERACTION_BUSY"
ERR_INTERACTION_COOLDOWN = "INTERACTION_COOLDOWN"
ERR_INTERACTION_NOT_HELD = "INTERACTION_NOT_HELD"


class Handlers:
    def __init__(self, server):
        self._server = server
        self._handlers = {
            "HELLO": self._handle_hello,
            "PING": self._handle_ping,
            "PONG": self._handle_pong,
            "JOIN_ROOM": self._handle_join_room,
            "EVENT": self._handle_event,
            "PRESENCE": self._handle_presence,
            "TRAVEL_REQUEST": self._handle_travel_request,
            "TRAVEL_RESPONSE": self._handle_travel_response,
            "TRAVEL_READY": self._handle_travel_ready,
            "CLOCK_SYNC": self._handle_clock_sync,
            "OBJECT_CLAIM": self._handle_object_claim,
            "OBJECT_RELEASE": self._handle_object_release,
            "OBJECT_UPDATE": self._handle_object_update,
            "INTERACTION_REQUEST": self._handle_interaction_request,
            "INTERACTION_END": self._handle_interaction_end,
            "OBJECT_GONE": self._handle_object_gone,
            "SAVE_PUSH": self._handle_save_push,
            "SAVE_REQUEST": self._handle_save_request,
            "FUNDS_SYNC": self._handle_funds_sync,
            "TIME_READY": self._handle_time_ready,
            "TIME_UNREADY": self._handle_time_unready,
            "TIME_SPEED": self._handle_time_speed,
        }
        # Per-room cache of the last completed save push, so a player who
        # joins after the host shared still receives the save immediately
        # instead of waiting for a re-share. Values:
        #   {"slot", "origin", "path", "size", "total", "received", "open"}
        self._save_caches = {}
        self._save_cache_dir = tempfile.mkdtemp(prefix="simmp-save-cache-")

    def get(self, message_type):
        return self._handlers.get(message_type)

    def _zone_of(self, conn, payload=None):
        """The zone a sender's world write belongs to.

        Prefers the zone stamped on the wire (client-tagged writes), falling
        back to the server's own view (ready zone, else presence zone).
        """
        if payload is not None:
            zone_id = payload.get("zone_id")
            if zone_id is not None:
                return zone_id
        player = self._server.session.get_player(conn.player_id)
        if player is None:
            return None
        return self._server.session.player_zone(player)

    async def _require_registered(self, conn, action):
        if conn.player_id is None:
            await conn.send(msg.make_error(ERR_NOT_REGISTERED, "send HELLO before %s" % action))
            return False
        return True

    async def _handle_hello(self, conn, frame):
        if conn.player_id is not None:
            await conn.send(msg.make_error(ERR_ALREADY_REGISTERED, "connection already registered"))
            return

        server = self._server
        session = server.session
        payload = frame["payload"]
        name = payload["client_name"]
        client_id = payload.get("client_id")

        # Identity resume: a returning client_id reuses the same player record
        # (player_id, room, presence dedup state) instead of joining as new.
        player = session.player_for_client_id(client_id) if client_id else None
        resumed = player is not None

        if resumed:
            old_conn = player.connection
            if old_conn is not None and old_conn is not conn and not old_conn.closed:
                server.logger.info(
                    "[MP][NET] Identity %s taken over; closing stale connection",
                    client_id,
                )
                await old_conn.close()
            player.connection = conn
            player.name = name
            player.disconnected_at = None
        else:
            player = session.create_player(conn, name)
            if client_id:
                session.bind_client_id(client_id, player.player_id)

        conn.player_id = player.player_id
        conn.name = player.name

        room_id = player.room_id or DEFAULT_ROOM_ID
        room = session.get_or_create_room(room_id)
        room.members[player.player_id] = player
        player.room_id = room_id
        conn.room_id = room_id

        server.logger.info(
            "[MP][NET] Player %s (%s) %s from %s",
            player.player_id,
            name,
            "resumed" if resumed else "accepted",
            conn.peer_address(),
        )

        await conn.send(msg.make_welcome(player.player_id, room_id, time.time()))
        await conn.send(msg.make_room_state(room_id, room.as_dict()["players"]))
        zone_id = session.player_zone(player)
        if zone_id is None:
            zone_id = session.dominant_room_zone(room_id)
        await conn.send(
            msg.make_world_state(
                room_id,
                server.session.get_world_objects(room_id, zone_id),
                zone_id=zone_id,
            )
        )
        await conn.send(
            msg.make_interaction_state(
                room_id,
                server.session.get_room_interactions(room_id, zone_id),
                zone_id=zone_id,
            )
        )
        await server.broadcast_room(
            room_id,
            msg.make_player_joined(player.player_id, name, room_id),
            exclude={player.player_id},
        )
        player.clock_ready = False
        player.clock_zone = None
        await self.sync_clock(room_id)

    async def _handle_join_room(self, conn, frame):
        if not await self._require_registered(conn, "joining a room"):
            return

        server = self._server
        player = server.session.get_player(conn.player_id)
        room_id = frame["payload"]["room_id"]
        old_room_id, new_room_id = server.session.move_player(player, room_id)
        conn.room_id = new_room_id

        new_room = server.session.get_room(new_room_id)
        server.logger.info(
            "[MP][ROOM] Player %s moved from %s to %s",
            conn.player_id,
            old_room_id,
            new_room_id,
        )

        await conn.send(msg.make_room_state(new_room_id, new_room.as_dict()["players"]))
        await conn.send(msg.make_world_state(new_room_id, server.session.get_world_objects(new_room_id)))
        await conn.send(msg.make_interaction_state(new_room_id, server.session.get_room_interactions(new_room_id)))
        await server.broadcast_room(
            new_room_id,
            msg.make_player_joined(player.player_id, player.name, new_room_id),
            exclude={player.player_id},
        )
        if old_room_id and old_room_id != new_room_id:
            await server.broadcast_room(
                old_room_id,
                msg.make_player_left(player.player_id, old_room_id, "left_room"),
                exclude={player.player_id},
            )
        player.clock_ready = False
        if old_room_id and old_room_id != new_room_id:
            await self.sync_clock(old_room_id)
        await self.sync_clock(new_room_id)

    async def _handle_ping(self, conn, frame):
        client_time = frame["payload"]["client_time"]
        await conn.send(msg.make_pong(client_time, time.time()))

    async def _handle_pong(self, conn, frame):
        self._server.logger.debug("[MP][NET] Player %s answered keep-alive", conn.player_id)

    async def _handle_event(self, conn, frame):
        if not await self._require_registered(conn, "sending events"):
            return

        payload = frame["payload"]
        player = self._server.session.get_player(conn.player_id)
        seq = payload.get("seq", 0)

        # Idempotency: events with an already-seen sequence number (e.g. a
        # resend after a dropped connection) are acked but not re-broadcast.
        if seq > 0 and seq <= player.last_event_seq:
            self._server.logger.info(
                "[MP][SYNC] Player %s re-sent seq %s (drop, already relayed)",
                conn.player_id,
                seq,
            )
            await conn.send(msg.make_event_ack(seq, conn.room_id))
            return
        if seq > 0:
            player.last_event_seq = seq

        self._server.logger.info(
            "[MP][SYNC] Player %s event %r data=%r seq=%s",
            conn.player_id,
            payload["event_type"],
            payload["data"],
            seq,
        )
        await conn.send(msg.make_event_ack(seq, conn.room_id))
        relay = msg.make_event(payload["event_type"], payload["data"], seq, player_id=conn.player_id)
        await self._server.broadcast_room(conn.room_id, relay, exclude={conn.player_id})

    async def _handle_presence(self, conn, frame):
        if not await self._require_registered(conn, "sending presence"):
            return

        payload = frame["payload"]
        player = self._server.session.get_player(conn.player_id)
        presence = {
            "player_id": conn.player_id,
            "room_id": conn.room_id,
            "zone_id": payload["zone_id"],
            "lot_id": payload["lot_id"],
            "timestamp": payload["timestamp"],
            "received_at": time.time(),
        }
        player.presence = presence
        self._server.logger.debug(
            "[MP][SYNC] Player %s presence zone=%s lot=%s",
            conn.player_id,
            payload["zone_id"],
            payload["lot_id"],
        )
        relay = msg.make_presence(
            payload["zone_id"],
            payload["lot_id"],
            payload["timestamp"],
            player_id=conn.player_id,
            room_id=conn.room_id,
        )
        await self._server.broadcast_room(conn.room_id, relay, exclude={conn.player_id})

    async def _handle_travel_request(self, conn, frame):
        if not await self._require_registered(conn, "requesting travel"):
            return
        await self._server.travel.start(conn, frame)

    async def _handle_travel_response(self, conn, frame):
        if not await self._require_registered(conn, "responding to travel"):
            return
        await self._server.travel.respond(conn, frame)

    async def _handle_travel_ready(self, conn, frame):
        if not await self._require_registered(conn, "reporting travel arrival"):
            return
        await self._server.travel.ready(conn, frame)

    async def _handle_clock_sync(self, conn, frame):
        if not await self._require_registered(conn, "sending clock sync"):
            return

        payload = frame["payload"]
        player = self._server.session.get_player(conn.player_id)
        player.clock_sync = {
            "player_id": conn.player_id,
            "room_id": conn.room_id,
            "zone_id": payload["zone_id"],
            "absolute_ticks": payload["absolute_ticks"],
            "real_time": payload["real_time"],
            "clock_speed": payload["clock_speed"],
        }
        self._server.logger.debug(
            "[MP][SYNC] Player %s clock zone=%s ticks=%s real=%s speed=%s",
            conn.player_id,
            payload["zone_id"],
            payload["absolute_ticks"],
            payload["real_time"],
            payload["clock_speed"],
        )
        relay = msg.make_clock_sync(
            payload["zone_id"],
            payload["absolute_ticks"],
            payload["real_time"],
            payload["clock_speed"],
            player_id=conn.player_id,
        )
        await self._server.broadcast_room(conn.room_id, relay, exclude={conn.player_id})

    async def _handle_object_claim(self, conn, frame):
        if not await self._require_registered(conn, "claiming objects"):
            return

        server = self._server
        room_id = conn.room_id
        payload = frame["payload"]
        key = payload["key"]
        zone_id = self._zone_of(conn, payload)
        ok, _, prev_owner = server.session.claim_object(room_id, key, conn.player_id, zone_id)
        if not ok:
            await conn.send(
                msg.make_error(
                    ERR_OBJECT_LOCKED,
                    "object %r is locked by player %s" % (key, prev_owner),
                    ref=key,
                )
            )
            return
        server.logger.info(
            "[MP][SYNC] Player %s claimed object %r in room %s zone %s",
            conn.player_id,
            key,
            room_id,
            zone_id,
        )
        await conn.send(msg.make_object_claim_ack(key, conn.player_id))
        await server.broadcast_zone(
            room_id,
            zone_id,
            msg.make_object_ownership(room_id, key, conn.player_id, player_id=conn.player_id, zone_id=zone_id),
            exclude={conn.player_id},
        )

    async def _handle_object_release(self, conn, frame):
        if not await self._require_registered(conn, "releasing objects"):
            return

        server = self._server
        room_id = conn.room_id
        payload = frame["payload"]
        key = payload["key"]
        zone_id = self._zone_of(conn, payload)
        released = server.session.release_object(room_id, key, conn.player_id, zone_id)
        server.logger.info(
            "[MP][SYNC] Player %s released object %r in room %s zone %s",
            conn.player_id,
            key,
            room_id,
            zone_id,
        )
        await conn.send(msg.make_object_claim_ack(key, None))
        if released:
            await server.broadcast_zone(
                room_id,
                zone_id,
                msg.make_object_ownership(room_id, key, None, player_id=conn.player_id, zone_id=zone_id),
                exclude={conn.player_id},
            )

    async def _handle_object_update(self, conn, frame):
        if not await self._require_registered(conn, "sending world updates"):
            return

        server = self._server
        session = server.session
        room_id = conn.room_id
        payload = frame["payload"]
        zone_id = self._zone_of(conn, payload)
        deltas = []
        for entry in payload["objects"]:
            status, detail = session.apply_world_update(
                room_id, entry["key"], entry["fields"], conn.player_id, zone_id
            )
            if status == "locked":
                await conn.send(
                    msg.make_error(
                        ERR_OBJECT_LOCKED,
                        "object %r is locked by player %s" % (entry["key"], detail),
                        ref=entry["key"],
                    )
                )
                return
            if status == "not_found":
                await conn.send(
                    msg.make_error(
                        ERR_OBJECT_NOT_FOUND,
                        "object %r was never claimed; claim it first" % entry["key"],
                    )
                )
                return
            if detail:
                deltas.append({"key": entry["key"], "fields": detail})

        if deltas:
            seq = session.next_world_seq(room_id, zone_id)
            server.logger.info(
                "[MP][SYNC] Player %s updated %s object(s) in room %s zone %s (world seq %s)",
                conn.player_id,
                len(deltas),
                room_id,
                zone_id,
                seq,
            )
            await server.broadcast_zone(
                room_id,
                zone_id,
                msg.make_world_delta(room_id, seq, deltas, player_id=conn.player_id, zone_id=zone_id),
                exclude={conn.player_id},
            )

    async def _handle_object_gone(self, conn, frame):
        """A lot object was deleted (build/buy): drop it and relay the removal.

        Only the current owner (or an unclaimed object) may be removed, so a
        peer can't delete someone else's actively-mirrored world entry. The
        removal is broadcast to the zone so every peer deletes its local copy
        of that object (same save, same def+position).
        """
        if not await self._require_registered(conn, "removing world objects"):
            return
        server = self._server
        room_id = conn.room_id
        payload = frame["payload"]
        key = payload["key"]
        zone_id = self._zone_of(conn, payload)
        removed = server.session.remove_world_object(room_id, key, zone_id)
        if removed is not None and removed.owner is not None and removed.owner != conn.player_id:
            # Not our object to delete: restore the entry and refuse.
            objects = server.session.get_world_object(room_id, key, zone_id)
            if objects is None:
                server.session.claim_object(room_id, key, removed.owner, zone_id)
                server.session.apply_world_update(
                    room_id, key, removed.fields, removed.owner, zone_id
                )
            await conn.send(
                msg.make_error(
                    ERR_OBJECT_LOCKED,
                    "object %r is owned by player %s; cannot remove it" % (key, removed.owner),
                    ref=key,
                )
            )
            return
        server.logger.info(
            "[MP][SYNC] Object %r removed from room %s zone %s by player %s",
            key,
            room_id,
            zone_id,
            conn.player_id,
        )
        await server.broadcast_zone(
            room_id,
            zone_id,
            msg.make_object_gone(key),
            exclude={conn.player_id},
        )

    async def _handle_funds_sync(self, conn, frame):
        """Echo-style household balance broadcast (including to the sender).

        Every client applies the absolute balance, so whoever spent/received
        simoleons last converges everyone onto that number.
        """
        if not await self._require_registered(conn, "syncing household funds"):
            return
        server = self._server
        balance = frame["payload"]["balance"]
        room_id = conn.room_id
        server.session.set_room_funds(room_id, balance, conn.player_id)
        server.logger.info(
            "[MP][FUNDS] Player %s set room %s balance to %s simoleons",
            conn.player_id,
            room_id,
            balance,
        )
        await server.broadcast_room(
            room_id,
            msg.make_funds_sync(balance, player_id=conn.player_id),
        )

    async def _handle_time_unready(self, conn, frame):
        """A player is no longer in a playable zone (CAS, manage worlds, menu).

        The room re-gates PAUSED so nobody plays ahead while they are away;
        they send TIME_READY again when they are back in a running zone.
        """
        if not await self._require_registered(conn, "reporting unready"):
            return
        server = self._server
        room_id = conn.room_id
        server.session.set_clock_unready(conn.player_id)
        server.logger.info(
            "[MP][SYNC] Player %s unready (left playable zone); room %s re-gating",
            conn.player_id,
            room_id,
        )
        await self.sync_clock(room_id)

    async def _handle_interaction_request(self, conn, frame):
        if not await self._require_registered(conn, "proposing interactions"):
            return

        server = self._server
        room_id = conn.room_id
        payload = frame["payload"]
        key = payload["object_key"]
        interaction = payload["interaction"]
        args = payload.get("args")
        affordance = payload.get("affordance")
        affordance_id = payload.get("affordance_id")
        target = payload.get("target")
        zone_id = self._zone_of(conn, payload)
        status, detail = server.session.request_interaction(
            room_id,
            key,
            conn.player_id,
            interaction,
            args=args,
            affordance=affordance,
            affordance_id=affordance_id,
            target=target,
            zone_id=zone_id,
        )
        if status == "busy":
            await conn.send(
                msg.make_error(
                    ERR_INTERACTION_BUSY,
                    "object %r is already in use by player %s" % (key, detail),
                    ref=key,
                )
            )
            return
        if status == "cooldown":
            await conn.send(
                msg.make_error(
                    ERR_INTERACTION_COOLDOWN,
                    "object %r is on cooldown until %s" % (key, detail),
                    ref=key,
                )
            )
            return
        server.logger.info(
            "[MP][SYNC] Player %s started interaction %r on %r in room %s zone %s (aff=%r aff_id=%s target=%r)",
            conn.player_id,
            interaction,
            key,
            room_id,
            zone_id,
            affordance,
            affordance_id,
            target,
        )
        # Echoed to the whole zone (including the requester) so every mirror
        # - including the sender's - self-heals from this single broadcast.
        await server.broadcast_zone(
            room_id,
            zone_id,
            msg.make_interaction_start(
                room_id,
                key,
                interaction,
                conn.player_id,
                detail["started_at"],
                args=args,
                affordance=detail.get("affordance"),
                affordance_id=detail.get("affordance_id"),
                target=detail.get("target"),
                zone_id=zone_id,
            ),
        )

    async def _handle_interaction_end(self, conn, frame):
        if not await self._require_registered(conn, "ending interactions"):
            return

        server = self._server
        room_id = conn.room_id
        payload = frame["payload"]
        key = payload["object_key"]
        zone_id = self._zone_of(conn, payload)
        status, cooldown_until = server.session.end_interaction(
            room_id, key, conn.player_id, server.interaction_cooldown, zone_id=zone_id
        )
        if status == "not_held":
            await conn.send(
                msg.make_error(
                    ERR_INTERACTION_NOT_HELD,
                    "you do not hold object %r" % key,
                    ref=key,
                )
            )
            return
        server.logger.info(
            "[MP][SYNC] Player %s ended interaction on %r in room %s zone %s",
            conn.player_id,
            key,
            room_id,
            zone_id,
        )
        await server.broadcast_zone(
            room_id,
            zone_id,
            msg.make_interaction_free(room_id, key, cooldown_until, zone_id=zone_id),
        )

    async def sync_clock(self, room_id):
        """Re-evaluate the gate and broadcast the authoritative clock to all members."""
        server = self._server
        snapshot = server.session.clock_snapshot(room_id)
        if snapshot is None:
            return
        server.logger.info(
            "[MP][SYNC] clock room=%s speed=%s desired=%s by=%s ready=%s/%s gate=%s",
            room_id,
            snapshot["speed"],
            snapshot["desired"],
            snapshot["by_player"],
            len(snapshot["ready"]),
            len(snapshot["participants"]),
            "open" if not snapshot["gate"] else "closed",
        )
        await server.broadcast_room(
            room_id,
            msg.make_time_sync(
                snapshot["speed"],
                ticks=snapshot["ticks"],
                player_id=snapshot["by_player"],
                gate=snapshot["gate"],
            ),
        )

    async def _handle_time_ready(self, conn, frame):
        if not await self._require_registered(conn, "reporting time readiness"):
            return

        server = self._server
        payload = frame["payload"]
        zone_id = payload["zone_id"]
        player = server.session.get_player(conn.player_id)
        if player.clock_zone is not None and player.clock_zone != zone_id:
            if player.clock_ready:
                old_zone = player.clock_zone
                world_keys, interaction_keys = server.session.release_player_zone(
                    conn.player_id, conn.room_id, old_zone, server.interaction_cooldown
                )
                for key in world_keys:
                    await server.broadcast_zone(
                        conn.room_id,
                        old_zone,
                        msg.make_object_ownership(
                            conn.room_id, key, None, player_id=conn.player_id, zone_id=old_zone
                        ),
                        exclude={conn.player_id},
                    )
                for key, cooldown_until in interaction_keys:
                    await server.broadcast_zone(
                        conn.room_id,
                        old_zone,
                        msg.make_interaction_free(
                            conn.room_id, key, cooldown_until, zone_id=old_zone
                        ),
                        exclude={conn.player_id},
                    )
                server.logger.info(
                    "[MP][SYNC] Player %s left zone %s -> %s; released %s object(s), %s interaction(s)",
                    conn.player_id,
                    old_zone,
                    zone_id,
                    len(world_keys),
                    len(interaction_keys),
                )
                server.session.clear_room_clock_ready(conn.room_id)
                server.logger.info(
                    "[MP][SYNC] Player %s left zone %s -> %s; room re-gating",
                    conn.player_id,
                    old_zone,
                    zone_id,
                )
        player.clock_zone = zone_id
        server.session.set_clock_ready(conn.player_id)
        server.logger.info(
            "[MP][SYNC] Player %s time-ready zone=%s",
            conn.player_id,
            zone_id,
        )
        # Flip the traveling client's mirror to the new zone's world.
        await conn.send(
            msg.make_world_state(
                conn.room_id,
                server.session.get_world_objects(conn.room_id, zone_id),
                zone_id=zone_id,
            )
        )
        await conn.send(
            msg.make_interaction_state(
                conn.room_id,
                server.session.get_room_interactions(conn.room_id, zone_id),
                zone_id=zone_id,
            )
        )
        await self.sync_clock(conn.room_id)

    async def _handle_time_speed(self, conn, frame):
        if not await self._require_registered(conn, "changing clock speed"):
            return

        server = self._server
        room = server.session.get_room(conn.room_id)
        if room is None:
            await conn.send(
                msg.make_error(ERR_UNKNOWN_ROOM, "you are not in a room")
            )
            return
        payload = frame["payload"]
        speed = payload["speed"]
        room.clock["desired"] = speed
        room.clock["by_player"] = conn.player_id
        if payload.get("ticks") is not None:
            room.clock["ticks"] = payload["ticks"]
        server.logger.info(
            "[MP][SYNC] Player %s set clock speed %s",
            conn.player_id,
            speed,
        )
        await self.sync_clock(conn.room_id)

    async def _handle_save_push(self, conn, frame):
        if not await self._require_registered(conn, "pushing save files"):
            return

        server = self._server
        room_id = conn.room_id
        payload = frame["payload"]
        slot = payload["slot"]
        seq = payload["seq"]
        total = payload["total"]
        size = payload["size"]
        chunk = _decode_chunk(payload["data"])
        self._cache_save_chunk(room_id, slot, seq, total, size, chunk, conn.player_id)

        # Relay every chunk to the rest of the room, then ack the sender with
        # the number of OTHER players that got it. A single player alone in the
        # room still receives the `reached=0` ack so the push protocol can
        # finish cleanly (the save is then written by its own mod, if any), and
        # the cached copy lets players who connect later still retrieve it.
        relay = msg.make_save_push(
            slot,
            seq,
            total,
            size,
            chunk,
            origin=conn.player_id,
        )
        members = server.session.get_room(room_id)
        peers = [player for player in list(members.members.values()) if player.player_id != conn.player_id]
        server.logger.info(
            "[MP][SYNC] Player %s push %s chunk %s/%s (%.1f KiB) to %s peer(s) in room %s",
            conn.player_id,
            slot,
            seq,
            total,
            size / 1024.0 if size else 0.0,
            len(peers),
            room_id,
        )
        await server.broadcast_room(
            room_id,
            relay,
            exclude={conn.player_id},
        )
        await conn.send(msg.make_save_ack(slot, True, len(peers), seq=seq, total=total))

    def _cache_save_chunk(self, room_id, slot, seq, total, size, chunk, origin):
        """Accumulate one SAVE_PUSH chunk into the room's cached save file.

        The cache holds only the *latest* completed slot per room. Starting a
        new slot (or a changed chunk shape) resets the file.
        """
        entry = self._save_caches.get(room_id)
        if entry is None or entry.get("slot") != slot or entry.get("total") != total or entry.get("size") != size:
            self._close_save_cache(entry)
            path = os.path.join(self._save_cache_dir, room_id, slot)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            entry = {
                "slot": slot,
                "origin": origin,
                "path": path,
                "size": size,
                "total": total,
                "received": 0,
                "open": True,
                "handle": open(path, "wb"),
            }
            self._save_caches[room_id] = entry
        if not entry["open"]:
            return
        entry["handle"].write(chunk)
        entry["received"] = seq
        if seq >= total:
            self._close_save_cache(entry)

    @staticmethod
    def _close_save_cache(entry):
        if not entry:
            return
        try:
            if entry.get("open"):
                entry["handle"].close()
        finally:
            entry["open"] = False

    async def _handle_save_request(self, conn, frame):
        """Replay the room's cached save to a player (e.g. a late joiner)."""
        if not await self._require_registered(conn, "requesting save files"):
            return
        room_id = conn.room_id
        entry = self._save_caches.get(room_id)
        # Only replay a fully-received save (handle closed). A partial cache
        # belongs to an in-flight push that is still broadcasting to the room.
        if not entry or entry.get("open") or not os.path.isfile(entry["path"]):
            return
        try:
            with open(entry["path"], "rb") as handle:
                data = handle.read()
        except OSError:
            return
        slot = entry["slot"]
        total = max(1, (len(data) + MAX_SAVE_CHUNK_BYTES - 1) // MAX_SAVE_CHUNK_BYTES)
        for seq in range(1, total + 1):
            await conn.send(
                msg.make_save_push(
                    slot,
                    seq,
                    total,
                    len(data),
                    data[(seq - 1) * MAX_SAVE_CHUNK_BYTES : seq * MAX_SAVE_CHUNK_BYTES],
                    origin=entry.get("origin"),
                )
            )
        self._server.logger.info(
            "[MP][SYNC] Replayed cached save %r (%.1f KiB) to player %s in room %s",
            slot,
            len(data) / 1024.0,
            conn.player_id,
            room_id,
        )


def _decode_chunk(data):
    import base64

    try:
        return base64.b64decode(data)
    except Exception:
        return b""