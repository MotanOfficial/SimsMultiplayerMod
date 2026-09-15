"""Offline presence helpers for the simmp client mod.

Pure Python. The game-specific sampler lives in game_hooks; these functions
build and format presence payloads and status lines.
"""

import time


def build_presence(zone_id, lot_id, timestamp=None):
    return {
        "zone_id": zone_id,
        "lot_id": lot_id,
        "timestamp": timestamp if timestamp is not None else time.time(),
    }


def format_presence(entry):
    """Single-line representation for mp.status / mp.who."""
    if not isinstance(entry, dict):
        return "-"
    zone = entry.get("zone_id", "?")
    lot = entry.get("lot_id", "?")
    stamp = entry.get("timestamp")
    age = ""
    if stamp:
        secs = max(0, int(time.time() - stamp))
        age = " %ss ago" % secs
    return "zone=%s lot=%s%s" % (zone, lot, age)