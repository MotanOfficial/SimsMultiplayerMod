"""Generate the committed `runtime_manifest.json` the launcher syncs against.

Usage (run by the author after changing any runtime code)::

    python tools/make_manifest.py                 # version from git + date
    python tools/make_manifest.py --version 1.0.19

Writes `runtime_manifest.json` at the repo root listing every runtime file
(server, protocol, mod source, launcher helpers) with its sha256. Commit and
push that file (plus the code changes), and every launcher with auto-update
pulls just the changed files on next start.

The manifest intentionally excludes the launcher .exe and launcher.py itself:
the .exe is the stable bootstrap, so re-transferring it is only ever needed
when the bootstrap code itself changes.
"""

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (relative path or dir, is_dir) — everything the launcher actually runs
# besides launcher.py/build_app.py/dev_console.py.
RUNTIME_PATHS = [
    ("client_mod/build_script_mod.py", False),
    ("client_mod/scripts", True),
    ("protocol", True),
    ("server", True),
    ("tools/game_paths.py", False),
    ("tools/lobby.py", False),
    ("tools/launcher_bridge.py", False),
    ("tools/launcher_lobby.py", False),
    ("tools/save_metadata.py", False),
    ("tools/save_sync.py", False),
    ("tools/launcher_ui", True),
]

QML_SUFFIXES = (".py", ".qml", ".qmldir")


def _git_short_sha():
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            stderr=subprocess.STDOUT,
            timeout=5,
        )
        return out.decode("utf-8", "replace").strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _iter_files():
    for spec, is_dir in RUNTIME_PATHS:
        path = ROOT / spec
        if not path.exists():
            raise SystemExit("Missing runtime path: %s" % path)
        if not is_dir:
            yield path
            continue
        for child in path.rglob("*"):
            if child.is_dir():
                continue
            if "__pycache__" in child.parts:
                continue
            if not child.name.endswith(QML_SUFFIXES) and child.name != "qmldir":
                continue
            yield child


def main():
    parser = argparse.ArgumentParser(description="Generate runtime_manifest.json")
    parser.add_argument("--version", default=None, help="manifest version (default: <date>-<git sha>)")
    args = parser.parse_args()
    version = args.version or "%s-%s" % (date.today().isoformat(), _git_short_sha())

    files = []
    for path in sorted(_iter_files(), key=lambda p: p.relative_to(ROOT).as_posix()):
        rel = path.relative_to(ROOT).as_posix()
        data = path.read_bytes().replace(b"\r\n", b"\n")
        digest = hashlib.sha256(data).hexdigest()
        files.append({"path": rel, "sha256": digest})

    manifest = {"version": version, "files": files}
    target = ROOT / "runtime_manifest.json"
    target.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("[MP][UP] Wrote %s" % target)
    print("[MP][UP] version=%s files=%d" % (version, len(files)))
    total = sum(len(list(p.read_bytes())) for p in _iter_files()) / 1024.0
    print("[MP][UP] runtime payload ~%.1f KiB (incremental: only changed files are fetched)" % total)
    print("[MP][UP] commit + push both the code changes and this manifest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())