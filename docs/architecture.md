# Architecture

## Goal

An independent, client/server multiplayer layer for The Sims 4. Multiple
players run the game on their own machines and share one game session.

This document describes the current (M6) architecture. Later milestones will
extend these layers without re-architecting them.

## Principle

The server is authoritative for the **multiplayer session** (who is connected,
what room they are in, important replicated events, travel coordination). It
does **not** simulate the Sims. The game clients remain responsible for all
actual game simulation.

> Do not synchronize every frame. Prefer event synchronization + periodic
> authoritative snapshots + client-side interpolation where it becomes
> necessary (later milestones).

## Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Sims 4 client_mod (runs inside the game, Python 3.7)        │
│                                                             │
│  commands/    mp.* cheat commands (game-only)               │
│  connectivity MultiplayerClient manager                     │
│  networking/  ClientEngine - thread + raw socket (no asyncio)│
│  state/       LocalSession - mirror of server truth         │
│  config/      Sims4Multiplayer.json loader (pure Python)    │
│  presence/    zone/lot helpers + in-game sampler            │
│  hooks/       alarm lifecycle + travel/clock hooks          │
└───────────────────────────┬─────────────────────────────────┘
                            │ length-prefixed JSON over TCP
┌───────────────────────────┴─────────────────────────────────┐
│ protocol/simmp   shared, versioned, validated messages      │
│   constants / messages (builders) / validation / framing    │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│ server (runs on any Python 3.8+, asyncio)                   │
│   networking/  MPServer, Connection (per socket)            │
│   protocol/    Handlers - per message type                  │
│   travel/      TravelCoordinator - group travel state       │
│   rooms/       RoomManager convenience                      │
│   state/       Session - authoritative players + rooms      │
│   main.py      CLI entry point                              │
└─────────────────────────────────────────────────────────────┘
```

Components talk to each other only through the shared `protocol/simmp`
package, so the server, the in-game code, and the wire format can evolve
independently.

## Server architecture

- `server/main.py` — CLI (see below), configures logging, runs the server.
- `server/networking/server.py` — `MPServer`. Owns the asyncio server and the
  set of live `Connection`s. Reads validated frames in a loop per connection,
  dispatches them to handlers, and cleans up on disconnect. A background
  reaper task (`_reaper`, every `reap_interval`) closes connections silent for
  longer than `stale_timeout` and prunes server-cached presence older than
  `presence_ttl` (`Session.expire_presence`).
- `server/networking/connection.py` — `Connection` wraps one TCP stream with
  `send()` / `close()`. Tracks the assigned `player_id`, `name`, `room_id`, and
  `last_activity` — refreshed on every successfully parsed frame, so inactivity
  (including a stalled `HELLO`) is measured in wall time and reaped the same
  way as a dead socket.
- `server/protocol/handlers.py` — `Handlers` maps message type -> coroutine.
  Currently: HELLO (identity resume/takeover via optional `client_id`), PING,
  PONG, JOIN_ROOM, EVENT (seq-dedup + ack), PRESENCE (relay with stamped
  origin identity), TRAVEL_REQUEST/RESPONSE/READY (group-travel handshake),
  CLOCK_SYNC (relay with stamped origin + server cache on the player),
  OBJECT_CLAIM/OBJECT_RELEASE (ownership reconciling + ack + broadcast),
  OBJECT_UPDATE (ownership check, merge changed fields, relay `WORLD_DELTA`),
  INTERACTION_REQUEST/INTERACTION_END (FCFS grant, cooldown, bus/cool/not-held
  errors, echo-style `INTERACTION_START`/`INTERACTION_FREE` broadcasts).
  HELLO and JOIN_ROOM also send `WORLD_STATE` right after `ROOM_STATE`, then
  `INTERACTION_STATE` right after that.
- `server/travel/coordinator.py` — `TravelCoordinator` manages one
  `TravelSession` per room at a time. Holds the invite-response state,
  all-or-nothing accept/abort logic, watchdog timers (invite + ready phases),
  and disconnect cleanup. Aborts the session when a member drops, an
  invitee declines, a deadline passes, or a newer request supersedes it.
- `server/state/session.py` — `Session` is the authoritative store: players
  keyed by `player_id`, rooms keyed by `room_id`, plus a `client_id` -> player
  map for identity resume. `Player` carries the last presence snapshot, the
  highest seen `EVENT` sequence (for resend dedup), a `clock_sync` cache
  populated by `CLOCK_SYNC` messages, and a `disconnected_at` stamp. On
  disconnect a player stays registered as a "ghost" (`connection = None`,
  presence cleared, removed from the room roster, `disconnected_at` set) so a
  returning `client_id` reuses the same `player_id`, room, and dedup state —
  and keeps its world ownership + held interactions reserved.
  `disconnect_player()` guards on `connection is conn` so a takeover never has
  the stale socket tear down the adopted player. The reaper's
  `expire_ghosts(player_ttl, interaction_cooldown)` evicts ghosts past the TTL:
  `release_player_interactions`
  (cooldown + `INTERACTION_FREE`), `release_player_world` (owner -> null +
  `OBJECT_OWNERSHIP`), then `_forget_player` drops the identity from the
  rooms/players/client_id maps, so a much-later reconnect starts fresh. `Player`
  and `Room` are plain records. A `lobby` room always exists.
  `expire_presence(ttl)` nulls cached presence snapshots older than the TTL
  (local arrival time, since peer clocks are not synchronized). The same
  `Session` owns the per-room **object catalog**: `WorldObject` records
  (`key`, `owner` player_id or null, `fields` dict, `rev`), a per-room world
  `seq`, `claim_object`/`release_object`/`apply_world_update`/`get_world_objects`
  for the handlers, and `next_world_seq()` bumps the monotonic per-room seq
  used in the `WORLD_DELTA` header. The same `Session` owns the per-room
  **interaction store**: `_interactions_by_room` / `_cooldowns_by_room` with
  `request_interaction(room, player_id, key, interaction, args)` (returns
  `("start", entry)`, `("busy", holder_id)`, or `("cooldown", until)`; a holder
  re-requesting renews its `started_at`), `end_interaction(...)` (returns
  `("ended", cooldown_until)` or `("not_held", None)`),
  `expire_interactions(now, max_duration)` (watchdog sweep result per room),
  `release_player_interactions(player_id)` (ghost eviction cleanup), and
  `get_room_interactions(room_id)` (for the `INTERACTION_STATE` snapshot).
- `server/rooms/room.py` — thin `RoomManager` convenience over `Session`.

### Message flow (M2 hello + event/presence)

```
Client            Server
  |  HELLO{name}   |
  |--------------->|  validates, assigns player_id, joins "lobby";
  |                |  with client_id: resumes that identity instead
  |  WELCOME       |
  |<---------------|
  |  ROOM_STATE    |
  |<---------------|
  |  WORLD_STATE   |  full catalog snapshot of the room (after join)
  |<---------------|
  |  EVENT{seq=1}  |  dedups by seq, broadcasts relay, acks sender
  |--------------->|----------------------> Other clients in room
  |  EVENT_ACK     |
  |<---------------|
  |  PRESENCE      |  stamps player_id/room_id, relays in-room
  |--------------->|----------------------> Other clients in room
```

### Travel + clock flow (M3)

```
Requester       Server            Invitees
  | TRAVEL_REQUEST(zone) |
  |---------------------->|  one TravelSession per room created
  |                       |----------------------> TRAVEL_INVITE (each)
  |                       |<---------------------- TRAVEL_RESPONSE(accepted)
  |                       |  all accepted (or solo)?
  |<-------- TRAVEL_BEGIN |----------------------> TRAVEL_BEGIN
  | (client travels; game hook)   (clients travel)
  |<-------- TRAVEL_READY |<---------------------- TRAVEL_READY
  |  all READY for target zone?
  |<----- TRAVEL_COMPLETE|----------------------> TRAVEL_COMPLETE
  |  if requester cached a CLOCK_SYNC, it is relayed (excl. requester)
  |                       |----------------------> CLOCK_SYNC{player_id}
```

`TRAVEL_ABORT` is broadcast on decline (`"declined by <name> (<reason>)"`),
member disconnect, `"invite timeout"`/`"ready timeout"`, wrong-zone READY, or a
superseding request. The watchdog timers (15s/30s defaults) are injectable for
tests. The in-game travel trigger (`sim_info.send_travel_switch_to_zone_op`)
and clock sample (`services.game_clock_service()`) are best-effort hooks that
no-op offline, where manual `mp.travel_ready` / `mp.clock` fall back.

### World flow (M4)

```
Owner client      Server                 Room peers
  | CLAIM{key}    |                       |
  |-------------->| catalog[key].owner = pid; seq unchanged
  |  CLAIM_ACK    |                       |
  |<--------------|  OWNERSHIP{owner=pid} |--------------> mirror owner set
  |  UPDATE{key,  |  verify owner == pid  |
  |   fields}     |---------------------->|  merge only changed fields,
  |-------------->|  bump room seq        |  keep if seq > last seen
  |               |  DELTA{seq, delta} ---|-------------->
  |  RELEASE{key} |  owner = null         |
  |<--------------|  CLAIM_ACK (null)     |
  |               |  OWNERSHIP{owner} ----|--------------> owner cleared
```

Anything not owned by the sender comes back as `ERROR OBJECT_LOCKED`; an
`OBJECT_UPDATE` naming a key nobody claimed is `ERROR OBJECT_NOT_FOUND`.
A `WORLD_STATE` snapshot is sent to each client right after `ROOM_STATE`, so a
late joiner sees the full catalog even if it missed every delta.

### Interaction flow (M5)

```
Player client      Server                    Room peers (incl. sender)
  | REQUEST{key,  |                           |
  |  interaction} |  FCFS per key             |
  |-------------->|  holder = pid; now        |
  |               |  START{pid,key,type,now}  |--------------> every mirror
  |               |<==========================|==============> marks active
  |  (busy key) ERROR INTERACTION_BUSY{ref}   |
  |              <|  (denial + per-key        |
  |               |   backoff on the client)  |
  |  END{key}     |  release + cooldown_until |
  |-------------->|  FREE{key,cooldown_until} |--------------> every mirror
  |               |<==========================|==============> frees + cooldown
```

`INTERACTION_START`/`INTERACTION_FREE` are broadcast to the whole room
**including the sender** (echo-style), so one server broadcast both confirms
the request and informs every peer. Denied requests are explicit `ERROR`
replies carrying the object key in `ref`. A `INTERACTION_STATE` snapshot is
sent right after `WORLD_STATE`, so a late joiner sees every active interaction.
The reaper also expires interactions older than `interaction_max_duration`
(`Session.expire_interactions`, emitting `INTERACTION_FREE`). A disconnect does
**not** release immediately: the player becomes a ghost and their held
interactions stay reserved for `ghost_ownership_ttl`; the reaper's
`expire_ghosts` releases them (same `INTERACTION_FREE` broadcast) only once the
ghost is evicted, alongside the ghost's world ownership
(`OBJECT_OWNERSHIP` owner null). On a same-`client_id` resume inside the
window the `INTERACTION_STATE`/`WORLD_STATE` snapshots already carry the
reserved state, so the reconnect restores ownership without any extra traffic.

All messages are validated with `protocol/simmp/validation.py` before being
trusted on the server; anything invalid gets an `ERROR` reply and is discarded.

## Client mod architecture

- `simmp_client/networking/engine.py` — `ClientEngine`. Threaded socket
  engine (no asyncio — the game's embedded Python does not ship it; verified
  live). Runs its own background daemon thread that owns the blocking TCP
  socket and a `select`-driven read loop, so blocking socket I/O never freezes
  the game simulation. Inbound frames go into a thread-safe deque; the game
  thread calls `drain()`. Outbound messages are `sendall`ed under a lock.
  Heartbeats (PING) are sent from the read loop. The engine also owns the
  reliable-`EVENT` bookkeeping: it assigns a `seq` to every outgoing event,
  keeps un-acked events in a bounded pending buffer, pops them when
  `EVENT_ACK` arrives, and `reconnect()` re-runs `HELLO` + resends everything
  still pending. The engine thread survives disconnects (it loops back to a
  fresh connection when `reconnect()` is requested), so auto-reconnect works
  from `CONNECTED` and `DISCONNECTED` alike. The engine optionally carries a
  stable `client_id` in its `HELLO` so a reconnect resumes the same server-side
  identity. No `sims4` imports, so this module runs on a normal Python
  interpreter and is unit tested against the real server.
- `simmp_client/state/session.py` — `LocalSession` mirrors what the server
  tells the client (player id, room, room roster, per-player presence, server
  time offset). It also tracks the client's own travel state
  (`travel_state` = idle/invited/traveling/traveled + request id, target zone,
  requester) and the latest relayed `clock_sync` reference.
  `purge_stale_presence()` drops its mirrored presence entries older than
  `presence_ttl` (wall clock armed from the local arrival time per player).
  It also holds the `world` field — a `WorldMirror` of the current room's
  object catalog (see below) — reset whenever the room changes.
- `simmp_client/state/world.py` — `WorldMirror` is a pure client-side catalog
  of the room: `apply_full()` replaces it (`WORLD_STATE`), `apply_delta()`
  merges per-object fields and records a monotonic `seq` (deltas with
  `seq <= last_seq` or from another room are dropped), `apply_ownership()`
  updates an object's owner from the `OBJECT_OWNERSHIP` broadcast, and
  `get(key)`/`count()` expose it. Each `ObjectMirror` keeps its fields flat
  and can return a smoothed `display_position(now, rate)` that lerps between
  the anchored position and the latest target, so jittery world snapshots ease
  in rather than snapping. It is importable offline (no `sims4` imports).
- `simmp_client/state/interactions.py` — `InteractionMirror` is a pure
  client-side mirror of the room's active interactions:
  `apply_full()` (`INTERACTION_STATE`), `apply_start()`/`apply_free()`
  (broadcasts; out-of-room updates are ignored), plus `get(key)`,
  `count()`, and `cooldown_until(key)` surface bookkeeping.
  Importable offline (no `sims4` imports).
- `simmp_client/connectivity.py` — `MultiplayerClient` ties engine + local
  session together, pumps incoming messages (`process_incoming()`), emits
  `[MP][...]` log lines through a pluggable `notify` callback, and periodically
  sends presence sampled from the game via a pluggable sampler. The presence
  alarm also runs `session.purge_stale_presence()` so the mirror never shows
  ghosts. World: `claim_object(key)`/`release_object(key)`/`update_object(key,
  fields)` send the M4 messages, and `set_world_sampler(sampler)` plugs in a
  game hook returning `[{"key", "fields"}]`; a periodic tick pushes updates
  for objects the local mirror owns (`world_sync` on/off, `world_interval`
  seconds) and `world_summary()` feeds `mp.world`. Interactions:
  `propose_interaction(key, interaction, args)`/`end_interaction(key)` send the
  M5 messages, `set_interaction_sampler(sampler)` plugs in a game hook
  returning `[{"key", "interaction", optional "args"}]`, and a periodic tick
  (`interaction_sync` on/off, `interaction_interval` seconds) proposes sampled
  keys that are free and **not denied**, ends sampled interactions that are no
  longer reported, and skips keys the mirror says someone else owns. Denied
  keys (an `ERROR` with `ref` in `INTERACTION_BUSY`/`INTERACTION_COOLDOWN`) get
  a 10s backoff, cleared early by any `INTERACTION_START`/`INTERACTION_FREE`
  for the key. `interaction_summary()` feeds `mp.inter` / `mp.inter_list`.
  Reconnect: `reconnect()` first captures what the client owned/held
  (`_capture_dropped_state`, arrmed as `_reclaim_pending`) and then re-runs
  `HELLO` on the engine; `_maybe_reclaim()` runs once after the reconnect
  snaphot `INTERACTION_STATE` is applied and re-claims world keys that are not
  owned by anyone else and re-proposes interactions that are unheld, not
  denied, and past cooldown. The alarm's drop detection captures the same state
  when the engine silently loses the connection, so a full `connect()` after a
  drop performs the same reclaim.
  Travel: `request_travel()`/`respond_travel()`/`confirm_travel_ready()`/`send_clock_sync()`;
  travel invites are auto-accepted (`auto_accept_travel`, overridable per-request
  via `travel_controller`); a `travel_controller(request_id, zone_id)` may
  return `True`/`False` (decide now) or `None` (defer — it opened a dialog and
  will call `respond_travel()` from a callback; the server's 15s invite timeout
  aborts if unanswered). On `TRAVEL_BEGIN` it triggers the game travel hook
  and a repeating alarm poller reports READY once the game reports the target
  zone running. It generates one stable `client_id` (`uuid4().hex`) per client
  and threads it through every `ClientEngine` it creates, so reconnects keep
  the same identity. Auto-reconnect: `auto_reconnect` (default on) plus
  `reconnect_backoff_min`/`reconnect_backoff_max`; `_on_alarm` runs
  `_maybe_auto_reconnect()` after each tick, which calls the fail-safe engine
  `reconnect()` (async, engine thread - the game thread never blocks) when the
  connection is down, doubling the delay per failed attempt (capped at the max)
  and resetting the counter once connected. `engine.reconnect()` itself now also
  works from `DISCONNECTED` (the previous connection died but the engine
  loop/thread survive), so drops self-heal even after a server restart; a
  `mp.disconnect()` cancels the retry schedule.
- `simmp_client/ui.py` — offline-safe in-game UI shims (M6). `available()`,
  `show_notification(text, title)`, and `show_travel_invite(request_id, zone_id,
  requester_name, on_decision)` use the game's dialog service
  (`services.get_ui_dialog_service(0)` + `ui.ui_dialog.UiDialogNotification` /
  `UiDialogOkCancel`) with lazy, guarded imports: outside the game (or in the
  main menu) `available()` is False and the show functions return False. The
  invitation dialog's response callback fires `on_decision(request_id,
  accepted)` on the game thread (never the engine thread). `GameUI` wraps the
  console with `note(line)` (always to console) and `toast()`/`travel_invite()`
  (no-ops unless `enabled` and the dialog service is reachable).
- `simmp_client/config.py` — pure-Python loader for `Sims4Multiplayer.json`
  (host, port, name, auto_connect, presence_interval, presence_ttl,
  auto_accept_travel, world_sync, world_interval, interaction_sync,
  interaction_interval, sync_funds, funds_interval, build_sync, ui_dialogs,
  auto_reconnect, reconnect_backoff_min, reconnect_backoff_max). Also used at
  game startup for auto-connect.
- `simmp_client/presence.py` — pure helpers to build/format presence payloads.
- `simmp_client/hooks/game_hooks.py` — alarm helpers + the game-only zone
  sampler, travel trigger, clock sampler, world sampler, funds sampler, and
  interaction sampler. Imports game modules lazily so the module is importable
  outside the game. `sample_world_objects()`, `sample_lot_objects()`, and
  `sample_interactions()` currently return `[]`: the actual game-side
  sim/object scans are deliberately left as best-effort hooks to be filled
  once verified in-game (object key identity across sessions is the open
  question; lot objects use `obj:<def>@<grid>` keys for that reason).
- `simmp_client/commands/cheat_commands.py` + `sims4_plugin.py` — game-only
  integration. Registered only when `sims4` is importable. On load, if the
  config enables `auto_connect`, a one-shot alarm connects shortly after
  startup and applies `auto_accept_travel`, `world_sync`, `world_interval`,
  `interaction_sync`, `interaction_interval`, `sync_funds`, `funds_interval`,
  `build_sync`, and `ui_dialogs` from the config.
  The console notifier doubles as the `GameUI` console; `[MP][ERROR]` lines are
  additionally toasted as an in-game notification when `ui_dialogs` is on. The
  travel controller opens the `UiDialogOkCancel` invite (via `ui.py`) when
  `ui_dialogs` is enabled and the dialog service is reachable, else falls back
  to `auto_accept_travel`; declining triggers the abort. New commands:
  `mp.claim`, `mp.release`, `mp.obj` (push a one-shot world update),
  `mp.world` (dump the mirror), `mp.inter` (propose an interaction),
  `mp.inter_end` (end an interaction), `mp.inter_list` (dump the interaction
  mirror), `mp.ui on|off` (toggle in-game dialogs), `mp.ui_test [text]`
  (show a test toast in-game).
- `simmp_client/__init__.py` — safe import guard; keeps the package usable
  for offline tests.

### Threading model

```
game thread (sim1)              engine thread (daemon)
mp.connect ─► engine.connect ─► socket.create_connection + HELLO
      │                              │ select()-driven read loop
      │                              │ heartbeat timer (PING)
      │                              │ A: seq 1..n + pending buffer
      │                              │ S: listen for EVENT_ACK
      │◄────── drain() ◄─────────────┘ inbound frames deque
      │  process_incoming()          │
      │  presence sampler + purge    │
mp.test ─► send_message() ──────────► sendall EVENT frame (seq, ack later)
      │                              │
mp.travel ─► send_travel_request() ─► TRAVEL_REQUEST
      │              alarm poller ◄─► game zone + clock hooks (travel/ready)
mp.clock ─► send_clock_sync() ──────► CLOCK_SYNC beacon
mp.claim ─► claim_object() ─────────► OBJECT_CLAIM
mp.obj ───► update_object() ────────► OBJECT_UPDATE (one-shot)
      │              world alarm ◄──► sample_world_objects() ─► owned deltas
      │                              (WORLD_STATE/DELTA feed the mirror)
mp.inter ──► propose_interaction() ─► INTERACTION_REQUEST
mp.inter_end ─► end_interaction() ──► INTERACTION_END
      │        interaction alarm ◄──► sample_interactions() ─► propose/end
      │                              (INTERACTION_STATE/START/FREE mirror)
mp.reconnect ◄───────────── engine.reconnect() ──► HELLO + resend pending
      │                        ── captures owned/held state first (ghost
      │                           resume on server; client reclaim fallback)
      │        [MP][ERROR] ──► GameUI.toast()        (ui_dialogs on)
      │        travel invite ──► travel_controller ─► GameUI.travel_invite()
      │                              (dialog) ─► respond_travel from callback
mp.ui ───► toggle GameUI.enabled      mp.ui_test ──► GameUI.toast()
mp.auto_reconnect ─► toggle auto-reconnect/backoff
      │        alarm tick ─► _maybe_auto_reconnect() ─► engine.reconnect()
      │              (async reconnect on the engine thread, backoff per
      │               failed attempt; the game thread never blocks)
```

The game thread never touches sockets; the engine thread never touches the
game. Shared state is the message deque plus a few thread-safe fields
(pending buffer is only mutated from the engine thread after enqueue).

## Protocol package

See `docs/protocol.md` for the wire format and message catalogue. The framing
(length-prefixed JSON) is isolated in `framing.py` so a binary codec can be
introduced later without touching the rest of the project.

## Logging

- Server: `logging` with the `simmp.server` logger. Console format
  `[MP][%(levelname)s] %(message)s` plus optional `--log-file`.
- Client (in game): console output through `sims4.commands.output`, prefixed
  `[MP][NET]`, `[MP][ROOM]`, `[MP][SYNC]`, `[MP][TRAVEL]`, `[MP][ERROR]`.
- Client (offline tests): stdlib logging via the engine logger.

## Directory layout

```
client_mod/         Sims 4 script mod (packaged to .ts4script)
protocol/simmp/     shared protocol package (canonical; copied into the mod)
server/             standalone multiplayer server
tests/              unittest suite (stdlib only, no third-party deps)
docs/               architecture, protocol, milestones, research, testing
```

## Running the server

    python server/main.py                  # 127.0.0.1:8765
    python server/main.py --host 0.0.0.0 --port 9000   # LAN
    python server/main.py --log-file server.log
## Deep host-authoritative layer (M19+)

Alongside the existing JSON session protocol, Motanplayer now has a **deep**
path modeled on host-authoritative Sims multiplayer:

- **Host** runs the live Sims simulation (Timeline.simulate stays on).
- **Joiners** disable local Timeline.simulate and relay pie-menu /
  interaction commands to the host as Motanplayer protobuf WrapperMessage
  blobs inside DEEP_RELAY frames.
- The host rebuilds ChoiceMenu / pushes affordances and fans native EA
  distributor / UI messages back as GameNetworkMessage (opaque
  msg_id + bytes), which joiners inject with omega.send.
- Injection uses simmp_client.deep.Override (role-aware monkey-patches)
  and MessageHandler dispatch. Protocol builders live in
  protocol/simmp/deep/ (dependency-free proto3 codec).
- Room host is claimed via HELLO.want_host / SESSION_ROLE and advertised
  with DEEP_HOST + ROOM_STATE.host_player_id.

Config: "deep_hooks": true, "want_host": true (first claimant becomes host).

The lighter poll-and-apply world/interaction sync remains for compatibility
while the deep surface expands (clock, live drag, build-buy, situations, …).
