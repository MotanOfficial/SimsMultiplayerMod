"""Shared launcher constants, settings helpers, and deferred runtime loading.

Stdlib-only so it can be imported by the PySide6 bridge, the selftest path,
and the frozen bootstrap without pulling in Qt.
"""

import json
import os
import sys

ROOT = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

try:
    from tools import updater
except ImportError:  # pragma: no cover - dev fallback when the run dir differs
    import updater  # type: ignore

CODE_ROOT = updater.runtime_data_root()

RUNTIME_DIR = os.path.join(os.environ.get("TEMP") or os.path.expanduser("~"), "simmp-launcher")
STATUS_FILE = os.path.join(RUNTIME_DIR, "status.json")
SERVER_LOG_FILE = os.path.join(RUNTIME_DIR, "server.log")
SETTINGS_FILE = os.path.join(RUNTIME_DIR, "settings.json")
DEFAULT_PORT = 8765

MUTED = "#8f97a5"
ACCENT = "#4f8cff"
GREEN = "#3ecf8e"
RED = "#ff5f57"
AMBER = "#ffb454"


def _load_settings():
    settings = {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            settings = {str(k): v for k, v in data.items()}
    except (OSError, ValueError):
        pass
    return settings


def _save_settings(settings):
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2)
    except OSError:
        pass


class _Runtime(object):
    """Runtime modules loaded after the updater mounts the runtime tree."""

    def __init__(self):
        self.lobby = None
        self.build_script_mod = None
        self.SlotMeta = None
        self.human_size = None
        self.human_time = None
        self.ts4_user_folder = None
        self.mods_folder = None
        self.saves_folder = None
        self.game_executable = None
        self.steam_game_id = None


RUNTIME = _Runtime()


def _load_app_modules():
    """Import the runtime modules (after the synced tree has been mounted)."""
    if RUNTIME.lobby is not None:
        return
    if os.path.join(ROOT, "client_mod") not in sys.path:
        sys.path.insert(0, os.path.join(ROOT, "client_mod"))
    from save_metadata import SlotMeta, human_size, human_time
    from tools.game_paths import (
        ts4_user_folder,
        mods_folder,
        saves_folder,
        game_executable,
        steam_game_id,
    )
    from tools import lobby
    import build_script_mod

    RUNTIME.lobby = lobby
    RUNTIME.build_script_mod = build_script_mod
    RUNTIME.SlotMeta = SlotMeta
    RUNTIME.human_size = human_size
    RUNTIME.human_time = human_time
    RUNTIME.ts4_user_folder = ts4_user_folder
    RUNTIME.mods_folder = mods_folder
    RUNTIME.saves_folder = saves_folder
    RUNTIME.game_executable = game_executable
    RUNTIME.steam_game_id = steam_game_id