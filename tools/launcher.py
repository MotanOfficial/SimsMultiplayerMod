"""Sims 4 Multiplayer launcher - PySide6/QML host/join lobby with auto-setup.

Runs completely offline-safe: game-path detection, mod auto-install, an
embedded lobby server, one-click save sharing, and game launch. Designed to be
bundled into a single .exe via ``tools/build_app.py`` (PyInstaller + PySide6).

The .exe is a thin bootstrap. The actual runtime code (server, protocol, mod
source, tools) is synced incrementally from the public GitHub repo into
``%LOCALAPPDATA%\\Sims4Multiplayer\\runtime`` by ``tools/updater.py`` and is
mounted over the frozen copies at startup, so an update to the app + mod is a
handful of small downloaded files - never a fresh .exe.

The UI lives in ``tools/launcher_ui/*.qml`` (Qt Quick, dark theme). A
``LauncherBridge`` QObject exposes the backend to QML via properties/slots and
emits Qt signals that QML renders as status cards, progress bars, and the
activity log.

Flow:
   Host:   Start lobby -> friends join via the shown LAN IP -> pick a save ->
           Share save -> save pops on every joiner -> Start Game.
   Join:   enter host IP -> Join -> save lands in your saves folder ->
           Start Game.
"""

import ctypes
import json
import os
import sys

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


def _run_selftest(dest):
    """Headless frozen-bundle self-test (SIM4_MP_SELFTEST=<dir>).

    Installs the mod into ``<dest>/Mods`` exactly like the "Install mod"
    button would, then writes ``<dest>/result.json``. Lets tests drive the
    one-file .exe without a display or clicks.
    """
    from launcher_common import ROOT
    from launcher_common import RUNTIME, _load_app_modules

    result = {"root": ROOT, "meipass": getattr(sys, "_MEIPASS", None)}
    try:
        os.makedirs(dest, exist_ok=True)
        _load_app_modules()
        result["mod_file"] = os.path.abspath(RUNTIME.build_script_mod.__file__)
        result["project_root"] = str(RUNTIME.build_script_mod.PROJECT_ROOT)
        mods = os.path.join(dest, "Mods")
        RUNTIME.build_script_mod.cmd_dev(mods)
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
    from launcher_common import CODE_ROOT, ROOT
    from launcher_common import updater

    updater.mount_runtime(CODE_ROOT)

    selftest = os.environ.get("SIM4_MP_SELFTEST")
    if selftest:
        _run_selftest(selftest)
        return

    from PySide6.QtGui import QGuiApplication
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtWidgets import QApplication
    from launcher_bridge import LauncherBridge

    if not os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        # Fusion fully supports control customization; the default Windows-native
        # style rejects custom background/contentItem delegates.
        os.environ["QT_QUICK_CONTROLS_STYLE"] = "Fusion"

    app = QApplication(sys.argv)
    app.setApplicationName("Sims4MultiplayerLauncher")
    app.setOrganizationName("Sims4Multiplayer")

    engine = QQmlApplicationEngine()
    bridge = LauncherBridge()
    engine.rootContext().setContextProperty("bridge", bridge)

    qml_warning_buffer = []

    def _on_qml_warnings(messages):
        for m in messages:
            try:
                text = m.toString()
            except Exception:
                text = str(m)
            if text:
                qml_warning_buffer.append(text.split("\n")[0])

    def _flush_qml_warnings():
        for line in qml_warning_buffer:
            bridge.qmlWarning(line)
        qml_warning_buffer.clear()

    engine.warnings.connect(_on_qml_warnings)

    qml_path = os.path.join(ROOT, "tools", "launcher_ui", "Main.qml")
    engine.load(QUrl.fromLocalFile(qml_path))
    if not engine.rootObjects():
        print("[LAUNCHER] QML failed to load: %s" % qml_path)
        return 1

    QTimer.singleShot(0, _flush_qml_warnings)

    if os.environ.get("SIM4_MP_SMOKE"):
        QTimer.singleShot(2500, app.quit)
        print("[LAUNCHER] QML smoke: window created OK")

    result = app.exec()
    bridge.shutdown()
    return result


if __name__ == "__main__":
    raise SystemExit(main())