# Milestones

The project is built in milestones. Each milestone ends with a runnable,
tested vertical slice so the game and server can be exercised end to end.

## M1 - Foundations (DONE)

Target: prove the full loop over a real TCP connection.

- [x] Shared protocol package `protocol/simmp` (envelope, framing,
      validation, message builders), versioned and strict.
- [x] Standalone asyncio server: hello/welcome, heartbeat PING/PONG,
      lobby + custom room join, TEST EVENT broadcast, authoritative room
      state, disconnect handling.
- [x] Sims 4 client mod:
  - non-blocking threaded socket engine (never freezes the sim);
  - local mirror of server truth (`LocalSession`);
  - in-game cheat commands: `mp.connect`, `mp.disconnect`, `mp.join`,
    `mp.test`, `mp.status`, `mp.process`;
  - import-guarded modules so the package is testable outside the game.
- [x] Build pipeline: `python client_mod/build_script_mod.py package`
      produces `Sims4Multiplayer.ts4script` (with the empty-`.pyo` trick);
      `dev` copies loose files into a `Mods/Sims4Multiplayer/Scripts/`
      folder for iteration.
  > Verified: the packed zip contains only `.py` + sibling `.pyo` pairs,
  > no `__pycache__`/`.pyc` leaks.
- [x] Tests (stdlib `unittest`, no third-party deps): framing, validation,
      messages, server integration (in-process), client engine.
      `python tests/run_tests.py` -> 38 tests pass.
- [x] Live smoke test: `python server/main.py` + real client connection,
      WELCOME received, server logs to console.

M1 deliberately has **no game-world replication** - it delivers the
transport, session, room and event plumbing that later milestones build on.

## M2 - In-game presence & reliability (DONE)

- [x] **Config + auto-connect**: `Sims4Multiplayer.json` (host, port, name,
      `auto_connect`, `presence_interval`). Loader is pure Python and unit
      tested; discovered via explicit path, `SIM4_MP_CONFIG`, or the game's
      Mods folder. When `auto_connect` is on, the plugin schedules a
      one-shot connect shortly after startup. Manual entry point:
      `mp.autoconnect`.
- [x] **Presence snapshots**: new `PRESENCE` protocol message (zone/lot +
      timestamp). The game thread samples the current zone via a guarded
      game hook and the connectivity alarm sends it on an interval; the
      server stamps origin identity and relays within the room; the client
      mirrors a per-player presence map. Console view: `mp.who`.
- [x] **Reliable-room layer**: every `EVENT` now carries a sender `seq`.
      The server dedupes resends per player and acks each accepted event
      (`EVENT_ACK`); the client keeps un-acked events in a bounded pending
      buffer, drops them on ack, and resends them when it reconnects.
      Protocol bumped to **v2**.
- [x] **Stable player identity**: `HELLO` takes an optional `client_id`
      (<= 64 chars). The server keeps a `client_id` -> player map after a
      disconnect ("ghost" player), so a reconnect reuses the same
      `player_id`, room, and event-dedup state (resends never duplicate to
      peers across sessions). A reconnect racing the live socket takes the
      identity over by closing the stale connection. The mod generates one
      `uuid4().hex` per client automatically; CLI smoke clients pass
      `--client-id`. Without `client_id`, HELLO behaves as before (fresh
      player each session).
- [x] **Live status**: `mp.status`/`mp.who` show the roster, presence, and
      pending counts; `mp.*` notifications go through one notifier that
      currently prints to the console (a real in-game toast/popup UI needs a
      game-side UI asset and is deferred - console is the working M2 UI).
- [x] Tests: protocol v2 builders/validation, server dedup+ack+presence
      relay, engine seq/pending/ack + reconnect-resend, config loader,
      presence helpers, offline game-hook no-ops.

Protocol v2 is backward-incompatible with the M1 0.x wire format, but since
the server and mod ship together this is a clean cut.

## M3 - Travel & lot sync (DONE)

- [x] **Group travel handshake**: new protocol messages
      `TRAVEL_REQUEST`/`INVITE`/`RESPONSE`/`BEGIN`/`READY`/`COMPLETE`/`ABORT`
      and a server-side `TravelCoordinator` holding one `TravelSession` per
      room. The initiator's room members are invited (everyone except the
      initiator); travel begins only when every invitee accepted (or
      immediately when solo), with watchdog timeouts (invite 15s / ready 30s,
      injectable for tests). All-or-nothing: any decline, member disconnect,
      wrong-zone READY, or timeout abort broadcasts `TRAVEL_ABORT` with the
      reason; a newer request supersedes the active one.
- [x] **Clock sync**: `CLOCK_SYNC` message (zone, absolute_ticks, real_time,
      clock_speed). The server caches the latest beacon on each player and
      relays beacons in-room with a stamped origin. After a completed travel it
      re-broadcasts the initiator's stored beacon (excluding the initiator)
      so the room can realign game time.
- [x] **Client travel integration**: `LocalSession` travel state machine
      (idle/invited/traveling/traveled), auto-accept (`auto_accept_travel`,
      plus a per-request `travel_controller` override), and a best-effort
      game hook that triggers `sim_info.send_travel_switch_to_zone_op` on
      `TRAVEL_BEGIN`. A repeating-alarm poller reports `TRAVEL_READY` once the
      game reports the target zone running (`services.current_zone_id()`,
      `zone.is_zone_running`); where the hook is unavailable it logs a hint to
      use `mp.travel_ready`. New commands: `mp.travel <zone_id>`,
      `mp.travel_ready`, `mp.travel_autoaccept on|off`, `mp.clock`.
- [x] **Config**: new `auto_accept_travel` boolean in `Sims4Multiplayer.json`,
      applied on auto-connect and honored by `mp.autoconnect`.
- [x] **Smoke tooling**: `tests/smoke/smoke_client.py` gained `--travel`,
      `--autoaccept`, `--travel-ready`, and `--clock`, enabling a scripted
      two-client host/invite/BEGIN/READY/COMPLETE run against the live server.
- [x] Tests: server travel flows (invite/accept/begin/ready/complete, solo
      begin, decline abort, invite/ready timeouts, member-disconnect abort,
      wrong-zone abort, unregistered rejection, clock relay), client travel
      flow (two `MultiplayerClient`s against a real in-process server:
      request -> invite -> auto-accept -> BEGIN -> manual READY -> COMPLETE,
      decline path, clock mirroring), protocol builders + validation rules for
      all new messages. Full suite: `python tests/run_tests.py` -> 93 tests
      (the hardening pass added keep-alive/reap/presence-TTL coverage).
- [x] In-game UI (toast/popup) for travel invites: no longer deferred - the M6
      travel-invite dialog surfaces it in-game (see the M6 section), with the
      console fallback and `auto_accept_travel` behavior intact.

## M4 - World-state replication (DONE)

- [x] Protocol v3: new message types `OBJECT_CLAIM`, `OBJECT_RELEASE`,
      `OBJECT_UPDATE`, `WORLD_STATE`, `WORLD_DELTA`, `OBJECT_OWNERSHIP`,
      `OBJECT_CLAIM_ACK`; structural validation for object entries (non-empty
      keys <= 64 chars, <= 32 fields, primitive-only field values, `rev`
      integer, per-message object cap of 16, `WORLD_DELTA.seq >= 1`) and the
      `owner` int-or-null special case.
- [x] Server authoritative **object catalog** per room (`Session`): claim is
      first-come-first-served (`OBJECT_CLAIM_ACK` to the winner +
      `OBJECT_OWNERSHIP` broadcast), release clears the owner, `OBJECT_UPDATE`
      is ownership-checked (`ERROR OBJECT_LOCKED` / `ERROR OBJECT_NOT_FOUND`)
      and only changed fields are merged. A per-room monotonic world `seq`
      rides on every `WORLD_DELTA` relay (never echoed to the sender).
- [x] `WORLD_STATE` full snapshot sent right after `ROOM_STATE` on both `HELLO`
      and `JOIN_ROOM`, so late joiners self-heal.
- [x] Client `WorldMirror`/`ObjectMirror` (pure, offline-testable): full
      replace on snapshot, field merge + stale-`seq` drop on delta, owner
      tracking, and lerped `display_position(now)` for smoothing.
- [x] Client wiring: `claim_object`/`release_object`/`update_object`,
      `set_world_sampler`, a periodic world tick that pushes only locally-owned
      objects (`world_sync`/`world_interval` config), and console commands
      `mp.claim`, `mp.release`, `mp.obj`, `mp.world`. `sample_world_objects()`
      is a best-effort hook currently returning `[]` (see open question).
- [x] Smoke tooling: `--world <key>` claims an object and pumps position
      deltas; `--ping` added earlier gives every smoke client a heartbeat.
- [x] Tests: protocol builders + validation for every new message, full
      server claim/update/lock/release flow with a late joiner, mirror unit
      tests, and a two-`MultiplayerClient` integration test (claim -> own +
      peer ownership ack, locked + not-found errors). Full suite:
      `python tests/run_tests.py` -> 118 tests.
- [ ] Open question for the game hook: what identifies a world object across
      sessions. The protocol assumes a stable string `key` per object per room;
      the in-game sampler (`sample_world_objects`) is left unimplemented until
      object identity (e.g. object id vs. persistent id) is confirmed in-game.
      Until then `mp.claim`/`mp.obj` exercise the path manually.

## M5 - Interaction sync & conflict resolution (DONE)

- [x] Protocol v4 (the M4 blurb above is now historical; v3 -> v4 is the M5
      cut): new message types `INTERACTION_REQUEST`, `INTERACTION_END`
      (client -> server) and `INTERACTION_START`, `INTERACTION_FREE`,
      `INTERACTION_STATE` (server -> client). `ERROR` gained an optional
      `ref` payload field carrying the offending object key. Structural
      validation: non-empty `object_key`/`interaction` strings (keys <= 64,
      types <= 128 chars), `started_at`/`cooldown_until` numbers,
      `player_id` ints, and `args` limited to dicts of JSON primitives with
      capped keys.
- [x] Server-authoritative **interaction store** per room (`Session`):
      first-come, first-served per object key; a grant broadcasts
      `INTERACTION_START` to the whole room **including the sender**
      (echo-style, so one broadcast confirms to the requester and updates
      every peer - no separate ack). Denials are explicit `ERROR` replies
      (`INTERACTION_BUSY`, `INTERACTION_COOLDOWN`, `INTERACTION_NOT_HELD`)
      with the key in `ref`.
- [x] Cooldown + watchdog: ending (or releasing) an interaction starts a
      `interaction_cooldown` (default 5s, injectable) during which the key is
      refused; the reaper auto-releases interactions older than
      `interaction_max_duration` (default 300s, injectable), emitting
      `INTERACTION_FREE`. Note: M5's "disconnect releases everything a holder
      has" behavior was replaced in M6 by the ghost holding period (below), so
      a disconnect no longer emits an immediate `INTERACTION_FREE`.
- [x] `INTERACTION_STATE` full snapshot sent right after `WORLD_STATE` on both
      `HELLO` and `JOIN_ROOM`, so late joiners and lost broadcasts self-heal.
- [x] Client `InteractionMirror` (pure, offline-testable): active interactions
      keyed by object, cooldown bookkeeping, room guards on broadcast applies.
- [x] Client wiring: `propose_interaction(key, interaction, args=None)` and
      `end_interaction(key)`, `set_interaction_sampler`, a periodic interaction
      tick that proposes sampled keys that are free and not denied and ends
      sampled interactions no longer reported (`interaction_sync` /
      `interaction_interval` config, mirroring the world-sync pattern),
      per-key denial backoff (10s, cleared early by any START/FREE), and
      console commands `mp.inter <key>/<type>`, `mp.inter_end <key>`,
      `mp.inter_list`. `sample_interactions()` is a best-effort hook currently
      returning `[]` (see open questions).
- [x] Smoke tooling: `--interact <key>/<type>` proposes an interaction right
      after WELCOME; combined with `--interact-end` it ends it after 3s.
- [x] Tests: protocol builders + validation for every interaction message and
      the `ref` on `ERROR`; server flow (FCFS grant + echo to a bystander,
      busy/cooldown/not-held errors, cooldown expiry re-grant, `INTERACTION_STATE`
      for a late joiner, watchdog auto-release with a tiny
      `interaction_max_duration`); `InteractionMirror` unit tests; config keys;
      and a two-`MultiplayerClient` integration test (propose -> both mirrors,
      busy denial with backoff, release -> cooldown, plus an auto-sampler test
      that proposes and ends a sampled interaction). Full suite:
      `python tests/run_tests.py` -> 138 tests.
- [ ] Open questions for the game hooks (unchanged from M4, extended for M5):
      object identity across sessions, AND now: what the `interaction` type
      string should be and how the game reports an active Sim interaction
      queue. `sample_world_objects()` and `sample_interactions()` both return
      `[]` until verified in-game; until then `mp.claim`/`mp.obj` and
      `mp.inter`/`mp.inter_end` exercise the paths manually.
- [x] In-game UI for interaction conflicts (toast/popup): done in M6 (see the
      M6 section) - connection errors toast via the UI notifier; the
      travel-invite dialog and interaction-conflict surface are implemented
      there too.

## M6 - In-game UI & reconnect hardening (DONE)

- [x] **In-game UI layer** (`simmp_client/ui.py`, offline-safe): a `GameUI`
      facade with `note()` (always to console), `toast()` and
      `travel_invite()` (only when `enabled` and the game's dialog service is
      reachable). Uses public game APIs `services.get_ui_dialog_service(0)`,
      `ui.ui_dialog.UiDialogNotification` / `UiDialogOkCancel`, and
      `sims4.localization.LocalizationHelperTuning.get_raw_text`. Outside the
      game, `available()` is False and every show method returns False without
      raising.
- [x] **Notifications**: the console notifier doubles as the `GameUI` console,
      and `[MP][ERROR]` lines are toasted in-game (`ui_dialogs: true`, the
      default). `mp.ui on|off` toggles it at runtime; `mp.ui_test [text]` shows
      a test toast.
- [x] **Travel-invite dialog**: the travel controller now opens a
      `UiDialogOkCancel` invite when `ui_dialogs` is on and the dialog service
      is reachable, deferring the decision (`_decide_travel` returns `None`)
      and responding from the dialog callback; the dialog's response listener
      handles `UiDialogResponse.Ok` by string comparison (robust across game
      patches) and triggers the abort on decline. Falling back to
      `auto_accept_travel` when UI is unavailable keeps the game working in
      the main menu. (`_decide_travel`) and the `TRAVEL_INVITE` handler now
      support the async (deferred) decision path.
- [x] **Reconnect restores ownership** (ghost scheme): a disconnected player
      becomes a "ghost" for `ghost_ownership_ttl` (default 60s, injectable).
      World ownership and held interactions stay reserved - **no** release
      broadcast during the window - so a same-`client_id` reconnect reuses the
      same identity, room, and state (verified via reconnect snapshots).
      `handlers.py` clears `disconnected_at` on resume.
- [x] **Ghost eviction**: the reaper (`expire_ghosts`) evicts ghosts past the
      TTL: releases their interactions (cooldown + `INTERACTION_FREE`),
      clears their object ownership (`OBJECT_OWNERSHIP` owner `null`, excluding
      the dead peer), and forgets the identity, so a much-later reconnect
      starts fresh with a new `player_id`.
- [x] **Client-side reclaim fallback**: `_capture_dropped_state()` remembers
      what the client owned/held at the moment of a drop (alarm detection or
      an explicit `reconnect()`); after the reconnect snapshots land,
      `_maybe_reclaim()` re-claims world keys that are not owned by another
      player and re-proposes interactions that are unheld, not denied, and
      past cooldown. Covers server-state loss (e.g. a restart) where no ghost
      exists to resume; a fresh `connect()` after a drop performs the same
      reclaim.
- [x] **Auto-reconnect with exponential backoff**: `engine.reconnect()` now
      also works from the `DISCONNECTED` state (the engine loop/thread keep
      running after a drop), and the connectivity alarm runs
      `_maybe_auto_reconnect()`: while `auto_reconnect` is on and the engine
      is down it schedules a fail-safe reconnect (async, engine thread - the
      game thread never blocks) and doubles the delay per failed attempt up to
      `reconnect_backoff_max`, resetting on success. A `mp.disconnect()`
      cancels the retry schedule. Config keys `auto_reconnect`,
      `reconnect_backoff_min` (2.0), `reconnect_backoff_max` (30.0) +
      `mp.auto_reconnect on|off` (runtime toggle, shown in `mp.status`). Once
      reconnected, the ghost resume or the reclaim fallback restores state.
- [x] **Frame-size pressure tests**: encode-at-limit boundary
      (`test_encode_at_limit_and_one_over`) plus server resilience: oversized
      frames, garbage JSON bodies, and a multi-megabyte structurally-valid
      `WORLD_STATE` are all rejected with `ERROR MALFORMED` (or dropped) and
      the server keeps serving fresh clients.
- [x] Config: `ui_dialogs` (bool, default True) plus the auto-reconnect keys
      `auto_reconnect` (True), `reconnect_backoff_min` (2.0),
      `reconnect_backoff_max` (30.0), all validated, applied on auto-connect
      and `mp.autoconnect`, and toggled at runtime via `mp.ui` /
      `mp.auto_reconnect`.
- [x] Tests: server ghost hold/takeover + eviction (with a tiny
      `ghost_ownership_ttl`), client reconnect restore and reclaim-after-
      server-loss, auto-reconnect backoff + restore after a server restart
      (engine reconnect-from-`DISCONNECTED` and the full client retry/reclaim),
      travel-controller deferral/abort round-trip, offline UI fallback
      semantics, config round-trips + validation, and the frame-size
      resilience tests. Full suite: `python tests/run_tests.py` -> 155 tests.
      Package rebuilt:
      `client_mod/build_script_mod.py package` -> 44 entries, `.py`/`.pyo`
      pairs only, no bytecode leaks.
- [x] **Live-game discovery (necessarily game-side)**: the mod was installed
      into a real game and did not connect. The game's `lastException`
      revealed `ModuleNotFoundError: No module named 'asyncio'`
      (`engine.py:14`) - the game's bundled CPython 3.7 ships **no asyncio**.
      The client engine was rewritten from an asyncio event loop to a
      background daemon thread owning a raw blocking `socket` (`select`-driven
      read loop, heartbeats, threadsafe send/drain), keeping the same public
      API. `framing.FrameDecoder` added (incremental sync decode for the
      threaded client; the server's asyncio `read_frame` is unchanged). The
      `uuid` dependency was replaced with `random`-based ids and the engine's
      `logging` import is guarded (the game ships `sims4.log`, not stdlib
      logging). All 155 offline tests still pass against the threaded engine,
      and a live-end-to-end drop -> auto-reconnect (with backoff) -> reclaim
      round-trip is confirmed over a real TCP server.
- [x] **Live-game discovery (necessarily game-side) II**: `find_config_file`
      treated an explicit missing path as "fall through to the game-directory
      search"; once a real `Mods/Sims4Multiplayer.json` existed, that fallback
      returned the game config for a missing explicit path. An explicit path
      is now authoritative (no silent fallback).
- [ ] Remaining game-side verification (can only be done in-game): the
      `UiDialogNotification` toast and the `UiDialogOkCancel` travel invite
      rendering, plus object/interaction samplers (see open questions). Offline
      tests lock the fallback/wiring; the dialog overlay itself needs a real
      running game to confirm.

## M7 - Live sim replication hooks (DONE)

Resolves the M4/M5 sample-hook gaps for the sim case. Unit + integration tests
are locked offline; the live-data result still needs one in-game confirmation
(see Remaining verification).

- [x] **Real `sample_world_objects()`**: samples the player's active sim
      (`services.active_sim_info()` -> `get_sim_instance()`) and emits one
      entry `{"key": "sim:<sim_info.id>", "fields": {...}}` where fields carry
      `x/y/z` position, `qw/qx/qy/qz` orientation, and `def` (definition id).
      Reads go through the public `obj.location.transform.translation`
      / `.orientation` accessors. Returns `[]` offline and before a household
      loads. The sim's persistent `sim_info.id` gives a cross-session stable
      key, answering the M4 identity open question for sims.
- [x] **Real `sample_interactions()`**: emits
      `{"key": "sim:<id>", "interaction": "<ClassName>"}` for the active sim's
      currently-playing interaction (plus queued ones, capped at 3, deduped by
      class). Uses public `sim.get_currently_playing_interaction()` and the
      iterable `sim.queue`. Returns `[]` offline.
- [x] **Auto-claim in the world tick**: `_maybe_send_world_update` now claims
      sampled keys this client does not yet own (one in-flight claim per key,
      cleared on `OBJECT_CLAIM_ACK`/`OBJECT_OWNERSHIP`), so the active sim's
      position streams to the room automatically without `mp.claim`. Compose
      with the M6 ghost/resume and reclaim paths (re-claim on reconnect).
- [x] Tests: a two-client integration test (fake sampler -> auto-claim ->
      exactly one claim on the wire -> peer merges the pushed delta), and
      offline game-hook tests (samplers return `[]`; `_vec3`/`_quat`/
      `_sim_world_entry` field mapping). Full suite:
      `python tests/run_tests.py` -> 162 tests.
- [ ] Remaining game-side verification (can only be done in-game): confirm in
      a running zone that `active_sim_info()`/`get_sim_instance()`/
      `location.transform` and `get_currently_playing_interaction()` behave as
      documented and that positions stream between two connected clients.
- [ ] Accepted v1 limitations (documented in `docs/sims4-research.md`): only
      the active sim is replicated (household members, non-sim objects, and
      furniture-level interaction conflict keys are future work); remote
      entries are mirrored but no local avatar is spawned/moved yet.

## M8 - Receive-side sim rendering (DONE)

The counterpart of M7: remote sim positions are now applied to the local
game, so a peer's sim moves on your screen when both clients share the same
save (the sim exists in each local game with the same persistent id).

- [x] **`game_hooks.apply_world_updates(entries)`**: parses `sim:<id>` keys,
      resolves the local `SimInfo` via `services.sim_info_manager().get(id)`,
      takes its live instance via `get_sim_instance()`, and moves it by
      setting `sim.location = Location(Transform(Vector3(pos), Quaternion(ori)),
      SurfaceIdentifier(zone_id, 0, SURFACETYPE_WORLD))`. Skips non-sim keys,
      unknown sims, un-instanced sims, missing/unchanged positions (epsilon
      < 0.05 units), and never raises. Returns the count moved (0 offline).
- [x] **Client wiring** (`connectivity.py`): `set_world_applier(applier)` +
      `_notify_remote_world()` calls the applier on the game thread right
      after every `WORLD_STATE`/`WORLD_DELTA`, handing it only entries whose
      mirror owner is another player (never the client's own driven sim).
      `install_presence_sampler()` now installs `apply_world_updates`.
- [x] Tests: offline applier returns 0 / helper parsing (`_sim_id_from_key`,
      `_position_from_fields`, `_orientation_from_fields`), and a two-client
      integration test (Alice claims+updates `sim:77`; Bob's applier receives
      it with owner=Alice; Alice's applier is never called with her own key).
      Full suite: `python tests/run_tests.py` -> 164 tests.
- [ ] Remaining game-side verification (can only be done in-game): confirm
      `sim.location = Location(Transform(...), surface)` moves an instanced
      sim as expected at current patch level, and that two clients sharing a
      save see each other's sim controller move on the lot.
- [ ] Accepted v1 limitations: a sim driven by a remote peer can still be
      moved by the local game's own autonomy between sync ticks (the next
      delta re-snaps it); household members are still not replicated; the
      interaction mirror remains read-only presence (no scripting of the
      remote sim's behavior); no anti-fight control-handed-over UI.

## M9 - Automated control, no user setup (DONE)

No explicit control wiring: every player plays normally — click any sim,
use whatever the pie menu offers, and the sync system figures out who drives
what automatically.

- [x] **Household-wide sampling, automatic**: `sample_world_objects`/
      `sample_interactions` iterate the whole playable household
      (`services.active_sim_info().household.sim_infos`), so a client pushes
      every instanced household sim it owns with no commands at all. Falls
      back to the active sim alone when no household exists.
- [x] **`mp.control` removed**: the manual sim-selection command and its
      `client.control_sim_ids` field are gone. Control is purely implicit —
      click a sim, do the on-screen actions, and claims/releases happen by
      themselves on the world tick.
- [x] **Claim arbitration on the wire**: the server attaches `ref=<key>` to
      `OBJECT_LOCKED` errors (both claim and update paths). The client
      discards that key's in-flight guard and backs off 30s (no claim ping
      spam) on every lock, and clears the backoff the instant an `OBJECT_OWNERSHIP
      owner=null` broadcast shows the key is free again - so a player takes
      over a sim ~one tick after its previous controller releases/disconnects.
- [x] Tests: `ERROR OBJECT_LOCKED` carries `ref`, client deny-backoff state on
      lock, in-flight cleared, and the backoff cleared on release. Full suite:
      `python tests/run_tests.py` -> 164 tests.
- [ ] Remaining game-side verification (can only be done in-game): the
      household iteration (`.household.sim_infos` + per-sim instances) and a
      two-client household split in a real shared save.
- [ ] Accepted v1 limitations: claim arbitration is first-come-first-served
      (the sim a player actively clicks is claimed a tick later, but a
      simultaneous click by both players resolves to whichever client claimed
      first); a multi-active-sim session still fights local autonomy on
      non-driven sims (the loser's copy snaps back each tick).

## M10 - Interaction execution on remote sims (DONE)

The label-only interaction mirror is now also an *executor*: when another
player's sim is doing something, the local copy of that sim runs the same
super-interaction, so the mirrored sim visually performs the action instead
of only wearing a label.

- [x] **Affordance identity on the wire**: the interaction sampler now emits
      `{"key", "interaction", "affordance", "affordance_id", "target"}` when
      it can resolve them (guarded helpers that never raise). `affordance_id`
      is the tuning guid64 of the super affordance the player clicked, the
      durable identity the receiving client needs; `target` is the aim
      `sim:<id>` when the interaction points at another sim (self/object
      targets are omitted - only sims are replicated).
- [x] **Protocol + server passthrough**: `INTERACTION_REQUEST`/`START` and
      `INTERACTION_STATE` entries may carry `affordance_id` (int),
      `affordance` (str), and `target` (str); all optional and type-validated.
      The server stores and echoes them unchanged (FCFS reservation logic is
      untouched), so room snapshots for late joiners keep the hints.
- [x] **Client mirror**: `InteractionMirror.apply_start`/`apply_full` persist
      the three hint fields; `application` of `INTERACTION_START`/`STATE`
      routes remote-owned entries to a pluggable interaction applier
      (`set_interaction_applier`) on the game thread - never this client's
      own driven sims, and with the affordance/aim data intact.
- [x] **`game_hooks.apply_interactions(entries)`** (receive-side executor):
      resolves the local sim by persistent id, resolves the super affordance
      by tuning id (falling back to name), skips sims already running that
      affordance, aims at the mirrored target sim when present, and pushes via
      `sim.queue.push_interaction` / `sim.push_super_affordance`. Every step is
      guarded and degrades to label-only mirroring (returns 0 offline).
- [x] Reconnect path: `_capture_dropped_state`/`_maybe_reclaim` now carry the
      affordance/aim hints so a re-proposed interaction after a drop restores
      the full identity.
- [x] Tests: protocol builders + validation for the new fields (positive and
      negative), server FCFS passthrough incl. the late-joiner snapshot,
      client mirror persistence, interaction-applier wiring (Bob's applier
      receives Alice's interaction with hints; Alice's applier never gets her
      own entry), online sampler reconcile, offline no-ops. Full suite:
      `python tests/run_tests.py` -> 169 tests.
- [ ] Remaining game-side verification (can only be done in-game): that
      `get_affordance()`/`affordance_id` resolve as documented on a real
      running interaction, that `sim.queue.push_interaction` (or
      `push_super_affordance` fallback) starts the interaction on a mirrored
      sim, and that the pushed interaction does not re-fire its own sampler
      loop (the FCFS mirror already dedupes, but an in-game check is needed).
- [ ] Accepted v1 limitations: interaction execution is a best-effort *push* -
      the receiving sim starts the affordance when it resolves and the sim is
      free; it does not replicate interaction progress, skill outcomes, or
      object-targeted actions (objects are not replicated). Result anims and
      socials between two household sims on a shared lot are the primary
      target.
- [ ] Interaction args (`{"book": ...}` etc.) are carried on the wire but not
  consumed by the executor yet.

## M11 - Save sync, UI and dev tooling (DONE)

- [x] SAVE_PUSH/SAVE_ACK protocol extension: `MAX_SAVE_CHUNK_BYTES=512 KiB`,
  bare-filename slot rule, seq/total/size/base64 validation, `SAVE_ACK`
  `reached>=0`, `origin` stamped by server, saved in validation INT_FIELDS.
- [x] Server: `_handle_save_push` relay to room peers (excludes sender) +
  `SAVE_ACK` with `reached=len(peers)` + `--status-file` JSON snapshot rewritten
  every 1s (atomic `os.replace`; writes on stop).
- [x] Client: `state/save_transfer.py` (`SaveInbox` reassembly with 600s prune
  window; `atomic_write` via temp+fsync+os.replace; `split_bytes` raw slices);
  engine `send_save_push`; connectivity `push_save_chunk` / `push_save_file`
  (raw-bytes splitting, fixes the earlier double-base64 encode bug) +
  SAVE_PUSH/SAVE_ACK handlers in `_handle_message`.
- [x] `game_hooks.receive_save`: `find_save_directory` scans candidate saves
  folders and immediate profile subfolders (prefers a folder already holding
  the slot; else scores by `*.save` count, ties go deepest), then writes via
  `atomic_write`.
- [x] Cheat commands: toast notifications on NET connect/disconnect, ROOM
  join/leave, and SAVE received; `mp.save_status` (shows inbox summary + save
  roots); `mp.save_push <path> [slot]` to push a local save from the game
  console.
- [x] `tools/save_sync.py`: standalone push client (HELLO → WELCOME → chunked
  SAVE_PUSH → wait SAVE_ACK → exit 0 when `reached>=1`). Uses a background
  `ThreadPoolExecutor` for the blocking `sendall` so the asyncio loop can
  still drain replies (a blocking `sendall` on the event-loop thread deadlocks
  via TCP buffer starvation).
- [x] `tools/dev_console.py`: tkinter GUI (stdlib only) with server start/stop,
  players list (from --status-file JSON), server log tail, Sync save button
  (runs save_sync.py), Run offline tests, Launch game, Launch smoke player,
  Build + deploy, and Show diag file (`Sims4Multiplayer-diag.txt`).
- [x] Tests: `python tests/run_tests.py` → **194 tests OK** (was 169 at M10; +14
  save-transfer + 11 protocol/server save-sync tests).
- [ ] In-game: verify the alarm span fix (restart game → `mp.diag` → read
  `Sims4Multiplayer-diag.txt` from the Mods folder → expect `span: real-time
  0.5s built`, `alarm=armed last_tick=...`; live smoke M10 interaction mirror
  test).
- [ ] In-game: end-to-end save sync — push a save with `tools/save_sync.py`
  while the game is connected; verify the game writes the slot to the correct
  saves folder (checked via `mp.save_status`).
- [ ] Accepted v1: save sync distributes raw save bytes; no delta sync, no
  conflict resolution, no auto-trigger from the save menu (manual push via
  `mp.save_push` or `tools/save_sync.py` only).

## M12 - Shared time / clock gate (DONE)

- [x] Protocol: `TIME_READY`, `TIME_SPEED`, `TIME_SYNC` messages with
  required/optional fields; clock speed constants (`CLOCK_SPEED_PAUSED/NORMAL/2/3`);
  validation (`speed` 0..3, `ticks >= 0`, missing-zone rejection).
- [x] Server time gate: `Room.clock` stores desired speed + last requesting
  player + ticks; `clock_gate_open`/`clock_snapshot`; disconnected players
  stay as clock participants (gate holds the room PAUSED until every member
  including ghosts has signalled ready); mid-session disconnect auto-pauses;
  `HELLO`/`JOIN_ROOM` mark not-ready and re-sync; `TIME_SPEED` stores the
  desired speed (last change wins) and `sync_clock` broadcasts
  `TIME_SYNC` to the room; ghost eviction re-opens gate and re-syncs.
- [x] Client: `game_hooks` `get_clock_speed` / `set_clock_speed` /
  `pause_game` / `unpause_game` (uses `ClockSpeedMode`); `connectivity`
  TIME_SYNC handler with echo-window suppression, `_apply_room_speed` +
  `_maybe_sync_clock` poller (sends TIME_READY once per connection when
  zone running, reset on every WELCOME); `engine` `send_time_ready` /
  `send_time_speed`.
- [x] Cheats: `mp.time` (print current speed), `mp.pause` (0),
  `mp.resume` (1), `mp.speed N` (2/3), `mp.ready`; `_mp_diag` now
  calls `_maybe_init()` and prints `time=` line; auto-connect alarm
  delay reduced to 2 s so `mp.diag` works on launch without a prior
  command.
- [x] Dev console: dark flat theme with a left sidebar (Host / Players /
  Tests & Build / Log). The Host page shows the save-slot cards at full
  180x120 with the baked color thumbnail (JPEG read off the `.save` head
  and decoded to PNG via Windows GDI+, cached; the baked grayscale PNG is
  the fallback) plus editable persisted slot labels, then only IP/port and
  a single Host/Stop toggle. Players page lists rooms + the per-room
  clock gate (speed / ready counts). Log page tails `server.log` and all
  tool output with append-only diffs; auto-read of the game diag file for
  3 minutes after launching the game. The true in-game slot name is left
  out of scope: it lives inside the LZ4-compressed DBPF index
  (SaveGameData protobuf), so slots show `Slot_<id>` + a user label for now.
- [x] Tests: `python tests/run_tests.py` -> **209 tests OK** (was 194
  at M11; +15 time-sync: validation, server gate flows, client handler
  unit tests).
- [ ] In-game: end-to-end verify — host + smoke player both join, host
  `mp.pause` / `mp.resume` / `mp.speed 2`; smoke player auto-readies
  via the alarm tick; confirm the room broadcasts match the expected
  gate → open → stored speed flow.

## M13 - Split-zone worlds (DONE)

Each connected player effectively owns a private copy of the room's world
space per zone: the server partitions the object catalog, ownership, the
interaction table and the world-delta sequence by **zone** inside a room, and
routes all world/claim/interaction traffic zone-scoped. This fixes the
M7-M12 "two players in different zones smear a single shared world" problem
(travel alone overwrote everyone's catalog) without breaking the common
same-zone case.

- [x] Global protocol: `zone_id` added as an optional field (int) to
  `OBJECT_CLAIM`, `OBJECT_RELEASE`, `OBJECT_UPDATE`, `WORLD_STATE`,
  `WORLD_DELTA`, `OBJECT_OWNERSHIP`, `INTERACTION_REQUEST`, `INTERACTION_END`,
  `INTERACTION_START`, `INTERACTION_FREE`, `INTERACTION_STATE`. Additive only,
  no version bump (still v4). `simmp/messages.py` builders and
  `constants.OPTIONAL_PAYLOAD_FIELDS` updated together.
- [x] Server store (`server/state/session.py`): world objects +
  per-zone `world_seq`, interactions, and cooldowns keyed by `(room_id,
  zone_id)`; helpers `player_zone` (ready zone, else presence zone),
  `_zone_key`, `dominant_room_zone`, `release_player_zone`. Expire/scan
  methods carry zone tuples so the reaper and ghost eviction stay
  zone-scoped.
- [x] Server routing (`networking/server.py` + `protocol/handlers.py`):
  `broadcast_zone(room_id, zone_id, message)` delivers to members whose
  `player_zone` is `None` or equals `zone_id`, so unknown-zone (still-gated)
  members keep receiving everything for bootstrap. Claim/update/interaction
  handlers resolve the writer's zone (`_zone_of`: payload `zone_id` else
  `player_zone`) and stamp it on broadcasts.
- [x] **Travel flip auto-release**: on `TIME_READY` announcing a different
  zone, the server releases everything the departed player held in the old
  zone (`OBJECT_OWNERSHIP owner=null` + `INTERACTION_FREE`, zone-stamped),
  then sends the traveler a fresh `WORLD_STATE` + `INTERACTION_STATE` for the
  new zone. The clock gate stays room-level (single save clock); re-gating on
  zone change is unchanged.
- [x] Client (`state/world.py`, `state/interactions.py`, `state/session.py`):
  both mirrors track a `zone_id`; `WORLD_STATE` for another zone replaces the
  mirror wholesale (travel snapshot), `WORLD_DELTA`/ownership/interactions
  from another zone are dropped. Writes (`claim`/`release`/`update`/interact)
  carry the live zone id from `game_hooks.current_zone_id()`.
- [x] In-game notifications (`notifications.py` + `commands/cheat_commands.py`):
  the toast decision logic lives in a pure, offline-testable module now.
  New toasts: travel invite/begin/complete/abort, remote interaction start on
  a sim you own ("Alice is Read on sim:..."), remote ownership takeover
  ("Alice took over sim:..."), reconnecting, with per-bucket cooldowns so
  broadcast bursts don't flood the screen. Existing connect/disconnect/
  room/save/error toasts preserved.
- [x] Tests: rewrote `test_world.py`/`test_interactions.py` for zone-aware
  mirrors, added `tests/test_zones.py` (isolated zones share no world,
  unknown-zone bootstrap delivery, same-zone sharing + flip releases), and
  `tests/test_notifications.py` (toast mapping). Live split-zone smoke
  `tests/smoke/smoke_split_zone.py` runs the real server binary and asserts
  the full cross-zone + flip-release flow (11/11). Full suite:
  `python tests/run_tests.py` -> **239 tests OK**.
- [ ] In-game verification (can only be done in-game, confirmed live already):
  a solo game travel with the game's own UI flips zones and releases holdings
  correctly (observed in a live run: `released 7 object(s), 6 interaction(s)`
  then re-claim + re-interact in the new zone). The real two-client
  split-zone scenario (both in different zones at once) still needs two game
  instances on a LAN.
- [ ] Accepted v1 limitation: the clock/readiness gate is room-wide, not
  per-zone; one save = one shared clock, so "same household playing in two
  zones simultaneously" is not achievable in a single save regardless of
  zone-scoping. What zone-scoping delivers is isolation (no cross-zone
  smearing) and a clean solo-travel/rejoin.

## M14 - Autonomy suppression for peer-driven sims (DONE)

Fixes the M8 accepted limitation: "a remote-driven sim can still be jostled
by local autonomy between sync ticks (re-snapped on the next delta)". When
one game is driving a sim the *other* game should not run its own autonomy
on that sim, so it does not fight the owner between world syncs.

- [x] Config flag `autonomy_suppression` (default on): pure
  `_coerce_and_validate` bool, wired through `sims4_plugin._apply_config`
  into `MultiplayerClient.autonomy_suppression`.
- [x] Client plumbing (`connectivity.py`): `set_autonomy_reconciler` hook +
  `_reconcile_autonomy(keys)` which compiles the set of `sim:<id>` keys whose
  mirror owner is another player (from the world mirror) and hands them to
  the reconciler. Runs after every `WORLD_STATE` / `WORLD_DELTA` and every
  ownership change (`OBJECT_OWNERSHIP`, `OBJECT_CLAIM_ACK`), so a released
  sim regains autonomy immediately on the release broadcast.
- [x] Game hook (`game_hooks.py`): `reconcile_autonomy(remote_owner_keys,
  my_player_id, my_zone_id)` walks the active household's instanced sims and
  toggles per-sim autonomy via `set_sim_autonomy(sim_info, enabled)`, a
  best-effort try-in-order helper: `sim_info.set_autonomy_enabled()`, then
  the autonomy component's `set_autonomy_enabled()`, then an
  `autonomy_enabled` attribute setter. Returns True on the first API that
  exists; never raises. Returns `(suppressed, restored, skipped)` for
  diagnostics.
- [x] Command `mp.autonomy on|off` toggles suppression live and immediately
  re-runs a reconcile; no-arg prints current state.
- [x] Tests: offline `test_game_hooks.py` (each API candidate + safe offline
  reconcile), `test_config.py` (flag round-trip), full client flow
  `test_autonomy_reconcile_receives_remote_owner_keys` (remote claim reaches
  reconciler, release clears it, suppression-off never fires). Full suite:
  `python tests/run_tests.py` -> **246 tests OK**.
- [ ] In-game verification (needs two game instances / a peer): confirm a
  peer-owned sim stops generating its own autonomy while the peer drives it,
  and that `mp.diag` reports the autonomy API path in use. On a single
  instance, `mp.autonomy` toggling is observable in the console only.

## M15 - Launcher + lobby + one-file .exe (DONE)

Turns multiplayer into a "give it to a friend" experience: no Python, no
registry edits, no folder hunting. A single windowed executable detects the
game on each PC, installs the mod automatically, and runs a two-tab
host/join lobby where the host shares a save and both sides get a Start
button that launches the game already configured to auto-connect.

- [x] `tools/game_paths.py` (pure, testable): detects the TS4 user folder
  (`Documents/Electronic Arts/The Sims 4`, OneDrive-redirected Documents
  handled), Mods/saves subfolders, and the install exe (`TS4_x64.exe`) via
  the Maxis `Install Dir` registry key, EA-app/Origin/Steam default paths,
  with test-injectable roots.
- [x] `tools/lobby.py` (pure, testable): `find_lan_ip()`, `ServerHandle`
  (runs the real `MPServer` in its own thread with a status.json callback),
  `push_save_file()` (host pushes a slot + waits for the reached-count ack),
  `receive_save_file()` (joiner pumps until the save lands on disk). All
  reuse the existing protocol/connectivity/save-transfer code paths.
- [x] `tools/launcher.py` tkinter GUI (stdlib only): path auto-detection +
  Browse, mod auto-install into the detected Mods folder, Host tab (lobby
  start/stop, save picker, share->ack->Start game gating), Join tab (enter
  host IP -> receive save -> Start game). On Start it writes
  `Sims4Multiplayer.json` (auto_connect) into the Mods folder and launches
  the detected exe (Steam `steam://rungameid/1222671` fallback).
- [x] `tools/build_app.py` PyInstaller wrapper (`--onefile --windowed`) that
  bundles the launcher + lobby + server + protocol + mod sources so the
  target machine needs nothing installed; `Run Launcher.bat` written next to
  the exe. Build: `python tools/build_app.py`.
- [x] Frozen-bundle robustness: in the one-file .exe the bundled data lives
  under `sys._MEIPASS`, so the launcher, the lobby helper and
  `build_script_mod` resolve their project root via `_MEIPASS` (dev falls
  back to `__file__`). A headless self-test (`SIM4_MP_SELFTEST=<dir>`, runs
  the exact "Install mod" path and dumps result.json) proved the .exe
  installs the full mod from the bundle.
- [x] Tests: `tests/test_game_paths.py` (doc/mods/saves/exe detection +
  registry), `tests/test_lobby.py` (real-server end-to-end: push to a
  connected player reaches 1, solo reaches 0, join receives the save into
  the intended folder, server start/stop/restart and port-conflict guard),
  `tests/test_launcher_gui.py` (deferred-error callbacks, LAN IP dropdown,
  frozen self-test install). Full suite:
  `python tests/run_tests.py` -> **270 tests OK**.
- [ ] Manual two-PC handoff test: run the built exe on both machines, host
  opens a lobby + shares a save, the other joins + receives, both Start
  game and land in the shared household. Requires two PCs on the same LAN
  (Windows firewall must allow the launcher/server on the host).

## M16 - Save sharing, joining gate, live money/build (DONE)

Second PC joins a session like the mod always knew what to do: no manual
save copy, no barrier to entry while someone is still loading, and the
household's money plus build/buy object edits flow between the two live
games instead of living inside each machine's save.

- [x] Save-cache replay for late joiners: the server caches a completed
  `SAVE_PUSH` per room and replays it to any client that joins after the
  host pushed (guard: only finished, on-disk caches; never streams a
  half-open file). The joiner requests it automatically right after
  WELCOME (lobby receive path), so the latch that used to wait for the
  host's manual re-share no longer applies.
- [x] Joining gate: time is kept paused until every player (including
  ghosts) has signalled `TIME_READY`. The client now re-pauses eagerly
  while gated (even inside its own echo window) so a player who hits play
  while a peer is still joining cannot run the room ahead.
- [x] `TIME_UNREADY`: when a player leaves the running zone (CAS, manage
  worlds, main menu), the server drops only that player's readiness and
  the room re-gates PAUSED until they send `TIME_READY` again.
- [x] Money sync (`FUNDS_SYNC`, protocol-int validated to
  `MAX_FUNDS_BALANCE`): the client samples the household balance every
  `funds_interval`, broadcasts on change (>= 1 simoleon), and applies a
  peer's absolute balance via `add_money`/`remove_money` deltas.
- [x] Build/buy object sync: the world sampler now also enumerates
  instanced lot objects under `obj:<def>@<grid>` keys (definition +
  coarse position, since runtime object ids differ per machine). Moves and
  new placements are broadcast as `WORLD_DELTA` deltas like sims; deletes
  are detected after two missing ticks (`OBJECT_GONE`, sims excluded,
  suppressed while the zone is not running) and applied locally by
  destroying the nearest same-definition object. New catalog placements
  and structural build apply on the next save reload (shared save).
- [x] Tests (+28): protocol builders/validation for `OBJECT_GONE` /
  `FUNDS_SYNC` / `TIME_UNREADY`, server handler flows (funds echo
  including sender, object-gone ownership/relay/catalog removal,
  unready re-gate & re-open), client funds baseline/throttle/apply,
  gone-detection hysteresis + zone guards, TIME_UNREADY flow, offline
  hook safety. Full suite:
  `python tests/run_tests.py` -> **298 tests OK**.
- [ ] In-game verification (2 PCs, Radmin/LAN): spend simoleons on one
  side while the other watches the balance converge; move/rotate a sofa
  and delete a lamp and watch them mirror; open CAS on one machine and
  confirm the other's game pauses until you return.

## M17 - Live-world hardening (DONE)

Follow-up to M16: the three M16 limitation items that are solvable in pure
client code (no in-game hook work needed) are closed.

- [x] **Deferred object destroy**: `OBJECT_GONE` no longer destroys the
  local copy synchronously. The mirror drops the key immediately, but the
  game object is destroyed only after `object_gone_delay` (5s) unless the
  same definition reappears within ~3 units of the old key - a move whose
  `WORLD_DELTA` was still in flight. This closes the move-vs-delete race
  (a briefly-missing old key no longer reads as a real delete) and the
  wrong-destroy of a surviving twin. `connectivity.py`: `_defer_object_gone`,
  `_maybe_flush_pending_removals`, `_object_reappeared_nearby`.
- [x] **Funds churn guard**: a `FUNDS_SYNC` whose balance equals the last
  value the applier actually applied is ignored (echoes cannot fight the
  applier or force a pointless re-broadcast). `_last_funds_applied` is
  tracked per applied balance.
- [x] **Runtime toggles**: `mp.build_sync on|off` (swaps the world sampler
  between household+lot and sims-only and disables/enables the destroy
  applier), `mp.funds_sync on|off`, and `mp.funds_interval <seconds>`.
  Shared `configure_build_sync`/`configure_funds_sync` helpers are also
  used by `sims4_plugin._apply_config`, so runtime toggles and the
  startup config can never drift apart.
- [x] Tests (+3 net): funds echo-ignore + two distinct applies; deferred
  destroy flushed after the window; destroy cancelled on a nearby same-def
  reappearance; destroy kept for an unrelated far-away definition. Full
  suite: `python tests/run_tests.py` -> **301 tests OK**.

## M18 - Incremental GitHub updates (DONE)

M15's 13.1 MB one-file .exe only changes when the bootstrap itself changes.
Everything else the app and mod run is now synced incrementally from the
public GitHub repo, so an update ships as a handful of small files - no
re-transferring the .exe, and the `Run Launcher.bat` is gone (double-click
the exe).

- [x] **`tools/updater.py`** (stdlib only): fetches the committed
  `runtime_manifest.json` from `raw.githubusercontent.com/MotanOfficial/
  SimsMultiplayerMod/main`, diffs per-file sha256 against the last-applied
  local manifest (`version.json`), downloads only changed/new files
  (sha-verified, one retry, atomic `os.replace`), and stores the applied
  manifest. Offline/moved-repo -> the local runtime is left untouched.
  `changed_mod_files()` flags any `client_mod/` change so the launcher can
  re-install the mod automatically. All network calls go through a pluggable
  `fetcher` for offline unit tests.
- [x] **`tools/make_manifest.py`**: author-side generator - walks the same
  `MOUNT_ROOTS` as the updater, emits `runtime_manifest.json` (version
  defaults to `DATE-git-short-sha`), and lists what changed since the repo
  HEAD-ish marker.
- [x] **Runtime mounting**: a `_RuntimeFinder` meta-path hook is inserted
  ahead of PyInstaller's `FrozenImporter` so every synced module name
  imports from `%LOCALAPPDATA%\Sims4Multiplayer\runtime` (top-level and
  nested, packages and namespace packages, mirroring `protocol/` ->
  `simmp`, `server/` -> `server.*`, `tools/*.py` -> `tools.*` plus the
  top-level `save_metadata` alias). Non-runtime names (stdlib, tkinter, the
  launcher) still resolve from the bundle. Cached bundle copies of routed
  names are evicted from `sys.modules` first. Verified end-to-end with the
  real .exe: the mod install copied the *runtime* `build_script_mod.py`, not
  the bundle copy.
- [x] **Launcher** (`tools/launcher.py`): startup order is now
  `mount_runtime(CODE_ROOT)` -> `_load_app_modules()` (runtime modules
  imported once, not at module top-level) -> GUI/selftest. Auto-update on
  start (default on, settings key `auto_update`), a "Check updates"
  button, and a status line reporting the local/remote version; after an
  update the mod is re-installed into the configured Mods folder when any
  `client_mod/` file changed. First run has no runtime: the check downloads
  the whole runtime (~335 KiB), the user restarts the launcher, and the
  next start runs it.
- [x] **`tools/build_app.py`**: no longer emits `Run Launcher.bat`
  (double-click the exe; the `dist/` .bat is deleted), and the frozen
  bootstrap always bundles `tools.updater` so the running exe never depends
  on a synced updater.
- [x] Tests (+17): manifest validation, plan/apply, full sync round-trips
  (first run, no-op, single-file change, offline, corrupt-file rollback),
  mod-change detection, and runtime mounting over a fake synced tree
  (modules resolve from the runtime dir, not the working copy). Full suite:
  `python tests/run_tests.py` -> **318 tests OK**, plus a frozen-bundle
  selftest (`SIM4_MP_SELFTEST=<dir>`) and a public-repo check.

## M18b - Live-trial bugfix: multi-chunk save push completed too early (DONE)

First real two-PC trial (host = Ashlyne's PC over Radmin VPN, joiner = Motan's
PC): the host's "Save synced to 1 player(s)" never turned the Start Game button
green and the joiner hung on "Connecting to ..." until the 120s timeout fired.
Root cause was in the host-side shortcut, not the server:

- The lobby server acks **every** `SAVE_PUSH` chunk it relays. The host helper
  (`tools/lobby.py::push_save_file`) treated *any* `SAVE_ACK` as completion and
  called `client.disconnect()` immediately - usually right after chunk 1/4.
- The engine's sender is synchronous under a send lock, but the *receive* pump
  is on the caller; killing the client after the first ack aborted the queue
  before the last chunk ever left the socket. The joiner got 3/4 chunks,
  `SaveInbox.feed` never reached `total/total`, no `Saved` line, so the GUI
  timed out with the button still greyed.
- `push_save_file` only sees that the server **broadcast** to one peer
  (`reached=1`); it never learns whether the joiner received everything.

Fix (commit `57c33a6`, manifest `2026-09-18-57c33a6`):

- `SAVE_ACK` now carries `seq`/`total` (optional, backward compatible).
  `push_save_file` waits for the worker to finish queueing **all** chunks,
  verifies `sent == queued_total`, then waits for the ack of the *final* chunk
  (`seq=total/total`) before disconnecting.
- Host Start button uses the live in-memory connected-player count (updated by
  `_apply_status` from the server callback) instead of re-reading a possibly
  stale `status.json` from disk, and drops to disabled when the room empties.
- `receive_save_file` gained an `on_line` callback so the join GUI surfaces
  `[MP][SAVE]` progress and `[MP][ERROR]` lines in real time while the file
  transfers.
- Regression coverage: lobby tests now push >1 MiB multi-chunk saves and
  byte-verify the received file; full suite **320 tests OK**; a two-process
  end-to-end repro (real host/join binaries over a real TCP socket) confirmed
  `4/4 (complete)` + `Saved '...'` after the fix.

## Out of scope until explicit decision

- Full DNA/lot/room package sharing (needs a large asset protocol and
  licensing review).
- Anti-cheat.
- Non-Python (native) server components.

Each proposed milestone must re-check `docs/sims4-research.md` for the game
APIs involved (especially zone/clock/object interactions) and confirm no
part of the design depends on code from S4MP/SimSync.