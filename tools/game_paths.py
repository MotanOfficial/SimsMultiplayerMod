"""Autodetect The Sims 4 install + user-data paths (stdlib only, testable).

Pure functions with injected roots so the tests can point them at temp
directories. Used by the launcher so a first-time user never has to know
where the game keeps its Mods/saves folders:

- ``ts4_user_folder``: ``Documents/Electronic Arts/The Sims 4`` (handles
  the OneDrive-redirected Documents).
- ``mods_folder`` / ``saves_folder``: the two subfolders the mod needs.
- ``game_executable``: the ``TS4_x64.exe`` run target, looked up in the
  EA-app, Origin and Steam default install locations (plus the Maxis
  registry key ``Install Dir``).
"""

import ctypes
import glob
import os
import sys

WOW64_KEYS = (r"SOFTWARE\WOW6432Node\Maxis\The Sims 4", r"SOFTWARE\Maxis\The Sims 4")
DOCUMENTS_SUBKEYS = (
    "Personal",
    r"Personal",
)
INSTALL_VALUE_NAME = "Install Dir"
EA_GAME_EXE_NAME = "TS4_x64.exe"

STEAM_APPS = [
    r"C:\Program Files (x86)\Steam\steamapps\common\The Sims 4",
    r"C:\Program Files\Steam\steamapps\common\The Sims 4",
]
EA_APPS = [
    r"C:\Program Files\EA Games\The Sims 4",
    r"C:\Program Files (x86)\EA Games\The Sims 4",
]
ORIGIN_APPS = [
    r"C:\Program Files (x86)\Origin Games\The Sims 4",
    r"C:\Program Files\Origin Games\The Sims 4",
]
GAME_BIN_SUBDIRS = (
    os.path.join("Game", "Bin"),
    os.path.join("Game", "Bin", "Win32"),
)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def _winreg_module(registry):
    if registry is not None:
        return registry
    try:
        import winreg as _winreg  # noqa: PLC0415

        return _winreg
    except Exception:
        return None


def _registry_install_dirs(registry=None):
    """Read the Maxis 'Install Dir' value from the registry, if present.

    ``registry`` is a test-only injectable module exposing ``OpenKey``/
    ``QueryValueEx``/``HKEY_LOCAL_MACHINE`` and a ``CloseKey``; it must also
    define the ``error`` exception. Windows-only; returns [] elsewhere.
    """
    reg = _winreg_module(registry)
    if reg is None:
        return []
    dirs = []
    hive = getattr(reg, "HKEY_LOCAL_MACHINE", None)
    if hive is None:
        return dirs
    for key in WOW64_KEYS:
        handle = None
        try:
            handle = reg.OpenKey(hive, key)
        except Exception:
            continue
        try:
            try:
                value, _kind = reg.QueryValueEx(handle, INSTALL_VALUE_NAME)
            except Exception:
                continue
            if isinstance(value, str) and value.strip():
                dirs.append(os.path.abspath(value.strip()))
        finally:
            try:
                reg.CloseKey(handle)
            except Exception:
                pass
    return dirs


def _documents_folders():
    """Candidate user-Documents folders, most likely first.

    The Sims 4 keeps user data under ``Documents/Electronic Arts/The Sims 4``.
    On machines with OneDrive Documents redirection the plain
    ``~/Documents`` path is wrong, so OneDrive variants are tried first.
    """
    candidates = []
    try:
        profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    except Exception:
        profile = None
    one_drive = os.environ.get("OneDrive")
    one_drive_consumer = os.environ.get("OneDriveConsumer")
    for root in (one_drive, one_drive_consumer, profile):
        if not root:
            continue
        candidates.append(os.path.join(root, "Documents"))
    if profile:
        candidates.append(os.path.join(profile, "Documents"))
    return _dedupe(os.path.abspath(path) for path in candidates)


def _dedupe(paths):
    seen = set()
    out = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        out.append(path)
    return out


def ts4_user_folder(existing_only=True, docs=None):
    """Find ``Documents/Electronic Arts/The Sims 4`` (first that exists).

    ``docs`` is a test-only injectable list of Documents roots. When
    ``existing_only`` is False the first *path* is returned even if the
    folder does not exist yet (the game creates it on first launch).
    """
    folders = []
    for documents in docs or _documents_folders():
        candidate = os.path.join(documents, "Electronic Arts", "The Sims 4")
        if os.path.isdir(candidate):
            return candidate
        folders.append(candidate)
    if not existing_only and folders:
        return folders[0]
    return None


def mods_folder(user_folder=None):
    path = os.path.join(user_folder or ts4_user_folder() or "", "Mods")
    return path if os.path.isdir(path) else None


def saves_folder(user_folder=None):
    path = os.path.join(user_folder or ts4_user_folder() or "", "saves")
    return path if os.path.isdir(path) else None


def _find_exe_under(install_dirs):
    for install in _as_list(install_dirs):
        for sub in GAME_BIN_SUBDIRS:
            candidate = os.path.join(install, sub, EA_GAME_EXE_NAME)
            if os.path.isfile(candidate):
                return candidate
    return None


def game_executable(roots=None, registry=None, search_defaults=True):
    """Locate ``TS4_x64.exe``.

    ``roots`` injectable list of install roots (test override). Checks, in
    order: injected roots, registry ``Install Dir``, EA-app defaults, Origin
    defaults, Steam defaults. Returns the absolute exe path or None.
    """
    sources = []
    sources += _as_list(roots)
    sources += _as_list(_registry_install_dirs(registry))
    if search_defaults:
        sources += _as_list(EA_APPS)
        sources += _as_list(ORIGIN_APPS)
        sources += _as_list(STEAM_APPS)
    return _find_exe_under(_dedupe(sources))


def install_folder(roots=None, registry=None, search_defaults=True):
    """Return just the install folder (dir containing Game/Bin) or None."""
    exe = game_executable(roots=roots, registry=registry, search_defaults=search_defaults)
    if not exe:
        return None
    return os.path.dirname(os.path.dirname(os.path.dirname(exe)))


def steam_game_id():
    """The Steam AppID for The Sims 4 (used as a launch fallback)."""
    return "1222671"


def open_folder(path):
    """Open a folder in Explorer (Windows). Best-effort."""
    if not path:
        return False
    try:
        if os.name == "nt":
            os.startfile(path)  # noqa: 601 (windows only) pylint: disable=no-member
        else:
            from subprocess import Popen  # noqa: PLC0415

            Popen(["xdg-open", path])
        return True
    except Exception:
        return False