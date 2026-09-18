"""End-to-end tests for the launcher lobby machinery (tools/lobby)."""

import os
import shutil
import tempfile
import threading
import time
import unittest

from tools import lobby


def _wait(predicate, timeout=10.0, interval=0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class LanIpTests(unittest.TestCase):
    def test_find_lan_ip_returns_string(self):
        ip = lobby.find_lan_ip()
        self.assertIsInstance(ip, str)
        # '' means "not found" but any returning value must look like an IP
        if ip:
            parts = ip.split(".")
            self.assertEqual(len(parts), 4)

    def test_all_lan_ips_are_unique_valid_ipv4(self):
        ips = lobby.all_lan_ips()
        self.assertIsInstance(ips, list)
        self.assertEqual(len(ips), len(set(ips)), "duplicated addresses")
        for ip in ips:
            parts = ip.split(".")
            self.assertEqual(len(parts), 4)
            for part in parts:
                self.assertTrue(part.isdigit() and 0 <= int(part) <= 255)
        # the default-route address must be included when it is known
        default = lobby.find_lan_ip()
        if default:
            self.assertIn(default, ips)

    def test_all_lan_ips_no_loopback(self):
        for ip in lobby.all_lan_ips():
            self.assertFalse(ip.startswith("127."))


class ServerHandleTests(unittest.TestCase):
    def test_start_stop_and_status_callback(self):
        tmp = tempfile.mkdtemp()
        status_file = os.path.join(tmp, "status.json")
        got = []
        handle = lobby.ServerHandle("127.0.0.1", 0, status_file=status_file, on_status=got.append)
        self.assertTrue(handle.start())
        self.assertTrue(_wait(lambda: handle.actual_port > 0))
        self.assertTrue(handle.thread_alive())
        self.assertTrue(_wait(lambda: bool(got)))
        status = got[-1]
        self.assertIn("players", status)
        # a second start while running is refused (single server per handle)
        self.assertFalse(handle.start())
        handle.stop()
        self.assertFalse(handle.thread_alive())
        # a stopped handle can be restarted on a fresh port
        self.assertTrue(handle.start())
        handle.stop()

    def test_start_conflict_returns_false(self):
        a = lobby.ServerHandle("127.0.0.1", 0)
        self.assertTrue(a.start())
        self.assertTrue(_wait(lambda: a.actual_port > 0))
        try:
            b = lobby.ServerHandle("127.0.0.1", a.actual_port)
            self.assertFalse(b.start())
        finally:
            a.stop()
            b.stop()


class PushAndReceiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.save_dir = os.path.join(self.tmp, "saves")
        os.makedirs(self.save_dir)
        self._env_backup = os.environ.get("SIM4_MP_SAVE_ROOT")
        # game_hooks._save_roots() appends "saves" to this var -> point at profile root
        os.environ["SIM4_MP_SAVE_ROOT"] = self.tmp
        self.server = lobby.ServerHandle("127.0.0.1", 0)
        self.assertTrue(self.server.start())
        self.assertTrue(_wait(lambda: self.server.actual_port > 0))

    def tearDown(self):
        self.server.stop()
        if self._env_backup is None:
            os.environ.pop("SIM4_MP_SAVE_ROOT", None)
        else:
            os.environ["SIM4_MP_SAVE_ROOT"] = self._env_backup
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_save(self, name="slot_00000001.save", size=512 * 1024):
        path = os.path.join(self.save_dir, name)
        with open(path, "wb") as handle:
            handle.write(b"Z" * size)
        return path

    def test_push_reaches_connected_player(self):
        slot = "multi_chunk_%d.save" % os.getpid()
        payload = os.urandom(3 * 512 * 1024 + 137)
        source = os.path.join(self.save_dir, slot)
        with open(source, "wb") as handle:
            handle.write(payload)
        received = {}

        def joiner():
            received["result"] = lobby.receive_save_file(
                "127.0.0.1", self.server.actual_port, timeout=25.0
            )

        thread = threading.Thread(target=joiner, daemon=True)
        thread.start()
        # let the joiner connect and register before pushing
        time.sleep(1.0)
        ok, reached = lobby.push_save_file(source, "127.0.0.1", self.server.actual_port)
        self.assertTrue(ok)
        self.assertEqual(reached, 1)
        thread.join(timeout=25.0)
        self.assertFalse(thread.is_alive(), "joiner never completed the multi-chunk save")
        got_slot, path = received["result"]
        self.assertEqual(got_slot, slot)
        self.assertTrue(os.path.isfile(path), "multi-chunk save was never written")
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), payload, "joiner received a truncated/bad save")

    def test_push_solo_reaches_zero(self):
        source = self._write_save()
        ok, reached = lobby.push_save_file(source, "127.0.0.1", self.server.actual_port)
        self.assertTrue(ok)
        self.assertEqual(reached, 0)

    def test_late_joiner_gets_save_shared_before_connect(self):
        # Regression: the host shared while nobody was connected (reached=0).
        # A joiner who connects afterwards must still receive the save via the
        # server's cached replay (SAVE_REQUEST), instead of hanging forever.
        slot = "late_join_%d.save" % os.getpid()
        with open(os.path.join(self.save_dir, slot), "wb") as handle:
            handle.write(b"W")
        source = self._write_save(name=slot, size=1024 * 1024 + 3)
        ok, reached = lobby.push_save_file(source, "127.0.0.1", self.server.actual_port)
        self.assertTrue(ok)
        self.assertEqual(reached, 0, "no peer was connected at push time")
        received = {}

        def joiner():
            received["result"] = lobby.receive_save_file(
                "127.0.0.1", self.server.actual_port, timeout=20.0
            )

        thread = threading.Thread(target=joiner, daemon=True)
        thread.start()
        thread.join(timeout=20.0)
        self.assertFalse(thread.is_alive(), "late joiner never received the cached save")
        got_slot, path = received["result"]
        self.assertEqual(got_slot, slot)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(os.path.dirname(path), self.save_dir)
        self.assertTrue(os.path.getsize(path) == 1024 * 1024 + 3, "cached replay was truncated")

    def test_receive_save_lands_in_saves_folder(self):
        slot = "lobby_test_%d.save" % os.getpid()
        # real flow: the client already owns that slot -> prefer_slot resolves
        # the temp saves folder deterministically instead of scoring by count
        with open(os.path.join(self.save_dir, slot), "wb") as handle:
            handle.write(b"W")
        source = self._write_save(name=slot, size=1024 * 1024 + 7000)
        received = {}

        def joiner():
            received["result"] = lobby.receive_save_file(
                "127.0.0.1", self.server.actual_port, timeout=20.0
            )

        thread = threading.Thread(target=joiner, daemon=True)
        thread.start()
        # let the joiner connect and register before pushing
        time.sleep(1.0)
        ok, reached = lobby.push_save_file(source, "127.0.0.1", self.server.actual_port)
        self.assertTrue(ok)
        thread.join(timeout=20.0)
        self.assertFalse(thread.is_alive(), "receive_save_file never returned")
        got_slot, path = received["result"]
        self.assertEqual(got_slot, slot)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(os.path.dirname(path), self.save_dir)
        self.assertTrue(reached >= 1)
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"Z" * (1024 * 1024 + 7000), "save was truncated on disk")


if __name__ == "__main__":
    unittest.main()