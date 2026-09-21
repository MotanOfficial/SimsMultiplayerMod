"""LauncherBridge mixin: diagnostics export + LAN hand-off to the host.

Keeps the bridge small (like SetupMixin/LobbyMixin): this mixin owns the
"Diagnostics" page behaviour - collecting the field logs, zipping them, the
host-side receiver that accepts a joiner's bundle, and the joiner-side send.
All heavy work runs off the GUI thread; results come back as log lines.
"""

import os
import threading

from PySide6.QtCore import QTimer, Slot

from launcher_common import CODE_ROOT, RUNTIME_DIR, updater

import importlib as _importlib

# Lazy import: 'tools.diagnostics' lives in the synced runtime tree, so it
# must be resolved at call time (after mount_runtime), not at module import.
_diagnostics = None


def _diag():
    global _diagnostics
    if _diagnostics is None:
        try:
            _diagnostics = _importlib.import_module("tools.diagnostics")
        except ImportError:  # pragma: no cover - dev fallback when run dir differs
            import diagnostics as _fallback  # type: ignore

            _diagnostics = _fallback
    return _diagnostics

LOG_HISTORY_LIMIT = 400

def _safe_platform():
    """platform.platform() with a fallback for trimmed frozen stdlibs."""
    try:
        import platform as _platform

        return _platform.platform()
    except Exception:  # noqa: BLE001 - 'platform' missing from the bundle
        import sys as _sys

        return "%s %s" % (_sys.platform, _sys.version.split()[0])



class DiagnosticsMixin(object):
    # ------------------------------------------------------------- lifecycle
    def _init_diagnostics(self):
        self._diag_history = []
        self._diag_receiver = None
        self._diag_status = ""
        self._diag_last_export = ""
        self._diag_dir = os.path.join(RUNTIME_DIR, _diag().EXPORT_DIRNAME)
        self._diag_received_dir = os.path.join(RUNTIME_DIR, _diag().RECEIVED_DIRNAME)
        try:
            self._diag_runtime_version = updater.installed_version(CODE_ROOT) or "(none)"
        except Exception:  # noqa: BLE001
            self._diag_runtime_version = "(unknown)"
        try:
            self.logAppended.connect(self._diag_remember)
        except Exception:  # noqa: BLE001
            pass
        QTimer.singleShot(800, self.refreshDiagStatus)

    def _diag_remember(self, line, kind):
        try:
            self._diag_history.append(line)
            if len(self._diag_history) > LOG_HISTORY_LIMIT:
                del self._diag_history[: LOG_HISTORY_LIMIT // 4]
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------ properties
    # NOTE: the Qt-facing @Property wrappers live on LauncherBridge (signals
    # must be declared on the QObject subclass); these are the plain getters.
    def _diag_runtime_version_text(self):
        return self._diag_runtime_version

    def _diag_status_text(self):
        return self._diag_status

    def _diag_target_text(self):
        """Where 'Send to host' would go, e.g. ``192.168.1.135:8766``."""
        host = (getattr(self, "_join_ip", "") or "").strip()
        if not host:
            return ""
        return "%s:%d" % (host, _diag().receiver_port(getattr(self, "_join_port", 8765)))

    @Slot()
    def refreshDiagStatus(self):
        try:
            diag = _diag()
            parts = ["runtime %s" % self._diag_runtime_version]
            try:
                present, missing = diag.default_paths()
            except AttributeError:
                # Older synced runtime: fall back to direct existence checks
                # against the same paths the exporter reads.
                present, missing = [], []
                try:
                    import os as _os

                    from launcher_common import RUNTIME_DIR as _rd

                    game_log = diag.game_client_log_path()
                    checks = [
                        ("server-log.txt", _os.path.join(_rd, "server.log")),
                        ("server-status.json", _os.path.join(_rd, "status.json")),
                        ("game-client.log", game_log),
                    ]
                    for name, path in checks:
                        try:
                            if _os.path.isfile(path):
                                present.append((name, path))
                            else:
                                missing.append((name, path))
                        except Exception:  # noqa: BLE001
                            missing.append((name, path))
                except Exception:  # noqa: BLE001
                    pass
            except Exception:  # noqa: BLE001
                present = []
            present_names = {name for name, _path in present}
            parts.append("server log %s" % ("yes" if "server-log.txt" in present_names else "no"))
            parts.append("game log %s" % ("yes" if "game-client.log" in present_names else "no"))
            if self._diag_receiver is not None and self._diag_receiver.thread_alive():
                parts.append("receiving on :%s" % self._diag_receiver.actual_port)
            if self._diag_last_export:
                parts.append("last export: %s" % os.path.basename(self._diag_last_export))
            self._diag_set_status(" | ".join(parts))
        except Exception as exc:  # noqa: BLE001 - status must never stay blank
            self._diag_set_status("status unavailable (%s)" % exc)

    def _diag_file_exists(self, name):
        try:
            diag = _diag()
            present, _missing = diag.default_paths()
            return any(entry == name for entry, _path in present)
        except Exception:  # noqa: BLE001
            return False

    def _diag_set_status(self, text):
        if text != self._diag_status:
            self._diag_status = text
            try:
                self.diagStatusChanged.emit(text)
            except Exception:  # noqa: BLE001
                pass

    def _diag_info(self):
        """Environment block for info.txt (versions, paths, ports, role)."""
        info = {
            "runtime version": self._diag_runtime_version,
            "lobby port": getattr(self, "_host_port", "?"),
            "join target": self._diag_target_text() or "(not joining)",
            "player name": (getattr(self, "_join_name", "") or getattr(self, "_host_name", "")),
            "game path": getattr(self, "_game", "") or "(not set)",
            "mods path": getattr(self, "_mods", "") or "(not set)",
            "saves path": getattr(self, "_saves", "") or "(not set)",
            "lobby running": bool(getattr(self, "server", None) is not None
                                  and self.server.thread_alive()),
            "frozen exe": bool(getattr(__import__("sys"), "_MEIPASS", None)),
            "python": __import__("sys").version.split()[0],
            "platform": _safe_platform(),
        }
        return info

    def _diag_export_bundle(self, directory):
        """Collect + write the zip (called on a worker thread)."""
        return _diag().export_bundle(
            directory,
            info=self._diag_info(),
            launcher_log=list(self._diag_history),
        )

    # ------------------------------------------------------------------ slots
    @Slot()
    def exportDiagnostics(self):
        """Zip every log into the Desktop so it can be shared by hand."""
        self._note("Collecting diagnostics...")

        def work():
            try:
                target = self._diag_export_bundle(_diag().desktop_directory())
                self._diag_last_export = target
                self._note("Diagnostics exported: %s" % target)
                self._note("Send that file to the other player (or use 'Send to host').")
            except Exception as exc:  # noqa: BLE001
                self._note("Diagnostics export failed: %s" % exc, kind="error")
            self.refreshDiagStatus()

        threading.Thread(target=work, daemon=True).start()

    @Slot()
    def sendDiagnosticsToHost(self):
        """POST this PC's bundle straight to the host's launcher."""
        target = self._diag_target_text()
        if not target:
            self._note("Enter the host's IP on the Join side first.", kind="error")
            return
        host = (self._join_ip or "").strip()
        port = _diag().receiver_port(self._join_port or 8765)
        self._note("Packaging diagnostics and sending to %s..." % target)

        def work():
            try:
                bundle = self._diag_export_bundle(self._diag_dir)
                self._diag_last_export = bundle
            except Exception as exc:  # noqa: BLE001
                self._note("Diagnostics export failed: %s" % exc, kind="error")
                self.refreshDiagStatus()
                return
            ok, detail = _diag().send_bundle(
                bundle,
                host,
                port,
                name=(self._join_name or "player"),
                role="join",
            )
            if ok:
                self._note("Host received the diagnostics (%s)." % detail)
            else:
                self._note(
                    "Send to host failed: %s. The host must have the lobby open "
                    "(its launcher listens on port %d). Exported a copy at %s"
                    % (detail, port, bundle),
                    kind="error",
                )
            self.refreshDiagStatus()

        threading.Thread(target=work, daemon=True).start()

    @Slot()
    def openDiagnosticsFolder(self):
        """Open the folder holding exported/received bundles."""
        try:
            os.makedirs(self._diag_dir, exist_ok=True)
        except OSError:
            pass
        if not _diag().open_in_explorer(self._diag_dir):
            self._note("Diagnostics folder: %s" % self._diag_dir)
        else:
            self._note("Opened %s" % self._diag_dir)

    # ---------------------------------------------------- host-side receiver
    def _start_diag_receiver(self, lobby_port):
        """Listen for joiners' bundles while the lobby is open (host side)."""
        self._stop_diag_receiver()
        port = _diag().receiver_port(lobby_port)
        receiver = _diag().DiagnosticsReceiver(
            port,
            self._diag_received_dir,
            on_received=self._on_diag_received,
            log=lambda line: self._note(line, kind="muted"),
        )
        if receiver.start():
            self._diag_receiver = receiver
            self._note("Players can send you their logs on port %d." % receiver.actual_port)
        self.refreshDiagStatus()

    def _stop_diag_receiver(self):
        receiver, self._diag_receiver = self._diag_receiver, None
        if receiver is not None:
            receiver.stop()
        try:
            self.refreshDiagStatus()
        except Exception:  # noqa: BLE001
            pass

    def _on_diag_received(self, path, meta):
        player = (meta or {}).get("name", "player")
        self._note("Received %s's diagnostics: %s" % (player, path))
        if _diag().open_in_explorer(os.path.dirname(path)):
            self._note("Opened the folder with the received bundle.")


