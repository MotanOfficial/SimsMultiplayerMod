"""Game-facing hooks.

The Sims 4 imports are done lazily inside the functions so this module (and
anything that imports it) still works on a regular Python interpreter for
unit testing.

Alarm API grounded in community documentation/alarms examples:
    alarms.add_alarm_real_time(owner, TimeSpan(interval_in_real_seconds(n)),
                               callback, repeating=True, use_sleep_time=True,
                               cross_zone=False)
The callback receives the alarm handle and should return True to keep the
alarm repeating.
"""


def _alarm_imports():
    """Resolve the alarms/clock modules and a TimeSpan builder, or raise."""
    import alarms  # noqa: F401
    import clock

    from date_and_time import TimeSpan

    try:
        from sims4.clock import interval_in_real_seconds
    except Exception:
        interval_in_real_seconds = None
    return alarms, clock, TimeSpan, interval_in_real_seconds


def _real_time_span(seconds):
    """A real-time TimeSpan for `seconds`, tolerating both span builders.

    Some builders (`interval_in_real_seconds`) already return a
    ``TimeSpan``; others return raw ticks. Never double-wrap a TimeSpan.
    """
    alarms, clock, TimeSpan, sims4_builder = _alarm_imports()
    for builder in (
        getattr(clock, "interval_in_real_seconds", None),
        sims4_builder,
        getattr(clock, "real_seconds", None),
    ):
        if builder is None:
            continue
        try:
            span = builder(seconds)
            if not isinstance(span, TimeSpan):
                span = TimeSpan(span)
            return span
        except Exception:
            continue
    raise RuntimeError("no real-time interval builder available")


def add_alarm_real_time(owner, seconds, callback, repeating=False):
    """Schedule a real-time alarm and return the handle (or None).

    Ground-truth signature from the shipped ``simulation/alarms.py`` (this
    game patch, decompiled from the running build):

        def add_alarm_real_time(owner, time_span, callback,
                                repeating=False, use_sleep_time=True,
                                cross_zone=False)

    There is no ``add_one_off_real_time`` in this build at all; a one-shot
    is just ``add_alarm_real_time(..., repeating=False)``. The callback is
    invoked with the (single) AlarmHandle argument. ``AlarmHandle`` keeps a
    ``weakref.ref(owner)``, so ``owner`` must be weakref-able (a plain
    ``object()`` is NOT; any class instance is).
    """
    handle = None
    try:
        alarm, clock, _, _ = _alarm_imports()
        if not hasattr(alarm, "add_alarm_real_time"):
            return None
        span = _real_time_span(seconds)
        for kwargs in (
            dict(repeating=repeating, use_sleep_time=True, cross_zone=False),
            dict(repeating=repeating),
        ):
            try:
                handle = alarm.add_alarm_real_time(owner, span, callback, **kwargs)
            except TypeError:
                continue
            except Exception:
                continue
            if handle is not None:
                break
    except Exception:
        handle = None
    return handle


def add_repeating_real_time_alarm(owner, seconds, callback):
    return add_alarm_real_time(owner, seconds, callback, repeating=True)


def cancel_alarm(handle):
    if handle is None:
        return
    try:
        import alarms

        alarms.cancel_alarm(handle)
    except Exception:
        pass


def _save_roots():
    """Candidate save directories (newest/active first), guarded for offline use."""
    roots = []
    try:
        import os

        profile = os.environ.get("SIM4_MP_SAVE_ROOT")
        if profile:
            roots.append(os.path.join(profile, "saves"))
        user = os.path.expanduser("~")
        roots.append(os.path.join(user, "Documents", "Electronic Arts", "The Sims 4", "saves"))
    except Exception:
        pass
    seen = set()
    unique = []
    for root in roots:
        if root not in seen:
            seen.add(root)
            unique.append(root)
    return unique


def find_save_directory(slot=None, prefer_slot=True, roots=None):
    """Resolve which saves folder an incoming `slot` should be written to.

    The game keeps saves under `Documents/Electronic Arts/The Sims 4/saves`,
    sometimes inside a per-profile subfolder; a slot written into the wrong
    profile is invisible in-game. Consider every candidate and its immediate
    subfolders, preferring one that already holds a file with the same name
    (`prefer_slot`), else the folder with the most `*.save` files (ties go
    to the deeper one), else the first existing root, else `None`.

    Pure filesystem code - works on any interpreter, used by tests too.
    """
    import os

    candidates = roots if roots is not None else _save_roots()
    directories = []
    for root in candidates:
        if not os.path.isdir(root):
            continue
        directories.append(root)
        try:
            for entry in sorted(os.listdir(root)):
                full = os.path.join(root, entry)
                if os.path.isdir(full):
                    directories.append(full)
        except OSError:
            pass
    if prefer_slot and slot:
        for directory in sorted(directories, key=lambda d: d.count(os.sep)):
            if slot and os.path.isfile(os.path.join(directory, slot)):
                return directory
    scored = [
        (
            sum(
                1
                for name in os.listdir(directory)
                if name.lower().endswith(".save") and os.path.isfile(os.path.join(directory, name))
            ),
            directory,
        )
        for directory in directories
    ]
    if scored:
        return max(scored, key=lambda item: (item[0], item[1].count(os.sep)))[1]
    for root in candidates:
        if os.path.isdir(root):
            return root
    return candidates[0] if candidates else None


def receive_save(slot, data):
    """Write an inbound save `slot` (bare filename) with `data` bytes.

    Returns the final path (raises on failure). Called by the connectivity
    layer on the game thread once a SAVE_PUSH transfer completes.
    """
    from simmp_client.state.save_transfer import atomic_write

    directory = find_save_directory(slot)
    if not directory:
        raise OSError("no writable save directory found")
    path = atomic_write(directory, slot, data)
    try:
        _applier_log("[MP][SAVE] received %s -> %s" % (slot, path))
    except Exception:
        pass
    return path


_applier_log = lambda line: None  # noqa: E731  (installed in-game by cheat_commands)


def set_interaction_logger(console):
    """Install a callable that receives `[MP][MIRROR] ...` console lines.

    Cheat commands wire this to the in-game cheat console on the game thread.
    Outside the game it stays a no-op so the applier never touches stdout.
    """
    global _applier_log
    if callable(console):
        _applier_log = console
    else:
        _applier_log = lambda line: None  # noqa: E731


def add_one_off_real_time_alarm(owner, seconds, callback):
    return add_alarm_real_time(owner, seconds, callback, repeating=False)


def diagnose_alarms():
    """Probe which alarm APIs this game patch supports and why they fail.

    Returns a list of strings for `mp.diag`: module resolution, which
    span builders work, and the exact exception (if any) raised by each
    known alarm-call signature. Lets us stop guessing the live API.
    """
    lines = []
    try:
        alarm, clock, TimeSpan, sims4_builder = _alarm_imports()
        lines.append("imports: alarms=%s clock=%s TimeSpan=%s sims4.clock.builder=%s"
                     % (alarm, clock, TimeSpan, sims4_builder))
    except Exception as exc:
        lines.append("imports FAILED: %r" % (exc,))
        return lines
    for label, mod in (("clock", clock),):
        interesting = sorted(
            name for name in dir(mod)
            if "interval" in name or "real" in name or "second" in name or "minute" in name
        )
        lines.append("clock attrs: %r" % (interesting,))
    try:
        import sims4.clock as s4clock
        lines.append("sims4.clock attrs: %r" % (
            sorted(n for n in dir(s4clock)
                   if "interval" in n or "real" in n or "second" in n or "minute" in n),
        ))
    except Exception as exc:
        lines.append("sims4.clock import FAILED: %r" % (exc,))
    candidate = getattr(clock, "interval_in_real_seconds", None)
    if candidate is not None:
        try:
            lines.append("clock.interval_in_real_seconds(0.5) -> %r"
                         % candidate(0.5))
        except Exception as exc:
            lines.append("clock.interval_in_real_seconds(0.5) raised %s: %s"
                         % (type(exc).__name__, exc))
    try:
        span = _real_time_span(0.5)
        lines.append("span: real-time 0.5s built via %r" % (_real_time_span.__name__,))
    except Exception as exc:
        span = None
        lines.append("span FAILED: %r" % (exc,))
    probes = []
    if span is not None:

        class _ProbeOwner(object):
            pass  # weakref-able, unlike a bare object()

        owner = _ProbeOwner()
        probes.append(("rt_repeat", lambda: alarm.add_alarm_real_time(owner, span, cb, repeating=True, use_sleep_time=True, cross_zone=False)))
        probes.append(("rt_once", lambda: alarm.add_alarm_real_time(owner, span, cb)))
        if hasattr(alarm, "add_alarm"):
            probes.append(("sim_once", lambda: alarm.add_alarm(owner, span, cb)))
        else:
            lines.append("NOTE: alarms.add_alarm MISSING (sim-time variant)")
        cb = lambda *args: True  # noqa: E731
        created = []
        for name, fn in probes:
            try:
                handle = fn()
                lines.append("%s -> handle=%s" % (name, handle))
                if handle is not None:
                    created.append(handle)
            except TypeError as exc:
                lines.append("%s -> TypeError: %s" % (name, exc))
            except Exception as exc:
                lines.append("%s -> ERROR %s: %s" % (name, type(exc).__name__, exc))
        for handle in created:
            try:
                alarm.cancel_alarm(handle)
            except Exception:
                try:
                    alarm.cancel(handle)
                except Exception:
                    pass
    else:
        lines.append("NOTE: frame builder FAILED; alarm scheduling not probed")
    return lines


def current_zone():
    """The game's current Zone object (or None). Tolerant of API drift.

    Modern builds expose ``services.current_zone()``; older ones expose the
    no-arg ``services.get_zone()``. Recent builds changed ``get_zone`` to take
    a required ``zone_id`` argument, so it is only used as a last resort.
    """
    try:
        import services

        zone = services.current_zone()
        if zone is not None:
            return zone
    except Exception:
        pass
    try:
        import services

        zone_manager = services.get_zone_manager()
        if zone_manager is not None:
            zone = getattr(zone_manager, "current_zone", None)
            if zone is not None:
                return zone
    except Exception:
        pass
    try:
        import services

        return services.get_zone()
    except Exception:
        return None


def sample_current_zone():
    """Best-effort zone sampler for the game.  Returns (zone_id, lot_id) or None."""
    try:
        import services

        zone = current_zone()
        if zone is None:
            return None
        zone_id = getattr(zone, "id", None)
        if zone_id is None:
            return None
        lot = getattr(zone, "lot", None)
        lot_id = None
        if lot is not None:
            lot_id = getattr(lot, "lot_id", None)
            if lot_id is None:
                lot_id = getattr(lot, "id", None)
        return (zone_id, lot_id)
    except Exception:
        return None


def current_zone_id():
    """Best-effort current zone id (int) or None when unavailable."""
    try:
        import services

        return services.current_zone_id()
    except Exception:
        try:
            return getattr(current_zone(), "id", None)
        except Exception:
            return None


class ZoneRunState(object):
    """Live zone state snapshot (values read via game services, never raising)."""

    __slots__ = ("running", "zone_id", "loading", "has_clock", "state")

    def __init__(self, running, zone_id, loading, has_clock, state):
        self.running = running
        self.zone_id = zone_id
        self.loading = loading
        self.has_clock = has_clock
        self.state = state

    def __str__(self):
        return "running=%s zone=%s loading=%s clock=%s state=%s" % (
            self.running, self.zone_id, self.loading, self.has_clock, self.state)


def current_zone_running_state():
    """Snapshot what the game thinks about the current zone.

    Returns a `ZoneRunState` (never raises). `state` is the raw zone-state
    enum name (e.g. ``RUNNING``/``ZONE_INIT``) when readable, else "unknown".
    """
    try:
        import services
    except Exception:
        return ZoneRunState(False, None, False, False, "no-services")
    try:
        zone = current_zone()
    except Exception:
        zone = None
    if zone is None:
        return ZoneRunState(False, None, False, False, "no-zone")
    zone_id = None
    try:
        zone_id = services.current_zone_id()
    except Exception:
        zone_id = None
    if zone_id is None:
        zone_id = getattr(zone, "id", None)
    try:
        running = bool(getattr(zone, "is_zone_running", False))
    except Exception:
        running = False
    try:
        loading = bool(getattr(zone, "is_zone_loading", False))
    except Exception:
        loading = False
    has_clock = False
    try:
        for alias in ("game_clock_service", "get_game_clock", "game_clock"):
            fn = getattr(services, alias, None)
            if fn is not None and fn() is not None:
                has_clock = True
                break
    except Exception:
        has_clock = False
    state = "unknown"
    try:
        zone_state = getattr(zone, "_zone_state", None)
        if zone_state is not None:
            state = getattr(zone_state, "name", str(zone_state))
    except Exception:
        state = "unknown"
    return ZoneRunState(running, zone_id, loading, has_clock, state)


def current_zone_is_running():
    """True while in a playable zone.

    The canonical check is ``zone.is_zone_running`` (zone state RUNNING),
    but it reads False during some live-lot timings, so a loaded lot whose
    game clock exists and that is not still loading also counts as running.
    """
    try:
        state = current_zone_running_state()
    except Exception:
        return False
    if state.running:
        return True
    if state.has_clock and not state.loading and state.zone_id is not None:
        return True
    return False


def sample_game_clock():
    """Best-effort game clock sample.

    Returns (absolute_ticks, clock_speed) or None. `clock_speed` is the raw
    int value of the ClockSpeedMode enum, serialized onto the wire.
    """
    try:
        import services
        from clock import ClockSpeedMode

        game_clock = services.game_clock_service()
        if game_clock is None:
            return None
        now = game_clock.now()
        if now is None:
            return None
        absolute_ticks = getattr(now, "absolute_ticks", None)
        if callable(absolute_ticks):
            absolute_ticks = absolute_ticks()
        if absolute_ticks is None:
            return None
        speed = getattr(game_clock, "clock_speed", ClockSpeedMode.NORMAL)
        speed_value = getattr(speed, "value", 0)
        return (int(absolute_ticks), int(speed_value))
    except Exception:
        return None


def get_clock_speed():
    """Best-effort current game clock speed (ClockSpeedMode int) or None.

    Uses the public `game_clock_service().clock_speed` property (0=paused,
    1=normal, 2, 3), the same surface `sample_game_clock()` relies on.
    """
    try:
        import services
        from clock import ClockSpeedMode

        game_clock = services.game_clock_service()
        if game_clock is None:
            return None
        speed = getattr(game_clock, "clock_speed", ClockSpeedMode.NORMAL)
        return int(getattr(speed, "value", 0))
    except Exception:
        return None


def set_clock_speed(speed):
    """Best-effort set of the game clock speed.

    `speed` is a ClockSpeedMode int (0=paused, 1=normal, 2, 3). Returns the
    applied speed int on success, else None. Uses the public API
    `game_clock.set_clock_speed(ClockSpeedMode.X)`.
    """
    try:
        import services
        from clock import ClockSpeedMode

        game_clock = services.game_clock_service()
        if game_clock is None:
            return None
        mode = ClockSpeedMode(int(speed))
        setter = getattr(game_clock, "set_clock_speed", None)
        if setter is None:
            return None
        setter(mode)
        applied = getattr(game_clock, "clock_speed", None)
        return int(getattr(applied, "value", int(speed)))
    except Exception:
        return None


def pause_game():
    """Force the game clock to paused. Returns True on success."""
    return set_clock_speed(0) is not None


def unpause_game():
    """Unpause the game clock to normal speed. Returns True on success."""
    return set_clock_speed(1) is not None


def travel_to_zone(zone_id):
    """Best-effort travel trigger: move the active Sim to `zone_id`.

    Validates the zone exists before triggering the op to avoid freezing the
    game on a bogus zone id.  Public API (Sims 4 Community Library
    `CommonTravelUtils`): `sim_info.send_travel_switch_to_zone_op(
    zone_id=zone_id)`.  Returns True when a travel op was requested, False
    when the game API is unavailable or the zone cannot be found.
    """
    try:
        import services

        if not _zone_exists(zone_id):
            return False

        client = services.client_manager().get_first_client()
        if client is None:
            return False
        sim = getattr(client, "active_sim", None)
        if sim is None:
            return False
        sim_info = getattr(sim, "sim_info", sim)
        op = getattr(sim_info, "send_travel_switch_to_zone_op", None)
        if op is None:
            return False
        op(zone_id=zone_id)
        return True
    except Exception:
        return False


def _zone_exists(zone_id):
    """True when `zone_id` resolves to real zone data.

    Tolerant of API drift: tries a couple of lookups and only blocks when it
    can positively conclude the zone is missing.
    """
    try:
        import services

        zone_manager = services.get_zone_manager()
        if zone_manager is not None:
            lookup = getattr(zone_manager, "get", None)
            if lookup is not None:
                try:
                    zone = lookup(zone_id)
                except Exception:
                    zone = None
                if zone is None:
                    return False
                return True
    except Exception:
        pass
    try:
        import services

        get_zone = getattr(services, "get_zone", None)
        if get_zone is not None:
            try:
                zone = get_zone(zone_id)
            except Exception:
                zone = None
            if zone is None:
                return False
            return True
    except Exception:
        pass
    return True


def _vec3(value):
    """Return (x, y, z) as floats, or None if unavailable."""
    if value is None:
        return None
    try:
        return (float(value.x), float(value.y), float(value.z))
    except Exception:
        return None


def _quat(value):
    """Return (w, x, y, z) as floats, or None if unavailable."""
    if value is None:
        return None
    try:
        return (float(value.w), float(value.x), float(value.y), float(value.z))
    except Exception:
        return None


def _sim_key(sim_info):
    """Return a stable string key for a sim, or None."""
    try:
        return "sim:%d" % int(sim_info.id)
    except Exception:
        return None


def _sim_world_entry(sim_info, sim):
    """Build one world-object entry dict for a sim, or None."""
    key = _sim_key(sim_info)
    if key is None:
        return None
    location = getattr(sim, "location", None)
    if location is None:
        return None
    transform = getattr(location, "transform", None)
    if transform is None:
        return None
    pos = _vec3(getattr(transform, "translation", None))
    if pos is None:
        return None
    fields = {"x": pos[0], "y": pos[1], "z": pos[2]}
    ori = _quat(getattr(transform, "orientation", None))
    if ori is not None:
        fields["qw"] = ori[0]
        fields["qx"] = ori[1]
        fields["qy"] = ori[2]
        fields["qz"] = ori[3]
    try:
        definition = getattr(sim, "definition", None)
        def_id = getattr(definition, "id", None)
        if def_id is not None:
            fields["def"] = int(def_id)
    except Exception:
        pass
    return {"key": key, "fields": fields}


def _sim_id_from_key(key):
    """Parse `sim:<id>` -> int id, or None for non-sim keys."""
    if not isinstance(key, str):
        return None
    if not key.startswith("sim:"):
        return None
    try:
        return int(key[4:])
    except Exception:
        return None


def _position_from_fields(fields):
    """Return (x, y, z) floats from mirrored fields, or None."""
    if not all(name in fields for name in ("x", "y", "z")):
        return None
    try:
        return (float(fields["x"]), float(fields["y"]), float(fields["z"]))
    except Exception:
        return None


def _orientation_from_fields(fields):
    """Return (w, x, y, z) floats from mirrored fields, or None."""
    if not all(name in fields for name in ("qw", "qx", "qy", "qz")):
        return None
    try:
        return (
            float(fields["qw"]),
            float(fields["qx"]),
            float(fields["qy"]),
            float(fields["qz"]),
        )
    except Exception:
        return None


def apply_world_updates(entries):
    """Move local Sims to match remote-owned world entries.

    Each entry is `{"key": "sim:<id>", "fields": {...}}` mirroring a sim owned
    by another player in the room. The local sim with the same persistent id
    (shared save) is teleported to the mirrored position/orientation. Non-sim
    keys, unknown sims, sims not instanced in the current zone, and fields
    without a position are ignored. Returns the number of sims moved (0
    offline / when nothing applies).
    """
    if not entries:
        return 0
    try:
        import services
        from routing import SurfaceIdentifier, SurfaceType
        from sims4.math import Location, Transform, Quaternion, Vector3

        manager = services.sim_info_manager()
        if manager is None:
            return 0
        zone_id = services.current_zone_id()
        if zone_id is None:
            return 0
        surface = SurfaceIdentifier(zone_id, 0, SurfaceType.SURFACETYPE_WORLD)
        applied = 0
        for entry in entries:
            key = entry.get("key")
            if key is None:
                continue
            if key.startswith("obj:"):
                applied += _apply_object_entry(key, entry.get("fields") or {})
                continue
            sim_id = _sim_id_from_key(key)
            if sim_id is None:
                continue
            fields = entry.get("fields") or {}
            pos = _position_from_fields(fields)
            if pos is None:
                continue
            try:
                sim_info = manager.get(sim_id)
            except Exception:
                sim_info = None
            if sim_info is None:
                continue
            try:
                sim = sim_info.get_sim_instance()
            except Exception:
                sim = None
            if sim is None:
                continue
            try:
                current = sim.location.transform.translation
                if (
                    abs(current.x - pos[0]) < 0.05
                    and abs(current.y - pos[1]) < 0.05
                    and abs(current.z - pos[2]) < 0.05
                ):
                    continue
            except Exception:
                pass
            ori = _orientation_from_fields(fields)
            quaternion = Quaternion(*ori) if ori is not None else Quaternion(1, 0, 0, 0)
            transform = Transform(Vector3(*pos), quaternion)
            sim.location = Location(transform, surface)
            applied += 1
        return applied
    except Exception:
        return 0


def apply_interactions(entries):
    """Push remote-owned interactions onto local mirrors of the same sim.

    Each entry is ``{"key": "sim:<id>", "interaction": "<ClassName>",
    "affordance": "<Name>", "affordance_id": <guid64>, "target": "sim:<id>"
    or "obj:<def>@<grid>"}``
    mirroring what another player's sim is doing. When the same sim exists
    locally (shared save, same persistent id), this resolves the super
    affordance by its tuning id and asks the local sim to run it, so the
    mirrored sim visibly performs the interaction instead of only showing a
    label.

    Resolution is deliberately best-effort: unknown sims, un-instanced sims,
    unresolvable affordances, non-sim keys and no-affordance entries are all
    skipped silently, and the push degrades to a no-op if several common
    interaction-entry points are unavailable on the current patch. Returns
    the number of interactions started (0 offline).
    """
    if not entries:
        return 0
    try:
        import services
        import sims4.resources

        interaction_manager = services.get_instance_manager(sims4.resources.Types.INTERACTION)
        if interaction_manager is None:
            return 0
        manager = services.sim_info_manager()
        if manager is None:
            return 0
        started = 0
        for entry in entries:
            sim_id = _sim_id_from_key(entry.get("key"))
            if sim_id is None:
                continue
            label = entry.get("interaction") or entry.get("affordance")
            affordance_id = entry.get("affordance_id")
            affordance = _resolve_affordance(interaction_manager, entry)
            if affordance is None:
                _applier_log("[MP][MIRROR] skip affordance for sim:%s (%s)" % (sim_id, label))
                continue
            try:
                sim_info = manager.get(sim_id)
            except Exception:
                sim_info = None
            if sim_info is None:
                _applier_log("[MP][MIRROR] no local sim:%s (%s)" % (sim_id, label))
                continue
            try:
                sim = sim_info.get_sim_instance()
            except Exception:
                sim = None
            if sim is None:
                _applier_log("[MP][MIRROR] sim:%s not instanced (%s)" % (sim_id, label))
                continue
            if _sim_already_running(sim, affordance_id):
                continue
            target = _interaction_target(entry.get("target"))
            if _push_interaction(sim, affordance, target):
                started += 1
                _applier_log(
                    "[MP][MIRROR] pushed %s on sim:%s"
                    % (getattr(affordance, "__name__", label) or label, sim_id)
                )
            else:
                _applier_log("[MP][MIRROR] push failed for sim:%s (%s)" % (sim_id, label))
        if started:
            _applier_log("[MP][MIRROR] applied %d remote interaction(s)" % started)
        return started
    except Exception:
        return 0


def _resolve_affordance(interaction_manager, entry):
    """The tuned super-interaction for an entry, or None.

    Prefers the stable tuning id (`affordance_id`); falls back to a
    name lookup by `affordance` then `interaction`. Never raises.
    """
    affordance = None
    affordance_id = entry.get("affordance_id")
    if isinstance(affordance_id, int) and affordance_id > 0:
        try:
            affordance = interaction_manager.get(affordance_id)
        except Exception:
            affordance = None
        if affordance is not None:
            return affordance
    for name_field in ("affordance", "interaction"):
        name = entry.get(name_field)
        if not isinstance(name, str) or not name:
            continue
        try:
            affordance = interaction_manager.get(name)
        except Exception:
            affordance = None
        if affordance is not None:
            return affordance
    return None


def _sim_already_running(sim, affordance_id):
    """True when the sim is already doing this affordance (avoid re-push/loops)."""
    if not isinstance(affordance_id, int) or affordance_id <= 0:
        return False
    try:
        top = sim.get_currently_playing_interaction()
    except Exception:
        top = None
    if top is None:
        return False
    try:
        return top.affordance_id == affordance_id
    except Exception:
        try:
            return top.get_affordance().id == affordance_id
        except Exception:
            return False


def _interaction_target_sim(target_key):
    """Resolve a mirrored `sim:<id>` target to its local instanced Sim."""
    sim_id = _sim_id_from_key(target_key)
    if sim_id is None:
        return None
    try:
        import services

        manager = services.sim_info_manager()
        if manager is None:
            return None
        sim_info = manager.get(sim_id)
        if sim_info is None:
            return None
        return sim_info.get_sim_instance()
    except Exception:
        return None


def _interaction_target(target_key):
    """Resolve a mirrored target key to a local sim or lot object, else None."""
    if not isinstance(target_key, str) or not target_key:
        return None
    if target_key.startswith("obj:"):
        parsed = _parse_object_key(target_key)
        if parsed is None:
            return None
        return _find_object_for_key(parsed)
    return _interaction_target_sim(target_key)


def _push_interaction(sim, affordance, target):
    """Ask `sim` to run `affordance` on `target` (None = self/no aim).

    Tries the common public queue entry points in order and swallows every
    failure so mirrored execution is always optional.
    """
    try:
        sim.queue.push_interaction(affordance, target=target)
        return True
    except Exception:
        pass
    try:
        sim.push_super_affordance(affordance, target=target)
        return True
    except Exception:
        pass
    return False


def diagnose_hooks():
    """Report why the samplers produce no entries, drilling from `services`
    down to instanced household sims. Returns list of strings; used by
    `mp.diag` to debug live sessions without guesses."""
    lines = []
    try:
        import services
    except Exception as exc:
        lines.append("services import failed: %r" % (exc,))
        return lines
    try:
        sim_info = services.active_sim_info()
    except Exception as exc:
        lines.append("active_sim_info raised: %r" % (exc,))
        return lines
    lines.append("active_sim_info id=%s" % (
        None if sim_info is None else getattr(sim_info, "id", "?")
    ))
    if sim_info is not None:
        try:
            household = getattr(sim_info, "household", None)
            if household is not None:
                ids = [
                    getattr(si, "id", "?")
                    for si in (list(getattr(household, "sim_infos", ()) or ()))
                ]
                lines.append("household sim_infos ids=%r" % (ids,))
            else:
                lines.append("household=None")
        except Exception as exc:
            lines.append("household iteration raised: %r" % (exc,))
    try:
        manager = services.sim_info_manager()
        lines.append("sim_info_manager count=%s" % (None if manager is None else len(manager)))
    except Exception as exc:
        lines.append("sim_info_manager raised: %r" % (exc,))
    pairs = _instanced_sim_infos()
    lines.append("instanced_pairs=%d" % len(pairs))
    for si, sim in pairs:
        lines.append("  key=%s instanced=%s" % (_sim_key(si), sim is not None))
    try:
        lines.append("world_sample=%d" % len(sample_world_objects()))
    except Exception as exc:
        lines.append("world sampler raised: %r" % (exc,))
    try:
        lines.append("interaction_sample=%d" % len(sample_interactions()))
    except Exception as exc:
        lines.append("interaction sampler raised: %r" % (exc,))
    return lines


def _instanced_sim_infos():
    """The player's household SimInfos with a live sim instance in this zone.

    Uses the active sim's household (the playable household). Falls back to
    the active sim alone when no household exists. Returns a list of
    ``(sim_info, sim)`` pairs; empty offline / before a household loads.
    """
    try:
        import services

        sim_info = services.active_sim_info()
        if sim_info is None:
            return []
        household = getattr(sim_info, "household", None)
        if household is not None:
            sim_infos = list(getattr(household, "sim_infos", ()) or ())
        else:
            sim_infos = [sim_info]
        pairs = []
        for si in sim_infos:
            try:
                sim = si.get_sim_instance()
            except Exception:
                sim = None
            if sim is None:
                continue
            pairs.append((si, sim))
        return pairs
    except Exception:
        return []


def sample_world_objects():
    """Sample the household sims' positions for world replication.

    Returns one entry per instanced sim with a stable ``sim:<id>`` key and
    position/orientation fields, or an empty list when no zone or sim is
    available. Safe to call outside the game (returns ``[]``).
    """
    entries = []
    for sim_info, sim in _instanced_sim_infos():
        entry = _sim_world_entry(sim_info, sim)
        if entry is not None:
            entries.append(entry)
    return entries


def household_sim_keys():
    """Sorted ``sim:<id>`` keys for the instanced household, or empty offline.

    Shared-save co-op: both clients sample the same household, so this is the
    roster the per-player sim ownership split is computed from.
    """
    keys = []
    for sim_info, _sim in _instanced_sim_infos():
        key = _sim_key(sim_info)
        if key is not None:
            keys.append(key)
    return sorted(keys)


def sample_interactions():
    """Sample household sims' running interactions for replication.

    Returns one entry per unique interaction per sim:

        {"key": "sim:<id>", "interaction": "<ClassName>",
         "affordance": "<Name>", "affordance_id": <guid64>,
         "target": "sim:<id>"}

    ``interaction`` is the running class name (display); ``affordance`` and
    ``affordance_id`` are the super affordance the player actually clicked,
    the identity the receiving client needs to push the same interaction onto
    its mirrored sim. ``target`` is the aim key when the interaction targets
    another sim (``sim:<id>``) or a lot object (``obj:<def>@<grid>``);
    self-targets are omitted. All extra fields are best-effort: entries
    degrade to label-only when the extraction fails. Safe to call outside
    the game.
    """
    entries = []
    for sim_info, sim in _instanced_sim_infos():
        key = _sim_key(sim_info)
        if key is None:
            continue
        running = []
        try:
            top = sim.get_currently_playing_interaction()
            if top is not None:
                running.append(top)
        except Exception:
            pass
        queue = getattr(sim, "queue", None)
        if queue is not None:
            try:
                for interaction in queue:
                    if len(running) >= 3:
                        break
                    if any(interaction is item for item in running):
                        continue
                    running.append(interaction)
            except Exception:
                pass
        seen = set()
        for interaction in running:
            label = _interaction_label(interaction)
            if label is None or label in seen:
                continue
            seen.add(label)
            entry = {"key": key, "interaction": label}
            affordance_id = _interaction_affordance_id(interaction)
            if affordance_id is not None:
                entry["affordance_id"] = affordance_id
            affordance_name = _interaction_affordance_name(interaction)
            if affordance_name is not None:
                entry["affordance"] = affordance_name
            target_key = _interaction_target_key(interaction, key)
            if target_key is not None:
                entry["target"] = target_key
            entries.append(entry)
    return entries


def sample_household_funds():
    """Best-effort household simoleon balance (int) or None offline/unknown."""
    try:
        import services

        household = services.active_household()
        if household is None:
            return None
        funds = getattr(household, "funds", None)
        if funds is None:
            return None
        amount = getattr(funds, "amount", None)
        if amount is None:
            return None
        return int(amount)
    except Exception:
        return None


def set_household_funds(balance):
    """Set the household balance to an absolute amount (best-effort).

    Uses `HouseholdFunds.add_money/remove_money` deltas, which are safe to
    call outside a UI flow and converge the local number to `balance`.
    Returns the applied balance on success, else None.
    """
    try:
        import services

        household = services.active_household()
        if household is None:
            return None
        funds = getattr(household, "funds", None)
        if funds is None:
            return None
        current = getattr(funds, "amount", None)
        if current is None:
            return None
        target = int(balance)
        delta = target - int(current)
        if delta > 0:
            add = getattr(funds, "add_money", None)
            if add is None:
                return None
            add(delta)
        elif delta < 0:
            remove = getattr(funds, "remove_money", None)
            if remove is None:
                return None
            remove(-delta)
        return target
    except Exception:
        return None


def _object_manager_iterate():
    """Best-effort iteration over instanced lot/zone objects (not sims).

    Tries the common `services.object_manager()` surfaces and degrades to an
    empty list without raising, so the sampler never breaks on API drift.
    """
    try:
        import services

        manager = services.object_manager()
        if manager is None:
            return []
        get_all = getattr(manager, "get_all", None)
        if callable(get_all):
            try:
                return list(get_all())
            except Exception:
                pass
        valid = getattr(manager, "valid_objects", None)
        if callable(valid):
            try:
                return list(valid())
            except Exception:
                pass
        objects = getattr(manager, "objects", None)
        if objects is not None:
            try:
                return list(objects)
            except Exception:
                pass
        stacks = getattr(manager, "stacks", None)
        if stacks is not None:
            try:
                return list(stacks)
            except Exception:
                pass
        return []
    except Exception:
        return []


def _definition_id(obj):
    try:
        definition = getattr(obj, "definition", None)
        if definition is None:
            return None
        return int(getattr(definition, "id", 0) or 0)
    except Exception:
        return None


def _object_key(obj, transform):
    """Stable cross-machine key for a lot object.

    Objects have no persistent id (runtime ids differ per load/save), so the
    key is derived from the definition (stable) + a coarse position grid,
    which matches objects placed at the same spot in the shared save.
    """
    def_id = _definition_id(obj)
    if def_id is None or transform is None:
        return None
    pos = _vec3(getattr(transform, "translation", None))
    if pos is None:
        return None
    grid = "_".join(str(int(round(v * 100.0))) for v in pos)
    return "obj:%d@%s" % (def_id, grid)


def sample_lot_objects():
    """Sample every instanced lot object (furniture, appliances, decor...).

    Returns entries with a ``obj:<def>@<grid>`` key plus position/orientation
    fields (and ``def``), mirroring the sim-entry shape so the shared write-back
    path can move a peer's copy of the same object. Safe to call offline.
    """
    entries = []
    for obj in _object_manager_iterate():
        if getattr(obj, "is_sim", False):
            continue
        location = getattr(obj, "location", None)
        if location is None:
            continue
        transform = getattr(location, "transform", None)
        if transform is None:
            continue
        key = _object_key(obj, transform)
        if key is None:
            continue
        pos = _vec3(getattr(transform, "translation", None))
        if pos is None:
            continue
        fields = {"x": pos[0], "y": pos[1], "z": pos[2]}
        ori = _quat(getattr(transform, "orientation", None))
        if ori is not None:
            fields["qw"] = ori[0]
            fields["qx"] = ori[1]
            fields["qy"] = ori[2]
            fields["qz"] = ori[3]
        def_id = _definition_id(obj)
        if def_id is not None:
            fields["def"] = def_id
        entries.append({"key": key, "fields": fields})
    return entries


def sample_playable_world():
    """Household sims + instanced lot objects (the full playable world)."""
    return sample_world_objects() + sample_lot_objects()


def _parse_object_key(key):
    """`obj:<def>@<x>_<y>_<z>` -> (def_id, approx position) or None."""
    if not isinstance(key, str) or not key.startswith("obj:"):
        return None
    try:
        rest = key[len("obj:"):]
        def_id, coords = rest.split("@", 1)
        cx, cy, cz = (int(v) for v in coords.split("_"))
        return int(def_id), (cx / 100.0, cy / 100.0, cz / 100.0)
    except Exception:
        return None


def _find_object_for_key(parsed):
    """Match a mirrored object key to a local object.

    Objects share per-definition keys, and grid snapping gives fuzzylom.
    Nearest-position match within a unit is used so a slight move does not
    look like delete+place.
    """
    if parsed is None:
        return None
    def_id, approx = parsed
    best, best_dist = None, 1.0
    for obj in _object_manager_iterate():
        if getattr(obj, "is_sim", False):
            continue
        if _definition_id(obj) != def_id:
            continue
        location = getattr(obj, "location", None)
        if location is None:
            continue
        pos = _vec3(getattr(location, "transform", None))
        if pos is None:
            continue
        if getattr(getattr(location, "transform", None), "orientation", None) is None:
            pass
        distance = (pos[0] - approx[0]) ** 2 + (pos[1] - approx[1]) ** 2 + (pos[2] - approx[2]) ** 2
        if distance < best_dist:
            best, best_dist = obj, distance
    return best


def _apply_object_entry(key, fields):
    """Best-effort move/ease of a local lot object to a mirrored position."""
    parsed = _parse_object_key(key)
    if parsed is None:
        return 0
    obj = _find_object_for_key(parsed)
    if obj is None:
        return 0
    pos = _position_from_fields(fields)
    if pos is None:
        return 0
    ori = _orientation_from_fields(fields)
    try:
        import services
        from sims4.math import Location, Transform, Quaternion, Vector3

        zone_id = services.current_zone_id()
        if zone_id is None:
            return 0
        from routing import SurfaceIdentifier, SurfaceType

        surface = SurfaceIdentifier(zone_id, 0, SurfaceType.SURFACETYPE_WORLD)
        quaternion = Quaternion(*ori) if ori is not None else Quaternion(1, 0, 0, 0)
        obj.location = Location(Transform(Vector3(*pos), quaternion), surface)
        return 1
    except Exception:
        try:
            from sims4.math import Vector3
            update_translation = getattr(obj, "update_translation", None)
            if update_translation is not None:
                update_translation(Vector3(*pos))
                return 1
        except Exception:
            pass
    return 0


def apply_object_gone(keys):
    """Best-effort destroy of locally-mirrored lot objects that a peer deleted.

    `keys` are ``obj:<def>@<grid>`` keys. Only the nearest same-definition
    local object is destroyed, and destroy is skipped if it is unavailable.
    Never touches sims (sim travel is handled by the zone/travel flow).
    """
    destroyed = 0
    for key in keys or []:
        parsed = _parse_object_key(key)
        if parsed is None:
            continue
        obj = _find_object_for_key(parsed)
        if obj is None:
            continue
        destroy = getattr(obj, "destroy", None)
        if not callable(destroy):
            continue
        try:
            destroy()
            destroyed += 1
        except Exception:
            pass
    return destroyed


def _interaction_label(interaction):
    if interaction is None:
        return None
    try:
        label = interaction.__class__.__name__
    except Exception:
        label = None
    if not label:
        return None
    return label


def _interaction_affordance_id(interaction):
    """The tuning guid64 of the super affordance the player clicked, or None.

    Best-effort: pulls from common interaction attributes and degrades to
    None without raising, so the sampler never breaks on API drift.
    """
    candidates = []
    try:
        affordance = interaction.get_affordance()
        candidates.append(getattr(affordance, "id", None))
    except Exception:
        pass
    try:
        candidates.append(getattr(interaction, "affordance_id", None))
    except Exception:
        pass
    try:
        affordance = interaction.get_affordance()
        candidates.append(getattr(affordance, "guid64", None))
    except Exception:
        pass
    for value in candidates:
        if isinstance(value, int) and value > 0:
            return value
    return None


def _interaction_affordance_name(interaction):
    """Display name of the base affordance (`__class__.__name__`), or None."""
    affordance = None
    try:
        affordance = interaction.get_affordance()
    except Exception:
        pass
    if affordance is None:
        affordance = interaction
    try:
        name = affordance.__class__.__name__
    except Exception:
        name = None
    return name or None


def _interaction_target_key(interaction, actor_key):
    """Aim key when the interaction targets another sim or a lot object.

    Sim targets are ``sim:<id>``; lot-object targets (bed, chair, ...) are
    ``obj:<def>@<grid>`` so the receiving client can resolve the same
    definition at the same spot in the shared save. Self-targets return None.
    """
    try:
        target = interaction.target
    except Exception:
        target = None
    if target is None:
        return None
    try:
        target_id = target.sim_info.id
    except Exception:
        target_id = None
    if target_id is not None:
        target_key = "sim:%s" % target_id
        if target_key == actor_key:
            return None
        return target_key
    try:
        location = getattr(target, "location", None)
        transform = getattr(location, "transform", None) if location is not None else None
        if transform is None:
            return None
        return _object_key(target, transform)
    except Exception:
        return None


def set_sim_autonomy(sim_info, enabled):
    """Best-effort per-sim autonomy toggle.

    Tries multiple known game APIs in order, swallowing errors so the mod
    never breaks the game.  Returns True when any API call appeared to
    succeed (best-effort: some APIs don't raise but also don't confirm).

    Known candidates (from game decompilation / community docs):
      - sim_info.set_autonomy_enabled(enabled)
      - sim.get_autonomy_component().set_autonomy_enabled(enabled)
      - autonomy_service disable/enable per sim
    """
    try:
        sim = sim_info.get_sim_instance()
    except Exception:
        sim = None
    # Candidate 1: sim_info.set_autonomy_enabled (most common)
    try:
        setter = getattr(sim_info, "set_autonomy_enabled", None)
        if setter is not None:
            setter(enabled)
            return True
    except Exception:
        pass
    # Candidate 2: autonomy component on sim instance
    if sim is not None:
        try:
            comp = getattr(sim, "get_autonomy_component", None)
            if comp is not None:
                ac = comp()
                if ac is not None:
                    setter2 = getattr(ac, "set_autonomy_enabled", None)
                    if setter2 is not None:
                        setter2(enabled)
                        return True
        except Exception:
            pass
    # Candidate 3: sim_info.autonomy_enabled setter (attribute-based)
    try:
        attr = getattr(sim_info, "autonomy_enabled", None)
        if attr is not None:
            setattr(sim_info, "autonomy_enabled", enabled)
            return True
    except Exception:
        pass
    return False


def reconcile_autonomy(remote_owner_keys, my_player_id, my_zone_id):
    """Reconcile per-sim autonomy based on world ownership.

    Walks the active household's instanced sims; for each sim whose
    ``sim:<id>`` key is owned by another player in the world mirror,
    autonomy is suppressed; for self-owned or unowned sims, autonomy is
    restored.

    Returns (suppressed, restored, skipped) counts for diagnostics.
    ``remote_owner_keys`` is a set of ``sim:<id>`` strings that are
    currently owned by another player.
    """
    suppressed = 0
    restored = 0
    skipped = 0
    for sim_info, sim in _instanced_sim_infos():
        key = _sim_key(sim_info)
        if key is None:
            skipped += 1
            continue
        should_suppress = key in remote_owner_keys
        try:
            if set_sim_autonomy(sim_info, not should_suppress):
                if should_suppress:
                    suppressed += 1
                else:
                    restored += 1
            else:
                skipped += 1
        except Exception:
            skipped += 1
    return suppressed, restored, skipped