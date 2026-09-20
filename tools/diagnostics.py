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
import http.server
import os
import shutil
import socket
import threading
import time
import urllib.error
import urllib.request
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
    from urllib.parse import parse_qs

    try:
        return parse_qs(path.split("?", 1)[1])
    except Exception:  # noqa: BLE001
        return query


class _Server(http.server.ThreadingHTTPServer):
    """Threaded HTTP server that refuses to share a busy port.

    ``SO_REUSEADDR`` would let a second receiver silently hijack an in-use
    port (and split incoming bundles between them), so the launcher gets a
    loud "could not bind" instead.
    """

    allow_reuse_address = False
    daemon_threads = True


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
        self._server = None
        self._thread = None

    # ------------------------------------------------------------ lifecycle
    def start(self):
        """Start serving. Returns True when bound, False when the port is busy."""
        if self._server is not None:
            return True
        try:
            server = _Server((self.host, self.port), _make_handler(self))
        except OSError as exc:
            self.log("Diagnostics receiver could not bind port %s: %s" % (self.port, exc))
            return False
        server.daemon_threads = True
        self._server = server
        self.actual_port = server.server_address[1]
        self._thread = threading.Thread(
            target=self._serve, name="simmp-diagnostics", daemon=True
        )
        self._thread.start()
        self.log("Diagnostics receiver listening on %s:%s" % (self.host, self.actual_port))
        return True

    def _serve(self):
        try:
            self._server.serve_forever(poll_interval=0.2)
        except Exception:  # noqa: BLE001 - shutdown races are not interesting
            pass

    def stop(self):
        server, self._server = self._server, None
        if server is None:
            return
        try:
            server.shutdown()
        except Exception:  # noqa: BLE001
            pass
        try:
            server.server_close()
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


def _make_handler(receiver):
    class _Handler(http.server.BaseHTTPRequestHandler):
        server_version = "SimMPDiagnostics/1.0"

        def log_message(self, fmt, *args):  # keep the launcher console clean
            return

        def _reply(self, status, payload):
            try:
                body = payload.encode("utf-8") if isinstance(payload, str) else payload
                self.send_response(status)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception:  # noqa: BLE001 - client vanished mid-reply
                pass

        def do_GET(self):  # noqa: N802 - http.server API
            if self.path.startswith(PING_PATH):
                self._reply(200, "simmp-diagnostics\n")
                return
            self._reply(404, "not found\n")

        def do_POST(self):  # noqa: N802 - http.server API
            if not self.path.startswith(RECEIVER_PATH):
                self._reply(404, "not found\n")
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except (TypeError, ValueError):
                length = 0
            if length > receiver.max_bytes:
                self._reply(413, "bundle larger than %d bytes\n" % receiver.max_bytes)
                return
            body = self.rfile.read(length) if length > 0 else b""
            self._reply(*receiver.handle_upload(body, _parse_query(self.path)))

    return _Handler


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
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/zip")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            reply = response.read().decode("utf-8", "replace").strip()
        return (True, reply or "sent")
    except urllib.error.HTTPError as exc:
        return (False, "host replied %s" % exc.code)
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return (False, "could not reach %s:%d (%s)" % (host, port, reason))


def ping_receiver(host, port, timeout=3.0):
    """True when a diagnostics receiver answers on ``host:port``."""
    host = (host or "").strip()
    if not host:
        return False
    try:
        url = "http://%s:%d%s" % (host, int(port), PING_PATH)
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return "simmp-diagnostics" in response.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return False


