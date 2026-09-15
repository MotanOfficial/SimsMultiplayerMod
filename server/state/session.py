"""Authoritative session state: connected players and rooms."""

import time

from simmp.constants import (
    CLOCK_SPEED_NORMAL,
    DEFAULT_ROOM_ID,
    MIN_CLOCK_SPEED,
)


class Player:
    def __init__(self, player_id, connection, name, joined_at=None):
        self.player_id = player_id
        self.connection = connection
        self.name = name
        self.joined_at = joined_at if joined_at is not None else time.time()
        self.room_id = None
        self.presence = None
        self.last_event_seq = 0
        self.clock_sync = None
        self.clock_ready = False
        self.clock_zone = None
        self.disconnected_at = None

    @property
    def connected(self):
        return self.connection is not None

    def as_dict(self):
        return {
            "player_id": self.player_id,
            "name": self.name,
            "connected": self.connected,
        }


class Room:
    def __init__(self, room_id, created_at=None):
        self.room_id = room_id
        self.created_at = created_at if created_at is not None else time.time()
        self.members = {}
        # Shared clock. `desired` is the last player's chosen speed (last
        # change wins); the custom clock gate forces PAUSED while any
        # participant (including ghosts, until they rejoin or are evicted)
        # has not signalled TIME_READY. `by_player` names who set `desired`.
        self.clock = {
            "desired": CLOCK_SPEED_NORMAL,
            "by_player": None,
            "ticks": None,
        }

    def as_dict(self):
        return {
            "room_id": self.room_id,
            "players": [player.as_dict() for player in self.members.values()],
            "clock": {
                "desired": self.clock["desired"],
                "by_player": self.clock["by_player"],
            },
        }


class WorldObject:
    """Server-authoritative snapshot of a replicated object in one room."""

    def __init__(self, key):
        self.key = key
        self.owner = None
        self.fields = {}
        self.rev = 0


class Interaction:
    """A reserved interaction on an object key in one room.

    The first player to request an object's interaction holds it (FCFS).
    After it ends a short cooldown blocks counter-requests on the same key.
    """

    def __init__(self, object_key, player_id, interaction, started_at, args=None, affordance=None, affordance_id=None, target=None):
        self.object_key = object_key
        self.player_id = player_id
        self.interaction = interaction
        self.started_at = started_at
        self.args = dict(args) if args else None
        self.affordance = affordance
        self.affordance_id = affordance_id
        self.target = target


class Session:
    def __init__(self):
        self._players = {}
        self._rooms = {DEFAULT_ROOM_ID: Room(DEFAULT_ROOM_ID)}
        self._next_player_id = 1000
        self._by_client_id = {}
        self._world_by_room = {}
        self._world_seq_by_room = {}
        self._interactions_by_room = {}
        self._cooldowns_by_room = {}

    @property
    def players(self):
        return dict(self._players)

    @property
    def rooms(self):
        return dict(self._rooms)

    def create_player(self, connection, name):
        player = Player(self._next_player_id, connection, name)
        self._next_player_id += 1
        self._players[player.player_id] = player
        return player

    def get_player(self, player_id):
        return self._players.get(player_id)

    def bind_client_id(self, client_id, player_id):
        self._by_client_id[client_id] = player_id

    def player_for_client_id(self, client_id):
        if client_id is None:
            return None
        player_id = self._by_client_id.get(client_id)
        if player_id is None:
            return None
        return self._players.get(player_id)

    def disconnect_player(self, player_id, conn):
        """Mark a player disconnected iff `conn` is still its live connection.

        Guards against identity takeover: when a reconnect adopts the same
        player record, the old socket's disconnect path must be a no-op, so a
        later PLAYER_LEFT is never emitted for a player that just reconnected.
        """
        player = self._players.get(player_id)
        if player is None or player.connection is not conn:
            return None
        room_id = player.room_id
        if room_id:
            room = self._rooms.get(room_id)
            if room is not None:
                room.members.pop(player.player_id, None)
        player.connection = None
        player.presence = None
        player.clock_ready = False
        player.disconnected_at = time.time()
        return (room_id, player.name, player.player_id)

    def get_room(self, room_id):
        return self._rooms.get(room_id)

    def get_or_create_room(self, room_id):
        room = self._rooms.get(room_id)
        if room is None:
            room = Room(room_id)
            self._rooms[room_id] = room
        return room

    def move_player(self, player, room_id):
        old_room_id = player.room_id
        if old_room_id:
            old_room = self._rooms.get(old_room_id)
            if old_room is not None:
                old_room.members.pop(player.player_id, None)
        new_room = self.get_or_create_room(room_id)
        new_room.members[player.player_id] = player
        player.room_id = new_room.room_id
        return old_room_id, new_room.room_id

    def expire_presence(self, ttl):
        now = time.time()
        for player in self._players.values():
            presence = player.presence
            if presence is not None and now - presence.get("received_at", 0) > ttl:
                player.presence = None

    def next_world_seq(self, room_id):
        self._world_seq_by_room[room_id] = self._world_seq_by_room.get(room_id, 0) + 1
        return self._world_seq_by_room[room_id]

    def get_world_object(self, room_id, key):
        return self._world_by_room.get(room_id, {}).get(key)

    def get_world_objects(self, room_id):
        objects = self._world_by_room.get(room_id, {})
        return [self._world_entry(obj) for obj in objects.values()]

    def _world_entry(self, obj):
        return {
            "key": obj.key,
            "owner": obj.owner,
            "fields": dict(obj.fields),
        }

    def claim_object(self, room_id, key, player_id):
        """Attempt to acquire ownership. Returns (ok, already_owner, prev_owner)."""
        objects = self._world_by_room.setdefault(room_id, {})
        obj = objects.get(key)
        if obj is None:
            obj = WorldObject(key)
            objects[key] = obj
        if obj.owner is not None and obj.owner != player_id:
            return (False, False, obj.owner)
        obj.owner = player_id
        return (True, obj.owner == player_id and obj.owner is not None, None)

    def release_object(self, room_id, key, player_id):
        """Release ownership if held by `player_id`. Returns True if released."""
        obj = self._world_by_room.get(room_id, {}).get(key)
        if obj is None or obj.owner != player_id:
            return False
        obj.owner = None
        return True

    def apply_world_update(self, room_id, key, fields, player_id):
        """Apply a delta to an owned object.

        Returns a (status, detail) tuple:
          ("ok", changed_fields)    - applied; changed is the delta actually sent
          ("locked", owner_player_id) - owned by someone else
          ("not_found", None)       - key was never claimed (claim it first)
        """
        obj = self._world_by_room.get(room_id, {}).get(key)
        if obj is None:
            return ("not_found", None)
        if obj.owner != player_id:
            return ("locked", obj.owner)
        changed = {
            name: value
            for name, value in fields.items()
            if obj.fields.get(name) != value
        }
        obj.fields.update(fields)
        return ("ok", changed)

    def get_interaction(self, room_id, key):
        return self._interactions_by_room.get(room_id, {}).get(key)

    def get_room_interactions(self, room_id):
        interactions = self._interactions_by_room.get(room_id, {})
        return [self._interaction_entry(interaction) for interaction in interactions.values()]

    def _interaction_entry(self, interaction):
        entry = {
            "object_key": interaction.object_key,
            "player_id": interaction.player_id,
            "interaction": interaction.interaction,
            "started_at": interaction.started_at,
        }
        if interaction.args:
            entry["args"] = interaction.args
        if interaction.affordance is not None:
            entry["affordance"] = interaction.affordance
        if interaction.affordance_id is not None:
            entry["affordance_id"] = interaction.affordance_id
        if interaction.target is not None:
            entry["target"] = interaction.target
        return entry

    def request_interaction(self, room_id, key, player_id, interaction, args=None, now=None, cooldown_override=None, affordance=None, affordance_id=None, target=None):
        """Reserve `key` for `player_id`'s interaction, first-come-first-served.

        Returns a (status, detail) tuple:
          ("start", entry)   - granted (or renewed by the same holder)
          ("busy", holder_id) - another player currently holds the key
          ("cooldown", cooldown_until) - key was recently released
        """
        now = now if now is not None else time.time()
        interactions = self._interactions_by_room.setdefault(room_id, {})
        current = interactions.get(key)
        if current is not None:
            if current.player_id == player_id:
                current.interaction = interaction
                current.args = dict(args) if args else None
                current.affordance = affordance
                current.affordance_id = affordance_id
                current.target = target
                current.started_at = now
                return ("start", self._interaction_entry(current))
            return ("busy", current.player_id)
        cooldown_until = self._cooldowns_by_room.get(room_id, {}).get(key, 0)
        if cooldown_until > now:
            return ("cooldown", cooldown_until)
        if cooldown_until:
            del self._cooldowns_by_room[room_id][key]
        held = Interaction(key, player_id, interaction, now, args, affordance, affordance_id, target)
        interactions[key] = held
        return ("start", self._interaction_entry(held))

    def end_interaction(self, room_id, key, player_id, cooldown, now=None):
        """End an interaction held by `player_id`, starting the release cooldown.

        Returns a (status, cooldown_until) tuple: ("ended", until) or
        ("not_held", None).
        """
        now = now if now is not None else time.time()
        interactions = self._interactions_by_room.get(room_id, {})
        current = interactions.get(key)
        if current is None or current.player_id != player_id:
            return ("not_held", None)
        del interactions[key]
        cooldown_until = now + cooldown
        self._cooldowns_by_room.setdefault(room_id, {})[key] = cooldown_until
        return ("ended", cooldown_until)

    def expire_interactions(self, max_duration, cooldown, now=None):
        """Auto-release interactions that ran longer than `max_duration`.

        Returns {room_id: [(key, cooldown_until)]} for each released key so the
        server can broadcast `INTERACTION_FREE`.
        """
        now = now if now is not None else time.time()
        released = {}
        for room_id, interactions in list(self._interactions_by_room.items()):
            for key, interaction in list(interactions.items()):
                if now - interaction.started_at > max_duration:
                    del interactions[key]
                    cooldown_until = now + cooldown
                    self._cooldowns_by_room.setdefault(room_id, {})[key] = cooldown_until
                    released.setdefault(room_id, []).append((key, cooldown_until))
        return released

    def release_player_interactions(self, player_id, cooldown, now=None):
        """Release every interaction held by `player_id` (e.g. on disconnect).

        Returns [(room_id, key, cooldown_until)] for broadcast.
        """
        now = now if now is not None else time.time()
        released = []
        for room_id, interactions in list(self._interactions_by_room.items()):
            for key, interaction in list(interactions.items()):
                if interaction.player_id != player_id:
                    continue
                del interactions[key]
                cooldown_until = now + cooldown
                self._cooldowns_by_room.setdefault(room_id, {})[key] = cooldown_until
                released.append((room_id, key, cooldown_until))
        return released

    def release_player_world(self, player_id):
        """Clear ownership of every object `player_id` owns.

        Returns [(room_id, key)] so the server can broadcast `OBJECT_OWNERSHIP`
        (owner null). World ownership normally outlives a disconnect (holding
        period), so this only runs on ghost eviction.
        """
        released = []
        for room_id, objects in self._world_by_room.items():
            for key, obj in list(objects.items()):
                if obj.owner == player_id:
                    obj.owner = None
                    released.append((room_id, key))
        return released

    def expire_ghosts(self, player_ttl, interaction_cooldown, now=None):
        """Evict players who stayed disconnected longer than `player_ttl`.

A disconnected player stays registered as a "ghost": their world ownership
and held interactions are kept (reserved) so a quick takeover/reconnect
restores the exact same state. After the TTL the ghost is evicted: its
objects and interactions are released (so the room can reuse the keys) and
its identity is dropped, so a much-later reconnect starts fresh (new
player_id).

        Returns a dict for the server to broadcast:
          {"interactions": [(room_id, key, cooldown_until)],
           "world": [(room_id, key, player_id)],
           "players": [player_id]}
        """
        now = now if now is not None else time.time()
        released = {"interactions": [], "world": [], "players": []}
        for player in list(self._players.values()):
            if player.connection is not None or player.disconnected_at is None:
                continue
            if now - player.disconnected_at <= player_ttl:
                continue
            released["interactions"].extend(
                self.release_player_interactions(player.player_id, interaction_cooldown, now)
            )
            world_released = self.release_player_world(player.player_id)
            released["world"].extend(
                (room_id, key, player.player_id) for room_id, key in world_released
            )
            self._forget_player(player)
            released["players"].append(player.player_id)
        return released

    def _forget_player(self, player):
        room = self._rooms.get(player.room_id) if player.room_id else None
        if room is not None:
            room.members.pop(player.player_id, None)
        self._players.pop(player.player_id, None)
        for client_id, player_id in list(self._by_client_id.items()):
            if player_id == player.player_id:
                self._by_client_id.pop(client_id, None)
        player.room_id = None

    def set_clock_ready(self, player_id):
        """Mark a player as ready to play (zone loaded, save applied)."""
        player = self._players.get(player_id)
        if player is None:
            return False
        player.clock_ready = True
        return True

    def clear_room_clock_ready(self, room_id):
        """Drop readiness for every member of a room (used on zone change).

        The time gate then stays closed until each member reports ready in the
        new zone, so nobody plays ahead while a group travels.
        """
        for player in self._players.values():
            if player.room_id == room_id:
                player.clock_ready = False

    def clock_gate_open(self, room_id):
        """True when every participant (members + ghosts) has signalled ready."""
        participants = [p for p in self._players.values() if p.room_id == room_id]
        if not participants:
            return False
        return all(p.clock_ready for p in participants)

    def clock_snapshot(self, room_id):
        """Compact clock state dict for broadcast / status-file inclusion."""
        room = self._rooms.get(room_id)
        if room is None:
            return None
        participants = [p for p in self._players.values() if p.room_id == room_id]
        gate_closed = not participants or not all(p.clock_ready for p in participants)
        ready = [p.player_id for p in participants if p.clock_ready]
        return {
            "speed": MIN_CLOCK_SPEED if gate_closed else room.clock["desired"],
            "desired": room.clock["desired"],
            "by_player": room.clock["by_player"],
            "ticks": room.clock["ticks"],
            "gate": gate_closed,
            "ready": ready,
            "participants": [p.player_id for p in participants],
        }