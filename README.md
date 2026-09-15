# Sims 4 Multiplayer Mod (M15)

An independent, client/server multiplayer layer for **The Sims 4**. The mod
runs inside each game instance; a standalone Python server coordinates the
session. The whole transport is our own design - no dependency on S4MP,
SimSync, or any non-stdlib Python package.

> M1 = foundations: connect/disconnect, heartbeat (PING/PONG), rooms
> (lobby + custom), TEST EVENT broadcast, strict validation, packaging,
> and a full test suite.
> M2 = presence + reliability: config file with auto-connect, per-player
> zone/lot presence (`PRESENCE`), per-event sequence numbers with `EVENT_ACK`
> and resend-on-reconnect, plus a stable `client_id` so reconnects keep the
> same `player_id`/room and dedup state. Wire protocol is v2 (superseded).
> M3 = travel + clock sync: group-travel handshake (`TRAVEL_*` messages)
> with an all-or-nothing accept/begin/ready/complete flow, timeout and
> disconnect aborts, in-game travel hook + manual fallback, `CLOCK_SYNC`
> relay after travel completes, `auto_accept_travel` config option, and
> expanded console commands (`mp.travel`, `mp.travel_ready`, `mp.clock`).
> M4 = world-state replication: a server-authoritative per-room object
> catalog with claim/release authority, delta-encoded `OBJECT_UPDATE` →
> `WORLD_DELTA` relay (monotonic per-room seq), `WORLD_STATE` snapshots on
> join, a client `WorldMirror` with smoothed positions, and world commands
> (`mp.claim`, `mp.release`, `mp.obj`, `mp.world`). Wire protocol is v3.
> The game-side object sampler (`sample_world_objects`) is a best-effort
> hook still returning `[]` until object identity is confirmed in-game.
> M5 = interaction sync & conflict resolution: a server-authoritative
> per-room interaction store (first-come, first-served per object), echo-style
> `INTERACTION_START`/`INTERACTION_FREE` broadcasts and `INTERACTION_STATE`
> snapshots (v4), release cooldown, lock protection with an auto-release
> watchdog plus disconnect cleanup, a client `InteractionMirror` with a
> pluggable interaction sampler and denial backoff, and commands (`mp.inter`,
> `mp.inter_end`, `mp.inter_list`). Wire protocol is v4.
> M6 = in-game UI + reconnect hardening: an offline-safe UI layer
> (`simmp_client/ui.py`) with in-game toasts for errors (via
> `services.get_ui_dialog_service`) and a travel-invite accept/decline dialog
> (falling back to console/auto-accept), configurable with `ui_dialogs` and
> `mp.ui on|off` / `mp.ui_test`; plus "ghost" reconnect semantics where a
> disconnected player's world ownership and held interactions stay reserved
> for `ghost_ownership_ttl` and are restored on a same-`client_id` reconnect,
> evicted by the reaper afterwards, with the client re-claiming anything the
> server lost. Frame-size pressure tests and server resilience hardening.
> Auto-reconnect fills the gap: after a drop the client reconnects on its own
> with exponential backoff (`auto_reconnect` / `reconnect_backoff_min` /
> `reconnect_backoff_max`, `mp.auto_reconnect on|off`), restoring ownership
> via the ghost scheme or the reclaim fallback, never blocking the game
> thread.
> M7-M12 = live sim replication: household-wide world/interaction samplers
> with auto-claim (`sim:<id>` keys), receive-side movement + interaction
> execution on the mirrored sim, save-file sync (`mp.save_push`),
> shared-time clock gate (`mp.pause`/`mp.resume`/`mp.speed`), and the dev
> console GUI. See `docs/milestones.md`.
> M13 = split-zone worlds: the object catalog, ownership, interactions and
> world-delta sequence are partitioned per (room, zone) so players in
> different zones never share or smear each other's world; traveling auto-
> releases the departed players holdings in the old zone and resyncs the new
> one. Protocol stays v4 (`zone_id` is an optional field on the world/claim/
> interaction messages).
> M14 = autonomy suppression: sims owned by another player stop running
> local autonomy (so a peer-driven sim is not jostled between sync ticks),
> reconciled on every world/ownership change and toggleable at runtime with
> `mp.autonomy on|off` / `autonomy_suppression` config (default on).
> M15 = launcher + lobby + one-file .exe: `tools/launcher.py` auto-detects
> the game install/Mods/saves folders on each PC, installs the mod, and runs
> a host/join lobby (embedded server, save share -> save sync -> Start game
> that launches the game already configured to auto-connect). `tools/build_app.py`
> packages it into a single windowed .exe with PyInstaller. See
> `docs/milestones.md`.

## Layout

```
protocol/simmp/   shared wire protocol (canonical copy)
server/           standalone asyncio multiplayer server
client_mod/       Sims 4 script mod (the in-game client)
tools/            launcher GUI, lobby, game-path detection, build script, dev console
tests/            stdlib unittest suite
docs/             architecture, protocol, milestones, research, testing
```

## Quick start (server only, no game)

```bash
# 1. run the server
python server/main.py --host 127.0.0.1 --port 8765

# 2. in another terminal, run a simulated client
python tests/smoke/smoke_client.py --port 8765 --name Alice
# -> WELCOME player_id: 1000 room: lobby

# presence and event relay between two clients (two terminals)
python tests/smoke/smoke_client.py --port 8765 --name Alice --presence 7/12
python tests/smoke/smoke_client.py --port 8765 --name Bob   --event hello

# reconnect with the same --client-id resumes the same player_id
python tests/smoke/smoke_client.py --port 8765 --name Alice --client-id ALICE-1

# travel flow (Alice requests travel to zone 4242; Bob auto-accepts)
python tests/smoke/smoke_client.py --port 8765 --name Bob --autoaccept --travel-ready --timeout 8
python tests/smoke/smoke_client.py --port 8765 --name Alice --travel 4242 --travel-ready --clock 4242/100000/2998527000/1 --timeout 8

# world replication: claim an object and pump position deltas
python tests/smoke/smoke_client.py --port 8765 --name Alice --world sofa
# (second terminal) Bob sees the OBJECT_OWNERSHIP + periodic OBJECT_UPDATE
python tests/smoke/smoke_client.py --port 8765 --name Bob

# interaction sync: propose an interaction and end it after 3s
python tests/smoke/smoke_client.py --port 8765 --name Alice --interact sofa/Read --interact-end
# (second terminal) Bob sees INTERACTION_START then INTERACTION_FREE
python tests/smoke/smoke_client.py --port 8765 --name Bob
```

## In the game

Requirements: The Sims 4 with **Script Mods** enabled, plus a separate
Python (3.8+) for the server.

1. Build the mod:

   ```bash
   python client_mod/build_script_mod.py package
   # -> client_mod/build/Sims4Multiplayer.ts4script
   ```

   Copy that file into your `Documents/Electronic Arts/The Sims 4/Mods/`
   folder. (For iteration, `python client_mod/build_script_mod.py dev <Mods folder>`
   installs loose files under `Mods/Sims4Multiplayer/Scripts/` instead.)

2. (Optional) Auto-connect via config. Put `Sims4Multiplayer.json` in the
   Mods folder (or set `SIM4_MP_CONFIG` to its path):

   ```json
   {
     "host": "192.168.1.20",
     "port": 8765,
     "name": "Alice",
     "auto_connect": true,
     "presence_interval": 5.0,
     "presence_ttl": 30.0,
     "auto_accept_travel": true,
     "world_sync": true,
     "world_interval": 5.0,
     "interaction_sync": true,
     "interaction_interval": 5.0,
     "ui_dialogs": true,
     "auto_reconnect": true,
     "reconnect_backoff_min": 2.0,
     "reconnect_backoff_max": 30.0
   }
   ```

   With `auto_connect: true` the mod connects on its own shortly after the
   game starts. `mp.autoconnect` reads the same file on demand.

3. Start the server on the host machine.

4. In-game (to host or join), open the console with Ctrl+Shift+C:

   ```
   mp.connect 192.168.1.20 8765 Alice
   mp.autoconnect                 # read Sims4Multiplayer.json and connect
   mp.who                         # roster + zone/lot presence
   mp.join partyroom
   mp.test hello                  # relayed to everyone else in the room
   mp.travel 4242                 # invite the room to travel to a zone
   mp.travel_ready                # manual "I arrived" (fallback for the hook)
   mp.travel_autoaccept off       # refuse (or re-enable with on) travel invites
   mp.clock                       # send a CLOCK_SYNC beacon + show local clock
   mp.claim sofa                  # claim authority over the object "sofa"
   mp.release sofa                # give it up again
   mp.obj sofa x 1.5              # push x=1.5 for an object you own
   mp.world                       # list the mirrored world catalog
   mp.inter sofa/Read             # propose an interaction on "sofa" (Read)
   mp.inter sofa/Read book xx     # ... with extra args
   mp.inter_end sofa              # end an interaction you hold
   mp.inter_list                  # list the interaction mirror
   mp.ui off                      # disable in-game dialogs/toasts (default on)
   mp.ui_test hello               # show a test toast in-game
   mp.auto_reconnect off          # stop auto-reconnecting after a drop
   mp.status                      # detailed internal state (pending, travel, etc.)
   mp.process                     # manually drain pending messages
   mp.disconnect
   ```

Commands are cheat-type; if they don't run, make sure Script Mods are on and
the game was restarted after installing the mod.

## Tests

```bash
python tests/run_tests.py      # 266 tests, stdlib only
python -m pytest -q            # optional
```

See `docs/m1-testing.md` for the full matrix and live smoke steps.

## Launcher (give it to another PC)

```bash
python tools/launcher.py       # GUI: host or join a lobby
python tools/build_app.py      # build dist/Sims4MultiplayerLauncher.exe (PyInstaller)
```

The launcher auto-detects (or lets you browse to) the game, Mods and saves
folders, installs the mod, runs an embedded lobby server, shares the chosen
save to joiners, and starts both games already set to auto-connect. Packaged
as a .exe the other PC needs nothing installed. Host IP is a dropdown of all
local adapters, so LAN VPNs (Radmin VPN, Hamachi, Tailscale) work: the host
picks its VPN IP and the joiner enters that address.

## Documentation

- `docs/architecture.md` - layering, threading model, message flow
- `docs/protocol.md` - wire format (v4), message catalogue, reliability
- `docs/milestones.md` - roadmap (M1-M15 done)
- `docs/sims4-research.md` - confirmed public modding facts (packaging, alarms, commands, UI)
- `docs/m1-testing.md` - unit + live verification

## Legal

Built from public modding documentation only; no code or assets from
S4MP/SimSync are used. The Sims 4 game files/EULA apply to running the mod
in-game; this repository contains only independent Python code.