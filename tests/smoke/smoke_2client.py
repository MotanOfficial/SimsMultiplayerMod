"""Live 2-client same-zone smoke against the real server binary.

Boots ``server/main.py`` on a free port, drives two clients (Alice + Bob)
through the full same-zone multiplayer scenario: connect, ready, claim,
world sync, interaction mirror with targeting, clock gate, and zone flip.
Verifies the server-side paths that a real two-game LAN session exercises.

Usage:
    python tests/smoke/smoke_2client.py
"""

import argparse
import asyncio
import os
import socket
import subprocess
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _entry in (_ROOT, os.path.join(_ROOT, "protocol")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from simmp import framing, messages as msg  # noqa: E402

ZONE_A = 100
ZONE_B = 200


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class Client:
    """Minimal raw-frame client with per-type inbox."""

    def __init__(self, name, port):
        self.name = name
        self.port = port
        self.inbox = []
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection("127.0.0.1", self.port)
        await self.send(msg.make_hello(self.name, "smoke-2client"))

    async def send(self, message):
        self.writer.write(framing.encode(message))
        await self.writer.drain()

    async def pump(self, duration):
        end = asyncio.get_event_loop().time() + duration
        while asyncio.get_event_loop().time() < end:
            remaining = max(0.01, min(end - asyncio.get_event_loop().time(), 0.1))
            try:
                frame = await asyncio.wait_for(framing.read_frame(self.reader), timeout=remaining)
            except asyncio.TimeoutError:
                continue
            if frame is None:
                break
            self.inbox.append(frame)
        return [f for f in self.inbox]

    def of(self, mtype, wherein=None):
        pool = wherein if wherein is not None else self.inbox
        return [f for f in pool if f["type"] == mtype]

    def since(self, seq, mtype):
        return [f for f in self.inbox if f["type"] == mtype
                and f["payload"].get("seq", 0) > seq]

    def clear(self):
        self.inbox.clear()


def mark(ok, text):
    print("%s %s" % ("PASS" if ok else "FAIL", text))
    return ok


def check(name, predicate):
    ok = bool(predicate())
    mark(ok, name)
    return ok


def summary(results):
    passed = sum(1 for r in results if r)
    print("=" * 60)
    print("RESULT: %d/%d checks passed" % (passed, len(results)))
    return 0 if all(results) else 1


async def run_scenario(port):
    alice = Client("Alice", port)
    bob = Client("Bob", port)
    for c in (alice, bob):
        await c.connect()
        await asyncio.sleep(0.2)
    a_welcome, b_welcome = await asyncio.gather(alice.pump(0.5), bob.pump(0.5))
    results = []

    a_pid = a_welcome[0]["payload"]["player_id"]
    b_pid = b_welcome[0]["payload"]["player_id"]

    results.append(check(
        "Alice got WELCOME with player_id",
        lambda: any(f["type"] == "WELCOME" for f in a_welcome),
    ))
    results.append(check(
        "Bob got WELCOME with player_id",
        lambda: any(f["type"] == "WELCOME" for f in b_welcome),
    ))

    # --- phase 1: both ready in zone A, clock gate opens ---
    alice.clear(); bob.clear()
    await alice.send(msg.make_time_ready(ZONE_A))
    await bob.send(msg.make_time_ready(ZONE_A))
    a_frames, b_frames = await asyncio.gather(alice.pump(0.5), bob.pump(0.5))

    results.append(check(
        "Clock gate opened (both in zone A)",
        lambda: any(f["type"] == "TIME_SYNC" and f["payload"].get("gate") is True
                     for f in a_frames),
    ))
    results.append(check(
        "Bob sees clock gate open too",
        lambda: any(f["type"] == "TIME_SYNC" and f["payload"].get("gate") is True
                     for f in b_frames),
    ))

    # --- phase 2: claim and world sync ---
    alice.clear(); bob.clear()
    await alice.send(msg.make_object_claim("sim:AAA111", zone_id=ZONE_A))
    await bob.send(msg.make_object_claim("sim:BBB222", zone_id=ZONE_A))
    a_frames, b_frames = await asyncio.gather(alice.pump(0.5), bob.pump(0.5))

    results.append(check(
        "Alice claims sim:AAA111",
        lambda: any(
            f["payload"].get("key") == "sim:AAA111" and f["payload"].get("owner") is not None
            for f in alice.of("OBJECT_CLAIM_ACK", a_frames)
        ),
    ))
    results.append(check(
        "Bob claims sim:BBB222",
        lambda: any(
            f["payload"].get("key") == "sim:BBB222" and f["payload"].get("owner") is not None
            for f in bob.of("OBJECT_CLAIM_ACK", b_frames)
        ),
    ))
    results.append(check(
        "Alice sees Bob's OBJECT_OWNERSHIP for sim:BBB222",
        lambda: any(
            f["payload"].get("key") == "sim:BBB222" and f["payload"].get("owner") == b_pid
            for f in alice.of("OBJECT_OWNERSHIP", a_frames)
        ),
    ))
    results.append(check(
        "Bob sees Alice's OBJECT_OWNERSHIP for sim:AAA111",
        lambda: any(
            f["payload"].get("key") == "sim:AAA111" and f["payload"].get("owner") == a_pid
            for f in bob.of("OBJECT_OWNERSHIP", b_frames)
        ),
    ))

    # --- phase 3: world delta (position) delivery ---
    alice.clear(); bob.clear()
    await alice.send(msg.make_object_update(
        [{"key": "sim:AAA111", "fields": {"x": 10.0, "y": 0.0, "z": 5.0}, "rev": 1}],
        zone_id=ZONE_A,
    ))
    await bob.send(msg.make_object_update(
        [{"key": "sim:BBB222", "fields": {"x": 20.0, "y": 0.0, "z": 15.0}, "rev": 1}],
        zone_id=ZONE_A,
    ))
    a_frames, b_frames = await asyncio.gather(alice.pump(0.5), bob.pump(0.5))

    results.append(check(
        "Alice receives WORLD_DELTA with Bob's sim:BBB222 position (x=20)",
        lambda: any(
            f["type"] == "WORLD_DELTA"
            and any(e.get("key") == "sim:BBB222" and e.get("fields", {}).get("x") == 20.0
                    for e in f["payload"].get("updates", []))
            for f in alice.of("WORLD_DELTA", a_frames)
        ),
    ))
    results.append(check(
        "Bob receives WORLD_DELTA with Alice's sim:AAA111 position (x=10)",
        lambda: any(
            f["type"] == "WORLD_DELTA"
            and any(e.get("key") == "sim:AAA111" and e.get("fields", {}).get("x") == 10.0
                    for e in f["payload"].get("updates", []))
            for f in bob.of("WORLD_DELTA", b_frames)
        ),
    ))

    # --- phase 4: interaction mirror with targeting ---
    alice.clear(); bob.clear()
    await alice.send(msg.make_interaction_request(
        "sim:AAA111", "PetSocial_Groom", affordance="aff_groom",
        affordance_id=99001, target="sim:BBB222", zone_id=ZONE_A,
    ))
    await bob.send(msg.make_interaction_request(
        "sim:BBB222", "Idle", affordance="aff_idle",
        affordance_id=99002, zone_id=ZONE_A,
    ))
    a_frames, b_frames = await asyncio.gather(alice.pump(0.5), bob.pump(0.5))

    results.append(check(
        "Bob sees INTERACTION_START for Alice's groom on sim:AAA111",
        lambda: any(
            f["type"] == "INTERACTION_START"
            and f["payload"].get("object_key") == "sim:AAA111"
            and f["payload"].get("interaction") == "PetSocial_Groom"
            and f["payload"].get("affordance_id") == 99001
            and f["payload"].get("target") == "sim:BBB222"
            for f in bob.of("INTERACTION_START", b_frames)
        ),
    ))
    results.append(check(
        "Alice sees INTERACTION_START for Bob's idle on sim:BBB222",
        lambda: any(
            f["type"] == "INTERACTION_START"
            and f["payload"].get("object_key") == "sim:BBB222"
            and f["payload"].get("interaction") == "Idle"
            and f["payload"].get("affordance_id") == 99002
            for f in alice.of("INTERACTION_START", a_frames)
        ),
    ))

    # --- phase 5: interaction end clears the slot for peers ---
    alice.clear(); bob.clear()
    await alice.send(msg.make_interaction_end("sim:AAA111", zone_id=ZONE_A))
    a_frames, b_frames = await asyncio.gather(alice.pump(0.4), bob.pump(0.4))

    results.append(check(
        "Bob sees INTERACTION_FREE for sim:AAA111 after Alice ends",
        lambda: any(
            f["type"] == "INTERACTION_FREE"
            and f["payload"].get("object_key") == "sim:AAA111"
            for f in bob.of("INTERACTION_FREE", b_frames)
        ),
    ))

    # --- phase 6: zone flip (Alice travels to ZONE_B) ---
    alice.clear(); bob.clear()
    await alice.send(msg.make_time_ready(ZONE_B))
    a_frames, b_frames = await asyncio.gather(alice.pump(0.6), bob.pump(0.6))

    results.append(check(
        "Alice released sim:AAA111 in zone A (auto-release on flip)",
        lambda: any(
            f["type"] == "OBJECT_OWNERSHIP"
            and f["payload"].get("key") == "sim:AAA111"
            and f["payload"].get("owner") is None
            and f["payload"].get("zone_id") == ZONE_A
            for f in bob.of("OBJECT_OWNERSHIP", b_frames)
        ),
    ))
    results.append(check(
        "Alice gets fresh WORLD_STATE for zone B",
        lambda: any(
            f["type"] == "WORLD_STATE"
            and f["payload"].get("zone_id") == ZONE_B
            for f in alice.of("WORLD_STATE", a_frames)
        ),
    ))

    # --- phase 7: Bob still operates in zone A (isolation) ---
    bob.clear()
    await bob.send(msg.make_object_claim("sim:CCC333", zone_id=ZONE_A))
    await bob.send(msg.make_object_update(
        [{"key": "sim:BBB222", "fields": {"x": 30.0, "y": 0.0, "z": 20.0}, "rev": 2}],
        zone_id=ZONE_A,
    ))
    b_frames = await bob.pump(0.4)
    results.append(check(
        "Bob can claim a new object in zone A (lowest seq restarts at 1)",
        lambda: any(
            f["payload"].get("key") == "sim:CCC333" and f["payload"].get("owner") is not None
            for f in bob.of("OBJECT_CLAIM_ACK", b_frames)
        ),
    ))

    for c in (alice, bob):
        c.writer.close()
    return results


async def main(argv=None):
    parser = argparse.ArgumentParser(description="2-client same-zone smoke")
    parser.add_argument("--verbose", action="store_true", help="stream server stdout/stderr")
    args = parser.parse_args(argv)

    port = free_port()
    log = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "simmp-2client-server.log")
    server = subprocess.Popen(
        [sys.executable, os.path.join(_ROOT, "server", "main.py"),
         "--host", "127.0.0.1", "--port", str(port),
         "--log-file", log, "--log-level", "INFO"],
        stdout=None if args.verbose else subprocess.DEVNULL,
        stderr=None if args.verbose else subprocess.DEVNULL,
        cwd=_ROOT,
    )

    try:
        deadline = time.time() + 15
        while True:
            try:
                sock = socket.create_connection(("127.0.0.1", port), timeout=0.5)
                sock.close()
                break
            except OSError:
                if server.poll() is not None:
                    print("server died on startup; see %s" % log)
                    return 1
                if time.time() > deadline:
                    print("server did not come up within 15s; see %s" % log)
                    return 1
                await asyncio.sleep(0.2)
        print("server up on 127.0.0.1:%s (log: %s)" % (port, log))
        results = await run_scenario(port)
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    return summary(results)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
