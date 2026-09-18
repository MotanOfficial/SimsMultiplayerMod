"""Sims 4 Multiplayer launcher - host/join lobby with auto-setup (stdlib only).

Runs completely offline-safe: game-path detection, mod auto-install, an
embedded lobby server, one-click save sharing, and game launch. Designed to
be bundled into a single .exe via ``tools/build_app.py`` (PyInstaller); no
third-party runtime dependencies.

The .exe is a thin bootstrap. The actual runtime code (server, protocol,
mod source, tools) is synced incrementally from the public GitHub repo into
``%LOCALAPPDATA%\\Sims4Multiplayer\\runtime`` by ``tools/updater.py`` and is
mounted over the frozen copies at startup, so an update to the app + mod is
a handful of small downloaded files - never a fresh .exe.

Flow:
   Host:   Start lobby -> friends join via the shown LAN IP -> pick a save ->
           Share save -> save pops on every joiner -> Start Game.
   Join:   enter host IP -> Join -> save lands in your saves folder ->
           Start Game.

After either side presses "Start Game" a ``Sims4Multiplayer.json`` is written
into the Mods folder so the game auto-connects on boot, and the game exe (or
the Steam fallback) is launched.

Updates: with ``auto_update`` on (default), the launcher checks the GitHub
manifest on every start, pulls only changed runtime files, and reinstalls the
mod into the configured Mods folder. "Check updates" forces a check.
"""

import ctypes
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog

ROOT = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from tools import updater  # noqa: E402

CODE_ROOT = updater.runtime_data_root()

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

BG = "#12141a"
PANEL = "#191c24"
FIELD = "#20242e"
BORDER = "#2b303c"
FG = "#e3e8ef"
MUTED = "#8f97a5"
ACCENT = "#4f8cff"
ACCENT_HOVER = "#6fa3ff"
GREEN = "#3ecf8e"
RED = "#ff5f57"
AMBER = "#ffb454"
FONT = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_SEMI = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 15, "bold")
FONT_BIG = ("Segoe UI", 12, "bold")
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
        root.geometry("900x780")
        root.minsize(780, 640)

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
        self._connected_players = 0

        _load_app_modules()
        self._build_widgets()
        self._apply_style()
        self._auto_detect()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(150, self._poll_queue)
        self.root.after(400, self._maybe_check_updates)

    # ------------------------------------------------------------------ UI
    def _apply_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(16, 8), font=FONT_SEMI)
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
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=FIELD,
            background=ACCENT,
            bordercolor=BORDER,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            thickness=10,
        )
        style.configure(
            "Done.Horizontal.TProgressbar",
            troughcolor=FIELD,
            background=GREEN,
            bordercolor=BORDER,
            lightcolor=GREEN,
            darkcolor=GREEN,
            thickness=10,
        )

    def _build_widgets(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=16, pady=(14, 6))
        accent = tk.Frame(header, bg=ACCENT, width=4)
        accent.pack(side="left", fill="y", padx=(0, 12))
        accent.pack_propagate(False)
        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left", fill="y")
        tk.Label(titles, text="Sims 4 Multiplayer", bg=BG, fg=FG, font=FONT_TITLE).pack(anchor="w")
        tk.Label(
            titles,
            text="LAN co-op lobby - host or join a session",
            bg=BG,
            fg=MUTED,
            font=FONT,
        ).pack(anchor="w")

        self._build_setup_frame()
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=16, pady=(4, 0))
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
        frame.pack(fill="x", padx=16, pady=(6, 6))
        self._setup_frame = frame
        self._section(frame, "Setup", pady=(10, 6))
        inner = tk.Frame(frame, bg=PANEL)
        inner.pack(fill="x", padx=14)
        self._setup_row(inner, "Game files", "game")
        self._setup_row(inner, "Mods folder", "mods")
        self._setup_row(inner, "Saves folder", "saves")
        actions = tk.Frame(frame, bg=PANEL)
        actions.pack(fill="x", padx=14, pady=(6, 4))
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
        tk.Button(
            actions,
            text="Check updates",
            command=self._manual_check_updates,
            bg=PANEL,
            fg=ACCENT,
            activebackground=PANEL,
            activeforeground=ACCENT_HOVER,
            relief="flat",
            font=FONT_BOLD,
            padx=14,
            pady=5,
        ).pack(side="left", padx=(0, 14))
        self._auto_update_var = tk.BooleanVar(value=bool(self.settings.get("auto_update", True)))
        tk.Checkbutton(
            actions,
            text="Auto-update",
            variable=self._auto_update_var,
            command=self._save_auto_update_setting,
            bg=PANEL,
            fg=FG,
            selectcolor=FIELD,
            activebackground=PANEL,
            activeforeground=FG,
        ).pack(side="left", padx=(0, 14))
        self.setup_status = tk.Label(actions, text="", bg=PANEL, fg=MUTED, font=FONT)
        self.setup_status.pack(side="left")
        row2 = tk.Frame(frame, bg=PANEL)
        row2.pack(fill="x", padx=12, pady=(0, 4))
        self.update_status = tk.Label(row2, text="", bg=PANEL, fg=MUTED, font=FONT)
        self.update_status.pack(anchor="w")

    def _log_frame(self):
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="both", expand=True, padx=16, pady=(8, 12))
        header = tk.Frame(footer, bg=BG)
        header.pack(fill="x")
        tk.Label(header, text="ACTIVITY", bg=BG, fg=MUTED, font=FONT_SEMI).pack(side="left")
        tk.Button(
            header, text="Clear", command=self._clear_log, bg=BG, fg=ACCENT, relief="flat",
            activebackground=BG, activeforeground=ACCENT_HOVER, cursor="hand2", font=FONT_BOLD,
        ).pack(side="right")
        self.log_view = tk.Text(
            footer,
            bg="#0f1116",
            fg=FG,
            insertbackground=FG,
            relief="flat",
            font=FONT_MONO,
            height=8,
            state="disabled",
            borderwidth=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
            padx=8,
            pady=6,
        )
        self.log_view.pack(fill="both", expand=True, pady=(4, 0))

    def _clear_log(self):
        self.log_view.config(state="normal")
        self.log_view.delete("1.0", "end")
        self.log_view.config(state="disabled")

    def _section(self, parent, text, pady=(12, 4)):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=14, pady=pady)
        tk.Label(row, text=text.upper(), bg=PANEL, fg=MUTED, font=FONT_SEMI).pack(side="left")
        tk.Frame(row, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, padx=(8, 0), pady=(6, 0))

    def _progress_row(self, parent, bg=FIELD):
        row = tk.Frame(parent, bg=bg)
        bar = ttk.Progressbar(row, style="Horizontal.TProgressbar", mode="determinate", maximum=100)
        pct = tk.Label(row, text="", bg=bg, fg=MUTED, font=FONT_MONO, width=5, anchor="e")
        bar.pack(side="left", fill="x", expand=True)
        pct.pack(side="left", padx=(8, 0))
        return row, bar, pct

    def _status_card(self, parent):
        """A phase card: colored strip + phase line + detail + progress bar."""
        outer = tk.Frame(parent, bg=PANEL)
        outer.pack(fill="x", padx=14, pady=(6, 6))
        strip = tk.Frame(outer, bg=MUTED, width=4)
        strip.pack(side="left", fill="y")
        inner = tk.Frame(outer, bg=FIELD, highlightbackground=BORDER, highlightthickness=1)
        inner.pack(side="left", fill="x", expand=True)
        phase = tk.Label(inner, text="", bg=FIELD, fg=FG, font=FONT_SEMI, anchor="w", justify="left")
        phase.pack(fill="x", padx=12, pady=(9, 0))
        detail = tk.Label(inner, text="", bg=FIELD, fg=MUTED, anchor="w", justify="left", wraplength=680, font=FONT)
        detail.pack(fill="x", padx=12)
        row, bar, pct = self._progress_row(inner, FIELD)
        row.pack(fill="x", padx=12, pady=(8, 10))
        return {"strip": strip, "inner": inner, "phase": phase, "detail": detail,
                "row": row, "bar": bar, "pct": pct}

    def _set_status(self, card, phase, detail=None, color=MUTED, progress=None, done=False):
        card["strip"].configure(bg=color)
        card["phase"].configure(text=phase, fg=FG if color == MUTED else color)
        if detail is not None:
            card["detail"].configure(text=detail)
        if progress is None:
            card["row"].pack_forget()
            return
        card["row"].pack(fill="x", padx=12, pady=(8, 10))
        value = max(0, min(100, int(progress)))
        card["bar"].configure(style="Done.Horizontal.TProgressbar" if done else "Horizontal.TProgressbar")
        card["bar"]["value"] = value
        card["pct"].configure(text=("%d%%" % value) if not done else "100%", fg=GREEN if done else MUTED)

    def _host_tab(self):
        tab = tk.Frame(self._notebook, bg=BG)
        self._notebook.add(tab, text="  Host a game  ")
        panel = tk.Frame(tab, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        panel.pack(fill="both", expand=True, padx=12, pady=12)

        self._section(panel, "Lobby", pady=(12, 4))
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=14)
        tk.Label(row, text="Port", bg=PANEL, fg=MUTED, width=11, anchor="w").pack(side="left")
        self.var_host_port = tk.StringVar(value=str(self.settings.get("host_port", DEFAULT_PORT)))
        tk.Spinbox(row, from_=1024, to=65535, textvariable=self.var_host_port, bg=FIELD, fg=FG,
                   insertbackground=FG, relief="flat", width=8, buttonbackground=PANEL).pack(side="left")
        tk.Label(row, text="Your LAN IP", bg=PANEL, fg=MUTED, width=12, anchor="w").pack(side="left", padx=(16, 0))
        self.var_lan_ip = tk.StringVar(value=lobby.find_lan_ip() or "?")
        self.lan_ip_combo = ttk.Combobox(row, textvariable=self.var_lan_ip, font=FONT_MONO, width=18)
        self.lan_ip_combo.pack(side="left")
        self.lan_ip_combo["values"] = lobby.all_lan_ips() or ["?"]
        tk.Button(row, text="Copy", command=self._copy_ip, bg=PANEL, fg=ACCENT, relief="flat",
                  activebackground=PANEL, activeforeground=ACCENT_HOVER, cursor="hand2").pack(side="left", padx=(6, 0))

        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=14, pady=(6, 0))
        tk.Label(row, text="Your name", bg=PANEL, fg=MUTED, width=11, anchor="w").pack(side="left")
        self.var_host_name = tk.StringVar(value=self.settings.get("host_name", "Host"))
        ttk.Entry(row, textvariable=self.var_host_name).pack(side="left", fill="x", expand=True, ipady=3)

        self.lobby_card = self._status_card(panel)
        # Legacy attribute kept as the phase line of the status card.
        self.lobby_status = self.lobby_card["phase"]
        self._set_status(self.lobby_card, "Lobby not running", "Start the lobby, then pick a save to share.")

        self.host_btns = tk.Frame(panel, bg=PANEL)
        self.host_btns.pack(fill="x", padx=14)
        self.btn_start_lobby = tk.Button(
            self.host_btns, text="Start lobby", command=self._start_lobby,
            bg=ACCENT, fg="#ffffff", relief="flat", font=FONT_BOLD, padx=16, pady=6, cursor="hand2",
        )
        self.btn_start_lobby.pack(side="left")
        self.btn_stop_lobby = tk.Button(
            self.host_btns, text="Stop lobby", command=self._stop_lobby,
            bg=PANEL, fg=RED, relief="flat", font=FONT_BOLD, padx=16, pady=6, cursor="hand2",
        )
        self.btn_stop_lobby.pack(side="left", padx=(8, 0))
        self.btn_stop_lobby.config(state="disabled")

        self._section(panel, "Save to share", pady=(16, 4))
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=14)
        self.var_save = tk.StringVar()
        self.save_combo = ttk.Combobox(row, textvariable=self.var_save, state="readonly", font=FONT)
        self.save_combo.pack(side="left", fill="x", expand=True, ipady=2)
        self.btn_refresh_saves = tk.Button(
            row, text="Refresh", command=self._refresh_saves, bg=PANEL, fg=ACCENT, relief="flat",
            activebackground=PANEL, activeforeground=ACCENT_HOVER, cursor="hand2",
        ).pack(side="left", padx=(6, 0))
        self.save_combo.bind("<<ComboboxSelected>>", self._on_save_picked)

        self.share_card = self._status_card(panel)
        self.sync_status = self.share_card["phase"]
        self.share_progress = self.share_card["bar"]
        self._set_status(self.share_card, "No save shared yet",
                         "Choose a save, then share it once a player has joined.")

        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=14, pady=(0, 12))
        self.btn_share = tk.Button(
            row, text="Share save with players", command=self._share_save,
            bg=PANEL, fg=ACCENT, relief="flat", font=FONT_BOLD, padx=16, pady=7,
            state="disabled", cursor="hand2",
        )
        self.btn_share.pack(side="left", padx=(0, 8))
        self.btn_host_start = tk.Button(
            row, text="Start game", command=self._start_game_host,
            bg=GREEN, fg="#0d1f17", relief="flat", font=FONT_BOLD, padx=20, pady=7,
            state="disabled", cursor="hand2",
        )
        self.btn_host_start.pack(side="left")

    def _join_tab(self):
        tab = tk.Frame(self._notebook, bg=BG)
        self._notebook.add(tab, text="  Join a game  ")
        panel = tk.Frame(tab, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        panel.pack(fill="both", expand=True, padx=12, pady=12)

        self._section(panel, "Lobby address", pady=(12, 4))
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=14)
        tk.Label(row, text="Host IP", bg=PANEL, fg=MUTED, width=11, anchor="w").pack(side="left")
        self.var_join_ip = tk.StringVar(value=self.settings.get("join_ip", ""))
        ttk.Entry(row, textvariable=self.var_join_ip).pack(side="left", fill="x", expand=True, ipady=3)

        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=14, pady=(6, 0))
        tk.Label(row, text="Port", bg=PANEL, fg=MUTED, width=11, anchor="w").pack(side="left")
        self.var_join_port = tk.StringVar(value=str(self.settings.get("join_port", DEFAULT_PORT)))
        port_entry = ttk.Entry(row, textvariable=self.var_join_port, width=16)
        port_entry.pack(side="left", ipady=3)
        tk.Label(row, text="Your name", bg=PANEL, fg=MUTED, width=10, anchor="w").pack(side="left", padx=(16, 0))
        self.var_join_name = tk.StringVar(value=self.settings.get("join_name", "Player"))
        ttk.Entry(row, textvariable=self.var_join_name).pack(side="left", fill="x", expand=True, ipady=3)

        self.join_card = self._status_card(panel)
        self.join_status = self.join_card["phase"]
        self.join_detail = self.join_card["detail"]
        self.join_progress = self.join_card["bar"]
        self._set_status(self.join_card, "Not joined", "Enter the host's IP and press Join lobby.")

        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=14, pady=(0, 12))
        self.btn_join = tk.Button(
            row, text="Join lobby", command=self._join_lobby,
            bg=ACCENT, fg="#ffffff", relief="flat", font=FONT_BOLD, padx=16, pady=7, cursor="hand2",
        )
        self.btn_join.pack(side="left")
        self.btn_join_start = tk.Button(
            row, text="Start game", command=self._start_game_join,
            bg=GREEN, fg="#0d1f17", relief="flat", font=FONT_BOLD, padx=20, pady=7,
            state="disabled", cursor="hand2",
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
                self._post(lambda e=exc: self.setup_status.config(text="Install failed: %s" % e, fg=RED))
        threading.Thread(target=work, daemon=True).start()
        self.setup_status.config(text="Installing...", fg=MUTED)

    # ----------------------------------------------------------------- updates
    def _save_auto_update_setting(self):
        self.settings["auto_update"] = bool(self._auto_update_var.get())
        _save_settings(self.settings)

    def _maybe_check_updates(self):
        if not bool(self.settings.get("auto_update", True)):
            self.update_status.config(
                text="Auto-update off - local runtime %s" % (updater.installed_version(CODE_ROOT) or "(none)"),
                fg=MUTED,
            )
            return
        self._check_updates(manual=False)

    def _manual_check_updates(self):
        self._check_updates(manual=True)

    def _check_updates(self, manual=False):
        if getattr(self, "_update_busy", False):
            self._note("Update check already running.")
            return
        self._update_busy = True
        self.update_status.config(text="Checking for updates...", fg=MUTED)
        before = updater.installed_version(CODE_ROOT) or "(none)"

        def work():
            summary = updater.sync(
                updater.base_url(),
                CODE_ROOT,
                log=lambda line: self._post(lambda: self._note("[UP] %s" % line)),
            )
            mods = self.var_mods.get().strip()
            reinstalled = False
            if summary.get("ok") and summary.get("changed") and mods:
                if updater.changed_mod_files(summary["changed"]):
                    try:
                        build_script_mod.cmd_dev(mods)
                        reinstalled = True
                    except Exception as exc:  # noqa: BLE001
                        self._post(lambda e=exc: self._note(
                            "Update downloaded, but mod reinstall into %s failed: %s" % (mods, e),
                            kind="error",
                        ))
            self._post(lambda: self._on_update_done(summary, before, reinstalled))

        threading.Thread(target=work, daemon=True).start()

    def _on_update_done(self, summary, before, reinstalled):
        self._update_busy = False
        if not summary.get("ok"):
            why = summary.get("error") or "no network?"
            self.update_status.config(
                text="Update check failed (%s) - continuing with local runtime %s" % (why, before),
                fg=RED,
            )
            return
        version = summary.get("version") or "?"
        changed = summary.get("changed") or []
        if not changed:
            self.update_status.config(text="Up to date (v%s)" % version, fg=GREEN)
            return
        self.update_status.config(text="Updated to v%s - restart the launcher to apply" % version, fg=GREEN)
        self._note("Runtime updated: %d file(s) changed (%s -> %s)." % (len(changed), before, version))
        if reinstalled:
            self._note("Mod reinstalled into the Mods folder - restart the game to apply.")
        else:
            self._note("Press 'Install mod' to install the updated mod into the game.")

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
        self._set_status(
            self.lobby_card,
            "Lobby open at %s:%s" % (self.var_lan_ip.get(), self.server.actual_port),
            "Tell the other PC to join - waiting for players.",
            color=GREEN,
        )
        self._note("Windows firewall may ask for permission - allow it so friends can join.")

    def _stop_lobby(self):
        if self.server is not None:
            self.server.stop()
            self.server = None
        self.synced = False
        self._connected_players = 0
        self.btn_start_lobby.config(state="normal")
        self.btn_stop_lobby.config(state="disabled")
        self._set_status(self.lobby_card, "Lobby stopped", "Start the lobby, then pick a save to share.")
        self.btn_share.config(state="disabled")
        self._update_host_start_button()

    def _on_status(self, data):
        self._post(lambda: self._apply_status(data))

    def _apply_status(self, data):
        players = data.get("players") or []
        connected = [p for p in players if p.get("connected")]
        self._connected_players = len(connected)
        if self.server is not None and self.server.thread_alive():
            names = ", ".join(p.get("name", "?") for p in connected)
            self._set_status(
                self.lobby_card,
                "Lobby open at %s:%s" % (self.var_lan_ip.get(), self.server.actual_port),
                ("%d player(s) connected: %s" % (len(connected), names)) if connected
                else "Waiting for players to join...",
                color=GREEN if connected else MUTED,
            )
            if connected and self.server and self.server.thread_alive():
                if self.selected_save and not self.synced:
                    self.btn_share.config(state="normal")
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

    def _share_save(self):
        if self.selected_save is None:
            self._note("Pick a save to share first.", kind="error")
            return
        if self.server is None or not self.server.thread_alive():
            self._note("Start the lobby first.", kind="error")
            return
        self.btn_share.config(state="disabled")
        self._set_status(self.share_card, "Sharing save...", os.path.basename(self.selected_save),
                         color=AMBER, progress=0)
        host = "127.0.0.1"
        port = self.server.actual_port
        path = self.selected_save
        name = self.var_host_name.get().strip() or "Host"
        def work():
            try:
                ok, reached = lobby.push_save_file(
                    path, host, port, name=name, timeout=60.0,
                    on_line=lambda line: self._post(lambda l=line: self._share_line(l)),
                )
                self._post(lambda: self._on_share_done(ok, reached))
            except Exception as exc:  # noqa: BLE001
                self._post(lambda e=exc: self._on_share_done(False, 0, e))
        threading.Thread(target=work, daemon=True).start()

    def _share_line(self, line):
        """Surface host-side push progress in the share card, not as red noise."""
        stripped = line.strip()
        if "sync alarm unavailable" in line:
            self._note(stripped)
            return
        match = re.search(r"SAVE_ACK .*?seq=(\d+)/(\d+)", line)
        if match:
            seq, total = int(match.group(1)), int(match.group(2))
            pct = (seq * 100 // total) if total else 100
            self._set_status(
                self.share_card,
                "Sharing save... %d/%d chunks" % (seq, total),
                os.path.basename(self.selected_save or ""),
                color=AMBER, progress=pct,
            )
            self._note(stripped)
            return
        if "[MP][ERROR]" in line:
            self._note(stripped, kind="error")
            return
        self._note(stripped)

    def _on_share_done(self, ok, reached, exc=None):
        if exc is not None:
            self._set_status(self.share_card, "Share failed", str(exc), color=RED)
            return
        if ok:
            # The server caches the save, so a player who joins after this
            # share (or wasn't connected at push time) still receives it.
            self.synced = True
            self.btn_share.config(state="normal")
            if reached >= 1:
                self._set_status(
                    self.share_card, "Save synced to %d player(s)" % reached,
                    "They can press Start game now.", color=GREEN, progress=100, done=True)
            else:
                self._set_status(
                    self.share_card, "Save staged",
                    "Players who join or reconnect will receive it automatically.",
                    color=GREEN, progress=100, done=True)
        else:
            self._set_status(self.share_card, "Share failed",
                             "The lobby server did not accept the save.", color=RED)
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
        self._set_status(self.join_card, "Connecting to %s:%s..." % (host, port),
                         "Waiting for the host to share the save...", color=AMBER, progress=0)
        self._note("Joining %s:%s - waiting for the host to share the save..." % (host, port))

        def _connected():
            self._note("Connected as %s - save request sent to the host's lobby." % name)
            self._set_status(self.join_card, "Connected - waiting for the save",
                             "The host has been asked to share their save.", color=AMBER)

        def work():
            try:
                slot, path = lobby.receive_save_file(
                    host,
                    port,
                    name=name,
                    timeout=120.0,
                    on_connected=lambda: self._post(_connected),
                    on_line=lambda line: self._post(lambda l=line: self._join_line(l)),
                )
                self._post(lambda: self._on_join_done(slot, path))
            except Exception as exc:  # noqa: BLE001
                self._post(lambda e=exc: self._on_join_done(None, None, e))
        self.join_thread = threading.Thread(target=work, daemon=True)
        self.join_thread.start()

    def _join_line(self, line):
        """Surface joiner-side client lines as live save progress, not red noise."""
        stripped = line.strip()
        if "sync alarm unavailable" in line:
            # Expected outside the game (launcher context); keep it in the
            # activity log but never let it mask the save-transfer progress.
            self._note(stripped)
            return
        if "[MP][SAVE]" in line:
            match = re.search(r"SAVE_PUSH (\S+) (\d+)/(\d+)", line)
            if match:
                slot, seq, total = match.group(1), int(match.group(2)), int(match.group(3))
                pct = (seq * 100 // total) if total else 100
                self._set_status(self.join_card, "Receiving save... %d/%d chunks" % (seq, total),
                                 slot, color=ACCENT, progress=pct)
                self._note(stripped)
                return
            if "Saved" in line:
                self._set_status(self.join_card, "Saved - ready to start", stripped,
                                 color=GREEN, progress=100, done=True)
                self._note(stripped)
                return
            self._note(stripped)
            return
        if "[MP][ERROR]" in line:
            self._set_status(self.join_card, "Save failed", stripped, color=RED)
            self._note(stripped, kind="error")
            return
        self._note(stripped)

    def _on_join_done(self, slot, path, exc=None):
        self.btn_join.config(state="normal", text="Join lobby")
        if exc is not None:
            self._set_status(self.join_card, "Join failed", str(exc), color=RED)
            self._note("Could not receive the save: %s" % exc, kind="error")
            return
        self._set_status(self.join_card, "Save received - ready to start",
                         "Saved '%s' -> %s" % (slot, path), color=GREEN, progress=100, done=True)
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


def _load_app_modules():
    """Import the runtime modules (after the synced tree has been mounted).

    These were previously module-level imports; they are deferred so the
    updater-mounted runtime tree (not the frozen copies) wins the import.
    Idempotent - safe to call from both ``main()`` and ``LauncherApp.__init__``.
    """
    global SlotMeta, human_size, human_time  # noqa: PLW0603
    global ts4_user_folder, mods_folder, saves_folder, game_executable, steam_game_id  # noqa: PLW0603
    global lobby  # noqa: PLW0603
    global build_script_mod  # noqa: PLW0603
    for entry in (ROOT, os.path.join(ROOT, "client_mod")):
        if entry not in sys.path:
            sys.path.insert(0, entry)
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


def _run_selftest(dest):
    """Headless frozen-bundle self-test (SIM4_MP_SELFTEST=<dir>).

    Installs the mod into ``<dest>/Mods`` exactly like the "Install mod"
    button would, then writes ``<dest>/result.json``. Lets tests drive the
    one-file .exe without a display or clicks.
    """
    result = {"root": ROOT, "meipass": getattr(sys, "_MEIPASS", None)}
    try:
        os.makedirs(dest, exist_ok=True)
        if os.path.join(ROOT, "client_mod") not in sys.path:
            sys.path.insert(0, os.path.join(ROOT, "client_mod"))
        import build_script_mod
        result["mod_file"] = os.path.abspath(build_script_mod.__file__)
        result["project_root"] = str(build_script_mod.PROJECT_ROOT)
        mods = os.path.join(dest, "Mods")
        build_script_mod.cmd_dev(mods)
        scripts = os.path.join(mods, "Sims4Multiplayer", "Scripts")
        result["ok"] = os.path.isdir(scripts) and bool(os.listdir(scripts))
        result["scripts"] = scripts
    except Exception as exc:  # noqa: BLE001
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
    with open(os.path.join(dest, "result.json"), "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, default=str)


def main():
    # Mount the synced runtime tree (if any) BEFORE importing the runtime
    # modules, so the launcher runs the on-disk runtime - not the bundle.
    updater.mount_runtime(CODE_ROOT)
    _load_app_modules()
    selftest = os.environ.get("SIM4_MP_SELFTEST")
    if selftest:
        _run_selftest(selftest)
        return
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()