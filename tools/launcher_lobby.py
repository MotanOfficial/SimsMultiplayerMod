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
        names = ", ".join(p.get("name", "?") for p in connected)
        self._set_card(
            "lobby",
            "Lobby open at %s:%s" % (self._current_ip(), self.server.actual_port),
            ("%d player(s) connected: %s" % (len(connected), names)) if connected
            else "Waiting for players to join...",
            GREEN if connected else MUTED,
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
            try:
                ok, reached = RUNTIME.lobby.push_save_file(
                    self._selected_save,
                    "127.0.0.1",
                    self.server.actual_port,
                    name=name,
                    timeout=60.0,
                    on_line=on_line,
                )
                self._on_share_done(ok, reached)
            except Exception as exc:  # noqa: BLE001
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
        self._set_can_host_start(self._synced and self._player_count() >= 1)

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
            try:
                slot, path = RUNTIME.lobby.receive_save_file(
                    host,
                    port,
                    name=name,
                    timeout=120.0,
                    on_connected=on_connected,
                    on_line=on_line,
                )
                self._on_join_done(slot, path)
            except Exception as exc:  # noqa: BLE001
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
    def _write_config(self, host, port, name):
        mods = self._mods.strip() or None
        if not mods:
            self._note("No Mods folder set - cannot write auto-connect config.", kind="error")
            return
        config_dir = os.path.join(mods, "Sims4Multiplayer")
        os.makedirs(config_dir, exist_ok=True)
        config = {
            "host": host,
            "port": int(port),
            "name": name,
            "auto_connect": True,
            "min_players": 2,
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
        self._note("Auto-connect config written for %s:%s (name: %s)" % (host, port, name))

    def _launch_game(self, role, config_host, config_port):
        name = (self._host_name if role == "host" else self._join_name).strip() or role.title()
        self._write_config(config_host, config_port, name)
        game = self._game.strip()
        if game and os.path.isfile(game):
            try:
                subprocess.Popen([game])
                self._note("Launched %s" % game)
            except Exception as exc:  # noqa: BLE001
                self._note("Failed to launch %s: %s" % (game, exc), kind="error")
                return
        else:
            try:
                os.startfile("steam://rungameid/%s" % RUNTIME.steam_game_id())  # noqa: 601
                self._note("Launched The Sims 4 via Steam (game files not found).")
            except Exception as exc:  # noqa: BLE001
                self._note("Could not launch the game: %s" % exc, kind="error")
        self._note("The game should auto-connect to %s:%s on startup." % (config_host, config_port))

    @Slot()
    def startGameHost(self):
        if self.server is None or not self.server.thread_alive():
            self._note("Start the lobby first.", kind="error")
            return
        self._note("Starting the game on the host side...")
        self._launch_game("host", "127.0.0.1", self.server.actual_port)
        self._set_can_host_start(False)

    @Slot()
    def startGameJoin(self):
        host = self._join_ip.strip()
        port = self._join_port.strip()
        self._note("Starting the game on the join side...")
        self._launch_game("join", host or "127.0.0.1", port or DEFAULT_PORT)
        self._set_can_join_start(False)

    # ---------------------------------------------------------- status helpers
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