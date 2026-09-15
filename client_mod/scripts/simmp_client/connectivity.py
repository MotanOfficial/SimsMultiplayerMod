"""High-level client manager used by the game integration (and tests).

Sits between the networking engine and the game commands. Game-agnostic
except for the alarm-based message pumping, which gracefully no-ops when the
game is unavailable.
"""

import random
import time

from simmp.constants import (
    CLOCK_SPEED_NORMAL,
    CLOCK_SPEED_PAUSED,
    MAX_CLOCK_SPEED,
    MIN_CLOCK_SPEED,
)
from simmp_client import version
from simmp_client.hooks import game_hooks
from simmp_client.networking.engine import ClientEngine, EngineState
from simmp_client.state.save_transfer import SaveInbox
from simmp_client.state.session import LocalSession


class MultiplayerClient:
    def __init__(self, client_name=None, notify=None, presence_interval=5.0, client_id=None, presence_ttl=30.0):
        self.client_name = client_name or "Sims4Player"
        self.client_id = client_id if client_id is not None else "%032x" % random.getrandbits(128)
        self.presence_interval = presence_interval
        self.presence_ttl = presence_ttl
        self._notify = notify if notify is not None else (lambda line: None)
        self._presence_sampler = None
        self._last_presence_sent = 0.0
        self._world_sampler = None
        self._last_world_sent = 0.0
        self.world_interval = 5.0
        self.world_sync = True
        self._world_applier = None
        self._interaction_applier = None
        self._interaction_sampler = None
        self._last_interaction_tick = 0.0
        self.interaction_interval = 5.0
        self.interaction_sync = True
        self.deny_backoff = 10.0
        self._denied_until = {}
        self.reclaim_on_reconnect = True
        self._reclaim_pending = False
        self._dropped_owned = set()
        self._dropped_held = {}
        self._claimed_in_flight = set()
        self._claim_denied_until = {}
        self.engine = None
        self.session = LocalSession()
        self.session.presence_ttl = self.presence_ttl
        self._alarm_handle = None
        self.auto_accept_travel = True
        self.travel_controller = None
        self.auto_reconnect = True
        self.reconnect_backoff_min = 2.0
        self.reconnect_backoff_max = 30.0
        self._reconnect_attempt = 0
        self._next_reconnect_at = 0.0
        self._alarm_started_at = 0.0
        self._last_alarm_tick = 0.0
        self._last_tick_error = None
        self.save_inbox = SaveInbox()
        self.time_gate = True
        self.time_speed = CLOCK_SPEED_NORMAL
        self.time_by_player = None
        self.time_ticks = None
        self.time_ready_sent = False
        self.zone_ready_id = None
        self.time_unready_sent = False
        self._ready_pending_reason = ""
        self.clock_interval = 1.5
        self._last_clock_tick = 0.0
        self._clock_echo_until = 0.0
        self._gate_open_since = 0.0
        self._clock_echo_window = 2.0
        self._clock_apply_enabled = True
        self._autonomy_reconciler = None
        self.autonomy_suppression = True
        # Household funds sync (money).
        self.funds_sampler = None
        self.funds_applier = None
        self.funds_interval = 2.0
        self._funds_baseline = None
        self._last_funds_sent = 0.0
        # Lot-object live sync (build/buy moves, deletions, placements).
        self._object_gone_applier = None
        self._world_seen_last = None
        self._world_missing_streak = {}
        self._world_tracked_zone = None

    def set_presence_sampler(self, sampler):
        """sampler() -> (zone_id, lot_id) or None. Called on the game thread."""
        self._presence_sampler = sampler

    def set_world_sampler(self, sampler):
        """sampler() -> [{"key": str, "fields": {...}}] or None. Game thread."""
        self._world_sampler = sampler

    def set_funds_sampler(self, sampler):
        """sampler() -> household simoleon balance (int) or None."""
        self.funds_sampler = sampler

    def set_funds_applier(self, applier):
        """applier(balance) -> apply an absolute household balance."""
        self.funds_applier = applier

    def set_object_gone_applier(self, applier):
        """applier([key, ...]) -> best-effort destroy of removed lot objects."""
        self._object_gone_applier = applier

    def set_world_applier(self, applier):
        """applier(entries) -> int. Called on the game thread after remote
        world state changes; receives remote-owned entries only."""
        self._world_applier = applier

    def set_interaction_sampler(self, sampler):
        """sampler() -> [{"key": str, "interaction": str}] or None. Game thread."""
        self._interaction_sampler = sampler

    def set_interaction_applier(self, applier):
        """applier(entries) -> int. Called on the game thread after remote
        interaction state changes; receives remote-owned entries only."""
        self._interaction_applier = applier

    def set_autonomy_reconciler(self, reconciler):
        """reconciler(remote_owner_keys, my_player_id, my_zone_id) -> (s,r,sk).
        Called on the game thread after ownership changes to toggle per-sim
        autonomy. Set to None to disable."""
        self._autonomy_reconciler = reconciler

    def _log(self, label, line):
        self._notify("[MP][%s] %s" % (label, line))

    def connect(self, host, port):
        if self.engine is not None and not self.engine.stopped:
            self._log("ERROR", "already connected")
            return False
        port = int(port)
        self.session = LocalSession()
        self.session.host = host
        self.session.port = port
        self.session.client_id = self.client_id
        self.session.presence_ttl = self.presence_ttl

        engine = ClientEngine(
            host,
            port,
            client_name=self.client_name,
            client_version=version.CLIENT_VERSION,
            client_id=self.client_id,
        )
        if not engine.connect(timeout=10.0):
            engine.stop()
            self.engine = None
            self._log("ERROR", "connection to %s:%s failed" % (host, port))
            return False

        self.engine = engine
        self._log("NET", "Connected to %s:%s" % (host, port))
        self._start_alarm()
        self._reconnect_attempt = 0
        self._next_reconnect_at = 0.0
        self.process_incoming()
        return True

    def disconnect(self):
        self._stop_alarm()
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
        self.session.connected = False
        self._reclaim_pending = False
        self._dropped_owned = set()
        self._dropped_held = {}
        self._claimed_in_flight = set()
        self._claim_denied_until = {}
        self._reconnect_attempt = 0
        self._next_reconnect_at = 0.0
        self._log("NET", "Disconnected")

    def reconnect(self):
        """Drop and re-establish the connection, restoring owned state.

        Whatever world ownership and interactions this client held at the
        moment of the drop is captured first; after the replacement HELLO a
        server-held ghost keeps them on the server, and anything the server no
        longer has is re-claimed / re-proposed by the client fallback.
        """
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected; cannot reconnect")
            return False
        self._capture_dropped_state()
        if self.engine.reconnect():
            self._log("NET", "Reconnecting (ownership will be restored on resume)")
            return True
        self._log("ERROR", "failed to schedule reconnect")
        return False

    def _capture_dropped_state(self):
        """Remember what this client held so it can be restored after a drop."""
        mine = self.session.player_id
        world = self.session.world
        self._dropped_owned = set()
        for key in world.keys():
            obj = world.get(key)
            if obj is not None and obj.owner == mine:
                self._dropped_owned.add(key)
        interactions = self.session.interactions
        self._dropped_held = {}
        for key in interactions.keys():
            entry = interactions.get(key)
            if entry is not None and entry["player_id"] == mine:
                self._dropped_held[key] = dict(entry)
        self._reclaim_pending = bool(self._dropped_owned or self._dropped_held)

    def _maybe_reclaim(self):
        """Re-claim/re-propose owned state that survived a reconnect gap.

        Runs once after the reconnect snapshots (WORLD_STATE then
        INTERACTION_STATE) have been applied. Keys still held by the server
        (ghost resume) or by another player are left alone.
        """
        if not self._reclaim_pending:
            return
        self._reclaim_pending = False
        owned, held = self._dropped_owned, self._dropped_held
        self._dropped_owned = set()
        self._dropped_held = {}
        mine = self.session.player_id
        now = time.time()
        for key in sorted(owned):
            mirror = self.session.world.get(key)
            if mirror is not None and mirror.owner not in (None, mine):
                continue
            self._log("SYNC", "Re-claiming object %r after reconnect" % key)
            self.claim_object(key)
        for key in sorted(held):
            if self.session.interactions.get(key) is not None:
                continue
            if now < self._denied_until.get(key, 0):
                continue
            if self.session.interactions.cooldown_until(key) > now:
                continue
            self._log("SYNC", "Re-proposing interaction on %r after reconnect" % key)
            entry = held[key]
            self.propose_interaction(
                key,
                entry.get("interaction", ""),
                args=entry.get("args"),
                affordance=entry.get("affordance"),
                affordance_id=entry.get("affordance_id"),
                target=entry.get("target"),
            )

    def send_test_event(self, text):
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        seq = self.engine.send_event("test", text)
        if seq:
            self._log("SYNC", "Sent EVENT test data=%r seq=%s" % (text, seq))
            return True
        self._log("ERROR", "failed to queue EVENT")
        return False

    def send_presence(self, zone_id, lot_id, timestamp=None):
        if self.engine is None or not self.engine.connected:
            return False
        return bool(self.engine.send_presence(zone_id, lot_id, timestamp))

    def join_room(self, room_id):
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        if self.engine.send_join_room(room_id):
            self._log("ROOM", "Requested join room %s" % room_id)
            return True
        return False

    def request_travel(self, zone_id):
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        ok = self.engine.send_travel_request(zone_id)
        if ok:
            self._log("TRAVEL", "Requested travel to zone %s" % zone_id)
        else:
            self._log("ERROR", "failed to queue TRAVEL_REQUEST")
        return bool(ok)

    def respond_travel(self, request_id, accepted, reason=None):
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        ok = self.engine.send_travel_response(request_id, accepted, reason)
        if ok:
            self._log("TRAVEL", "Responded %s to travel request" % ("accepted" if accepted else "declined"))
        return bool(ok)

    def confirm_travel_ready(self, zone_id=None):
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        target_zone = zone_id or self.session.travel_zone_id
        if target_zone is None or self.session.travel_request_id is None:
            self._log("ERROR", "no active travel to confirm")
            return False
        ok = self.engine.send_travel_ready(target_zone, self.session.travel_request_id)
        if ok:
            self._log("TRAVEL", "Reported READY for zone %s" % target_zone)
        return bool(ok)

    def send_clock_sync(self, zone_id=None):
        if self.engine is None or not self.engine.connected:
            return False
        sample = game_hooks.sample_game_clock()
        if sample is None:
            self._log("ERROR", "game clock not available")
            return False
        absolute_ticks, clock_speed = sample
        target_zone = zone_id or game_hooks.current_zone_id() or self.session.travel_zone_id or 0
        ok = self.engine.send_clock_sync(target_zone, absolute_ticks, time.time(), clock_speed)
        if ok:
            self._log("SYNC", "CLOCK_SYNC zone=%s ticks=%s speed=%s" % (target_zone, absolute_ticks, clock_speed))
        return bool(ok)

    def set_clock_apply_enabled(self, enabled):
        """Toggle whether room TIME_SYNC frames drive the local game clock."""
        self._clock_apply_enabled = bool(enabled)

    def change_clock_speed(self, speed):
        """Local player changes the room clock (last change wins).

        Applies the speed locally right away (when the room is running) and
        broadcasts TIME_SPEED so the server mirrors it to the whole room. The
        echo window suppresses the resulting TIME_SYNC applying a second time.
        """
        speed = int(speed)
        if speed < MIN_CLOCK_SPEED or speed > MAX_CLOCK_SPEED:
            self._log("ERROR", "clock speed must be %s..%s" % (MIN_CLOCK_SPEED, MAX_CLOCK_SPEED))
            return False
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        now = time.time()
        if not self.time_gate:
            game_hooks.set_clock_speed(speed)
            # Echo window: suppress the server bouncing our own change back.
            self._clock_echo_until = now + self._clock_echo_window
        ticks = None
        sample = game_hooks.sample_game_clock()
        if sample is not None:
            ticks = sample[0]
        ok = self.engine.send_time_speed(speed, ticks=ticks)
        if ok:
            self.time_speed = speed
            self._log("TIME", "Clock speed set to %s" % speed)
        else:
            self._log("ERROR", "failed to queue TIME_SPEED")
        return bool(ok)

    def mark_ready(self):
        """Explicitly send TIME_READY (manual fallback for mp.ready)."""
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        if self.time_ready_sent:
            self._log("TIME", "already reported ready")
            return True
        zone_id = game_hooks.current_zone_id()
        if zone_id is None:
            self._log("ERROR", "no current zone available")
            return False
        ok = self.engine.send_time_ready(zone_id)
        if ok:
            self.time_ready_sent = True
            self._log("TIME", "TIME_READY zone=%s" % zone_id)
        return bool(ok)

    def clock_summary(self):
        return "gate=%s speed=%s by=%s ready=%s echo=%.1fs local=%s" % (
            "open" if not self.time_gate else "closed",
            self.time_speed,
            self.time_by_player,
            "sent" if self.time_ready_sent else "pending",
            max(0.0, self._clock_echo_until - time.time()),
            game_hooks.get_clock_speed(),
        )

    def _apply_room_speed(self, speed):
        if not self._clock_apply_enabled:
            return False
        try:
            result = game_hooks.set_clock_speed(speed)
            self._log("TIME", "Applied room speed %s -> %s" % (speed, result))
            return result is not None
        except Exception as exc:
            self._log("TIME", "Apply room speed %s FAILED: %r" % (speed, exc))
            return False

    def _maybe_sync_clock(self):
        """Reconcile the game clock with the room's authoritative state.

        Runs on the game thread (alarm tick). While the room is gated (someone
        is joining / not ready yet) the client enforces PAUSED and never pushes
        a start, so nobody plays ahead. Once the gate is open, any local
        divergence beyond the echo window is a deliberate player change (last
        change wins) and is broadcast as TIME_SPEED. TIME_READY is re-sent
        automatically the first time the zone is running, again after any
        WELCOME (fresh or resumed connection), and whenever the running zone
        changes id mid-session (travel), which makes the server re-gate the
        room until every member has arrived in the new zone.
        """
        engine = self.engine
        if engine is None or not engine.connected:
            return
        zone_state = game_hooks.current_zone_running_state()
        if not zone_state.running:
            # Outside a playable zone (CAS, manage worlds, main menu, loading).
            # Tell the server so it re-gates the room PAUSED until we return
            # and re-ready; without this the other player would keep playing
            # while we are away in CAS/menus.
            if self.time_ready_sent and not self.time_unready_sent:
                if engine.send_time_unready():
                    self.time_unready_sent = True
                    self.time_ready_sent = False
                    self._log("TIME", "TIME_UNREADY (left playable zone)")
            if not self.time_ready_sent:
                reason = str(zone_state)
                if reason != self._ready_pending_reason:
                    self._ready_pending_reason = reason
                    self._log("TIME", "TIME_READY waiting: %s" % reason)
            return
        now = time.time()
        zone_id = zone_state.zone_id
        if zone_id is None:
            return
        self.time_unready_sent = False
        if not self.time_ready_sent or self.zone_ready_id != zone_id:
            if not engine.send_time_ready(zone_id):
                return
            self.time_ready_sent = True
            self.zone_ready_id = zone_id
            self._ready_pending_reason = ""
            self._log("TIME", "TIME_READY zone=%s" % zone_id)
        if now < self._last_clock_tick:
            return
        self._last_clock_tick = now + self.clock_interval
        local = game_hooks.get_clock_speed()
        if local is None:
            return
        if self.time_gate:
            # Gated: someone is still joining/loading. The room must stay
            # paused. Do this eagerly even inside an echo window - the echo
            # exists only to suppress the server bouncing our own OPEN-gate
            # speed change back at us, never a PAUSE.
            if local != CLOCK_SPEED_PAUSED:
                game_hooks.set_clock_speed(CLOCK_SPEED_PAUSED)
            return
        if now - self._gate_open_since < self._clock_echo_window:
            if local != self.time_speed:
                self._apply_room_speed(self.time_speed)
            return
        if local != self.time_speed and now >= self._clock_echo_until:
            self._clock_echo_until = now + self._clock_echo_window
            ticks = None
            sample = game_hooks.sample_game_clock()
            if sample is not None:
                ticks = sample[0]
            if engine.send_time_speed(local, ticks=ticks):
                self.time_speed = local
                self._log("TIME", "TIME_SPEED %s (local change)" % local)

    def _current_zone_id(self):
        try:
            return game_hooks.current_zone_id()
        except Exception:
            return None

    def claim_object(self, key):
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        ok = self.engine.send_object_claim(key, zone_id=self._current_zone_id())
        if ok:
            self._log("SYNC", "Requested ownership of object %r" % key)
        return ok

    def release_object(self, key):
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        ok = self.engine.send_object_release(key, zone_id=self._current_zone_id())
        if ok:
            self._log("SYNC", "Released object %r" % key)
        return ok

    def update_object(self, key, fields):
        """Push a delta for an object this client owns (rev is best-effort)."""
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        ok = self.engine.send_object_update(
            [{"key": key, "fields": fields, "rev": 0}], zone_id=self._current_zone_id()
        )
        if ok:
            self._log("SYNC", "Sent OBJECT_UPDATE %r %s" % (key, fields))
        return ok

    def propose_interaction(self, object_key, interaction, args=None, affordance=None, affordance_id=None, target=None):
        """Reserve an interaction on `object_key` (first come, first served).

        Carries the sender-side affordance identity + aim so peers can push
        the same super-interaction onto their mirrored sim. All extras are
        best-effort and optional on the wire.
        """
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        ok = self.engine.send_interaction_request(
            object_key,
            interaction,
            args,
            affordance=affordance,
            affordance_id=affordance_id,
            target=target,
            zone_id=self._current_zone_id(),
        )
        if ok:
            self._log("SYNC", "Proposed interaction %r on %r" % (interaction, object_key))
        return ok

    def end_interaction(self, object_key):
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        ok = self.engine.send_interaction_end(object_key, zone_id=self._current_zone_id())
        if ok:
            self._log("SYNC", "Ending interaction on %r" % object_key)
        return ok

    def push_save_chunk(self, slot, seq, total, size, data):
        """Send one SAVE_PUSH chunk (`data` raw bytes). Server relays it to peers."""
        if self.engine is None or not self.engine.connected:
            self._log("ERROR", "not connected")
            return False
        ok = self.engine.send_save_push(slot, seq, total, size, data)
        if not ok:
            self._log("ERROR", "failed to queue SAVE_PUSH %s/%s" % (seq, total))
        return bool(ok)

    def push_save_file(self, slot, data, chunk_size=512 * 1024):
        """Push a whole save file as SAVE_PUSH chunks. Returns (sent, total)."""
        total = (len(data) + chunk_size - 1) // chunk_size if data else 1
        sent = 0
        for seq in range(1, total + 1):
            chunk = data[(seq - 1) * chunk_size : seq * chunk_size]
            if not self.push_save_chunk(slot, seq, total, len(data), chunk):
                break
            sent += 1
        return (sent, total)

    def request_save(self):
        """Ask the server to replay the room's cached save (if any).

        Essential for late joiners: a player who connects after the host
        already shared would otherwise wait forever for a broadcast that
        already happened.
        """
        if self.engine is None or not self.engine.connected:
            return False
        return self.engine.send_save_request()

    def process_incoming(self):
        if self.engine is None:
            return
        self.ensure_alarm()
        for message in self.engine.drain():
            self._handle_message(message)

    def alarm_summary(self):
        """One-line alarm health for `mp.diag`."""
        handle = "armed" if self._alarm_handle is not None else "none"
        if self._last_alarm_tick:
            ago = time.time() - self._last_alarm_tick
            return "%s last_tick=%.1fs ago" % (handle, ago)
        return "%s (no tick yet)" % handle

    def status(self):
        session = self.session
        lines = [
            "player_id=%s" % session.player_id,
            "name=%s" % self.client_name,
            "client_id=%s" % session.client_id,
            "connected=%s" % session.connected,
            "host=%s:%s" % (session.host, session.port),
            "room=%s" % session.room_id,
            "room_players=%s" % sorted(session.room_players.keys()),
            "engine_state=%s" % (self.engine.state if self.engine else "none"),
            "pending_events=%s" % (self.engine.pending_count if self.engine else 0),
            "auto_reconnect=%s attempts=%s" % (
                "on" if self.auto_reconnect else "off",
                self._reconnect_attempt,
            ),
        ]
        if session.presence:
            lines.append("presence=" + ", ".join(
                "%s(zone=%s lot=%s)" % (pid, p.get("zone_id"), p.get("lot_id"))
                for pid, p in sorted(session.presence.items())
            ))
        if session.travel_state != "idle":
            lines.append("travel=%s zone=%s requester=%s(%s)" % (
                session.travel_state,
                session.travel_zone_id,
                session.travel_requester_id,
                session.travel_requester_name,
            ))
        if session.clock_sync:
            lines.append("clock=%s" % session.clock_sync)
        lines.append("clock_room=%s" % self.clock_summary())
        if self._ready_pending_reason:
            lines.append("ready_wait=%s" % self._ready_pending_reason)
        lines.append("alarm=%s" % self.alarm_summary())
        lines.append("tick_error=%s" % (self._last_tick_error or "none"))
        try:
            lines.append("zone=%s" % game_hooks.current_zone_running_state())
        except Exception:
            lines.append("zone=probe-failed")
        world = session.world
        if world.objects:
            lines.append("world=%s object(s) seq=%s" % (world.count(), world.last_seq))
        return "\n".join(lines)

    def world_summary(self):
        world = self.session.world
        if not world.objects:
            return "-"
        parts = []
        for key in sorted(world.keys()):
            mirror = world.get(key)
            parts.append("%s(owner=%s@%s)" % (key, mirror.owner, mirror.fields.get("x", "-")))
        return ", ".join(parts)

    def presence_summary(self):
        parts = []
        for pid, p in sorted(self.session.presence.items()):
            parts.append("#%s@zone%s/lot%s" % (pid, p.get("zone_id"), p.get("lot_id")))
        return ", ".join(parts) if parts else "-"

    def interaction_summary(self):
        mirror = self.session.interactions
        parts = []
        mine = self.session.player_id
        for key in sorted(mirror.keys()):
            entry = mirror.get(key)
            holder = "me" if entry["player_id"] == mine else "#%s" % entry["player_id"]
            parts.append("%s=%s(%s)" % (key, entry["interaction"], holder))
        for key in sorted(mirror.cooldowns.keys()):
            parts.append("%s=cooldown" % key)
        return ", ".join(parts) if parts else "-"

    def save_summary(self):
        active = self.save_inbox.active()
        return "transfers=%s" % (", ".join(active) if active else "-")

    def _handle_message(self, message):
        message_type = message["type"]
        payload = message["payload"]
        if message_type == "WELCOME":
            self.session.apply_welcome(payload)
            self.time_ready_sent = False
            self.zone_ready_id = None
            self.time_gate = True
            self._log("NET", "Player ID: %s (room %s)" % (payload["player_id"], payload["room_id"]))
        elif message_type == "ROOM_STATE":
            self.session.apply_room_state(payload)
            names = [p["name"] for p in payload["players"]]
            self._log("ROOM", "Room %s players: %s" % (payload["room_id"], ", ".join(names) or "-"))
        elif message_type == "PLAYER_JOINED":
            self.session.apply_player_joined(payload)
            self._log(
                "ROOM",
                "Player %s (%s) joined %s"
                % (payload["player_id"], payload["name"], payload["room_id"]),
            )
        elif message_type == "PLAYER_LEFT":
            self.session.apply_player_left(payload)
            self._log(
                "ROOM",
                "Player %s left %s (%s)"
                % (payload["player_id"], payload["room_id"], payload["reason"]),
            )
        elif message_type == "EVENT":
            self._log(
                "SYNC",
                "Received EVENT type=%s data=%r from=%s seq=%s"
                % (payload["event_type"], payload["data"], payload.get("player_id"), payload["seq"]),
            )
        elif message_type == "PRESENCE":
            self.session.apply_presence(payload)
        elif message_type == "TRAVEL_INVITE":
            self.session.apply_travel_invite(payload, message["request_id"])
            self._log(
                "TRAVEL",
                "Travel invite to zone %s from player %s (%s)"
                % (payload["zone_id"], payload["requester_id"], payload["requester_name"]),
            )
            accepted = self._decide_travel(message["request_id"], payload["zone_id"])
            if accepted is None:
                self._log("TRAVEL", "Waiting for a decision on the travel invite...")
            else:
                self.respond_travel(message["request_id"], accepted)
                if not accepted:
                    self.session.apply_travel_abort(payload, message["request_id"])
        elif message_type == "TRAVEL_BEGIN":
            self.session.apply_travel_begin(payload, message["request_id"])
            self._log("TRAVEL", "Travel BEGIN to zone %s" % payload["zone_id"])
            triggered = game_hooks.travel_to_zone(payload["zone_id"])
            if not triggered:
                self._log("TRAVEL", "[*] game hook unavailable; use mp.travel_ready to confirm manually")
        elif message_type == "TRAVEL_COMPLETE":
            self.session.apply_travel_complete(payload, message["request_id"])
            self._log("TRAVEL", "Travel COMPLETE for zone %s" % payload["zone_id"])
        elif message_type == "TRAVEL_ABORT":
            self.session.apply_travel_abort(payload, message["request_id"])
            self._log("TRAVEL", "Travel ABORTED: %s" % payload["reason"])
        elif message_type == "CLOCK_SYNC":
            self.session.apply_clock_sync(payload)
            self._log("SYNC", "CLOCK_SYNC from=%s zone=%s ticks=%s" % (
                payload.get("player_id"), payload["zone_id"], payload["absolute_ticks"],
            ))
        elif message_type == "TIME_SYNC":
            explicit_gate = payload.get("gate")
            if explicit_gate is not None:
                gate = bool(explicit_gate)
            else:
                gate = payload["speed"] == CLOCK_SPEED_PAUSED
            was_closed = self.time_gate
            self.time_speed = payload["speed"]
            self.time_by_player = payload.get("player_id")
            self.time_ticks = payload.get("ticks")
            self.time_gate = gate
            now = time.time()
            if gate:
                # Room paused (peer still joining/loading): apply the PAUSE
                # immediately, never delayed by an echo window.
                self._apply_room_speed(CLOCK_SPEED_PAUSED)
            elif was_closed:
                self._gate_open_since = now
                if now >= self._clock_echo_until:
                    self._clock_echo_until = now + self._clock_echo_window
                    self._apply_room_speed(payload["speed"])
            elif now >= self._clock_echo_until:
                self._apply_room_speed(payload["speed"])
            self._log("SYNC", "TIME_SYNC speed=%s by=%s gate=%s" % (
                payload["speed"],
                payload.get("player_id"),
                "open" if not gate else "closed",
            ))
        elif message_type == "WORLD_STATE":
            self.session.apply_world_state(payload)
            self._log("SYNC", "World state for room %s: %s object(s)" % (
                payload["room_id"], len(payload["objects"]),
            ))
        elif message_type == "OBJECT_GONE":
            key = payload["key"]
            self.session.world.apply_removal(key, payload.get("zone_id"))
            self._log("SYNC", "Object removed: %s" % key)
            applier = self._object_gone_applier
            if applier is not None:
                try:
                    applier([key])
                except Exception:
                    pass
        elif message_type == "FUNDS_SYNC":
            balance = payload["balance"]
            self._funds_baseline = balance
            applier = self.funds_applier
            if applier is not None:
                try:
                    result = applier(balance)
                except Exception:
                    result = None
                self._log("FUNDS", "peer set household balance %s -> %s" % (balance, result))
            else:
                self._log("FUNDS", "peer set household balance %s" % balance)
            self._notify_remote_world()
        elif message_type == "WORLD_DELTA":
            self.session.apply_world_delta(payload)
            self._log("SYNC", "World delta from=%s seq=%s keys=%s" % (
                payload.get("player_id"),
                payload["seq"],
                [u["key"] for u in payload["updates"]],
            ))
            self._notify_remote_world()
        elif message_type == "OBJECT_OWNERSHIP":
            self.session.apply_object_ownership(payload)
            self._claimed_in_flight.discard(payload.get("key"))
            if payload.get("owner") is None:
                self._claim_denied_until.pop(payload.get("key"), None)
            self._log("SYNC", "Object %r owner -> %s" % (payload["key"], payload.get("owner")))
            self._reconcile_autonomy()
        elif message_type == "OBJECT_CLAIM_ACK":
            self.session.apply_object_claim_ack(payload)
            self._claimed_in_flight.discard(payload.get("key"))
            self._log("SYNC", "Ownership ack for %r: owner=%s" % (payload["key"], payload.get("owner")))
            self._reconcile_autonomy()
        elif message_type == "INTERACTION_STATE":
            self.session.apply_interaction_state(payload)
            self._log("SYNC", "Interaction state for room %s: %s active" % (
                payload["room_id"], len(payload["interactions"]),
            ))
            self._notify_remote_interactions()
            self._maybe_reclaim()
        elif message_type == "INTERACTION_START":
            self.session.apply_interaction_start(payload)
            self._denied_until.pop(payload["object_key"], None)
            self._log("SYNC", "Interaction start: %s on %r by %s" % (
                payload["interaction"], payload["object_key"], payload["player_id"],
            ))
            self._notify_remote_interactions()
        elif message_type == "INTERACTION_FREE":
            self.session.apply_interaction_free(payload)
            self._denied_until.pop(payload["object_key"], None)
            self._log("SYNC", "Interaction released: %r" % payload["object_key"])
        elif message_type == "SAVE_PUSH":
            status, data = self.save_inbox.feed(
                payload["slot"],
                payload["seq"],
                payload["total"],
                payload["size"],
                payload["data"],
            )
            self._log(
                "SAVE",
                "SAVE_PUSH %s %s/%s (%s)"
                % (payload["slot"], payload["seq"], payload["total"], status),
            )
            if status == "complete":
                try:
                    path = game_hooks.receive_save(payload["slot"], data)
                    self._log("SAVE", "Saved %r -> %s" % (payload["slot"], path))
                except Exception as exc:
                    self._log("ERROR", "Save write failed: %s: %s" % (type(exc).__name__, exc))
        elif message_type == "SAVE_ACK":
            self._log(
                "SAVE",
                "SAVE_ACK %s ok=%s reached=%s%s"
                % (
                    payload["slot"],
                    payload["ok"],
                    payload["reached"],
                    (" (%s)" % payload["message"]) if payload.get("message") else "",
                ),
            )
        elif message_type == "PONG":
            self.session.apply_pong(payload)
            self._log("NET", "Pong server_time=%s" % payload["server_time"])
        elif message_type == "ERROR":
            self._log("ERROR", "Server error %s: %s" % (payload["code"], payload["message"]))
            ref = payload.get("ref")
            if ref and payload["code"] in ("INTERACTION_BUSY", "INTERACTION_COOLDOWN"):
                self._denied_until[ref] = time.time() + self.deny_backoff
            elif ref and payload["code"] == "OBJECT_LOCKED":
                # Someone else claimed this key first. Stop pinging it for a
                # while (clear the in-flight guard so a later release is seen)
                # and back off so losers do not spam the server every tick.
                self._claimed_in_flight.discard(ref)
                self._claim_denied_until[ref] = time.time() + 30.0
        else:
            self._log("NET", "Unhandled message %s" % message_type)

    def _start_alarm(self):
        # NOTE: the game-thread tick is a *chained one-off* alarm, not a
        # repeating one. This game build has NO `add_one_off_real_time`;
        # a one-shot is `add_alarm_real_time(..., repeating=False)`. Each
        # tick re-arms the next in `_on_alarm_chained`.
        if self._alarm_handle is not None:
            return
        self._alarm_started_at = time.time()
        self._alarm_handle = game_hooks.add_one_off_real_time_alarm(self, 0.5, self._on_alarm_chained)
        if self._alarm_handle is None:
            self._log("ERROR", "sync alarm unavailable; will retry on next tick/command")
        else:
            self._log("NET", "sync alarm started")

    def _on_alarm_chained(self, *args):
        # Fired by the one-off alarm scheduled in `_start_alarm`: run one
        # tick, then re-arm the next. The pending handle is spent either way.
        self._alarm_handle = None
        try:
            self._on_alarm(*args)
        finally:
            try:
                self.ensure_alarm()
            except Exception:
                pass

    def ensure_alarm(self):
        """(Re)start the 0.5s game-thread tick if it is missing or stale.

        Alarm creation can fail when connecting mid-load, and the game may
        drop a pending schedule; every manual command runs this (via
        `process_incoming`) so the sync loop self-heals without a restart.
        The loop survives connection drops (it drives the auto-reconnect);
        only an explicit `disconnect()` (engine gone) stops it.
        """
        if self.engine is None or self.engine.stopped:
            return
        now = time.time()
        if self._alarm_handle is not None:
            if self._last_alarm_tick:
                if now - self._last_alarm_tick < 5.0:
                    return
            elif now - self._alarm_started_at < 2.0:
                # Freshly created but not yet due; give the game a breath.
                return
            self._stop_alarm()
            self._log("NET", "sync alarm stale; restarting")
        self._start_alarm()

    def _stop_alarm(self):
        game_hooks.cancel_alarm(self._alarm_handle)
        self._alarm_handle = None

    def _decide_travel(self, request_id, zone_id):
        if self.travel_controller is not None:
            try:
                decision = self.travel_controller(request_id, zone_id)
            except Exception:
                self._log("ERROR", "travel controller failed; falling back to auto-accept")
                decision = None
            if decision is None:
                # The controller defers the decision (e.g. it opened a dialog
                # and will call respond_travel() from the response callback).
                return None
            return bool(decision)
        return self.auto_accept_travel

    def _maybe_report_travel_ready(self):
        session = self.session
        if session.travel_state != "traveling":
            return
        if self.engine is None or not self.engine.connected:
            return
        zone_id = game_hooks.current_zone_id()
        if zone_id is None:
            return
        if zone_id != session.travel_zone_id:
            return
        if not game_hooks.current_zone_is_running():
            return
        if self.confirm_travel_ready(zone_id):
            session.travel_state = "traveled"

    def _on_alarm(self, *args):
        try:
            self._last_alarm_tick = time.time()
            engine = self.engine
            if engine is not None and engine.connected:
                self._reconnect_attempt = 0
            if engine is not None and not engine.connected and self.session.connected:
                self._capture_dropped_state()
                self.session.connected = False
            self.process_incoming()
            self._maybe_sync_clock()
            self.session.purge_stale_presence()
            self._maybe_send_presence()
            self._maybe_send_world_update()
            self._maybe_sync_funds()
            self._maybe_send_interactions()
            self._maybe_report_travel_ready()
            self._maybe_auto_reconnect()
        except Exception as exc:
            # A single failing tick must never silently kill the repeating
            # schedule; log once per distinct error instead of spamming.
            key = "%s: %s" % (type(exc).__name__, exc)
            if key != self._last_tick_error:
                self._last_tick_error = key
                try:
                    self._log("ERROR", "sync tick failed: %s" % key)
                except Exception:
                    pass
        return True

    def _maybe_auto_reconnect(self):
        """Reconnect with backoff after a drop while `auto_reconnect` is on.

        Reuses the fail-safe engine `reconnect()` (async, on the engine
        thread), so the game thread never blocks. A successful connection
        resets the backoff; each failed attempt doubles it up to
        `reconnect_backoff_max`.
        """
        engine = self.engine
        if not self.auto_reconnect or engine is None or engine.connected or engine.stopped:
            return
        if engine.state == EngineState.CONNECTING:
            return
        now = time.time()
        if now < self._next_reconnect_at:
            return
        if engine.reconnect():
            self._reconnect_attempt += 1
            backoff = self.reconnect_backoff_min * (2 ** (self._reconnect_attempt - 1))
            delay = min(backoff, self.reconnect_backoff_max)
            self._next_reconnect_at = now + delay
            self._log(
                "NET",
                "Auto-reconnect attempt %d scheduled (next in %.1fs)"
                % (self._reconnect_attempt, delay),
            )
        else:
            self._next_reconnect_at = now + self.reconnect_backoff_min

    def _maybe_send_presence(self):
        if self.engine is None or not self.engine.connected or self._presence_sampler is None:
            return
        now = time.time()
        if now - self._last_presence_sent < self.presence_interval:
            return
        try:
            sample = self._presence_sampler()
        except Exception:
            self._log("ERROR", "presence sampler failed")
            return
        if sample is None:
            return
        zone_id, lot_id = sample
        if self.send_presence(zone_id, lot_id, now):
            self._last_presence_sent = now

    def _notify_remote_world(self):
        """Hand remote-owned mirror entries to the game-side applier.

        Runs on the game thread (alarm -> process_incoming). Only sims owned
        by another player in the room are passed; entries this client owns
        (its own driven sim) are never applied.
        """
        applier = self._world_applier
        if applier is None:
            return
        if self.engine is None or not self.engine.connected:
            return
        mine = self.session.player_id
        entries = []
        remote_owner_keys = set()
        zone_id = self.zone_ready_id
        for key in self.session.world.keys():
            mirror = self.session.world.get(key)
            if mirror is None:
                continue
            owner = mirror.owner
            if owner is None or owner == mine:
                continue
            entries.append({"key": key, "fields": dict(mirror.fields)})
            remote_owner_keys.add(key)
        if entries:
            try:
                applier(entries)
            except Exception:
                pass
        self._reconcile_autonomy(remote_owner_keys)

    def _reconcile_autonomy(self, remote_owner_keys=None):
        """Toggle local autonomy off for sims owned by other players.

        Best-effort and game-thread only; never raises. Refreshes on every
        world sync and every ownership change so a released sim regains its
        autonomy immediately.
        """
        if not self.autonomy_suppression or self._autonomy_reconciler is None:
            return
        if self.engine is None or not self.engine.connected:
            return
        mine = self.session.player_id
        zone_id = self.zone_ready_id
        remote_keys = remote_owner_keys
        if remote_keys is None:
            remote_keys = set()
            for key in self.session.world.keys():
                mirror = self.session.world.get(key)
                if mirror is None:
                    continue
                owner = mirror.owner
                if owner is None or owner == mine:
                    continue
                remote_keys.add(key)
        try:
            self._autonomy_reconciler(remote_keys, mine, zone_id)
        except Exception:
            pass

    def _notify_remote_interactions(self):
        """Hand remote-owned interaction entries to the game-side applier.

        Runs on the game thread (alarm -> process_incoming). Only interactions
        on sims owned by another player are passed; entries this client
        proposed are never re-executed locally (its own game already runs
        them). Includes the affordance identity + target so the applier can
        push the same super-interaction onto the mirrored sim.
        """
        applier = self._interaction_applier
        if applier is None:
            return
        if self.engine is None or not self.engine.connected:
            return
        mine = self.session.player_id
        entries = []
        for key in self.session.interactions.keys():
            mirror = self.session.interactions.get(key)
            if mirror is None:
                continue
            owner = mirror["player_id"]
            if owner is None or owner == mine:
                continue
            entries.append(
                {
                    "key": key,
                    "interaction": mirror["interaction"],
                    "args": mirror.get("args"),
                    "affordance": mirror.get("affordance"),
                    "affordance_id": mirror.get("affordance_id"),
                    "target": mirror.get("target"),
                }
            )
        if not entries:
            return
        try:
            applier(entries)
        except Exception:
            pass

    def _maybe_send_world_update(self):
        if not self.world_sync or self._world_sampler is None:
            return
        if self.engine is None or not self.engine.connected:
            return
        now = time.time()
        if now - self._last_world_sent < self.world_interval:
            return
        # Travel/loading safety: never declare objects "gone" while the zone
        # is not running, or an empty sampler during a loading screen would
        # look like the whole lot was deleted.
        zone_state = game_hooks.current_zone_running_state()
        running = bool(zone_state.running)
        zone_id = zone_state.zone_id
        if self._world_tracked_zone != zone_id:
            self._world_seen_last = None
            self._world_missing_streak = {}
            self._world_tracked_zone = zone_id
        try:
            objects = self._world_sampler()
        except Exception:
            self._log("ERROR", "world sampler failed")
            return
        present = {}
        for entry in objects or []:
            key = entry.get("key")
            if isinstance(key, str) and key:
                present[key] = entry
        # Gone detection (build/buy deletes): a key that used to exist and has
        # now been missing on two consecutive ticks is broadcast as removed.
        # Sims are excluded - a sim leaving the zone is travel, not deletion.
        if self._world_seen_last is not None and running:
            for key in list(self._world_seen_last):
                if key in present or key.startswith("sim:"):
                    continue
                streak = self._world_missing_streak.get(key, 0) + 1
                if streak >= 2:
                    self._world_seen_last.discard(key)
                    self._world_missing_streak.pop(key, None)
                    self._send_object_gone(key)
                else:
                    self._world_missing_streak[key] = streak
        if self._world_seen_last is None:
            self._world_seen_last = set(present)
        else:
            self._world_seen_last.update(present)
        mine = self.session.player_id
        updates = []
        now = time.time()
        for entry in present.values():
            key = entry.get("key")
            if not isinstance(key, str) or not key:
                continue
            mirror = self.session.world.get(key)
            if mirror is None or mirror.owner != mine:
                # Not owned on this session yet: (re)claim so the next tick can
                # push deltas. One claim per key until the ack/ownership lands,
                # paused while the server denied us (someone else holds it).
                if key not in self._claimed_in_flight and now >= self._claim_denied_until.get(key, 0):
                    self._claimed_in_flight.add(key)
                    self.claim_object(key)
                continue
            updates.append({"key": key, "fields": entry.get("fields", {}), "rev": 0})
        if updates and self.engine.send_object_update(updates):
            self._last_world_sent = now

    def _send_object_gone(self, key):
        if self.engine is None or not self.engine.connected:
            return
        if self.engine.send_object_gone(key):
            mirror = self.session.world.get(key)
            if mirror is not None:
                self.session.world.apply_removal(key)
            self._log("SYNC", "Object removed locally, broadcast gone: %s" % key)

    def _maybe_sync_funds(self):
        """Broadcast a changed household balance; apply nothing locally.

        The local game already holds the (possibly new) balance - we just
        publish it so peers converge to the same number. The first sample is
        absorbed as a baseline so connecting doesn't overwrite a peer
        mid-session.
        """
        if self.funds_sampler is None:
            return
        if self.engine is None or not self.engine.connected:
            return
        now = time.time()
        if now - self._last_funds_sent < self.funds_interval:
            return
        try:
            balance = self.funds_sampler()
        except Exception:
            self._log("ERROR", "funds sampler failed")
            return
        if balance is None:
            return
        balance = int(balance)
        if self._funds_baseline is None:
            self._funds_baseline = balance
            self._log("FUNDS", "baseline %s simoleons" % balance)
            return
        if abs(balance - self._funds_baseline) < 1:
            return
        if self.engine.send_funds_sync(balance):
            self._funds_baseline = balance
            self._last_funds_sent = now
            self._log("FUNDS", "broadcast balance %s (changed)" % balance)

    def _maybe_send_interactions(self):
        """Reconcile the mirror against what this client's sims are doing.

        Newly sampled interactions on free objects are proposed; interactions
        this client held but which are no longer sampled are ended. Keys the
        server just denied are skipped until their backoff expires, and keys
        that someone else currently holds are left alone.
        """
        if not self.interaction_sync or self._interaction_sampler is None:
            return
        if self.engine is None or not self.engine.connected:
            return
        now = time.time()
        if now - self._last_interaction_tick < self.interaction_interval:
            return
        self._last_interaction_tick = now
        try:
            sample = self._interaction_sampler()
        except Exception:
            self._log("ERROR", "interaction sampler failed")
            return
        if not sample:
            return
        mine = self.session.player_id
        active = {}
        for entry in sample:
            key = entry.get("key")
            if isinstance(key, str) and key:
                active[key] = entry
        mirror = self.session.interactions

        for key in list(mirror.keys()):
            entry = mirror.get(key)
            if entry is not None and entry["player_id"] == mine and key not in active:
                self.end_interaction(key)
        for key, entry in active.items():
            mirror = self.session.interactions.get(key)
            if mirror is not None:
                continue
            if now < self._denied_until.get(key, 0):
                continue
            if not self.propose_interaction(
                key,
                entry.get("interaction", ""),
                args=entry.get("args"),
                affordance=entry.get("affordance"),
                affordance_id=entry.get("affordance_id"),
                target=entry.get("target"),
            ):
                return