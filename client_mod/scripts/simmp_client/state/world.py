"""Client-side mirror of the replicated world state.

The server is authoritative for object ownership; the mirror tracks the
latest full snapshot (`WORLD_STATE`) plus incremental deltas (`WORLD_DELTA`),
Lamport-ordered by the server's per-room `seq`, and offers a simple linear
smoothing helper for easing rendered positions toward the latest snapshot.
"""

import time


def lerp(a, b, t):
    """Linear interpolation: t=0 -> a, t=1 -> b."""
    return a + (b - a) * t


class ObjectMirror:
    __slots__ = ("key", "owner", "fields", "anchor", "receive_time", "anchor_time")

    def __init__(self, key, owner=None, fields=None):
        self.key = key
        self.owner = owner
        self.fields = dict(fields) if fields else {}
        self.anchor = None
        now = time.time()
        self.receive_time = now
        self.anchor_time = now

    def merge_fields(self, updates, now=None):
        """Apply a field delta, capturing an anchor when a position moves."""
        now = now if now is not None else time.time()
        before = self.position()
        self.fields.update(updates or {})
        after = self.position()
        if before is not None and after is not None and before != after:
            self.anchor = before
            self.anchor_time = now
        self.receive_time = now

    def position(self):
        fields = self.fields
        if not all(name in fields for name in ("x", "y", "z")):
            return None
        return (float(fields["x"]), float(fields["y"]), float(fields["z"]))

    def display_position(self, now=None, rate=2.0):
        """Eased position toward the latest snapshot.

        `rate` (per second) controls convergence: right after a move the
        position lerps from the previous snapshot, fully catching up after
        `1/rate` seconds. With no anchor yet the latest position is exact.
        Returns (x, y, z) or None when the object has no position.
        """
        target = self.position()
        if target is None:
            return None
        now = now if now is not None else time.time()
        if self.anchor is None:
            return target
        t = min(1.0, rate * max(0.0, now - self.anchor_time))
        return tuple(lerp(self.anchor[i], target[i], t) for i in range(3))


class WorldMirror:
    def __init__(self):
        self.room_id = None
        self.zone_id = None
        self.objects = {}
        self.last_seq = 0

    def reset(self, room_id, zone_id=None):
        self.room_id = room_id
        self.zone_id = zone_id
        self.objects = {}
        self.last_seq = 0

    def apply_full(self, room_id, zone_id, objects):
        self.reset(room_id, zone_id)
        for entry in objects:
            mirror = ObjectMirror(entry["key"], entry.get("owner"), entry.get("fields"))
            self.objects[mirror.key] = mirror

    def apply_delta(self, room_id, zone_id, seq, updates):
        if room_id != self.room_id or zone_id != self.zone_id:
            return
        if seq <= self.last_seq:
            return
        self.last_seq = seq
        now = time.time()
        for update in updates:
            mirror = self.objects.get(update["key"])
            if mirror is None:
                mirror = ObjectMirror(update["key"])
                self.objects[mirror.key] = mirror
            mirror.merge_fields(update.get("fields"), now)

    def apply_ownership(self, key, owner, zone_id=None):
        if zone_id is not None and zone_id != self.zone_id:
            return
        mirror = self.objects.get(key)
        if mirror is None:
            mirror = ObjectMirror(key)
            self.objects[mirror.key] = mirror
        mirror.owner = owner

    def apply_claim_ack(self, key, owner):
        self.apply_ownership(key, owner)

    def apply_removal(self, key, zone_id=None):
        if zone_id is not None and zone_id != self.zone_id:
            return
        self.objects.pop(key, None)

    def get(self, key):
        return self.objects.get(key)

    def keys(self):
        return list(self.objects.keys())

    def count(self):
        return len(self.objects)