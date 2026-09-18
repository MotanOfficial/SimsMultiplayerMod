"""In-game cheat commands for M3.

These modules import `sims4` and therefore only load inside the game. The
import happens from sims4_plugin.py, which is only imported when the mod runs
inside The Sims 4.

Commands (open the console with Ctrl+Shift+C):

    mp.connect <host> [port] [name]
    mp.disconnect
    mp.join <room_id>
    mp.test <message>
    mp.who                      # roster + presence snapshot
    mp.autoconnect [config]     # read Sims4Multiplayer.json and connect
    mp.status                   # detailed internal status
    mp.process                  # manually drain pending messages
    mp.travel <zone_id>         # invite the room to travel together
    mp.travel_ready             # confirm arrival (manual fallback for the game hook)
    mp.travel_autoaccept on|off # refuse future travel invites
    mp.clock                    # send a CLOCK_SYNC beacon and show the clock state
    mp.claim <key>              # take ownership of a replicated object
    mp.release <key>            # release ownership of a replicated object
    mp.obj <key> x y z          # push a position delta for an owned object
    mp.world                    # list the mirrored world catalog
    mp.inter <key> <interaction> # propose an interaction on an object (e.g. mp.inter sofa Read)
    mp.inter_end <key>          # end an interaction you hold
    mp.inter_list               # list active interactions + cooldowns
    mp.ui on|off                # toggle in-game dialogs/toasts
    mp.ui_test [text]           # show a test toast (in-game only)
    mp.auto_reconnect [on|off]  # toggle automatic reconnect after a drop
"""

import sims4.commands

from simmp.constants import CLOCK_SPEED_NORMAL, CLOCK_SPEED_PAUSED, MAX_CLOCK_SPEED, MIN_CLOCK_SPEED
from simmp_client import ui as mp_ui
from simmp_client.connectivity import MultiplayerClient
from simmp_client.hooks import game_hooks
from simmp_client.logfile import FileLog
from simmp_client.notifications import ToastFilter


def _console_output(line, connection=None):
    if connection is not None:
        try:
            sims4.commands.CheatOutput(connection)(line)
        except Exception:
            pass


_ui = mp_ui.GameUI(enabled=True, console=_console_output)


_toast_filter = ToastFilter()

_client_log = FileLog()


def _console_line(line):
    """Echo a mod log line to the cheat console (works without a connection)."""
    try:
        sims4.commands.output(line)
    except Exception:
        pass


def _notify(line):
    _console_output(line)
    _console_line(line)
    _client_log.write(line)
    toast = _toast_filter.pick(
        line,
        self_player_id=_client.session.player_id if _client.session else None,
        roster=_client.session.room_players if _client.session else None,
        world=_client.session.world if _client.session else None,
    )
    if toast:
        _ui.toast(toast)


def _toast_for(line):
    """Back-compat alias for the pure toast matcher (kept for imports)."""
    return _toast_filter.pick(line)


_client = MultiplayerClient(notify=_notify)


def configure_ui(enabled):
    """Apply the `ui_dialogs` config value (True/False) to the in-game UI."""
    _ui.enabled = bool(enabled)


def _configure_auto_reconnect(config):
    _client.auto_reconnect = bool(config.get("auto_reconnect", True))
    _client.reconnect_backoff_min = float(config.get("reconnect_backoff_min", 2.0))
    _client.reconnect_backoff_max = float(config.get("reconnect_backoff_max", 30.0))


def _on_travel_decision(request_id, accepted):
    _client.respond_travel(request_id, accepted)
    if not accepted:
        _client.session.apply_travel_abort({"reason": "declined"}, request_id)


def _travel_controller(request_id, zone_id):
    if _ui.enabled and mp_ui.available():
        requester = _client.session.travel_requester_name
        if mp_ui.show_travel_invite(request_id, zone_id, requester, _on_travel_decision):
            _console_output("[MP][TRAVEL] travel invite dialog shown; waiting for decision...")
            return None
    return _client.auto_accept_travel


def install_presence_sampler():
    _client.set_presence_sampler(game_hooks.sample_current_zone)
    _client.set_world_sampler(game_hooks.sample_playable_world)
    _client.set_world_applier(game_hooks.apply_world_updates)
    _client.set_funds_sampler(game_hooks.sample_household_funds)
    _client.set_funds_applier(game_hooks.set_household_funds)
    _client.set_object_gone_applier(game_hooks.apply_object_gone)
    _client.set_interaction_sampler(game_hooks.sample_interactions)
    _client.set_interaction_applier(game_hooks.apply_interactions)
    _client.set_autonomy_reconciler(game_hooks.reconcile_autonomy)
    game_hooks.set_interaction_logger(_console_output)
    _client.travel_controller = _travel_controller


def configure_build_sync(enabled):
    """Toggle live lot-object sync (world sampler + destroy applier).

    On = household sims + instanced lot objects (moves/rotations/deletes
    relay); off = sims only, so build/buy edits stay local.
    """
    _client.build_sync = bool(enabled)
    if _client.build_sync:
        _client.set_world_sampler(game_hooks.sample_playable_world)
        _client.set_object_gone_applier(game_hooks.apply_object_gone)
    else:
        _client.set_world_sampler(game_hooks.sample_world_objects)
        _client.set_object_gone_applier(None)


def configure_funds_sync(enabled):
    """Toggle live household-funds sync (sampler + applier)."""
    _client.funds_sampler = game_hooks.sample_household_funds if enabled else None
    _client.funds_applier = game_hooks.set_household_funds if enabled else None


def get_client():
    return _client


def _maybe_init():
    """One-time lazy init triggered by the first command.

    The game engine (alarms service) is not ready during mod import time, so
    anything needing alarms is deferred until the player uses a command.
    """
    if not getattr(_maybe_init, "_done", False):
        _maybe_init._done = True
        try:
            from simmp_client import sims4_plugin

            sims4_plugin.schedule_auto_connect()
        except Exception:
            pass


@sims4.commands.Command("mp.connect", command_type=sims4.commands.CommandType.Cheat)
def _mp_connect(host="127.0.0.1", port="8765", name="", _connection=None):
    _maybe_init()
    if name:
        _client.client_name = name
    _client.connect(host, port)
    _console_output("[MP][NET] connecting to %s:%s..." % (host, port), _connection)


@sims4.commands.Command("mp.disconnect", command_type=sims4.commands.CommandType.Cheat)
def _mp_disconnect(_connection=None):
    _client.disconnect()


@sims4.commands.Command("mp.join", command_type=sims4.commands.CommandType.Cheat)
def _mp_join(room_id="lobby", _connection=None):
    if not room_id:
        _console_output("[MP][ROOM] usage: mp.join <room_id>", _connection)
        return
    _client.join_room(room_id)


@sims4.commands.Command("mp.test", command_type=sims4.commands.CommandType.Cheat)
def _mp_test(text="hello", _connection=None):
    _client.send_test_event(text)


@sims4.commands.Command("mp.who", command_type=sims4.commands.CommandType.Cheat)
def _mp_who(_connection=None):
    _client.process_incoming()
    _console_output("[MP][ROOM] %s" % _client.status(), _connection)
    _console_output("[MP][ROOM] presence: %s" % _client.presence_summary(), _connection)


@sims4.commands.Command("mp.autoconnect", command_type=sims4.commands.CommandType.Cheat)
def _mp_autoconnect(path="", _connection=None):
    from simmp_client.config import ConfigError, find_config_file, load_config

    try:
        cfg_path = find_config_file(path if path else None)
        if cfg_path is None:
            _console_output("[MP][NET] no config file found; create Sims4Multiplayer.json in the Mods folder", _connection)
            return
        config = load_config(cfg_path)
    except ConfigError as exc:
        _console_output("[MP][ERROR] config error: %s" % exc, _connection)
        return
    _client.client_name = config["name"]
    _console_output("[MP][NET] config loaded from %s" % cfg_path, _connection)
    _client.min_players = config["min_players"]
    _client.presence_ttl = config["presence_ttl"]
    _client.auto_accept_travel = config["auto_accept_travel"]
    _client.world_sync = config["world_sync"]
    _client.world_interval = config["world_interval"]
    _client.interaction_sync = config["interaction_sync"]
    _client.interaction_interval = config["interaction_interval"]
    configure_ui(config["ui_dialogs"])
    _configure_auto_reconnect(config)
    _client.connect(config["host"], config["port"])


@sims4.commands.Command("mp.status", command_type=sims4.commands.CommandType.Cheat)
def _mp_status(_connection=None):
    _client.process_incoming()
    _console_output(_client.status(), _connection)


@sims4.commands.Command("mp.process", command_type=sims4.commands.CommandType.Cheat)
def _mp_process(_connection=None):
    _client.process_incoming()
    _console_output("[MP][NET] drained pending messages", _connection)


@sims4.commands.Command("mp.travel", command_type=sims4.commands.CommandType.Cheat)
def _mp_travel(zone_id="", _connection=None):
    _client.process_incoming()
    if not zone_id or not zone_id.isdigit():
        _console_output("[MP][TRAVEL] usage: mp.travel <zone_id>", _connection)
        return
    _client.request_travel(int(zone_id))


@sims4.commands.Command("mp.travel_ready", command_type=sims4.commands.CommandType.Cheat)
def _mp_travel_ready(_connection=None):
    _client.process_incoming()
    _client.confirm_travel_ready()


@sims4.commands.Command("mp.travel_autoaccept", command_type=sims4.commands.CommandType.Cheat)
def _mp_travel_autoaccept(setting="", _connection=None):
    if setting in ("on", "1", "true", "yes"):
        _client.auto_accept_travel = True
        _console_output("[MP][TRAVEL] auto-accept travel invites: on", _connection)
    elif setting in ("off", "0", "false", "no"):
        _client.auto_accept_travel = False
        _console_output("[MP][TRAVEL] auto-accept travel invites: off", _connection)
    else:
        _console_output("[MP][TRAVEL] usage: mp.travel_autoaccept on|off", _connection)


@sims4.commands.Command("mp.clock", command_type=sims4.commands.CommandType.Cheat)
def _mp_clock(_connection=None):
    _client.process_incoming()
    sent = _client.send_clock_sync()
    _client.process_incoming()
    clock = _client.session.clock_sync
    if clock:
        _console_output("[MP][SYNC] clock=%s" % clock, _connection)
    if not sent:
        _console_output("[MP][SYNC] note: game clock not available here", _connection)


@sims4.commands.Command("mp.time", command_type=sims4.commands.CommandType.Cheat)
def _mp_time(_connection=None):
    _client.process_incoming()
    _console_output("[MP][TIME] %s" % _client.clock_summary(), _connection)


@sims4.commands.Command("mp.pause", command_type=sims4.commands.CommandType.Cheat)
def _mp_pause(_connection=None):
    _client.process_incoming()
    if _client.change_clock_speed(CLOCK_SPEED_PAUSED):
        _console_output("[MP][TIME] game paused (server broadcast follows)", _connection)
    else:
        _console_output("[MP][ERROR] failed to send TIME_SPEED", _connection)


@sims4.commands.Command("mp.resume", command_type=sims4.commands.CommandType.Cheat)
def _mp_resume(_connection=None):
    _client.process_incoming()
    if _client.change_clock_speed(CLOCK_SPEED_NORMAL):
        _console_output("[MP][TIME] game resumed", _connection)
    else:
        _console_output("[MP][ERROR] failed to send TIME_SPEED", _connection)


@sims4.commands.Command("mp.speed", command_type=sims4.commands.CommandType.Cheat)
def _mp_speed(speed="", _connection=None):
    _client.process_incoming()
    if not speed or not speed.isdigit():
        _console_output("[MP][TIME] usage: mp.speed 0|1|2|3", _connection)
        return
    value = int(speed)
    if value < MIN_CLOCK_SPEED or value > MAX_CLOCK_SPEED:
        _console_output("[MP][TIME] speed must be 0 (paused) to 3 (ultra-fast)", _connection)
        return
    if _client.change_clock_speed(value):
        _console_output("[MP][TIME] clock speed set to %s" % value, _connection)
    else:
        _console_output("[MP][ERROR] failed to send TIME_SPEED", _connection)


@sims4.commands.Command("mp.ready", command_type=sims4.commands.CommandType.Cheat)
def _mp_ready(_connection=None):
    _client.process_incoming()
    if _client.mark_ready():
        _console_output("[MP][TIME] sent TIME_READY (will be sent once per connection/zone)", _connection)
    else:
        _console_output("[MP][ERROR] could not send TIME_READY; is the zone running?", _connection)


@sims4.commands.Command("mp.claim", command_type=sims4.commands.CommandType.Cheat)
def _mp_claim(key="", _connection=None):
    if not key:
        _console_output("[MP][SYNC] usage: mp.claim <key>", _connection)
        return
    _client.process_incoming()
    _client.claim_object(key)
    _client.process_incoming()


@sims4.commands.Command("mp.release", command_type=sims4.commands.CommandType.Cheat)
def _mp_release(key="", _connection=None):
    if not key:
        _console_output("[MP][SYNC] usage: mp.release <key>", _connection)
        return
    _client.process_incoming()
    _client.release_object(key)
    _client.process_incoming()


@sims4.commands.Command("mp.obj", command_type=sims4.commands.CommandType.Cheat)
def _mp_obj(key="", x="", y="", z="", _connection=None):
    if not key:
        _console_output("[MP][SYNC] usage: mp.obj <key> <x> <y> <z>", _connection)
        return
    try:
        fields = {"x": float(x), "y": float(y), "z": float(z)}
    except ValueError:
        _console_output("[MP][SYNC] usage: mp.obj <key> <x> <y> <z>", _connection)
        return
    _client.process_incoming()
    _client.update_object(key, fields)
    _client.process_incoming()


@sims4.commands.Command("mp.world", command_type=sims4.commands.CommandType.Cheat)
def _mp_world(_connection=None):
    _client.process_incoming()
    _console_output("[MP][SYNC] world: %s" % _client.world_summary(), _connection)


@sims4.commands.Command("mp.inter", command_type=sims4.commands.CommandType.Cheat)
def _mp_inter(key="", interaction="", *_args, _connection=None):
    if not key or not interaction:
        _console_output("[MP][SYNC] usage: mp.inter <key> <interaction>", _connection)
        return
    _client.process_incoming()
    _client.propose_interaction(key, interaction)
    _client.process_incoming()


@sims4.commands.Command("mp.inter_end", command_type=sims4.commands.CommandType.Cheat)
def _mp_inter_end(key="", _connection=None):
    if not key:
        _console_output("[MP][SYNC] usage: mp.inter_end <key>", _connection)
        return
    _client.process_incoming()
    _client.end_interaction(key)
    _client.process_incoming()


@sims4.commands.Command("mp.inter_list", command_type=sims4.commands.CommandType.Cheat)
def _mp_inter_list(_connection=None):
    _client.process_incoming()
    _console_output("[MP][SYNC] interactions: %s" % _client.interaction_summary(), _connection)


@sims4.commands.Command("mp.save_status", command_type=sims4.commands.CommandType.Cheat)
def _mp_save_status(_connection=None):
    _client.process_incoming()
    _console_output("[MP][SAVE] %s" % _client.save_summary(), _connection)
    dirs = game_hooks.find_save_directory(roots=[])
    for root in game_hooks._save_roots():
        _console_output("[MP][SAVE] root: %s" % root, _connection)
    if dirs:
        _console_output("[MP][SAVE] target dir: %s" % dirs, _connection)


@sims4.commands.Command("mp.save_push", command_type=sims4.commands.CommandType.Cheat)
def _mp_save_push(path="", slot="", _connection=None):
    import os

    if not path:
        _console_output("[MP][SAVE] usage: mp.save_push <file> [slot]", _connection)
        return
    if not os.path.isfile(path):
        _console_output("[MP][SAVE] no such file: %s" % path, _connection)
        return
    with open(path, "rb") as handle:
        data = handle.read()
    slot = slot or os.path.basename(path)
    _client.process_incoming()
    sent, total = _client.push_save_file(slot, data)
    _console_output(
        "[MP][SAVE] pushed %s (%s bytes) as %s: %s/%s chunks"
        % (path, len(data), slot, sent, total),
        _connection,
    )


def _dump_diag(lines):
    """Write `mp.diag` output to the Mods folder so it can be read off-box."""
    try:
        import os

        from simmp_client.config import candidate_config_paths

        base = None
        for path in candidate_config_paths():
            directory = os.path.dirname(path)
            if os.path.isdir(directory):
                base = directory
                break
        if base is None:
            return None
        target = os.path.join(base, "Sims4Multiplayer-diag.txt")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        return target
    except Exception:
        return None


@sims4.commands.Command("mp.diag", command_type=sims4.commands.CommandType.Cheat)
def _mp_diag(_connection=None):
    _maybe_init()
    lines = []
    for line in game_hooks.diagnose_hooks():
        lines.append("[MP][DIAG] %s" % line)
    for line in game_hooks.diagnose_alarms():
        lines.append("[MP][DIAG][ALARM] %s" % line)
    lines.append("[MP][DIAG] alarm=%s" % _client.alarm_summary())
    lines.append("[MP][DIAG] saves=%s" % _client.save_summary())
    lines.append("[MP][DIAG] time=%s" % _client.clock_summary())
    lines.append(_client.status())
    for line in lines:
        _console_output(line, _connection)
    path = _dump_diag(lines)
    if path:
        _console_output("[MP][DIAG] wrote %s" % path, _connection)


@sims4.commands.Command("mp.ui", command_type=sims4.commands.CommandType.Cheat)
def _mp_ui(setting="", _connection=None):
    if setting in ("on", "1", "true", "yes"):
        _ui.enabled = True
        _console_output("[MP][UI] in-game dialogs: on", _connection)
    elif setting in ("off", "0", "false", "no"):
        _ui.enabled = False
        _console_output("[MP][UI] in-game dialogs: off", _connection)
    else:
        _console_output("[MP][UI] usage: mp.ui on|off", _connection)


@sims4.commands.Command("mp.auto_reconnect", command_type=sims4.commands.CommandType.Cheat)
def _mp_auto_reconnect(setting="", _connection=None):
    if setting in ("on", "1", "true", "yes"):
        _client.auto_reconnect = True
        _console_output("[MP][NET] auto-reconnect: on", _connection)
    elif setting in ("off", "0", "false", "no"):
        _client.auto_reconnect = False
        _console_output("[MP][NET] auto-reconnect: off", _connection)
    else:
        _console_output("[MP][NET] auto-reconnect: %s" % ("on" if _client.auto_reconnect else "off"), _connection)


@sims4.commands.Command("mp.autonomy", command_type=sims4.commands.CommandType.Cheat)
def _mp_autonomy(setting="", _connection=None):
    if setting in ("on", "1", "true", "yes"):
        _client.autonomy_suppression = True
        _console_output("[MP][AUTO] autonomy suppression: on", _connection)
    elif setting in ("off", "0", "false", "no"):
        _client.autonomy_suppression = False
        _console_output("[MP][AUTO] autonomy suppression: off", _connection)
    else:
        _console_output("[MP][AUTO] autonomy suppression: %s" % ("on" if _client.autonomy_suppression else "off"), _connection)
    if _client.autonomy_suppression:
        _client._reconcile_autonomy()


@sims4.commands.Command("mp.ui_test", command_type=sims4.commands.CommandType.Cheat)
def _mp_ui_test(text="hello from multiplayer", _connection=None):
    shown = _ui.toast(text)
    reason = ""
    if not shown:
        last_error = mp_ui.show_notification.last_error
        reason = " (last error: %r)" % (last_error,) if last_error else ""
    _console_output(
        "[MP][UI] test toast %sshown%s (in-game only)" % ("" if shown else "not ", reason),
        _connection,
    )


@sims4.commands.Command("mp.build_sync", command_type=sims4.commands.CommandType.Cheat)
def _mp_build_sync(setting="", _connection=None):
    if setting in ("on", "1", "true", "yes"):
        configure_build_sync(True)
        _console_output("[MP][SYNC] build/buy live sync: on", _connection)
    elif setting in ("off", "0", "false", "no"):
        configure_build_sync(False)
        _console_output("[MP][SYNC] build/buy live sync: off", _connection)
    else:
        _console_output(
            "[MP][SYNC] build/buy live sync: %s" % ("on" if _client.build_sync else "off"),
            _connection,
        )


@sims4.commands.Command("mp.funds_sync", command_type=sims4.commands.CommandType.Cheat)
def _mp_funds_sync(setting="", _connection=None):
    if setting in ("on", "1", "true", "yes"):
        configure_funds_sync(True)
        _client._funds_baseline = None
        _console_output("[MP][FUNDS] funds live sync: on", _connection)
    elif setting in ("off", "0", "false", "no"):
        configure_funds_sync(False)
        _console_output("[MP][FUNDS] funds live sync: off", _connection)
    else:
        _console_output(
            "[MP][FUNDS] funds live sync: %s" % ("on" if _client.funds_sampler is not None else "off"),
            _connection,
        )


@sims4.commands.Command("mp.funds_interval", command_type=sims4.commands.CommandType.Cheat)
def _mp_funds_interval(seconds="", _connection=None):
    if seconds:
        try:
            value = float(seconds)
        except ValueError:
            _console_output("[MP][FUNDS] usage: mp.funds_interval <seconds>", _connection)
            return
        if value <= 0:
            _console_output("[MP][FUNDS] interval must be positive", _connection)
            return
        _client.funds_interval = value
        _console_output("[MP][FUNDS] poll interval: %.1fs" % value, _connection)
    else:
        _console_output("[MP][FUNDS] poll interval: %.1fs" % _client.funds_interval, _connection)