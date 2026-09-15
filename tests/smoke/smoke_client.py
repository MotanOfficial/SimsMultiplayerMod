"""Minimal CLI client for live smoke testing against `server/main.py`.

Standalone (stdlib asyncio). Connects, sends HELLO, prints everything
inbound, and keeps itself alive with periodic PING heartbeats. Optionally
send one test EVENT (--event) right after WELCOME.

Usage:
    python tests/smoke/smoke_client.py --host 127.0.0.1 --port 8765 --name Alice
    python tests/smoke/smoke_client.py --event hello
    python tests/smoke/smoke_client.py --ping 3 --timeout 20
    python tests/smoke/smoke_client.py --time-ready 7 --time-speed 2 --timeout 20
"""

import argparse
import asyncio
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _entry in (_ROOT, os.path.join(_ROOT, "protocol")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from simmp import framing, messages as msg


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Sims4Multiplayer smoke-test client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--name", default="SmokeClient")
    parser.add_argument("--client-id", default=None, help="stable identity across reconnects")
    parser.add_argument("--event", default=None, help="send a TEST event once after WELCOME")
    parser.add_argument("--presence", default=None, help="send PRESENCE after WELCOME as zone/lot, e.g. 7/12")
    parser.add_argument("--travel", default=None, help="send a TRAVEL_REQUEST for the given zone id after WELCOME")
    parser.add_argument("--clock", default=None, help="send a CLOCK_SYNC beacon, e.g. 1/100000/2998527000/1")
    parser.add_argument("--world", default=None, help="claim an object key and push position deltas, e.g. sofa")
    parser.add_argument("--time-ready", default=None,
                        help="send TIME_READY for a zone after WELCOME, e.g. 7 (join the clock gate)")
    parser.add_argument("--time-speed", type=int, default=None,
                        help="send TIME_SPEED with this speed after WELCOME, e.g. 2")
    parser.add_argument("--interact", default=None,
                        help="propose an interaction key/type then end it after 3s, e.g. sim:123/Read")
    parser.add_argument("--interact-aff", type=int, default=None,
                        help="guid64 tuning id of the super affordance (execution hint)")
    parser.add_argument("--interact-name", default=None,
                        help="display name of the super affordance (execution hint)")
    parser.add_argument("--interact-target", default=None,
                        help="aim sim:<id> the interaction points at (execution hint)")
    parser.add_argument("--interact-end", action="store_true",
                        help="send INTERACTION_END for the --interact key after a short delay")
    parser.add_argument("--autoaccept", action="store_true", help="auto-accept TRAVEL_INVITE messages")
    parser.add_argument("--travel-ready", action="store_true", help="reply TRAVEL_READY after TRAVEL_BEGIN")
    parser.add_argument("--timeout", type=float, default=5.0, help="exit after this many idle seconds")
    parser.add_argument("--ping", type=float, default=5.0, help="send PING heartbeats every N seconds (0 = off)")
    return parser.parse_args(argv)


async def _messages(reader):
    while True:
        message = await framing.read_frame(reader)
        if message is None:
            return
        yield message


async def _wait_for_type(reader, wanted):
    async for message in _messages(reader):
        if message["type"] == wanted:
            return message
        print("<<", message["type"], message["payload"])


async def main(argv=None):
    args = parse_args(argv)
    reader, writer = await asyncio.open_connection(args.host, args.port)
    print("> connected")

    def send(message):
        writer.write(framing.encode(message))
        return writer.drain()

    await send(msg.make_hello(args.name, "smoke-client", client_id=args.client_id))
    welcome = await _wait_for_type(reader, "WELCOME")
    print(">> WELCOME player_id: %s room: %s" % (welcome["payload"]["player_id"], welcome["payload"]["room_id"]))

    if args.event:
        await send(msg.make_event("test", args.event, seq=1))
        print("> sent EVENT: %s" % args.event)

    if args.presence:
        zone_id, lot_id = (int(part) for part in args.presence.split("/"))
        await send(msg.make_presence(zone_id, lot_id))
        print("> sent PRESENCE: zone=%s lot=%s" % (zone_id, lot_id))

    if args.travel:
        await send(msg.make_travel_request(int(args.travel)))
        print("> sent TRAVEL_REQUEST: zone=%s" % args.travel)

    if args.clock:
        zone_id, ticks, real_time, speed = (part for part in args.clock.split("/"))
        await send(msg.make_clock_sync(int(zone_id), int(ticks), float(real_time), int(speed)))
        print("> sent CLOCK_SYNC: zone=%s ticks=%s real=%s speed=%s" % (zone_id, ticks, real_time, speed))

    if args.time_ready:
        await send(msg.make_time_ready(int(args.time_ready)))
        print("> sent TIME_READY: zone=%s" % args.time_ready)

    if args.time_speed is not None:
        await send(msg.make_time_speed(args.time_speed))
        print("> sent TIME_SPEED: %s" % args.time_speed)

    if args.world:
        await send(msg.make_object_claim(args.world))
        print("> sent OBJECT_CLAIM: %s" % args.world)

    if args.interact:
        key, _, interaction = args.interact.partition("/")
        await send(msg.make_interaction_request(
            key,
            interaction or "Read",
            affordance=args.interact_name,
            affordance_id=args.interact_aff,
            target=args.interact_target,
        ))
        print("> sent INTERACTION_REQUEST: %r %s (aff=%s id=%s target=%s)"
              % (key, interaction or "Read", args.interact_name, args.interact_aff, args.interact_target))

    async def interact_pump():
        if not args.interact:
            return
        await asyncio.sleep(3.0)
        key = args.interact.partition("/")[0]
        await send(msg.make_interaction_end(key))
        print("> sent INTERACTION_END: %s" % key)

    interact_task = asyncio.get_running_loop().create_task(interact_pump()) if (
        args.interact and args.interact_end
    ) else None

    async def world_pump():
        if not args.world:
            return
        step = 0
        while True:
            await asyncio.sleep(1.0)
            step += 1
            fields = {"x": float(step % 10) / 10.0, "y": 0.0, "z": 0.0}
            await send(msg.make_object_update([{"key": args.world, "fields": fields, "rev": step}]))
            print("> sent OBJECT_UPDATE %s -> %s" % (args.world, fields))

    world_task = asyncio.get_running_loop().create_task(world_pump()) if args.world else None

    async def heartbeat():
        # The server reaps idle connections after stale_timeout, so keep a
        # long-running smoke client alive (and let a remote peer observe the
        # PONG round-trips) unless --ping 0 disabled it.
        count = 0
        while True:
            await asyncio.sleep(args.ping)
            await send(msg.make_ping(time.time()))
            count += 1

    heartbeat_task = asyncio.get_running_loop().create_task(heartbeat()) if args.ping else None

    async def printer():
        async for message in _messages(reader):
            print("<<", message["type"], message["payload"])
            if message["type"] == "TRAVEL_INVITE" and args.autoaccept:
                await send(msg.make_travel_response(True, request_id_value=message["request_id"]))
                print("> auto-accepted travel invite for zone %s" % message["payload"]["zone_id"])
            if message["type"] == "TRAVEL_BEGIN" and args.travel_ready:
                await send(msg.make_travel_ready(message["payload"]["zone_id"], request_id_value=message["request_id"]))
                print("> reported READY for zone %s" % message["payload"]["zone_id"])

    try:
        await asyncio.wait_for(printer(), timeout=args.timeout)
    except asyncio.TimeoutError:
        print("(idle timeout, exiting)")
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
        if world_task is not None:
            world_task.cancel()
        if interact_task is not None:
            interact_task.cancel()
        writer.close()
        await writer.wait_closed()
        if heartbeat_task is not None:
            await asyncio.gather(heartbeat_task, return_exceptions=True)
        if world_task is not None:
            await asyncio.gather(world_task, return_exceptions=True)
        if interact_task is not None:
            await asyncio.gather(interact_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())