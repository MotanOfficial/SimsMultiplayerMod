import os
import re
import tempfile
import unittest

from simmp_client.logfile import FileLog


class FileLogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._path = os.path.join(self._tmp.name, "client.log")

    def tearDown(self):
        self._tmp.cleanup()

    def _read(self):
        with open(self._path, "r", encoding="utf-8") as handle:
            return handle.read()

    def test_appends_lines(self):
        log = FileLog(self._path)
        log.write("[MP][NET] one")
        log.write("[MP][NET] two")
        lines = self._read().splitlines()
        self.assertEqual(len(lines), 2)
        for line, suffix in zip(lines, ("[MP][NET] one", "[MP][NET] two")):
            # Every file line is prefixed with a wall-clock timestamp.
            self.assertRegex(line, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} " + re.escape(suffix) + "$")

    def test_creates_parent_directory(self):
        nested = os.path.join(self._tmp.name, "a", "b", "client.log")
        FileLog(nested).write("x")
        self.assertTrue(os.path.isfile(nested))

    def test_truncates_when_over_cap(self):
        log = FileLog(self._path, max_bytes=200)
        for i in range(100):
            log.write("line %03d padding to force rotation" % i)
        contents = self._read()
        self.assertLessEqual(len(contents.encode("utf-8")), 200)
        self.assertIn("line 099", contents)

    def test_write_never_raises_on_bad_path(self):
        FileLog(os.path.join(self._tmp.name, "\0bad")).write("ignored")
