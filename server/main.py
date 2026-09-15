"""Entry point for the multiplayer server.

Run from the project root:

    python server/main.py [--host 127.0.0.1] [--port 8765]

Starts an asyncio server and blocks until interrupted.
"""

import asyncio
import logging
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROTOCOL = os.path.join(_ROOT, "protocol")
for _entry in (_ROOT, _PROTOCOL):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from server.config import parse_args  # noqa: E402
from server.networking.server import MPServer  # noqa: E402


def _configure_logging(args):
    handlers = []
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(getattr(logging, args.log_level))
    console.setFormatter(logging.Formatter("[MP][%(levelname)s] %(message)s"))
    handlers.append(console)
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, args.log_level))
        file_handler.setFormatter(logging.Formatter("[MP][%(asctime)s][%(levelname)s] %(message)s"))
        handlers.append(file_handler)
    return handlers


async def _run_server(args, logger):
    from simmp.constants import PROTOCOL_VERSION

    server = MPServer(args.host, args.port, logger=logger, status_file=args.status_file)
    await server.start()
    logger.info(
        "[MP][NET] Listening on %s:%s (protocol v%s)",
        server.host,
        server.port,
        PROTOCOL_VERSION,
    )
    try:
        await server.serve_forever()
    finally:
        await server.stop()


def main(argv=None):
    args = parse_args(argv)
    handlers = _configure_logging(args)
    logger = logging.getLogger("simmp.server")
    logger.setLevel(getattr(logging, args.log_level))
    for handler in handlers:
        logger.addHandler(handler)
    try:
        asyncio.run(_run_server(args, logger))
    except KeyboardInterrupt:
        logger.info("[MP][NET] Shutting down")
    return 0


if __name__ == "__main__":
    sys.exit(main())