"""Улюблені треки й історія прослуховувань — спільні для консольної й віконної версії.

favorites.json (у теці налаштувань): що вподобано. Для кожного треку, крім шляху,
пам'ятаємо «відбиток» — виконавця, назву, альбом і тривалість. Якщо файл перенесли чи
перейменували, після сканування медіатеки знаходимо його за відбитком і тихо
оновлюємо шлях, тож лайк не губиться.

history.json: скільки разів і коли трек звучав (лише на цьому комп'ютері). З неї —
розумні списки й позначка «вже звучав» для «Прибрати неулюблені».
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from pathlib import Path

from .core import CONF_DIR, Track, is_cue_path, log, real_path
from .i18n import _

FAV_FILE = CONF_DIR / "favorites.json"
HISTORY_FILE = CONF_DIR / "history.json"
HEARD_SECONDS = 30          # стільки треба послухати, щоб трек «звучав»
SMART_LIMIT = 100
STALE_DAYS = 30             # «Давно не звучали» — понад місяць


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").casefold()
    s = re.sub(r"[\(\[].*?[\)\]]", " ", s)            # (Remastered 2011), [Live] — для пошуку пари не важливі
    return " ".join(re.findall(r"\w+", s))


def fingerprint(t: Track) -> tuple[str, str]:
    return _norm(t.artist or t.albumartist), _norm(t.title)


class _Store:
    def __init__(self, path: Path):
        self.path = path
        self._mtime = None
        self.data: dict = {}
        self.reload()

    def reload(self):
        """Друга версія Платівки могла змінити файл — перечитуємо, якщо він новіший."""
        try:
            m = self.path.stat().st_mtime
        except OSError:
            m = None
        if m == self._mtime and self.data:
            return
        try:
            self.data = json.loads(self.path.read_text("utf-8")) if m is not None else {}
        except Exception as e:
            log(f"{self.path.name}: {e}")
            self.data = {}
        self._mtime = m

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False), "utf-8")
            tmp.replace(self.path)
            self._mtime = self.path.stat().st_mtime
        except OSError as e:
            log(f"{self.path.name}: {e}")


class Favorites(_Store):
    """{"v": 1, "items": [{path, artist, title, album, length, added}]} — найновіші в кінці."""

    def __init__(self, path: Path = FAV_FILE):
        super().__init__(path)
        self._index()

    def reload(self):
        super().reload()
        self.data.setdefault("v", 1)
        self.data.setdefault("items", [])
        self._index()

    def _index(self):
        self._paths = {it["path"]: it for it in self.data.get("items", []) if "path" in it}

    def __contains__(self, path: str) -> bool:
        return path in self._paths

    def __len__(self) -> int:
        return len(self._paths)

    def paths(self) -> list[str]:
        """Від нещодавно вподобаних до давніших."""
        return [it["path"] for it in reversed(self.data["items"])]

    def set(self, t: Track, liked: bool):
        self.reload()
        if liked and t.path not in self._paths:
            self.data["items"].append({"path": t.path, "artist": t.artist or t.albumartist, "title": t.title,
                                       "album": t.album, "length": round(t.length or 0, 1),
                                       "added": int(time.time())})
        elif not liked:
            self.data["items"] = [it for it in self.data["items"] if it.get("path") != t.path]
        self._index()
        self.save()

    def toggle(self, t: Track) -> bool:
        liked = t.path not in self._paths
        self.set(t, liked)
        return liked

    def relink(self, tracks: dict[str, Track]) -> int:
        """Файли перенесли чи перейменували — знаходимо їх за відбитком. Повертає, скільки знайдено."""
        self.reload()
        lost = [it for it in self.data["items"] if it.get("path") not in tracks
                and not os.path.exists(real_path(it.get("path", "")))]
        if not lost:
            return 0
        index: dict[tuple, list[Track]] = {}
        for t in tracks.values():
            index.setdefault(fingerprint(t), []).append(t)
        taken = set(self._paths)
        moved = 0
        for it in lost:
            key = (_norm(it.get("artist", "")), _norm(it.get("title", "")))
            if not all(key):
                continue
            cands = [t for t in index.get(key, []) if t.path not in taken
                     and abs((t.length or 0) - (it.get("length") or 0)) <= 3]
            if len(cands) > 1 and it.get("album"):                # кілька версій пісні — уточнюємо альбомом
                same = [t for t in cands if _norm(t.album) == _norm(it["album"])]
                cands = same or cands
            if cands:
                best = min(cands, key=lambda t: abs((t.length or 0) - (it.get("length") or 0)))
                log(f"улюблені: {it['path']} → {best.path}")
                it["path"] = best.path
                taken.add(best.path)
                moved += 1
        if moved:
            self._index()
            self.save()
        return moved

    def export_m3u(self, dest: str, track) -> int:
        lines = ["#EXTM3U"]
        n = 0
        for p in self.paths():
            if is_cue_path(p) or not os.path.exists(p):
                continue
            t = track(p)
            lines.append(f"#EXTINF:{int(t.length or -1)},{t.display}")
            lines.append(p)
            n += 1
        Path(dest).write_text("\n".join(lines) + "\n", "utf-8")
        return n


class History(_Store):
    """{"v": 1, "tracks": {path: [скільки разів, коли востаннє]}}."""

    def __init__(self, path: Path = HISTORY_FILE):
        super().__init__(path)

    def reload(self):
        super().reload()
        self.data.setdefault("v", 1)
        self.data.setdefault("tracks", {})

    def note(self, path: str, listened: float, length: float, skipped: bool = False):
        """Трек дограв, його слухали ≥30 с або перемкнули вручну після кількох секунд."""
        if not path:
            return
        full = listened >= HEARD_SECONDS or (length and listened >= length - 2)
        if not full and not (skipped and listened >= 3):
            return
        self.reload()
        rec = self.data["tracks"].get(path, [0, 0])
        if full:
            rec[0] += 1
        rec[1] = int(time.time())
        self.data["tracks"][path] = rec
        self.save()

    def heard(self, path: str) -> bool:
        return path in self.data["tracks"]

    def plays(self, path: str) -> int:
        return self.data["tracks"].get(path, [0, 0])[0]

    def last(self, path: str) -> int:
        return self.data["tracks"].get(path, [0, 0])[1]


# ── розумні списки ──
def recently_added(tracks: dict[str, Track], limit: int = SMART_LIMIT) -> list[str]:
    return [t.path for t in sorted(tracks.values(), key=lambda t: -(t.added or t.mtime))[:limit]]


def most_played(tracks: dict[str, Track], hist: History, limit: int = SMART_LIMIT) -> list[str]:
    items = [(hist.plays(p), hist.last(p), p) for p in tracks if hist.plays(p) >= 2]
    return [p for *_x, p in sorted(items, reverse=True)[:limit]]


def not_played_lately(tracks: dict[str, Track], hist: History, limit: int = SMART_LIMIT,
                      days: int = STALE_DAYS) -> list[str]:
    edge = time.time() - days * 86400
    items = [(hist.last(p), p) for p in tracks if 0 < hist.last(p) < edge]
    return [p for _x, p in sorted(items)[:limit]]


# ── «Прибрати неулюблені» ──
def removal_plan(paths: list[str], favs: Favorites, hist: History, only_heard: bool = True) -> dict:
    """Що прибрати: не вподобане (і, якщо only_heard, лише те, що вже звучало).

    remove — що прибрати зі списку; files — справжні файли, які можна віддати в Кошик
    (без треків з .cue: один файл — увесь альбом, частину не видалиш); size — їхній розмір.
    """
    keep, remove, unheard, cue = [], [], 0, 0
    for p in paths:
        if p in favs:
            keep.append(p)
        elif only_heard and not hist.heard(p):
            keep.append(p)
            unheard += 1
        else:
            remove.append(p)
    files, size = [], 0
    for p in remove:
        if is_cue_path(p):
            cue += 1
            continue
        try:
            size += os.path.getsize(p)
            files.append(p)
        except OSError:
            pass
    return {"keep": keep, "remove": remove, "files": files, "size": size, "favorites": sum(p in favs for p in paths),
            "unheard": unheard, "cue": cue, "total": len(paths)}


def move_to_trash(files: list[str]) -> tuple[list[str], list[str]]:
    """У системний Кошик (ніколи не назавжди). Повертає (переміщені, ті, що не вдалося)."""
    from send2trash import send2trash
    done, failed = [], []
    for f in files:
        try:
            send2trash(f)
            done.append(f)
        except Exception as e:
            log(f"кошик: {f}: {e}")
            failed.append(f)
    return done, failed


def fmt_size(n: float) -> str:
    units = (_("Б"), _("КБ"), _("МБ"), _("ГБ"))
    for i, unit in enumerate(units):
        if n < 1024 or i == len(units) - 1:
            return f"{n:.0f} {unit}" if i < 2 else f"{n:.1f} {unit}"
        n /= 1024
    return ""
