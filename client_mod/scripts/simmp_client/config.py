"""Configuration for the simmp client mod.

Pure Python with no game imports, so it is unit-testable outside the game.

Config is a small JSON file named `Sims4Multiplayer.json`. Lookup order:

1. an explicit path (command line / `mp.autoconnect <path>`),
2. the `SIM4_MP_CONFIG` environment variable,
3. the game's Mods folder (inferred from `USERPROFILE` on Windows):
   `Documents/Electronic Arts/The Sims 4/Mods/Sims4Multiplayer.json`.

If the file is missing, the mod does nothing at startup (you can still
`mp.connect` manually). Unknown keys and bad types raise `ConfigError`.
"""

import json
import os
import random

CONFIG_FILE_NAME = "Sims4Multiplayer.json"
CLIENT_ID_FILE_NAME = "Sims4Multiplayer.client_id"

DEFAULT_CONFIG = {
    "host": "127.0.0.1",
    "port": 8765,
    "name": "Sims4Player",
    "auto_connect": False,
    "min_players": 2,
    "presence_interval": 5.0,
    "presence_ttl": 30.0,
    "auto_accept_travel": True,
    # Legacy sampler sync defaults off — deep_hooks is the primary path.
    # Re-enable these only for an explicit legacy fallback session.
    "world_sync": False,
    "world_interval": 5.0,
    "interaction_sync": False,
    "interaction_interval": 5.0,
    "sync_funds": False,
    "funds_interval": 2.0,
    "build_sync": False,
    "ui_dialogs": True,
    "autonomy_suppression": True,
    "deep_hooks": True,
    "want_host": True,
    "auto_reconnect": True,
    "reconnect_backoff_min": 2.0,
    "reconnect_backoff_max": 30.0,
}


class ConfigError(ValueError):
    pass


def default_config():
    return dict(DEFAULT_CONFIG)


def _coerce_and_validate(values):
    config = default_config()
    if not isinstance(values, dict):
        raise ConfigError("config must be a JSON object")
    unknown = set(values) - set(config)
    if unknown:
        raise ConfigError("unknown config key(s): %s" % ", ".join(sorted(unknown)))
    config.update(values)

    for key in ("host", "name"):
        if key in values:
            if not isinstance(values[key], str) or not values[key].strip():
                raise ConfigError("%s must be a non-empty string" % key)

    if "port" in values:
        port = values["port"]
        if isinstance(port, bool) or not isinstance(port, int) or not 0 < port < 65536:
            raise ConfigError("port must be an integer in 1..65535")

    if "auto_connect" in values and not isinstance(values["auto_connect"], bool):
        raise ConfigError("auto_connect must be true or false")

    if "min_players" in values:
        count = values["min_players"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ConfigError("min_players must be an integer >= 1")

    if "presence_interval" in values:
        interval = values["presence_interval"]
        if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval <= 0:
            raise ConfigError("presence_interval must be a positive number")

    if "presence_ttl" in values and values["presence_ttl"] is not False:
        ttl = values["presence_ttl"]
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or ttl < 0:
            raise ConfigError("presence_ttl must be a non-negative number")

    if "auto_accept_travel" in values and not isinstance(values["auto_accept_travel"], bool):
        raise ConfigError("auto_accept_travel must be true or false")

    if "world_sync" in values and not isinstance(values["world_sync"], bool):
        raise ConfigError("world_sync must be true or false")

    if "world_interval" in values and values["world_interval"] is not False:
        interval = values["world_interval"]
        if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval <= 0:
            raise ConfigError("world_interval must be a positive number")

    if "interaction_sync" in values and not isinstance(values["interaction_sync"], bool):
        raise ConfigError("interaction_sync must be true or false")

    if "interaction_interval" in values and values["interaction_interval"] is not False:
        interval = values["interaction_interval"]
        if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval <= 0:
            raise ConfigError("interaction_interval must be a positive number")

    if "sync_funds" in values and not isinstance(values["sync_funds"], bool):
        raise ConfigError("sync_funds must be true or false")

    if "funds_interval" in values and values["funds_interval"] is not False:
        interval = values["funds_interval"]
        if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval <= 0:
            raise ConfigError("funds_interval must be a positive number")

    if "build_sync" in values and not isinstance(values["build_sync"], bool):
        raise ConfigError("build_sync must be true or false")

    if "ui_dialogs" in values and not isinstance(values["ui_dialogs"], bool):
        raise ConfigError("ui_dialogs must be true or false")
    if "autonomy_suppression" in values and not isinstance(values["autonomy_suppression"], bool):
        raise ConfigError("autonomy_suppression must be true or false")
    if "deep_hooks" in values and not isinstance(values["deep_hooks"], bool):
        raise ConfigError("deep_hooks must be true or false")
    if "want_host" in values and not isinstance(values["want_host"], bool):
        raise ConfigError("want_host must be true or false")
    if "auto_reconnect" in values and not isinstance(values["auto_reconnect"], bool):
        raise ConfigError("auto_reconnect must be true or false")
    if "reconnect_backoff_min" in values:
        value = values["reconnect_backoff_min"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0.5:
            raise ConfigError("reconnect_backoff_min must be a number >= 0.5")
    if "reconnect_backoff_max" in values:
        value = values["reconnect_backoff_max"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ConfigError("reconnect_backoff_max must be a positive number")
    if (
        "reconnect_backoff_min" in values
        and "reconnect_backoff_max" in values
        and values["reconnect_backoff_min"] > values["reconnect_backoff_max"]
    ):
        raise ConfigError("reconnect_backoff_min must not exceed reconnect_backoff_max")
    return config


def load_config(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            values = json.load(handle)
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        raise ConfigError("cannot read %s: %s" % (path, exc))
    return _coerce_and_validate(values)


def write_default_config(path):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(DEFAULT_CONFIG, handle, indent=2)
    return path


def candidate_config_paths():
    env_path = os.environ.get("SIM4_MP_CONFIG")
    if env_path:
        yield env_path
    profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    mods = os.path.join(profile, "Documents", "Electronic Arts", "The Sims 4", "Mods")
    yield os.path.join(mods, CONFIG_FILE_NAME)
    yield os.path.join(mods, "Sims4Multiplayer", CONFIG_FILE_NAME)


def find_config_file(explicit=None):
    if explicit:
        # An explicit path is authoritative: if it is gone, do not silently
        # fall back to the automatic game-directory search.
        return explicit if os.path.isfile(explicit) else None
    for path in candidate_config_paths():
        if os.path.isfile(path):
            return path
    return None


def client_id_file_path(explicit_config_path=None):
    """Where the persistent client identity lives: next to the config file.

    Launcher-managed installs keep the config (and therefore the identity)
    across mod reinstalls, which source-only persistence could not.
    """
    config_path = find_config_file(explicit_config_path)
    if config_path:
        directory = os.path.dirname(config_path)
    else:
        profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        directory = os.path.join(
            profile, "Documents", "Electronic Arts", "The Sims 4", "Mods"
        )
    return os.path.join(directory, CLIENT_ID_FILE_NAME)


def load_or_create_client_id(explicit_config_path=None):
    """Stable per-install client identity, persisted across game restarts.

    The server keys its ghost/resume behaviour on `client_id`; a random id
    per launch turned every game restart into a brand-new player (new
    player_id, no resume, 60s of ownership reserved for an identity that
    would never return). The id is a 32-hex-char string stored in a sidecar
    file next to the config. Never raises: on any I/O failure a fresh id is
    returned so this session still works (it just will not persist).
    """
    path = client_id_file_path(explicit_config_path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            stored = handle.read().strip()
    except OSError:
        stored = ""
    if _is_valid_client_id(stored):
        return stored
    client_id = "%032x" % random.getrandbits(128)
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(client_id)
    except OSError:
        pass
    return client_id


def _is_valid_client_id(value):
    if not isinstance(value, str) or len(value) != 32:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True