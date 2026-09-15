"""Command line configuration for the server."""

import argparse

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_LOG_LEVEL = "INFO"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="simmp multiplayer server (M1)")
    parser.add_argument("--host", default=DEFAULT_HOST, help="bind address (default %s)" % DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="bind port (default %s)" % DEFAULT_PORT)
    parser.add_argument(
        "--log-level",
        default=DEFAULT_LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="console log level (default %s)" % DEFAULT_LOG_LEVEL,
    )
    parser.add_argument("--log-file", default=None, help="optional log file path")
    parser.add_argument(
        "--status-file",
        default=None,
        help="optional JSON status file (connected players/rooms) rewritten periodically",
    )
    return parser.parse_args(argv)