"""Server-side travel coordinator (M3).

One TravelSession is active per room at a time. The initiator's room
membership defines who travels: everyone in the room except the initiator is
invited, and travel only begins once every invitee has accepted. All-or-
nothing: any decline aborts, and the coordinator tears the session down when
a member drops, a deadline passes, or a newer request supersedes it.

States: PENDING (inviting) -> TRAVELING (awaiting READY) -> COMPLETE/ABORTED.
"""

import asyncio
import logging

from simmp import messages as msg


class TravelSession:
    PENDING = "pending"
    TRAVELING = "traveling"
    COMPLETE = "complete"
    ABORTED = "aborted"

    def __init__(self, request_id, zone_id, room_id, requester_id):
        self.request_id = request_id
        self.zone_id = zone_id
        self.room_id = room_id
        self.requester_id = requester_id
        self.members = set()
        self.invited = set()
        self.accepted = set()
        self.ready = set()
        self.state = self.PENDING
        self.timeout_task = None

    @property
    def active(self):
        return self.state in (self.PENDING, self.TRAVELING)


class TravelCoordinator:
    def __init__(self, server, logger=None, invite_timeout=15.0, ready_timeout=30.0):
        self._server = server
        self.logger = logger or logging.getLogger("simmp.server.travel")
        self.invite_timeout = invite_timeout
        self.ready_timeout = ready_timeout
        self._active = {}

    def active_session(self, room_id):
        return self._active.get(room_id)

    async def start(self, conn, frame):
        room_id = conn.room_id
        zone_id = frame["payload"]["zone_id"]
        requester_id = conn.player_id

        old = self._active.get(room_id)
        if old is not None and old.active:
            self.logger.info("[MP][TRAVEL] Superseding travel %s in room %s", old.request_id, room_id)
            await self.abort(old, "superseded")

        session = TravelSession(frame["request_id"], zone_id, room_id, requester_id)
        self._active[room_id] = session

        room = self._server.session.get_room(room_id)
        members = {pid for pid, p in room.members.items() if pid == requester_id or p.connected}
        session.members = members
        session.invited = members - {requester_id}

        self.logger.info(
            "[MP][TRAVEL] Player %s requests travel to zone %s (room %s, %s invited)",
            requester_id,
            zone_id,
            room_id,
            len(session.invited),
        )

        for pid in sorted(session.invited):
            player = self._server.session.get_player(pid)
            if player is None:
                continue
            await self._send(
                player,
                msg.make_travel_invite(
                    zone_id,
                    requester_id,
                    self._requester_name(requester_id),
                    request_id_value=session.request_id,
                ),
            )

        if not session.invited:
            await self._begin(session)
        else:
            self._set_timeout(session, self.invite_timeout, "invite")

    async def respond(self, conn, frame):
        session = self._active.get(conn.room_id)
        if session is None or not session.active or session.request_id != frame["request_id"]:
            return
        if session.state != TravelSession.PENDING:
            return
        if conn.player_id not in session.invited:
            return

        player = self._server.session.get_player(conn.player_id)
        if frame["payload"]["accepted"]:
            session.accepted.add(conn.player_id)
            self.logger.info("[MP][TRAVEL] Player %s accepted travel to zone %s", conn.player_id, session.zone_id)
        else:
            reason = frame["payload"].get("reason") or "declined"
            who = player.name if player is not None else str(conn.player_id)
            self.logger.info("[MP][TRAVEL] Player %s declined travel: %s", conn.player_id, reason)
            await self.abort(session, "declined by %s (%s)" % (who, reason))
            return

        if session.accepted == session.invited:
            await self._begin(session)

    async def ready(self, conn, frame):
        session = self._active.get(conn.room_id)
        if session is None or not session.active or session.state != TravelSession.TRAVELING:
            return
        if frame["request_id"] != session.request_id or conn.player_id not in session.members:
            return
        if frame["payload"]["zone_id"] != session.zone_id:
            self.logger.info(
                "[MP][TRAVEL] Player %s READY for wrong zone %s (expected %s)",
                conn.player_id,
                frame["payload"]["zone_id"],
                session.zone_id,
            )
            await self.abort(session, "player reached wrong zone")
            return

        session.ready.add(conn.player_id)
        self.logger.info(
            "[MP][TRAVEL] Player %s ready in zone %s (%s/%s)",
            conn.player_id,
            session.zone_id,
            len(session.ready),
            len(session.members),
        )
        if session.ready == session.members:
            await self.complete(session)

    def _requester_name(self, requester_id):
        player = self._server.session.get_player(requester_id)
        return player.name if player is not None else str(requester_id)

    async def _begin(self, session):
        session.state = TravelSession.TRAVELING
        self.logger.info("[MP][TRAVEL] Travel %s to zone %s begins", session.request_id, session.zone_id)
        await self._broadcast_room(
            session.room_id,
            msg.make_travel_begin(session.zone_id, request_id_value=session.request_id),
        )
        self._set_timeout(session, self.ready_timeout, "ready")

    async def complete(self, session):
        session.state = TravelSession.COMPLETE
        self._cancel_timeout(session)
        self.logger.info("[MP][TRAVEL] Travel %s to zone %s complete", session.request_id, session.zone_id)
        await self._broadcast_room(
            session.room_id,
            msg.make_travel_complete(session.zone_id, request_id_value=session.request_id),
        )

        # Share the initiator's clock reference so the room can realign time.
        requester = self._server.session.get_player(session.requester_id)
        if requester is not None and requester.clock_sync is not None:
            clock_ref = requester.clock_sync
            await self._broadcast_room(
                session.room_id,
                msg.make_clock_sync(
                    clock_ref["zone_id"],
                    clock_ref["absolute_ticks"],
                    clock_ref["real_time"],
                    clock_ref["clock_speed"],
                    player_id=session.requester_id,
                ),
                exclude={session.requester_id},
            )

        if self._active.get(session.room_id) is session:
            self._active.pop(session.room_id, None)

    async def abort(self, session, reason):
        if session.state in (TravelSession.COMPLETE, TravelSession.ABORTED):
            return
        session.state = TravelSession.ABORTED
        self._cancel_timeout(session)
        self.logger.info("[MP][TRAVEL] Travel %s aborted: %s", session.request_id, reason)
        await self._broadcast_room(
            session.room_id,
            msg.make_travel_abort(reason, request_id_value=session.request_id),
        )
        if self._active.get(session.room_id) is session:
            self._active.pop(session.room_id, None)

    def cancel_on_disconnect(self, player_id):
        for room_id, session in list(self._active.items()):
            if session.active and player_id in session.members:
                self.logger.info("[MP][TRAVEL] Player %s disconnected mid-travel", player_id)
                asyncio.get_running_loop().create_task(self.abort(session, "member disconnected"))

    def _set_timeout(self, session, delay, phase):
        self._cancel_timeout(session)
        loop = asyncio.get_running_loop()
        session.timeout_task = loop.create_task(self._watchdog(session, delay, phase))

    def _cancel_timeout(self, session):
        task = session.timeout_task
        session.timeout_task = None
        if task is not None and asyncio.current_task() is not task:
            task.cancel()

    async def _watchdog(self, session, delay, phase):
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        await self.abort(session, "%s timeout" % phase)

    async def _send(self, player, message):
        try:
            await player.connection.send(message)
        except Exception as exc:
            self.logger.warning("[MP][TRAVEL] Failed to deliver to player %s: %s", player.player_id, exc)

    async def _broadcast_room(self, room_id, message, exclude=None):
        await self._server.broadcast_room(room_id, message, exclude=exclude)