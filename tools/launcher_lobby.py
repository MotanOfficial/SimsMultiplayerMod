"""LauncherBridge mixin: lobby lifecycle, save sharing, joining, launch."""

import json
import os
import re
import subprocess
import threading

from PySide6.QtCore import Slot

from launcher_common import (
    ACCENT,
    AMBER,
    DEFAULT_PORT,
    GREEN,
    MUTED,
    RED,
    RUNTIME,
    STATUS_FILE,
)


class LobbyMixin(object):
    # ---------------------------------------------------------------- lobby
    @Slot()
    def startLobby(self):
        try:
            port = int(self._host_port.strip() or DEFAULT_PORT)
        except ValueError:
            self._note("Port must be a number.", kind="error")
            return
        if self.server is not None and self.server.thread_alive():
            self._note("Lobby already running.")
            return
        self._note("Opening lobby on port %s..." % port)
        self.server = RUNTIME.lobby.ServerHandle(
            host="0.0.0.0",
            port=port,
            status_file=STATUS_FILE,
            log_file=self._server_log_file(),
            log_level="INFO",
            on_status=self._on_status,
            on_log=lambda line: self._note(line),
        )
        if not self.server.start():
            self._note("Failed to bind port %s - is it already in use?" % port, kind="error")
            self.server = None
            return
        self.hostPort = str(self.server.actual_port)
        self._start_diag_receiver(self.server.actual_port)
        self._set_card(
            "lobby",
            "Lobby open at %s:%s" % (self._current_ip(), self.server.actual_port),
            "Tell the other PC to join - waiting for players.",
            GREEN,
        )
        self.lobbyRunningChanged.emit(self.lobbyRunning)
        self._note("Windows firewall may ask for permission - allow it so friends can join.")

    @Slot()
    def stopLobby(self):
        self._disconnect_held()
        self._stop_diag_receiver()
        if self.server is not None:
            self.server.stop()
            self.server = None
        self._synced = False
        self._set_players(0)
        self._set_card("lobby", "Lobby stopped", "Start the lobby, then pick a save to share.", MUTED)
        self.lobbyRunningChanged.emit(self.lobbyRunning)
        self._set_can_share(False)
        self._update_host_start_button()

    def _server_log_file(self):
        from launcher_common import SERVER_LOG_FILE
        return SERVER_LOG_FILE

    def _on_status(self, data):
        self._post_status(data)

    def _post_status(self, data):
        players = data.get("players") or []
        connected = [p for p in players if p.get("connected")]
        self._set_players(len(connected))
        if self.server is None or not self.server.thread_alive():
            return
        if connected:
            # Prefer showing in-game seats; lobby GUI seats stay connected.
            game = [p for p in connected if not p.get("lobby")]
            lobby = [p for p in connected if p.get("lobby")]
            parts = []
            if game:
                parts.append(
                    "%d in-game: %s"
                    % (len(game), ", ".join(p.get("name", "?") for p in game))
                )
            if lobby:
                parts.append(
                    "%d lobby: %s"
                    % (len(lobby), ", ".join(p.get("name", "?") for p in lobby))
                )
            detail = "; ".join(parts) if parts else "%d connected" % len(connected)
            color = GREEN
        elif self._synced:
            detail = "Waiting for players (save already synced)."
            color = AMBER
        else:
            detail = "Waiting for players to join..."
            color = MUTED
        self._set_card(
            "lobby",
            "Lobby open at %s:%s" % (self._current_ip(), self.server.actual_port),
            detail,
            color,
        )
        if connected:
            self._set_can_share(bool(self._selected_save and not self._synced))
        self._update_host_start_button()

    def _player_count(self):
        if hasattr(self, "_connected_players"):
            return self._connected_players
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return len([p for p in data.get("players", []) if p.get("connected")])
        except Exception:
            return 0

    # ------------------------------------------------------------------ share
    @Slot()
    def shareSave(self):
        if self._selected_save is None:
            self._note("Pick a save to share first.", kind="error")
            return
        if self.server is None or not self.server.thread_alive():
            self._note("Start the lobby first.", kind="error")
            return
        self._set_can_share(False)
        self._set_card(
            "share",
            "Sharing save...",
            os.path.basename(self._selected_save),
            AMBER,
            progress=0,
            show_bar=True,
        )
        name = self._host_name.strip() or "Host"

        def on_line(line):
            self._share_line(line)

        def work():
            self._disconnect_held("_share_client")
            try:
                held = []
                ok, reached = RUNTIME.lobby.push_save_file(
                    self._selected_save,
                    "127.0.0.1",
                    self.server.actual_port,
                    name=name,
                    timeout=60.0,
                    on_line=on_line,
                    keep_alive=True,
                    held=held,
                )
                if held:
                    self._share_client = held[0]
                self._on_share_done(ok, reached)
            except Exception as exc:  # noqa: BLE001
                self._share_client = None
                self._on_share_done(False, 0, exc)

        self.push_thread = threading.Thread(target=work, daemon=True)
        self.push_thread.start()

    def _share_line(self, line):
        stripped = line.strip()
        if "sync alarm unavailable" in line:
            self._note(stripped)
            return
        match = re.search(r"SAVE_ACK .*?seq=(\d+)/(\d+)", line)
        if match:
            seq, total = int(match.group(1)), int(match.group(2))
            pct = (seq * 100 // total) if total else 100
            self._set_card(
                "share",
                "Sharing save... %d/%d chunks" % (seq, total),
                os.path.basename(self._selected_save or ""),
                AMBER,
                progress=pct,
                show_bar=True,
            )
            self._note(stripped)
            return
        if "[MP][ERROR]" in line:
            self._note(stripped, kind="error")
            return
        self._note(stripped)

    def _on_share_done(self, ok, reached, exc=None):
        if exc is not None:
            self._set_card("share", "Share failed", str(exc), RED)
            return
        if ok:
            self._synced = True
            if reached >= 1:
                self._set_card(
                    "share",
                    "Save synced to %d player(s)" % reached,
                    "They can press Start game now.",
                    GREEN,
                    progress=100,
                    done=True,
                )
            else:
                self._set_card(
                    "share",
                    "Save staged",
                    "Players who join or reconnect will receive it automatically.",
                    GREEN,
                    progress=100,
                    done=True,
                )
            self._set_can_share(bool(self._player_count() >= 1))
        else:
            self._set_card("share", "Share failed", "The lobby server did not accept the save.", RED)
            self._set_can_share(bool(self._player_count() >= 1 and self._selected_save))
        self._update_host_start_button()

    def _update_host_start_button(self):
        # Once the save is synced, Start stays available even if lobby TCP
        # clients disconnect to launch the game. Requiring a live player
        # count made the host Start button die the moment the laptop left.
        self._set_can_host_start(bool(self._synced))

    # ----------------------------------------------------------------- join
    @Slot()
    def joinLobby(self):
        host = self._join_ip.strip()
        try:
            port = int(self._join_port.strip() or DEFAULT_PORT)
        except ValueError:
            self._note("Port must be a number.", kind="error")
            return
        if not host:
            self._note("Enter the host's IP address.", kind="error")
            return
        if RUNTIME.ts4_user_folder:
            ts4_user = RUNTIME.ts4_user_folder()
            if ts4_user:
                os.environ["SIM4_MP_SAVE_ROOT"] = ts4_user
        name = self._join_name.strip() or "Player"
        self._joining = True
        self.joiningChanged.emit(True)
        self._set_card(
            "join",
            "Connecting to %s:%s..." % (host, port),
            "Waiting for the host to share the save...",
            AMBER,
            progress=0,
            show_bar=True,
        )
        self._note("Joining %s:%s - waiting for the host to share the save..." % (host, port))

        def on_connected():
            self._note("Connected as %s - save request sent to the host's lobby." % name)
            self._set_card(
                "join",
                "Connected - waiting for the save",
                "The host has been asked to share their save.",
                AMBER,
            )

        def on_line(line):
            self._join_line(line)

        def work():
            self._disconnect_held("_join_client")
            try:
                held = []
                slot, path = RUNTIME.lobby.receive_save_file(
                    host,
                    port,
                    name=name,
                    timeout=120.0,
                    on_connected=on_connected,
                    on_line=on_line,
                    keep_alive=True,
                    held=held,
                )
                if held:
                    self._join_client = held[0]
                self._on_join_done(slot, path)
            except Exception as exc:  # noqa: BLE001
                self._join_client = None
                self._on_join_done(None, None, exc)

        self.join_thread = threading.Thread(target=work, daemon=True)
        self.join_thread.start()

    def _join_line(self, line):
        stripped = line.strip()
        if "sync alarm unavailable" in line:
            self._note(stripped)
            return
        if "[MP][SAVE]" in line:
            match = re.search(r"SAVE_PUSH (\S+) (\d+)/(\d+)", line)
            if match:
                slot, seq, total = match.group(1), int(match.group(2)), int(match.group(3))
                pct = (seq * 100 // total) if total else 100
                self._set_card(
                    "join",
                    "Receiving save... %d/%d chunks" % (seq, total),
                    slot,
                    ACCENT,
                    progress=pct,
                    show_bar=True,
                )
                self._note(stripped)
                return
            if "Saved" in line:
                self._set_card("join", "Saved - ready to start", stripped, GREEN, progress=100, done=True)
                self._note(stripped)
                return
            self._note(stripped)
            return
        if "[MP][ERROR]" in line:
            self._set_card("join", "Save failed", stripped, RED)
            self._note(stripped, kind="error")
            return
        self._note(stripped)

    def _on_join_done(self, slot, path, exc=None):
        self._joining = False
        self.joiningChanged.emit(False)
        if exc is not None:
            self._set_card("join", "Join failed", str(exc), RED)
            self._note("Could not receive the save: %s" % exc, kind="error")
            return
        self._set_card("join", "Save received - ready to start",
                       "Saved '%s' -> %s" % (slot, path), GREEN, progress=100, done=True)
        self._note("Save 'slot_%s' received and saved to %s" % (slot.replace(".save", ""), path))
        self._set_can_join_start(True)

    # --------------------------------------------------------------- launch
    def _canonical_mods_folder(self):
        """Mods folder the game actually reads Sims4Multiplayer.json from.

        Prefer the real EA Documents Mods path. Never trust Temp paths or
        leftover test/repo folders (unit tests once polluted settings.json
        with ``tests/_tmp_canonical_mods``).
        """
        import tempfile

        guessed = ""
        try:
            guessed = (RUNTIME.mods_folder() or "").strip()
        except Exception:
            guessed = ""
        configured = (self._mods or "").strip()
        temp_root = os.path.normcase(os.path.abspath(tempfile.gettempdir()))
        repo_tests = os.path.normcase(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests"))
        )

        def _is_unusable(path):
            if not path:
                return True
            abs_path = os.path.normcase(os.path.abspath(path))
            if abs_path == temp_root or abs_path.startswith(temp_root + os.sep):
                return True
            if abs_path == repo_tests or abs_path.startswith(repo_tests + os.sep):
                return True
            # Must look like a Sims 4 Mods folder when EA path is known.
            leaf = os.path.basename(abs_path.rstrip("\\/"))
            if leaf.lower() != "mods":
                return True
            return False

        if configured and not _is_unusable(configured) and os.path.isdir(configured):
            return configured
        if guessed and not _is_unusable(guessed) and os.path.isdir(guessed):
            if configured and configured != guessed:
                self._note(
                    "Mods path %s is unusable; using %s for config."
                    % (configured, guessed),
                    kind="error",
                )
                self._mods = guessed
                try:
                    self.modsPathChanged.emit(guessed)
                except Exception:
                    pass
            return guessed
        if configured and not _is_unusable(configured):
            return configured
        return None
    def _mod_scripts_root(self, mods):
        return os.path.join(mods, "Sims4Multiplayer", "Scripts")

    def _required_mod_files(self, mods):
        root = self._mod_scripts_root(mods)
        return [
            os.path.join(root, "simmp_client", "sims4_plugin.py"),
            os.path.join(root, "simmp_client", "connectivity.py"),
            os.path.join(root, "simmp_client", "deep", "__init__.py"),
            os.path.join(root, "simmp_client", "deep", "interactions.py"),
            os.path.join(root, "simmp", "messages.py"),
            os.path.join(root, "simmp", "deep", "messages.py"),
        ]

    def _read_json_file(self, path):
        try:
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError, TypeError):
            return None

    def _verify_config_payload(self, config, host, port, name, role):
        """Return a list of human-readable problems with a written config."""
        problems = []
        if not isinstance(config, dict):
            return ["config is missing or not valid JSON"]
        expect_host = str(host).strip()
        expect_port = int(port)
        expect_name = (name or "").strip()
        is_host = role == "host"
        checks = (
            ("host", expect_host, str(config.get("host", "")).strip()),
            ("port", expect_port, config.get("port")),
            ("name", expect_name, str(config.get("name", "")).strip()),
            ("auto_connect", True, config.get("auto_connect")),
            ("deep_hooks", True, config.get("deep_hooks")),
            ("want_host", is_host, config.get("want_host")),
            ("world_sync", False, config.get("world_sync")),
            ("interaction_sync", True, config.get("interaction_sync")),
            ("sync_funds", False, config.get("sync_funds")),
            ("build_sync", False, config.get("build_sync")),
            ("min_players", 2, config.get("min_players")),
        )
        for key, expected, actual in checks:
            if actual != expected:
                problems.append("%s=%r (expected %r)" % (key, actual, expected))
        return problems

    def _installed_mod_has_preconnect(self, mods):
        """True when the installed scripts include the preconnect gate."""
        path = os.path.join(
            self._mod_scripts_root(mods), "simmp_client", "sims4_plugin.py"
        )
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            return False
        return "try_pending_connect" in text and "begin_preconnect_gate" in text

    def _preflight_launch(self, role, host, port, name):
        """Validate Mods path, installed scripts, and written config before launch.

        Returns (ok, errors). On failure the game must not start — otherwise
        players get into a save with stale/temp config and no auto-connect.
        """
        errors = []
        mods = self._canonical_mods_folder()
        if not mods:
            errors.append(
                "No usable Mods folder (Temp paths are rejected). "
                "Set Mods to Documents\\Electronic Arts\\The Sims 4\\Mods."
            )
            return False, errors
        if not os.path.isdir(mods):
            errors.append("Mods folder does not exist: %s" % mods)
            return False, errors

        missing = [path for path in self._required_mod_files(mods) if not os.path.isfile(path)]
        if missing:
            errors.append(
                "Mod scripts incomplete under %s (%d missing). Press Install mod."
                % (self._mod_scripts_root(mods), len(missing))
            )
        elif not self._installed_mod_has_preconnect(mods):
            errors.append(
                "Installed mod is outdated (no preconnect/auto-connect gate). "
                "Press Install mod, then try again."
            )

        targets = [
            os.path.join(mods, "Sims4Multiplayer.json"),
            os.path.join(mods, "Sims4Multiplayer", "Sims4Multiplayer.json"),
        ]
        for target in targets:
            if not os.path.isfile(target):
                errors.append("Config not written: %s" % target)
                continue
            problems = self._verify_config_payload(
                self._read_json_file(target), host, port, name, role
            )
            if problems:
                errors.append(
                    "Config %s is wrong: %s" % (target, "; ".join(problems))
                )

        if role == "host":
            if self.server is None or not self.server.thread_alive():
                errors.append("Lobby server is not running.")
            else:
                try:
                    actual = int(self.server.actual_port)
                    if int(port) != actual:
                        errors.append(
                            "Config port %s does not match lobby port %s"
                            % (port, actual)
                        )
                except (TypeError, ValueError):
                    errors.append("Lobby port is invalid.")
        else:
            if not str(host).strip():
                errors.append("Join IP is empty.")
            try:
                p = int(port)
                if not (0 < p < 65536):
                    errors.append("Join port out of range: %s" % port)
            except (TypeError, ValueError):
                errors.append("Join port is invalid: %s" % port)

        return (not errors), errors

    def _write_config(self, host, port, name, role="join"):
        """Write Sims4Multiplayer.json for a deep-hooks session.

        Host claims simulation authority (`want_host`); joiners relay UI
        intent and do not claim. Legacy sampler sync (world / interaction /
        funds / build) is turned off so it does not fight deep hooks.

        Returns the Mods folder written to, or None on failure.
        """
        mods = self._canonical_mods_folder()
        if not mods:
            self._note("No Mods folder set - cannot write auto-connect config.", kind="error")
            return None
        config_dir = os.path.join(mods, "Sims4Multiplayer")
        os.makedirs(config_dir, exist_ok=True)
        is_host = role == "host"
        config = {
            "host": host,
            "port": int(port),
            "name": name,
            "auto_connect": True,
            "min_players": 2,
            # Deep host-authoritative path (primary).
            "deep_hooks": True,
            "want_host": is_host,
            # Interaction mirror stays on so peers see Sleep/Sit/etc.
            # (deep pie-menu relay does not fan out host autonomy sleep).
            "world_sync": False,
            "interaction_sync": True,
            "sync_funds": False,
            "build_sync": False,
        }
        targets = [
            os.path.join(mods, "Sims4Multiplayer.json"),
            os.path.join(config_dir, "Sims4Multiplayer.json"),
        ]
        for target in targets:
            try:
                with open(target, "w", encoding="utf-8") as handle:
                    json.dump(config, handle, indent=2)
            except OSError as exc:
                self._note("Could not write config %s: %s" % (target, exc), kind="error")
                return None
        self._note(
            "Auto-connect config written to %s for %s:%s (name: %s, deep %s)"
            % (mods, host, port, name, "host" if is_host else "joiner")
        )
        return mods

    def _launch_game(self, role, config_host, config_port):
        name = (self._host_name if role == "host" else self._join_name).strip() or role.title()
        if self._write_config(config_host, config_port, name, role=role) is None:
            self._note("Launch blocked: could not write Sims4Multiplayer.json.", kind="error")
            return False
        ok, errors = self._preflight_launch(role, config_host, config_port, name)
        if not ok:
            self._note("Launch blocked — fix these before starting the game:", kind="error")
            for err in errors:
                self._note("  • %s" % err, kind="error")
            self._note(
                "Tip: Mods must be Documents\\...\\Mods (not Temp). "
                "Use Install mod, then Start Game again.",
                kind="error",
            )
            return False
        self._note("Preflight OK — Mods, deep config, and scripts look ready.")
        game = self._game.strip()
        if game and os.path.isfile(game):
            try:
                subprocess.Popen([game])
                self._note("Launched %s" % game)
            except Exception as exc:  # noqa: BLE001
                self._note("Failed to launch %s: %s" % (game, exc), kind="error")
                return False
        else:
            try:
                os.startfile("steam://rungameid/%s" % RUNTIME.steam_game_id())  # noqa: 601
                self._note("Launched The Sims 4 via Steam (game files not found).")
            except Exception as exc:  # noqa: BLE001
                self._note("Could not launch the game: %s" % exc, kind="error")
                return False
        self._note("The game should auto-connect to %s:%s on startup." % (config_host, config_port))
        return True

    @Slot()
    def startGameHost(self):
        if self.server is None or not self.server.thread_alive():
            self._note("Start the lobby first.", kind="error")
            return
        # Keep the lobby TCP seat connected so the GUI stays in the room;
        # it is tagged lobby=true and does not block the in-game clock gate.
        self._note("Starting the game on the host side...")
        if self._launch_game("host", "127.0.0.1", self.server.actual_port):
            self._set_can_host_start(False)

    @Slot()
    def startGameJoin(self):
        host = self._join_ip.strip()
        port = self._join_port.strip()
        # Keep the join lobby seat connected (lobby=true) while the game
        # auto-connects with its own in-game client.
        self._note("Starting the game on the join side...")
        if self._launch_game("join", host or "127.0.0.1", port or DEFAULT_PORT):
            self._set_can_join_start(False)

    # ---------------------------------------------------------- status helpers
    def _disconnect_held(self, *names):
        names = names or ("_share_client", "_join_client")
        for name in names:
            client = getattr(self, name, None)
            if client is not None:
                try:
                    client.disconnect()
                except Exception:
                    pass
                setattr(self, name, None)

    def _current_ip(self):
        if getattr(self, "_lan_ips", None) and len(self._lan_ips) > getattr(self, "_lan_ip_index", 0):
            return self._lan_ips[self._lan_ip_index]
        return "?"

    def _set_card(self, card, phase, detail, color, progress=0, show_bar=False, done=False):
        self.cardStatus.emit(card, phase, detail, color, int(progress), show_bar, done)

    def _set_players(self, count):
        if count != self._connected_players:
            self._connected_players = count
            self.playerCountChanged.emit(count)

    def _set_can_share(self, value):
        if value != self._can_share:
            self._can_share = bool(value)
            self.canShareChanged.emit(self._can_share)

    def _set_can_host_start(self, value):
        if value != self._can_host_start:
            self._can_host_start = bool(value)
            self.canHostStartChanged.emit(self._can_host_start)

    def _set_can_join_start(self, value):
        if value != self._can_join_start:
            self._can_join_start = bool(value)
            self.canJoinStartChanged.emit(self._can_join_start)