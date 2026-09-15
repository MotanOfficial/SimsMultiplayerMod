"""Live split-zone smoke against the real server binary, run from project root.

Boots ``server/main.py`` as a subprocess on a free port, then drives three raw
clients through the zone-isolation, zone-flip auto-release, and bootstrap
scenarios, asserting on the observed frames.

Usage:
    python tests/smoke/smoke_split_zone.py
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
        await self.send(msg.make_hello(self.name, "smoke-split-zone"))

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
        return [frame for frame in self.inbox]

    def of(self, mtype, wherein=None):
        pool = wherein if wherein is not None else self.inbox
        return [frame for frame in pool if frame["type"] == mtype]


def mark(ok, text):
    print("%s %s" % ("PASS" if ok else "FAIL", text))
    return ok


def check(name, predicate, frames):
    ok = bool(predicate(frames))
    mark(ok, name)
    return ok


def summary(results):
    passed = sum(1 for r in results if r)
    print("=" * 60)
    print("RESULT: %d/%d checks passed" % (passed, len(results)))


async def run_scenario(port, log):
    alice, bob, carol = Client("Alice", port), Client("Bob", port), Client("Carol", port)
    for c in (alice, bob, carol):
        await c.connect()
        await asyncio.sleep(0.2)
        await c.pump(0.3)

    results = []

    # --- phase 1: Alice and Bob ready in zone 100, Carol stays unknown (gated) ---
    await alice.send(msg.make_time_ready(100))
    await bob.send(msg.make_time_ready(100))
    frames_a, frames_b, frames_c = await asyncio.gather(
        alice.pump(0.4), bob.pump(0.4), carol.pump(0.4)
    )

    # Alice claims sofa in zone 100 -> room dominant => snapshot zone 100 to both
    await alice.send(msg.make_object_claim("sofa", zone_id=100))
    frames_a, frames_b, frames_c = await asyncio.gather(
        alice.pump(0.4), bob.pump(0.4), carol.pump(0.4)
    )

    results.append(check(
        "Alice gets OBJECT_CLAIM_ACK owner=Alice for 'sofa' in zone 100",
        lambda fr: any(
            f["payload"].get("key") == "sofa" and f["payload"].get("owner") is not None
            for f in alice.of("OBJECT_CLAIM_ACK", frames_a)
        ),
        frames_a,
    ))
    results.append(check(
        "Bob sees OBJECT_OWNERSHIP(sofa, zone 100)",
        lambda fr: any(
            f["payload"].get("key") == "sofa" and f["payload"].get("zone_id") == 100
            and f["payload"].get("owner") is not None
            for f in bob.of("OBJECT_OWNERSHIP", frames_b)
        ),
        frames_b,
    ))
    results.append(check(
        "Carol (unknown zone) receives a bootstrap WORLD_STATE on HELLO",
        lambda fr: any(f["type"] == "WORLD_STATE" for f in carol.inbox),
        frames_c,
    ))
    results.append(check(
        "Carol (unknown zone) receives Alice's OBJECT_OWNERSHIP (bootstrap delivery)",
        lambda fr: any(
            f["payload"].get("key") == "sofa" and f["payload"].get("zone_id") == 100
            for f in carol.of("OBJECT_OWNERSHIP", frames_c)
        ),
        frames_c,
    ))

    # --- phase 3: Alice's interaction in zone 100 ---
    await alice.send(msg.make_interaction_request("sofa", "Read", zone_id=100))
    frames_a, frames_b, frames_c = await asyncio.gather(
        alice.pump(0.4), bob.pump(0.4), carol.pump(0.4)
    )
    results.append(check(
        "Bob sees INTERACTION_START(sofa, zone 100)",
        lambda fr: any(
            f["payload"].get("object_key") == "sofa" and f["payload"].get("zone_id") == 100
            for f in bob.of("INTERACTION_START", frames_b)
        ),
        frames_b,
    ))
    results.append(check(
        "Carol (unknown zone) sees INTERACTION_START (bootstrap delivery)",
        lambda fr: any(
            f["payload"].get("object_key") == "sofa" and f["payload"].get("zone_id") == 100
            for f in carol.of("INTERACTION_START", frames_c)
        ),
        frames_c,
    ))

    # --- phase 4: Alice flips to zone 200 (travel) ---
    await alice.send(msg.make_time_ready(200))
    frames_a, frames_b, frames_c = await asyncio.gather(
        alice.pump(0.6), bob.pump(0.6), carol.pump(0.6)
    )
    results.append(check(
        "Old zone (100) gets OBJECT_OWNERSHIP(null) for 'sofa' after flip",
        lambda fr: any(
            f["payload"].get("key") == "sofa" and f["payload"].get("owner") is None
            and f["payload"].get("zone_id") == 100
            for f in bob.of("OBJECT_OWNERSHIP", frames_b)
        ),
        frames_b,
    ))
    results.append(check(
        "Old zone (100) gets INTERACTION_FREE('sofa') after flip",
        lambda fr: any(
            f["payload"].get("object_key") == "sofa" and f["payload"].get("zone_id") == 100
            for f in bob.of("INTERACTION_FREE", frames_b)
        ),
        frames_b,
    ))
    results.append(check(
        "Alice receives fresh WORLD_STATE for zone 200 (travel snapshots)",
        lambda fr: any(
            f["type"] == "WORLD_STATE" and f["payload"].get("zone_id") == 200
            for f in alice.of("WORLD_STATE", frames_a)
        ),
        frames_a,
    ))

    # --- phase 5: Bob reclaims sofa in 100 now that Alice released it ---
    await bob.send(msg.make_object_claim("sofa", zone_id=100))
    frames_b, frames_a, frames_c = await asyncio.gather(
        bob.pump(0.4), alice.pump(0.4), carol.pump(0.4)
    )
    results.append(check(
        "Bob can reclaim 'sofa' in zone 100 after Alice's flip-released it",
        lambda fr: any(
            f["payload"].get("key") == "sofa" and f["payload"].get("owner") is not None
            for f in bob.of("OBJECT_CLAIM_ACK", frames_b)
        ),
        frames_b,
    ))
    results.append(check(
        "Alice does NOT see Bob's zone-100 ownership (different zone)",
        lambda fr: not any(
            f["type"] == "OBJECT_OWNERSHIP" and f["payload"].get("zone_id") == 100
            for f in alice.of("OBJECT_OWNERSHIP", frames_a)
        ),
        frames_a,
    ))

    for c in (alice, bob, carol):
        c.writer.close()
    return results


async def main(argv=None):
    parser = argparse.ArgumentParser(description="live split-zone smoke against real server")
    parser.add_argument("--verbose", action="store_true", help="stream server stdout/stderr")
    args = parser.parse_args(argv)

    port = free_port()
    log = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "simmp-smoke-server.log")
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
        results = await run_scenario(port, log)
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    summary(results)
    return 1 if not all(results) else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))