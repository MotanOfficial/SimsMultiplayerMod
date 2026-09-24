"""LauncherBridge QObject: the Qt-facing controller for the QML launcher.

Owns all signals/properties QML binds against; the meat of the actions lives
in the SetupMixin (paths/mod/updates/saves) and LobbyMixin (lobby/share/join)
sisters so the file stays small. Cross-thread updates (lobby server thread,
save-push worker, updater) are safe because Qt signals auto-queue.
"""

import os

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from launcher_common import MUTED, RUNTIME, _load_app_modules, _load_settings, _save_settings
from launcher_diag import DiagnosticsMixin
from launcher_lobby import LobbyMixin
from launcher_setup import SetupMixin


class LauncherBridge(SetupMixin, LobbyMixin, DiagnosticsMixin, QObject):
    cardStatus = Signal(str, str, str, str, int, bool, bool)
    logAppended = Signal(str, str)
    setupStatusChanged = Signal(str, str)
    updateStatusChanged = Signal(str, str)
    diagStatusChanged = Signal(str)

    gamePathChanged = Signal(str)
    modsPathChanged = Signal(str)
    savesPathChanged = Signal(str)
    hostPortChanged = Signal(str)
    hostNameChanged = Signal(str)
    joinIpChanged = Signal(str)
    joinPortChanged = Signal(str)
    joinNameChanged = Signal(str)
    lanIpsChanged = Signal()
    lanIpIndexChanged = Signal(int)
    savesChanged = Signal()
    autoUpdateChanged = Signal(bool)
    playerCountChanged = Signal(int)
    lobbyRunningChanged = Signal(bool)
    canShareChanged = Signal(bool)
    canHostStartChanged = Signal(bool)
    canJoinStartChanged = Signal(bool)
    joiningChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = _load_settings()
        self._game = self.settings.get("game", "")
        self._mods = self.settings.get("mods", "")
        self._saves = self.settings.get("saves", "")
        self._auto_update = bool(self.settings.get("auto_update", True))
        self._host_port = str(self.settings.get("host_port", "8765"))
        self._host_name = self.settings.get("host_name", "Host")
        self._join_ip = self.settings.get("join_ip", "")
        self._join_port = str(self.settings.get("join_port", "8765"))
        self._join_name = self.settings.get("join_name", "Player")

        self.server = None
        self.push_thread = None
        self.join_thread = None
        self._share_client = None
        self._join_client = None
        self._selected_save = None
        self._save_items = []
        self._save_labels = []
        self._synced = False
        self._connected_players = 0
        self._update_busy = False
        self._joining = False
        self._can_share = False
        self._can_host_start = False
        self._can_join_start = False
        self._shutdown_done = False

        _load_app_modules()
        ips = list(RUNTIME.lobby.all_lan_ips() or [])
        self._lan_ips = ips or ["?"]
        primary = RUNTIME.lobby.find_lan_ip() or ""
        self._lan_ip_index = self._lan_ips.index(primary) if primary in self._lan_ips else 0
        self._auto_detect()
        self._init_diagnostics()
        QTimer.singleShot(400, self._maybe_check_updates)

    # -------------------------------------------------------------- properties
    def _prop_str(self, name, value, notifier):
        cur = getattr(self, "_%s" % name)
        if cur != value:
            setattr(self, "_%s" % name, value)
            notifier.emit(value)

    @Property(str, notify=gamePathChanged)
    def gamePath(self):
        return self._game

    @gamePath.setter
    def gamePath(self, value):
        self._prop_str("game", value, self.gamePathChanged)

    @Property(str, notify=modsPathChanged)
    def modsPath(self):
        return self._mods

    @modsPath.setter
    def modsPath(self, value):
        self._prop_str("mods", value, self.modsPathChanged)

    @Property(str, notify=savesPathChanged)
    def savesPath(self):
        return self._saves

    @savesPath.setter
    def savesPath(self, value):
        self._prop_str("saves", value, self.savesPathChanged)

    @Property(str, notify=hostPortChanged)
    def hostPort(self):
        return self._host_port

    @hostPort.setter
    def hostPort(self, value):
        self._prop_str("host_port", value, self.hostPortChanged)

    @Property(str, notify=hostNameChanged)
    def hostName(self):
        return self._host_name

    @hostName.setter
    def hostName(self, value):
        self._prop_str("host_name", value, self.hostNameChanged)

    @Property(str, notify=joinIpChanged)
    def joinIp(self):
        return self._join_ip

    @joinIp.setter
    def joinIp(self, value):
        self._prop_str("join_ip", value, self.joinIpChanged)

    @Property(str, notify=joinPortChanged)
    def joinPort(self):
        return self._join_port

    @joinPort.setter
    def joinPort(self, value):
        self._prop_str("join_port", value, self.joinPortChanged)

    @Property(str, notify=joinNameChanged)
    def joinName(self):
        return self._join_name

    @joinName.setter
    def joinName(self, value):
        self._prop_str("join_name", value, self.joinNameChanged)

    @Property(bool, notify=autoUpdateChanged)
    def autoUpdate(self):
        return self._auto_update

    @autoUpdate.setter
    def autoUpdate(self, value):
        value = bool(value)
        if value != self._auto_update:
            self._auto_update = value
            self.settings["auto_update"] = value
            _save_settings(self.settings)
            self.autoUpdateChanged.emit(value)

    @Property(list, notify=lanIpsChanged)
    def lanIps(self):
        return self._lan_ips

    @Property(int, notify=lanIpIndexChanged)
    def lanIpIndex(self):
        return self._lan_ip_index

    @Property(list, notify=savesChanged)
    def saves(self):
        return self._save_labels

    @Property(int, notify=playerCountChanged)
    def playerCount(self):
        return self._connected_players

    @Property(bool, notify=lobbyRunningChanged)
    def lobbyRunning(self):
        return self.server is not None and self.server.thread_alive()

    @Property(bool, notify=canShareChanged)
    def canShare(self):
        return self._can_share

    @Property(bool, notify=canHostStartChanged)
    def canHostStart(self):
        return self._can_host_start

    @Property(bool, notify=canJoinStartChanged)
    def canJoinStart(self):
        return self._can_join_start

    @Property(bool, notify=joiningChanged)
    def joining(self):
        return self._joining

    # ------------------------------------------------------- diagnostics page
    @Property(str, notify=diagStatusChanged)
    def runtimeVersion(self):
        return self._diag_runtime_version_text()

    @Property(str, notify=diagStatusChanged)
    def diagStatus(self):
        return self._diag_status_text()

    @Property(str, notify=diagStatusChanged)
    def diagTarget(self):
        return self._diag_target_text()

    # ---------------------------------------------------------------- slots
    @Slot(int)
    def lanIpSelected(self, index):
        if 0 <= index < len(self._lan_ips):
            self._lan_ip_index = index
            self.lanIpIndexChanged.emit(index)

    @Slot()
    def copyIp(self):
        ip = self._current_ip()
        if ip and ip != "?":
            from PySide6.QtGui import QGuiApplication
            QGuiApplication.clipboard().setText(ip)
            self._note("Copied %s to clipboard." % ip)

    @Slot()
    def shutdown(self):
        if self._shutdown_done:
            return
        self._shutdown_done = True
        self.settings.update({
            "game": self._game,
            "mods": self._mods,
            "saves": self._saves,
            "host_port": self._host_port,
            "host_name": self._host_name,
            "join_ip": self._join_ip,
            "join_port": self._join_port,
            "join_name": self._join_name,
        })
        _save_settings(self.settings)
        self._disconnect_held()
        self._stop_diag_receiver()
        if self.server is not None:
            self.server.stop()
            self.server = None

    # ------------------------------------------------------------- utilities
    def _auto_detect(self):
        import tempfile

        temp_root = os.path.normcase(os.path.abspath(tempfile.gettempdir()))
        repo_tests = os.path.normcase(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests"))
        )

        def _is_unusable_mods(path):
            if not path:
                return False
            abs_path = os.path.normcase(os.path.abspath(path))
            if abs_path == temp_root or abs_path.startswith(temp_root + os.sep):
                return True
            if abs_path == repo_tests or abs_path.startswith(repo_tests + os.sep):
                return True
            leaf = os.path.basename(abs_path.rstrip("\\/"))
            return leaf.lower() != "mods"

        for key in ("game", "mods", "saves"):
            current = getattr(self, "_%s" % key)
            if not current or (key == "mods" and _is_unusable_mods(current)):
                guessed = self._guess(key) or ""
                if guessed:
                    setattr(self, "_%s" % key, guessed)
        self.refreshSaves()

    def _note(self, text, kind="info"):
        self.logAppended.emit("%s %s" % (self._now(), text), kind)

    @Slot(str)
    def qmlWarning(self, text):
        self.logAppended.emit("%s [QML] %s" % (self._now(), text.strip()), "qml")

    @staticmethod
    def _now():
        import time
        return time.strftime("%H:%M:%S")