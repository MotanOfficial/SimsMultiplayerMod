"""Push a local save file to every connected player via the server.

    python tools/save_sync.py <save_file> [--host HOST] [--port PORT] [--slot NAME]

Exits 0 only when at least one other player acknowledged the file. Reuses the
real client stack (`MultiplayerClient.push_save_file`), hit-tested by the
save-sync tests, so save_sync tells the truth about host saves reaching clients.
"""

import argparse
import asyncio
import concurrent.futures
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for entry in (ROOT, os.path.join(ROOT, "protocol"), os.path.join(ROOT, "client_mod", "scripts")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from simmp_client.connectivity import MultiplayerClient  # noqa: E402


def _connected(client):
    client.process_incoming()
    return client.session.player_id is not None


async def wait_connected(client, timeout=5.0):
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _connected(client):
            return True
        await asyncio.sleep(0.05)
    return False


async def wait_ack(client, log_lines, timeout=15.0):
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        client.process_incoming()
        for line in list(log_lines):
            if "SAVE_ACK" in line and "reached=" in line:
                return line
        await asyncio.sleep(0.05)
    return None


async def run(path, host, port, slot=None, ack_timeout=15.0):
    with open(path, "rb") as handle:
        payload = handle.read()
    slot = slot or os.path.basename(path)
    log = []
    client = MultiplayerClient(client_name="SaveSync", notify=log.append)
    if not client.connect(host, port):
        print("[SAVESYNC] connect() returned False; is the server up?", file=sys.stderr)
        return 2
    logging.getLogger("simmp").setLevel(logging.WARNING)
    if not await wait_connected(client):
        print("[SAVESYNC] timed out waiting for WELCOME", file=sys.stderr)
        return 2

    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(client.push_save_file, slot, payload)
        while not future.done():
            client.process_incoming()
            await asyncio.sleep(0.02)
        sent, total = future.result()
    finally:
        pool.shutdown()
    print("[SAVESYNC] pushed %s (%s bytes) as %s: %s/%s chunks" % (path, len(payload), slot, sent, total))
    if sent != total:
        print("[SAVESYNC] upload incomplete; not waiting for ack", file=sys.stderr)
        client.disconnect()
        return 1

    ack = await wait_ack(client, log, timeout=ack_timeout)
    client.disconnect()
    if ack is None:
        print("[SAVESYNC] no SAVE_ACK within %.0fs" % ack_timeout, file=sys.stderr)
        return 1
    print("[SAVESYNC] %s" % ack)
    reached = [int(token.split("=", 1)[1]) for token in ack.split() if token.startswith("reached=")]
    if reached and reached[0] >= 1:
        print("[SAVESYNC] delivered to %s other player(s)" % reached[0])
        return 0
    print("[SAVESYNC] no other player connected; save acked locally only", file=sys.stderr)
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("save_file", help="path to the .save file to distribute")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--slot", default=None, help="slot name on the server (default: file basename)")
    parser.add_argument("--ack-timeout", type=float, default=15.0)
    args = parser.parse_args(argv)
    if not os.path.isfile(args.save_file):
        print("[SAVESYNC] no such file: %s" % args.save_file, file=sys.stderr)
        return 2
    try:
        return asyncio.run(run(args.save_file, args.host, args.port, args.slot, args.ack_timeout))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())