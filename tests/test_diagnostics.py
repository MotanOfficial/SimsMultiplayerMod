"""Unit tests for the launcher diagnostics bundler and LAN hand-off (stdlib)."""

import os
import tempfile
import time
import unittest
import zipfile

from tools import diagnostics


class CollectBundleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _file(self, name, data=b"hello\n"):
        path = os.path.join(self._tmp.name, name)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def test_collects_present_files_and_notes_missing_ones(self):
        present = self._file("present.log", b"line\n")
        files = diagnostics.collect_bundle(
            paths={
                "server-log.txt": present,
                "game-client.log": os.path.join(self._tmp.name, "nope.log"),
            },
            info={"runtime version": "test"},
        )
        self.assertEqual(files["server-log.txt"], b"line\n")
        self.assertNotIn("game-client.log", files)
        info = files["info.txt"].decode("utf-8")
        self.assertIn("server-log.txt", info)
        self.assertIn("missing", info)
        self.assertIn("runtime version: test", info)
        self.assertIn("README.txt", files)

    def test_identity_file_is_hashed_not_shipped(self):
        secret = self._file("Sims4Multiplayer.client_id", b"deadbeef" * 4)
        files = diagnostics.collect_bundle(paths={"mod-client-id.sha256.txt": secret})
        body = files["mod-client-id.sha256.txt"].decode("utf-8")
        self.assertTrue(body.startswith("sha256="))
        self.assertNotIn("deadbeef", body)

    def test_launcher_log_is_included_when_given(self):
        files = diagnostics.collect_bundle(
            paths={}, launcher_log=["20:00 first", "20:01 second"]
        )
        text = files["launcher-log.txt"].decode("utf-8")
        self.assertIn("20:00 first", text)
        self.assertIn("20:01 second", text)

    def test_read_capped_truncates_and_reports(self):
        big = self._file("big.log", b"x" * 5000)
        data, note = diagnostics._read_capped(big, limit=1000)
        self.assertEqual(len(data), 1000)
        self.assertIn("truncated", note)
        data, note = diagnostics._read_capped(big, limit=6000)
        self.assertEqual(len(data), 5000)
        self.assertNotIn("truncated", note)

    def test_read_capped_missing_file(self):
        data, note = diagnostics._read_capped(os.path.join(self._tmp.name, "gone.log"))
        self.assertIsNone(data)
        self.assertEqual(note, "missing")


class WriteBundleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_zip_contents_and_name(self):
        path = diagnostics.write_bundle(
            {"README.txt": b"hi", "info.txt": b"there"}, self._tmp.name, stamp=0
        )
        self.assertTrue(path.endswith(".zip"))
        self.assertTrue(os.path.basename(path).startswith("Sims4Multiplayer-diagnostics-"))
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(sorted(archive.namelist()), ["README.txt", "info.txt"])
            self.assertEqual(archive.read("README.txt"), b"hi")

    def test_explicit_name_is_used(self):
        path = diagnostics.write_bundle({"a.txt": b"x"}, self._tmp.name, name="mine.zip")
        self.assertEqual(os.path.basename(path), "mine.zip")


class ReceiverPortTests(unittest.TestCase):
    def test_offset_and_junk(self):
        self.assertEqual(diagnostics.receiver_port(8765), 8766)
        self.assertEqual(diagnostics.receiver_port("9000"), 9001)
        self.assertEqual(diagnostics.receiver_port(None), 8766)
        self.assertEqual(diagnostics.receiver_port("nope"), 8766)


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.received = []
        self.receiver = diagnostics.DiagnosticsReceiver(
            0,
            self._tmp.name,
            on_received=lambda path, meta: self.received.append((path, meta)),
            host="127.0.0.1",
        )
        self.assertTrue(self.receiver.start())
        self.addCleanup(self.receiver.stop)

    def _wait_for_received(self, count=1, timeout=8.0):
        deadline = time.time() + timeout
        while time.time() < deadline and len(self.received) < count:
            time.sleep(0.05)
        return len(self.received) >= count

    def test_ping_answers(self):
        self.assertTrue(
            diagnostics.ping_receiver("127.0.0.1", self.receiver.actual_port, timeout=5.0)
        )

    def test_upload_round_trip_stores_and_reports(self):
        bundle = diagnostics.write_bundle(
            {"README.txt": b"contents"}, self._tmp.name, name="send.zip"
        )
        ok, detail = diagnostics.send_bundle(
            bundle, "127.0.0.1", self.receiver.actual_port, name="Laptop", role="join"
        )
        self.assertTrue(ok, detail)
        self.assertTrue(self._wait_for_received(), "receiver callback never fired")
        path, meta = self.received[0]
        self.assertTrue(os.path.isfile(path))
        self.assertIn("Laptop", meta["name"])
        self.assertEqual(meta["role"], "join")
        self.assertIn("join", os.path.basename(path))
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(archive.read("README.txt"), b"contents")

    def test_oversize_upload_is_rejected(self):
        small = diagnostics.DiagnosticsReceiver(
            0, self._tmp.name, host="127.0.0.1", max_bytes=16
        )
        self.assertTrue(small.start())
        self.addCleanup(small.stop)
        bundle = diagnostics.write_bundle(
            {"big.txt": b"x" * 500}, self._tmp.name, name="big.zip"
        )
        ok, detail = diagnostics.send_bundle(
            bundle, "127.0.0.1", small.actual_port, timeout=10.0
        )
        self.assertFalse(ok)
        self.assertIn("413", detail)
        self.assertEqual(self.received, [])

    def test_port_in_use_reports_failure(self):
        second = diagnostics.DiagnosticsReceiver(
            self.receiver.actual_port, self._tmp.name, host="127.0.0.1"
        )
        self.assertFalse(second.start(), "binding a busy port must fail cleanly")


class SendBundleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_missing_host(self):
        ok, detail = diagnostics.send_bundle("x.zip", "", 8766)
        self.assertFalse(ok)
        self.assertIn("no host address", detail)

    def test_bad_port(self):
        ok, detail = diagnostics.send_bundle("x.zip", "127.0.0.1", "nope")
        self.assertFalse(ok)
        self.assertIn("bad port", detail)

    def test_unreachable_host(self):
        bundle = diagnostics.write_bundle({"a.txt": b"x"}, self._tmp.name, name="z.zip")
        ok, detail = diagnostics.send_bundle(bundle, "127.0.0.1", 59999, timeout=3.0)
        self.assertFalse(ok)
        self.assertIn("could not reach", detail)

    def test_missing_file(self):
        ok, detail = diagnostics.send_bundle(
            os.path.join(self._tmp.name, "nope.zip"), "127.0.0.1", 8766, timeout=3.0
        )
        self.assertFalse(ok)
        self.assertIn("cannot read bundle", detail)

