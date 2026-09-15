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
    from simmp_client.hooks import game_hooks

    client = cheat_commands.get_client()
    client.client_name = config["name"]
    client.presence_interval = config["presence_interval"]
    client.presence_ttl = config["presence_ttl"]
    client.auto_accept_travel = config["auto_accept_travel"]
    client.world_sync = config["world_sync"]
    client.world_interval = config["world_interval"]
    client.interaction_sync = config["interaction_sync"]
    client.interaction_interval = config["interaction_interval"]
    client.funds_interval = config["funds_interval"]
    client.funds_sampler = game_hooks.sample_household_funds if config["sync_funds"] else None
    client.funds_applier = game_hooks.set_household_funds if config["sync_funds"] else None
    client._object_gone_applier = game_hooks.apply_object_gone if config["build_sync"] else None
    client.autonomy_suppression = config["autonomy_suppression"]
    cheat_commands.configure_ui(config["ui_dialogs"])
    client.auto_reconnect = config["auto_reconnect"]
    client.reconnect_backoff_min = config["reconnect_backoff_min"]
    client.reconnect_backoff_max = config["reconnect_backoff_max"]
    return client


def _safe_connect(client, host, port):
    try:
        client.connect(host, port)
    except Exception:
        pass


def schedule_auto_connect():
    global _auto_connect_config
    if _auto_connect_config is None:
        return
    from simmp_client.commands import cheat_commands
    from simmp_client.hooks import game_hooks

    config = _auto_connect_config
    _auto_connect_config = None
    client = _apply_config(config)
    host = config["host"]
    port = config["port"]
    game_hooks.add_one_off_real_time_alarm(
        client,
        2.0,
        lambda *args: _safe_connect(client, host, port),
    )


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
    return True


_installed = install()
