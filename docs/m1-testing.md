# Testing

Covers M1/M2/M3 verification, from unit tests to a live two-machine-style
smoke test.

## Automated suite

No third-party dependencies. Both runners are equivalent:

```bash
python tests/run_tests.py      # stdlib unittest discovery + summary
python -m pytest -q            # if pytest is installed
```

The `conftest.py` at the repo root puts `protocol/`, `client_mod/scripts/`,
and the repo root on `sys.path` for pytest. `tests/run_tests.py` does the
same itself.

### What is covered

| File | Coverage |
|------|----------|
| `tests/test_framing.py` | 4-byte length header, encode/decode round trip, empty/oversized frames fail, garbage bytes rejected |
| `tests/test_validation.py` | envelope shape, unknown type / version, required/unknown fields, type checks (int/float/str), string length caps, special ROOM_STATE/HELLO checks, TRAVEL_* + CLOCK_SYNC field rules (bool `accepted`, int ticks/speed, string length caps), all 18 builder messages validate |
| `tests/test_protocol.py` | every builder produces a message that passes `validate_message`, error codes `MALFORMED`/`UNKNOWN_TYPE`/`INCOMPATIBLE_VERSION` raised correctly |
| `tests/test_server.py` | in-process `MPServer` on an ephemeral port: hello->welcome, room state, PING->PONG, JOIN_ROOM broadcast of PLAYER_JOINED/PLAYER_LEFT, TEST EVENT broadcast to room members and not to outside members, malformed message -> ERROR reply, `client_id` identity resume (same player_id/room, dedup survives reconnect, fresh events still relay), `client_id` takeover closes the stale connection |
| `tests/test_client_engine.py` | `ClientEngine` against the real in-process server: connect/hello/welcome, heartbeat PING emission, inbound queue drains, test event round trip, EVENT seq/pending/ACK flow, presence mirroring, reconnect keeps identity + resends pending, disconnect sanity |
| `tests/test_config.py` | config loader: defaults, round-trip, type/range validation, unknown keys, env/explicit discovery |
| `tests/test_presence.py` | presence payload helpers + game-hook no-ops outside the game |
| `tests/test_travel.py` | in-process server travel coordinator: invite->accept->BEGIN->READY->COMPLETE, solo immediate BEGIN, decline abort (reason propagated), invite/ready watchdog timeouts, member-disconnect abort, wrong-zone READY abort, unregistered TRAVEL_REQUEST rejected, CLOCK_SYNC relay with stamped origin |
| `tests/test_travel_client.py` | two `MultiplayerClient`s against a real in-process server: request -> invite -> auto-accept -> BEGIN -> manual `confirm_travel_ready` -> COMPLETE, decline path with `auto_accept_travel=False`, CLOCK_SYNC mirrored into the local session |

Requirement for every networking test: the server and client run in separate
event loops or separate threads so both the server authoritiveness and the
client's threaded model are exercised for real.

## Live smoke tests

These are the manual checks used at the end of M1 (not part of the suite):

### 1. Server CLI + real client

```bash
# terminal 1
python server/main.py --host 127.0.0.1 --port 8765
# expected on startup:
#   [MP][INFO] [MP][NET] Listening on 127.0.0.1:8765

# terminal 2
python tests/smoke/smoke_client.py --port 8765 --name Alice
# expected:
#   WELCOME player_id: 1000 room: lobby

# terminal 3 (same identity as terminal 2 -> resume, same player_id)
python tests/smoke/smoke_client.py --port 8765 --name Alice --client-id ALICE-1
#   WELCOME player_id: 1000 room: lobby   (server kept the identity
#   even though terminal 2 already disconnected)
```

> Note: the console handler writes to **stdout** (`StreamHandler(sys.stdout)`).
> If you force-kill the server process the OS pipe buffer may be lost - stop
> it with Ctrl+C or use `--log-file server.log` for persistent capture.

### 2. Two-room broadcast check

Connect two clients with different `name`s, then with one of them send a
test event (game: `mp.test hello`; CLI: `--event hello`). The *other*
client's console shows the relayed event; the sender sees `EVENT_ACK`.

Presence: run one client with `--presence 7/12`. The other client in the
same room sees the `PRESENCE` message with its zone/lot and the sender's
server-stamped `player_id` (verified live in M2).

### 3. Travel flow (M3 smoke)

Terminal 2 (`Bob`) connects first and waits; terminal 3 (`Alice`) then
requests the group travel:

```bash
# terminal 1: server
python server/main.py --port 8765

# terminal 2
python tests/smoke/smoke_client.py --port 8765 --name Bob --autoaccept --travel-ready --timeout 8

# terminal 3
python tests/smoke/smoke_client.py --port 8765 --name Alice --travel 4242 --travel-ready --clock 4242/100000/2998527000/1 --timeout 8
```

Expected on the server log:

```
Player <Alice> requests travel to zone 4242 (room lobby, 1 invited)
Player 1000 accepted travel to zone 4242
Travel ... to zone 4242 begins
Player 1000 ready in zone 4242 (1/2)
Player 1001 ready in zone 4242 (2/2)
Travel ... to zone 4242 complete
```

Bob sees `TRAVEL_INVITE` (auto-accepted), `CLOCK_SYNC` (Alice's beacon relay),
`TRAVEL_BEGIN`, `TRAVEL_COMPLETE`, and the replayed clock reference. Alice sees
TRAVEL_BEGIN/COMPLETE but **no** echo of her own clock beacon (excluded from
the replay). Decline/member-disconnect paths were verified in the automated
suite (watchdogs + abort reasons).

### 4. Identity resume + takeover

Run `--client-id` clients as documented in M2; verified live in M2.5.

## In-game verification (manual)

1. Build or dev-install the mod (see README). Optionally drop a
   `Sims4Multiplayer.json` config in the Mods folder (`auto_connect` on to
   connect automatically at startup).
2. Start the server on the host machine (`--host 0.0.0.0` if the game is on
   another PC).
3. In-game: open console (Ctrl+Shift+C), run:
   - `mp.connect <host> <port> <name>` -> console shows `WELCOME`, room join
   - `mp.status` -> prints player id, room, roster, presence, heartbeat,
     pending-event state
   - `mp.who` -> roster plus per-player zone/lot presence
   - `mp.autoconnect [config]` -> reads your config file and connects
   - `mp.test hello` from client A -> client B in the same room shows
     `[MP][EVENT] ... seq=..`; client A sees the ack (its pending count
     returns to 0)
- `mp.join myroom` -> both clients still see the shared roster; messages
      and presence only flow within the new room
   - `mp.travel 4242` -> everyone in the room gets the invite; with default
      `auto_accept_travel`, `TRAVEL_BEGIN` follows and each client triggers
      the in-game travel hook (`send_travel_switch_to_zone_op`) and reports
      READY once the target zone is running
   - `mp.travel_ready` -> manual fallback that reports arrival when the game
      boundary hooks are unavailable (the client says so with a hint log)
   - `mp.travel_autoaccept off` -> next invites are declined (server logs
      `aborted: declined by <name>`) - `on` restores auto-accept
   - `mp.clock` -> emits a `CLOCK_SYNC` beacon; peers see the relayed clock
      with the sender's player_id; after a completed travel the initiator's
      stored beacon is replayed to the room
   - `mp.disconnect` -> server logs the disconnect, clients in the room get
      the updated roster
4. Kill one game window: the remaining client(s) see `PLAYER_LEFT`/
   updated `ROOM_STATE` after the connection drop is detected.

## Known M3 caveats and assumptions

- Travel is **best-effort in-game**: `travel_to_zone()` requires an active
  `SimInfo` and the `send_travel_switch_to_zone_op` API; if unavailable the
  client logs a hint and you confirm arrival with `mp.travel_ready`. The
  automated and CLI-smoke tests exercise the protocol flow but cannot run the
  actual game here.
- A room member who joins *during* an active travel is not waited on (members
  are frozen at request start) but still receives the outcome broadcasts.
- The `CLOCK_SYNC` replay after COMPLETE only happens when the initiator had a
  stored beacon (e.g. ran `mp.clock`); it excludes the initiator.
- Travel watchdog defaults (invite 15s, ready 30s) are server-side and
  injectable at construction (`TravelCoordinator(server, invite_timeout=...,
  ready_timeout=...)`), which the tests rely on for fast timeout coverage.

## Known M1/M2 caveats

- Alarms in the mod use a fallback call signature because `use_sleep_time` /
  `cross_zone` may not exist on old patches; behavior was chosen to never
  throw in-game.
- The zone sampler is best-effort: if `services.get_zone()` isn't available
  (or fails), no presence is sent; the sampler never throws.
- Reconnects now use a stable `client_id` (HELLO): the server keeps the
  identity mapping, so a returning client reuses its `player_id`, room, and
  `last_event_seq`. Resends of already-relayed events are deduped across
  sessions; a reconnect racing the old socket is handled by a server takeover
  that closes the stale connection. A client that never sends `client_id`
  still joins fresh each session (old behavior).
- `process_incoming()` is only auto-invoked by an alarm (while connected)
  plus the `mp.*` commands; the M2 console/status output is the working
  in-game UI until a real toast/dialog asset is added.