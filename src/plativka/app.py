"""
Платівка / Plativka — консольний музичний плеєр у дусі Winamp для macOS, Linux і Windows.

Звук:      mpv, керування через JSON IPC.
Інтерфейс: Textual.  Теги й обкладинки: mutagen + Pillow (+ textual-image для справжніх картинок).

Запуск:  plativka              звичайний режим
         plativka --demo       без mpv і без звуку (подивитися інтерфейс)
         plativka --lang=en    мова інтерфейсу (uk / en)
         plativka --256        примусово 256 кольорів
         plativka --truecolor  примусово 24-бітний колір
         plativka --no-images  обкладинки «пікселями» навіть у Ghostty/Kitty/iTerm2/WezTerm
"""
from __future__ import annotations

import asyncio
import colorsys
import io
import json
import os
import platform
import re
import random
import shlex
import shutil
import signal
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import __version__, pickers, sysdeps, sysvol
from .i18n import LANG, LANGS, _, file_manager_from, n_tracks

APP_NAME = _("Платівка")
GITHUB_URL = "https://github.com/dkindratyuk-web/plativka"
ISSUES_URL = GITHUB_URL + "/issues/new/choose"
AUTHOR = "dkindratyuk-web"
VERSION = __version__
CONF_DIR = sysdeps.config_dir()
CACHE_DIR = sysdeps.cache_dir()
AUDIO_EXT = {".mp3", ".flac", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".wav",
             ".aiff", ".aif", ".wma", ".alac", ".mp2"}
COVER_NAMES = ("cover", "folder", "front", "album", "albumart", "albumartsmall", "artwork")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


# ─────────────────────── колір терміналу (до імпорту Textual) ───────────────────────
def _mac_major() -> int:
    try:
        return int(platform.mac_ver()[0].split(".")[0] or 0)
    except ValueError:
        return 0


def setup_color_mode(argv: list[str]) -> None:
    if os.environ.get("TEXTUAL_COLOR_SYSTEM"):
        return
    if "--256" in argv:
        os.environ["TEXTUAL_COLOR_SYSTEM"] = "256"
    elif "--truecolor" in argv:
        os.environ["TEXTUAL_COLOR_SYSTEM"] = "truecolor"
    elif os.environ.get("TERM_PROGRAM") == "Apple_Terminal":
        # Terminal.app уміє 24-бітний колір починаючи з macOS 26
        os.environ["TEXTUAL_COLOR_SYSTEM"] = "truecolor" if _mac_major() >= 26 else "256"


setup_color_mode(sys.argv)

# Віджет справжніх картинок (Kitty/Ghostty — протокол Kitty, iTerm2/WezTerm — Sixel).
# Визначається в main() до старту інтерфейсу: потім терміналу вже не можна поставити запитання.
GRAPHICS = None


def setup_graphics(argv: list[str]) -> None:
    global GRAPHICS
    if "--no-images" in argv or os.environ.get("TERM_PROGRAM") == "Apple_Terminal":
        return
    if not (sys.stdout.isatty() and sys.stdin.isatty()):
        return
    try:
        from textual_image.renderable import Image as _R, SixelImage as _RS, TGPImage as _RT
        from textual_image.widget import Image as _W
    except Exception:
        return
    if _R in (_RS, _RT):
        GRAPHICS = _W

from mutagen import File as MutagenFile  # noqa: E402
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps  # noqa: E402
from rich.style import Style  # noqa: E402
from rich.text import Text  # noqa: E402
from textual import events, on, work  # noqa: E402
from textual.app import App, ComposeResult  # noqa: E402
from textual.binding import Binding  # noqa: E402
from textual.containers import Horizontal, Vertical, VerticalScroll  # noqa: E402
from textual.css.query import NoMatches  # noqa: E402
from textual.screen import ModalScreen, Screen  # noqa: E402
from textual.theme import Theme  # noqa: E402
from textual.widget import Widget  # noqa: E402
from textual.widgets import (DataTable, DirectoryTree, Footer, Input, OptionList,  # noqa: E402
                             SelectionList, Static, Tree)
from textual.widgets.option_list import Option  # noqa: E402


# ═══════════════════════════════════ УТИЛІТИ ═══════════════════════════════════
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

    @property
    def display(self) -> str:
        return f"{self.artist} — {self.title}" if self.artist else self.title

    @property
    def fmt(self) -> str:
        return Path(self.path).suffix.lstrip(".").upper()

    @property
    def sort_key(self):
        return (self.disc or 0, self.track or 0, Path(self.path).name.lower())


def read_track(path: str) -> Track:
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
        for fn in sorted(files):
            if not fn.startswith(".") and Path(fn).suffix.lower() in AUDIO_EXT:
                yield os.path.join(root, fn)


class Library:
    """Теки користувача + кеш тегів (щоб великі бібліотеки відкривались миттєво)."""

    def __init__(self, folders: list[str]):
        self.folders = list(folders)
        self.tracks: dict[str, Track] = {}
        self.cache_file = CACHE_DIR / "library.json"
        try:
            data = json.loads(self.cache_file.read_text("utf-8"))
            if data.get("v") != 3:
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
            tmp.write_text(json.dumps({"v": 3, "tracks": [asdict(t) for t in self.tracks.values()]},
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
        for i, path in enumerate(paths):
            old = self.tracks.get(path)
            try:
                st = os.stat(path)
            except OSError:
                continue
            if old and old.mtime == st.st_mtime and old.size == st.st_size:
                found[path] = old
            else:
                found[path] = read_track(path)
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


_BRAILLE_BITS = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))


def braille_vinyl(w: int, h: int, angle: float, groove: str, label: str, shine: str) -> Text:
    """Платівка крапками Брайля: чіткі лінії в будь-якому шрифті. angle — кут відблиску (обертання)."""
    import math
    W, H = w * 2, h * 4
    cx, cy = (W - 1) / 2, (H - 1) / 2
    R = min(W, H) / 2 - 0.3
    rings = [R - 0.4, R * .80, R * .64, R * .50]
    lab_r = R * .34
    out = Text()
    for row in range(h):
        for col in range(w):
            bits, kind = 0, 0  # 0 нічого, 1 доріжка, 2 етикетка, 3 відблиск
            for dy in range(4):
                for dx in range(2):
                    x, y = col * 2 + dx, row * 4 + dy
                    r = math.hypot(x - cx, y - cy)
                    a = math.degrees(math.atan2(y - cy, x - cx)) % 360
                    on, k = False, 0
                    if r <= lab_r:
                        on, k = r > 1.3, 2
                    elif r <= R:
                        if any(abs(r - rr) < 0.55 for rr in rings):
                            on, k = True, 1
                        d = min(abs((a - angle + 180) % 360 - 180), abs((a - angle) % 360 - 180))
                        # відблиск: тонкі дуги між доріжками, лише в секторі світла
                        if d < 20 and lab_r + 1.5 < r < R - 1.2 and abs(r - round(r / 1.9) * 1.9) < 0.5:
                            on, k = True, 3
                    if on:
                        bits |= _BRAILLE_BITS[dy][dx]
                        kind = max(kind, k)
            ch = chr(0x2800 + bits) if bits else " "
            out.append(ch, Style(color={1: groove, 2: label, 3: shine}.get(kind, groove), bold=kind == 2))
        if row < h - 1:
            out.append("\n")
    return out


def halfblocks(im: Image.Image, w: int, h: int) -> Text:
    """Картинка → w×h символів «▀» (верхній піксель — колір символу, нижній — фон)."""
    im = ImageOps.fit(im, (w, h * 2), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=2))
    im = ImageEnhance.Color(im).enhance(1.15)
    px = im.load()
    out = Text()
    for y in range(0, h * 2, 2):
        for x in range(w):
            top, bot = px[x, y], px[x, y + 1]
            out.append("▀", Style(color=rgb_hex(top), bgcolor=rgb_hex(bot)))
        if y < h * 2 - 2:
            out.append("\n")
    return out


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


def make_theme(name: str, base: str, accent_rgb=None) -> Theme:
    b = BASES[base]
    a = accent_rgb or b["accent"]
    dark = b["dark"]
    return Theme(
        name=name, dark=dark,
        primary=tune(a, dark), secondary=tune(a, dark, .09), accent=tune(a, dark, -.09),
        warning="#E0A21A" if dark else "#9A6400", error="#FF6B5E" if dark else "#C0392B",
        success="#4CD08A" if dark else "#1B7F45",
        foreground=b["foreground"], background=b["background"], surface=b["surface"], panel=b["panel"],
    )


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
                    self.time_pos = d or 0.0
                elif n == "duration":
                    self.duration = d or 0.0
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

    async def load(self, path: str, start: float = 0.0, paused: bool = False):
        self._seek_on_load = start if start > 1 else None
        self.time_pos, self.duration = start, 0.0
        self._want_pause = paused
        await self._safe("set_property", "pause", paused)
        res = await self._safe("loadfile", path, "replace")
        if isinstance(res, dict) and res.get("playlist_entry_id") is not None:
            self.entry_id = res["playlist_entry_id"]
        log(f"load entry={self.entry_id} start={start:.0f} paused={paused} {path}")

    async def set_pause(self, p: bool):
        self._want_pause = p
        await self._safe("set_property", "pause", p)

    async def stop(self):
        log("stop")
        await self._safe("stop")
        self.active = False
        self.time_pos = 0.0

    async def seek(self, t: float):
        if self.active:
            await self._safe("seek", max(0.0, t), "absolute")

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

    async def load(self, path, start=0.0, paused=False):
        self._path = path
        tr = read_track(path)
        self.duration = tr.length or 200.0
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


# ═══════════════════════════════════ ВІДЖЕТИ ═══════════════════════════════════
DIGITS = {
    "0": ("█▀█", "█ █", "█▄█"), "1": ("▀█ ", " █ ", "▄█▄"), "2": ("▀▀█", "█▀▀", "█▄▄"),
    "3": ("▀▀█", " ▀█", "▄▄█"), "4": ("█ █", "▀▀█", "  █"), "5": ("█▀▀", "▀▀█", "▄▄█"),
    "6": ("█▀▀", "█▀█", "█▄█"), "7": ("▀▀█", "  █", "  █"), "8": ("█▀█", "█▀█", "█▄█"),
    "9": ("█▀█", "▀▀█", "▄▄█"), ":": (" ", "▪", "▪"), "-": ("   ", "▀▀▀", "   "), " ": ("   ", "   ", "   "),
}


class Clickable(Static):
    """Текстова кнопка в стилі Winamp: клік запускає дію екрана."""

    def __init__(self, label: str, action: str, **kw):
        super().__init__(label, **kw)
        self._act = action

    async def on_click(self, event: events.Click) -> None:
        event.stop()
        await self.screen.run_action(self._act)


class BigTime(Static):
    """Великий час як на РК-дисплеї Winamp. Клік — показати залишок."""

    def show(self, sec: float | None, remaining: bool, blink: bool):
        txt = fmt_time(sec) if sec is not None else "-:--"
        if txt == "-:--":
            txt = "  :  "
        s = ("-" if remaining and sec is not None else " ") + txt.rjust(5)
        rows = ["", "", ""]
        for ch in s:
            g = DIGITS.get(ch, DIGITS[" "])
            if ch == ":" and blink:
                g = (" ", " ", " ")
            for i in range(3):
                rows[i] += g[i] + ("" if ch in ": " else " ")
        self.update("\n".join(rows))

    async def on_click(self, event: events.Click) -> None:
        await self.screen.run_action("toggle_remaining")


class VUMeter(Static):
    def show(self, levels, peaks, enabled: bool):
        w = max(6, self.size.width - 2)
        dark = self.app.current_theme.dark
        lo, mid, hi = ((76, 208, 138), (224, 186, 46), (255, 98, 82)) if dark else \
            ((27, 140, 72), (196, 142, 0), (205, 55, 40))
        empty = Style(color=self.app.dim_hex)
        out = Text()
        for i, name in enumerate(("L", "R")):
            out.append(name + " ", Style(color=self.app.dim_hex, bold=True))
            n = int(round(levels[i] * w)) if enabled else 0
            pk = int(round(peaks[i] * w)) if enabled else -1
            for x in range(w):
                f = x / max(1, w - 1)
                c = mix(lo, mid, f / .7) if f < .7 else mix(mid, hi, (f - .7) / .3)
                if x < n:
                    out.append("▊", Style(color=rgb_hex(c)))
                elif x == pk - 1 and pk > 0:
                    out.append("▏", Style(color=rgb_hex(c)))
                else:
                    out.append("▊", empty)
            out.append("\n")
        out.append("  " + (vu_scale(w) if enabled else _("рівні недоступні")), Style(color=self.app.dim_hex))
        self.update(out)


def vu_scale(w: int) -> str:
    """Підписи шкали в дБ на своїх місцях: -48 на початку, -12 на 3/4, 0 в кінці."""
    row = [" "] * w
    for label, frac in (("-48", 0.0), ("-12", 0.75), ("0", 1.0)):
        x = min(int(round(frac * (w - 1))), w - len(label))
        if all(c == " " for c in row[max(0, x - 1):x + len(label) + 1]):
            row[x:x + len(label)] = label
    return "".join(row)


class Marquee(Static):
    def __init__(self, **kw):
        super().__init__("", **kw)
        self._text = ""
        self._shift = 0

    def set_text(self, t: str):
        if t != self._text:
            self._text, self._shift = t, 0
        self.render_now()

    def step(self):
        self._shift += 1
        self.render_now()

    def render_now(self):
        w = max(1, self.size.width)
        t = self._text
        if len(t) <= w:
            self.update(Text(t))
            return
        loop = t + "   ✦   "
        o = self._shift % len(loop)
        self.update(Text((loop + loop)[o:o + w]))


class SeekBar(Widget):
    DEFAULT_CSS = "SeekBar { height: 1; }"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.frac = 0.0
        self.total = 0.0

    def set(self, frac, total):
        if abs(frac - self.frac) > .001 or total != self.total:
            self.frac, self.total = frac, total
            self.refresh()

    def render(self):
        lab = " " + fmt_time(self.total) if self.total else "  -:--"
        w = max(4, self.size.width - len(lab))
        pos = int(clamp(self.frac, 0, 1) * (w - 1))
        p, d = self.app.primary_hex, self.app.dim_hex
        t = Text()
        t.append("━" * pos, Style(color=p))
        t.append("●", Style(color=p, bold=True))
        t.append("─" * (w - pos - 1), Style(color=d))
        t.append(lab, Style(color=d))
        return t

    async def on_click(self, event: events.Click):
        lab = " " + fmt_time(self.total) if self.total else "  -:--"
        w = max(4, self.size.width - len(lab))
        if event.x < w:
            await self.app.seek_frac(clamp(event.x / (w - 1), 0, 1))


class VolumeBar(Widget):
    """Гучність. Ширина підлаштовується: у тісному вікні зникають підпис і відсотки."""
    DEFAULT_CSS = "VolumeBar { height: 1; width: 1fr; min-width: 6; }"
    _bar = (0, 10)  # де починаються «смужки» і скільки їх — для кліку мишкою

    def render(self):
        app = self.app
        v, w = app.volume, self.size.width
        dim, pri = Style(color=app.dim_hex), Style(color=app.primary_hex)
        label = _("без звуку ") if app.sys_muted else _("гучн ")
        pct = f" {v:>3}%"
        if w >= len(label) + 10 + len(pct):
            parts, nb = [label], 10
        elif w >= 10 + len(pct):
            parts, nb = [], 10
        else:
            parts, nb, pct = [], max(3, min(10, w)), ""
        lead = "".join(parts)
        total = len(lead) + nb + len(pct)
        pad = max(0, w - total)  # притиснути до правого краю
        self._bar = (pad + len(lead), nb)
        n = round(v / 100 * nb)
        t = Text(" " * pad)
        t.append(lead, dim)
        t.append("▮" * n, dim if app.sys_muted else pri)
        t.append("▮" * (nb - n), dim)
        t.append(pct, dim)
        return t

    async def on_click(self, event: events.Click):
        start, nb = self._bar
        x = event.x - start
        if 0 <= x < nb:
            await self.app.set_volume(round((x + 1) / nb * 100))

    async def on_mouse_scroll_up(self, event):
        await self.app.set_volume(self.app.volume + 5)

    async def on_mouse_scroll_down(self, event):
        await self.app.set_volume(self.app.volume - 5)


class EmptyHint(Static, can_focus=True):
    """Підказка в порожній панелі. На неї можна перейти Tab-ом; Enter виконує дію (додати теку)."""
    BINDINGS = [Binding("enter,space", "activate", show=False)]

    def __init__(self, text, action: str, **kw):
        super().__init__(text, **kw)
        self._act = action

    async def action_activate(self):
        await self.screen.run_action(self._act)

    async def on_click(self, event):
        await self.screen.run_action(self._act)


class KeyBar(Horizontal):
    """Нижній рядок клавіш. Показує стільки підказок, скільки влазить, — найважливіші першими."""
    DEFAULT_CSS = "KeyBar { height: 1; width: 1fr; }"

    def __init__(self, hints, **kw):
        super().__init__(**kw)
        self.hints = hints  # (клавіша, підпис, дія, пріоритет: 1 — найважливіше)

    def compose(self) -> ComposeResult:
        for i, (key, desc, action, _prio) in enumerate(self.hints):
            yield Clickable(Text.assemble((f" {key}", "bold"), f" {desc} "), action, id=f"kb-{i}", classes="kb")

    def on_mount(self):
        self.call_after_refresh(self.fit)

    def on_resize(self, event):
        self.fit()

    def fit(self):
        width = self.size.width or 80
        order = sorted(range(len(self.hints)), key=lambda i: self.hints[i][3])
        used, show = 0, set()
        for i in order:
            key, desc, _a, _p = self.hints[i]
            need = len(key) + len(desc) + 3
            if used + need <= width:
                used += need
                show.add(i)
        for i in range(len(self.hints)):
            try:
                self.query_one(f"#kb-{i}").display = i in show
            except NoMatches:
                pass


class DblClickMixin:
    """Клік виділяє, подвійний клік або Enter — відтворює (як у Winamp)."""
    _kb = False
    _last = (None, 0.0)

    def is_activation(self, key) -> bool:
        if self._kb:
            self._kb = False
            return True
        now = time.monotonic()
        prev_key, prev_t = self._last
        self._last = (key, now)
        return prev_key == key and now - prev_t < 0.45


class PlaylistTable(DblClickMixin, DataTable):
    BINDINGS = [Binding("delete,backspace", "app.remove_selected", _("Прибрати"), show=False)]

    def action_select_cursor(self):
        self._kb = True
        super().action_select_cursor()


class LibraryTree(DblClickMixin, Tree):
    BINDINGS = [
        Binding("p", "app.lib_play", _("Грати вузол"), show=False),
        Binding("a", "app.lib_append", _("Додати в список"), show=False),
    ]

    def action_select_cursor(self):
        self._kb = True
        super().action_select_cursor()


class DirsOnly(DirectoryTree):
    def filter_paths(self, paths):
        out = []
        for p in paths:
            try:
                if p.is_dir() and not p.name.startswith("."):
                    out.append(p)
            except OSError:
                pass
        return out


# ═══════════════════════════════════ ДІАЛОГИ ═══════════════════════════════════
class FolderPicker(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss(None)", _("Скасувати"))]

    def __init__(self, title: str):
        super().__init__()
        self.title_text = title

    def compose(self) -> ComposeResult:
        start = Path.home() / "Music"
        if not start.is_dir():
            start = Path.home()
        with Vertical(id="dlg"):
            yield Static(self.title_text, classes="dlg-title")
            yield Static(_("Оберіть теку стрілками або впишіть шлях. Можна перетягнути теку з {fm} у поле.").format(fm=file_manager_from()),
                         classes="dlg-help")
            yield Input(str(start), id="path")
            yield DirsOnly(str(start), id="dirs")
            with Horizontal(classes="dlg-buttons"):
                yield Clickable(_(" ↑ Вище "), "go_up", classes="btn")
                yield Static(classes="spacer")
                yield Clickable(_(" Скасувати "), "dismiss(None)", classes="btn")
                yield Clickable(_(" Додати цю теку "), "submit", classes="btn primary")

    def on_mount(self):
        self.query_one("#dirs").focus()

    @on(DirectoryTree.NodeHighlighted)
    def _hl(self, ev):
        if ev.node.data is not None:
            self.query_one("#path", Input).value = str(ev.node.data.path)

    @on(Input.Submitted)
    def action_submit(self):
        raw = self.query_one("#path", Input).value.strip()
        try:
            parts = [x.strip('"') for x in shlex.split(raw, posix=not sysdeps.IS_WIN)]
            raw = parts[0] if parts else raw
        except ValueError:
            pass
        p = Path(os.path.expanduser(raw))
        if p.is_dir():
            self.dismiss(str(p.resolve()))
        else:
            self.app.notify(_("Такої теки немає"), severity="error")

    def action_go_up(self):
        tree = self.query_one("#dirs", DirectoryTree)
        parent = Path(str(tree.path)).parent
        tree.path = parent
        self.query_one("#path", Input).value = str(parent)


class ConfirmScreen(ModalScreen):
    """Так / Ні. Enter або Y — так, Esc або N — ні."""
    BINDINGS = [Binding("escape,n", "dismiss(False)", _("Скасувати")),
                Binding("y,enter", "dismiss(True)", _("Так"))]

    def __init__(self, title: str, text: str, yes: str):
        super().__init__()
        self.title_text, self.text, self.yes = title, text, yes

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(self.title_text, classes="dlg-title")
            yield Static(self.text, classes="dlg-help")
            with Horizontal(classes="dlg-buttons"):
                yield Static(classes="spacer")
                yield Clickable(_(" Скасувати "), "dismiss(False)", classes="btn")
                yield Clickable(f" {self.yes} ", "dismiss(True)", classes="btn danger")


class HelpScreen(ModalScreen):
    """F1: про програму, автор, GitHub, усі клавіші, налаштування."""
    BINDINGS = [Binding("escape,f1,question_mark,q", "dismiss(None)", _("Закрити"))]

    def compose(self) -> ComposeResult:
        app = self.app
        with Vertical(id="dlg", classes="help"):
            yield Static(f"{APP_NAME} {VERSION}", classes="dlg-title")
            yield Static(_("Музичний плеєр у дусі Winamp. Автор: {author}. Безкоштовно, з відкритим кодом (MIT).")
                         .format(author=AUTHOR), classes="dlg-help")
            with Horizontal(classes="dlg-buttons"):
                yield Clickable(_(" GitHub — сторінка проєкту "), "open_url('github')", classes="btn primary")
                yield Clickable(_(" Повідомити про помилку "), "open_url('issues')", classes="btn")
                yield Static(classes="spacer")
                yield Clickable(_(" Закрити "), "dismiss(None)", classes="btn")
            yield Static(GITHUB_URL, id="help-url")
            yield Static(_("Налаштування"), classes="help-h")
            with Horizontal(classes="help-set"):
                yield Static(_("Гучність:"), classes="help-k")
                yield Clickable("", "toggle_volume_mode", id="set-volume", classes="flag on")
            with Horizontal(classes="help-set"):
                yield Static(_("Мова:"), classes="help-k")
                yield Clickable("", "app.toggle_language", id="set-lang", classes="flag on")
            yield Static(_("Клавіші"), classes="help-h")
            with VerticalScroll(id="help-keys"):
                yield Static(self._keys_text())

    def on_mount(self):
        self.update_settings()

    def update_settings(self):
        app = self.app
        mode = (_("як у системі (клавіші гучності керують і плеєром)") if app.volume_mode == "system"
                else _("окрема гучність плеєра"))
        if app.volume_mode == "system" and app.sysvol is None and not app.demo:
            mode += _(" — недоступно, діє гучність плеєра")
        self.query_one("#set-volume", Static).update(mode + "  ⇄")
        lang = (app.cfg.get("lang") or LANG)
        self.query_one("#set-lang", Static).update(
            {"uk": "українська", "en": "English"}[lang] + _("  ⇄  (після перезапуску)"))

    def action_toggle_volume_mode(self):
        self.app.toggle_volume_mode()
        self.set_timer(0.6, self.update_settings)

    def action_open_url(self, which: str):
        self.app.open_url(GITHUB_URL if which == "github" else ISSUES_URL)

    def _keys_text(self) -> Text:
        rows = [
            ("Z X C V B", _("назад · грати · пауза · стоп · далі")),
            (_("Пробіл"), _("пауза / продовжити")),
            ("← →", _("перемотати на 5 секунд")),
            ("+ −", _("гучність")),
            ("Tab", _("перейти між списком відтворення й медіатекою")),
            ("1 / 2", _("список відтворення / медіатека")),
            ("S / R", _("перемішування / повтор")),
            (_("J або /"), _("знайти трек")),
            ("L", _("додати теку до медіатеки")),
            ("Shift+P", _("уся медіатека в список")),
            ("M", _("показати / сховати медіатеку")),
            ("O", _("обкладинка: звичайна → велика → вимкнена")),
            ("N", _("сповіщення про трек")),
            ("T", _("світла / темна тема")),
            ("F2", _("мова інтерфейсу")),
            *([("H", _("сховати в трей"))] if sysdeps.IS_WIN else []),
            ("Delete", _("прибрати трек зі списку")),
            ("F1 / ?", _("ця довідка")),
            ("Q", _("вийти")),
            ("", ""),
            (_("У медіатеці"), ""),
            ("Enter", _("грати трек разом з альбомом")),
            ("P", _("грати виконавця / альбом / теку")),
            ("A", _("додати в кінець списку")),
        ]
        t = Text()
        for k, d in rows:
            t.append(f"{k:<12}", Style(bold=True, color=self.app.primary_hex))
            t.append(d + "\n")
        return t


class FoldersScreen(ModalScreen):
    """Теки медіатеки: додати (системне вікно), прибрати позначені, прибрати всі."""
    BINDINGS = [Binding("escape", "dismiss(None)", _("Закрити"))]

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(_("Теки медіатеки"), classes="dlg-title")
            yield Static(_("Позначте теки пробілом або кліком і натисніть «Прибрати позначені». "
                           "Файли на диску залишаться."), classes="dlg-help")
            yield SelectionList(id="folders")
            yield Static(_("Тек ще немає. Натисніть «+ Додати…», щоб обрати теку з музикою."), id="folders-empty")
            with Horizontal(classes="dlg-buttons"):
                yield Clickable(_(" + Додати… "), "add", classes="btn primary")
                yield Clickable(_(" Прибрати позначені "), "remove_checked", classes="btn")
                yield Clickable(_(" Прибрати всі "), "remove_all", classes="btn danger", id="rm-all")
                yield Static(classes="spacer")
                yield Clickable(_(" Закрити "), "dismiss(None)", classes="btn")

    def on_mount(self):
        self.refresh_list()

    def refresh_list(self):
        sl = self.query_one(SelectionList)
        sl.clear_options()
        home = str(Path.home())
        dim = Style(color=self.app.dim_hex)
        for f in self.app.lib.folders:
            n = len(self.app.lib.under(f))
            p = Path(f)
            label = Text(p.name or f, Style(bold=True))
            label.append(f"  {n_tracks(n)}" if n else "", dim)
            label.append(f"   {str(p.parent).replace(home, '~', 1)}", dim)
            sl.add_option((label, f))
        has = bool(self.app.lib.folders)
        sl.display = has
        self.query_one("#folders-empty").display = not has
        self.query_one("#rm-all").display = len(self.app.lib.folders) > 1
        if has:
            sl.highlighted = 0
            sl.focus()

    def action_add(self):
        self.app.add_library_folder(after=self.refresh_list)

    def action_remove_checked(self):
        sel = list(self.query_one(SelectionList).selected)
        if not sel:
            hl = self.query_one(SelectionList).highlighted
            if hl is not None and self.app.lib.folders:
                sel = [self.query_one(SelectionList).get_option_at_index(hl).value]
        if sel:
            self.app.remove_folders(sel)
            self.refresh_list()

    def action_remove_all(self):
        def done(ok):
            if ok:
                self.app.clear_library()
                self.refresh_list()
        self.app.push_screen(ConfirmScreen(
            _("Прибрати всі теки з медіатеки?"),
            _("Медіатека стане порожньою. Файли на диску залишаться, список відтворення теж. "
              "Теки можна буде додати знову клавішею L."),
            _("Прибрати всі")), done)


class ListPicker(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss(None)", _("Скасувати"))]

    def __init__(self, title: str, items: list[tuple[str, str]], help_text: str = ""):
        super().__init__()
        self.title_text, self.items, self.help_text = title, items, help_text

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(self.title_text, classes="dlg-title")
            if self.help_text:
                yield Static(self.help_text, classes="dlg-help")
            yield OptionList(*[Option(Text(lbl), id=k) for k, lbl in self.items], id="opts")

    def on_mount(self):
        self.query_one("#opts").focus()

    @on(OptionList.OptionSelected)
    def _sel(self, ev):
        self.dismiss(ev.option.id)


class JumpScreen(ModalScreen):
    """Аналог «Jump to file» (J) з Winamp: швидкий пошук по медіатеці й списку."""
    BINDINGS = [Binding("escape", "dismiss(None)", _("Закрити"))]

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(_("Знайти трек"), classes="dlg-title")
            yield Input(placeholder=_("виконавець, назва або альбом…"), id="q")
            yield OptionList(id="res")
            yield Static(_("Enter — грати  ·  ↓ — до результатів  ·  Esc — закрити"), classes="dlg-help")

    def on_mount(self):
        self.pool = self.app.search_pool()
        self.query_one("#q").focus()
        self._fill("")

    def _fill(self, q: str):
        toks = q.lower().split()
        ol = self.query_one("#res", OptionList)
        ol.clear_options()
        n = 0
        opts = []
        for path, hay, label in self.pool:
            if all(t in hay for t in toks):
                opts.append(Option(Text(label), id=path))
                n += 1
                if n >= 300:
                    break
        ol.add_options(opts)
        if opts:
            ol.highlighted = 0

    @on(Input.Changed)
    def _ch(self, ev):
        self._fill(ev.value)

    @on(Input.Submitted)
    def _sub(self):
        ol = self.query_one("#res", OptionList)
        if ol.option_count and ol.highlighted is not None:
            self.dismiss(ol.get_option_at_index(ol.highlighted).id)

    def on_key(self, ev: events.Key):
        if ev.key == "down" and self.focused is self.query_one("#q"):
            self.query_one("#res").focus()
            ev.stop()

    @on(OptionList.OptionSelected)
    def _sel(self, ev):
        self.dismiss(ev.option.id)


class NoMpvScreen(Screen):
    BINDINGS = [Binding("q,escape", "app.quit", _("Вийти"))]

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(_("Потрібен mpv"), classes="dlg-title")
            cmd = sysdeps.mpv_install_hint()
            how = (_("Встановіть його командою:\n\n    {cmd}\n\nі запустіть плеєр знову.").format(cmd=cmd)
                   if cmd else _("Перевстановіть Платівку: mpv входить до інсталятора."))
            yield Static(_("Платівка відтворює звук через mpv, але його не знайдено.\n\n{how}\n\n"
                           "Подивитися інтерфейс без звуку: plativka --demo").format(how=how),
                         classes="dlg-help")
        yield Footer()


# ═══════════════════════════════════ ГОЛОВНИЙ ЕКРАН ═══════════════════════════════════
class MainScreen(Screen):
    # Клавіші Z X C V B — як у Winamp
    BINDINGS = [
        Binding("z", "prev", _("Попер."), show=False),
        Binding("x", "play", _("Грати"), show=False),
        Binding("c", "pause", _("Пауза"), show=False),
        Binding("v", "stop", _("Стоп"), show=False),
        Binding("b", "next", _("Наст."), show=False),
        Binding("tab", "next_panel(1)", _("Панель"), show=False, priority=True),
        Binding("shift+tab", "next_panel(-1)", _("Панель"), show=False, priority=True),
        Binding("1", "focus_panel('playlist')", _("Список"), show=False),
        Binding("2", "focus_panel('library')", _("Медіатека"), show=False),
        Binding("f1,question_mark", "help", _("Довідка"), show=False),
        Binding("space", "toggle", _("Пауза"), show=False, priority=True),
        Binding("left", "seek(-5)", _("−5 с"), show=False, priority=True),
        Binding("right", "seek(5)", _("+5 с"), show=False, priority=True),
        Binding("plus,equals_sign", "volume(5)", _("Гучн+"), show=False),
        Binding("minus", "volume(-5)", _("Гучн−"), show=False),
        Binding("l", "add_library_folder", _("Тека"), show=False),
        Binding("j,slash", "jump", _("Пошук"), show=False),
        Binding("s", "shuffle", _("Перемішати"), show=False),
        Binding("r", "repeat", _("Повтор"), show=False),
        Binding("n", "popups", _("Сповіщення"), show=False),
        Binding("m", "toggle_library", _("Медіатека"), show=False),
        Binding("t", "theme", _("Тема"), show=False),
        Binding("o", "cover_mode", _("Обкладинка"), show=False),
        Binding("P,shift+p", "app.lib_all", _("Усе в список"), show=False),
        Binding("f2", "language", _("Мова"), show=False),
        *([Binding("h", "hide_to_tray", _("У трей"), show=False)] if sysdeps.IS_WIN else []),
        Binding("q", "app.quit", _("Вихід"), show=False),
    ]
    KEY_HINTS = [
        ("Z", _("Попер."), "prev", 2), ("X", _("Грати"), "play", 1), ("C", _("Пауза"), "pause", 1),
        ("V", _("Стоп"), "stop", 3), ("B", _("Наст."), "next", 1),
        ("Tab", _("Панель"), "next_panel(1)", 2), ("J", _("Пошук"), "jump", 2),
        ("L", _("Тека"), "add_library_folder", 4), ("M", _("Медіатека"), "toggle_library", 3),
        ("T", _("Тема"), "theme", 5),
        *([("H", _("У трей"), "hide_to_tray", 4)] if sysdeps.IS_WIN else []),
        ("F1", _("Довідка"), "help", 1), ("Q", _("Вихід"), "app.quit", 2),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal(id="body"):
            with Vertical(id="left"):
                with Vertical(id="main-win"):
                    with Horizontal(id="top"):
                        with Vertical(id="cover-box"):
                            yield Static(id="cover")
                            if GRAPHICS is not None:
                                yield GRAPHICS(id="cover-img")
                        with Vertical(id="lcd"):
                            with Horizontal(id="lcd-row"):
                                yield Static("■", id="state-icon")
                                yield BigTime(id="bigtime")
                                yield VUMeter(id="vu")
                            yield Marquee(id="marquee")
                            yield Static(id="info")
                            with Horizontal(id="flags"):
                                yield Clickable(_("перемішати"), "shuffle", id="f-shuffle", classes="flag")
                                yield Clickable(_("повтор: вимк"), "repeat", id="f-repeat", classes="flag")
                                yield Clickable(_("сповіщ: плеєр"), "popups", id="f-popups", classes="flag")
                                yield Static(id="f-extra")
                    yield SeekBar(id="seek")
                    with Horizontal(id="transport"):
                        yield Clickable(" ◀◀ ", "prev", classes="tbtn")
                        yield Clickable(" ▶ ", "play", classes="tbtn")
                        yield Clickable(" ‖ ", "pause", classes="tbtn")
                        yield Clickable(" ■ ", "stop", classes="tbtn")
                        yield Clickable(" ▶▶ ", "next", classes="tbtn")
                        yield Clickable(" ⏏ ", "add_playlist_folder", classes="tbtn", id="eject")
                        yield VolumeBar(id="volume")
                with Vertical(id="pl-win"):
                    yield PlaylistTable(id="playlist", cursor_type="row", zebra_stripes=False,
                                        show_cursor=True)
                    yield EmptyHint(_("Список порожній.\n\nОберіть альбом чи теку в медіатеці й натисніть Enter або P, "
                                      "або додайте теку кнопкою «+ Тека» нижче."), "add_playlist_folder", id="pl-empty")
                    with Horizontal(classes="tools"):
                        yield Clickable(_(" + Тека "), "add_playlist_folder", classes="btn")
                        yield Clickable(_(" − Прибрати "), "app.remove_selected", classes="btn")
                        yield Clickable(_(" Очистити "), "clear_playlist", classes="btn")
                        yield Static(classes="spacer")
                        yield Clickable(_(" Знайти "), "jump", classes="btn")
            with Vertical(id="library-win"):
                with Horizontal(classes="tabs"):
                    yield Clickable(_(" Виконавці "), "lib_mode('artists')", id="tab-artists", classes="tab")
                    yield Clickable(_(" Теки "), "lib_mode('folders')", id="tab-folders", classes="tab")
                yield LibraryTree(_("Медіатека"), id="library")
                yield EmptyHint(_("Медіатека порожня.\n\nДодайте теку з музикою: клавіша L або кнопка «+ Тека».\n\n"
                                  "Або просто перетягніть теку з {fm} у вікно плеєра.").format(fm=file_manager_from()),
                                "add_library_folder", id="lib-empty")
                with Horizontal(classes="tools"):
                    yield Clickable(_(" + Тека "), "add_library_folder", classes="btn")
                    yield Clickable(_(" Теки… "), "remove_library_folder", classes="btn")
                    yield Static(classes="spacer")
                    yield Clickable(_(" ▶ Усе "), "app.lib_all", classes="btn primary")
                    yield Clickable(" ↻ ", "rescan", classes="btn")
        yield KeyBar(self.KEY_HINTS, id="keybar")

    def on_mount(self):
        self.query_one("#main-win").border_title = APP_NAME
        self.query_one("#pl-win").border_title = _("Список відтворення")
        self.query_one("#library-win").border_title = _("Медіатека")
        tree = self.query_one(LibraryTree)
        tree.show_root = False
        tree.guide_depth = 2
        self.app.after_main_mount()

    # дії делегуються в застосунок
    async def action_prev(self): await self.app.prev()
    async def action_next(self): await self.app.next()
    async def action_play(self): await self.app.play()
    async def action_pause(self): await self.app.pause()
    async def action_toggle(self): await self.app.toggle()
    async def action_stop(self): await self.app.stop()
    async def action_seek(self, d: int): await self.app.seek_rel(d)
    async def action_volume(self, d: int): await self.app.set_volume(self.app.volume + d)
    def action_shuffle(self): self.app.toggle_shuffle()
    def action_repeat(self): self.app.cycle_repeat()
    def action_popups(self): self.app.cycle_popups()
    def action_theme(self): self.app.toggle_theme()
    def action_help(self): self.app.push_screen(HelpScreen())

    def action_focus_panel(self, which: str):
        if which == "library" and not self.app.show_library:
            self.app.toggle_library()
            return
        a, b = ("#library", "#lib-empty") if which == "library" else ("#playlist", "#pl-empty")
        target = self.query_one(a) if self.query_one(a).display else self.query_one(b)
        if target.display:
            target.focus()
        elif which == "playlist" and self.app.show_library and self.has_class("narrow"):
            self.app.toggle_library()

    def action_next_panel(self, step: int):
        def pick(a, b):
            wa, wb = self.query_one(a), self.query_one(b)
            return wa if wa.display else wb
        panels = [w for w in (pick("#playlist", "#pl-empty"), pick("#library", "#lib-empty"))
                  if w.display and w.parent.styles.display != "none"]
        if self.has_class("narrow"):  # у вузькому вікні видно одну панель — перемикаємо, що видно
            self.app.toggle_library()
            return
        if not panels:
            return
        cur = self.focused
        i = next((k for k, w in enumerate(panels) if w is cur or (cur is not None and w.parent is cur.parent)), -1)
        panels[(i + step) % len(panels)].focus()

    def on_descendant_focus(self, event):
        self.app.update_panel_titles()

    def on_descendant_blur(self, event):
        self.app.update_panel_titles()
    def action_language(self): self.app.toggle_language()
    def action_hide_to_tray(self): self.app.hide_to_tray()
    def action_cover_mode(self): self.app.cycle_cover_mode()
    def action_toggle_library(self): self.app.toggle_library()
    def action_toggle_remaining(self): self.app.toggle_remaining()
    def action_lib_mode(self, mode: str): self.app.set_lib_mode(mode)
    def action_add_library_folder(self): self.app.add_library_folder()
    def action_remove_library_folder(self): self.app.remove_library_folder()
    def action_add_playlist_folder(self): self.app.add_playlist_folder()
    def action_clear_playlist(self): self.app.clear_playlist()
    def action_rescan(self): self.app.start_scan()
    def action_jump(self): self.app.jump()

    def on_paste(self, event: events.Paste):
        self.app.handle_paste(event.text)

    @on(DataTable.RowSelected, "#playlist")
    async def _row(self, ev: DataTable.RowSelected):
        tbl = self.query_one(PlaylistTable)
        if tbl.is_activation(ev.cursor_row):
            await self.app.play_index(ev.cursor_row)

    @on(Tree.NodeSelected, "#library")
    async def _node(self, ev: Tree.NodeSelected):
        tree = self.query_one(LibraryTree)
        data = ev.node.data
        if not data or data[0] != "track":
            tree._kb = False
            return
        if tree.is_activation(id(ev.node)):
            await self.app.play_from_library(ev.node)


# ═══════════════════════════════════ ЗАСТОСУНОК ═══════════════════════════════════
CSS = """
Screen { background: $background; }
#body { height: 1fr; }
#left { width: 1fr; min-width: 60; }

/* ── головне вікно ── */
#main-win {
    height: 13; padding: 0 1;
    border: round $primary 55%; border-title-color: $primary; border-title-style: bold;
    border-subtitle-color: $warning;
    background: $primary 5%;
}
#top { height: 8; }
#cover-box { width: 16; height: 8; }
#cover, #cover-img { width: 100%; height: 100%; }
Screen.big-cover #main-win { height: 17; }
Screen.big-cover #top { height: 12; }
Screen.big-cover #cover-box { width: 24; height: 12; }
#lcd { width: 1fr; height: 8; margin-left: 2; padding: 0 1; background: $primary 11%; }
#lcd-row { height: 3; }
#state-icon { width: 3; height: 3; content-align: left middle; color: $primary; text-style: bold; }
#bigtime { width: 22; height: 3; color: $primary; }
#vu { width: 1fr; height: 3; margin-left: 1; }
#marquee { height: 1; margin-top: 1; text-style: bold; color: $foreground; }
#info { height: 1; color: $foreground 65%; }
#flags { height: 1; }
.flag { width: auto; margin-right: 1; color: $foreground 35%; }
.flag.on { color: $primary; text-style: bold; }
.flag:hover { color: $foreground; }
#f-extra { width: 1fr; color: $foreground 45%; text-align: right; }
#seek { margin-top: 1; }
#transport { height: 1; }
.tbtn { width: auto; color: $foreground 80%; background: $primary 10%; margin-right: 1; text-style: bold; }
.tbtn:hover { background: $primary 35%; color: $foreground; }
#eject { margin-left: 1; }
.spacer { width: 1fr; }

/* ── список відтворення ── */
#pl-win {
    height: 1fr; padding: 0 1;
    border: round $secondary 30%; border-title-color: $secondary 70%; border-title-style: bold;
    border-subtitle-color: $foreground 55%;
    background: $secondary 4%;
}
#playlist { height: 1fr; background: transparent; scrollbar-size-vertical: 1; overflow-x: hidden; }
#playlist > .datatable--header { background: transparent; color: $secondary; text-style: bold; }
#playlist > .datatable--cursor { background: $secondary 30%; color: $foreground; text-style: bold; }
#playlist > .datatable--hover { background: $secondary 12%; }
#playlist:blur > .datatable--cursor { background: $secondary 14%; }
#pl-empty { height: 1fr; content-align: center middle; text-align: center; color: $foreground 55%; display: none; }
#pl-empty:focus, #lib-empty:focus { color: $foreground; text-style: bold; }
.tools { height: 1; margin-top: 1; }
.btn { width: auto; color: $foreground 75%; background: $foreground 6%; margin-right: 1; }
.btn:hover { background: $foreground 15%; color: $foreground; }
.btn.primary { background: $primary 80%; color: $background; text-style: bold; }
.btn.danger { background: $error 85%; color: $background; text-style: bold; }

/* ── медіатека ── */
#library-win {
    width: 42%; max-width: 64; min-width: 32; padding: 0 1;
    border: round $accent 30%; border-title-color: $accent 70%; border-title-style: bold;
    border-subtitle-color: $foreground 55%;
    background: $accent 4%;
}
.tabs { height: 1; margin-bottom: 1; }
.tab { width: auto; color: $foreground 50%; margin-right: 1; }
.tab.on { background: $accent 22%; color: $accent; text-style: bold; }
.tab:hover { color: $foreground; }
#library { height: 1fr; background: transparent; scrollbar-size-vertical: 1; overflow-x: hidden; }
#library > .tree--cursor { background: $accent 30%; color: $foreground; text-style: bold; }
#library > .tree--highlight { background: $accent 10%; }
#library > .tree--guides { color: $accent 30%; }
#library > .tree--guides-selected { color: $accent 60%; }
#library:blur > .tree--cursor { background: $accent 14%; }
#lib-empty { height: 1fr; content-align: center middle; text-align: center; color: $foreground 55%; display: none; }

/* вузький термінал: вікна стоять стовпчиком, медіатека заміщує список (M) */
Screen.narrow #body { layout: vertical; }
Screen.narrow #left { min-width: 0; height: 1fr; }
Screen.narrow.lib-shown #left { height: 13; }
Screen.narrow.lib-shown #pl-win { display: none; }
Screen.narrow #library-win { width: 1fr; max-width: 999; min-width: 0; height: 1fr; }
Screen.lib-hidden #library-win { display: none; }

Footer { background: $primary 8%; }
/* активна панель: товста яскрава рамка */
#pl-win:focus-within { border: heavy $secondary; border-title-color: $secondary; background: $secondary 7%; }
#library-win:focus-within { border: heavy $accent; border-title-color: $accent; background: $accent 7%; }
#keybar { background: $primary 8%; }
.kb { width: auto; color: $foreground 80%; }
.kb:hover { background: $primary 25%; color: $foreground; }
/* довідка і теки */
#dlg.help { width: 86; }
#help-url { color: $foreground 50%; margin-bottom: 1; }
.help-h { text-style: bold; color: $primary; margin-top: 1; }
.help-set { height: 1; }
.help-k { width: 12; color: $foreground 70%; }
#help-keys { height: 12; background: $primary 4%; }
#folders { height: auto; max-height: 14; background: $primary 4%; border: none; margin-bottom: 1; }
#folders-empty { color: $foreground 60%; margin-bottom: 1; }
Toast { background: $surface; width: 44; }
Toast.-information { border-left: outer $primary; }
Toast.-information > .toast--title { color: $primary; text-style: bold; }

/* ── діалоги ── */
ModalScreen { align: center middle; background: $background 70%; }
NoMpvScreen { align: center middle; }
#dlg {
    width: 78; max-width: 95%; height: auto; max-height: 90%; padding: 1 2;
    border: round $primary 60%; background: $surface;
}
.dlg-title { text-style: bold; color: $primary; margin-bottom: 1; }
.dlg-help { color: $foreground 65%; margin-bottom: 1; }
#dlg Input { margin-bottom: 1; border: tall $primary 30%; background: $primary 6%; }
#dlg Input:focus { border: tall $primary 70%; }
#dirs { height: 16; background: $primary 4%; margin-bottom: 1; }
#dirs > .tree--cursor { background: $primary 30%; }
.dlg-buttons { height: 1; margin-top: 1; }
#opts, #res { height: auto; max-height: 18; background: $primary 4%; border: none; }
#opts > .option-list--option-highlighted, #res > .option-list--option-highlighted { background: $primary 30%; }
.dlg-buttons { height: 1; }
"""


class Plativka(App):
    CSS = CSS
    TITLE = APP_NAME
    ENABLE_COMMAND_PALETTE = False

    def __init__(self, demo: bool = False):
        super().__init__()
        self.demo = demo
        self.cfg = self.load_cfg()
        self.lib = Library(self.cfg["folders"])
        self.extra: dict[str, Track] = {}
        self.playlist: list[str] = [p for p in self.cfg["playlist"] if isinstance(p, str)]
        self.current: int = self.cfg.get("current", -1)
        self.player_volume: int = int(self.cfg.get("volume", 70))   # власна гучність плеєра (mpv)
        self.volume: int = self.player_volume                         # те, що показує смужка
        self.volume_mode: str = self.cfg.get("volume_mode", "system")  # system — дзеркало гучності системи
        self.sysvol = None
        self.sys_muted = False
        self.smtc = None
        self.shuffle: bool = bool(self.cfg.get("shuffle", False))
        self.repeat: str = self.cfg.get("repeat", "off")
        self.remaining: bool = bool(self.cfg.get("remaining", False))
        self.popups: str = self.cfg.get("popups", "app")  # off | app | system
        self.base: str = self.cfg.get("theme", "light")
        self.lib_mode: str = self.cfg.get("lib_mode", "artists")
        self.show_library: bool = bool(self.cfg.get("show_library", True))
        self.cover_mode: str = self.cfg.get("cover_mode") or ("big" if self.cfg.get("big_cover") else "normal")
        self._spin = 0.0
        self.history: list[int] = []
        self.stopped = True
        self.cover_accent = None
        self.cover_img: Image.Image | None = None
        self.player: BasePlayer | None = None
        self.main: MainScreen | None = None
        self.scanning = False
        self._theme_flip = False
        self._last_cover_path = None
        self._load_lock = asyncio.Lock()
        self._load_gen = 0
        self.tray = None
        self.mpris = None
        self.minimize_to_tray: bool = bool(self.cfg.get("minimize_to_tray", False))
        self._hidden = False
        self._quitting = False
        self._cover_file: Path | None = None
        self._tray_title = None

    # ── конфіг ──
    def load_cfg(self) -> dict:
        d = {"folders": [], "playlist": [], "current": -1, "position": 0.0, "volume": 70}
        try:
            d.update(json.loads((CONF_DIR / "config.json").read_text("utf-8")))
        except Exception:
            pass
        return d

    def save_cfg(self):
        pos = self.player.time_pos if self.player and self.player.active else self.cfg.get("position", 0)
        self.cfg.update(folders=self.lib.folders, playlist=self.playlist, current=self.current,
                        position=round(pos or 0, 1), volume=self.player_volume, volume_mode=self.volume_mode, shuffle=self.shuffle,
                        repeat=self.repeat, remaining=self.remaining, theme=self.base, popups=self.popups,
                        lib_mode=self.lib_mode, show_library=self.show_library, cover_mode=self.cover_mode,
                        minimize_to_tray=self.minimize_to_tray)
        try:
            CONF_DIR.mkdir(parents=True, exist_ok=True)
            tmp = CONF_DIR / "config.tmp"
            tmp.write_text(json.dumps(self.cfg, ensure_ascii=False, indent=1), "utf-8")
            tmp.replace(CONF_DIR / "config.json")
        except OSError:
            pass

    # ── кольори ──
    @property
    def primary_hex(self) -> str:
        return self.current_theme.primary

    @property
    def dim_hex(self) -> str:
        t = self.current_theme
        return rgb_hex(mix(hex_rgb(t.background), hex_rgb(t.foreground), .28))

    def apply_theme(self):
        self._theme_flip = not self._theme_flip
        name = f"plativka-{'a' if self._theme_flip else 'b'}"
        self.register_theme(make_theme(name, self.base, self.cover_accent))
        self.theme = name
        self.render_cover()

    # ── життєвий цикл ──
    async def on_mount(self):
        self.apply_theme()
        cls = DemoPlayer if self.demo else MpvPlayer
        rotate_log()
        log(f"--- старт {APP_NAME} {VERSION}, demo={self.demo}")
        self.player = cls(self._mpv_eof, self._mpv_error, self._mpv_message, self._mpv_external_pause)
        if not self.demo and not MpvPlayer.find_exe():
            await self.push_screen(NoMpvScreen())
            return
        try:
            await self.player.start(self.player_volume)
        except Exception as e:
            self.notify(_("Не вдалося запустити mpv: {e}").format(e=e), severity="error", timeout=10, markup=False)
        self.setup_platform()
        if self.volume_mode == "system" and not self.demo:
            self._init_sysvol()
        self.main = MainScreen()
        await self.push_screen(self.main)

    # ── інтеграція з системою ──
    def setup_platform(self):
        loop = asyncio.get_running_loop()
        if not sysdeps.IS_WIN:
            # закрили вікно терміналу / вимикається система — зберегтися й вийти
            for sig in (signal.SIGHUP, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, lambda: asyncio.ensure_future(self.action_quit()))
                except (NotImplementedError, RuntimeError, ValueError):
                    pass
        else:
            from . import winplat
            winplat.on_close(self.save_cfg)  # mpv закриється сам: він у «завданні» плеєра
            if not self.demo and not os.environ.get("PLATIVKA_NO_TRAY"):
                try:
                    from .smtc import Smtc
                    sm = Smtc(self)
                    if sm.start():
                        self.smtc = sm
                        log("smtc: ok")
                except Exception as e:
                    log(f"smtc: {e}")
            try:
                if os.environ.get("PLATIVKA_NO_TRAY"):
                    raise RuntimeError("tray disabled by PLATIVKA_NO_TRAY")
                from .tray import Tray
                self.tray = Tray(self, self.tray_image())
                self.tray.start()
            except Exception as e:
                log(f"tray: {e}")
                self.tray = None
        if sysdeps.IS_LINUX and not self.demo:
            self.run_worker(self._start_mpris())

    async def _start_mpris(self):
        try:
            from .mpris import Mpris
        except Exception as e:
            log(f"mpris: {e}")
            return
        m = Mpris(self)
        if await m.start():
            self.mpris = m
            log("mpris: ok")

    def tray_image(self, cover: Image.Image | None = None) -> Image.Image:
        if cover is not None:
            return ImageOps.fit(cover, (64, 64), Image.LANCZOS)
        ic = sysdeps.icon_path()
        if ic:
            try:
                return Image.open(ic).convert("RGBA").resize((64, 64), Image.LANCZOS)
            except Exception:
                pass
        return vinyl_image((20, 140, 150), (255, 255, 255), False)

    def _platform_tick(self):
        cur = self.track(self.playlist[self.current]) if 0 <= self.current < len(self.playlist) else None
        if self.mpris is not None:
            try:
                self.mpris.refresh(cur, self._cover_file)
            except Exception as e:
                log(f"mpris refresh: {e}")
        if self.smtc is not None:
            self.smtc.refresh(cur, self._cover_file)
        if self.tray is not None:
            title = f"{APP_NAME} — {cur.display}" if cur else APP_NAME
            if title != self._tray_title:
                self._tray_title = title
                self.tray.set_title(title)
            if self.minimize_to_tray and not self._hidden:
                from . import winplat
                if winplat.is_minimized():
                    self.hide_to_tray()

    def hide_to_tray(self):
        if not sysdeps.IS_WIN or self.tray is None:
            return
        from . import winplat
        if not winplat.hide_window():
            self.notify(_("Сховати в трей можна лише у власному вікні плеєра (ярлик «Платівка»), "
                          "не у Windows Terminal."), timeout=6)
            return
        self._hidden = True
        if not self.cfg.get("tray_hint_shown"):
            self.cfg["tray_hint_shown"] = True
            self.tray.notify(APP_NAME, _("Платівка грає далі в треї. Вийти можна з меню її іконки."))
            self.save_cfg()

    def show_from_tray(self):
        if sysdeps.IS_WIN:
            from . import winplat
            winplat.show_window()
        self._hidden = False

    def toggle_from_tray(self):
        self.run_worker(self.toggle())

    def next_from_tray(self):
        self.run_worker(self.next())

    def prev_from_tray(self):
        self.run_worker(self.prev())

    def toggle_minimize_to_tray(self):
        self.minimize_to_tray = not self.minimize_to_tray
        self.save_cfg()

    def quit_from_tray(self):
        self.run_worker(self.action_quit())

    def toggle_language(self):
        new = "en" if (self.cfg.get("lang") or LANG) == "uk" else "uk"
        self.cfg["lang"] = new
        self.save_cfg()
        self.notify(_({"uk": "Мова інтерфейсу: українська. Зміниться після перезапуску плеєра.",
                       "en": "Мова інтерфейсу: англійська. Зміниться після перезапуску плеєра."}[new]),
                    timeout=5)

    def after_main_mount(self):
        self.update_layout()
        self.call_after_refresh(self.update_panel_titles)
        self.rebuild_playlist()
        self.rebuild_tree()
        self.update_flags()
        self.set_interval(0.25, self.ui_tick)
        self.set_interval(0.1, self.vu_tick)
        self.set_interval(5, self.save_cfg)
        if self.lib.folders:
            self.start_scan(quiet=True)
        if 0 <= self.current < len(self.playlist) and os.path.exists(self.playlist[self.current]):
            self.run_worker(self.play_index(self.current, start=float(self.cfg.get("position", 0)), paused=True))
        else:
            self.current = -1
            self.update_now_playing()

    async def action_quit(self):
        if self._quitting:
            return
        self._quitting = True
        self.save_cfg()
        if self.tray is not None:
            self.tray.stop()
        if self.mpris is not None:
            self.mpris.stop()
        if self.smtc is not None:
            self.smtc.stop()
        if self.player:
            await self.player.close()
        self.exit()

    def on_resize(self, event: events.Resize):
        self.update_layout()
        if self.main:
            self.rebuild_playlist(keep_cursor=True)
            self.update_now_playing()

    def update_layout(self):
        if not self.main:
            return
        narrow = self.size.width < 104
        s = self.main
        s.set_class(narrow, "narrow")
        s.set_class(not self.show_library, "lib-hidden")
        s.set_class(self.show_library, "lib-shown")
        s.set_class(self.cover_mode == "big" and self.size.height >= 30, "big-cover")

    # ── доступ до треків ──
    def track(self, path: str) -> Track:
        t = self.lib.tracks.get(path) or self.extra.get(path)
        if t is None:
            t = self.extra[path] = read_track(path)
        return t

    # ── відтворення ──
    async def play_index(self, i: int, start: float = 0.0, paused: bool = False):
        if not (0 <= i < len(self.playlist)):
            return
        # Кожен новий запит на відтворення скасовує попередні, ще не виконані
        # (напр. відновлення сесії на паузі не перебʼє трек, який ви вже ввімкнули).
        self._load_gen += 1
        gen = self._load_gen
        async with self._load_lock:
            if gen != self._load_gen:
                return
            await self._play_index(i, start, paused)

    async def _play_index(self, i: int, start: float = 0.0, paused: bool = False):
        if not (0 <= i < len(self.playlist)):
            return
        if self.current != i and self.current >= 0:
            self.history.append(self.current)
            self.history = self.history[-200:]
        self.current = i
        self.stopped = False
        path = self.playlist[i]
        await self.player.load(path, start=start, paused=paused)
        if not paused:
            self.announce(path)
        self.update_now_playing()
        self.mark_current()
        self.load_cover_bg(path)
        self.save_cfg()

    async def play(self):
        if not self.playlist:
            self.notify(_("Список порожній — оберіть музику в медіатеці"))
            return
        if self.player.active and self.player.paused:
            await self.player.set_pause(False)
        elif self.player.active:
            await self.player.seek(0)
        else:
            i = self.current if self.current >= 0 else max(0, self.cursor_row())
            await self.play_index(i)

    async def pause(self):
        if self.player.active:
            await self.player.set_pause(not self.player.paused)

    async def toggle(self):
        if self.player.active:
            await self.player.set_pause(not self.player.paused)
        else:
            await self.play()

    async def stop(self):
        await self.player.stop()
        self.stopped = True

    def next_index(self, auto: bool) -> int | None:
        n = len(self.playlist)
        if not n:
            return None
        if auto and self.repeat == "one":
            return self.current
        if self.shuffle and n > 1:
            recent = set(self.history[-max(1, n // 2):] + [self.current])
            pool = [i for i in range(n) if i not in recent] or [i for i in range(n) if i != self.current]
            return random.choice(pool)
        j = self.current + 1
        if j >= n:
            return 0 if (self.repeat == "all" or not auto) else None
        return j

    async def next(self, auto: bool = False):
        j = self.next_index(auto)
        if j is None:
            self.stopped = True
            await self.player.stop()
            if auto and self.playlist:
                self.notify(_("Список відтворення закінчився. Повтор усього: клавіша R"), timeout=5)
            return
        await self.play_index(j)

    async def prev(self):
        if self.player.active and self.player.time_pos > 3:
            await self.player.seek(0)
            return
        if self.shuffle and self.history:
            j = self.history.pop()
            if 0 <= j < len(self.playlist):
                self.current = -1
                await self.play_index(j)
                return
        if self.playlist:
            await self.play_index((self.current - 1) % len(self.playlist))

    async def seek_rel(self, d: float):
        if self.player.active:
            await self.player.seek(self.player.time_pos + d)

    async def seek_frac(self, f: float):
        if self.player.active and self.player.duration:
            await self.player.seek(f * self.player.duration)

    async def set_volume(self, v: int):
        self.volume = int(clamp(v, 0, 100))
        if self.sysvol is not None:
            self.sys_muted = False
            self._sysvol_set(self.volume)
        else:
            self.player_volume = self.volume
            await self.player.set_volume(self.volume)
        self._refresh_volume()

    def _refresh_volume(self):
        if self.main:
            try:
                self.main.query_one(VolumeBar).refresh()
            except NoMatches:
                pass

    # Гучність системи: плеєр завжди на 100 %, смужка показує й змінює гучність системи
    @work(thread=True, exclusive=True, group="sysvol")
    def _init_sysvol(self):
        sysvol.init_thread()
        sv = sysvol.detect()
        if sv is None:
            log("sysvol: недоступна, лишається гучність плеєра")
            return
        log(f"sysvol: {sv.name}")
        self.call_from_thread(self._sysvol_ready, sv)
        import threading
        while not self._quitting and self.sysvol is sv:
            try:
                r = sv.get()
            except Exception:
                r = None
            if r is not None:
                self.call_from_thread(self._sysvol_changed, *r)
            for _i in range(7):
                if self._quitting or self.sysvol is not sv:
                    break
                time.sleep(0.1)

    def _sysvol_ready(self, sv):
        self.sysvol = sv
        self.run_worker(self.player.set_volume(100))

    def _sysvol_changed(self, v: int, muted: bool):
        if self.sysvol is None:
            return
        if (v, muted) != (self.volume, self.sys_muted) and time.monotonic() - getattr(self, "_sysvol_t", 0) > 0.8:
            self.volume, self.sys_muted = v, muted
            self._refresh_volume()

    @work(thread=True, group="sysvol-set")
    def _sysvol_set(self, v: int):
        self._sysvol_t = time.monotonic()
        sysvol.init_thread()
        if self.sysvol is not None:
            self.sysvol.set(v)

    def toggle_volume_mode(self):
        if self.volume_mode == "system":
            self.volume_mode = "player"
            self.sysvol = None
            self.sys_muted = False
            self.volume = self.player_volume
            self.run_worker(self.player.set_volume(self.player_volume))
        else:
            self.volume_mode = "system"
            if not self.demo:
                self._init_sysvol()
        self._refresh_volume()
        self.save_cfg()

    def open_url(self, url: str):
        import webbrowser
        import threading
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
        self.notify(_("Відкриваю в браузері: {url}").format(url=url), timeout=3, markup=False)

    def open_github(self):
        self.open_url(GITHUB_URL)

    def update_panel_titles(self):
        if not self.main:
            return
        for win, title in (("#pl-win", _("Список відтворення")), ("#library-win", _("Медіатека"))):
            try:
                w = self.main.query_one(win)
            except NoMatches:
                continue
            w.border_title = ("● " + title) if w.has_pseudo_class("focus-within") else title

    def _mpv_eof(self, early=None):
        if early:
            pos, dur = early
            self.notify(_("Трек обірвався на {pos} з {dur}: файл, схоже, обрізаний або пошкоджений. "
                          "Вмикаю наступний.").format(pos=fmt_time(pos), dur=fmt_time(dur)),
                        severity="warning", timeout=6)
        log(f"eof → наступний (early={early})")
        self.run_worker(self.next(auto=True))

    def _mpv_external_pause(self, paused: bool):
        if paused:
            self.notify(_("Пауза ззовні: навушники, медіаклавіша або інша програма"), timeout=4)

    def _mpv_error(self, err):
        name = Path(self.playlist[self.current]).name if 0 <= self.current < len(self.playlist) else ""
        self.notify(_("Не вдалося відтворити {name}").format(name=name), severity="warning", markup=False)
        self.run_worker(self.next(auto=True))

    def _mpv_message(self, args):
        if not args:
            return
        log(f"медіаклавіша: {args}")
        if args[0] == "plativka-next":
            self.run_worker(self.next())
        elif args[0] == "plativka-prev":
            self.run_worker(self.prev())
        elif args[0] == "plativka-stop":
            self.run_worker(self.stop())

    def announce(self, path: str):
        if self.popups == "off":
            return
        t = self.track(path)
        title = t.title
        sub = " · ".join(x for x in (t.album, t.year) if x)
        if self.popups == "system" and sysdeps.can_system_notify():
            self._sys_notify(path, t.artist or APP_NAME, title, sub)
        else:
            self.notify(title + (f"\n{sub}" if sub else ""), title=t.artist or _("Зараз грає"),
                        timeout=4, markup=False)

    @work(thread=True, group="osnotify")
    def _sys_notify(self, path: str, head: str, body: str, sub: str):
        """Системне сповіщення про трек — з обкладинкою, де система це вміє."""
        img = self.cover_img if self._last_cover_path == path else None
        if img is None:
            try:
                img = load_cover(path)
            except Exception:
                img = None
        jpeg, cover = None, None
        if img is not None:
            try:
                import io
                small = img.convert("RGB")
                small.thumbnail((256, 256))
                buf = io.BytesIO()
                small.save(buf, "JPEG", quality=85)
                jpeg = buf.getvalue()
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cover = CACHE_DIR / "notify-cover.jpg"
                cover.write_bytes(jpeg)
            except Exception:
                jpeg, cover = None, None
        if sysdeps.IS_WIN:
            from . import winnotify
            if not winnotify.show(head, body + (f"\n{sub}" if sub else ""), str(cover) if cover else None):
                if self.tray is not None:
                    self.tray.notify(head, body + (f"\n{sub}" if sub else ""))
        elif sysdeps.IS_MAC and sysdeps.in_kitty():
            self._notify_n = getattr(self, "_notify_n", 0) + 1
            seq = sysdeps.kitty_notification(head, body + (f"\n{sub}" if sub else ""), jpeg,
                                             ident=f"plativka-{self._notify_n}")
            self.call_from_thread(self._write_terminal, seq)
        else:
            sysdeps.system_notify(head, body, sub, image=str(cover) if cover else None)

    def _write_terminal(self, seq: str):
        try:
            self._driver.write(seq)
            self._driver.flush()
        except Exception:
            pass

    def cycle_popups(self):
        order = ["app", "system", "off"] if sysdeps.can_system_notify() else ["app", "off"]
        i = order.index(self.popups) if self.popups in order else -1
        self.popups = order[(i + 1) % len(order)]
        self.update_flags()
        self.notify({"app": _("Сповіщення про трек: у плеєрі"),
                     "system": _("Сповіщення про трек: лише системні ({os})").format(os=sysdeps.OS_NAME),
                     "off": _("Сповіщення про трек вимкнено")}[self.popups], timeout=2)

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self.update_flags()

    def cycle_repeat(self):
        self.repeat = {"off": "all", "all": "one", "one": "off"}[self.repeat]
        self.update_flags()

    def toggle_remaining(self):
        self.remaining = not self.remaining

    def toggle_theme(self):
        self.base = "dark" if self.base == "light" else "light"
        self.apply_theme()
        self.save_cfg()

    def cycle_cover_mode(self):
        """O: обкладинка → велика обкладинка → платівка замість обкладинки."""
        self.cover_mode = {"normal": "big", "big": "off", "off": "normal"}.get(self.cover_mode, "normal")
        self.update_layout()
        self.render_cover()
        self.save_cfg()
        msg = {"normal": _("Обкладинка: звичайна"), "big": _("Обкладинка: велика"),
               "off": _("Обкладинки вимкнено, замість них платівка")}[self.cover_mode]
        if self.cover_mode == "big" and self.size.height < 30:
            msg += _(" (потрібне вікно від 30 рядків)")
        self.notify(msg, timeout=2)

    def toggle_library(self):
        self.show_library = not self.show_library
        self.update_layout()
        if self.main:
            target = "#library" if self.show_library else "#playlist"
            self.main.query_one(target).focus()

    # ── періодичне оновлення ──
    def ui_tick(self):
        if not self.main or not self.main.is_current or not self.main.is_mounted:
            return
        try:
            self._ui_tick()
        except NoMatches:
            pass
        self._platform_tick()

    def _ui_tick(self):
        p, s = self.player, self.main
        state = "■" if (self.stopped or not p.active) else ("‖" if p.paused else "▶")
        s.query_one("#state-icon", Static).update(state)
        dur = p.duration or (self.track(self.playlist[self.current]).length if 0 <= self.current < len(self.playlist) else 0)
        if p.active:
            sec = max(0.0, dur - p.time_pos) if self.remaining and dur else p.time_pos
            blink = p.paused and int(time.monotonic() * 2) % 2 == 0
        else:
            sec, blink = None, False
        s.query_one(BigTime).show(sec, self.remaining, blink)
        s.query_one(SeekBar).set((p.time_pos / dur) if (dur and p.active) else 0.0, dur)
        if p.active and not p.paused:
            s.query_one(Marquee).step()
            if self.cover_mode == "off":
                self._spin = (self._spin + 24) % 360
                self.render_cover()
        # mpv знає точну тривалість — підставляємо, якщо теги її не дали (0:00 у списку)
        if p.active and p.duration and 0 <= self.current < len(self.playlist):
            t = self.track(self.playlist[self.current])
            if not t.length:
                t.length = p.duration
                self.rebuild_playlist(keep_cursor=True)

    async def vu_tick(self):
        if not self.player or not self.main or not self.main.is_current:
            return
        await self.player.poll_levels()
        try:
            vu = self.main.query_one(VUMeter)
        except NoMatches:
            return
        vu.show(self.player.levels, self.player.peaks, self.player.vu_ok)

    def update_now_playing(self):
        if not self.main:
            return
        s = self.main
        if 0 <= self.current < len(self.playlist):
            t = self.track(self.playlist[self.current])
            s.query_one(Marquee).set_text(f"{self.current + 1}. {t.display} ({fmt_time(t.length)})")
            parts = [t.fmt]
            if t.bitrate:
                parts.append(_("{kbps} кбіт/с").format(kbps=t.bitrate // 1000))
            if t.samplerate:
                parts.append(_("{khz} кГц").format(khz=f"{t.samplerate / 1000:g}"))
            if t.channels:
                parts.append(_("стерео") if t.channels >= 2 else _("моно"))
            album = " · ".join(x for x in (t.album, t.year) if x)
            s.query_one("#info", Static).update(Text("  ".join(parts) + (f"   {album}" if album else "")))
        else:
            s.query_one(Marquee).set_text(_("{app} {ver} — оберіть, що послухати").format(app=APP_NAME, ver=VERSION))
            s.query_one("#info", Static).update("")
        s.query_one("#main-win").border_subtitle = _("демо, без звуку") if self.demo else ""

    def update_flags(self):
        if not self.main:
            return
        s = self.main
        sh = s.query_one("#f-shuffle", Static)
        sh.set_class(self.shuffle, "on")
        rp = s.query_one("#f-repeat", Static)
        rp.update({"off": _("повтор: вимк"), "all": _("повтор: все"), "one": _("повтор: один")}[self.repeat])
        rp.set_class(self.repeat != "off", "on")
        pp = s.query_one("#f-popups", Static)
        pp.update({"off": _("сповіщ: вимк"), "app": _("сповіщ: плеєр"), "system": _("сповіщ: {os}").format(os=sysdeps.OS_NAME)}[self.popups])
        pp.set_class(self.popups != "off", "on")
        s.query_one("#tab-artists").set_class(self.lib_mode == "artists", "on")
        s.query_one("#tab-folders").set_class(self.lib_mode == "folders", "on")
        self.save_cfg()

    # ── обкладинка ──
    @work(thread=True, exclusive=True, group="cover")
    def load_cover_bg(self, path: str):
        img = None
        try:
            img = load_cover(path)
        except Exception:
            img = None
        self.call_from_thread(self._set_cover, path, img)

    def _set_cover(self, path, img):
        self._last_cover_path = path
        self.cover_img = img
        if self.mpris is not None or self.smtc is not None:
            self._cover_file = self._write_cover_file(path, img)
        if self.tray is not None:
            self.tray.set_image(self.tray_image(img))
        acc = accent_from(img) if img is not None else None
        if acc != self.cover_accent:
            self.cover_accent = acc
            self.apply_theme()
        else:
            self.render_cover()

    def _write_cover_file(self, path: str, img) -> Path | None:
        """Обкладинка у файл — для віджета плеєра робочого столу (MPRIS)."""
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            for old in CACHE_DIR.glob("cover-*.jpg"):
                old.unlink(missing_ok=True)
            if img is None:
                return None
            f = CACHE_DIR / f"cover-{abs(hash(path)) % 10 ** 8}.jpg"
            img.convert("RGB").save(f, "JPEG", quality=88)
            return f
        except Exception:
            return None

    def render_cover(self):
        if not self.main:
            return
        w = self.main.query_one("#cover", Static)
        t = self.current_theme
        img_w = self.main.query("#cover-img").first() if GRAPHICS is not None else None
        if img_w is not None:
            # термінал уміє справжні картинки: обкладинка або чітка платівка у високій роздільності
            use = self.cover_mode != "off"
            img_w.display = use
            w.display = not use
            if use:
                if self.cover_img is not None:
                    key = ("cover", id(self.cover_img))
                    pic = self.cover_img
                else:
                    key = ("vinyl", t.name, t.primary)
                    pic = None
                if getattr(self, "_img_key", None) != key:
                    self._img_key = key
                    if pic is None:
                        bg = mix(hex_rgb(t.background), hex_rgb(t.primary), .05)
                        pic = vinyl_image(hex_rgb(t.primary), bg, t.dark, size=384)
                    else:
                        pic = ImageOps.fit(pic, (512, 512), Image.LANCZOS)
                    img_w.image = pic
                return
        if self.cover_mode == "off":
            groove = rgb_hex(mix(hex_rgb(t.background), hex_rgb(t.foreground), .45))
            shine = rgb_hex(mix(hex_rgb(t.background), hex_rgb(t.foreground), .85))
            w.update(braille_vinyl(16, 8, self._spin, groove, t.primary, shine))
            return
        if self.cover_img is not None:
            img = self.cover_img
        else:
            bg = mix(hex_rgb(t.background), hex_rgb(t.primary), .05)
            img = vinyl_image(hex_rgb(t.primary), bg, t.dark)
        w.update(halfblocks(img, *((24, 12) if self.main.has_class("big-cover") else (16, 8))))

    # ── список відтворення ──
    def cursor_row(self) -> int:
        if not self.main:
            return -1
        return self.main.query_one(PlaylistTable).cursor_row

    def rebuild_playlist(self, keep_cursor: bool = True):
        if not self.main:
            return
        tbl = self.main.query_one(PlaylistTable)
        cur = tbl.cursor_row if keep_cursor else 0
        tbl.clear(columns=True)
        width = max(20, tbl.size.width or 60)
        tbl.add_column("", width=1, key="m")
        tbl.add_column("#", width=4, key="n")
        tbl.add_column(_("Трек"), width=max(10, width - 24), key="t")
        tbl.add_column(_("Час"), width=6, key="d")
        total = 0.0
        for i, path in enumerate(self.playlist):
            t = self.track(path)
            total += t.length
            tbl.add_row(*self._row_cells(i, t), key=str(i))
        empty = not self.playlist
        tbl.display = not empty
        self.main.query_one("#pl-empty").display = empty
        n = len(self.playlist)
        self.main.query_one("#pl-win").border_subtitle = \
            f"{n_tracks(n)} · {fmt_time(total)}" if n else ""
        if n:
            tbl.move_cursor(row=clamp(cur, 0, n - 1), animate=False)

    def _row_cells(self, i: int, t: Track):
        playing = i == self.current
        st = Style(bold=True, color=self.primary_hex) if playing else Style()
        mark = Text("▶" if playing else "", style=st)
        return (mark, Text(f"{i + 1}.", style=Style(color=self.dim_hex) if not playing else st),
                Text(t.display, style=st, overflow="ellipsis", no_wrap=True),
                Text(fmt_time(t.length).rjust(6), style=st if playing else Style(color=self.dim_hex)))

    def mark_current(self):
        self.rebuild_playlist(keep_cursor=True)
        if self.main and 0 <= self.current < len(self.playlist):
            tbl = self.main.query_one(PlaylistTable)
            if self.focused is not tbl:
                tbl.move_cursor(row=self.current, animate=False)

    def add_to_playlist(self, paths: list[str], play: bool = False, replace: bool = False, quiet: bool = False):
        if not paths:
            return
        if replace:
            self.playlist = list(paths)
            self.current = -1
            self.history.clear()
            start = 0
        else:
            start = len(self.playlist)
            self.playlist.extend(paths)
        self.rebuild_playlist()
        self.save_cfg()
        if play:
            self.run_worker(self.play_index(start))
        elif not quiet:
            self.notify(_("Додано {n}").format(n=n_tracks(len(paths))))

    def action_remove_selected(self):
        if not self.main or not self.playlist:
            return
        i = self.cursor_row()
        if not (0 <= i < len(self.playlist)):
            return
        del self.playlist[i]
        if i < self.current:
            self.current -= 1
        elif i == self.current:
            self.current = -1
            self.run_worker(self.stop())
        self.history = [h if h < i else h - 1 for h in self.history if h != i]
        self.rebuild_playlist()
        self.save_cfg()

    def clear_playlist(self):
        self.playlist.clear()
        self.current = -1
        self.history.clear()
        self.run_worker(self.stop())
        self.rebuild_playlist()
        self.update_now_playing()
        self.save_cfg()

    # ── медіатека ──
    def set_lib_mode(self, mode: str):
        self.lib_mode = mode
        self.rebuild_tree()
        self.update_flags()

    def rebuild_tree(self):
        if not self.main:
            return
        tree = self.main.query_one(LibraryTree)
        tree.clear()
        has = bool(self.lib.tracks)
        tree.display = has
        self.main.query_one("#lib-empty").display = not has and not self.scanning
        n = len(self.lib.tracks)
        self.main.query_one("#library-win").border_subtitle = \
            n_tracks(n) if n else ""
        if not has:
            return
        dim = Style(color=self.dim_hex)
        if self.lib_mode == "artists":
            artists: dict[str, dict[str, list[Track]]] = {}
            for t in self.lib.tracks.values():
                a = t.albumartist or t.artist or _("Без тегів")
                alb = t.album or Path(t.path).parent.name
                artists.setdefault(a, {}).setdefault(alb, []).append(t)
            for a in sorted(artists, key=lambda s: (s == _("Без тегів"), s.lower())):
                albums = artists[a]
                cnt = sum(len(v) for v in albums.values())
                an = tree.root.add(Text(a).append(f"  {cnt}", dim), data=("group", None), expand=False)
                paths_a = []
                for alb in sorted(albums, key=lambda k: (min((x.year for x in albums[k]), default="") or "9999", k.lower())):
                    tracks = sorted(albums[alb], key=lambda t: t.sort_key)
                    year = next((x.year for x in tracks if x.year), "")
                    lbl = Text(alb).append(f"  {year}" if year else "", dim)
                    al = an.add(lbl, data=("group", [t.path for t in tracks]), expand=False)
                    for t in tracks:
                        num = f"{t.track:>2}  " if t.track else "    "
                        al.add_leaf(Text(num, dim).append(t.title).append(f"  {fmt_time(t.length)}", dim),
                                    data=("track", t.path))
                    paths_a.extend(t.path for t in tracks)
                an.data = ("group", paths_a)
        else:
            for root in self.lib.folders:
                tracks = self.lib.under(root)
                rn = tree.root.add(Text(Path(root).name or root).append(f"  {len(tracks)}", dim),
                                   data=("group", [t.path for t in tracks]), expand=len(self.lib.folders) == 1)
                nodes = {root.rstrip(os.sep): rn}
                for t in tracks:
                    d = os.path.dirname(t.path)
                    if d not in nodes:
                        rel = Path(d).relative_to(root).parts
                        cur = root.rstrip(os.sep)
                        for part in rel:
                            nxt = os.path.join(cur, part)
                            if nxt not in nodes:
                                nodes[nxt] = nodes[cur].add(Text(part), data=("group", []), expand=False)
                            cur = nxt
                    nodes[d].add_leaf(Text(Path(t.path).stem), data=("track", t.path))
                # шляхи для груп-тек (усе, що всередині)
                for d, node in nodes.items():
                    if node is not rn:
                        pre = d + os.sep
                        node.data = ("group", [t.path for t in tracks if t.path.startswith(pre)])

    def node_paths(self, node) -> list[str]:
        data = node.data
        if not data:
            return []
        if data[0] == "track":
            return [data[1]]
        return list(data[1] or [])

    async def play_from_library(self, node):
        """Enter на треку: у список іде весь альбом/тека, грає обраний трек."""
        parent = node.parent
        paths = self.node_paths(parent) if parent is not None and parent.data else [node.data[1]]
        if node.data[1] not in paths:
            paths = [node.data[1]]
        self.add_to_playlist(paths, replace=True)
        await self.play_index(paths.index(node.data[1]))

    def action_lib_play(self):
        node = self.main.query_one(LibraryTree).cursor_node if self.main else None
        if node is None:
            return
        paths = self.node_paths(node)
        if node.data and node.data[0] == "track":
            self.run_worker(self.play_from_library(node))
        else:
            self.add_to_playlist(paths, play=True, replace=True)

    def action_lib_all(self):
        """Уся медіатека в список відтворення — у тому ж порядку, що й у дереві."""
        if not self.lib.tracks or not self.main:
            self.notify(_("Медіатека порожня — додайте теку клавішею L"))
            return
        tree = self.main.query_one(LibraryTree)
        paths, seen = [], set()
        for node in tree.root.children:
            for p in self.node_paths(node):
                if p not in seen:
                    seen.add(p)
                    paths.append(p)
        start = random.randrange(len(paths)) if self.shuffle else 0
        self.add_to_playlist(paths, replace=True, quiet=True)
        self.run_worker(self.play_index(start))
        self.notify(_("У списку вся медіатека: {n}").format(n=n_tracks(len(paths))))

    def action_lib_append(self):
        node = self.main.query_one(LibraryTree).cursor_node if self.main else None
        if node is not None:
            self.add_to_playlist(self.node_paths(node))

    def add_library_folder(self, after=None):
        def done(paths):
            self.add_folders_to_library(paths)
            if after:
                after()
        self._pick_folders(_("Оберіть теки з музикою для медіатеки"), done)

    def _pick_folders(self, title: str, done):
        """Системне вікно вибору теки; якщо його немає — вибір у самому плеєрі."""
        if pickers.available():
            self._native_pick(title, done)
        else:
            self.push_screen(FolderPicker(title), lambda p: p and done([p]))

    @work(thread=True, exclusive=True, group="picker")
    def _native_pick(self, title: str, done):
        res = pickers.choose_folders(title)

        def finish():
            if res is None:
                self.push_screen(FolderPicker(title), lambda p: p and done([p]))
            elif res:
                done(res)
        self.call_from_thread(finish)

    def add_folders_to_library(self, paths: list[str]):
        added = []
        for p in paths:
            p = str(Path(p).resolve())
            if any(p == f or p.startswith(f.rstrip(os.sep) + os.sep) for f in self.lib.folders):
                self.notify(_("«{name}» уже в медіатеці").format(name=Path(p).name), markup=False)
                continue
            # нова тека може містити вже додані — тоді вони поглинаються
            self.lib.folders = [f for f in self.lib.folders if not f.startswith(p.rstrip(os.sep) + os.sep)]
            self.lib.folders.append(p)
            added.append(p)
        if added:
            self.save_cfg()
            self.start_scan()

    def remove_library_folder(self):
        """Вікно «Теки медіатеки»: додати, прибрати позначені, прибрати всі."""
        self.push_screen(FoldersScreen())

    def remove_folders(self, paths: list[str]):
        removed = 0
        for path in paths:
            if path in self.lib.folders:
                self.lib.folders.remove(path)
                pre = path.rstrip(os.sep) + os.sep
                self.lib.tracks = {k: v for k, v in self.lib.tracks.items() if not k.startswith(pre)}
                removed += 1
        if removed:
            self.lib.save()
            self.save_cfg()
            self.rebuild_tree()
            self.notify(_("Прибрано тек: {n} (файли не видалено)").format(n=removed))

    def clear_library(self):
        n = len(self.lib.folders)
        self.lib.folders = []
        self.lib.tracks = {}
        self.lib.save()
        self.save_cfg()
        self.rebuild_tree()
        self.notify(_("Медіатеку очищено: прибрано тек — {n} (файли не видалено)").format(n=n))

    def start_scan(self, quiet: bool = False):
        if self.scanning:
            return
        self.scanning = True
        self._scan(quiet)

    @work(thread=True, exclusive=True, group="scan")
    def _scan(self, quiet: bool):
        def progress(i, total):
            self.call_from_thread(self._scan_progress, i, total)
        try:
            total = self.lib.scan(progress)
        except Exception as e:
            total = -1
            self.call_from_thread(self.notify, _("Помилка сканування: {e}").format(e=e), severity="error", markup=False)
        self.call_from_thread(self._scan_done, total, quiet)

    def _scan_progress(self, i, total):
        if self.main:
            self.main.query_one("#library-win").border_subtitle = _("сканую {i} з {total}…").format(i=i, total=total)

    def _scan_done(self, total, quiet):
        self.scanning = False
        self.rebuild_tree()
        self.rebuild_playlist()
        self.update_now_playing()
        if not quiet and total >= 0:
            self.notify(_("Медіатека оновлена: {n}").format(n=n_tracks(total)))

    def add_playlist_folder(self):
        def done(paths):
            for p in paths:
                self._collect_folder(p)
        self._pick_folders(_("Оберіть теку для списку відтворення"), done)

    @work(thread=True, group="collect")
    def _collect_folder(self, path: str):
        paths = list(scan_dir(path))
        for p in paths:
            if p not in self.lib.tracks and p not in self.extra:
                self.extra[p] = read_track(p)
        self.call_from_thread(self.add_to_playlist, paths)

    def handle_paste(self, text: str):
        """Перетягування теки/файлів із файлового менеджера у вікно вставляє їхні шляхи."""
        try:
            if sysdeps.IS_WIN:  # у Windows шляхи з «\», лапки лише навколо шляхів із пробілами
                parts = [x.strip('"') for x in shlex.split(text.strip(), posix=False)]
            else:
                parts = shlex.split(text.strip())
        except ValueError:
            parts = text.split()
        dirs, files = [], []
        for p in parts:
            if p.startswith("file://"):
                p = unquote(urlparse(p).path)
            p = os.path.expanduser(p)
            if os.path.isdir(p):
                dirs.append(p)
            elif os.path.isfile(p) and Path(p).suffix.lower() in AUDIO_EXT:
                files.append(p)
        if dirs:
            self.add_folders_to_library(dirs)
        if files:
            self.add_to_playlist(files)
        if not dirs and not files:
            self.notify(_("Перетягніть теку з музикою або аудіофайли"))

    # ── пошук ──
    def search_pool(self):
        seen, pool = set(), []
        for path in self.playlist + list(self.lib.tracks):
            if path in seen:
                continue
            seen.add(path)
            t = self.track(path)
            hay = f"{t.artist} {t.title} {t.album} {t.albumartist} {Path(path).stem}".lower()
            pool.append((path, hay, f"{t.display}" + (f"   ·  {t.album}" if t.album else "")))
        return pool

    def jump(self):
        async def done(path):
            if not path:
                return
            if path in self.playlist:
                await self.play_index(self.playlist.index(path))
            else:
                self.playlist.append(path)
                self.rebuild_playlist()
                await self.play_index(len(self.playlist) - 1)
        self.push_screen(JumpScreen(), done)


def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__)
        return
    setup_graphics(sys.argv)
    Plativka(demo="--demo" in sys.argv).run()
