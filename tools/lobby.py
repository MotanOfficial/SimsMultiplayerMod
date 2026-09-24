"""Embedded lobby machinery for the launcher (stdlib only).

The launcher needs a server that starts/stops inside its own process and a
way to (a) push a save file to every connected player and (b) receive such a
push on the join side and land it in the local saves folder. All of this is
game-agnostic and therefore unit-testable offline by pointing it at a real
in-process server:

- ``find_lan_ip``: one best-guess LAN IPv4 for the join screen.
- ``ServerHandle``: runs an ``MPServer`` on a background thread (its own
  event loop), mirrors ``status.json`` into a callback, can be stopped.
- ``push_save_file``: connect as a SaveSync-style player, upload a save via
  ``MultiplayerClient.push_save_file`` and wait for the ack count.
- ``receive_save_file``: connect as a normal player, pump until a
  ``SAVE_PUSH`` transfer completes and the file is written, then disconnect.
"""

import asyncio
import logging
import os
import socket
import sys
import threading
import time

ROOT = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _entry in (ROOT, os.path.join(ROOT, "protocol"), os.path.join(ROOT, "client_mod", "scripts")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from simmp_client.connectivity import MultiplayerClient  # noqa: E402


def find_lan_ip():
    """Return one plausible LAN IPv4 ('' if undetermined).

    Opens a UDP socket to no destination just to read the outgoing interface
    address. Falls back to the machine's first non-loopback IPv4.
    """
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
        finally:
            probe.close()
    except Exception:
        pass
    try:
        host = socket.gethostname()
        for info in socket.getaddrinfo(host, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass
    return ""


def all_lan_ips():
    """Return all local non-loopback IPv4s across every adapter.

    Unlike ``find_lan_ip`` (which only sees the default route's NIC), this
    also picks up virtual/VPN adapters (Radmin VPN, Hamachi, Tailscale, ...)
    so the host can advertise the right address to remote players. Default
    route IP first when known. '' entries filtered out; never raises.
    """
    found = []
    seen = set()
    default = find_lan_ip()

    def add(ip):
        ip = (ip or "").strip()
        if not ip:
            return
        if ip in seen:
            return
        try:
            socket.inet_aton(ip)
        except OSError:
            return
        if ip.startswith("127.") or ip.startswith("0."):
            return
        seen.add(ip)
        found.append(ip)

    add(default)
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(info[4][0])
    except Exception:
        pass
    try:
        import winreg
    except ImportError:
        return found
    try:
        base = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces",
        )
        try:
            count = winreg.QueryInfoKey(base)[0]
            for i in range(count):
                with winreg.OpenKey(base, winreg.EnumKey(base, i)) as sub:
                    for value_name in ("IPAddress", "DhcpIPAddress"):
                        try:
                            value = winreg.QueryValueEx(sub, value_name)[0]
                        except OSError:
                            continue
                        if isinstance(value, str):
                            value = [value]
                        for ip in value:
                            add(ip)
        finally:
            winreg.CloseKey(base)
    except OSError:
        pass
    return found


class ServerHandle:
    """Run an in-process MPServer on its own thread.

    ``on_status(data)`` is invoked with the parsed status.json on each poll
    tick; ``on_log(line)`` receives server log lines so the GUI can tail them.
    """

    def __init__(self, host="0.0.0.0", port=8765, status_file=None,
                 log_file=None, log_level="INFO", on_status=None, on_log=None,
                 min_players=2):
        self.host = host
        self.port = int(port)
        self.status_file = status_file
        self.log_file = log_file
        self.log_level = log_level
        self.on_status = on_status
        self.on_log = on_log
        self.min_players = max(1, int(min_players))
        self.thread = None
        self._loop = None
        self._server = None
        self._stopping = threading.Event()
        self._status_pos = 0
        self._ready = False
        self._error = None
        self.actual_port = self.port

    # -- lifecycle --------------------------------------------------------
    def start(self):
        """Start the server thread; blocks until the socket is bound.

        Returns True on success, False if the server failed to bind (e.g.
        the port is taken) or is already running.
        """
        if self.thread is not None and self.thread.is_alive():
            return False
        self._stopping.clear()
        self.thread = threading.Thread(target=self._runner, daemon=True, name="lobby-server")
        self.thread.start()
        # poll until the loop reports a bound port (or give up)
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if self._ready:
                return True
            if self._error is not None:
                return False
            time.sleep(0.05)
        return False

    def _runner(self):
        self._error = None
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._amain())
        except Exception as exc:  # pragma: no cover - hard to force
            self._error = exc
            self._log("ERROR", "server thread died: %r" % (exc,))
        finally:
            try:
                self._loop.close()
            except Exception:
                pass

    async def _amain(self):
        from server.networking.server import MPServer

        server = MPServer(
            self.host,
            self.port,
            logger=self._make_logger(),
            status_file=self.status_file,
            min_players=self.min_players,
        )
        try:
            await server.start()
        except Exception as exc:
            self._error = exc
            return
        self._server = server
        self.actual_port = server.port
        self._log("INFO", "Listening on %s:%s" % (server.host, server.port))
        self._ready = True
        while not self._stopping.is_set():
            if self.on_status is not None and self.status_file:
                data = self._read_status()
                if data is not None:
                    try:
                        self.on_status(data)
                    except Exception:
                        pass
            await asyncio.sleep(1.0)
        await self._server.stop()

    def _make_logger(self):
        logger = logging.getLogger("simmp.launcher.server")
        logger.handlers = []
        logger.setLevel(self.log_level)
        handler = logging.StreamHandler(sys.stdout)
        if self.log_file:
            try:
                handler = logging.FileHandler(self.log_file, encoding="utf-8")
            except Exception:
                pass
        handler.setFormatter(logging.Formatter("[MP][%(levelname)s] %(message)s"))
        logger.addHandler(handler)
        return logger

    def _log(self, level, line):
        if self.on_log is not None:
            try:
                self.on_log("[%s] %s" % (level, line))
            except Exception:
                pass

    @staticmethod
    def _read_status_path(status_file):
        import json

        try:
            with open(status_file, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return None

    def _read_status(self):
        return self._read_status_path(self.status_file)

    def stop(self):
        if self.thread is None:
            return
        self._stopping.set()
        if self._loop is not None:
            # wake the loop so the running sleep() completes and the server
            # can tear itself down cleanly (socket released, tasks cancelled)
            try:
                self._loop.call_soon_threadsafe(lambda: None)
            except Exception:
                pass
        self.thread.join(timeout=5)
        self.thread = None
        self._loop = None
        self._server = None
        self._ready = False

    def thread_alive(self):
        return self.thread is not None and self.thread.is_alive()


def push_save_file(path, host, port, slot=None, timeout=30.0, name="LobbyHost", on_line=None, keep_alive=False, held=None):
    """Upload ``path`` to the server; return the ack ``(ok, reached)``.

    Raises on connect/upload failure; returns ``(False, reached)`` when the
    server acked locally only (no other player was connected).
    ``on_line(line)``, if given, receives every client ``[MP][...]`` log line
    as it happens (SAVE_ACK progress/errors) so the caller can surface a live
    progress bar in its own UI.
    ``keep_alive=True`` keeps the connected client alive after a successful
    push instead of disconnecting in ``finally``; pass a ``held`` list and the
    live client is appended to it so the caller owns the lifecycle (disconnect
    it later on stop/quit).
    """
    with open(path, "rb") as handle:
        payload = handle.read()
    slot = slot or os.path.basename(path)
    chunk_size = 512 * 1024
    total = (len(payload) + chunk_size - 1) // chunk_size if payload else 1
    log = []

    def _notify(line):
        log.append(line)
        if on_line is not None:
            try:
                on_line(line)
            except Exception:
                pass

    client = MultiplayerClient(client_name=name, notify=_notify)
    client.is_lobby = True
    client.deep_hooks = False
    if not client.connect(host, port):
        client.disconnect()
        raise RuntimeError("connect() returned False; is the lobby running?")
    keep = False
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            client.process_incoming()
            if client.session.player_id is not None:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("timed out waiting for WELCOME")

        sent_holder = {}

        def _push():
            sent_holder["result"] = client.push_save_file(slot, payload, chunk_size=chunk_size)

        worker = threading.Thread(target=_push, daemon=True, name="save-push")
        worker.start()

        # Let the worker queue every chunk first. The engine flushes the socket
        # synchronously from the worker's send lock, so once the worker returns
        # every chunk has hit the wire; only then do acks make sense.
        deadline = time.monotonic() + timeout
        while worker.is_alive() and time.monotonic() < deadline:
            client.process_incoming()
            time.sleep(0.05)
        if worker.is_alive():
            raise RuntimeError("timed out queuing save chunks for the lobby")
        sent, queued_total = sent_holder.get("result", (0, total))
        if sent != queued_total:
            raise RuntimeError(
                "push aborted after %s/%s chunks (send failure? disconnect?)" % (sent, queued_total)
            )

        # Now wait for the ack of the FINAL chunk (seq == total). The server
        # acks every chunk it relays, so acking the first chunk alone does not
        # mean the file transfer finished.
        ack_line = None
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            client.process_incoming()
            for line in list(log):
                if (
                    "SAVE_ACK" in line
                    and "reached=" in line
                    and "seq=%s/%s" % (total, total) in line
                ):
                    ack_line = line
                    break
            if ack_line is not None:
                break
            time.sleep(0.05)
        if ack_line is None:
            client.disconnect()
            raise RuntimeError("no final-chunk SAVE_ACK within %.0fs" % timeout)
        ok = bool(ack_line) and "ok=True" in ack_line
        reached = [
            int(token.split("=", 1)[1]) for token in ack_line.split() if token.startswith("reached=")
        ]
        keep = bool(keep_alive and held is not None)
        if keep:
            held.append(client)
        return (ok, reached[0] if reached else 0)
    finally:
        if not keep:
            try:
                client.disconnect()
            except Exception:
                pass


def receive_save_file(host, port, name="LobbyClient", timeout=60.0, save_dir_candidates=None, on_connected=None, on_line=None, keep_alive=False, held=None):
    """Connect, pump, and report an inbound save + where it was written.

    Returns ``(slot, path)`` once a ``SAVE_PUSH`` completes and is written to
    disk by ``game_hooks.receive_save``. The write-target resolution is
    game-agnostic (pure filesystem) but defaults to the real save folder when
    no candidates are injected.

    A ``SAVE_REQUEST`` is sent right after WELCOME so a late joiner receives
    the save the host shared before they connected (the server caches it).
    ``on_connected()``, if given, is invoked once after WELCOME/request so the
    caller can tell the user they are actually in the lobby. ``on_line(line)``,
    if given, receives every client ``[MP][...]`` log line as it happens so the
    caller can surface save-transfer progress/errors in its own UI.
    ``keep_alive=True`` keeps the connected client alive after a successful
    receive instead of disconnecting in ``finally``; pass a ``held`` list and
    the live client is appended to it so the caller owns the lifecycle.
    """
    log = []

    def _notify(line):
        log.append(line)
        if on_line is not None:
            try:
                on_line(line)
            except Exception:
                pass

    client = MultiplayerClient(client_name=name, notify=_notify)
    client.is_lobby = True
    client.deep_hooks = False
    if not client.connect(host, port):
        client.disconnect()
        raise RuntimeError("connect() returned False; is the lobby running?")
    keep = False
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            client.process_incoming()
            if client.session.player_id is not None:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("timed out waiting for WELCOME")
        client.request_save()
        if on_connected is not None:
            on_connected()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            client.process_incoming()
            for line in list(log):
                arrow = line.strip().find("->")
                if "[MP][SAVE] Saved" not in line or arrow < 0:
                    continue
                path = line.strip()[arrow + 2:].strip().strip("'\"")
                if not path:
                    continue
                slot = os.path.basename(path)
                if slot:
                    keep = bool(keep_alive and held is not None)
                    if keep:
                        held.append(client)
                    return (slot, path)
            time.sleep(0.05)
        raise RuntimeError("no save received within %.0fs" % timeout)
    finally:
        if not keep:
            try:
                client.disconnect()
            except Exception:
                pass