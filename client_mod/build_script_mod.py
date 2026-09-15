"""Build the client mod into a .ts4script package or a dev Scripts folder.

Usage:
    python client_mod/build_script_mod.py package
        -> creates client_mod/build/Sims4MultiplayerMod.ts4script

    python client_mod/build_script_mod.py dev "C:/Users/<you>/Documents/Electronic Arts/The Sims 4/Mods"
        -> copies mod source + shared protocol into Mods/Sims4Multiplayer/Scripts
           (the game auto-loads loose .py files from a mod folder's Scripts/)

The shared protocol package (protocol/simmp) is copied into the mod so the
mod is fully self-contained and never depends on S4MP/SimSync.
"""

import argparse
import ast
import pathlib
import re
import shutil
import sys
import zipfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "client_mod" / "scripts"
PROTOCOL_DIR = PROJECT_ROOT / "protocol" / "simmp"
BUILD_DIR = PROJECT_ROOT / "client_mod" / "build"
MOD_NAME = "Sims4Multiplayer"
ZIP_NAME = MOD_NAME + ".ts4script"

# The game executes every loose .py it finds under Mods with its bundled
# CPython 3.7, which has no `asyncio`. Any module shipped to the game must
# parse as Python 3.7 and must not import modules that are missing there.
UNSAFE_IMPORTS = (
    "asyncio",
    "uuid",
    "ssl",
)

_UNSAFE_RE = re.compile(
    r"^import\s+(?P<mod>%s)(\s|$)|^from\s+(?:\w+\.)*(?:%s)\s+import"
    % ("|".join(UNSAFE_IMPORTS), "|".join(UNSAFE_IMPORTS)),
    re.MULTILINE,
)


def _game_files():
    for base in (SCRIPTS_DIR, PROTOCOL_DIR):
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            yield path


def _audit_game_sources():
    """Fail the build if any game-shipped module would break in the game.

    The game's embedded Python is CPython 3.7 and lacks `asyncio`, so a
    single stray import rendered the whole mod unable to load at startup.
    """
    problems = []
    for path in _game_files():
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append("%s: not UTF-8" % path)
            continue
        try:
            ast.parse(source, filename=str(path), feature_version=(3, 7))
        except SyntaxError as exc:
            problems.append("%s: %s" % (path, exc))
        for match in _UNSAFE_RE.finditer(source):
            problems.append(
                "%s: unsafe import %r (not available in the game's Python 3.7)" % (path, match.group("mod") or match.group(0))
            )
    if problems:
        print("[MP][BUILD] GAME-SOURCE AUDIT FAILED:")
        for problem in problems:
            print("  - %s" % problem)
        print("[MP][BUILD] The mod would not load in the game; refusing to build.")
        raise SystemExit(1)


def _copy_tree(src, dst):
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts:
            continue
        if path.suffix in (".pyc", ".pyo"):
            continue
        target = dst / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _add_empty_pyo(directory):
    for path in directory.rglob("*.py"):
        pyo = path.with_suffix(".pyo")
        if not pyo.exists():
            pyo.touch()


def cmd_package():
    _audit_game_sources()
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    scripts_dir = BUILD_DIR / "scripts"
    _copy_tree(SCRIPTS_DIR, scripts_dir)
    _copy_tree(PROTOCOL_DIR, scripts_dir / "simmp")
    _add_empty_pyo(scripts_dir)

    zip_path = BUILD_DIR / ZIP_NAME
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in scripts_dir.rglob("*"):
            if not path.is_file():
                continue
            zf.write(path, path.relative_to(scripts_dir).as_posix())

    print("[MP][BUILD] Wrote %s" % zip_path)
    print("[MP][BUILD] Copy %s into your Mods folder, then enable Script Mods." % ZIP_NAME)


def cmd_dev(mods_folder):
    _audit_game_sources()
    dest = pathlib.Path(mods_folder) / MOD_NAME / "Scripts"
    if dest.exists():
        shutil.rmtree(dest)
    _copy_tree(SCRIPTS_DIR, dest)
    _copy_tree(PROTOCOL_DIR, dest / "simmp")
    print("[MP][BUILD] Dev copy installed to %s" % dest)
    print("[MP][BUILD] Enable custom content and restart the game.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the Sims 4 multiplayer client mod")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("package", help="build Sims4MultiplayerMod.ts4script")
    dev = sub.add_parser("dev", help="dev-mode copy into a The Sims 4 Mods folder")
    dev.add_argument("mods_folder", help="path to the game's Mods folder")
    args = parser.parse_args(argv)

    if args.command == "dev":
        cmd_dev(args.mods_folder)
    else:
        cmd_package()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())