"""Tests for game-path autodetection used by the launcher."""

import os
import unittest

from tools import game_paths


def _make_tree(base, *relpaths):
    """Create a marker file under base for each relative path (dirs auto-made)."""
    for rel in relpaths:
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(b"x")
    return base


class DocumentsTests(unittest.TestCase):
    def test_ts4_user_folder_prefers_first_existing(self):
        import tempfile

        tmp = tempfile.mkdtemp()
        docs1 = os.path.join(tmp, "D1")
        docs2 = os.path.join(tmp, "D2")
        # only docs2 has the TS4 folder
        _make_tree(docs2, os.path.join("Electronic Arts", "The Sims 4", "slot.save"))
        found = game_paths.ts4_user_folder(docs=[docs1, docs2])
        self.assertEqual(
            os.path.normpath(found),
            os.path.normpath(os.path.join(docs2, "Electronic Arts", "The Sims 4")),
        )

    def test_ts4_user_folder_returns_first_even_if_missing(self):
        import tempfile

        tmp = tempfile.mkdtemp()
        docs1 = os.path.join(tmp, "D1")
        found = game_paths.ts4_user_folder(docs=[docs1], existing_only=False)
        self.assertEqual(
            os.path.normpath(found),
            os.path.normpath(os.path.join(docs1, "Electronic Arts", "The Sims 4")),
        )

    def test_mods_and_saves_folders(self):
        import tempfile

        tmp = tempfile.mkdtemp()
        user = os.path.join(tmp, "Electronic Arts", "The Sims 4")
        _make_tree(
            user,
            os.path.join("Mods", "keep.txt"),
            os.path.join("saves", "keep.txt"),
            os.path.join("Other", "keep.txt"),
        )
        self.assertEqual(game_paths.mods_folder(user_folder=user), os.path.join(user, "Mods"))
        self.assertEqual(game_paths.saves_folder(user_folder=user), os.path.join(user, "saves"))
        missing = os.path.join(tmp, "missing", "user")
        self.assertIsNone(game_paths.mods_folder(user_folder=missing))


class FakeRegistry:
    """winreg stand-in: OpenKey(hive, key) -> per-key dict of name->(value,kind)."""

    HKEY_LOCAL_MACHINE = 42

    def __init__(self):
        self._rows = {}

    def set(self, key, name, value, kind=1):
        self._rows.setdefault(key, {})[name] = (value, kind)

    def OpenKey(self, hive, key):  # noqa: N802
        if key not in self._rows:
            raise OSError("not found")
        return key

    def QueryValueEx(self, handle, name):  # noqa: N802
        return self._rows[handle][name]

    def CloseKey(self, handle):  # noqa: N802
        return None


class ExeTests(unittest.TestCase):
    def _exe(self, install):
        return os.path.join(install, "Game", "Bin", "TS4_x64.exe")

    def test_prefers_injected_roots(self):
        import tempfile

        tmp = tempfile.mkdtemp()
        a = os.path.join(tmp, "A")
        b = os.path.join(tmp, "B")
        _make_tree(a, os.path.join("Game", "Bin", "TS4_x64.exe"))
        found = game_paths.game_executable(roots=[a, b])
        self.assertEqual(os.path.normpath(found), os.path.normpath(self._exe(a)))

    def test_injected_roots_win_over_defaults(self):
        import tempfile

        tmp = tempfile.mkdtemp()
        a = os.path.join(tmp, "custom")
        _make_tree(a, os.path.join("Game", "Bin", "TS4_x64.exe"))
        # A default steam path that does not exist must not shadow an existing
        # injected root even though it would sort before it.
        found = game_paths.game_executable(roots=[a])
        self.assertEqual(os.path.normpath(found), os.path.normpath(self._exe(a)))

    def test_registry_install_dir_used(self):
        import tempfile

        tmp = tempfile.mkdtemp()
        install = os.path.join(tmp, "reg")
        _make_tree(install, os.path.join("Game", "Bin", "TS4_x64.exe"))
        reg = FakeRegistry()
        for key in game_paths.WOW64_KEYS:
            reg.set(key, game_paths.INSTALL_VALUE_NAME, "not-a-dir")
        reg.set(game_paths.WOW64_KEYS[0], game_paths.INSTALL_VALUE_NAME, install)
        found = game_paths.game_executable(registry=reg)
        self.assertEqual(os.path.normpath(found), os.path.normpath(self._exe(install)))

    def test_registry_missing_returns_none(self):
        reg = FakeRegistry()
        self.assertIsNone(game_paths.game_executable(registry=reg))

    def test_no_exe_returns_none(self):
        self.assertIsNone(
            game_paths.game_executable(
                roots=["C:\\definitely\\missing"], registry=FakeRegistry(), search_defaults=False
            )
        )

    def test_install_folder(self):
        import tempfile

        tmp = tempfile.mkdtemp()
        a = os.path.join(tmp, "A")
        _make_tree(a, os.path.join("Game", "Bin", "TS4_x64.exe"))
        self.assertEqual(os.path.normpath(game_paths.install_folder(roots=[a])),
                         os.path.normpath(a))

    def test_steam_id(self):
        self.assertEqual(game_paths.steam_game_id(), "1222671")


if __name__ == "__main__":
    unittest.main()