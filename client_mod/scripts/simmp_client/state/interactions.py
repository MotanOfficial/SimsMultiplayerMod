"""Client-side mirror of reserved interactions (`INTERACTION_*`).

Who is interacting with which object is server-authoritative. This mirror
tracks the latest full snapshot (`INTERACTION_STATE`, sent on join) plus the
incremental `INTERACTION_START`/`INTERACTION_FREE` broadcasts, and records
release cooldowns so `mp.inter` can show why an object is temporarily blocked.
"""


class InteractionMirror:
    def __init__(self):
        self.room_id = None
        self.interactions = {}
        self.cooldowns = {}

    def reset(self, room_id):
        self.room_id = room_id
        self.interactions = {}
        self.cooldowns = {}

    def apply_full(self, room_id, interactions):
        self.reset(room_id)
        for entry in interactions:
            self.interactions[entry["object_key"]] = {
                "player_id": entry["player_id"],
                "interaction": entry["interaction"],
                "started_at": entry["started_at"],
                "args": entry.get("args"),
                "affordance": entry.get("affordance"),
                "affordance_id": entry.get("affordance_id"),
                "target": entry.get("target"),
            }

    def apply_start(self, room_id, object_key, player_id, interaction, started_at, args=None, affordance=None, affordance_id=None, target=None):
        if room_id != self.room_id:
            return
        self.interactions[object_key] = {
            "player_id": player_id,
            "interaction": interaction,
            "started_at": started_at,
            "args": args,
            "affordance": affordance,
            "affordance_id": affordance_id,
            "target": target,
        }
        self.cooldowns.pop(object_key, None)

    def apply_free(self, room_id, object_key, cooldown_until):
        if room_id != self.room_id:
            return
        self.interactions.pop(object_key, None)
        self.cooldowns[object_key] = cooldown_until

    def get(self, object_key):
        return self.interactions.get(object_key)

    def cooldown_until(self, object_key):
        return self.cooldowns.get(object_key, 0)

    def keys(self):
        return list(self.interactions.keys())

    def count(self):
        return len(self.interactions)

    def clear_cooldown(self, object_key):
        self.cooldowns.pop(object_key, None)