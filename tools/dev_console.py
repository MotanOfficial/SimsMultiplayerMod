"""Desktop dev console for Sims 4 Multiplayer (stdlib only, dark theme).

Left sidebar switches modes (Host / Players / Tests & Build / Log). The
Host page shows the save slots with their baked color thumbnail (JPEG read
off the `.save` head and converted to PNG via Windows GDI+, cached) plus
the server IP/port and the Host toggle. Server log and tool output tail
into the Log page. The real in-game slot name is unreachable without the
LZ4 DBPF decoder, so slots show editable labels persisted to JSON.

    python tools/dev_console.py
"""

import ctypes
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_MAIN = os.path.join(ROOT, "server", "main.py")
SAVE_SYNC = os.path.join(ROOT, "tools", "save_sync.py")
RUN_TESTS = os.path.join(ROOT, "tests", "run_tests.py")
SMOKE_CLIENT = os.path.join(ROOT, "tests", "smoke", "smoke_client.py")
BUILD_SCRIPT = os.path.join(ROOT, "client_mod", "build_script_mod.py")
RUNTIME_DIR = os.path.join(tempfile.gettempdir(), "simmp-dev")
GAME_CMD = "steam://rungameid/1222671"

try:
    TS4_FOLDER = os.path.join(os.path.expanduser("~"), "Documents", "Electronic Arts", "The Sims 4")
except Exception:
    TS4_FOLDER = ""
MODS_FOLDER = os.path.join(TS4_FOLDER, "Mods")
SAVES_FOLDER = os.path.join(TS4_FOLDER, "saves")
DIAG_FILE = os.path.join(MODS_FOLDER, "Sims4Multiplayer-diag.txt")

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from save_metadata import SlotMeta, human_size, human_time

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# ---------- palette ----------
BG = "#131418"
SIDEBAR_BG = "#1b1d23"
PANEL_BG = "#1e2129"
FIELD_BG = "#2a2d36"
TEXT = "#eceef3"
DIM = "#9aa0ac"
BORDER = "#333845"
ACCENT = "#5b8cff"
ACCENT_HOVER = "#729bff"
DANGER = "#e5484d"
DANGER_HOVER = "#f0555a"
OK = "#3fbf6f"
WARN = "#e5b94a"

FONT = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_BIG = ("Segoe UI", 12, "bold")
FONT_MONO = ("Consolas", 9)

# Windows UI: allow per-monitor DPI scaling so small fonts stay crisp.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


class DevConsole(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sims 4 Multiplayer - Dev Console")
        self.geometry("1080x720")
        self.minsize(880, 600)
        self.configure(bg=BG)
        self._configure_styles()
        os.makedirs(RUNTIME_DIR, exist_ok=True)
        self.server_proc = None
        self.queue = queue.Queue()
        self._log_pos = 0  # byte offset into server.log already shown
        self._auto_diag_until = 0.0
        self._diag_mtime = 0.0
        self._slot_photos = {}
        self._log_source = "server"
        self.slot_meta = SlotMeta(SAVES_FOLDER, RUNTIME_DIR)
        self._build_layout()
        self._show_page("host")
        self._refresh_slots()
        self._append("console ready\n")
        self.after(200, self._drain_queue)
        self.after(1000, self._poll)

    # ================= appearance =================
    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("BG.TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL_BG)
        style.configure("Slide.TLabel", background=SIDEBAR_BG, foreground=DIM, font=FONT)
        style.configure("Title.TLabel", background=SIDEBAR_BG, foreground=TEXT, font=FONT_TITLE)
        style.configure("Sub.TLabel", background=SIDEBAR_BG, foreground=DIM, font=("Segoe UI", 8))
        style.configure("Head.TLabel", background=BG, foreground=TEXT, font=FONT_BIG)
        style.configure("HeadDim.TLabel", background=BG, foreground=DIM, font=("Segoe UI", 9, "bold"))
        style.configure("Dim.TLabel", background=BG, foreground=DIM, font=FONT)
        style.configure("CardDim.TLabel", background=PANEL_BG, foreground=DIM, font=("Segoe UI", 8))
        style.configure("Plain.TLabel", background=BG, foreground=TEXT, font=FONT)

        style.configure("Nav.TButton", background=SIDEBAR_BG, foreground=DIM,
                        borderwidth=0, focuscolor=SIDEBAR_BG, padding=(12, 9), font=("Segoe UI", 10))
        style.map("Nav.TButton",
                  background=[("active", PANEL_BG), ("pressed", PANEL_BG)],
                  foreground=[("active", TEXT), ("pressed", TEXT)])
        style.configure("NavOn.TButton", background=ACCENT, foreground="#0c0f16",
                        borderwidth=0, focuscolor=SIDEBAR_BG, padding=(12, 9), font=("Segoe UI", 10, "bold"))
        style.map("NavOn.TButton",
                  background=[("active", ACCENT_HOVER), ("pressed", ACCENT_HOVER)],
                  foreground=[("active", "#0c0f16")])

        style.configure("Tool.TButton", background=PANEL_BG, foreground=TEXT,
                        borderwidth=1, relief="flat", focuscolor=PANEL_BG, padding=(8, 5), font=FONT)
        style.map("Tool.TButton",
                  background=[("active", "#262a34"), ("pressed", "#2f3441")],
                  foreground=[("disabled", DIM)])
        style.configure("ToolDim.TButton", background=BG, foreground=DIM,
                        borderwidth=1, relief="flat", focuscolor=BG, padding=(8, 5), font=FONT)
        style.map("ToolDim.TButton",
                  background=[("active", PANEL_BG), ("pressed", PANEL_BG)],
                  foreground=[("active", TEXT), ("disabled", "#555a66")])

        style.configure("Accent.TButton", background=ACCENT, foreground="#0c0f16",
                        borderwidth=0, relief="flat", focuscolor=BG, padding=(18, 10), font=FONT_BIG)
        style.map("Accent.TButton",
                  background=[("active", ACCENT_HOVER), ("pressed", ACCENT_HOVER)],
                  foreground=[("disabled", "#6a7080")])
        style.configure("Stop.TButton", background=DANGER, foreground="#16090a",
                        borderwidth=0, relief="flat", focuscolor=BG, padding=(18, 10), font=FONT_BIG)
        style.map("Stop.TButton",
                  background=[("active", DANGER_HOVER), ("pressed", DANGER_HOVER)])

        style.configure("Dark.TEntry", fieldbackground=FIELD_BG, foreground=TEXT,
                        insertcolor=TEXT, bordercolor=FIELD_BG, lightcolor=FIELD_BG,
                        darkcolor=FIELD_BG, padding=5, font=FONT)

    @staticmethod
    def _rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return canvas.create_polygon(pts, smooth=True, **kw)

    def _set_badge(self, text, color):
        canvas = self.badge
        canvas.delete("all")
        w, h = 174, 26
        self._rounded_rect(canvas, 2, 2, w - 2, h - 2, 13, fill=color, outline="")
        canvas.create_text(w / 2, h / 2, text=text, fill="#0c0f16", font=FONT_BOLD)

    # ================= layout =================
    def _build_layout(self):
        root = tk.Frame(self, bg=BG)
        root.pack(fill=tk.BOTH, expand=True)

        # --- top bar ---
        bar = tk.Frame(root, bg=SIDEBAR_BG, height=46)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="Sims 4  ·  Multiplayer", bg=SIDEBAR_BG, fg=TEXT,
                 font=FONT_TITLE).pack(side=tk.LEFT, padx=(16, 4), pady=4)
        tk.Label(bar, text="dev console", bg=SIDEBAR_BG, fg=DIM,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, pady=4)
        self.badge = tk.Canvas(bar, width=180, height=30, bg=SIDEBAR_BG, highlightthickness=0)
        self.badge.pack(side=tk.RIGHT, padx=12, pady=8)
        self._set_badge("server stopped", "#3a3e4a")

        # --- sidebar ---
        side = tk.Frame(root, bg=SIDEBAR_BG, width=178)
        side.pack(side=tk.LEFT, fill=tk.Y)
        side.pack_propagate(False)
        self._nav = {}
        for page, label in (("host", "Host"), ("players", "Players"),
                            ("tests", "Tests & Build"), ("log", "Log")):
            btn = ttk.Button(side, text=label, style="Nav.TButton",
                             command=lambda p=page: self._show_page(p))
            btn.pack(fill=tk.X, padx=10, pady=3, ipady=1)
            self._nav[page] = btn
        tk.Label(side, text="\nS4MP dev tool", bg=SIDEBAR_BG, fg="#5a5f6c",
                 font=("Segoe UI", 8)).pack(side=tk.BOTTOM, pady=(0, 8))

        # --- pages ---
        self.content = tk.Frame(root, bg=BG)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.pages = {}
        self.pages["host"] = self._build_host_page()
        self.pages["players"] = self._build_players_page()
        self.pages["tests"] = self._build_tests_page()
        self.pages["log"] = self._build_log_page()

    def _show_page(self, name):
        for key, frame in self.pages.items():
            frame.pack_forget()
        self.pages[name].pack(fill=tk.BOTH, expand=True)
        for key, btn in self._nav.items():
            btn.configure(style="NavOn.TButton" if key == name else "Nav.TButton")

    def _build_host_page(self):
        page = ttk.Frame(self.content, style="BG.TFrame", padding=14)
        ttk.Label(page, text="Host a game", style="Head.TLabel").pack(anchor="w")

        # save slots
        ttk.Label(page, text="PICK THE SAVE TO SHARE", style="HeadDim.TLabel").pack(anchor="w", pady=(14, 4))
        toolbar = ttk.Frame(page, style="BG.TFrame")
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="Refresh slots", style="Tool.TButton",
                   command=self._refresh_slots).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Open saves folder", style="Tool.TButton",
                   command=self._open_saves).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Sync a file...", style="Tool.TButton",
                   command=self._browse_save).pack(side=tk.LEFT)
        wrap = ttk.Frame(page, style="BG.TFrame")
        wrap.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.slots_canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0, width=700)
        self.slots_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.slots_canvas.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.slots_canvas.configure(yscrollcommand=sb.set)
        self.slots_inner = tk.Frame(self.slots_canvas, bg=BG)
        win = self.slots_canvas.create_window((0, 0), window=self.slots_inner, anchor="nw")
        self.slots_inner.bind("<Configure>",
                              lambda e: self.slots_canvas.configure(
                                  scrollregion=self.slots_canvas.bbox("all")))
        self.slots_canvas.bind("<Configure>",
                               lambda e: self.slots_canvas.itemconfig(win, width=e.width))

        def _wheel(event):
            self.slots_canvas.yview_scroll(int(-event.delta / 120), "units")

        self.slots_canvas.bind("<MouseWheel>", _wheel)
        self.slots_inner.bind("<MouseWheel>", _wheel)

        # server + host
        ttk.Label(page, text="SERVER", style="HeadDim.TLabel").pack(anchor="w", pady=(6, 4))
        conn = ttk.Frame(page, style="Panel.TFrame", padding=10)
        conn.pack(fill=tk.X)
        ttk.Label(conn, text="IP", background=PANEL_BG, foreground=DIM,
                  font=FONT_BOLD).pack(side=tk.LEFT)
        self.host = ttk.Entry(conn, width=16, style="Dark.TEntry")
        self.host.insert(0, "127.0.0.1")
        self.host.pack(side=tk.LEFT, padx=(6, 14))
        ttk.Label(conn, text="Port", background=PANEL_BG, foreground=DIM,
                  font=FONT_BOLD).pack(side=tk.LEFT)
        self.port = ttk.Entry(conn, width=7, style="Dark.TEntry")
        self.port.insert(0, "8765")
        self.port.pack(side=tk.LEFT, padx=(6, 16))
        self.host_btn = ttk.Button(conn, text="Host", style="Accent.TButton",
                                   command=self._toggle_server)
        self.host_btn.pack(side=tk.LEFT)
        hint = ttk.Label(conn, text="other players join this IP while the host keeps the save synced",
                         style="Dim.TLabel", background=PANEL_BG)
        hint.pack(side=tk.LEFT, padx=14)
        return page

    def _build_players_page(self):
        page = ttk.Frame(self.content, style="BG.TFrame", padding=14)
        ttk.Label(page, text="Players & rooms", style="Head.TLabel").pack(anchor="w")
        self.players_lbl = tk.Label(page, text="players: none", bg=BG, fg=TEXT,
                                    font=FONT_BOLD, wraplength=760, justify="left",
                                    anchor="w")
        self.players_lbl.pack(fill=tk.X, pady=(14, 4))
        ttk.Label(page, text="Server state and per-room clock gate refresh once a second;",
                  style="Dim.TLabel").pack(anchor="w")
        bar = ttk.Frame(page, style="BG.TFrame")
        bar.pack(fill=tk.X, pady=(18, 0))
        ttk.Button(bar, text="Launch game", style="Accent.TButton",
                   command=self._launch_game).pack(side=tk.LEFT)
        ttk.Button(bar, text="Launch smoke player", style="Tool.TButton",
                   command=self._launch_smoke).pack(side=tk.LEFT, padx=8)
        ttk.Button(bar, text="Show diag file", style="ToolDim.TButton",
                   command=self._show_diag).pack(side=tk.LEFT)
        return page

    def _build_tests_page(self):
        page = ttk.Frame(self.content, style="BG.TFrame", padding=14)
        ttk.Label(page, text="Tests & build", style="Head.TLabel").pack(anchor="w")
        ttk.Label(page, text="Everything runs offline; progress lands in the Log page.",
                  style="Dim.TLabel").pack(anchor="w", pady=(4, 14))
        bar = ttk.Frame(page, style="BG.TFrame")
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="Run offline tests", style="Tool.TButton",
                   command=self._run_tests).pack(side=tk.LEFT)
        ttk.Button(bar, text="Build + deploy", style="Tool.TButton",
                   command=self._build_deploy).pack(side=tk.LEFT, padx=8)
        ttk.Label(page, text="Tests: runs the full suite (268 tests) with the real protocol code.\n"
                             "Build + deploy: packages the mod to Sims4Multiplayer.ts4script and\n"
                             "drops the dev build into the Mods folder.", style="Dim.TLabel",
                  justify="left").pack(anchor="w", pady=(16, 0))
        return page

    def _build_log_page(self):
        page = ttk.Frame(self.content, style="BG.TFrame", padding=14)
        ttk.Label(page, text="Log", style="Head.TLabel").pack(anchor="w")
        bar = ttk.Frame(page, style="BG.TFrame")
        bar.pack(fill=tk.X, pady=(2, 6))
        self.log_src_server = ttk.Button(bar, text="Server log", style="NavOn.TButton",
                                         command=lambda: self._set_log_source("server"))
        self.log_src_server.pack(side=tk.LEFT)
        self.log_src_diag = ttk.Button(bar, text="Diag file", style="Nav.TButton",
                                       command=lambda: self._set_log_source("diag"))
        self.log_src_diag.pack(side=tk.LEFT, padx=6)
        ttk.Button(bar, text="Clear", style="ToolDim.TButton",
                   command=lambda: self.log.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=6)
        self.log = scrolledtext.ScrolledText(page, height=24, font=FONT_MONO,
                                             bg="#101116", fg="#d7dae0",
                                             insertbackground=TEXT, relief="flat",
                                             highlightthickness=1, highlightbackground=BORDER,
                                             wrap="char", padx=6, pady=6)
        self.log.pack(fill=tk.BOTH, expand=True)
        return page

    # ================= log / io helpers =================
    def _append(self, text):
        self.log.insert(tk.END, text)
        self.log.see(tk.END)

    def _run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def _spawn(self, argv):
        return subprocess.Popen(
            argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, creationflags=CREATE_NO_WINDOW, cwd=ROOT)

    def _stream_proc(self, proc, label):
        for line in proc.stdout:
            self.queue.put(("[%s] " % label) + line)
        proc.wait()
        self.queue.put(("[%s] exited with code %s\n" % (label, proc.returncode)))

    # ================= server control =================
    def _toggle_server(self):
        if self.server_proc is not None and self.server_proc.poll() is None:
            self._stop_server()
        else:
            self._start_server()

    def _start_server(self):
        if self.server_proc is not None and self.server_proc.poll() is None:
            return
        log_path = os.path.join(RUNTIME_DIR, "server.log")
        status_path = os.path.join(RUNTIME_DIR, "status.json")
        argv = [
            sys.executable, SERVER_MAIN,
            "--host", self.host.get(),
            "--port", self.port.get(),
            "--log-file", log_path,
            "--status-file", status_path,
        ]
        self._append("server: starting %s\n" % (" ".join(argv)))
        try:
            self.server_proc = subprocess.Popen(argv, creationflags=CREATE_NO_WINDOW, cwd=ROOT)
        except Exception as exc:
            self._append("server: failed to start: %s\n" % exc)
            return
        self.host_btn.configure(text="Stop", style="Stop.TButton")
        self._set_badge("server starting", WARN)

    def _stop_server(self):
        proc = self.server_proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        self.server_proc = None
        self.host_btn.configure(text="Host", style="Accent.TButton")
        self._set_badge("server stopped", "#3a3e4a")
        self._append("server: stop requested\n")

    # ================= polling =================
    def _poll(self):
        self._refresh_status()
        self._refresh_log_tail()
        self._auto_read_diag()
        self.after(1000, self._poll)

    def _auto_read_diag(self):
        if time.time() > self._auto_diag_until:
            return
        try:
            mtime = os.path.getmtime(DIAG_FILE)
        except Exception:
            return
        if mtime == self._diag_mtime:
            return
        self._diag_mtime = mtime
        try:
            with open(DIAG_FILE, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except Exception:
            return
        self._append("\n--- diag auto-read %s ---\n%s" % (time.strftime("%H:%M:%S"), content))

    def _refresh_status(self):
        status_path = os.path.join(RUNTIME_DIR, "status.json")
        try:
            with open(status_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            if self.server_proc is not None and self.server_proc.poll() is None:
                self.players_lbl.config(text="server running ... waiting for status")
            return
        players = data.get("players") or []
        rooms = data.get("rooms") or []
        lines = ["connected players: %d" % len(players)]
        for room in rooms:
            label = room.get("room_id") or "?"
            n = len(room.get("players", []) or [])
            clock = room.get("clock")
            bit = "  room %s: %d player(s)" % (label, n)
            if clock and clock.get("gate"):
                ready = len(clock.get("ready", []) or [])
                total = len(clock.get("participants", []) or [])
                bit += "  |  time paused, waiting for ready %d/%d" % (ready, total)
            elif clock:
                bit += "  |  time running @ speed %s (by %s)" % (clock.get("speed"), clock.get("by_player"))
            lines.append(bit)
        self.players_lbl.config(text="\n".join(lines))
        running = self.server_proc is not None
        if running and self.server_proc.poll() is None:
            self._set_badge("server running", OK)
        elif running and self.server_proc.poll() is not None:
            self._set_badge("server exited", DANGER)
        else:
            self._set_badge("server stopped", "#3a3e4a")

    def _set_log_source(self, source):
        """Log page view switch: 'server' tails server.log, 'diag' shows the
        game's diagnostics file. Only the active source auto-tails."""
        self._log_source = source
        self.log_src_server.configure(style="NavOn.TButton" if source == "server" else "Nav.TButton")
        self.log_src_diag.configure(style="NavOn.TButton" if source == "diag" else "Nav.TButton")
        self.log.delete("1.0", tk.END)
        if source == "server":
            self._log_pos = 0
            self._refresh_log_tail()
        else:
            self._show_diag()

    def _refresh_log_tail(self):
        if self._log_source != "server":
            return
        log_path = os.path.join(RUNTIME_DIR, "server.log")
        try:
            size = os.path.getsize(log_path)
        except Exception:
            return
        if size < self._log_pos:
            self._log_pos = 0  # log was replaced (server restarted)
        if size == self._log_pos:
            return
        try:
            with open(log_path, "rb") as handle:
                handle.seek(self._log_pos)
                blob = handle.read()
        except Exception:
            return
        if not blob:
            return
        self._log_pos = size
        try:
            text = blob.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        self._append(text)

    # ================= save slots =================
    def _open_saves(self):
        try:
            os.startfile(SAVES_FOLDER)  # noqa: 601  (windows only)
        except Exception as exc:
            self._append("saves: %s\n" % exc)

    def _refresh_slots(self):
        for child in self.slots_inner.winfo_children():
            child.destroy()
        try:
            slots = self.slot_meta.slots()
        except Exception as exc:
            self._append("saves: %s\n" % exc)
            return
        self._slot_photos = {}
        if not slots:
            tk.Label(self.slots_inner, text="No Slot_*.save in %s" % SAVES_FOLDER,
                     bg=BG, fg=DIM, font=FONT).pack(anchor="w", padx=6, pady=10)
            return
        for it in slots:
            card = tk.Frame(self.slots_inner, bg=PANEL_BG,
                            highlightthickness=1, highlightbackground=BORDER)
            card.pack(fill=tk.X, pady=5)
            thumb = it.get("thumb")
            img = None
            if thumb:
                try:
                    photo = tk.PhotoImage(file=thumb)  # 180x120, full size
                    self._slot_photos[it["id"]] = photo
                    img = photo
                except Exception:
                    img = None
            if img is not None:
                tk.Label(card, image=img, bg=PANEL_BG,
                         highlightthickness=1, highlightbackground="#2c3140",
                         width=180, height=120).pack(side=tk.LEFT, padx=10, pady=8)
            else:
                tk.Label(card, text="no\npreview", bg="#2a2d36", fg=DIM,
                         width=180, height=9).pack(side=tk.LEFT, padx=10, pady=8)

            info = tk.Frame(card, bg=PANEL_BG)
            info.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 10), pady=8)
            title = it["label"] or it["id"]
            tk.Label(info, text=title, bg=PANEL_BG, fg=TEXT,
                     font=FONT_BIG, anchor="w").pack(fill=tk.X)
            tk.Label(info, text="%s  |  %s  |  %s"
                     % (it["file"], human_size(it["size"]), human_time(it["mtime"])),
                     bg=PANEL_BG, fg=DIM, font=("Segoe UI", 8), anchor="w").pack(fill=tk.X, pady=(2, 6))
            row = tk.Frame(info, bg=PANEL_BG)
            row.pack(fill=tk.X)
            entry = tk.Entry(row, bg="#2d3039", fg=TEXT, insertbackground=TEXT,
                             relief="flat", font=FONT, width=26)
            entry.insert(0, it["label"] or it["id"])
            entry.pack(side=tk.LEFT, ipady=3)
            ttk.Button(row, text="Save name", style="ToolDim.TButton",
                       command=lambda s=it["id"], e=entry: self._save_slot_label(s, e)).pack(side=tk.LEFT, padx=4)

            ttk.Button(card, text="Sync", style="Accent.TButton",
                       command=lambda p=it["path"]: self._sync_save(p)).pack(side=tk.RIGHT, padx=12, pady=8)
            ttk.Button(card, text="Open folder", style="ToolDim.TButton",
                       command=lambda p=it["path"]: os.startfile(os.path.dirname(p))).pack(side=tk.RIGHT, pady=8)

    def _save_slot_label(self, slot_id, entry):
        self.slot_meta.set_label(slot_id, entry.get())
        self._append("saves: label for %s -> %s\n" % (slot_id, entry.get().strip() or "(cleared)"))
        self._refresh_slots()

    # ================= actions =================
    def _browse_save(self):
        path = filedialog.askopenfilename(
            title="Pick the save to distribute",
            initialdir=SAVES_FOLDER or None,
            filetypes=[("Sims 4 save", "*.save"), ("All files", "*.*")])
        if path:
            self._sync_save(path)

    def _sync_save(self, path):
        if not path:
            return
        argv = [sys.executable, SAVE_SYNC, path,
                "--host", self.host.get(), "--port", self.port.get(),
                "--ack-timeout", "15"]
        self._append("sync: pushing %s\n" % os.path.basename(path))
        self._run_in_thread(self._stream_proc, self._spawn(argv), "sync")

    def _run_tests(self):
        self._show_page("log")
        self._append("tests: running suite...\n")
        self._run_in_thread(self._stream_proc, self._spawn([sys.executable, RUN_TESTS]), "tests")

    def _build_deploy(self):
        self._show_page("log")
        self._append("build: packaging + deploying to Mods folder...\n")
        self._run_in_thread(
            self._stream_proc, self._spawn([sys.executable, BUILD_SCRIPT, "package"]), "build")

        def deploy_after_package():
            time.sleep(0.5)
            self._stream_proc(self._spawn([sys.executable, BUILD_SCRIPT, "dev", MODS_FOLDER]), "build")

        self._run_in_thread(deploy_after_package)

    def _launch_smoke(self):
        argv = [sys.executable, SMOKE_CLIENT,
                "--host", self.host.get(), "--port", self.port.get(),
                "--name", "Smoke", "--timeout", "30"]
        self._append("smoke: launching %s\n" % (" ".join(argv)))
        try:
            subprocess.Popen(argv, creationflags=CREATE_NO_WINDOW, cwd=ROOT)
        except Exception as exc:
            self._append("smoke: failed: %s\n" % exc)

    def _launch_game(self):
        self._append("game: launching %s\n" % GAME_CMD)
        try:
            subprocess.Popen(GAME_CMD, shell=True)
        except Exception as exc:
            self._append("game: failed: %s\n" % exc)
            return
        self._auto_diag_until = time.time() + 180
        self._diag_mtime = 0.0
        self._append("game: watching %s for diag output\n" % DIAG_FILE)

    def _show_diag(self):
        self._show_page("log")
        if self._log_source != "diag":
            self._set_log_source("diag")
            return
        try:
            with open(DIAG_FILE, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except Exception as exc:
            self._append("diag: %s\n" % exc)
            return
        self.log.delete("1.0", tk.END)
        self._append(content + "\n")

    # ================= thread->UI queue =================
    def _drain_queue(self):
        try:
            while True:
                self._append(self.queue.get_nowait())
        except queue.Empty:
            pass
        self.after(200, self._drain_queue)

    def destroy(self):
        self._stop_server()
        super().destroy()


def main():
    DevConsole().mainloop()


if __name__ == "__main__":
    main()