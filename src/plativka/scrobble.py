"""Скроблінг: Last.fm і ListenBrainz. Обидва вимкнені, доки людина сама їх не підключить.

Що надсилається: виконавець, назва, альбом, тривалість і час прослуховування — більше нічого.
Правило скроблу (як у Last.fm): трек довший за 30 с, прослухано половину або 4 хвилини.
Рахується саме час звучання (пауза й перемотування вперед не додають).

Без інтернету прослухане чекає в черзі (файл у теці налаштувань) і надсилається пізніше —
Платівка лишається офлайн-плеєром. Вся мережа — в окремому потоці, плеєр нею не гальмує.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .core import CONF_DIR, VERSION, log
from .i18n import _

CONF = CONF_DIR / "scrobble.json"
QUEUE = CONF_DIR / "scrobble-queue.json"
MIN_LEN = 30.0
MAX_WAIT = 240.0
BATCH = 50
LASTFM_API = os.environ.get("PLATIVKA_LASTFM_API", "https://ws.audioscrobbler.com/2.0/")
LASTFM_AUTH = "https://www.last.fm/api/auth/"
LB_API = os.environ.get("PLATIVKA_LB_API", "https://api.listenbrainz.org").rstrip("/")


def lastfm_keys() -> tuple[str, str]:
    """Ключ застосунку Платівка на Last.fm: у збірках — вбудований (_keys.py з секретів GitHub),
    з вихідного коду — зі змінних середовища PLATIVKA_LASTFM_KEY / PLATIVKA_LASTFM_SECRET."""
    key, secret = os.environ.get("PLATIVKA_LASTFM_KEY", ""), os.environ.get("PLATIVKA_LASTFM_SECRET", "")
    if not (key and secret):
        try:
            from . import _keys
            key, secret = getattr(_keys, "LASTFM_KEY", ""), getattr(_keys, "LASTFM_SECRET", "")
        except ImportError:
            pass
    return key, secret


class ScrobbleError(Exception):
    def __init__(self, msg: str, auth: bool = False, retry: bool = True):
        super().__init__(msg)
        self.auth, self.retry = auth, retry


def _http(url: str, data: dict | bytes | None = None, headers: dict | None = None, timeout: float = 15):
    from .core import https_context
    body = None
    if isinstance(data, dict):
        body = urllib.parse.urlencode(data).encode()
    elif isinstance(data, bytes):
        body = data
    req = urllib.request.Request(url, data=body, headers={"User-Agent": f"Plativka/{VERSION}", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=https_context()) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


# ═══════════════════════ Last.fm ═══════════════════════
class LastFM:
    name = "Last.fm"

    def __init__(self, key: str, secret: str, session: str = "", user: str = ""):
        self.key, self.secret, self.session, self.user = key, secret, session, user

    def _sign(self, params: dict) -> str:
        raw = "".join(f"{k}{params[k]}" for k in sorted(params) if k not in ("format", "callback"))
        return hashlib.md5((raw + self.secret).encode("utf-8")).hexdigest()

    def call(self, method: str, params: dict | None = None, post: bool = True, session: bool = True) -> dict:
        p = {"method": method, "api_key": self.key, **{k: str(v) for k, v in (params or {}).items() if v not in (None, "")}}
        if session:
            p["sk"] = self.session
        p["api_sig"] = self._sign(p)
        p["format"] = "json"
        try:
            if post:
                code, raw = _http(LASTFM_API, p)
            else:
                code, raw = _http(LASTFM_API + "?" + urllib.parse.urlencode(p))
        except OSError as e:
            raise ScrobbleError(f"мережа: {getattr(e, 'reason', e)}") from e
        try:
            j = json.loads(raw or b"{}")
        except ValueError:
            raise ScrobbleError(f"Last.fm: HTTP {code}")
        if "error" in j:
            err = int(j.get("error") or 0)
            # 4, 9, 14 — немає чи прострочений дозвіл: треба підключити знову; 11, 16, 29 — тимчасово
            raise ScrobbleError(f"Last.fm {err}: {j.get('message', '')}", auth=err in (4, 9, 14, 26),
                                retry=err in (8, 11, 16, 29))
        if code >= 500:
            raise ScrobbleError(f"Last.fm: HTTP {code}")
        return j

    # ── підключення: токен → сторінка в браузері → сесія ──
    def get_token(self) -> str:
        return self.call("auth.getToken", post=False, session=False)["token"]

    def auth_url(self, token: str) -> str:
        return f"{LASTFM_AUTH}?api_key={self.key}&token={token}"

    def get_session(self, token: str) -> tuple[str, str]:
        s = self.call("auth.getSession", {"token": token}, post=False, session=False)["session"]
        return s["key"], s.get("name", "")

    # ── робота ──
    def now_playing(self, t: dict):
        self.call("track.updateNowPlaying", {"artist": t["artist"], "track": t["title"], "album": t.get("album"),
                                             "duration": int(t.get("length") or 0) or None})

    def scrobble(self, items: list[dict]):
        p = {}
        for i, t in enumerate(items[:BATCH]):
            p[f"artist[{i}]"], p[f"track[{i}]"], p[f"timestamp[{i}]"] = t["artist"], t["title"], int(t["ts"])
            if t.get("album"):
                p[f"album[{i}]"] = t["album"]
            if t.get("length"):
                p[f"duration[{i}]"] = int(t["length"])
        self.call("track.scrobble", p)

    def love(self, t: dict, on: bool):
        self.call("track.love" if on else "track.unlove", {"artist": t["artist"], "track": t["title"]})


# ═══════════════════════ ListenBrainz ═══════════════════════
class ListenBrainz:
    name = "ListenBrainz"

    def __init__(self, token: str = "", user: str = ""):
        self.token, self.user = token, user

    def _req(self, path: str, payload: dict | None = None) -> dict:
        try:
            code, raw = _http(LB_API + path, json.dumps(payload).encode() if payload is not None else None,
                              {"Authorization": f"Token {self.token}", "Content-Type": "application/json"})
        except OSError as e:
            raise ScrobbleError(f"мережа: {getattr(e, 'reason', e)}") from e
        try:
            j = json.loads(raw or b"{}")
        except ValueError:
            j = {}
        if code == 401:
            raise ScrobbleError("ListenBrainz: токен не підходить", auth=True, retry=False)
        if code == 429 or code >= 500:
            raise ScrobbleError(f"ListenBrainz: HTTP {code}")
        if code >= 400:
            raise ScrobbleError(f"ListenBrainz {code}: {j.get('error', '')}", retry=False)
        return j

    def validate(self) -> str:
        j = self._req("/1/validate-token")
        if not j.get("valid"):
            raise ScrobbleError("ListenBrainz: токен не підходить", auth=True, retry=False)
        return j.get("user_name", "")

    @staticmethod
    def _meta(t: dict) -> dict:
        info = {"media_player": "Plativka", "media_player_version": VERSION,
                "submission_client": "Plativka", "submission_client_version": VERSION}
        if t.get("length"):
            info["duration_ms"] = int(float(t["length"]) * 1000)
        m = {"artist_name": t["artist"], "track_name": t["title"], "additional_info": info}
        if t.get("album"):
            m["release_name"] = t["album"]
        return m

    def now_playing(self, t: dict):
        self._req("/1/submit-listens", {"listen_type": "playing_now", "payload": [{"track_metadata": self._meta(t)}]})

    def scrobble(self, items: list[dict]):
        payload = [{"listened_at": int(t["ts"]), "track_metadata": self._meta(t)} for t in items[:BATCH]]
        self._req("/1/submit-listens", {"listen_type": "single" if len(payload) == 1 else "import", "payload": payload})

    def love(self, t: dict, on: bool):
        """Лайк у ListenBrainz прив'язаний до запису MusicBrainz — шукаємо його за виконавцем і назвою."""
        q = urllib.parse.urlencode({"artist_name": t["artist"], "recording_name": t["title"]})
        j = self._req(f"/1/metadata/lookup/?{q}")
        mbid = j.get("recording_mbid")
        if not mbid:
            log(f"ListenBrainz: не знайшов «{t['artist']} — {t['title']}» у MusicBrainz, лайк пропущено")
            return
        self._req("/1/feedback/recording-feedback", {"recording_mbid": mbid, "score": 1 if on else 0})


# ═══════════════════════ Скроблер: правило, черга, потік ═══════════════════════
def _meta_of(track) -> dict | None:
    artist = (track.artist or "").strip()
    title = (track.title or "").strip()
    if not artist or not title:
        return None                          # без виконавця Last.fm скробл не прийме
    return {"artist": artist, "title": title, "album": (track.album or "").strip(), "length": float(track.length or 0)}


class Scrobbler:
    def __init__(self, conf_path=None, queue_path=None):
        self.conf_path, self.queue_path = conf_path or CONF, queue_path or QUEUE
        self.cfg = self._read(self.conf_path, {})
        self.pending: list[dict] = self._read(self.queue_path, [])
        self.errors: dict[str, str] = {}      # служба → остання помилка (для значка й вікна)
        self.sent = 0
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._jobs: list = []                 # «зараз грає» й лайки — надсилаються, коли мережа є
        self._cur = None                      # (метадані, час початку, наслухано секунд, уже скроблено)
        self._last = None
        self._thread = None
        self.on_change = None                 # виклик (з потоку), коли змінився стан — оновити значок

    # ── збереження ──
    @staticmethod
    def _read(path, default):
        try:
            return json.loads(path.read_text("utf-8"))
        except (OSError, ValueError):
            return default

    def _write(self, path, data):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
            try:
                os.chmod(tmp, 0o600)          # там дозволи Last.fm і токен ListenBrainz
            except OSError:
                pass
            os.replace(tmp, path)
        except OSError as e:
            log(f"скроблінг: не вдалося зберегти {path.name}: {e}")

    def save_conf(self):
        self._write(self.conf_path, self.cfg)

    # ── служби ──
    def services(self) -> list:
        out = []
        lf = self.cfg.get("lastfm") or {}
        key, secret = lastfm_keys()
        if lf.get("session") and key:
            out.append(LastFM(key, secret, lf["session"], lf.get("user", "")))
        lb = self.cfg.get("listenbrainz") or {}
        if lb.get("token"):
            out.append(ListenBrainz(lb["token"], lb.get("user", "")))
        return out

    @property
    def enabled(self) -> bool:
        return bool(self.services())

    def love_sync(self, name: str) -> bool:
        key = "lastfm" if name == LastFM.name else "listenbrainz"
        return bool((self.cfg.get(key) or {}).get("love", True))

    def status(self) -> tuple[str, str]:
        """(стан, підказка): off / ok / wait / error."""
        if not self.enabled:
            return "off", ""
        names = ", ".join(f"{s.name} ({s.user})" if s.user else s.name for s in self.services())
        if self.errors:
            return "error", "; ".join(f"{k}: {v}" for k, v in self.errors.items())
        n = len(self.pending)
        return ("wait", f"{names} · {n}") if n else ("ok", names)

    def _changed(self):
        cb = self.on_change
        if cb:
            try:
                cb()
            except Exception:
                pass

    # ── прослуховування (викликається з потоку інтерфейсу) ──
    def begin(self, track):
        """Почав грати новий трек: «зараз грає» і новий відлік часу."""
        meta = _meta_of(track) if track is not None else None
        # [метадані, час початку, наслухано с, уже скроблено, «зараз грає» вже надіслано]
        self._cur = [meta, time.time(), 0.0, False, False] if meta else None
        self._last = None

    def tick(self, playing: bool):
        """Кожні ~0,5 с: додати час звучання; дійшли до порогу — поставити скробл у чергу."""
        now = time.time()
        last, self._last = self._last, now
        cur = self._cur
        if not cur or not playing or last is None:
            return
        meta = cur[0]
        if not cur[4]:                        # «зараз грає» — коли трек справді зазвучав, а не на паузі після запуску
            cur[4] = True
            cur[1] = now
            if self.enabled:
                self._push(("now", meta))
        dt = now - last
        if dt <= 0 or dt > 5:                 # сон комп'ютера чи збій таймера — не рахуємо
            return
        cur[2] += dt
        if cur[3] or meta["length"] < MIN_LEN:
            return
        if cur[2] >= min(meta["length"] / 2, MAX_WAIT):
            cur[3] = True
            if self.enabled:
                with self._lock:
                    self.pending.append({**meta, "ts": int(cur[1]), "to": [s.name for s in self.services()]})
                    self._write(self.queue_path, self.pending)
                self._changed()
                self._wake.set()

    def love(self, track, on: bool):
        meta = _meta_of(track)
        if meta and self.enabled:
            self._push(("love", meta, on))

    def _push(self, job):
        with self._lock:
            self._jobs.append(job)
        self.start()
        self._wake.set()

    # ── надсилання (окремий потік) ──
    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name="scrobbler", daemon=True)
            self._thread.start()
        if self.pending:
            self._wake.set()

    def flush(self):
        self.start()
        self._wake.set()

    def _run(self):
        delay = 60.0
        while True:
            self._wake.wait(delay)
            self._wake.clear()
            if not self.enabled:
                with self._lock:
                    self._jobs.clear()
                continue
            ok = self.send_all()
            delay = 60.0 if ok else min(delay * 2, 900.0) if self.pending else 60.0

    def send_all(self) -> bool:
        """Надіслати, що є. True — усе пішло (або нічого не було)."""
        ok = True
        with self._lock:
            jobs, self._jobs = self._jobs, []
        services = {s.name: s for s in self.services()}
        for job in jobs:
            for s in services.values():
                if job[0] == "love" and not self.love_sync(s.name):
                    continue
                try:
                    s.now_playing(job[1]) if job[0] == "now" else s.love(job[1], job[2])
                    self.errors.pop(s.name, None)
                except ScrobbleError as e:
                    self._fail(s, e)
                    if job[0] == "love" and e.retry:      # лайк не губимо — спробуємо пізніше
                        with self._lock:
                            self._jobs.append(job)
                        ok = False
        for name, s in services.items():
            while True:
                with self._lock:
                    batch = [t for t in self.pending if name in t.get("to", [name])][:BATCH]
                if not batch:
                    break
                try:
                    s.scrobble(batch)
                    self.errors.pop(name, None)
                except ScrobbleError as e:
                    self._fail(s, e)
                    ok = False
                    if e.retry or e.auth:
                        break                              # лишаємо в черзі
                with self._lock:                           # надіслано (або відкинуто сервісом) — прибрати
                    for t in batch:
                        to = [x for x in t.get("to", [name]) if x != name]
                        if to:
                            t["to"] = to
                        elif t in self.pending:
                            self.pending.remove(t)
                    self.sent += len(batch)
                    self._write(self.queue_path, self.pending)
        self._changed()
        return ok

    def _fail(self, s, e: ScrobbleError):
        msg = str(e)
        if e.auth:
            msg = _("потрібно підключити знову")
        elif msg.startswith("мережа"):
            msg = "offline"
        if self.errors.get(s.name) != msg:
            log(f"скроблінг {s.name}: {e}")
        if msg == "offline":
            self.errors.pop(s.name, None)                 # не помилка: просто черга
        else:
            self.errors[s.name] = msg

    # ── налаштування (з вікна) ──
    def connect_lastfm(self, session: str, user: str):
        self.cfg["lastfm"] = {**(self.cfg.get("lastfm") or {}), "session": session, "user": user}
        self.errors.pop(LastFM.name, None)
        self.save_conf()
        self.start()

    def connect_listenbrainz(self, token: str, user: str):
        self.cfg["listenbrainz"] = {**(self.cfg.get("listenbrainz") or {}), "token": token, "user": user}
        self.errors.pop(ListenBrainz.name, None)
        self.save_conf()
        self.start()

    def disconnect(self, name: str):
        key = "lastfm" if name == LastFM.name else "listenbrainz"
        self.cfg.pop(key, None)
        self.errors.pop(name, None)
        with self._lock:
            for t in list(self.pending):
                to = [x for x in t.get("to", []) if x != name]
                if to:
                    t["to"] = to
                else:
                    self.pending.remove(t)
            self._write(self.queue_path, self.pending)
        self.save_conf()
        self._changed()

    def set_love_sync(self, name: str, on: bool):
        key = "lastfm" if name == LastFM.name else "listenbrainz"
        if key in self.cfg:
            self.cfg[key]["love"] = bool(on)
            self.save_conf()
