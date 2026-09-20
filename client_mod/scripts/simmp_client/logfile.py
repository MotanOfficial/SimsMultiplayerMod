"""Bounded append-only file log for field debugging.

The game's embedded Python has no logging setup and the cheat console is
ephemeral, so an in-game problem otherwise leaves no trace to inspect after
the fact. This writes every client log line to a single capped file and
truncates the oldest content in place when it grows too large. Pure stdlib and
game-agnostic; it never raises, so logging can never break gameplay.
"""

import os
import time

MAX_BYTES = 1 << 20  # 1 MiB


def default_log_path():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Sims4Multiplayer", "client.log")


class FileLog(object):
    def __init__(self, path=None, max_bytes=MAX_BYTES):
        self.path = path or default_log_path()
        self.max_bytes = max_bytes
        self._size = None

    def write(self, line):
        try:
            if self._size is None:
                try:
                    self._size = os.path.getsize(self.path)
                except OSError:
                    self._size = 0
            text_line = str(line).rstrip("\n")
            # Field logs are read after the fact (often copied off the machine),
            # so every file line carries a wall-clock timestamp. The console
            # output stays unstamped; only the file gets the prefix.
            stamped = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), text_line)
            text = (stamped + "\n").encode("utf-8", "replace")
            if self._size + len(text) > self.max_bytes:
                self._truncate()
            directory = os.path.dirname(self.path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.path, "ab") as handle:
                handle.write(text)
            self._size += len(text)
        except Exception:
            pass

    def _truncate(self):
        keep = self.max_bytes // 2
        try:
            with open(self.path, "rb") as handle:
                handle.seek(max(0, self._size - keep))
                tail = handle.read()
            newline = tail.find(b"\n")
            if newline != -1:
                tail = tail[newline + 1:]
            with open(self.path, "wb") as handle:
                handle.write(tail)
            self._size = len(tail)
        except Exception:
            self._size = 0
