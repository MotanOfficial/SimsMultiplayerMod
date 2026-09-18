import hashlib
import json
import os
import sys
import tempfile
import unittest

from tools import updater
from tools.updater import (
    apply_changes,
    changed_mod_files,
    fetch_manifest,
    installed_version,
    load_local_manifest,
    mount_runtime,
    plan_update,
    sync,
    validate_manifest,
)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _manifest(version, files):
    return {"version": version, "files": [{"path": p, "sha256": s} for p, s in files]}


class FakeStore(object):
    """Pluggable fetcher: manifests (str) + raw files (bytes) in one URL table."""

    def __init__(self, manifest, files):
        self.manifest = manifest
        self.files = dict(files)
        self.calls = []

    def __call__(self, url, timeout):
        self.calls.append(url)
        if url.endswith("runtime_manifest.json"):
            return json.dumps(self.manifest)
        for path in self.files:
            if url.endswith("/" + path):
                return self.files[path]
        return None


class ManifestTests(unittest.TestCase):
    def test_validate_manifest_ok(self):
        m = _manifest("v1", [("tools/lobby.py", "a" * 64)])
        self.assertIs(validate_manifest(m), m)

    def test_validate_manifest_rejects_malformed(self):
        bad = [
            None,
            3,
            {},
            {"version": "", "files": []},
            {"version": "v1", "files": "x"},
            {"version": "v1", "files": [{"path": "a.py"}]},
            {"version": "v1", "files": [{"path": "", "sha256": "a" * 64}]},
            {"version": "v1", "files": [{"path": "a.py", "sha256": "short"}]},
            {"version": "v1", "files": [{"path": "a.py", "sha256": "a" * 64}, {"path": "a.py", "sha256": "b" * 64}]},
        ]
        for case in bad:
            with self.assertRaises(ValueError):
                validate_manifest(case)

    def test_fetch_manifest_parses_and_rejects(self):
        store = FakeStore(_manifest("v1", [("a.py", "b" * 64)]), {})
        fetcher = store.__call__
        self.assertEqual(fetch_manifest(updater.base_url(), fetcher=fetcher)["version"], "v1")
        bad = FakeStore(_manifest("v1", [("a.py", "x")]), {})
        self.assertIsNone(fetch_manifest(updater.base_url(), fetcher=bad.__call__))
        self.assertIsNone(fetch_manifest(updater.base_url(), fetcher=lambda u, t: None))


class PlanTests(unittest.TestCase):
    def test_plan_update_diffs(self):
        remote = _manifest("v2", [("a.py", "a" * 64), ("b.py", "b" * 64), ("c.py", "c" * 64)])
        local = _manifest("v1", [("a.py", "a" * 64), ("b.py", "zzzz" + "0" * 60)])
        changes = plan_update(remote, local)
        self.assertEqual(changes, [("b.py", "b" * 64), ("c.py", "c" * 64)])

    def test_plan_update_none_local_downloads_all(self):
        remote = _manifest("v1", [("a.py", "a" * 64), ("b.py", "b" * 64)])
        self.assertEqual(len(plan_update(remote, None)), 2)


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="simmp_updater_")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def test_apply_changes_writes_verified_files(self):
        payload = b"hello\n"
        store = FakeStore(_manifest("v1", [("tools/a.py", _sha(b"hello\n"))]), {"tools/a.py": payload})
        ok, errors = apply_changes(updater.base_url(), self.tmp, [("tools/a.py", _sha(payload))], fetcher=store.__call__)
        self.assertTrue(ok)
        self.assertEqual(errors, [])
        with open(os.path.join(self.tmp, "tools", "a.py"), "rb") as handle:
            self.assertEqual(handle.read(), payload)

    def test_apply_changes_checksum_mismatch_aborts_file(self):
        store = FakeStore(_manifest("v1", [("b.py", _sha(b"other"))]), {"b.py": b"actual"})
        ok, errors = apply_changes(
            updater.base_url(),
            self.tmp,
            [("b.py", "f" * 64)],
            fetcher=store.__call__,
        )
        self.assertFalse(ok)
        self.assertTrue(any("checksum" in e for e in errors))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "b.py")))

    def test_apply_changes_missing_download(self):
        store = FakeStore(_manifest("v1", [("gone.py", "e" * 64)]), {})
        ok, errors = apply_changes(
            updater.base_url(),
            self.tmp,
            [("gone.py", "e" * 64)],
            fetcher=store.__call__,
        )
        self.assertFalse(ok)
        self.assertTrue(any("download failed" in e for e in errors))


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="simmp_sync_")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def _tree(self):
        files = {
            "tools/lobby.py": b"A=1\n",
            "protocol/simmp/messages.py": b"FOO=2\n",
        }
        return files

    def test_sync_first_run_downloads_then_noop(self):
        files = self._tree()
        manifest = _manifest("v2026-09-18-a", [(p, _sha(d)) for p, d in files.items()])
        store = FakeStore(manifest, files)
        res = sync(updater.base_url(), self.tmp, fetcher=store.__call__)
        self.assertTrue(res["ok"])
        self.assertEqual(sorted(res["changed"]), sorted(files))
        self.assertEqual(res["version"], "v2026-09-18-a")
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "tools", "lobby.py")))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, updater.VERSION_FILE)))
        local = load_local_manifest(self.tmp)
        self.assertEqual(local["version"], "v2026-09-18-a")

        res2 = sync(updater.base_url(), self.tmp, fetcher=store.__call__)
        self.assertTrue(res2["ok"])
        self.assertEqual(res2["changed"], [])
        self.assertEqual(res2["version"], "v2026-09-18-a")

    def test_sync_updates_only_changed_file(self):
        files = self._tree()
        manifest = _manifest("v-a", [(p, _sha(d)) for p, d in files.items()])
        store = FakeStore(manifest, files)
        self.assertTrue(sync(updater.base_url(), self.tmp, fetcher=store.__call__)["ok"])

        files["tools/lobby.py"] = b"X=99\n"
        new_manifest = _manifest("v-b", [(p, _sha(d)) for p, d in files.items()])
        store2 = FakeStore(new_manifest, files)
        res = sync(updater.base_url(), self.tmp, fetcher=store2.__call__)
        self.assertTrue(res["ok"])
        self.assertEqual(res["changed"], ["tools/lobby.py"])
        self.assertEqual(res["version"], "v-b")
        with open(os.path.join(self.tmp, "tools", "lobby.py"), "rb") as handle:
            self.assertEqual(handle.read(), b"X=99\n")

    def test_sync_offline_leaves_runtime_untouched(self):
        files = self._tree()
        manifest = _manifest("v-a", [(p, _sha(d)) for p, d in files.items()])
        store = FakeStore(manifest, files)
        self.assertTrue(sync(updater.base_url(), self.tmp, fetcher=store.__call__)["ok"])
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "tools", "lobby.py")))

        res = sync(updater.base_url(), self.tmp, fetcher=lambda u, t: None)
        self.assertFalse(res["ok"])
        self.assertIsNotNone(res["error"])
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "tools", "lobby.py")))

    def test_sync_corrupt_file_does_not_publish_manifest(self):
        files = self._tree()
        manifest = _manifest("v-a", [(p, _sha(d)) for p, d in files.items()])
        store = FakeStore(manifest, files)
        self.assertTrue(sync(updater.base_url(), self.tmp, fetcher=store.__call__)["ok"])

        new_files = dict(files)
        new_files["protocol/simmp/messages.py"] = b"CHANGED\n"
        new_manifest = _manifest("v-b", [(p, _sha(d)) for p, d in new_files.items()])
        store2 = FakeStore(new_manifest, {"protocol/simmp/messages.py": b"WRONG"})
        res = sync(updater.base_url(), self.tmp, fetcher=store2.__call__)
        self.assertFalse(res["ok"])
        self.assertTrue(any("checksum" in str(e) for e in [res["error"]]))
        local = load_local_manifest(self.tmp)
        self.assertEqual(local["version"], "v-a")

    def test_installed_version_and_has_runtime(self):
        self.assertEqual(installed_version(self.tmp), "")
        files = self._tree()
        manifest = _manifest("v9", [(p, _sha(d)) for p, d in files.items()])
        sync(updater.base_url(), self.tmp, fetcher=FakeStore(manifest, files).__call__)
        self.assertEqual(installed_version(self.tmp), "v9")
        self.assertTrue(updater.has_runtime(self.tmp))


class MountTests(unittest.TestCase):
    """End-to-end: the runtime finder makes imports resolve from the synced
    tree, not from the working copy."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="simmp_mount_")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        tree = {
            "protocol/simmp/__init__.py": "",
            "protocol/simmp/messages.py": "FOO = 123\n",
            "client_mod/scripts/simmp_client/cc.py": "BAR = 456\n",
            "client_mod/build_script_mod.py": "BAZ = 789\n",
            "server/main.py": "QUX = 'server-main'\n",
            "tools/lobby.py": "def fn():\n    return 42\n",
            "tools/save_metadata.py": "def human_size(n):\n    return '%d bytes' % n\n",
        }
        for rel, content in tree.items():
            full = os.path.join(self.tmp, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as handle:
                handle.write(content)
        self._saved_path = list(sys.path)
        self._saved_modules = dict(sys.modules)
        self._saved_meta = list(sys.meta_path)
        mount_runtime(self.tmp)
        self.finder = None
        for finder in sys.meta_path:
            if getattr(finder, "_simmp_runtime", None) == os.path.abspath(self.tmp):
                self.finder = finder

    def tearDown(self):
        sys.meta_path[:] = [f for f in self._saved_meta]
        for name in set(sys.modules) - set(self._saved_modules):
            del sys.modules[name]
        sys.modules.update(self._saved_modules)
        sys.path[:] = self._saved_path

    def test_finder_installed(self):
        self.assertIsNotNone(self.finder)
        self.assertGreater(mount_runtime(self.tmp), 0)

    def test_runtime_modules_resolve_from_disk(self):
        import simmp.messages  # noqa: F401 - resolved through the finder
        import simmp_client.cc  # noqa: F401
        import build_script_mod  # noqa: F401
        from tools.lobby import fn
        from save_metadata import human_size
        import server.main  # noqa: F401

        self.assertEqual(simmp.messages.FOO, 123)
        self.assertTrue(simmp.messages.__file__.startswith(self.tmp))
        self.assertEqual(simmp_client.cc.BAR, 456)
        self.assertEqual(build_script_mod.BAZ, 789)
        self.assertEqual(server.main.QUX, "server-main")
        self.assertEqual(fn(), 42)
        self.assertEqual(human_size(4), "4 bytes")

    def test_namespace_parent_shadows_listing(self):
        # simmp_client has no __init__.py - a namespace package built from the
        # runtime script root; cc.py must be found there, not from anything
        # bundled or on the working-copy sys.path.
        import simmp_client
        self.assertIn("simmp_client", simmp_client.__name__)
        import simmp_client.cc
        self.assertTrue(simmp_client.cc.__file__.startswith(self.tmp))


class ChangeTrackingTests(unittest.TestCase):
    def test_changed_mod_files(self):
        self.assertTrue(changed_mod_files(["client_mod/scripts/simmp_client/cc.py"]))
        self.assertFalse(changed_mod_files(["server/main.py", "tools/lobby.py"]))


if __name__ == "__main__":
    unittest.main()