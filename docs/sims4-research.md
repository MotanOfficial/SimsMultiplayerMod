# Sims 4 modding reference: confirmed public facts

Record of Sims 4 modding facts the project actually relies on, with the
source class of each fact. This project intentionally avoids copying any
code or assets from S4MP or SimSync: this file notes only public, official,
or widely documented game modding behavior.

> Legal boundary: everything below is standard Python script-modding for
> The Sims 4 (public API calls + documented mod packaging rules). The
> project does not depend on, bundle, or copy S4MP/SimSync anything.

## Game runtime facts

- The game executes script mods with a bundled CPython **3.7**, so all mod
  code must run on 3.7 (no static typing in game-executed files, none of the
  3.8+ syntax).
- **LIVE GAME CHECK (M6, confirmed by an actual in-game run): the game's
  embedded Python ships NO `asyncio`.** `import asyncio` raises
  `ModuleNotFoundError` and the whole mod fails to load. The client engine
  therefore uses a background `threading.Thread` + a blocking `socket` with
  `select`-driven reads, stdlib only. Verified present in the game's Python:
  `socket`, `select`, `threading`, `struct`, `json`, `collections`, `time`,
  `os`, `random`, `uuid` (confirmed by reaching them in the import chain).
  Not confirmed / avoided: `logging` (the game ships `sims4.log`, so the
  engine guards `import logging` with a no-op fallback logger) and anything
  else from the standard library.
- Cheat commands are registered with the public decorator:

  ```python
  import sims4.commands

  @sims4.commands.Command("mp.connect", command_type=sims4.commands.CommandType.Cheat)
  def _cmd(host="127.0.0.1", port="8765", name="", _connection=None):
      ...
  ```

  Command args arrive as strings; `_connection` is injected by the engine.
  Use `sims4.commands.output(text)` to print to the console.

- Repeating real-time ticks (heartbeat scheduling) use `alarms`:

  ```python
  import alarms
  import clock

  alarms.add_alarm_real_time(
      owner,
      clock.interval_in_real_seconds(30),
      callback,
      repeating=True,
      use_sleep_time=True,
      cross_zone=False,
  )
  ```

  It is possible the `use_sleep_time`/`cross_zone` keywords are rejected by
  older game patches (TypeError). The alarm helper in the mod therefore calls
  with a keyword-less fallback tuple when the full signature raises.

- **Confirmed in-game (current patch line): `add_alarm_real_time(...,
  repeating=True)` never schedules** — the call raises and the returned
  handle is `None`, silently killing every repeating-alarm-driven loop (no
  claims, proposals, presence, or reconnect ticks). One-off real-time alarms
  (`add_one_off_real_time`) schedule and fire fine. The client therefore runs
  its 0.5s tick as a **chained one-off** (`_start_alarm` →
  `_on_alarm_chained` → re-arm in `ensure_alarm`), with `mp.diag` reporting
  `alarm=armed last_tick=...` and every `mp.*` command re-arming a
  missing/stale schedule. Do not switch back to repeating alarms without
  re-verifying in-game.

- **Real-time alarm span double-wrap bug (fixed)**: `clock.interval_in_real_seconds`
  already returns a `TimeSpan`; passing that result into `TimeSpan(span)` raises
  `RuntimeError('no real-time interval builder available')` because the constructor
  rejects `TimeSpan` objects. Confirming: `sims4.clock` does not exist in this
  patch (`ModuleNotFoundError`); only top-level `clock` exists. The mod's
  `_real_time_span` helper therefore skips wrapping when the builder result is
  already a `TimeSpan` (`isinstance(span, TimeSpan)`), keeping the chained one-off
  alarm alive on the current patch line.

  Alarm callbacks run on the game thread; socket work must *not* happen in
  them (see architecture: the engine owns a separate thread).

- Travel to a destination zone is triggered on a Sim's `SimInfo` with:

  ```python
  sim_info.send_travel_switch_to_zone_op(zone_id=zone_id)
  ```

  (confirmed from the `CommonTravelUtils` API surface in SimulationClock /
  travel utilities; the mod calls it defensively via `getattr` and only on an
  active Sim).

- The current zone id and whether the zone has finished loading are read from
  the global `services`:

  ```python
  import services, zone

  zone_id = services.current_zone_id()      # int or None before a zone exists
  running = services.current_zone().is_zone_running
  ```

- The game clock is sampled through `services.game_clock_service()`:

  ```python
  import services
  from clock import ClockSpeedMode

  game_clock = services.game_clock_service()      # None if not started
  now = game_clock.now()                          # game-time Date/Time
  ticks = game_clock.clock_speed                  # ClockSpeedMode enum
  speed = int(game_clock.clock_speed)             # 1 / 2 / 3
  absolute_ticks = now.absolute_ticks()           # monotonic game-time ticks
  ```

  `ClockSpeedMode` also offers `get_clock_speed_value()`; `game_clock.clock_speed`
  currently maps to a member whose int value is the speed multiplier. These
  calls are all `getattr`-guarded in the game hook so the mod still imports
  and runs offline where `services`/`clock` are absent.

## Mod packaging facts

- The game only loads script mods as `*.ts4script` or `*.zip` in the Mods
  folder, and loose Python inside a `Scripts/` subfolder **only in
  development** (when running the game from a dev build / with the relevant
  script load flag).
- In `*.ts4script` (a zip), the game's script loader imports every `.py`
  module. A `.py` with a sibling `.pyo` file is loaded from the `.pyo`; a
  `.py` with a sibling `.pyc` is compiled/imported with a quirk (the pyc gets
  deleted in memory and the source is compiled fresh) - so real `.pyc` bytes
  are fragile, and a `.pyo` with real bytecode from the wrong Python version
  can crash. Packed zips therefore ship **source `.py` + empty `.pyo`**
  siblings: the loader takes the empty pyo, the module import still works,
  and there is no version skew.
- Shipping only `.py` (no `.pyo`/`.pyc`) in a zipped mod can be ignored by
  the loader. Hence `.pyo` companions are required in the package.
- The build script's `dev` target copies loose `.py` into
  `Mods/Sims4Multiplayer/Scripts/...` for iteration, which the loader picks
  up recursively in development.

## Sims 4 networking / multiplayer

- The Sims 4 has no official multiplayer and no documented public
  multiplayer protocol for third parties. The game client is a fully local
  simulation with a headless-ish server baked into the shipped game; there is
  no supported "dedicated server" API for self-hosting multiplayer.
- Community projects (e.g. S4MP) existed as reverse-engineered overlays.
  Per project policy we do not reuse their code or assets; this project builds
  an independent Python transport of our own design.

## Relevance to this project

- The in-game mod is Python 3.7-compatible and avoids `asyncio` (not present
  in the game's interpreter); the standalone server may use any modern Python.
- All network I/O is on a dedicated background thread (`threading.Thread` +
  socket + `select`); game thread work (alarms, commands) only drains queued
  results.
- Packaging follows the empty-`.pyo` rule verified in the build output.

## Open question: object identity (M4 world sampler)

- The M4 protocol keys world objects by a stable string `key` per room. The
  in-game sampler is intentionally stubbed (`sample_world_objects()` returns
  `[]`) until the identity question is answered in-game: whether a stable
  per-object string (persistent id vs. transient object id vs. a mod-assigned
  label tied to a zone lot) exists for the objects we want to replicate.
- The claim/update/release protocol itself is complete and covered by tests;
  the missing piece is only the game-side hook that returns `[{"key",
  "fields"}]` from the live simulation.

## M5 re-check + open questions (interaction sync)

Per the milestone rule, M5 was checked against the notes above before any
code was written:

- The M5 design depends **only** on protocol features already built in M4/M5
  (validated JSON messages, room-scoped broadcasts, reaper sweeps) plus a
  pluggable client sampler - no new game API is required to ship the sync
  layer. **No part of the design reuses S4MP/SimSync code.**
- No new confirmed game facts were added this milestone (the travel/clock/zone
  facts above are unchanged and remain the only ones in use).
- New open questions, folded into the M4 identity one above:

1. **Interaction identity**: when a Sim in the game *actually* starts using an
   object, what identifies that start/end and its object so the sampler can
   report `[{"key", "interaction"}]`? Candidates to verify in-game: the active
   interaction queue on the Sim (`sim_info.get_sim_instance(...).get_currently_playing_interaction()`),
   interaction `InteractionContext`, and the same object-identity problem as
   M4. The `interaction` type string is currently an open vocabulary (the
   smoke mode passes a bare `Read`/`Sit`); a canonical set needs in-game
   verification.
2. Until verified, `sample_interactions()` returns `[]`; `mp.inter` /
   `mp.inter_end` exercise the full proposal/end/conflict path manually against
   the live server.

## M6 re-check + added facts (in-game UI)

Per the milestone rule, M6 was checked against the notes above before any code
was written. The M5 facts remain the only game APIs in use, plus **three** new
public UI APIs needed for the travel-invite dialog and notifications:

- The global `services` exposes the UI dialog service:

  ```python
  import services

  service = services.get_ui_dialog_service(0)
  ```

  It is a singleton (owner id `0`) and may be `None` when no UI is active
  (e.g. the main menu), which is exactly the condition the mod uses to fall
  back to the console. Returns `None` cleanly outside the game too.

- Dialogs are created on the service with the public dialog classes and shown
  immediately:

  ```python
  from ui.ui_dialog import UiDialogNotification, UiDialogOkCancel, UiDialogResponse

  dialog = service.create_dialog(
      UiDialogNotification, None,
      text=..., title=...,
  )
  dialog.show_dialog()
  ```

  `UiDialogNotification` takes `text`/`title`; `UiDialogOkCancel` additionally
  takes `ok_text`/`cancel_text` and an `add_listener(callback)` whose callback
  receives `(response, ...)`; the request-response decision is
  `response == UiDialogResponse.Ok`. The mod compares responses by string
  (`str(response) == str(UiDialogResponse.Ok)`) so a future game patch that
  changes the enum identity does not break the check. Dialog callbacks run on
  the game thread, which is why the travel decision is safe to route straight
  into `respond_travel()`.

- User-facing strings are localized through the tuning helper:

  ```python
  from sims4.localization import LocalizationHelperTuning

  LocalizationHelperTuning.get_raw_text("Hello")  # -> localized UiText
  ```

- Re-check outcome: the M6 design (dialog/toast via `get_ui_dialog_service`,
  ghost reaper, reconnect reclaim, framing pressure tests) needs no new game
  simulation APIs; **no part of it reuses S4MP/SimSync code.** The remaining
  in-game verification is the visual rendering of the toast and the
  accept/decline dialog (the offline tests cover the fallback and wiring only),
  plus the unresolved M4/M5 sampler identity questions above.

## M7 added facts: object & interaction samplers (live-data hooks)

The M4/M5 open questions about object identity and interaction identity are
resolved for the **sim** case (the only replicated entity in v1); the answers
below are all public game APIs confirmed from widely documented scripting
sources (Sims 4 Community Library docs, Mod The Sims posts, and the
TS4-InspectObject tooling, all describing the shipped `sims4`/`services`
modules). None of it is S4MP/SimSync code.

- Every spawnable thing in the current zone, including Sims, is an `Object`
  registered with the zone object manager:

  ```python
  import services
  object_manager = services.object_manager()
  for obj in object_manager.get_all():
      ...
  ```

  An object is a Sim when `obj.is_sim` is truthy. `object_manager()`
  returns the live manager for the current zone and is `None`/raises only
  when no zone is loaded, so the sampler guards every access.

- **Object identity**: each `Object` has
  - `obj.definition.id` — the object/tuning id (stable, the "what kind of
    object" across sessions);
  - `obj.id` — the instance id (session-scoped allocation);
  - `obj.persistent_id` — for persistent *lot statics* only (0 otherwise),
    stable across save/load. **Not all objects have one.**
  - Sims additionally expose `sim_info.id` — the persistent SimInfo id,
    stable across single-player sessions. The world/interaction samplers use
    `sim:<sim_info.id>` as the replication key (protocol keys are strings).
  - `obj.location` is a `sims4.math.Location`; position =
    `obj.location.transform.translation` (a `Vector3`, `.x/.y/.z`, e.g.
    `0.701569, 0.000000, 0.000031`) and orientation =
    `obj.location.transform.orientation` (a `Quaternion`, `.w/.x/.y/.z`).
    These are already exposed by a `GameObject`'s public accessors
    (`obj.location`, `obj.definition`, `.translation`/`.orientation`).
- **Active sim + its interactions**:

  ```python
  sim_info = services.active_sim_info()       # None before a household loads
  sim = sim_info.get_sim_instance()           # None while not in a zone
  top = sim.get_currently_playing_interaction()  # running Interaction or None
  queue = sim.queue                            # _InteractionQueue, iterable
  ```

  `sim.queue` is iterable over queued+running `Interaction` objects; a
  running `Interaction` has a tuning-class identity used by the sampler as
  the `interaction` string (`interaction.__class__.__name__`, e.g.
  `Chat`/`SimInventoryBasicInteraction`). Guard every access: the exact
  methods/attributes vary across patch levels, so the samplers degrade to
  `[]` rather than raising.

- **Full-household sampler contract (M9, current)**: `sample_world_objects()`
  emits `[{"key": "sim:<id>", "fields": {"x","y","z","qw","qx","qy","qz","def"}}]`;
  `sample_interactions()` emits one entry per unique interaction per sim:

  ```python
  {"key": "sim:<id>", "interaction": "<ClassName>",
   "affordance": "<Name>", "affordance_id": <guid64>, "target": "sim:<id>"}
  ```

  Both return `[]` offline/in-zone-empty. Auto-claim: the world tick
  auto-claims sampled keys it does not yet own (one claim in flight per key
  until the ack), so the player's sim position streams to the room without
  `mp.claim`. The extra interaction fields are best-effort execution hints
  computed by guarded helpers (`_interaction_affordance_id/name/target_key`)
  that never raise on API drift; entries degrade to label-only when a hint
  cannot be resolved.
- **Interaction execution (M10)**: `apply_interactions(entries)` (installed
  via `set_interaction_applier`) is called on the game thread after
  `INTERACTION_START`/`INTERACTION_STATE`, with remote-owned entries only. It
  resolves the local sim by persistent id and the super affordance first by
  tuning id, then by name, skips a sim already running that affordance
  (avoiding re-push loops), and starts the interaction on the mirrored sim:

  ```python
  interaction_manager = services.get_instance_manager(sims4.resources.Types.INTERACTION)
  affordance = interaction_manager.get(entry["affordance_id"])
  sim.queue.push_interaction(affordance, target=aim_sim)   # or
  sim.push_super_affordance(affordance, target=aim_sim)    # fallback
  ```

  Every step is wrapped so failure degrades to read-only label mirroring.
  This mirrors S4MP-style "run the same affordance on the peer's copy" but
  implemented independently against the public interaction manager, sim
  queue, and the existing FCFS interaction reservation (no S4MP/SimSync
  code).
- **The super affordance vs the running class**: a running `Interaction`'s
  `__class__.__name__` is the *subclass* running right now; the stable,
  cross-client identity is the tuned **super affordance** the player clicked
  (`interaction.get_affordance()` -> `.id`/`.guid64`, also exposed as
  `interaction.affordance_id` on many classes). Both are sampled; the
  receiver prefers the guid64.
- Limitations of the current samplers/applier (accepted for v1, revisit in
  M10+): only **in-lot household sims are replicated**; interactions are keyed
  by the sim and executed as a best-effort affordance push (no progress/skill
  outcome replication, no object-targeted actions since objects are not
  replicated). Autonomy suppression (M14) addresses the "remote sim jostled by
  local autonomy between sync ticks" part: each client reconciles per-sim
  autonomy from the world mirror, disabling it for sims owned by another
  player and restoring it on release.
- **Receiving side (M8)**: remote-owned sim entries are applied back into the
  game by the receive-side applier `apply_world_updates(entries)`, which
  resolves each `sim:<id>` via `services.sim_info_manager().get(sim_id)` /
  `sim_info.get_sim_instance()` and moves the local instance with the public
  `sims4.math` + `routing` pattern seen in community teleport tooling:

  ```python
  from routing import SurfaceIdentifier, SurfaceType
  from sims4.math import Location, Transform, Quaternion, Vector3

  surface = SurfaceIdentifier(services.current_zone_id(), 0, SurfaceType.SURFACETYPE_WORLD)
  sim.location = Location(Transform(Vector3(x, y, z), Quaternion(w, x, y, z)), surface)
  ```

  The client calls the applier (installed via `set_world_applier`) on the
  game thread after every `WORLD_STATE`/`WORLD_DELTA`, passing only objects
  whose mirror owner is another player. This only works when both clients
  share the same save, so a peer's sim exists locally with the same
  persistent id; sims the local game does not have are ignored.
- **Automated control (M9)**: the samplers iterate the playable household via
  `services.active_sim_info().household.sim_infos` (each `SimInfo` instanced
  via `get_sim_instance()`). There is **no** manual control selection: every
  client pushes all instanced household sims it owns, and because claims are
  server-side FCFS with per-key deny-backoff (30s) cleared on
  `OBJECT_OWNERSHIP owner=null`, each sim ends up driven by at most one
  client at a time while everyone else's copy mirrors it. Clicking a sim and
  doing any on-screen action just works — ownership follows whoever claims
  first, no commands.