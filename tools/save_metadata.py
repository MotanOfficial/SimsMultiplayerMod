"""Slot metadata for the Sims 4 dev console (stdlib only).

Reads The Sims 4 save files and extracts what a slot-picker needs without
parsing the game's proprietary LZ4-compressed DBPF index:

- a small thumbnail. Every ``Slot_xxx.save`` bakes a *color* JPEG and then
  a smaller *grayscale* PNG at its very start, before the index. Tkinter's
  ``PhotoImage`` cannot decode JPEG, so the color JPEG is decoded to a PNG
  using Windows GDI+ via ``ctypes`` (the "imgType" Tk photo handler for JPEG
  is not present) and cached; if that fails the grayscale PNG is used;
- file facts: size, last-modified time.

The real in-game slot *name* lives inside the compressed ``SaveGameData``
(SHORT_SAVE_GAME_DATA, type 0x0D) protobuf, which is unreachable without
implementing the internal DBPF compression. Until then, slots can be given
human labels via ``SlotMeta.labels`` (persisted JSON).

    from save_metadata import SlotMeta

    meta = SlotMeta(saves_dir, cache_dir)  # lists Slot_*.save
    for it in meta.slots():
        it["thumb"]  # cached PNG path for the picker (color) or None
"""

import ctypes
import ctypes.wintypes as wintypes
import json
import os
import shutil
import struct
import tempfile
import time

THUMB_DIR_NAME = "slot-thumbs"
_LABELS_FILE = "slot-labels.json"
_THUMB_CACHE_VERSION = "2"  # bump to invalidate cached thumbnails

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"

# class GdiplusStartupInput { UINT32 GdiplusVersion; DebugEventProc Callback;
#                            BOOL SuppressBackground; BOOL SuppressExternal; }
_GDI_STARTUP = ctypes.create_string_buffer(40)
_GDI_STARTUP[:4] = b"\x01\x00\x00\x00"
_GDI_TOKEN = ctypes.c_void_p()
_GDI_DLL = ctypes.WinDLL("gdiplus")
_GDI_STARTED = _GDI_DLL.GdiplusStartup(
    ctypes.byref(_GDI_TOKEN), _GDI_STARTUP, None) == 0

if _GDI_STARTED:

    class _GUID(ctypes.Structure):
        _fields_ = [("data1", ctypes.c_ulong),
                    ("data2", ctypes.c_ushort),
                    ("data3", ctypes.c_ushort),
                    ("data4", ctypes.c_ubyte * 8)]

    _PNG_CLSID = _GUID(0x557CF406, 0x1A04, 0x11D3)
    for _i, _b in enumerate(bytes.fromhex("9A730000F81EF32E")):
        _PNG_CLSID.data4[_i] = _b


def jpeg_bytes_to_png(jpeg_path, png_path):
    """Decode a JPEG file into a PNG file with GDI+; True on success."""
    if not _GDI_STARTED:
        return False
    bitmap = ctypes.c_void_p()
    status = _GDI_DLL.GdipCreateBitmapFromFile(
        wintypes.LPCWSTR(jpeg_path), ctypes.byref(bitmap))
    if status != 0 or not bitmap.value:
        return False
    try:
        status = _GDI_DLL.GdipSaveImageToFile(
            bitmap, wintypes.LPCWSTR(png_path), ctypes.byref(_PNG_CLSID), None)
        return status == 0 and os.path.exists(png_path)
    finally:
        _GDI_DLL.GdipDisposeImage(bitmap)


def _jpeg_bytes(data):
    """Slice one complete JPEG out of ``data`` (FFD8 .. FFD9) or return None."""
    start = data.find(JPEG_MAGIC)
    if start < 0:
        return None
    pos = start + 2
    n = len(data)
    while pos + 4 <= n:
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker == 0xD9:  # EOI
            return bytes(data[start:pos + 2])
        if marker in (0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8):
            pos += 2
            continue
        if marker == 0xDA:  # SOS: entropy data ends at the first FFD9
            stop = data.find(b"\xff\xd9", pos + 2)
            return bytes(data[start:stop + 2]) if stop >= 0 else None
        seg_len = (data[pos + 2] << 8) | data[pos + 3]
        pos += 2 + seg_len
    return None


def extract_png_bytes(save_path, limit=4 * 1024 * 1024):
    """Extract the baked thumbnail PNG (colorType 0, grayscale) or None."""
    try:
        with open(save_path, "rb") as handle:
            data = handle.read(limit)
    except OSError:
        return None
    start = data.find(PNG_MAGIC)
    if start < 0:
        return None
    pos = start + 8
    while True:
        if pos + 8 > len(data):
            return None
        (chunk_len,) = struct.unpack_from(">I", data, pos)
        chunk_type = data[pos + 4:pos + 8]
        pos += 12 + chunk_len
        if chunk_type == b"IEND":
            return bytes(data[start:pos])
        if chunk_type not in (b"IHDR", b"IDAT", b"PLTE", b"tRNS", b"pHYs", b"tEXt",
                              b"zTXt", b"iTXt", b"bKGD", b"sRGB", b"gAMA", b"cHRM"):
            return None


def extract_thumbnail(save_path, out_path, limit=4 * 1024 * 1024):
    """Write a displayable thumbnail for ``save_path`` to ``out_path``.

    Prefers the baked color JPEG converted to PNG via GDI+; falls back to
    the baked grayscale PNG. Returns the path on success, else ``None``.
    """
    try:
        with open(save_path, "rb") as handle:
            data = handle.read(limit)
    except OSError:
        return None
    jpeg = _jpeg_bytes(data)
    if jpeg is not None:
        fd, tmp_jpeg = tempfile.mkstemp(suffix=".jpg", dir=os.path.dirname(out_path))
        os.close(fd)
        try:
            with open(tmp_jpeg, "wb") as handle:
                handle.write(jpeg)
            if jpeg_bytes_to_png(tmp_jpeg, out_path):
                return out_path
        except OSError:
            pass
        finally:
            try:
                os.remove(tmp_jpeg)
            except OSError:
                pass
    png = extract_png_bytes(save_path, limit)
    if png is None:
        return None
    try:
        with open(out_path, "wb") as handle:
            handle.write(png)
        return out_path
    except OSError:
        return None


class SlotMeta(object):
    """Directory of save slots + cached thumbnails + editable labels."""

    def __init__(self, saves_dir, cache_dir):
        self.saves_dir = saves_dir
        self.thumbs_dir = os.path.join(cache_dir, THUMB_DIR_NAME)
        self._version_path = os.path.join(self.thumbs_dir, ".v%s" % _THUMB_CACHE_VERSION)
        if os.path.isdir(self.thumbs_dir) and not os.path.exists(self._version_path):
            shutil.rmtree(self.thumbs_dir, ignore_errors=True)
        os.makedirs(self.thumbs_dir, exist_ok=True)
        with open(self._version_path, "w"):
            pass
        self._labels_path = os.path.join(cache_dir, _LABELS_FILE)
        self.labels = {}
        try:
            with open(self._labels_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                self.labels = {str(k): str(v) for k, v in data.items() if isinstance(v, str)}
        except (OSError, ValueError):
            pass

    def _thumb_path(self, slot_id):
        return os.path.join(self.thumbs_dir, "%s.png" % slot_id)

    def slots(self):
        """Ordered list of dicts: id, file, size, mtime, label, thumb, has_thumb."""
        items = []
        try:
            names = [
                n for n in os.listdir(self.saves_dir)
                if n.startswith("Slot_") and n.endswith(".save") and "BACKUP" not in n
            ]
        except OSError:
            return items
        for name in names:
            path = os.path.join(self.saves_dir, name)
            slot_id = name[len("Slot_"):-len(".save")]
            try:
                st = os.stat(path)
            except OSError:
                continue
            items.append({
                "id": slot_id,
                "file": name,
                "path": path,
                "size": st.st_size,
                "mtime": st.st_mtime,
                "label": self.labels.get(slot_id, ""),
            })
        items.sort(key=lambda it: it["mtime"], reverse=True)
        os.makedirs(self.thumbs_dir, exist_ok=True)
        for it in items:
            thumb = self._thumb_path(it["id"])
            if not os.path.exists(thumb) or os.path.getsize(thumb) == 0:
                if extract_thumbnail(it["path"], thumb):
                    pass
                else:
                    thumb = None
            it["thumb"] = thumb if thumb and os.path.exists(thumb) else None
            it["has_thumb"] = it["thumb"] is not None
        return items

    def set_label(self, slot_id, label):
        label = (label or "").strip()
        if label:
            self.labels[slot_id] = label
        else:
            self.labels.pop(slot_id, None)
        self._save_labels()

    def _save_labels(self):
        os.makedirs(os.path.dirname(self._labels_path), exist_ok=True)
        with open(self._labels_path, "w", encoding="utf-8") as handle:
            json.dump(self.labels, handle, ensure_ascii=False, sort_keys=True, indent=2)


def human_size(num):
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return "%.0f %s" % (num, unit) if unit == "B" else "%.1f %s" % (num, unit)
        num /= 1024.0


def human_time(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))