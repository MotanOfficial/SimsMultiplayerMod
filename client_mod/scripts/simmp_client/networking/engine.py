"""Threaded socket networking engine for the client mod.

The Sims 4 game's embedded Python ships no `asyncio`, so this engine drives a
raw blocking TCP socket on a background daemon thread. The public surface
matches the previous asyncio engine exactly, so the rest of the client code is
unchanged:

- The engine thread owns the socket and the read loop. The read loop is
  `select`-based, so it also serves the heartbeat and notices reconnect
  requests / stop within a fraction of a second without blocking forever.
- The game thread calls `drain()` to pull inbound frames and `send_message()`
  to push outbound bytes (blocking `sendall` under a lock - small frames,
  fine on the game thread).
- The engine thread survives disconnects and reconnects, so `reconnect()`
  works from `CONNECTED` and `DISCONNECTED` (required by client-side
  auto-reconnect with backoff).
- The socket is handed to the game thread / locked; no game imports here.
"""

import collections
import select
import socket
import threading
import time

try:
    import logging as _logging
except ImportError:  # pragma: no cover - the game's embedded Python may omit it
    _logging = None

from simmp import framing, messages as msg
from simmp.constants import MAX_FRAME_BYTES


class _NullLogger:
    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def exception(self, *args, **kwargs):
        pass


def _make_logger(name):
    if _logging is None:
        return _NullLogger()
    return _logging.getLogger(name)


class EngineState:
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2


class ClientEngine:
    def __init__(
        self,
        host,
        port,
        client_name="Sims4Player",
        client_version="0.1.0",
        client_id=None,
        on_message=None,
        heartbeat_interval=5.0,
        connect_timeout=10.0,
        frame_limit=MAX_FRAME_BYTES,
        pending_limit=64,
        logger=None,
    ):
        self._host = host
        self._port = port
        self._client_name = client_name
        self._client_version = client_version
        self._client_id = client_id
        self._on_message = on_message
        self._heartbeat_interval = heartbeat_interval
        self._connect_timeout = connect_timeout
        self._frame_limit = frame_limit
        self._pending_limit = pending_limit
        self.logger = logger or _make_logger("simmp.client.net")

        self._recv = collections.deque()
        self._recv_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._pending_lock = threading.Lock()
        self._state = EngineState.DISCONNECTED
        self._stopped = False
        self._thread = None
        self._sock = None
        self._connected_evt = threading.Event()
        self._reconnect_requested = False
        self._seq = 0
        self._pending = {}

    @property
    def state(self):
        return self._state

    @property
    def connected(self):
        return self._state == EngineState.CONNECTED

    @property
    def stopped(self):
        return self._stopped

    @property
    def peer(self):
        return (self._host, self._port)

    @property
    def client_id(self):
        return self._client_id

    @property
    def pending(self):
        with self._pending_lock:
            return dict(sorted(self._pending.items()))

    @property
    def pending_count(self):
        with self._pending_lock:
            return len(self._pending)

    @property
    def next_seq(self):
        return self._seq + 1

    def connect(self, timeout=None):
        if self._state != EngineState.DISCONNECTED or self._stopped:
            return False
        timeout = timeout if timeout is not None else self._connect_timeout
        self._connected_evt = threading.Event()
        self._thread = threading.Thread(target=self._run, name="simmp-engine", daemon=True)
        self._thread.start()
        if not self._connected_evt.wait(timeout):
            self.stop()
            return False
        return self._state == EngineState.CONNECTED

    def send_message(self, message):
        if self._state != EngineState.CONNECTED or self._sock is None:
            return False
        payload = self._encode(message)
        if payload is None:
            return False
        try:
            with self._send_lock:
                self._sock.sendall(payload)
            return True
        except Exception:
            return False

    def send_event(self, event_type, data=None):
        if self._state != EngineState.CONNECTED or self._sock is None:
            return False
        self._seq += 1
        seq = self._seq
        message = msg.make_event(event_type, data, seq=seq)
        with self._pending_lock:
            if len(self._pending) >= self._pending_limit:
                oldest = next(iter(sorted(self._pending)))
                self._pending.pop(oldest, None)
                self.logger.warning("[MP][ERROR] pending queue overflow, dropped seq %s", oldest)
            self._pending[seq] = message
        if not self.send_message(message):
            with self._pending_lock:
                self._pending.pop(seq, None)
            return False
        return seq

    def send_presence(self, zone_id, lot_id, timestamp=None):
        return self.send_message(msg.make_presence(zone_id, lot_id, timestamp))

    def send_join_room(self, room_id):
        return self.send_message(msg.make_join_room(room_id))

    def send_travel_request(self, zone_id):
        return self.send_message(msg.make_travel_request(zone_id))

    def send_travel_response(self, request_id, accepted, reason=None):
        return self.send_message(msg.make_travel_response(accepted, reason=reason, request_id_value=request_id))

    def send_travel_ready(self, zone_id, request_id):
        return self.send_message(msg.make_travel_ready(zone_id, request_id_value=request_id))

    def send_clock_sync(self, zone_id, absolute_ticks, real_time, clock_speed):
        return self.send_message(msg.make_clock_sync(zone_id, absolute_ticks, real_time, clock_speed))

    def send_time_ready(self, zone_id):
        return self.send_message(msg.make_time_ready(zone_id))

    def send_time_speed(self, speed, ticks=None):
        return self.send_message(msg.make_time_speed(speed, ticks=ticks))

    def send_object_update(self, objects, zone_id=None):
        """`objects` is [{"key": str, "fields": {...}, "rev": int}]."""
        return self.send_message(msg.make_object_update(objects, zone_id=zone_id))

    def send_object_claim(self, key, zone_id=None):
        return self.send_message(msg.make_object_claim(key, zone_id=zone_id))

    def send_object_release(self, key, zone_id=None):
        return self.send_message(msg.make_object_release(key, zone_id=zone_id))

    def send_interaction_request(self, object_key, interaction, args=None, affordance=None, affordance_id=None, target=None, zone_id=None):
        return self.send_message(
            msg.make_interaction_request(
                object_key,
                interaction,
                args,
                affordance=affordance,
                affordance_id=affordance_id,
                target=target,
                zone_id=zone_id,
            )
        )

    def send_interaction_end(self, object_key, zone_id=None):
        return self.send_message(msg.make_interaction_end(object_key, zone_id=zone_id))

    def send_save_push(self, slot, seq, total, size, data):
        return self.send_message(msg.make_save_push(slot, seq, total, size, data))

    def send_save_request(self):
        return self.send_message(msg.make_save_request())

    def reconnect(self):
        """Re-establish the connection in place, resending un-acked events.

        Works from `CONNECTED` (clean re-HELLO) and from `DISCONNECTED`
        (the previous connection died but the engine thread is still alive),
        which is what feeds client-side auto-reconnect with backoff.
        """
        if self._stopped or self._thread is None or not self._thread.is_alive():
            return False
        if self._state not in (EngineState.CONNECTED, EngineState.DISCONNECTED):
            return False
        self._reconnect_requested = True
        return True

    def drain(self):
        with self._recv_lock:
            messages = list(self._recv)
            self._recv.clear()
        return messages

    def stop(self):
        if self._stopped and (self._thread is None or not self._thread.is_alive()):
            return
        self._stopped = True
        self._close_socket()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread() and thread.is_alive():
            thread.join(timeout=5.0)
        self._state = EngineState.DISCONNECTED
        self._thread = None
        self._connected_evt.set()

    def _run(self):
        # One lifecycle per connection; the thread stays alive across drops so
        # `reconnect()` keeps working, and exits only on `stop()`.
        while not self._stopped:
            # A reconnect request is consumed at the start of each cycle. If it
            # arrived while the previous read loop was still up, `_read_loop`
            # breaks out and we circle back immediately; if it arrived while we
            # were waiting below, `_wait_for_action()` swallowed it and this
            # top-of-loop clear just makes the fresh cycle read normally.
            self._reconnect_requested = False
            self._state = EngineState.CONNECTING
            sock = self._open_socket()
            if sock is not None:
                self._sock = sock
                self._state = EngineState.CONNECTED
                self._connected_evt.set()
                self.logger.info("[MP][NET] Connected to %s:%s", self._host, self._port)
                try:
                    self._send_frame(
                        msg.make_hello(self._client_name, self._client_version, client_id=self._client_id)
                    )
                    self._resend_pending()
                    self._read_loop(sock)
                finally:
                    self._close_socket()
                self._state = EngineState.DISCONNECTED
            else:
                # The event must fire on failure too, so a `connect()` waiter
                # unblocks and can return False.
                self._state = EngineState.DISCONNECTED
                self._connected_evt.set()
            if self._reconnect_requested:
                continue
            if not self._wait_for_action():
                break
        self._state = EngineState.DISCONNECTED

    def _open_socket(self):
        try:
            sock = socket.create_connection((self._host, self._port), timeout=self._connect_timeout)
            sock.settimeout(None)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            return sock
        except Exception as exc:
            self.logger.info("[MP][NET] Connect failed: %s", exc)
            return None

    def _wait_for_action(self):
        while not self._stopped:
            if self._reconnect_requested:
                return True
            time.sleep(0.05)
        return False

    def _read_loop(self, sock):
        decoder = framing.FrameDecoder(limit=self._frame_limit)
        next_heartbeat = time.time() + self._heartbeat_interval
        while not self._stopped and not self._reconnect_requested:
            now = time.time()
            if now >= next_heartbeat:
                next_heartbeat = now + self._heartbeat_interval
                try:
                    self._send_frame(msg.make_ping())
                except Exception:
                    break
            try:
                readable, _, _ = select.select([sock], [], [], 0.25)
            except (OSError, ValueError):
                break
            if not readable:
                continue
            try:
                chunk = sock.recv(65536)
            except (socket.timeout, OSError):
                break
            if not chunk:
                self.logger.info("[MP][NET] Server closed the connection")
                break
            try:
                frames = decoder.feed(chunk)
            except framing.FrameError as exc:
                self.logger.warning("[MP][ERROR] Malformed frame from server: %s", exc)
                break
            for frame in frames:
                self._track_ack(frame)
                with self._recv_lock:
                    self._recv.append(frame)
                if self._on_message is not None:
                    try:
                        self._on_message(frame)
                    except Exception:
                        self.logger.exception("[MP][ERROR] on_message callback failed")

    def _track_ack(self, frame):
        if frame.get("type") != "EVENT_ACK":
            return
        seq = frame.get("payload", {}).get("seq")
        with self._pending_lock:
            if seq in self._pending:
                self._pending.pop(seq, None)
                self.logger.debug("[MP][NET] EVENT seq %s acked (%s pending)", seq, len(self._pending))

    def _resend_pending(self):
        with self._pending_lock:
            pending = dict(sorted(self._pending.items()))
        for seq in sorted(pending):
            message = pending[seq]
            try:
                self._send_frame(message)
                self.logger.info("[MP][NET] Resent EVENT seq %s after reconnect", seq)
            except Exception as exc:
                self.logger.info("[MP][ERROR] Failed to resend EVENT seq %s: %s", seq, exc)

    def _encode(self, message):
        try:
            return framing.encode(message, limit=self._frame_limit)
        except framing.FrameError as exc:
            self.logger.warning("[MP][ERROR] %s", exc)
            return None

    def _send_frame(self, message):
        payload = self._encode(message)
        if payload is None:
            return
        sock = self._sock
        if sock is None:
            raise OSError("no socket")
        with self._send_lock:
            sock.sendall(payload)

    def _close_socket(self):
        with self._send_lock:
            sock = self._sock
            self._sock = None
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass