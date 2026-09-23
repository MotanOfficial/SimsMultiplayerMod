"""LauncherBridge mixin: setup paths, mod install, update checks, save listing."""

import importlib
import os
import sys
import threading

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QFileDialog

from launcher_common import CODE_ROOT, GREEN, MUTED, RED, ROOT, RUNTIME, RUNTIME_DIR
from launcher_common import updater

# launcher_common binds updater before mount_runtime runs, so the frozen
# bootstrap wins that import. The manifest ships tools/updater.py too and
# the mount has already routed it, so prefer the synced copy this session.
try:
    _synced_updater = importlib.import_module("tools.updater")
except Exception:  # noqa: BLE001 - fall back to the bootstrap copy
    _synced_updater = None
if _synced_updater is not None and os.path.normcase(
    str(getattr(_synced_updater, "__file__", "") or "")
).startswith(os.path.normcase(CODE_ROOT)):
    updater = _synced_updater


class SetupMixin(object):
    # ------------------------------------------------------------------- paths
    def _guess(self, key):
        if key == "game":
            return RUNTIME.game_executable() or ""
        if key == "mods":
            return RUNTIME.mods_folder() or ""
        if key == "saves":
            return RUNTIME.saves_folder() or ""
        return ""

    @Slot(str)
    def autoFill(self, key):
        value = self._guess(key)
        if key == "game":
            self.gamePath = value
        elif key == "mods":
            self.modsPath = value
        elif key == "saves":
            self.savesPath = value
        self._note("Auto-detected %s: %s" % (key, value or "(not found)"))
        if key == "saves":
            self.refreshSaves()

    @Slot(str)
    def browse(self, key):
        if key == "game":
            current = self._game
            chosen, _ = QFileDialog.getOpenFileName(
                None,
                "Locate TS4_x64.exe",
                os.path.dirname(current) if current else "",
                "The Sims 4 (TS4_x64.exe)",
            )
        else:
            current = getattr(self, "_%s" % key)
            initial = current if current and os.path.isdir(current) else ""
            chosen = QFileDialog.getExistingDirectory(None, "Choose %s" % key, initial)
        if not chosen:
            return
        if key == "game":
            self.gamePath = chosen
        elif key == "mods":
            self.modsPath = chosen
        else:
            self.savesPath = chosen
        if key == "saves":
            self.refreshSaves()

    def _mods_path(self):
        return self._mods.strip() or None

    def _saves_path(self):
        return self._saves.strip() or None

    # ------------------------------------------------------------------- mod
    @Slot()
    def installMod(self):
        if not self._mods:
            self.setupStatusChanged.emit("No Mods folder set", RED)
            return

        def work():
            try:
                sys.path.insert(0, os.path.join(ROOT, "client_mod"))
                RUNTIME.build_script_mod.cmd_dev(self._mods)
                self.setupStatusChanged.emit(
                    "Mod installed into %s" % os.path.join(self._mods, "Sims4Multiplayer"), GREEN
                )
            except Exception as exc:  # noqa: BLE001
                self.setupStatusChanged.emit("Install failed: %s" % exc, RED)

        threading.Thread(target=work, daemon=True).start()
        self.setupStatusChanged.emit("Installing...", MUTED)

    # ---------------------------------------------------------------- updates
    def _maybe_check_updates(self):
        if not self._auto_update:
            self.updateStatusChanged.emit(
                "Auto-update off - local runtime %s" % (updater.installed_version(CODE_ROOT) or "(none)"),
                MUTED,
            )
            return
        self._check_updates(manual=False)

    @Slot()
    def checkUpdates(self):
        self._check_updates(manual=True)

    def _check_updates(self, manual=False):
        if self._update_busy:
            self._note("Update check already running.")
            return
        self._update_busy = True
        self.updateStatusChanged.emit("Checking for updates...", MUTED)
        before = updater.installed_version(CODE_ROOT) or "(none)"

        def work():
            summary = updater.sync(
                updater.base_url(),
                CODE_ROOT,
                log=lambda line: self._note(line),
            )
            mods = self._mods
            reinstalled = False
            if summary.get("ok") and summary.get("changed") and mods:
                if updater.changed_mod_files(summary["changed"]):
                    try:
                        RUNTIME.build_script_mod.cmd_dev(mods)
                        reinstalled = True
                    except Exception as exc:  # noqa: BLE001
                        self._note("Update downloaded, but mod reinstall into %s failed: %s" % (mods, exc),
                                   kind="error")
            self._on_update_done(summary, before, reinstalled)

        threading.Thread(target=work, daemon=True).start()

    def _on_update_done(self, summary, before, reinstalled):
        self._update_busy = False
        if not summary.get("ok"):
            why = summary.get("error") or "no network?"
            self.updateStatusChanged.emit(
                "Update check failed (%s) - continuing with local runtime %s" % (why, before), RED
            )
            return
        version = summary.get("version") or "?"
        changed = summary.get("changed") or []
        if not changed:
            self.updateStatusChanged.emit("Up to date (v%s)" % version, GREEN)
            return
        self.updateStatusChanged.emit("Updated to v%s - restart the launcher to apply" % version, GREEN)
        self._note("Runtime updated: %d file(s) changed (%s -> %s)." % (len(changed), before, version))
        if reinstalled:
            self._note("Mod reinstalled into the Mods folder - restart the game to apply.")
        else:
            self._note("Press 'Install mod' to install the updated mod into the game.")

    # ------------------------------------------------------------------ saves
    def _slot_items(self):
        paths = self._saves_path()
        if not paths:
            return []
        cache_dir = os.path.join(RUNTIME_DIR, "thumbs")
        slot_meta = RUNTIME.SlotMeta(paths, cache_dir)
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
            label = slot_meta.labels.get(slot_id, "")
            line = "%s  %s  %s" % (
                name,
                label or "",
                "%s  %s" % (RUNTIME.human_size(st.st_size), RUNTIME.human_time(st.st_mtime)),
            )
            items.append((line, name, full))
        items.sort(key=lambda it: os.stat(it[2]).st_mtime, reverse=True)
        return items

    @Slot()
    def refreshSaves(self):
        items = self._slot_items()
        self._save_items = items
        self._save_labels = [line for line, _, _ in items]
        self._selected_save = items[0][2] if items else None
        self.savesChanged.emit()

    @Slot(int)
    def selectSave(self, index):
        if index < 0 or index >= len(self._save_items):
            return
        line, file_, path = self._save_items[index]
        self._selected_save = path
        self._note("Selected save: %s (%s)" % (file_, path))
        self._synced = False
        self._update_host_start_button()