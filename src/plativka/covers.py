"""Обкладинки з інтернету — лише якщо їх немає у файлі чи теці і лише якщо людина ввімкнула.

Звідки: MusicBrainz + Cover Art Archive (відкрита база), запасний — iTunes Search.
Що надсилається: лише виконавець і назва альбому (або пісні). Береться тільки впевнений збіг:
нормалізовані назви мають збігтися (з урахуванням кирилиці й латиниці: «Океан Ельзи» = «Okean Elzy»).
Знайдене кладеться в кеш і далі працює без мережі. Сумнівне не підставляємо — для цього є
ручний вибір «Знайти обкладинку…»."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import threading
import time
import unicodedata
import urllib.parse
import urllib.request

from .core import CACHE_DIR, VERSION, GITHUB_URL, Track, log, real_path

COVERS_DIR = CACHE_DIR / "covers"
MAX_BYTES = 6 * 1024 * 1024
MAX_SIDE = 1000
RETRY_MISS_DAYS = 30
UA = f"Plativka/{VERSION} ( {GITHUB_URL} )"

_mb_lock = threading.Lock()
_mb_last = 0.0

# ── нормалізація й транслітерація ──
_UK = {"а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie", "ж": "zh", "з": "z",
       "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
       "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
       "щ": "shch", "ь": "", "ю": "iu", "я": "ia", "ы": "y", "э": "e", "ё": "e", "ъ": "", "'": "", "’": ""}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").casefold().replace("&", " and ")
    s = re.sub(r"[\(\[].*?[\)\]]", " ", s)          # (Deluxe Edition), [Remastered]
    s = re.sub(r"\b(the|feat|ft)\b\.?", " ", s)
    return " ".join(re.findall(r"\w+", s))


def skeleton(s: str) -> str:
    """Латинський «кістяк»: щоб Ельзи/Elzy/Elzi, Скрябін/Skryabin, Кузьма/Kuzma збігались."""
    t = "".join(_UK.get(ch, ch) for ch in norm(s))
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = t.replace("kh", "h").replace("ck", "k").replace("w", "v").replace("y", "i").replace("j", "i")
    t = t.replace("ks", "x").replace("oo", "u")
    return re.sub(r"(.)\1+", r"\1", t.replace(" ", ""))


def same(a: str, b: str) -> bool:
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    return na == nb or (len(na) > 2 and skeleton(a) == skeleton(b) and skeleton(a) != "")


# ── кеш ──
def cache_key(t: Track) -> str | None:
    artist = norm(t.albumartist or t.artist)
    what = norm(t.album) or ("~" + norm(t.title) if t.title else "")
    if not artist or not what:
        return None
    return hashlib.sha1(f"{artist}|{what}".encode()).hexdigest()[:20]


def cached(t: Track) -> bytes | None:
    k = cache_key(t)
    if not k:
        return None
    f = COVERS_DIR / f"{k}.jpg"
    try:
        return f.read_bytes() if f.is_file() else None
    except OSError:
        return None


def _missed_recently(k: str) -> bool:
    f = COVERS_DIR / f"{k}.none"
    try:
        return time.time() - f.stat().st_mtime < RETRY_MISS_DAYS * 86400
    except OSError:
        return False


def store(t: Track, data: bytes, folder_copy: bool = False) -> bytes | None:
    """Зберегти в кеш (і, якщо попросили, як cover.jpg поруч із музикою). Повертає JPEG."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(data))
        im = im.convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=90)
        jpg = buf.getvalue()
    except Exception as e:
        log(f"обкладинка: не картинка ({e})")
        return None
    k = cache_key(t)
    if k:
        try:
            COVERS_DIR.mkdir(parents=True, exist_ok=True)
            (COVERS_DIR / f"{k}.jpg").write_bytes(jpg)
            (COVERS_DIR / f"{k}.none").unlink(missing_ok=True)
        except OSError as e:
            log(f"обкладинка: кеш ({e})")
    if folder_copy:
        dest = os.path.join(os.path.dirname(real_path(t.path)), "cover.jpg")
        if not os.path.exists(dest):
            try:
                with open(dest, "wb") as f:
                    f.write(jpg)
            except OSError as e:
                log(f"обкладинка: cover.jpg ({e})")
    return jpg


# ── мережа ──
def _ctx():
    from .core import https_context
    return https_context()


def _get(url: str, accept: str = "application/json", limit: int = 2 * 1024 * 1024) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=10, context=_ctx()) as r:
        data = r.read(limit + 1)
    if len(data) > limit:
        raise ValueError("завеликий файл")
    return data


def _mb(path: str, query: dict) -> dict:
    global _mb_last
    with _mb_lock:                      # MusicBrainz просить не частіше за раз на секунду
        wait = 1.1 - (time.monotonic() - _mb_last)
        if wait > 0:
            time.sleep(wait)
        _mb_last = time.monotonic()
        url = f"https://musicbrainz.org/ws/2/{path}/?" + urllib.parse.urlencode({**query, "fmt": "json"})
        return json.loads(_get(url))


def _lucene(s: str) -> str:
    return '"' + re.sub(r'([+\-&|!(){}\[\]^"~*?:\\/])', r"\\\1", s) + '"'


def _mb_candidates(artist: str, album: str, title: str, strict: bool) -> list[dict]:
    out = []
    if album:
        j = _mb("release-group", {"query": f"artist:{_lucene(artist)} AND releasegroup:{_lucene(album)}", "limit": 10})
        for g in j.get("release-groups", []):
            a = " ".join(c.get("name", "") + c.get("joinphrase", "") for c in g.get("artist-credit", []))
            if strict and not (same(a, artist) and same(g.get("title", ""), album) and int(g.get("score", 0)) >= 85):
                continue
            out.append({"src": "MusicBrainz", "label": f"{a} — {g.get('title', '')}",
                        "url": f"https://coverartarchive.org/release-group/{g['id']}/front-500",
                        "thumb": f"https://coverartarchive.org/release-group/{g['id']}/front-250"})
    elif title:
        j = _mb("recording", {"query": f"artist:{_lucene(artist)} AND recording:{_lucene(title)}", "limit": 10})
        for r in j.get("recordings", []):
            a = " ".join(c.get("name", "") + c.get("joinphrase", "") for c in r.get("artist-credit", []))
            if strict and not (same(a, artist) and same(r.get("title", ""), title) and int(r.get("score", 0)) >= 85):
                continue
            for rel in r.get("releases", [])[:2]:
                rg = (rel.get("release-group") or {}).get("id")
                if rg:
                    out.append({"src": "MusicBrainz", "label": f"{a} — {rel.get('title', '')}",
                                "url": f"https://coverartarchive.org/release-group/{rg}/front-500",
                                "thumb": f"https://coverartarchive.org/release-group/{rg}/front-250"})
    return out


def _itunes_candidates(artist: str, album: str, title: str, strict: bool) -> list[dict]:
    entity = "album" if album else "song"
    term = f"{artist} {album or title}"
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode({"term": term, "entity": entity, "limit": 15})
    j = json.loads(_get(url))
    out = []
    for r in j.get("results", []):
        a, name = r.get("artistName", ""), r.get("collectionName" if album else "trackName", "")
        art = r.get("artworkUrl100")
        if not art:
            continue
        if strict and not (same(a, artist) and same(name, album or title)):
            continue
        out.append({"src": "Apple", "label": f"{a} — {r.get('collectionName', '')}",
                    "url": art.replace("100x100bb", "1000x1000bb"), "thumb": art.replace("100x100bb", "300x300bb")})
    return out


def _ids(t: Track):
    return (t.albumartist or t.artist or "").strip(), (t.album or "").strip(), (t.title or "").strip()


def candidates(t: Track, limit: int = 6) -> list[dict]:
    """Для ручного вибору: усі розумні варіанти з обох джерел (без суворої перевірки)."""
    artist, album, title = _ids(t)
    if not artist or not (album or title):
        return []
    out, seen = [], set()
    for fn in (_mb_candidates, _itunes_candidates):
        try:
            for c in fn(artist, album, title, False):
                if c["url"] not in seen:
                    seen.add(c["url"])
                    out.append(c)
        except Exception as e:
            log(f"обкладинка ({fn.__name__}): {e}")
    # спершу ті, що точно збігаються
    def rank(c):
        lab = c["label"].split(" — ", 1)
        return not (len(lab) == 2 and same(lab[0], artist) and same(lab[1], album or lab[1]))
    out.sort(key=rank)
    return out[:limit]


def download(url: str) -> bytes | None:
    try:
        return _get(url, "image/*", MAX_BYTES)
    except Exception as e:
        log(f"обкладинка: {e}")
        return None


def fetch_auto(t: Track) -> bytes | None:
    """Автоматичний пошук: лише впевнений збіг. Повертає JPEG (уже в кеші) або None."""
    k = cache_key(t)
    if not k or _missed_recently(k):
        return None
    artist, album, title = _ids(t)
    for fn in (_mb_candidates, _itunes_candidates):
        try:
            cands = fn(artist, album, title, True)
        except Exception as e:
            log(f"обкладинка ({fn.__name__}): {e}")
            return None                   # мережа впала — спробуємо іншого разу, без позначки «не знайдено»
        for c in cands[:3]:
            data = download(c["url"])
            if data:
                jpg = store(t, data)
                if jpg:
                    return jpg
    try:
        COVERS_DIR.mkdir(parents=True, exist_ok=True)
        (COVERS_DIR / f"{k}.none").touch()
    except OSError:
        pass
    return None


_busy: set[str] = set()
_busy_lock = threading.Lock()


def fetch_in_background(t: Track, done) -> bool:
    """Шукати у фоні; done(jpg) викликається з іншого потоку, лише якщо щось знайшлося."""
    k = cache_key(t)
    if not k or _missed_recently(k):
        return False
    with _busy_lock:
        if k in _busy:
            return False
        _busy.add(k)

    def work():
        try:
            jpg = fetch_auto(t)
        finally:
            with _busy_lock:
                _busy.discard(k)
        if jpg:
            done(jpg)
    threading.Thread(target=work, daemon=True).start()
    return True
