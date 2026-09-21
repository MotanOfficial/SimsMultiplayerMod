"""Installation entry point executed when the mod loads inside the game.

Importing this module registers the mp.* cheat commands (the decorators in
cheat_commands.py run at import time), installs the zone-presence sampler,
and optionally auto-connects a short time after startup when
`Sims4Multiplayer.json` sets `"auto_connect": true`, applying the configured
`auto_accept_travel` preference.
"""

_auto_connect_config = None


def _apply_config(config):
    from simmp_client.commands import cheat_commands

    client = cheat_commands.get_client()
    client.client_name = config["name"]
    client.min_players = config["min_players"]
    client.presence_interval = config["presence_interval"]
    client.presence_ttl = config["presence_ttl"]
    client.auto_accept_travel = config["auto_accept_travel"]
    client.world_sync = config["world_sync"]
    client.world_interval = config["world_interval"]
    client.interaction_sync = config["interaction_sync"]
    client.interaction_interval = config["interaction_interval"]
    client.funds_interval = config["funds_interval"]
    cheat_commands.configure_funds_sync(config["sync_funds"])
    cheat_commands.configure_build_sync(config["build_sync"])
    client.autonomy_suppression = config["autonomy_suppression"]
    cheat_commands.configure_ui(config["ui_dialogs"])
    client.auto_reconnect = config["auto_reconnect"]
    client.reconnect_backoff_min = config["reconnect_backoff_min"]
    client.reconnect_backoff_max = config["reconnect_backoff_max"]
    return client


def _safe_connect(client, host, port, attempt=1, max_attempts=8):
    """Connect once; on failure log and re-arm so auto-connect is not silent."""
    from simmp_client.hooks import game_hooks

    try:
        ok = client.connect(host, port)
    except Exception as exc:
        ok = False
        try:
            client._log("ERROR", "auto-connect to %s:%s failed: %s" % (host, port, exc))
        except Exception:
            pass
    else:
        if not ok:
            try:
                client._log(
                    "ERROR",
                    "auto-connect to %s:%s failed (attempt %s/%s)"
                    % (host, port, attempt, max_attempts),
                )
            except Exception:
                pass
    if ok or attempt >= max_attempts:
        return
    delay = min(2.0 * attempt, 15.0)
    game_hooks.add_one_off_real_time_alarm(
        client,
        delay,
        lambda *args: _safe_connect(client, host, port, attempt + 1, max_attempts),
    )


def schedule_auto_connect():
    """Apply the stored config and arm the one-shot connect alarm.

    Returns True when the alarm was actually scheduled. The alarm service may
    not be ready during mod import, so the config is only consumed on success;
    a later `mp.*` command retries via `cheat_commands._maybe_init()`.
    """
    global _auto_connect_config
    if _auto_connect_config is None:
        return False
    from simmp_client.commands import cheat_commands
    from simmp_client.hooks import game_hooks

    config = _auto_connect_config
    client = _apply_config(config)
    host = config["host"]
    port = config["port"]
    handle = game_hooks.add_one_off_real_time_alarm(
        client,
        2.0,
        lambda *args: _safe_connect(client, host, port),
    )
    if handle is None:
        return False
    _auto_connect_config = None
    return True


def install():
    from simmp_client.commands import cheat_commands
    from simmp_client.config import ConfigError, find_config_file, load_config

    cheat_commands.install_presence_sampler()

    global _auto_connect_config
    cfg_path = find_config_file()
    if not cfg_path:
        return True

    try:
        config = load_config(cfg_path)
    except ConfigError:
        return True

    if config is None or not config.get("auto_connect"):
        return True

    _auto_connect_config = config
    # Try to arm the connect alarm right away so the player never has to type
    # a command. If the alarm service is not up yet at import time this is a
    # no-op and the first mp.* command retries through _maybe_init().
    try:
        schedule_auto_connect()
    except Exception:
        pass
    return True


from simmp_client import SIM4_AVAILABLE

_installed = install() if SIM4_AVAILABLE else None
