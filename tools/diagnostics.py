"""Diagnostics bundling and LAN hand-off for the launcher (stdlib only).

Field problems on this mod are diagnosed from a handful of text files:

* ``server.log``      - the host's embedded server log (claims, relays, ghosts)
* ``status.json``     - the host's live server status snapshot
* ``client.log``      - the *game-side* mod log (per PC)
* ``Sims4Multiplayer-diag.txt`` - the mod's own ``mp.diag`` dump (per PC)
* ``Sims4Multiplayer.json``     - the auto-connect config (per PC)
* the launcher's own activity history (per PC)

This module gathers them into one self-describing ``.zip`` (with a README and
an environment summary), and provides the two ends of a LAN hand-off: the host
launcher runs :class:`DiagnosticsReceiver` while its lobby is open, and a
joiner's launcher POSTs its bundle there with :func:`send_bundle`, so players
stop trading files by hand.

Pure stdlib so it is unit-testable without Qt or the game.
"""

import hashlib
import os
import shutil
import socket
import threading
import time
import zipfile

#: Cap per collected file (extra content is dropped, a note is recorded) so a
#: run-away log can never produce an unusable bundle.
MAX_FILE_BYTES = 4 * 1024 * 1024
#: Cap on a whole received/uploaded bundle.
MAX_BUNDLE_BYTES = 16 * 1024 * 1024
#: Suffix used for the receiver's listening port (lobby port + 1).
RECEIVER_PORT_OFFSET = 1
RECEIVER_PATH = "/diagnostics"
PING_PATH = "/ping"
RECEIVED_DIRNAME = "received"
EXPORT_DIRNAME = "diagnostics"


def receiver_port(lobby_port, offset=RECEIVER_PORT_OFFSET):
    """Diagnostics receiver port for a given lobby port (e.g. 8765 -> 8766)."""
    try:
        return int(lobby_port) + int(offset)
    except (TypeError, ValueError):
        return 8766


def _stamp(now=None):
    return time.strftime("%Y%m%d-%H%M%S", time.localtime(now or time.time()))


def _safe_name(value, fallback="player"):
    cleaned = []
    for ch in str(value or ""):
        cleaned.append(ch if (ch.isalnum() or ch in "._-") else "_")
    name = "".join(cleaned).strip("._")
    return name or fallback


def game_client_log_path():
    """Mirror of ``simmp_client.logfile.default_log_path`` without the import."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Sims4Multiplayer", "client.log")


def _read_capped(path, limit=MAX_FILE_BYTES):
    """(data, note) for one file; data is None when it is missing/unreadable."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return (None, "missing")
    try:
        with open(path, "rb") as handle:
            data = handle.read(limit)
    except OSError as exc:
        return (None, "unreadable (%s)" % exc)
    if size > len(data):
        return (data, "truncated to the last %d KiB" % (limit // 1024))
    return (data, "%d KiB" % ((len(data) + 1023) // 1024))


def collect_bundle(paths=None, info=None, launcher_log=None):
    """Build the bundle as ``{name_in_zip: bytes}``. Never raises.

    ``paths`` maps bundle names to source files; the defaults target the
    standard host/joiner locations. ``info`` is a dict of extra summary lines
    (versions, paths, ports...) rendered into ``info.txt``. ``launcher_log`` is
    the launcher's own activity history (list of strings).
    """
    try:  # the launcher imports these both ways depending on the entry point
        from tools.launcher_common import (
            RUNTIME_DIR,
            SERVER_LOG_FILE,
            SETTINGS_FILE,
            STATUS_FILE,
        )
    except ImportError:  # pragma: no cover - frozen/working-copy layout
        from launcher_common import (  # type: ignore
            RUNTIME_DIR,
            SERVER_LOG_FILE,
            SETTINGS_FILE,
            STATUS_FILE,
        )

    source_paths = {
        "server-log.txt": SERVER_LOG_FILE,
        "server-status.json": STATUS_FILE,
        "launcher-settings.json": SETTINGS_FILE,
        "game-client.log": game_client_log_path(),
    }
    mods = _mods_folder()
    if mods:
        source_paths["mod-diag.txt"] = os.path.join(mods, "Sims4Multiplayer-diag.txt")
        source_paths["mod-config.json"] = os.path.join(mods, "Sims4Multiplayer.json")
        source_paths["mod-client-id.sha256.txt"] = os.path.join(
            mods, "Sims4Multiplayer.client_id"
        )
    if paths:
        source_paths.update(paths)

    files = {}
    lines = []
    for name, path in source_paths.items():
        if not path:
            continue
        data, note = _read_capped(path)
        if data is None:
            lines.append("%-28s %-10s %s" % (name, note, path))
            continue
        if name.endswith(".sha256.txt"):
            # Never ship the raw client identity: its hash is enough to tell
            # whether two logs came from the same install.
            files[name] = ("sha256=%s\n" % hashlib.sha256(data).hexdigest()).encode("utf-8")
        else:
            files[name] = data
        lines.append("%-28s %-10s %s" % (name, note, path))

    if launcher_log:
        text = "\n".join(str(line) for line in launcher_log)
        files["launcher-log.txt"] = (text + "\n").encode("utf-8", "replace")

    info_lines = [
        "Sims 4 Multiplayer diagnostics bundle",
        "created: %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "",
        "-- collected --",
    ]
    info_lines.extend(lines or ["(nothing found)"])
    if info:
        info_lines.append("")
        info_lines.append("-- environment --")
        for key in sorted(info):
            info_lines.append("%s: %s" % (key, info[key]))
    info_lines.append("")
    info_lines.append("mods folder: %s" % (mods or "(unknown)"))
    info_lines.append("runtime dir: %s" % RUNTIME_DIR)
    files["info.txt"] = ("\n".join(info_lines) + "\n").encode("utf-8", "replace")
    files["README.txt"] = _readme(has_launcher_log=bool(launcher_log))
    return files


def _mods_folder():
    try:
        try:
            from tools.launcher_common import RUNTIME
        except ImportError:  # pragma: no cover - frozen/working-copy layout
            from launcher_common import RUNTIME  # type: ignore

        return RUNTIME.mods_folder() or ""
    except Exception:  # noqa: BLE001 - path detection is best-effort
        return ""


_README_BODY = """Sims 4 Multiplayer - diagnostics bundle
=========================================

What is in here
---------------
info.txt               Summary of what was found, plus versions and paths.
server-log.txt         Host side: the embedded server's log (lobby, claims,
                       relays, ghost eviction). Empty on a joiner's PC.
server-status.json     Host side: live snapshot of rooms/players/clock gate.
game-client.log        The in-game mod log for THIS PC - the main file. Shows
                       connect, room, world sync, claim denials and
                       "world sync health" lines.
mod-diag.txt           Output of the in-game `mp.diag` command (if used).
mod-config.json        The auto-connect config the launcher wrote for the game.
mod-client-id.sha256   Hash (not the value) of this install's client identity.
launcher-log.txt       The launcher's own activity log for this session.
launcher-settings.json Launcher settings (paths, ports, names).

How to read the in-game log
---------------------------
[MP][NET]   connection lifecycle: connects, reconnects, heartbeats
[MP][ROOM]  who is in the room
[MP][SYNC]  world/interaction sync: ownership, deltas, and
            "world sync health: N claim(s) denied by other player(s); ..."
[MP][TIME]  the shared pause/speed gate while players load in
[MP][ERROR] real failures (server-side denials are reported in [MP][SYNC])

Log lines in game-client.log start with a wall-clock timestamp.
"""


def _readme(has_launcher_log=True):
    extra = ""
    if not has_launcher_log:
        extra = "\n(no launcher-log.txt: this bundle was collected without one)\n"
    return ("""%s%s""" % (_README_BODY, extra)).encode("utf-8")


def write_bundle(files, directory, name=None, stamp=None):
    """Write ``files`` into a zip in ``directory``; returns the zip path."""
    os.makedirs(directory, exist_ok=True)
    target = os.path.join(
        directory, name or "Sims4Multiplayer-diagnostics-%s.zip" % _stamp(stamp)
    )
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for entry in sorted(files):
            archive.writestr(entry, files[entry])
    return target


def export_bundle(directory, **kwargs):
    """Collect + zip in one call (used by the launcher's Export button)."""
    return write_bundle(collect_bundle(**kwargs), directory)


def desktop_directory():
    """Best-effort Desktop path (OneDrive-redirected Documents included)."""
    for candidate in (
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        os.path.join(os.environ.get("OneDrive", ""), "Desktop"),
        os.path.expanduser("~/Desktop"),
    ):
        if candidate and os.path.isdir(candidate):
            return candidate
    return os.path.expanduser("~")


def open_in_explorer(path):
    """Open a folder/file with the OS handler; returns True on success."""
    try:
        if os.name == "nt":
            os.startfile(path)  # noqa: 601 - Windows-only helper
        elif shutil.which("xdg-open"):
            os.system('xdg-open "%s" >/dev/null 2>&1 &' % path)
        return True
    except Exception:  # noqa: BLE001
        return False


def _parse_query(path):
    query = {}
    if "?" not in path:
        return query
    try:
        from urllib.parse import parse_qs  # lazy: urllib may be trimmed in the bundle

        return parse_qs(path.split("?", 1)[1])
    except Exception:  # noqa: BLE001
        # Minimal fallback: split on & and = without percent-decoding.
        try:
            for chunk in path.split("?", 1)[1].split("&"):
                if "=" in chunk:
                    key, _, value = chunk.partition("=")
                    query.setdefault(key, []).append(value)
        except Exception:  # noqa: BLE001
            pass
        return query


def _reason(status):
    return {
        200: "OK",
        404: "Not Found",
        413: "Payload Too Large",
    }.get(status, "OK")


def _send_reply(conn, status, payload):
    """Write one minimal HTTP/1.1 text response; never raises."""
    try:
        body = payload.encode("utf-8") if isinstance(payload, str) else payload
        head = (
            "HTTP/1.1 %d %s\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n\r\n" % (status, _reason(status), len(body))
        )
        conn.sendall(head.encode("utf-8") + body)
    except Exception:  # noqa: BLE001 - client vanished mid-reply
        pass


def _recv_until(conn, marker, limit=65536):
    """Read until ``marker`` appears; b"" on close/overflow/timeout."""
    data = b""
    try:
        while marker not in data:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if len(data) > limit:
                break
    except (OSError, socket.timeout):
        pass
    return data


def _recv_exact(conn, count):
    """Read exactly ``count`` bytes (b"" shortfall allowed); never raises."""
    data = b""
    try:
        while len(data) < count:
            chunk = conn.recv(min(65536, count - len(data)))
            if not chunk:
                break
            data += chunk
    except (OSError, socket.timeout):
        pass
    return data


def _read_reply(sock_file):
    """Parse one HTTP/1.x response into ``(status, body)``; never raises."""
    try:
        status_line = sock_file.readline(8192).decode("latin-1")
    except (OSError, socket.timeout, ValueError):
        return (0, "")
    parts = status_line.split()
    try:
        status = int(parts[1]) if len(parts) >= 2 else 0
    except (TypeError, ValueError):
        status = 0
    length = 0
    try:
        while True:
            line = sock_file.readline(8192).decode("latin-1")
            if not line or line in ("\r\n", "\n"):
                break
            if line.lower().startswith("content-length:"):
                try:
                    length = max(0, int(line.split(":", 1)[1].strip() or 0))
                except (TypeError, ValueError):
                    length = 0
    except (OSError, socket.timeout, ValueError):
        return (status, "")
    body = b""
    try:
        while len(body) < length:
            chunk = sock_file.read(min(65536, length - len(body)))
            if not chunk:
                break
            body += chunk
    except (OSError, socket.timeout, ValueError):
        pass
    return (status, body.decode("utf-8", "replace"))


class DiagnosticsReceiver(object):
    """Tiny HTTP listener that accepts a joiner's bundle on the host.

    ``POST /diagnostics?name=<player>&role=<host|join>`` with the zip as body
    stores it under ``directory``; ``GET /ping`` answers ``simmp-diagnostics``
    so a joiner can confirm the host is reachable before sending. ``port=0``
    binds a free port and reports it as ``actual_port`` (used by tests).
    """

    def __init__(self, port, directory, on_received=None, log=None,
                 host="0.0.0.0", max_bytes=MAX_BUNDLE_BYTES):
        self.port = int(port)
        self.host = host
        self.directory = directory
        self.max_bytes = int(max_bytes)
        self.on_received = on_received
        self.log = log or (lambda *_args, **_kwargs: None)
        self.actual_port = self.port
        self._socket = None
        self._stop = threading.Event()
        self._thread = None

    # ------------------------------------------------------------ lifecycle
    def start(self):
        """Start serving. Returns True when bound, False when the port is busy."""
        if self._socket is not None:
            return True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # NOTE: deliberately no SO_REUSEADDR - a second receiver must fail
        # loudly instead of silently hijacking an in-use port.
        try:
            sock.bind((self.host, self.port))
        except OSError as exc:
            self.log("Diagnostics receiver could not bind port %s: %s" % (self.port, exc))
            try:
                sock.close()
            except OSError:
                pass
            return False
        try:
            sock.listen(8)
        except OSError as exc:
            self.log("Diagnostics receiver listen failed on port %s: %s" % (self.port, exc))
            try:
                sock.close()
            except OSError:
                pass
            return False
        self._socket = sock
        self.actual_port = sock.getsockname()[1]
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._serve, name="simmp-diagnostics", daemon=True
        )
        self._thread.start()
        self.log("Diagnostics receiver listening on %s:%s" % (self.host, self.actual_port))
        return True

    def _serve(self):
        try:
            self._socket.settimeout(0.5)
            while not self._stop.is_set():
                try:
                    conn, _addr = self._socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                worker = threading.Thread(
                    target=self._handle_one, args=(conn,), daemon=True
                )
                worker.start()
        except Exception:  # noqa: BLE001 - shutdown races are not interesting
            pass

    def _handle_one(self, conn):
        try:
            conn.settimeout(25.0)
            raw = _recv_until(conn, b"\r\n\r\n")
            if b"\r\n\r\n" not in raw:
                _send_reply(conn, 404, "not found\n")
                return
            head, rest = raw.split(b"\r\n\r\n", 1)
            lines = head.decode("latin-1").split("\r\n")
            if not lines:
                _send_reply(conn, 404, "not found\n")
                return
            parts = lines[0].split()
            if len(parts) < 2:
                _send_reply(conn, 404, "not found\n")
                return
            method, path = parts[0].upper(), parts[1]
            length = 0
            for line in lines[1:]:
                if line.lower().startswith("content-length:"):
                    try:
                        length = int(line.split(":", 1)[1].strip() or 0)
                    except (TypeError, ValueError):
                        length = 0
                    break
            if method == "GET":
                if path.startswith(PING_PATH):
                    _send_reply(conn, 200, "simmp-diagnostics\n")
                else:
                    _send_reply(conn, 404, "not found\n")
                return
            if method != "POST" or not path.startswith(RECEIVER_PATH):
                _send_reply(conn, 404, "not found\n")
                return
            if length > self.max_bytes:
                _send_reply(conn, 413, "bundle larger than %d bytes\n" % self.max_bytes)
                return
            body = rest[:length] + _recv_exact(conn, max(0, length - len(rest)))
            _send_reply(conn, *self.handle_upload(body, _parse_query(path)))
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass

    def stop(self):
        self._stop.set()
        sock, self._socket = self._socket, None
        if sock is None:
            return
        try:
            sock.close()
        except Exception:  # noqa: BLE001
            pass
        self._thread = None
        self.log("Diagnostics receiver stopped")

    def thread_alive(self):
        return self._thread is not None and self._thread.is_alive()

    # -------------------------------------------------------------- requests
    def handle_upload(self, body, query):
        """Store one uploaded bundle; returns (status, text) for the reply."""
        if len(body) > self.max_bytes:
            return (413, "bundle larger than %d bytes\n" % self.max_bytes)
        if not body:
            return (400, "empty body\n")
        name = _safe_name(query.get("name", ["player"])[0])
        role = _safe_name(query.get("role", ["join"])[0], "join")
        try:
            os.makedirs(self.directory, exist_ok=True)
            target = os.path.join(
                self.directory, "diag-%s-%s-%s.zip" % (_stamp(), role, name)
            )
            with open(target, "wb") as handle:
                handle.write(body)
        except OSError as exc:
            self.log("Could not store received diagnostics: %s" % exc)
            return (500, "could not store bundle\n")
        self.log("Received diagnostics from %s (%s): %s" % (name, role, os.path.basename(target)))
        if self.on_received is not None:
            try:
                self.on_received(target, {"name": name, "role": role})
            except Exception:  # noqa: BLE001
                pass
        return (200, "ok %s\n" % os.path.basename(target))


def send_bundle(zip_path, host, port, name="player", role="join", timeout=25.0):
    """POST ``zip_path`` to a host's diagnostics receiver.

    Returns ``(ok, detail)`` - never raises, so a launcher button can report
    exactly what happened ("host has no receiver on this port", timeouts...).
    """
    host = (host or "").strip()
    if not host:
        return (False, "no host address set")
    try:
        port = int(port)
    except (TypeError, ValueError):
        return (False, "bad port")
    try:
        with open(zip_path, "rb") as handle:
            body = handle.read(MAX_BUNDLE_BYTES + 1)
    except OSError as exc:
        return (False, "cannot read bundle: %s" % exc)
    url = "http://%s:%d%s?name=%s&role=%s" % (
        host,
        port,
        RECEIVER_PATH,
        _safe_name(name),
        _safe_name(role, "join"),
    )
    return _post_raw(url, body, timeout, host, port)


def _post_raw(url, body, timeout, host, port):
    """POST bytes via raw sockets; ``(ok, detail)`` - never raises."""
    path = url.split("://", 1)[-1]
    slash = path.find("/")
    path = path[slash:] if slash >= 0 else "/"
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except (OSError, socket.timeout) as exc:
        return (False, "could not reach %s:%d (%s)" % (host, port, exc))
    try:
        sock.settimeout(timeout)
        request = (
            "POST %s HTTP/1.1\r\n"
            "Host: %s:%d\r\n"
            "Content-Type: application/zip\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n\r\n" % (path, host, port, len(body))
        )
        sock.sendall(request.encode("utf-8") + body)
        status, reply = _read_reply(sock.makefile("rb"))
    except (OSError, socket.timeout, ValueError) as exc:
        try:
            sock.close()
        except OSError:
            pass
        return (False, "could not reach %s:%d (%s)" % (host, port, exc))
    try:
        sock.close()
    except OSError:
        pass
    reply = (reply or "").strip()
    if status == 200:
        return (True, reply or "sent")
    if status == 413:
        return (False, "host replied 413")
    if status:
        return (False, "host replied %s" % status)
    return (False, "could not reach %s:%d (no reply)" % (host, port))


def ping_receiver(host, port, timeout=3.0):
    """True when a diagnostics receiver answers on ``host:port``."""
    host = (host or "").strip()
    if not host:
        return False
    try:
        port = int(port)
    except (TypeError, ValueError):
        return False
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except (OSError, socket.timeout):
        return False
    try:
        sock.settimeout(timeout)
        sock.sendall(
            ("GET %s HTTP/1.1\r\nHost: %s:%d\r\nConnection: close\r\n\r\n"
             % (PING_PATH, host, port)).encode("utf-8")
        )
        _status, reply = _read_reply(sock.makefile("rb"))
        return "simmp-diagnostics" in reply
    except (OSError, socket.timeout, ValueError):
        return False
    finally:
        try:
            sock.close()
        except OSError:
            pass


