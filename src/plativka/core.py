"""Ядро Платівки без інтерфейсу: треки й теги, медіатека, обкладинки, колір, mpv.

Спільне для консольної версії (Textual, app.py) і віконної (Qt, gui/).
"""
from __future__ import annotations

import asyncio
import colorsys
import io
import json
import os
import random
import re
import shlex
import shutil
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from mutagen import File as MutagenFile
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from . import __version__, sysdeps
from .i18n import _

APP_NAME = _("Платівка")
GITHUB_URL = "https://github.com/dkindratyuk-web/plativka"
ISSUES_URL = GITHUB_URL + "/issues/new/choose"
AUTHOR = "dkindratyuk-web"
VERSION = __version__
CONF_DIR = sysdeps.config_dir()
CACHE_DIR = sysdeps.cache_dir()
AUDIO_EXT = {".mp3", ".flac", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".wav",
             ".aiff", ".aif", ".wma", ".alac", ".mp2", ".ape", ".wv"}
COVER_NAMES = ("cover", "folder", "front", "album", "albumart", "albumartsmall", "artwork")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

LOG_FILE = CACHE_DIR / "plativka.log"


def log(msg: str) -> None:
    """Журнал подій відтворення: ~/.cache/plativka/plativka.log (для розбору збоїв)."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")
    except OSError:
        pass


def rotate_log() -> None:
    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 1_000_000:
            LOG_FILE.replace(LOG_FILE.with_suffix(".old.log"))
    except OSError:
        pass


def fmt_time(sec: float | None) -> str:
    if sec is None or sec < 0 or sec != sec:
        return "-:--"
    s = int(sec)
    h, m, s = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fix_text(s: str | None) -> str:
    """Виправляє «кракозябри» з тегів у cp1251, записаних як latin-1 (часто в укр./рос. MP3)."""
    if not s:
        return ""
    s = str(s).replace("\x00", "").strip()
    try:
        raw = s.encode("latin-1")
    except UnicodeEncodeError:
        return s
    if not any(b >= 0xC0 for b in raw):
        return s
    try:
        d = raw.decode("cp1251")
    except UnicodeDecodeError:
        return s
    letters = [ch for ch in d if ch.isalpha()]
    cyr = sum("Ѐ" <= ch <= "ӿ" for ch in letters)
    return d if letters and cyr >= len(letters) * 0.5 else s


def parse_num(s: str) -> int:
    try:
        return int(str(s).split("/")[0].strip() or 0)
    except ValueError:
        return 0


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def rgb_hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(clamp(c, 0, 255)) for c in rgb)


def hex_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


# ═══════════════════════════════════ ДАНІ ═══════════════════════════════════
@dataclass
class Track:
    path: str
    title: str = ""
    artist: str = ""
    album: str = ""
    albumartist: str = ""
    track: int = 0
    disc: int = 0
    year: str = ""
    length: float = 0.0
    bitrate: int = 0
    samplerate: int = 0
    channels: int = 0
    mtime: float = 0.0
    size: int = 0
    start: float = 0.0      # трек з CUE: початок і кінець у спільному файлі (0 — до кінця файлу)
    end: float = 0.0
    added: float = 0.0      # коли трек з'явився в медіатеці (для «Нещодавно додані»)

    @property
    def segment(self):
        return (self.start, self.end) if (self.start or self.end) else None

    @property
    def display(self) -> str:
        return f"{self.artist} — {self.title}" if self.artist else self.title

    @property
    def fmt(self) -> str:
        return Path(real_path(self.path)).suffix.lstrip(".").upper()

    @property
    def sort_key(self):
        return (self.disc or 0, self.track or 0, Path(self.path).name.lower())


def read_track(path: str) -> Track:
    if is_cue_path(path):
        return read_cue_track(path)
    p = Path(path)
    t = Track(path=str(p))
    try:
        st = p.stat()
        t.mtime, t.size = st.st_mtime, st.st_size
    except OSError:
        pass
    try:
        f = MutagenFile(str(p), easy=True)
    except Exception:
        f = None
    if f is None or not getattr(getattr(f, "info", None), "length", 0):
        # часто це MP3 з «сміттям» на початку або M4A з розширенням .mp3 — пробуємо явно
        from mutagen.easyid3 import EasyID3  # noqa: F401  (реєструє easy-ключі)
        from mutagen.easymp4 import EasyMP4
        from mutagen.mp3 import EasyMP3
        for cls in (EasyMP3, EasyMP4):
            try:
                g = cls(str(p))
                if getattr(g.info, "length", 0):
                    f = g
                    break
            except Exception:
                pass
    if f is not None:
        info = getattr(f, "info", None)
        if info is not None:
            t.length = float(getattr(info, "length", 0) or 0)
            t.bitrate = int(getattr(info, "bitrate", 0) or 0)
            t.samplerate = int(getattr(info, "sample_rate", 0) or 0)
            t.channels = int(getattr(info, "channels", 0) or 0)
        tags = f.tags or {}

        def g(k):
            try:
                v = tags.get(k)
            except Exception:
                return ""
            return fix_text(v[0]) if v else ""

        t.title, t.artist, t.album = g("title"), g("artist"), g("album")
        t.albumartist = g("albumartist")
        t.track, t.disc = parse_num(g("tracknumber")), parse_num(g("discnumber"))
        t.year = g("date")[:4]
    if not t.length and t.bitrate and t.size:
        t.length = t.size * 8 / t.bitrate  # груба оцінка; точну тривалість дасть mpv під час гри
    if not t.title or not t.artist:
        a, ti = name_from_file(p.stem)
        t.title = t.title or ti
        t.artist = t.artist or a
    return t


def name_from_file(stem: str):
    """«01. Kalush - Зорі» → («Kalush», «Зорі»). Для файлів без тегів."""
    s = stem.replace("_", " ").strip()
    # номер треку на початку: «01. », «1) », «01 - », «01 » (лише з нулем, щоб не зрізати «50 Cent»)
    s = re.sub(r"^\s*(\d{1,3}\s*[.)]\s*|\d{1,3}\s+-\s+|0\d\s+)", "", s)
    for sep in (" - ", " – ", " — "):
        if sep in s:
            a, t = s.split(sep, 1)
            if a.strip() and t.strip():
                return a.strip(), t.strip()
    return "", s


def scan_dir(folder: str):
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        audio = [os.path.join(root, fn) for fn in sorted(files)
                 if not fn.startswith(".") and Path(fn).suffix.lower() in AUDIO_EXT]
        split = {}
        for fn in files:
            if fn.lower().endswith(".cue") and not fn.startswith("."):
                for f, n in cue_tracks(os.path.join(root, fn), audio):
                    split.setdefault(f, []).append(n)
        for f in audio:
            if f in split:
                yield from (cue_path(f, n) for n in sorted(split[f]))
            else:
                yield f


# ═══════════════════════════════════ CUE ═══════════════════════════════════
# Альбом одним файлом (FLAC/APE/WAV) + .cue з розбивкою: кожен трек — «віртуальний»
# шлях «файл#track03». Грає той самий файл з потрібного місця до потрібного.
_CUE_RE = re.compile(r"^(.*)#track(\d{1,3})$")


def cue_path(file: str, n: int) -> str:
    return f"{file}#track{n:02d}"


def is_cue_path(p: str) -> bool:
    return bool(_CUE_RE.match(p)) and not os.path.exists(p)


def real_path(p: str) -> str:
    """Справжній файл для шляху (для треку з CUE — спільний файл альбому)."""
    m = _CUE_RE.match(p)
    return m.group(1) if m and not os.path.exists(p) else p


def _read_text(path: str) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1")


def _cue_val(rest: str) -> str:
    rest = rest.strip()
    if rest.startswith('"'):
        end = rest.find('"', 1)
        return rest[1:end if end > 0 else None]
    return rest


_cue_cache: dict[str, tuple] = {}


def parse_cue(cue: str, audio: list[str] | None = None) -> dict:
    """{файл: {"album", "performer", "date", "tracks": {n: {title, performer, start}}}}.

    Беремо лише файли, що справді лежать поруч (часто .cue каже «album.wav», а лежить
    album.flac — тоді шукаємо за назвою без розширення або беремо єдиний аудіофайл у теці).
    """
    try:
        st = os.stat(cue)
        key = (st.st_mtime, st.st_size, tuple(audio or ()))
        if cue in _cue_cache and _cue_cache[cue][0] == key:
            return _cue_cache[cue][1]
        text = _read_text(cue)
    except OSError:
        return {}
    folder = os.path.dirname(cue)
    if audio is None:
        try:
            audio = [os.path.join(folder, f) for f in sorted(os.listdir(folder))
                     if Path(f).suffix.lower() in AUDIO_EXT and not f.startswith(".")]
        except OSError:
            audio = []

    def locate(name: str) -> str | None:
        cand = os.path.join(folder, name.replace("\\", "/"))
        if os.path.isfile(cand) and Path(cand).suffix.lower() in AUDIO_EXT:
            return cand
        stem = Path(name.replace("\\", "/")).stem.lower()
        same = [a for a in audio if Path(a).stem.lower() == stem]
        if same:
            return same[0]
        return audio[0] if len(audio) == 1 else None

    album = {"album": "", "performer": "", "date": ""}
    out: dict = {}
    cur_file = None
    tr = None
    for line in text.splitlines():
        parts = line.strip().split(None, 1)
        if not parts:
            continue
        kw, rest = parts[0].upper(), (parts[1] if len(parts) > 1 else "")
        if kw == "REM":
            sub = rest.split(None, 1)
            if sub and sub[0].upper() == "DATE" and len(sub) > 1:
                album["date"] = _cue_val(sub[1])[:4]
        elif kw == "FILE":
            if rest.strip().startswith('"'):
                name = _cue_val(rest)
            else:  # FILE name.flac WAVE — без лапок
                name = rest.rsplit(None, 1)[0] if len(rest.split()) > 1 else rest
            cur_file = locate(name)
            if cur_file:
                out.setdefault(cur_file, {"tracks": {}})
            tr = None
        elif kw == "TRACK":
            try:
                n = int(rest.split()[0])
            except (ValueError, IndexError):
                tr = None
                continue
            tr = {"title": "", "performer": "", "start": None}
            if cur_file:
                out[cur_file]["tracks"][n] = tr
        elif kw in ("TITLE", "PERFORMER"):
            val = fix_text(_cue_val(rest))
            if tr is not None:
                tr["title" if kw == "TITLE" else "performer"] = val
            else:
                album["album" if kw == "TITLE" else "performer"] = val
        elif kw == "INDEX" and tr is not None:
            sub = rest.split()
            if len(sub) == 2 and sub[0] in ("01", "1"):
                try:
                    mm, ss, ff = (int(x) for x in sub[1].split(":"))
                    tr["start"] = mm * 60 + ss + ff / 75
                except ValueError:
                    pass
    for f, d in out.items():
        d.update(album)
        d["tracks"] = {n: t for n, t in d["tracks"].items() if t["start"] is not None}
    out = {f: d for f, d in out.items() if len(d["tracks"]) >= 2}
    _cue_cache[cue] = (key, out)
    return out


def cue_tracks(cue: str, audio: list[str] | None = None):
    for f, d in parse_cue(cue, audio).items():
        for n in d["tracks"]:
            yield f, n


def _cue_for(file: str):
    folder = os.path.dirname(file)
    try:
        cues = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".cue")]
    except OSError:
        return None
    for c in sorted(cues, key=lambda c: Path(c).stem.lower() != Path(file).stem.lower()):
        d = parse_cue(c).get(file)
        if d:
            return d
    return None


_base_cache: dict = {}


def read_cue_track(path: str) -> Track:
    m = _CUE_RE.match(path)
    file, n = m.group(1), int(m.group(2))
    try:
        st = os.stat(file)
        key = (file, st.st_mtime, st.st_size)
    except OSError:
        key = (file, 0, 0)
    if _base_cache.get("key") != key:   # усі треки альбому читають один і той самий файл
        _base_cache.update(key=key, track=read_track(file))
    base = _base_cache["track"]
    d = _cue_for(file)
    t = Track(path=path, album=base.album, albumartist=base.albumartist, year=base.year,
              bitrate=base.bitrate, samplerate=base.samplerate, channels=base.channels,
              mtime=base.mtime, size=base.size, track=n, disc=base.disc)
    if not d or n not in d["tracks"]:
        t.title = f"Track {n:02d}"
        return t
    info = d["tracks"][n]
    starts = sorted((k, v["start"]) for k, v in d["tracks"].items())
    t.start = info["start"]
    later = [s for k, s in starts if k > n]
    t.end = later[0] if later else 0.0
    t.length = max(0.0, (t.end or base.length) - t.start)
    t.title = info["title"] or f"Track {n:02d}"
    t.artist = info["performer"] or d["performer"] or base.artist
    t.album = d["album"] or base.album
    t.albumartist = d["performer"] or base.albumartist
    t.year = d["date"] or base.year
    return t


class Library:
    """Теки користувача + кеш тегів (щоб великі бібліотеки відкривались миттєво)."""

    def __init__(self, folders: list[str]):
        self.folders = list(folders)
        self.tracks: dict[str, Track] = {}
        self.cache_file = CACHE_DIR / "library.json"
        try:
            data = json.loads(self.cache_file.read_text("utf-8"))
            if data.get("v") not in (3, 4):
                data = {}
            for d in data.get("tracks", []):
                tr = Track(**d)
                self.tracks[tr.path] = tr
        except Exception:
            pass

    def save(self):
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            tmp = self.cache_file.with_suffix(".tmp")
            tmp.write_text(json.dumps({"v": 4, "tracks": [asdict(t) for t in self.tracks.values()]},
                                      ensure_ascii=False), "utf-8")
            tmp.replace(self.cache_file)
        except OSError:
            pass

    def scan(self, progress=None) -> int:
        found: dict[str, Track] = {}
        paths = []
        for folder in self.folders:
            if os.path.isdir(folder):
                paths.extend(scan_dir(folder))
        total = len(paths)
        first = not self.tracks          # перше сканування: «додано» = дата файлу, а не «щойно»
        now = time.time()
        for i, path in enumerate(paths):
            old = self.tracks.get(path)
            try:
                st = os.stat(real_path(path))
            except OSError:
                continue
            if old and old.mtime == st.st_mtime and old.size == st.st_size:
                found[path] = old
            else:
                found[path] = read_track(path)
            t = found[path]
            if not t.added:
                t.added = (old.added if old and old.added else (st.st_mtime if first else now))
            if progress and (i % 25 == 0 or i == total - 1):
                progress(i + 1, total)
        self.tracks = found
        self.save()
        return total

    def under(self, folder: str) -> list[Track]:
        pre = folder.rstrip(os.sep) + os.sep
        return sorted((t for p, t in self.tracks.items() if p.startswith(pre)),
                      key=lambda t: (os.path.dirname(t.path).lower(), t.sort_key))


# ═══════════════════════════════════ ОБКЛАДИНКИ ═══════════════════════════════════
def find_cover(path: str) -> bytes | None:
    path = real_path(path)
    try:
        f = MutagenFile(path)
    except Exception:
        f = None
    if f is not None and f.tags is not None:
        tags = f.tags
        try:  # ID3 (MP3): спершу передня обкладинка, потім будь-яка
            pics = tags.getall("APIC") if hasattr(tags, "getall") else []
            pics = sorted(pics, key=lambda f: 0 if getattr(f, "type", 0) == 3 else 1)
            if pics:
                return pics[0].data
        except Exception:
            pass
        try:
            covr = tags.get("covr")  # MP4/M4A
            if covr:
                return bytes(covr[0])
        except Exception:
            pass
    pics = getattr(f, "pictures", None)  # FLAC
    if pics:
        return pics[0].data
    folder = Path(path).parent
    try:
        imgs = [p for p in folder.iterdir() if p.suffix.lower() in IMG_EXT and not p.name.startswith(".")]
    except OSError:
        return None
    for name in COVER_NAMES:
        for p in imgs:
            if p.stem.lower() == name:
                return p.read_bytes()
    for p in imgs:
        if any(k in p.stem.lower() for k in ("cover", "front", "folder")):
            return p.read_bytes()
    if len(imgs) == 1:
        return imgs[0].read_bytes()
    return None


def load_cover(path: str) -> Image.Image | None:
    data = find_cover(path)
    if not data:
        return None
    try:
        im = Image.open(io.BytesIO(data))
        im.draft("RGB", (256, 256))
        return im.convert("RGB")
    except Exception:
        return None


def vinyl_image(accent, bg, dark: bool, size: int = 64) -> Image.Image:
    """Заглушка, коли обкладинки немає: платівка в кольорі теми."""
    if size != 64:  # малюємо 64 px і масштабуємо із запасом — краї гладкі
        big = _vinyl64(accent, bg, dark, 4)
        return big.resize((size, size), Image.LANCZOS)
    return _vinyl64(accent, bg, dark, 1)


def _vinyl64(accent, bg, dark: bool, k: int) -> Image.Image:
    s = 64 * k
    im = Image.new("RGB", (s, s), tuple(int(c) for c in bg))
    d = ImageDraw.Draw(im)
    disc = (24, 26, 32) if dark else (38, 42, 52)
    c = s / 2
    d.ellipse((2 * k, 2 * k, s - 3 * k, s - 3 * k), fill=disc)
    groove = tuple(int(v) for v in mix(disc, (120, 128, 145), .35))
    for r in (27, 23, 19):
        d.ellipse((c - r * k, c - r * k, c + r * k, c + r * k), outline=groove, width=k)
    a = tuple(int(v) for v in accent)
    d.ellipse((c - 12 * k, c - 12 * k, c + 12 * k, c + 12 * k), fill=a)
    d.ellipse((c - 2 * k, c - 2 * k, c + 2 * k, c + 2 * k), fill=disc)
    hl = tuple(int(v) for v in mix(disc, (255, 255, 255), .22))
    d.arc((8 * k, 8 * k, s - 9 * k, s - 9 * k), 200, 245, fill=hl, width=2 * k)
    return im



def accent_from(im: Image.Image):
    """Домінантний «живий» колір обкладинки — з нього фарбується інтерфейс."""
    small = im.resize((32, 32))
    bins: dict[int, list] = {}
    for r, g, b in small.getdata():
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if s < .18 or l < .12 or l > .92:
            continue
        w = s * (1 - abs(l - .5) * 1.4)
        k = int(h * 18) % 18
        acc = bins.setdefault(k, [0.0, 0.0, 0.0, 0.0])
        acc[0] += w
        acc[1] += r * w
        acc[2] += g * w
        acc[3] += b * w
    if not bins:
        return None
    k, (w, r, g, b) = max(bins.items(), key=lambda kv: kv[1][0])
    if w < 4:
        return None
    return (r / w, g / w, b / w)


# ═══════════════════════════════════ ТЕМИ ═══════════════════════════════════
BASES = {
    "light": dict(background="#ECEFF4", surface="#F6F7FA", panel="#E1E6EE", foreground="#1A2030",
                  accent=(14, 124, 132), dark=False),
    "dark": dict(background="#111319", surface="#181B23", panel="#20242E", foreground="#E3E7F0",
                 accent=(84, 208, 198), dark=True),
}


def tune(rgb, dark: bool, shift: float = 0.0) -> str:
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    h = (h + shift) % 1.0
    s = clamp(s, .45, .85)
    l = clamp(l, .58, .72) if dark else clamp(l, .30, .40)
    return rgb_hex(tuple(c * 255 for c in colorsys.hls_to_rgb(h, l, s)))




# ═══════════════════════════════════ ПЛЕЄРИ ═══════════════════════════════════
class MpvError(Exception):
    pass


class BasePlayer:
    demo = False

    def __init__(self, on_eof, on_error, on_message, on_external_pause=None):
        self.on_eof, self.on_error, self.on_message = on_eof, on_error, on_message
        self.on_external_pause = on_external_pause or (lambda paused: None)
        self.time_pos = 0.0
        self.duration = 0.0
        self.paused = True
        self.active = False  # файл завантажено
        self.levels = [0.0, 0.0]
        self.peaks = [0.0, 0.0]
        self.vu_ok = True
        self.replaygain = "album"     # off | track | album
        self.on_advance = None        # gapless: mpv сам перейшов до наступного файлу (шлях)
        self.seg = None               # трек з CUE: (початок, кінець) у спільному файлі

    def _decay(self, l, r):
        for i, v in enumerate((l, r)):
            self.levels[i] = max(v, self.levels[i] * .72)
            self.peaks[i] = max(self.levels[i], self.peaks[i] - .025)


class MpvPlayer(BasePlayer):
    def __init__(self, *a):
        super().__init__(*a)
        self.proc = None
        self.reader = self.writer = None
        self._req = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._seek_on_load: float | None = None
        self._dir = None
        self.entry_id = None          # який файл зараз завантажено в mpv
        self._want_pause = None       # пауза, яку ми самі просили (решта — «ззовні»)
        self.path = None              # який файл грає (справжній, для CUE — файл альбому)
        self.abs_pos = 0.0            # позиція у файлі (time_pos — у межах треку CUE)
        self._dur_abs = 0.0
        self._seg_done = False
        self._next = None             # gapless: (шлях, id у плейлисті mpv), уже доданий наступним

    @staticmethod
    def find_exe() -> str | None:
        return sysdeps.find_mpv()

    async def start(self, volume: int):
        exe = self.find_exe()
        if not exe:
            raise FileNotFoundError("mpv")
        self._dir = tempfile.mkdtemp(prefix="plativka-")
        conf = os.path.join(self._dir, "input.conf")
        Path(conf).write_text(
            "NEXT script-message plativka-next\nPREV script-message plativka-prev\n"
            # macOS шле клавішу ⏯ (F8) як PLAY, а Linux/Windows — як PLAYPAUSE: обидві перемикають паузу
            "PLAYPAUSE cycle pause\nPLAY cycle pause\nPAUSE cycle pause\n"
            "PLAYONLY set pause no\nPAUSEONLY set pause yes\n"
            "STOP script-message plativka-stop\n", "utf-8")
        args = [exe, "--no-config", "--idle=yes", "--no-video", "--no-terminal", "--audio-display=no",
                f"--input-conf={conf}", "--input-media-keys=yes",
                f"--volume={volume}", "--volume-max=100",
                "--gapless-audio=weak", "--prefetch-playlist=yes",
                f"--replaygain={self.replaygain if self.replaygain in ('track', 'album') else 'no'}",
                f"--log-file={CACHE_DIR / 'mpv.log'}",
                *shlex.split(os.environ.get("PLATIVKA_MPV_ARGS", ""))]
        quiet = dict(stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL,
                     stderr=asyncio.subprocess.DEVNULL)
        if not sysdeps.IS_WIN:
            # Зв'язок через переданий сокет: якщо плеєр зникне (закрили вікно, збій),
            # сокет закриється і mpv завершиться сам, а не гратиме «сиротою» у фоні.
            import socket
            mine, theirs = socket.socketpair()
            fd = theirs.fileno()
            os.set_inheritable(fd, True)
            self.proc = await asyncio.create_subprocess_exec(
                *args, f"--input-ipc-client=fd://{fd}", pass_fds=(fd,), **quiet)
            theirs.close()
            self.reader, self.writer = await asyncio.open_connection(sock=mine, limit=2 ** 20)
        else:
            # Windows: іменований канал; mpv прив'язаний до «завдання», яке Windows
            # закриває разом із плеєром — тож і тут mpv не переживе плеєр.
            from . import winplat
            pipe = rf"\\.\pipe\plativka-{os.getpid()}"
            self.proc = await asyncio.create_subprocess_exec(
                *args, f"--input-ipc-server={pipe}", creationflags=0x08000000, **quiet)
            winplat.kill_with_parent(self.proc.pid)
            loop = asyncio.get_running_loop()
            for _ in range(200):
                try:
                    reader = asyncio.StreamReader(limit=2 ** 20, loop=loop)
                    proto = asyncio.StreamReaderProtocol(reader, loop=loop)
                    transport, _p = await loop.create_pipe_connection(lambda: proto, pipe)
                    self.reader = reader
                    self.writer = asyncio.StreamWriter(transport, proto, reader, loop)
                    break
                except OSError:
                    if self.proc.returncode is not None:
                        raise RuntimeError("mpv exited right after start")
                    await asyncio.sleep(0.05)
            else:
                raise RuntimeError("mpv does not respond")
        asyncio.get_running_loop().create_task(self._loop())
        for i, prop in enumerate(("time-pos", "duration", "pause", "idle-active"), 1):
            await self.cmd("observe_property", i, prop)
        try:  # рівні гучності для індикатора — справжні, з потоку звуку
            await self.cmd("af", "add", "@vu:lavfi=[astats=metadata=1:reset=1]")
        except Exception:
            self.vu_ok = False

    async def cmd(self, *args):
        if not self.writer:
            raise MpvError("not connected")
        self._req += 1
        rid = self._req
        fut = asyncio.get_running_loop().create_future()
        self._pending[rid] = fut
        self.writer.write((json.dumps({"command": list(args), "request_id": rid}) + "\n").encode())
        await self.writer.drain()
        try:
            return await asyncio.wait_for(fut, 3)
        finally:
            self._pending.pop(rid, None)

    async def _loop(self):
        while True:
            try:
                line = await self.reader.readline()
            except Exception:
                break
            if not line:
                break
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            rid = msg.get("request_id")
            if rid in self._pending:
                fut = self._pending[rid]
                if not fut.done():
                    if msg.get("error") == "success":
                        fut.set_result(msg.get("data"))
                    else:
                        fut.set_exception(MpvError(msg.get("error")))
                continue
            ev = msg.get("event")
            if ev == "property-change":
                n, d = msg.get("name"), msg.get("data")
                if n == "time-pos":
                    self.abs_pos = d or 0.0
                    self.time_pos = self.abs_pos - (self.seg[0] if self.seg else 0.0)
                    if self.seg and self.seg[1] and not self._seg_done and self.abs_pos >= self.seg[1] - 0.02:
                        self._seg_done = True     # кінець треку з CUE — файл грає далі, а ми йдемо до наступного
                        self.on_eof(None)
                elif n == "duration":
                    self._dur_abs = d or 0.0
                    self._set_duration()
                elif n == "pause":
                    self.paused = bool(d)
                    if self._want_pause is not None and self.paused != self._want_pause:
                        log(f"pause={self.paused} ззовні (медіаклавіша/навушники/інша програма)")
                        self._want_pause = self.paused
                        self.on_external_pause(self.paused)
                elif n == "idle-active":
                    if d:
                        self.active = False
            elif ev == "file-loaded":
                self.active = True
                if self._seek_on_load:
                    t, self._seek_on_load = self._seek_on_load, None
                    asyncio.get_running_loop().create_task(self._safe("seek", t, "absolute"))
            elif ev == "end-file":
                reason = msg.get("reason")
                eid = msg.get("playlist_entry_id")
                log(f"end-file reason={reason} entry={eid} current={self.entry_id} "
                    f"pos={self.time_pos:.1f} dur={self.duration:.1f} {msg.get('file_error') or ''}")
                if eid is not None and self.entry_id is not None and eid != self.entry_id:
                    continue  # подія від попереднього файлу — ігноруємо
                if reason == "eof" and self._next:
                    # gapless: mpv уже грає наступний файл, який ми додали заздалегідь
                    path, nid = self._next
                    self._next = None
                    self.entry_id, self.path, self.seg = nid, path, None
                    self.time_pos = self.abs_pos = 0.0
                    self._dur_abs = self.duration = 0.0
                    log(f"gapless → {path}")
                    if self.on_advance:
                        self.on_advance(path)
                    continue
                if reason == "eof" and self._seg_done:
                    self.active = False
                    continue      # кінець треку з CUE ми вже обробили
                if reason == "eof":
                    self.active = False
                    early = None
                    if self.duration and self.time_pos < self.duration - 4:
                        early = (self.time_pos, self.duration)
                    self.on_eof(early)
                elif reason == "error":
                    self.active = False
                    self.on_error(msg.get("file_error") or "error")
            elif ev == "client-message":
                self.on_message(msg.get("args") or [])

    async def _safe(self, *args):
        try:
            return await self.cmd(*args)
        except Exception:
            return None

    def _set_duration(self):
        if self.seg:
            s, e = self.seg
            self.duration = max(0.0, (e or self._dur_abs) - s) if (e or self._dur_abs) else 0.0
        else:
            self.duration = self._dur_abs

    async def load(self, path: str, start: float = 0.0, paused: bool = False, seg=None):
        """seg=(початок, кінець) — трек з CUE усередині файлу path."""
        prev_seg, prev_path = self.seg, self.path
        self._next = None
        self._want_pause = paused
        # наступний трек з CUE того самого файлу, що вже грає: просто йдемо далі, без перезавантаження
        if (seg and prev_seg and prev_path == path and self.active and not paused and start < 1
                and prev_seg[1] and abs(seg[0] - prev_seg[1]) < 0.5 and abs(self.abs_pos - seg[0]) < 3):
            self.seg, self._seg_done = seg, False
            self.time_pos = self.abs_pos - seg[0]
            self._set_duration()
            await self._safe("set_property", "pause", False)
            log(f"cue → {seg[0]:.1f}–{seg[1]:.1f} {path}")
            return
        self.seg, self._seg_done, self.path = seg, False, path
        off = seg[0] if seg else 0.0
        self._seek_on_load = (off + start) if (off + start) > 1 else None
        self.time_pos, self.abs_pos = start, off + start
        self._dur_abs = self.duration = 0.0
        await self._safe("set_property", "pause", paused)
        res = await self._safe("loadfile", path, "replace")
        if isinstance(res, dict) and res.get("playlist_entry_id") is not None:
            self.entry_id = res["playlist_entry_id"]
        log(f"load entry={self.entry_id} start={start:.0f} paused={paused} seg={seg} {path}")

    async def preload(self, path: str | None):
        """Gapless: заздалегідь додати наступний файл у mpv, щоб він заграв без паузи.

        None — прибрати те, що було додано (змінився порядок, таймер сну тощо).
        Для треків з CUE не потрібно: вони й так грають з одного файлу.
        """
        if self._next:
            await self._safe("playlist-clear")
            self._next = None
        if not path or not self.path or self.seg:
            return
        res = await self._safe("loadfile", path, "append")
        nid = res.get("playlist_entry_id") if isinstance(res, dict) else None
        self._next = (path, nid)

    async def set_replaygain(self, mode: str):
        self.replaygain = mode
        await self._safe("set_property", "replaygain", mode if mode in ("track", "album") else "no")

    async def set_pause(self, p: bool):
        self._want_pause = p
        await self._safe("set_property", "pause", p)

    async def stop(self):
        log("stop")
        self._next = None
        await self._safe("stop")
        self.active = False
        self.time_pos = 0.0

    async def seek(self, t: float):
        if self.active:
            off = self.seg[0] if self.seg else 0.0
            if self.seg and self.seg[1]:
                t = min(t, self.seg[1] - off - 0.5)
            self._seg_done = False
            await self._safe("seek", max(0.0, t) + off, "absolute")

    async def set_volume(self, v: int):
        await self._safe("set_property", "volume", v)

    async def poll_levels(self):
        l = r = 0.0
        if self.vu_ok and self.active and not self.paused:
            d = await self._safe("get_property", "af-metadata/vu")
            if isinstance(d, dict):
                def lv(key):
                    v = d.get(key)
                    try:
                        db = float(v)
                    except (TypeError, ValueError):
                        return None
                    return clamp((db + 48) / 48, 0, 1)
                l = lv("lavfi.astats.1.RMS_level") or lv("lavfi.astats.Overall.RMS_level") or 0.0
                r = lv("lavfi.astats.2.RMS_level")
                r = l if r is None else r
        self._decay(l, r)

    async def close(self):
        try:
            if self.writer:
                self.writer.write(b'{"command":["quit"]}\n')
                await asyncio.wait_for(self.writer.drain(), 1)
        except Exception:
            pass
        if self.proc and self.proc.returncode is None:
            try:
                await asyncio.wait_for(self.proc.wait(), 1.5)
            except Exception:
                self.proc.kill()
        if self._dir:
            shutil.rmtree(self._dir, ignore_errors=True)


class DemoPlayer(BasePlayer):
    """Режим --demo: без звуку, час і рівні імітуються. Позначено в інтерфейсі."""
    demo = True

    def __init__(self, *a):
        super().__init__(*a)
        self._t0 = None
        self._path = None

    async def start(self, volume):
        pass

    async def load(self, path, start=0.0, paused=False, seg=None):
        self._path = path
        tr = read_track(path)
        self.duration = ((seg[1] or tr.length) - seg[0]) if seg else (tr.length or 200.0)
        self.duration = self.duration or 200.0
        self.time_pos = start
        self.paused = paused
        self.active = True
        self._t0 = time.monotonic() - start

    def _tick(self):
        if self.active and not self.paused:
            self.time_pos += 0.1
            if self.time_pos >= self.duration:
                self.active = False
                self.on_eof(None)

    async def set_pause(self, p):
        self.paused = p

    async def stop(self):
        self.active = False
        self.time_pos = 0.0

    async def seek(self, t):
        self.time_pos = clamp(t, 0, self.duration)

    async def set_volume(self, v):
        pass

    async def preload(self, path):
        pass

    async def set_replaygain(self, mode):
        self.replaygain = mode

    async def poll_levels(self):
        self._tick()
        if self.active and not self.paused:
            t = time.monotonic()
            base = .55 + .25 * abs(((t * .7) % 2) - 1)
            self._decay(base * random.uniform(.75, 1), base * random.uniform(.7, 1))
        else:
            self._decay(0, 0)

    async def close(self):
        pass


# ═══════════════════════════════════ ОНОВЛЕННЯ ═══════════════════════════════════
RELEASES_API = "https://api.github.com/repos/dkindratyuk-web/plativka/releases/latest"


def version_tuple(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def check_update(force: bool = False, every: float = 20 * 3600) -> dict | None:
    """Чи вийшла новіша Платівка. Не частіше ніж раз на добу; без мережі — тихо None.

    Повертає {"version": "1.3.6", "url": сторінка випуску}, якщо новіша за поточну.
    Запит лише один — до GitHub, про останній випуск; нічого про вас не надсилається.
    """
    import urllib.request
    state_file = CACHE_DIR / "update.json"
    try:
        state = json.loads(state_file.read_text("utf-8"))
    except Exception:
        state = {}
    if not force and time.time() - state.get("checked", 0) < every:
        latest = state.get("latest")
    else:
        try:
            req = urllib.request.Request(RELEASES_API, headers={
                "Accept": "application/vnd.github+json", "User-Agent": f"Plativka/{VERSION}"})
            with urllib.request.urlopen(req, timeout=8) as r:
                rel = json.loads(r.read().decode("utf-8"))
            latest = {"version": str(rel.get("tag_name", "")).lstrip("v"),
                      "url": rel.get("html_url") or GITHUB_URL + "/releases/latest"}
        except Exception as e:
            log(f"перевірка оновлень: {e}")
            return None
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps({"checked": time.time(), "latest": latest}), "utf-8")
        except OSError:
            pass
    if latest and latest.get("version") and version_tuple(latest["version"]) > version_tuple(VERSION):
        return latest
    return None


# ═══════════════════════════════ СПІЛЬНЕ ДЛЯ ОБОХ ВЕРСІЙ ═══════════════════════════════
SLEEP_CHOICES = (15, 30, 45, 60, 90)   # хвилин; ще є «після цього треку»
FADE_SECONDS = 8


class PlayerExtras:
    """Gapless, треки з CUE і таймер сну — однаково для консольної й віконної версії.

    Потрібні від класу: self.player, self.playlist, self.current, self.track(path),
    self.next_index(auto), self.history.
    """

    _preload_idx = None
    sleep_until: float | None = None    # time.monotonic(), коли зупинитися
    sleep_after_track = False
    sleep_minutes = None
    _fading = False

    # ── улюблені й історія (favorites.py) ──
    @property
    def favs(self):
        if getattr(self, "_favs", None) is None:
            from .favorites import Favorites
            self._favs = Favorites()
        return self._favs

    @property
    def hist(self):
        if getattr(self, "_hist", None) is None:
            from .favorites import History
            self._hist = History()
        return self._hist

    def end_listen(self):
        """Трек перемикають: записати в історію, скільки його слухали."""
        path = getattr(self, "_listen_path", None)
        self._listen_path = None
        if path and self.player is not None:
            try:
                self.hist.note(path, float(self.player.time_pos or 0), self.track(path).length or 0, skipped=True)
            except Exception as e:
                log(f"історія: {e}")

    def is_fav(self, path: str | None) -> bool:
        return bool(path) and path in self.favs

    def toggle_fav(self, path: str | None) -> bool | None:
        """Лайк / зняти лайк. Повертає новий стан або None, якщо треку немає."""
        if not path:
            return None
        return self.favs.toggle(self.track(path))

    def smart_lists(self, tracks: dict) -> list[tuple[str, str, list[str]]]:
        """(ключ, назва, шляхи) для розумних списків у бібліотеці."""
        from . import favorites as F
        favs = [p for p in self.favs.paths() if p in tracks or os.path.exists(real_path(p))]
        return [("favorites", _("Улюблені"), favs),
                ("recent", _("Нещодавно додані"), F.recently_added(tracks)),
                ("most", _("Найчастіше слухаю"), F.most_played(tracks, self.hist)),
                ("stale", _("Давно не звучали"), F.not_played_lately(tracks, self.hist))]

    async def load_track(self, path: str, start: float = 0.0, paused: bool = False):
        self.end_listen()
        self._listen_path = path
        t = self.track(path)
        await self.player.load(real_path(path), start=start, paused=paused, seg=t.segment)
        await self.refresh_preload()

    async def refresh_preload(self):
        """Наперед сказати mpv, що грати далі (gapless). Викликати, коли змінився порядок."""
        p = self.player
        if p is None or not hasattr(p, "preload"):
            return
        j = None
        if not self.sleep_after_track and 0 <= self.current < len(self.playlist):
            j = self.next_index(True)
        self._preload_idx = j
        nxt = None
        if j is not None:
            path = self.playlist[j]
            cur = self.track(self.playlist[self.current])
            if not self.track(path).segment and not cur.segment:
                nxt = real_path(path)
        await p.preload(nxt)

    def gapless_index(self, path: str) -> int | None:
        """Який рядок плейлиста заграв сам (gapless) — щоб показати його поточним."""
        j = self._preload_idx
        self._preload_idx = None
        if j is not None and 0 <= j < len(self.playlist) and real_path(self.playlist[j]) == path:
            return j
        for k, q in enumerate(self.playlist):
            if real_path(q) == path:
                return k
        return None

    def mark_advanced(self, j: int):
        prev = getattr(self, "_listen_path", None)
        if prev:                                       # gapless: попередній трек дограв до кінця
            n = self.track(prev).length or 0
            self.hist.note(prev, n, n)
        self._listen_path = self.playlist[j]
        if self.current != j and self.current >= 0:
            self.history = (self.history + [self.current])[-200:]
        self.current = j

    # ── таймер сну ──
    def set_sleep(self, minutes):
        """minutes: число хвилин, "track" — після поточного треку, None — вимкнути."""
        timed = isinstance(minutes, (int, float)) and not isinstance(minutes, bool)
        self.sleep_until = time.monotonic() + minutes * 60 if timed else None
        self.sleep_minutes = minutes if timed else None
        self.sleep_after_track = minutes == "track"

    @property
    def sleep_left(self) -> float | None:
        return max(0.0, self.sleep_until - time.monotonic()) if self.sleep_until else None

    def sleep_label(self) -> str:
        if self.sleep_after_track:
            return _("сон: після треку")
        left = self.sleep_left
        if left is None:
            return ""
        return _("сон: {t}").format(t=fmt_time(left))

    def sleep_consume_eof(self) -> bool:
        """Кінець треку: якщо таймер «після цього треку» — зупиняємось замість наступного."""
        if self.sleep_after_track:
            self.set_sleep(None)
            return True
        return False

    async def sleep_tick(self) -> bool:
        """Викликати щосекунди. True — таймер щойно спрацював і музику поставлено на паузу."""
        left = self.sleep_left
        if left is None or self._fading or left > 0:
            return False
        self._fading = True
        try:
            p = self.player
            if p is None or not p.active or p.paused:
                return True
            base = None
            try:
                base = await p.cmd("get_property", "volume") if hasattr(p, "cmd") else None
            except Exception:
                base = None
            if isinstance(base, (int, float)) and base > 0:
                steps = FADE_SECONDS * 5
                for i in range(1, steps + 1):   # м'яко стишуємо, а не обриваємо
                    await p._safe("set_property", "volume", base * (1 - i / steps))
                    await asyncio.sleep(0.2)
            await p.set_pause(True)
            if isinstance(base, (int, float)):
                await p._safe("set_property", "volume", base)
            return True
        finally:
            self.set_sleep(None)
            self._fading = False
