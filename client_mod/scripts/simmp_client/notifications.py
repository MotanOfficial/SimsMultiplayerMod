"""Toast-decision logic for in-game notifications (M13).

Pure stdlib logic, no game imports, so it is fully unit-testable offline.
`cheat_commands` (game-side) feeds every log line produced by the client
through `ToastFilter.pick()` and renders the returned text (or nothing) as a
toast on the game thread.

Decisions made here mirror what a human would want to see while actually
playing: connection/room/save/travel events, and interactions **on your own
sims** by another player. High-frequency chatter (ownership ack for your own
claims, released objects, remote sims' own idle interactions) is deliberately
silenced. A small per-bucket cooldown prevents toast spam from bursty
broadcasts.
"""

import time

COOLDOWN = 2.0


def shorten_key(key):
    """Human-friendly key: `sim:123456789012345678` -> `sim:345678`."""
    if key.startswith("sim:"):
        return "sim:%s" % str(key[len("sim:"):])[-6:]
    return key


def player_name(roster, player_id):
    """Resolve a player_id to a display name ("Player N" as fallback)."""
    if roster is None:
        return "Player %s" % player_id
    entry = roster.get(player_id)
    if entry and entry.get("name"):
        return entry["name"]
    presence = roster.get(player_id)
    if presence and presence.get("name"):
        return presence["name"]
    return "Player %s" % player_id


class ToastFilter(object):
    """Decides which client log lines become toasts (or None)."""

    def __init__(self, cooldown=COOLDOWN):
        self.cooldown = cooldown
        self._last_toast_at = {}

    def _gate(self, bucket):
        """Return True when a toast of `bucket` should be suppressed."""
        now = time.time()
        last = self._last_toast_at.get(bucket)
        if last is not None and now - last < self.cooldown:
            return True
        self._last_toast_at[bucket] = now
        return False

    def pick(self, line, self_player_id=None, roster=None, world=None):
        """Map one log line to a toast text (or None to stay console-only)."""
        if line.startswith("[MP][ERROR]"):
            return line
        if "[MP][NET] Connected to" in line:
            return "[MP] Connected to the server"
        if "[MP][NET] Disconnected" in line:
            return "[MP] Disconnected from the server"
        if "[MP][NET] Reconnecting" in line:
            return "[MP] Connection lost; reconnecting..."
        if "[MP][ROOM] Player " in line and (" joined " in line or " left " in line):
            if self._gate("room"):
                return None
            return line
        if "[MP][SAVE] received" in line:
            return line
        if "SAVE_ACK" in line and "reached" in line:
            return line
        if "[MP][TRAVEL] Travel invite to zone" in line:
            return self._travel_invite(line, roster)
        if "[MP][TRAVEL] Travel BEGIN" in line:
            return self._travel_phase(line, "begin")
        if "[MP][TRAVEL] Travel COMPLETE" in line:
            return self._travel_phase(line, "complete")
        if "[MP][TRAVEL] Travel ABORTED" in line:
            return "[MP] " + line.split("Travel ABORTED:", 1)[-1].strip()
        if "[MP][SYNC] Interaction start:" in line:
            return self._interaction_start(line, self_player_id, roster, world)
        if "[MP][SYNC] Object " in line and " owner ->" in line:
            return self._ownership(line, self_player_id, roster)
        return None

    def _travel_invite(self, line, roster):
        zone = line.split("Travel invite to zone ", 1)[-1].split(" from", 1)[0].strip()
        return "[MP] Travel invite to zone %s" % zone

    def _travel_phase(self, line, phase):
        if self._gate("travel_" + phase):
            return None
        zone = None
        for marker in ("to zone ", "for zone "):
            if marker in line:
                zone = line.split(marker, 1)[-1].strip()
                break
        head = "Traveling to" if phase == "begin" else "Arrived in"
        return "[MP] %s%s" % (head, (" zone " + zone) if zone else "")

    def _interaction_start(self, line, self_player_id, roster, world):
        payload = line.split("Interaction start:", 1)[-1].strip()
        parts = payload.rsplit(" by ", 1)
        if len(parts) != 2:
            return None
        rest, pid_text = parts
        try:
            pid = int(pid_text.strip())
        except (TypeError, ValueError):
            return None
        if self_player_id is not None and pid == self_player_id:
            return None
        on_parts = rest.rsplit(" on ", 1)
        if len(on_parts) != 2:
            return None
        interaction, key_text = on_parts
        key = key_text.strip().strip("'")
        owner = None
        if world is not None:
            entry = world.get(key)
            owner = entry.owner if entry is not None else None
        if owner is None or owner != self_player_id:
            return None
        if self._gate("interaction"):
            return None
        who = player_name(roster, pid)
        return "[MP] %s is %s on %s" % (who, interaction.strip(), shorten_key(key))

    def _ownership(self, line, self_player_id, roster):
        head, owner_text = line.split(" owner ->", 1)
        key = head.split("Object ", 1)[-1].strip().strip("'")
        owner_text = owner_text.strip()
        if owner_text in ("None", "null", ""):
            return None
        try:
            owner = int(owner_text)
        except (TypeError, ValueError):
            return None
        if owner == self_player_id:
            return None
        if self._gate("ownership"):
            return None
        who = player_name(roster, owner)
        return "[MP] %s took over %s" % (who, shorten_key(key))