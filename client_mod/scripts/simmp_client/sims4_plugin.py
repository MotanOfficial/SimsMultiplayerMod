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
    client.deep_hooks = config.get("deep_hooks", True)
    client.want_host = config.get("want_host", True)
    cheat_commands.configure_ui(config["ui_dialogs"])
    client.auto_reconnect = config["auto_reconnect"]
    client.reconnect_backoff_min = config["reconnect_backoff_min"]
    client.reconnect_backoff_max = config["reconnect_backoff_max"]
    # Keep connect target on the client so the preconnect tick can dial
    # without depending on a nested one-shot alarm that may never fire.
    client._pending_connect_host = config["host"]
    client._pending_connect_port = config["port"]
    return client


def try_pending_connect(client=None):
    """Connect now if auto-connect is still pending. Returns True on success.

    Unlike the old one-shot alarm path, this is safe to call every sync tick:
    it no-ops when already connected / no target, and only clears the stored
    config after TCP is up.
    """
    global _auto_connect_config
    from simmp_client.commands import cheat_commands

    if client is None:
        client = cheat_commands.get_client()
    engine = getattr(client, "engine", None)
    if engine is not None and engine.connected:
        _auto_connect_config = None
        client._pending_connect_host = None
        client._pending_connect_port = None
        return True
    host = getattr(client, "_pending_connect_host", None)
    port = getattr(client, "_pending_connect_port", None)
    if not host or port is None:
        if _auto_connect_config is None:
            return False
        client = _apply_config(_auto_connect_config)
        host = client._pending_connect_host
        port = client._pending_connect_port
    if not host or port is None:
        return False
    try:
        client.begin_preconnect_gate()
    except Exception:
        pass
    try:
        ok = client.connect(host, port)
    except Exception as exc:
        try:
            client._log("ERROR", "auto-connect to %s:%s failed: %s" % (host, port, exc))
        except Exception:
            pass
        return False
    if ok:
        _auto_connect_config = None
        client._pending_connect_host = None
        client._pending_connect_port = None
        try:
            client._log("NET", "auto-connected to %s:%s" % (host, port))
        except Exception:
            pass
        return True
    try:
        client._log("ERROR", "auto-connect to %s:%s failed" % (host, port))
    except Exception:
        pass
    return False


def schedule_auto_connect():
    """Apply config and arm preconnect; connect is driven by the sync tick.

    Returns True when a pending connect target is armed. The alarm service may
    not be ready during mod import — config is kept until TCP succeeds so a
    handle that never fires cannot permanently disable auto-connect.
    """
    global _auto_connect_config
    if _auto_connect_config is None:
        # Still retry from client-stored host/port after a prior arm.
        from simmp_client.commands import cheat_commands

        client = cheat_commands.get_client()
        if getattr(client, "_pending_connect_host", None):
            try:
                client.begin_preconnect_gate()
            except Exception:
                pass
            return True
        return False
    client = _apply_config(_auto_connect_config)
    try:
        client.begin_preconnect_gate()
    except Exception:
        pass
    return True


def _install_zone_ready_retry():
    """Retry auto-connect / preconnect gate when a lot finishes loading."""
    candidates = (
        ("zone", "Zone", "on_loading_screen_animation_finished"),
        ("zone", "Zone", "on_hit_their_marks"),
        ("sims.gameplay", "Gameplay", "on_loading_screen_animation_finished"),
    )
    for module_name, class_name, method_name in candidates:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name, None)
            if cls is None:
                continue
            original = getattr(cls, method_name, None)
            if original is None or getattr(original, "_simmp_preconnect", False):
                continue

            def _make(orig):
                def wrapped(self, *args, **kwargs):
                    try:
                        schedule_auto_connect()
                        try_pending_connect()
                    except Exception:
                        pass
                    try:
                        from simmp_client.commands import cheat_commands

                        client = cheat_commands.get_client()
                        if getattr(client, "_preconnect_gate", False):
                            client.begin_preconnect_gate()
                        try:
                            client.ensure_alarm()
                        except Exception:
                            pass
                    except Exception:
                        pass
                    return orig(self, *args, **kwargs)

                wrapped._simmp_preconnect = True
                return wrapped

            setattr(cls, method_name, _make(original))
            return True
        except Exception:
            continue
    return False


def install():
    from simmp_client.commands import cheat_commands
    from simmp_client.config import ConfigError, find_config_file, load_config

    cheat_commands.install_presence_sampler()

    try:
        from simmp_client import tick_pump
        from simmp_client.logfile import FileLog

        if tick_pump.install():
            FileLog().write("[MP][NET] tick_pump installed")
    except Exception:
        pass

    global _auto_connect_config
    cfg_path = find_config_file()
    config = None
    if cfg_path:
        try:
            config = load_config(cfg_path)
        except ConfigError:
            config = None

    deep_enabled = True if config is None else bool(config.get("deep_hooks", True))
    if deep_enabled:
        try:
            from simmp_client import deep as deep_hooks
            deep_hooks.install()
        except Exception:
            pass

    if config is None or not config.get("auto_connect"):
        return True

    _auto_connect_config = config
    try:
        client = _apply_config(config)
        client.begin_preconnect_gate()
    except Exception:
        pass
    try:
        _install_zone_ready_retry()
    except Exception:
        pass
    try:
        schedule_auto_connect()
    except Exception:
        pass
    return True


from simmp_client import SIM4_AVAILABLE

_installed = install() if SIM4_AVAILABLE else None
