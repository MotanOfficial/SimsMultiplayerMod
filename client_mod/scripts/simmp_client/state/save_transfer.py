"""SAVE_PUSH chunk reassembly and atomic save writing (game-agnostic).

Pure Python, no game imports: unit-testable on a normal interpreter and
safe to ship inside the mod. The game hooks decide *where* a completed
save lands (`game_hooks.receive_save`); this module only tracks the state.

Chunks must arrive in order within a transfer (seq 1..total, exactly the
declared size); anything else is ignored, so duplicate/retransmit frames
can never corrupt a completed file.
"""

import base64
import os
import tempfile
import time

MAX_CHUNK_WINDOW_SECONDS = 600.0


class SaveInbox:
    def __init__(self, window=None):
        self.window = window if window is not None else MAX_CHUNK_WINDOW_SECONDS
        self._transfers = {}

    def feed(self, slot, seq, total, size, data_b64):
        """Feed one chunk. Returns ("more"|"duplicate"|"badseq"|"complete", bytes|None)."""
        now = time.time()
        state = self._transfers.get(slot)
        if state is None:
            state = {"total": total, "size": size, "next": 1, "buffer": bytearray(), "last": now}
            self._transfers[slot] = state
            self._prune(now)
        if seq != state["next"]:
            return ("duplicate" if seq < state["next"] else "badseq", None)
        free = size - len(state["buffer"])
        if free <= 0:
            return ("badseq", None)
        chunk = _decode(data_b64)
        if chunk is None or len(chunk) > free:
            return ("badseq", None)
        state["buffer"].extend(chunk)
        state["next"] += 1
        state["last"] = now
        if state["next"] > state["total"]:
            if len(state["buffer"]) != size:
                del self._transfers[slot]
                return ("badseq", None)
            data = bytes(state["buffer"])
            del self._transfers[slot]
            return ("complete", data)
        return ("more", None)

    def forget(self, slot):
        self._transfers.pop(slot, None)

    def active(self):
        return sorted(self._transfers.keys())

    def _prune(self, now):
        for slot in list(self._transfers.keys()):
            if now - self._transfers[slot]["last"] > self.window:
                del self._transfers[slot]


def _decode(data_b64):
    try:
        return base64.b64decode(data_b64)
    except Exception:
        return None


def split_bytes(data, chunk_bytes=512 * 1024):
    """Yield raw slices of `data` (each fits one SAVE_PUSH chunk)."""
    for index in range(0, len(data), chunk_bytes):
        yield data[index : index + chunk_bytes]


def atomic_write(directory, filename, data):
    """Write `data` to `directory/filename` atomically (temp file + rename).

    Returns the final path. Raises OSError/ValueError on bad input.
    """
    if not filename or os.path.basename(filename) != filename:
        raise ValueError("filename must be a bare basename")
    os.makedirs(directory, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".save-incoming-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        target = os.path.join(directory, filename)
        os.replace(temp_path, target)
        return target
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise