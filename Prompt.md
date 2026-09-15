I want you to help me build a completely independent multiplayer mod for The Sims 4 from scratch.

## Goal

Build a multiplayer framework that allows multiple players to run The Sims 4 on their own PCs and share the same game session/world.

The long-term goal is something comparable to a proper Sims 4 multiplayer experience:

- 2+ players
- Each player controls their own Sims
- Players see each other's Sims and relevant game-state changes
- Shared game time
- Synchronised interactions
- Synchronised objects/world state where practical
- Players can travel together between lots
- Players can enter different lots/worlds and remain synchronised
- Save/load multiplayer state
- Reconnect handling
- Host/client or dedicated-server architecture
- LAN first, internet multiplayer later
- No Patreon dependency
- No dependency on S4MP or SimSync at runtime

This is an independent project. Do NOT attempt to bypass, crack, unlock, or copy paid S4MP/SimSync functionality. We can study publicly available Sims 4 modding documentation and legitimately available open-source projects for technical concepts, but do not copy proprietary code or circumvent access controls/licenses.

## Important technical constraint

The Sims 4 gameplay modding environment is primarily Python + tuning/XML.

Therefore:

### Sims 4 client mod
Use Python for the actual Sims 4 mod.

The client-side mod should:
- hook into the Sims 4 simulation where possible
- observe relevant game events
- serialize relevant state
- communicate with our multiplayer server
- receive state/events from the server
- apply remote-player state to the local game
- coordinate travel/loading
- avoid modifying the game executable unless absolutely necessary

### Multiplayer server
Initially implement the server in Python so we can iterate quickly.

Use:
- asyncio
- a clean networking abstraction
- structured messages
- JSON initially for debugging
- versioned protocol
- authoritative session state

Later, if there is a real reason for it, we can port the server to C++ or Rust.

Do NOT prematurely optimize.

## Architecture

Use a client/server architecture.

Example:

Sims 4 Client A
    |
    | multiplayer protocol
    v
Multiplayer Server
    ^
    | multiplayer protocol
    |
Sims 4 Client B

The server should initially be authoritative for:
- connected players
- rooms/sessions
- player identities
- game clock
- player-controlled Sims
- important replicated events
- travel coordination
- connection/reconnection state

The server should NOT attempt to simulate the entire Sims 4 game itself.

The Sims 4 clients remain responsible for the actual simulation.

## Development philosophy

Do not try to implement everything at once.

Build a sequence of small, testable milestones.

Before implementing a feature:

1. Inspect the existing project.
2. Determine what Sims 4 APIs/hooks are actually available.
3. Research the relevant Sims 4 modding interfaces if necessary.
4. Explain the approach briefly.
5. Implement the smallest working version.
6. Add logging.
7. Add a test or reproducible manual test.
8. Verify it works before moving to the next milestone.

Do not invent Sims 4 APIs.

If you are unsure whether an API/class/function exists, search the project, documentation, or installed game/modding resources before using it.

## First milestone

Do NOT start with travel.

First create a minimal end-to-end multiplayer proof of concept.

The first milestone should be:

### M1 — Client/server connection

Create:

/server
/client_mod
/protocol
/docs
/tests

The server should:

- start locally
- listen on localhost
- accept multiple clients
- assign each connection a player ID
- maintain connected-player state
- support a simple room/session
- log connections/disconnections
- send a welcome message
- support ping/pong
- broadcast a test event from one client to the others

The Sims 4 client mod should:

- load correctly as a script mod
- initialize the multiplayer subsystem
- connect to localhost
- identify itself
- receive the assigned player ID
- send heartbeat/ping messages
- log connection status
- receive server events
- expose a simple test command/interaction that sends a test multiplayer event

For the first test, I want something extremely simple such as:

Player A triggers:
    TEST_EVENT "hello"

Server receives it and broadcasts it.

Player B receives:
    TEST_EVENT "hello"

Nothing more complicated is necessary for M1.

## Protocol

Design a small versioned protocol.

For example:

{
    "version": 1,
    "type": "HELLO",
    "request_id": "...",
    "payload": {}
}

Possible initial message types:

HELLO
WELCOME
PING
PONG
JOIN_ROOM
ROOM_STATE
PLAYER_JOINED
PLAYER_LEFT
EVENT
ERROR

Keep protocol code isolated so it can later be replaced with a binary protocol without rewriting the entire project.

Every message should be validated.

Never blindly trust client input.

## Project structure

Use a clean structure similar to:

project/
├── client_mod/
│   ├── scripts/
│   ├── multiplayer/
│   ├── hooks/
│   ├── state/
│   ├── networking/
│   └── commands/
│
├── server/
│   ├── networking/
│   ├── rooms/
│   ├── state/
│   ├── protocol/
│   └── main.py
│
├── protocol/
│   └── protocol documentation/schema
│
├── tests/
│
└── docs/
    ├── architecture.md
    ├── protocol.md
    ├── milestones.md
    └── sims4-research.md

Adapt this structure if you find a better one.

## Future milestones

After M1 works, proceed roughly in this order:

M2 — Player/session system
- rooms
- player IDs
- player names
- ownership
- reconnect handling

M3 — Game clock synchronization
- detect game time
- pause/unpause
- game speed
- synchronize time
- prevent obvious desync

M4 — Sim identification
- identify active Sims
- stable Sim identifiers
- determine which Sims belong to which player
- synchronize basic Sim metadata

M5 — Sim state replication
Start with only important state:
- Sim position
- current lot/zone
- current interaction
- basic animation/interaction state
- mood
- needs where practical

Do not attempt to synchronize every internal Sims 4 variable.

M6 — Interaction synchronization
Determine which interactions need replication.

For example:

Player A:
    Sim A starts interaction X with object Y

Server:
    validates/broadcasts event

Player B:
    sees/applies corresponding state

M7 — Object/world synchronization
- object creation/deletion where possible
- object state changes
- ownership where necessary
- avoid attempting to replicate the entire world every frame

Use event/state-delta synchronization rather than constantly sending the entire world state.

M8 — Travel

This is a major feature.

Research how Sims 4 travel actually works before implementing it.

Desired flow:

Player A requests travel
        ↓
Server receives travel request
        ↓
Server coordinates all affected players
        ↓
Clients prepare/save required state
        ↓
Travel begins
        ↓
Clients load destination zone
        ↓
Clients report READY
        ↓
Server waits for required clients
        ↓
Simulation resumes

Handle:
- different loading times
- player disconnect during travel
- one player refusing/canceling travel
- household travel
- world travel
- lot travel
- travel failures
- loading screens
- zone IDs
- returning to the previous lot

M9 — Save synchronization
- multiplayer save ownership
- synchronization
- recovery
- versioning
- backups

M10 — Internet multiplayer
Only after LAN works reliably.

Add:
- authentication
- room codes
- NAT considerations
- secure connections
- server deployment
- reconnect
- latency handling

## Networking philosophy

Do NOT synchronize every frame.

Prefer:

event-based synchronization
+
periodic authoritative snapshots
+
client-side interpolation/reconciliation where necessary.

The Sims 4 simulation is complex, so determine what genuinely needs replication instead of attempting to mirror every internal variable.

## Logging

Create useful logs on both client and server.

Example:

[MP][NET] Connected
[MP][NET] Player ID: 1234
[MP][ROOM] Joined room ABC123
[MP][SYNC] Received EVENT
[MP][TRAVEL] Travel requested
[MP][TRAVEL] Waiting for player 2
[MP][ERROR] Connection lost

Logs should make debugging desynchronization possible.

## Safety / compatibility

Do not modify game files unnecessarily.

Do not require executable patching unless there is no viable supported/modding approach.

Keep the project modular so Sims 4 updates do not require rewriting the entire networking layer.

Separate:

Sims 4 integration
from
networking
from
server logic
from
protocol.

## Research

Before implementing Sims 4-specific hooks, investigate legitimate publicly available resources such as:

- Sims 4 Community Library
- Sims 4 Python modding documentation
- Sims 4 tuning/XML systems
- publicly available Sims 4 multiplayer research
- legitimately open-source Sims 4 multiplayer projects

If using existing open-source code, inspect its license first and respect it.

Do not assume an old Sims 4 multiplayer project is compatible with the current game.

## What I expect from you

Act as the lead developer for this project.

Do not just give me a huge theoretical explanation.

Actually create the project files and implementation in the current workspace.

Start by:

1. Inspecting the current workspace.
2. Checking whether a project already exists.
3. Creating the initial architecture.
4. Implementing M1.
5. Creating the server.
6. Creating the Sims 4 script-mod skeleton.
7. Creating the protocol.
8. Creating tests for the server/protocol.
9. Creating documentation explaining how to install the client mod and start the server.
10. Running the tests.
11. Fixing any errors you encounter.

At the end, report:

- files created
- files modified
- what currently works
- what does not work yet
- how I can test M1 with two Sims 4 clients
- the next milestone you recommend

IMPORTANT:

Do not jump directly to implementing travel or full synchronization.

Get the smallest client → server → client communication working first.

If you encounter a Sims 4-specific limitation, investigate it and explain the limitation rather than inventing an API or pretending something works.

Build this incrementally and keep the code maintainable.