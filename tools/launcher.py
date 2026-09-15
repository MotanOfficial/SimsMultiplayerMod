"""Sims 4 Multiplayer launcher - host/join lobby with auto-setup (stdlib only).

Runs completely offline: game-path detection, mod auto-install, an embedded
lobby server, one-click save sharing, and game launch. Designed to be bundled
into a single .exe via ``tools/build_app.py`` (PyInstaller); no third-party
runtime dependencies.

Flow:
   Host:   Start lobby -> friends join via the shown LAN IP -> pick a save ->
           Share save -> save pops on every joiner -> Start Game.
   Join:   enter host IP -> Join -> save lands in your saves folder ->
           Start Game.

After either side presses "Start Game" a ``Sims4Multiplayer.json`` is written
into the Mods folder so the game auto-connects on boot, and the game exe (or
the Steam fallback) is launched.
"""

import ctypes
import json
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from save_metadata import SlotMeta, human_size, human_time  # noqa: E402
from tools.game_paths import (  # noqa: E402
    ts4_user_folder,
    mods_folder,
    saves_folder,
    game_executable,
    steam_game_id,
)
from tools import lobby  # noqa: E402

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

BG = "#131418"
PANEL = "#1a1d24"
FIELD = "#21262f"
BORDER = "#2c313c"
FG = "#d7dbe2"
MUTED = "#8b93a1"
ACCENT = "#5b8cff"
ACCENT_HOVER = "#729bff"
GREEN = "#46b880"
RED = "#e44c4c"
FONT = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_BIG = ("Segoe UI", 11, "bold")
FONT_MONO = ("Consolas", 9)

RUNTIME_DIR = os.path.join(os.environ.get("TEMP") or os.path.expanduser("~"), "simmp-launcher")
STATUS_FILE = os.path.join(RUNTIME_DIR, "status.json")
SERVER_LOG_FILE = os.path.join(RUNTIME_DIR, "server.log")
SETTINGS_FILE = os.path.join(RUNTIME_DIR, "settings.json")
DEFAULT_PORT = 8765


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


class LauncherApp(object):
    def __init__(self, root):
        self.root = root
        root.title("Sims 4 Multiplayer - Lobby")
        root.configure(bg=BG)
        root.geometry("880x720")
        root.minsize(760, 600)

        os.makedirs(RUNTIME_DIR, exist_ok=True)
        self.settings = _load_settings()
        self.server = None
        self.push_thread = None
        self.join_thread = None
        self.selected_save = None
        self.synced = False
        self.slot_meta = None
        self.log_queue = queue.Queue()
        self._pending_state = {}

        self._build_widgets()
        self._apply_style()
        self._auto_detect()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(150, self._poll_queue)

    # ------------------------------------------------------------------ UI
    def _apply_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(14, 6))
        style.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", "#ffffff")])
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=FG, font=FONT)
        style.configure("Panel.TLabel", background=PANEL, foreground=FG, font=FONT)
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=FONT)
        style.configure("Title.TLabel", background=BG, foreground=FG, font=FONT_TITLE)
        style.configure("Big.TLabel", background=PANEL, foreground=FG, font=FONT_BIG)
        style.configure("Action.TButton", background=ACCENT, foreground="#ffffff", font=FONT_BOLD, padding=(10, 6))
        style.map("Action.TButton", background=[("active", ACCENT_HOVER)])
        style.configure("TButton", background=PANEL, foreground=FG, font=FONT, padding=(10, 5))
        style.map("TButton", background=[("active", "#232833")])
        style.configure("TEntry", fieldbackground=FIELD, foreground=FG, insertcolor=FG, bordercolor=BORDER)
        style.configure("TCombobox", fieldbackground=FIELD, foreground=FG, background=FIELD, arrowcolor=FG)
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=FIELD)

    def _build_widgets(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(header, text="Sims 4 Multiplayer", bg=BG, fg=FG, font=FONT_TITLE).pack(side="left")
        tk.Label(
            header,
            text="LAN co-op lobby - host or join a session",
            bg=BG,
            fg=MUTED,
            font=FONT,
        ).pack(side="left", padx=(12, 0), pady=(6, 0))

        self._build_setup_frame()
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=16)
        self._host_tab()
        self._join_tab()
        self._log_frame()

    def _setup_row(self, parent, label, key):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, bg=PANEL, fg=MUTED, width=12, anchor="w", font=FONT).pack(side="left")
        entry = ttk.Entry(row)
        entry.pack(side="left", fill="x", expand=True, ipady=3)
        var = tk.StringVar()
        entry.configure(textvariable=var)
        tk.Button(
            row,
            text="Auto",
            command=lambda: self._auto_fill(key),
            bg=PANEL,
            fg=ACCENT,
            activebackground=PANEL,
            activeforeground=ACCENT_HOVER,
            relief="flat",
            font=FONT_BOLD,
        ).pack(side="left", padx=(6, 2))
        tk.Button(
            row,
            text="Browse",
            command=lambda: self._browse(key),
            bg=PANEL,
            fg=ACCENT,
            activebackground=PANEL,
            activeforeground=ACCENT_HOVER,
            relief="flat",
            font=FONT_BOLD,
        ).pack(side="left")
        setattr(self, "var_%s" % key, var)
        return row

    def _build_setup_frame(self):
        frame = tk.Frame(self.root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="x", padx=16, pady=6)
        self._setup_frame = frame
        self._setup_row(frame, "Game files", "game")
        self._setup_row(frame, "Mods folder", "mods")
        self._setup_row(frame, "Saves folder", "saves")
        actions = tk.Frame(frame, bg=PANEL)
        actions.pack(pady=(2, 8))
        tk.Button(
            actions,
            text="Install mod",
            command=self._install_mod,
            bg=ACCENT,
            fg="#ffffff",
            activebackground=ACCENT_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            font=FONT_BOLD,
            padx=18,
            pady=5,
        ).pack(side="left", padx=(0, 8))
        self.setup_status = tk.Label(actions, text="", bg=PANEL, fg=MUTED, font=FONT)
        self.setup_status.pack(side="left")

    def _log_frame(self):
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        tk.Label(footer, text="Activity", bg=BG, fg=MUTED, font=FONT_BOLD).pack(anchor="w")
        self.log_view = tk.Text(
            footer,
            bg=FIELD,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            font=FONT_MONO,
            height=9,
            state="disabled",
            borderwidth=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
        )
        self.log_view.pack(fill="both", expand=True, pady=(4, 0))

    def _host_tab(self):
        tab = tk.Frame(self._notebook, bg=BG)
        self._notebook.add(tab, text="  Host a game  ")
        panel = tk.Frame(tab, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        panel.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(panel, text="Lobby", bg=PANEL, fg=FG, font=FONT_BIG).pack(anchor="w", padx=12, pady=(10, 4))
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=12)
        tk.Label(row, text="Port", bg=PANEL, fg=MUTED, width=12, anchor="w").pack(side="left")
        self.var_host_port = tk.StringVar(value=str(self.settings.get("host_port", DEFAULT_PORT)))
        tk.Spinbox(row, from_=1024, to=65535, textvariable=self.var_host_port, bg=FIELD, fg=FG,
                   insertbackground=FG, relief="flat", width=8, buttonbackground=PANEL).pack(side="left")
        tk.Label(row, text="Your LAN IP", bg=PANEL, fg=MUTED, width=12, anchor="w").pack(side="left", padx=(14, 0))
        self.var_lan_ip = tk.StringVar(value=lobby.find_lan_ip() or "?")
        tk.Label(row, textvariable=self.var_lan_ip, bg=PANEL, fg=ACCENT, font=FONT_MONO).pack(side="left")
        tk.Button(row, text="Copy", command=self._copy_ip, bg=PANEL, fg=ACCENT, relief="flat",
                  activebackground=PANEL, activeforeground=ACCENT_HOVER).pack(side="left", padx=(4, 0))

        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(6, 0))
        tk.Label(row, text="Your name", bg=PANEL, fg=MUTED, width=12, anchor="w").pack(side="left")
        self.var_host_name = tk.StringVar(value=self.settings.get("host_name", "Host"))
        ttk.Entry(row, textvariable=self.var_host_name).pack(side="left", fill="x", expand=True, ipady=3)

        self.lobby_status = tk.Label(
            panel, text="Lobby not running", bg=PANEL, fg=MUTED, font=FONT_BOLD, anchor="w"
        )
        self.lobby_status.pack(fill="x", padx=12, pady=(10, 2))
        self.host_btns = tk.Frame(panel, bg=PANEL)
        self.host_btns.pack(fill="x", padx=12)
        self.btn_start_lobby = tk.Button(
            self.host_btns, text="Start lobby", command=self._start_lobby,
            bg=ACCENT, fg="#ffffff", relief="flat", font=FONT_BOLD, padx=14, pady=6,
        )
        self.btn_start_lobby.pack(side="left")
        self.btn_stop_lobby = tk.Button(
            self.host_btns, text="Stop lobby", command=self._stop_lobby,
            bg=PANEL, fg=RED, relief="flat", font=FONT_BOLD, padx=14, pady=6,
        )
        self.btn_stop_lobby.pack(side="left", padx=(8, 0))
        self.btn_stop_lobby.config(state="disabled")

        tk.Label(panel, text="Save to share", bg=PANEL, fg=FG, font=FONT_BIG).pack(anchor="w", padx=12, pady=(14, 4))
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=12)
        self.var_save = tk.StringVar()
        self.save_combo = ttk.Combobox(row, textvariable=self.var_save, state="readonly", font=FONT)
        self.save_combo.pack(side="left", fill="x", expand=True, ipady=2)
        self.btn_refresh_saves = tk.Button(
            row, text="Refresh", command=self._refresh_saves, bg=PANEL, fg=ACCENT, relief="flat",
            activebackground=PANEL, activeforeground=ACCENT_HOVER,
        ).pack(side="left")
        self.save_combo.bind("<<ComboboxSelected>>", self._on_save_picked)

        self.sync_status = tk.Label(panel, text="No save shared yet", bg=PANEL, fg=MUTED, anchor="w")
        self.sync_status.pack(fill="x", padx=12, pady=(8, 2))
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(0, 10))
        self.btn_share = tk.Button(
            row, text="Share save with players", command=self._share_save,
            bg=PANEL, fg=ACCENT, relief="flat", font=FONT_BOLD, padx=14, pady=6,
            state="disabled",
        )
        self.btn_share.pack(side="left", padx=(0, 8))
        self.btn_host_start = tk.Button(
            row, text="Start game", command=self._start_game_host,
            bg=GREEN, fg="#ffffff", relief="flat", font=FONT_BOLD, padx=18, pady=6,
            state="disabled",
        )
        self.btn_host_start.pack(side="left")

    def _join_tab(self):
        tab = tk.Frame(self._notebook, bg=BG)
        self._notebook.add(tab, text="  Join a game  ")
        panel = tk.Frame(tab, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        panel.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(panel, text="Join a lobby", bg=PANEL, fg=FG, font=FONT_BIG).pack(anchor="w", padx=12, pady=(10, 4))
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=12)
        tk.Label(row, text="Host IP", bg=PANEL, fg=MUTED, width=12, anchor="w").pack(side="left")
        self.var_join_ip = tk.StringVar(value=self.settings.get("join_ip", ""))
        ttk.Entry(row, textvariable=self.var_join_ip).pack(side="left", fill="x", expand=True, ipady=3)

        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(6, 0))
        tk.Label(row, text="Port", bg=PANEL, fg=MUTED, width=12, anchor="w").pack(side="left")
        self.var_join_port = tk.StringVar(value=str(self.settings.get("join_port", DEFAULT_PORT)))
        port_entry = ttk.Entry(row, textvariable=self.var_join_port, width=16)
        port_entry.pack(side="left", ipady=3)
        tk.Label(row, text="Your name", bg=PANEL, fg=MUTED, width=10, anchor="w").pack(side="left", padx=(14, 0))
        self.var_join_name = tk.StringVar(value=self.settings.get("join_name", "Player"))
        ttk.Entry(row, textvariable=self.var_join_name).pack(side="left", fill="x", expand=True, ipady=3)

        self.join_status = tk.Label(panel, text="Not joined", bg=PANEL, fg=MUTED, font=FONT_BOLD, anchor="w")
        self.join_status.pack(fill="x", padx=12, pady=(10, 2))
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(0, 12))
        self.btn_join = tk.Button(
            row, text="Join lobby", command=self._join_lobby,
            bg=ACCENT, fg="#ffffff", relief="flat", font=FONT_BOLD, padx=14, pady=6,
        )
        self.btn_join.pack(side="left")
        self.btn_join_start = tk.Button(
            row, text="Start game", command=self._start_game_join,
            bg=GREEN, fg="#ffffff", relief="flat", font=FONT_BOLD, padx=18, pady=6,
            state="disabled",
        )
        self.btn_join_start.pack(side="left", padx=(8, 0))
        self._refresh_saves()

    # --------------------------------------------------------------- setup
    def _guess(self, key):
        if key == "game":
            return game_executable() or ""
        if key == "mods":
            return mods_folder() or ""
        if key == "saves":
            return saves_folder() or ""
        return ""

    def _auto_fill(self, key):
        value = self._guess(key)
        getattr(self, "var_%s" % key).set(value)
        self._note("Auto-detected %s: %s" % (key, value or "(not found)"))
        if key == "saves":
            self._refresh_saves()

    def _browse(self, key):
        var = getattr(self, "var_%s" % key)
        current = var.get()
        if key == "game":
            chosen = filedialog.askopenfilename(
                title="Locate TS4_x64.exe",
                filetypes=[("The Sims 4", "TS4_x64.exe")],
                initialdir=os.path.dirname(current) if current else None,
            )
        else:
            chosen = filedialog.askdirectory(
                title="Choose %s" % key,
                initialdir=current or None,
            )
        if chosen:
            var.set(chosen)
            if key == "saves":
                self._refresh_saves()

    def _auto_detect(self):
        for key in ("game", "mods", "saves"):
            if not getattr(self, "var_%s" % key).get():
                getattr(self, "var_%s" % key).set(self._guess(key) or "")
        self._refresh_saves()

    def _mods_path(self):
        return self.var_mods.get().strip() or None

    def _saves_path(self):
        return self.var_saves.get().strip() or None

    def _install_mod(self):
        mods = self._mods_path()
        if not mods:
            self.setup_status.config(text="No Mods folder set", fg=RED)
            return
        def work():
            try:
                sys.path.insert(0, os.path.join(ROOT, "client_mod"))
                import build_script_mod
                build_script_mod.cmd_dev(mods)
                self._post(lambda: self.setup_status.config(
                    text="Mod installed into %s" % os.path.join(mods, "Sims4Multiplayer"), fg=GREEN))
            except Exception as exc:  # noqa: BLE001
                self._post(lambda: self.setup_status.config(text="Install failed: %s" % exc, fg=RED))
        threading.Thread(target=work, daemon=True).start()
        self.setup_status.config(text="Installing...", fg=MUTED)

    # ----------------------------------------------------------------- saves
    def _slot_items(self):
        paths = self._saves_path()
        if not paths:
            return []
        cache_dir = os.path.join(RUNTIME_DIR, "thumbs")
        self.slot_meta = SlotMeta(paths, cache_dir)
        items = []
        try:
            names = [
                n for n in os.listdir(paths)
                if n.startswith("Slot_") and n.endswith(".save") and "BACKUP" not in n
            ]
        except OSError:
            return []
        for name in names:
            full = os.path.join(paths, name)
            try:
                st = os.stat(full)
            except OSError:
                continue
            slot_id = name[len("Slot_"):-len(".save")]
            label = self.slot_meta.labels.get(slot_id, "")
            line = "%s  %s  %s" % (
                name,
                label or "",
                "%s  %s" % (human_size(st.st_size), human_time(st.st_mtime)),
            )
            items.append((line, name, full))
        items.sort(key=lambda it: os.stat(it[2]).st_mtime, reverse=True)
        return items

    def _refresh_saves(self):
        items = self._slot_items()
        self._save_items = items
        if items:
            self.save_combo["values"] = [line for line, _, _ in items]
            self._selected_slot_path = items[0][2]
            self.selected_save = self._selected_slot_path
        else:
            self.save_combo["values"] = []
            self.selected_save = None

    def _on_save_picked(self, _event=None):
        current = self.var_save.get()
        for line, file_, path in self._save_items:
            if line == current:
                self.selected_save = path
                self._note("Selected save: %s (%s)" % (file_, path))
                self.synced = False
                self._update_host_start_button()
                return

    # ----------------------------------------------------------------- lobby
    def _start_lobby(self):
        try:
            port = int(self.var_host_port.get().strip() or DEFAULT_PORT)
        except ValueError:
            self._note("Port must be a number.", kind="error")
            return
        if self.server is not None and self.server.thread_alive():
            self._note("Lobby already running.")
            return
        self._note("Opening lobby on port %s..." % port)
        self.server = lobby.ServerHandle(
            host="0.0.0.0",
            port=port,
            status_file=STATUS_FILE,
            log_file=SERVER_LOG_FILE,
            log_level="INFO",
            on_status=self._on_status,
            on_log=lambda line: self._post(lambda: self._note(line)),
        )
        if not self.server.start():
            self._note("Failed to bind port %s - is it already in use?" % port, kind="error")
            self.server = None
            return
        self.var_host_port.set(str(self.server.actual_port))
        self.btn_start_lobby.config(state="disabled")
        self.btn_stop_lobby.config(state="normal")
        self.lobby_status.config(text="Lobby open at %s:%s - tell the other PC to join" % (
            self.var_lan_ip.get(), self.server.actual_port), fg=GREEN)
        self._note("Windows firewall may ask for permission - allow it so friends can join.")

    def _stop_lobby(self):
        if self.server is not None:
            self.server.stop()
            self.server = None
        self.synced = False
        self.btn_start_lobby.config(state="normal")
        self.btn_stop_lobby.config(state="disabled")
        self.lobby_status.config(text="Lobby stopped", fg=MUTED)
        self.btn_share.config(state="disabled")
        self._update_host_start_button()

    def _on_status(self, data):
        self._post(lambda: self._apply_status(data))

    def _apply_status(self, data):
        players = data.get("players") or []
        connected = [p for p in players if p.get("connected")]
        if self.server is not None and self.server.thread_alive():
            self.lobby_status.config(
                text="Lobby open at %s:%s - %d player(s) connected%s" % (
                    self.var_lan_ip.get(),
                    self.server.actual_port,
                    len(connected),
                    "  (%s)" % ", ".join(p.get("name", "?") for p in connected) if connected else "",
                ),
                fg=GREEN,
            )
            if connected and self.server and self.server.thread_alive():
                if self.selected_save and not self.synced:
                    self.btn_share.config(state="normal")
                self._update_host_start_button()

    def _player_count(self):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return len([p for p in data.get("players", []) if p.get("connected")])
        except Exception:
            return 0

    def _share_save(self):
        if self.selected_save is None:
            self._note("Pick a save to share first.", kind="error")
            return
        if self.server is None or not self.server.thread_alive():
            self._note("Start the lobby first.", kind="error")
            return
        self.btn_share.config(state="disabled")
        self.sync_status.config(text="Sharing save...", fg=MUTED)
        host = "127.0.0.1"
        port = self.server.actual_port
        path = self.selected_save
        name = self.var_host_name.get().strip() or "Host"
        def work():
            try:
                ok, reached = lobby.push_save_file(path, host, port, name=name, timeout=60.0)
                self._post(lambda: self._on_share_done(ok, reached))
            except Exception as exc:  # noqa: BLE001
                self._post(lambda: self._on_share_done(False, 0, exc))
        threading.Thread(target=work, daemon=True).start()

    def _on_share_done(self, ok, reached, exc=None):
        if exc is not None:
            self.sync_status.config(text="Share failed: %s" % exc, fg=RED)
            return
        if ok and reached >= 1:
            self.synced = True
            self.sync_status.config(
                text="Save synced to %d player(s). They can press Start game now." % reached, fg=GREEN)
            self.btn_share.config(state="normal")
        else:
            self.sync_status.config(
                text="No connected players yet - keep the lobby open and try again.", fg=RED)
            self.btn_share.config(state="normal")
        self._update_host_start_button()

    def _update_host_start_button(self):
        if self.synced and self._player_count() >= 1:
            self.btn_host_start.config(state="normal")
        else:
            self.btn_host_start.config(state="disabled")

    # -------------------------------------------------------------------- join
    def _join_lobby(self):
        host = self.var_join_ip.get().strip()
        try:
            port = int(self.var_join_port.get().strip() or DEFAULT_PORT)
        except ValueError:
            self._note("Port must be a number.", kind="error")
            return
        if not host:
            self._note("Enter the host's IP address.", kind="error")
            return
        ts4_user = ts4_user_folder()
        if ts4_user:
            os.environ["SIM4_MP_SAVE_ROOT"] = ts4_user
        name = self.var_join_name.get().strip() or "Player"
        self.btn_join.config(state="disabled", text="Joining...")
        self.join_status.config(text="Connecting to %s:%s..." % (host, port), fg=MUTED)
        self._note("Joining %s:%s - waiting for the host to share the save..." % (host, port))
        def work():
            try:
                slot, path = lobby.receive_save_file(host, port, name=name, timeout=120.0)
                self._post(lambda: self._on_join_done(slot, path))
            except Exception as exc:  # noqa: BLE001
                self._post(lambda: self._on_join_done(None, None, exc))
        self.join_thread = threading.Thread(target=work, daemon=True)
        self.join_thread.start()

    def _on_join_done(self, slot, path, exc=None):
        self.btn_join.config(state="normal", text="Join lobby")
        if exc is not None:
            self.join_status.config(text="Join failed: %s" % exc, fg=RED)
            self._note("Could not receive the save: %s" % exc, kind="error")
            return
        self.join_status.config(text="Joined. Save '%s' received -> %s" % (slot, path), fg=GREEN)
        self._note("Save 'slot_%s' received and saved to %s" % (slot.replace(".save", ""), path))
        self.btn_join_start.config(state="normal")

    # --------------------------------------------------------------- start game
    def _write_config(self, host, port, name):
        mods = self._mods_path()
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
        name = (self.var_host_name if role == "host" else self.var_join_name).get().strip() or role.title()
        self._write_config(config_host, config_port, name)
        game = self.var_game.get().strip()
        if game and os.path.isfile(game):
            try:
                subprocess.Popen([game])
                self._note("Launched %s" % game)
            except Exception as exc:  # noqa: BLE001
                self._note("Failed to launch %s: %s" % (game, exc), kind="error")
                return
        else:
            try:
                os.startfile("steam://rungameid/%s" % steam_game_id())  # noqa: 601
                self._note("Launched The Sims 4 via Steam (game files not found).")
            except Exception as exc:  # noqa: BLE001
                self._note("Could not launch the game: %s" % exc, kind="error")
        self._note("The game should auto-connect to %s:%s on startup." % (config_host, config_port))

    def _start_game_host(self):
        if self.server is None or not self.server.thread_alive():
            self._note("Start the lobby first.", kind="error")
            return
        self._note("Starting the game on the host side...")
        self._launch_game("host", "127.0.0.1", self.server.actual_port)
        self.btn_host_start.config(state="disabled")

    def _start_game_join(self):
        host = self.var_join_ip.get().strip()
        port = self.var_join_port.get().strip()
        self._note("Starting the game on the join side...")
        self._launch_game("join", host or "127.0.0.1", port or DEFAULT_PORT)
        self.btn_join_start.config(state="disabled")

    # ------------------------------------------------------------------ misc
    def _copy_ip(self):
        ip = self.var_lan_ip.get()
        if ip and ip != "?":
            self.root.clipboard_clear()
            self.root.clipboard_append(ip)
            self._note("Copied %s to clipboard." % ip)

    def _note(self, text, kind="info"):
        line = "%s %s\n" % (time.strftime("[%H:%M:%S]"), text)
        self.log_view.config(state="normal")
        self.log_view.insert("end", line)
        self.log_view.see("end")
        self.log_view.config(state="disabled")

    def _post(self, fn):
        self.log_queue.put(fn)

    def _poll_queue(self):
        try:
            while True:
                fn = self.log_queue.get_nowait()
                try:
                    fn()
                except Exception as exc:  # noqa: BLE001
                    self._note("UI error: %s" % exc, kind="error")
        except queue.Empty:
            pass
        self.root.after(150, self._poll_queue)

    def _on_close(self):
        self._save_settings_callback()
        if self.server is not None:
            self.server.stop()
            self.server = None
        self.root.destroy()

    def _save_settings_callback(self):
        self.settings.update({
            "game": self.var_game.get(),
            "mods": self.var_mods.get(),
            "saves": self.var_saves.get(),
            "host_port": self.var_host_port.get(),
            "host_name": self.var_host_name.get(),
            "join_ip": self.var_join_ip.get(),
            "join_port": self.var_join_port.get(),
            "join_name": self.var_join_name.get(),
        })
        _save_settings(self.settings)


def main():
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()