"""Game-thread tick pump that keeps running while the clock is paused.

Joiner field logs showed repeating real-time alarms still going silent for
tens of seconds (only revived by ``mp.status``). Host alarms stayed healthy.
This module monkey-patches a few always-on game update paths so multiplayer
keeps draining TCP / mirroring even when the alarm service flakes.
"""

from __future__ import division

import time

_INTERVAL = 0.4
_last_pump_at = 0.0
_installed = False
_in_pump = False


def pump():
    """Throttle and run one multiplayer game-thread tick."""
    global _last_pump_at, _in_pump
    if _in_pump:
        return
    now = time.time()
    if now - _last_pump_at < _INTERVAL:
        return
    _last_pump_at = now
    _in_pump = True
    try:
        from simmp_client.commands import cheat_commands

        client = cheat_commands.get_client()
        if client is None:
            return
        pump_fn = getattr(client, "game_thread_pump", None)
        if callable(pump_fn):
            pump_fn()
    except Exception:
        pass
    finally:
        _in_pump = False


def _wrap(module_name, class_name, method_name):
    try:
        module = __import__(module_name, fromlist=[class_name])
        cls = getattr(module, class_name, None)
        if cls is None:
            return False
        original = getattr(cls, method_name, None)
        if original is None or getattr(original, "_simmp_tick_pump", False):
            return False

        def wrapped(self, *args, **kwargs):
            try:
                pump()
            except Exception:
                pass
            return original(self, *args, **kwargs)

        wrapped._simmp_tick_pump = True
        setattr(cls, method_name, wrapped)
        return True
    except Exception:
        return False


def install():
    """Install permanent update hooks (not tied to deep session role)."""
    global _installed
    if _installed:
        return True
    candidates = (
        ("zone", "Zone", "update"),
        ("zone", "Zone", "shift_turn"),
        ("server.client", "Client", "process_zone_update"),
        ("server.client", "Client", "_process_zone_update"),
        ("server.client", "Client", "send_to_gsi"),
        ("clock", "GameClock", "advance_for_time"),
        ("clock", "GameClock", "service_tick"),
        ("sims.sim_info_manager", "SimInfoManager", "on_all_households_and_sim_infos_loaded"),
    )
    ok = False
    for item in candidates:
        if _wrap(*item):
            ok = True
    _installed = ok
    return ok
