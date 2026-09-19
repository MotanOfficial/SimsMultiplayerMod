"""Build the Sims 4 Multiplayer launcher into a single .exe (PyInstaller).

Usage::

    python tools/build_app.py

Outputs ``dist/Sims4MultiplayerLauncher.exe`` (windowed, one-file). No
third-party dependencies are required on the target machine — everything
(lobby server, save sync, PySide6/QML UI, GDI+ thumbnail extraction) ships
inside the .exe. The .exe is the stable bootstrap: actual runtime code is
synced incrementally from GitHub by ``tools/updater.py`` into the user's
runtime folder, so updates never mean re-transferring this .exe. Just
double-click the .exe to start it (no launcher .bat is written or needed).

Development note: without the flag ``--onedir``, PyInstaller compresses the
entire tree into one archive that is extracted to a temp folder at launch.
First start is ~3-5 seconds slower while extraction happens. Subsequent
starts are fast thanks to PyInstaller's own caching.
"""

import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

APP_NAME = "Sims4MultiplayerLauncher"
LAUNCHER = ROOT / "tools" / "launcher.py"

ADD_DATA = [
    (ROOT / "client_mod" / "scripts",    "client_mod/scripts"),
    (ROOT / "protocol",                  "protocol"),
    (ROOT / "client_mod" / "build_script_mod.py", "client_mod"),
    (ROOT / "tools" / "launcher_ui",     "tools/launcher_ui"),
]

HIDDEN_IMPORTS = [
    "simmp_client",
    "simmp_client.connectivity",
    "simmp_client.hooks",
    "simmp_client.hooks.game_hooks",
    "simmp_client.config",
    "simmp_client.state",
    "simmp_client.state.save_transfer",
    "server",
    "server.networking",
    "server.networking.server",
    "simmp",
    "simmp.constants",
    "simmp.framing",
    "simmp.messages",
    "simmp.validation",
"tools",
    "tools.game_paths",
    "tools.lobby",
    "tools.save_metadata",
    "tools.updater",
    # Qt runtime modules the QML engine loads lazily but PyInstaller must
    # trace now so their hook-collected binaries/qml data are bundled.
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
]

SEARCH_PATHS = [
    ROOT,
    ROOT / "client_mod" / "scripts",
    ROOT / "protocol",
    ROOT / "tools",
    ROOT / "server",
]

DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build" / "launcher_build"


def build():
    pyinstaller = sys.executable
    cmd = [
        pyinstaller,
        "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR),
    ]
    for path in SEARCH_PATHS:
        cmd += ["--paths", str(path)]
    for src, dest in ADD_DATA:
        sep = ";" if sys.platform == "win32" else ":"
        cmd += ["--add-data", "%s%s%s" % (str(src), sep, dest)]
    for mod in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", mod]
    cmd.append(str(LAUNCHER))

    print("[BUILD] Running PyInstaller...")
    print("[BUILD] cmd: %s" % " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print("[BUILD] *** PyInstaller FAILED (exit code %d) ***" % result.returncode)
        return False
    exe = DIST_DIR / ("%s.exe" % APP_NAME)
    if exe.exists():
        print("[BUILD] Success: %s" % exe)
        print("[BUILD] Double-click the .exe to run it (no launcher .bat needed).")
    else:
        print("[BUILD] Expected .exe not found at %s" % exe)
    return True


def main():
    return 0 if build() else 1


if __name__ == "__main__":
    raise SystemExit(main())