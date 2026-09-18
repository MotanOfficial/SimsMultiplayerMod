"""Incremental GitHub sync for the launcher's runtime code (stdlib only).

The frozen .exe is a thin, stable bootstrap: it does the GUI, game-path
detection, the lobby, and game launch. Every other Python file the app runs
(server, protocol, tools, and the mod source the launcher installs into the
game) lives in a user-writable runtime folder and is refreshed *incrementally*
from the public GitHub repo, so an update ships as a handful of small files
instead of a fresh multi-megabyte .exe.

Flow::

    sync(base_url, code_root)
        fetch remote ``runtime_manifest.json``
        diff per-file sha256 against the last-applied local manifest
        download only changed/new files (verified, atomic per file)
        store the applied manifest as ``version.json``

    mount_runtime(code_root)
        for a frozen (PyInstaller) build, insert a meta-path finder ahead of
        ``FrozenImporter`` so every synced module name imports from the
        runtime tree on disk - not the frozen copies - while every other
        name (stdlib, UI, the launcher itself) still resolves normally.

Everything is pure stdlib (`urllib`, `hashlib`, `json`, `importlib`) and the
network calls go through a pluggable ``fetcher`` so the whole module is
unit-testable offline.
"""

import hashlib
import importlib.machinery
import json
import os
import sys
import urllib.request

OWNER = "MotanOfficial"
REPO = "SimsMultiplayerMod"
REF = "main"
MANIFEST_PATH = "runtime_manifest.json"
VERSION_FILE = "version.json"

# Repo-relative prefix -> (dotted-name prefix, relative disk search root).
# ``path`` files are mapped by stripping the prefix to a module name; the
# third element names the repo folder that serves as the import search root
# for those modules.
MOUNT_ROOTS = (
    ("protocol/", "", "protocol"),
    ("client_mod/scripts/", "", "client_mod/scripts"),
    ("server/", "server.", "server"),
    ("tools/", "tools.", "tools"),
    ("client_mod/build_script_mod.py", "", "client_mod"),
)


def runtime_data_root():
    """Persistent folder for the synced runtime code (not %TEMP%).
    `%LOCALAPPDATA%\\Sims4Multiplayer\\runtime` on Windows, else under the
    user's home.
    """
    local = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(local, "Sims4Multiplayer", "runtime")


def base_url(ref=REF):
    return "https://raw.githubusercontent.com/%s/%s/%s/" % (OWNER, REPO, ref)


def fetch_text(url, timeout=8.0, fetcher=None):
    """UTF-8 body of ``url`` (or None on any failure).

    ``fetcher(url, timeout) -> str`` may be injected for tests/offline runs.
    """
    if fetcher is not None:
        try:
            return fetcher(url, timeout)
        except Exception:  # noqa: BLE001
            return None
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except Exception:  # noqa: BLE001
        return None


def fetch_bytes(url, timeout=10.0, fetcher=None):
    """Raw body of ``url`` (or None on any failure)."""
    if fetcher is not None:
        try:
            return fetcher(url, timeout)
        except Exception:  # noqa: BLE001
            return None
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read()
    except Exception:  # noqa: BLE001
        return None


def validate_manifest(manifest):
    """Check a parsed manifest; raise ValueError if malformed."""
    if not isinstance(manifest, dict):
        raise ValueError("manifest is not an object")
    if not isinstance(manifest.get("version"), str) or not manifest["version"]:
        raise ValueError("manifest.version must be a non-empty string")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ValueError("manifest.files must be a list")
    seen = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise ValueError("manifest.files entries must be objects")
        path = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(path, str) or not path or path in seen:
            raise ValueError("manifest.files path must be a unique non-empty string")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("manifest.files sha256 must be a 64-char hex digest")
        seen.add(path)
    return manifest


def fetch_manifest(base, manifest_path=MANIFEST_PATH, fetcher=None):
    """Remote manifest dict, or None when the fetch/parse fails."""
    body = fetch_text(base + manifest_path, fetcher=fetcher)
    if body is None:
        return None
    try:
        manifest = json.loads(body)
    except ValueError:
        return None
    try:
        return validate_manifest(manifest)
    except ValueError:
        return None


def load_local_manifest(code_root):
    """Last-applied manifest from ``<code_root>/version.json`` or None."""
    try:
        with open(os.path.join(code_root, VERSION_FILE), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    try:
        return validate_manifest(data)
    except ValueError:
        return None


def plan_update(remote, local):
    """[(path, sha256)] for files that differ or are missing locally."""
    changes = []
    if local is None:
        local_files = {}
    else:
        local_files = {entry["path"]: entry["sha256"] for entry in local.get("files", [])}
    for entry in remote.get("files", []):
        path = entry["path"]
        if local_files.get(path) != entry["sha256"]:
            changes.append((path, entry["sha256"]))
    return changes


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _write_atomic(target, data):
    """Write bytes to ``target`` via a temp file + os.replace."""
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + ".tmp-%d" % os.getpid()
    with open(tmp, "wb") as handle:
        handle.write(data)
    os.replace(tmp, target)


def apply_changes(base, code_root, changes, fetcher=None, log=None):
    """Download and verify only the changed files; return (ok, errors)."""
    log = log or (lambda *_: None)
    errors = []
    for path, digest in changes:
        url = base + path
        payload = None
        for _ in range(2):  # one retry for transient Github blips
            payload = fetch_bytes(url, fetcher=fetcher)
            if payload is not None:
                break
        if payload is None:
            errors.append("download failed: %s" % path)
            continue
        if _sha256(payload) != digest:
            errors.append("checksum mismatch: %s" % path)
            continue
        _write_atomic(os.path.join(code_root, path), payload)
        log("updated %s" % path)
    return (not errors, errors)


def write_local_manifest(code_root, manifest):
    os.makedirs(code_root, exist_ok=True)
    with open(os.path.join(code_root, VERSION_FILE), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1)


def sync(base, code_root, fetcher=None, log=None):
    """Fetch, diff and apply; return a summary dict (never raises net errors).

    Summary: ``{"ok", "error", "version", "changed": [paths]}``. ``ok`` is
    False only when the remote manifest could not be fetched (offline/moved),
    in which case the prior local runtime is left untouched.
    """
    log = log or (lambda *_: None)
    remote = fetch_manifest(base, fetcher=fetcher)
    if remote is None:
        return {"ok": False, "error": "could not fetch the update manifest", "version": None, "changed": []}
    local = load_local_manifest(code_root)
    changes = plan_update(remote, local)
    if not changes:
        if local is None or local.get("version") != remote["version"]:
            write_local_manifest(code_root, remote)
        return {"ok": True, "error": None, "version": remote["version"], "changed": []}
    ok, errors = apply_changes(base, code_root, changes, fetcher=fetcher, log=log)
    summary = {
        "ok": ok,
        "error": "; ".join(errors) if errors else None,
        "version": remote["version"],
        "changed": [path for path, _ in changes],
    }
    if ok:
        write_local_manifest(code_root, remote)
    return summary


def changed_mod_files(changed):
    """True when any synced path feeds the client mod (needs re-install)."""
    return any(path.startswith("client_mod/") for path in changed)


# --------------------------------------------------------------------------- #
# Runtime mounting (frozen builds only - non-frozen uses sys.path normally)
# --------------------------------------------------------------------------- #

def _mapping(rel_posix):
    """Repo-relative POSIX path -> (module name, disk search root), or None."""
    for prefix, dot_prefix, rel_root in MOUNT_ROOTS:
        if not rel_posix.startswith(prefix):
            continue
        rest = rel_posix[len(prefix):]
        if not rest:
            if prefix.endswith(".py"):
                return (dot_prefix + prefix.rsplit("/", 1)[-1][:-3], rel_root)
            return None
        if not rest.endswith(".py"):
            return None
        if rest.endswith("/__init__.py"):
            name = dot_prefix + rest[:-len("/__init__.py")]
        else:
            name = dot_prefix + rest[:-3]
        return (name.replace("/", ".").strip("."), rel_root)
    return None


def _module_name(rel_posix):
    mapping = _mapping(rel_posix)
    return mapping[0] if mapping else None


def walk_py_files(code_root):
    seen = set()
    for base, dirs, names in os.walk(code_root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in names:
            if not name.endswith(".py"):
                continue
            full = os.path.join(base, name)
            rel = os.path.relpath(full, code_root).replace("\\", "/")
            name = _module_name(rel)
            if name and name not in seen:
                seen.add(name)
                yield name, full, rel


class _RuntimeFinder(object):
    """Meta-path finder: runtime-tree names load from the runtime folder on
    disk, everything else falls through to the (PyInstaller) frozen importer.

    Runtime names are resolved against the disk search root that mirrors the
    source layout (``protocol/`` <-> ``simmp``, ``server/`` <-> ``server``,
    ...) instead of the caller's ``path``, which can point at the bundle.
    """

    def __init__(self, name_roots, original_frozen):
        self._name_roots = name_roots
        self._original = original_frozen

    def find_spec(self, fullname, path=None, target=None):
        roots = self._name_roots.get(fullname)
        if roots:
            for root_dir in roots:
                spec = importlib.machinery.PathFinder.find_spec(fullname, [root_dir])
                if spec is not None:
                    return spec
        if self._original is not None:
            return self._original.find_spec(fullname, path, target)
        return None


def mount_runtime(code_root, log=None):
    """Make the synced runtime tree the source of truth for imports.

    In a PyInstaller one-file build ``FrozenImporter`` sits at the front of
    ``sys.meta_path`` and would shadow real files on ``sys.path``. We insert
    a finder *before* it that resolves every synced module name from the
    runtime folder on disk; names not in the runtime tree (stdlib, UI, the
    launcher itself) still resolve normally. Package roots in ``sys.modules``
    that were cached by the earlier frozen bootstrap are evicted so they
    re-import from the runtime tree. Returns the number of names routed.
    """
    log = log or (lambda *_: None)
    code_root = os.path.abspath(code_root)
    if not os.path.isdir(code_root):
        return 0
    name_roots = {}
    for _name, _full, rel in walk_py_files(code_root):
        mapping = _mapping(rel)
        if not mapping:
            continue
        name, rel_root = mapping
        root = os.path.join(code_root, rel_root)
        name_roots.setdefault(name, []).append(root)
        parts = name.split(".")
        for i in range(1, len(parts)):
            pkg = ".".join(parts[:i])
            name_roots.setdefault(pkg, []).append(root)
    name_roots = {n: sorted(set(rs)) for n, rs in name_roots.items()}
    # The launcher imports tools/save_metadata.py as a top-level module too,
    # so alias every tools.* module name at the top level as well.
    for name, roots in list(name_roots.items()):
        if name.startswith("tools."):
            short = name.split(".")[-1]
            name_roots.setdefault(short, []).extend(roots)
    name_roots = {n: sorted(set(rs)) for n, rs in name_roots.items()}
    if not name_roots:
        return 0
    # Evict bundle/working-copy cached copies of every routed name so the
    # next import resolves (top-level and nested) from the runtime tree.
    for _name in name_roots:
        sys.modules.pop(_name, None)

    for finder in list(sys.meta_path):
        if getattr(finder, "_simmp_runtime", None) == code_root:
            return len(name_roots)

    original = None
    for finder in list(sys.meta_path):
        if finder.__class__.__name__ in ("FrozenImporter", "PyInstallerImportHook"):
            original = finder
            break
    runtime = _RuntimeFinder(name_roots, original)
    runtime._simmp_runtime = code_root  # type: ignore[attr-defined]
    if original is not None:
        sys.meta_path.remove(original)
    sys.meta_path.insert(0, runtime)
    log("runtime finder active for %d module(s) from %s" % (len(name_roots), code_root))
    return len(name_roots)


def installed_version(code_root):
    """'' when no local runtime manifest exists, else its version string."""
    local = load_local_manifest(code_root)
    return local["version"] if local else ""


def has_runtime(code_root):
    return os.path.isfile(os.path.join(code_root, VERSION_FILE))