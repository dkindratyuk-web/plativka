"""Скроблінг: правило «половина або 4 хвилини», черга без інтернету, підписи Last.fm, ListenBrainz."""
import hashlib
import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import pytest

from plativka import scrobble


def T(artist="Glass Atlas", title="Slow Orbit", album="Slow Orbit", length=252.0):
    return SimpleNamespace(artist=artist, title=title, album=album, length=length)


class Clock:
    def __init__(self):
        self.t = 1_700_000_000.0

    def __call__(self):
        return self.t


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(scrobble.time, "time", c)
    return c


@pytest.fixture
def sc(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATIVKA_LASTFM_KEY", "k")
    monkeypatch.setenv("PLATIVKA_LASTFM_SECRET", "s")
    s = scrobble.Scrobbler(tmp_path / "c.json", tmp_path / "q.json")
    s.start = lambda: None                    # без фонового потоку: надсилаємо вручну
    return s


def play(s, clock, seconds, step=0.5, playing=True):
    for _ in range(int(seconds / step)):
        clock.t += step
        s.tick(playing)


def test_rule_half_or_four_minutes(sc, clock):
    sc.cfg = {"lastfm": {"session": "x", "user": "me"}}
    sc.begin(T(length=252))
    play(sc, clock, 120)
    assert not sc.pending                       # ще не половина
    play(sc, clock, 10)
    assert len(sc.pending) == 1 and sc.pending[0]["title"] == "Slow Orbit"
    sc.begin(T(title="Long", length=1800))
    play(sc, clock, 239)
    assert len(sc.pending) == 1
    play(sc, clock, 2)                          # 4 хвилини
    assert len(sc.pending) == 2
    sc.begin(T(title="Intro", length=20))       # коротше за 30 с — не скроблиться
    play(sc, clock, 20)
    sc.begin(T(title="Paused"))
    play(sc, clock, 600, playing=False)         # пауза не рахується
    assert len(sc.pending) == 2
    sc.begin(SimpleNamespace(artist="", title="file name", album="", length=200))
    play(sc, clock, 200)                        # без виконавця — не скроблимо
    assert len(sc.pending) == 2


def test_disabled_collects_nothing(sc, clock):
    sc.begin(T())
    play(sc, clock, 300)
    assert not sc.pending and sc.status()[0] == "off"


def test_lastfm_signature():
    lf = scrobble.LastFM("key", "secret")
    p = {"method": "auth.getSession", "api_key": "key", "token": "t", "format": "json"}
    assert lf._sign(p) == hashlib.md5("api_keykeymethodauth.getSessiontokentsecret".encode()).hexdigest()


class Fake(BaseHTTPRequestHandler):
    calls: list = []
    down = False

    def log_message(self, *a):
        pass

    def _reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        Fake.calls.append(("GET", u.path, q, self.headers.get("Authorization")))
        if u.path == "/1/validate-token":
            return self._reply(200, {"valid": self.headers.get("Authorization") == "Token good", "user_name": "lbuser"})
        if u.path == "/1/metadata/lookup/":
            return self._reply(200, {"recording_mbid": "mbid-1"})
        if q.get("method") == "auth.getToken":
            return self._reply(200, {"token": "tok"})
        if q.get("method") == "auth.getSession":
            return self._reply(200, {"session": {"key": "sess", "name": "lfuser"}})
        self._reply(404, {})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        if Fake.down:
            return self._reply(503, {})
        u = urllib.parse.urlparse(self.path)
        if self.headers.get("Content-Type") == "application/json":
            Fake.calls.append(("POST", u.path, json.loads(raw), self.headers.get("Authorization")))
            return self._reply(200, {"status": "ok"})
        q = dict(urllib.parse.parse_qsl(raw.decode()))
        Fake.calls.append(("POST", u.path, q, None))
        if q.get("sk") == "expired":
            return self._reply(403, {"error": 9, "message": "Invalid session key"})
        self._reply(200, {"ok": 1})


@pytest.fixture
def server(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    monkeypatch.setattr(scrobble, "LASTFM_API", base + "/2.0/")
    monkeypatch.setattr(scrobble, "LB_API", base)
    monkeypatch.setattr(scrobble, "_http", _plain_http)
    Fake.calls, Fake.down = [], False
    yield base
    srv.shutdown()


def _plain_http(url, data=None, headers=None, timeout=5):
    import urllib.error
    import urllib.request
    body = urllib.parse.urlencode(data).encode() if isinstance(data, dict) else data
    req = urllib.request.Request(url, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_send_both_services_queue_offline_and_love(sc, clock, server):
    lf = scrobble.LastFM("k", "s")
    assert lf.get_token() == "tok" and lf.get_session("tok") == ("sess", "lfuser")
    lb = scrobble.ListenBrainz("good")
    assert lb.validate() == "lbuser"
    with pytest.raises(scrobble.ScrobbleError):
        scrobble.ListenBrainz("bad").validate()

    sc.connect_lastfm("sess", "lfuser")
    sc.connect_listenbrainz("good", "lbuser")
    Fake.down = True                              # «немає інтернету»
    sc.begin(T())
    play(sc, clock, 200)
    assert sc.send_all() is False and len(sc.pending) == 1 and sc.status()[0] in ("wait", "error")
    Fake.down = False
    assert sc.send_all() is True and not sc.pending and sc.status()[0] == "ok"
    posts = [c for c in Fake.calls if c[0] == "POST"]
    assert any(c[2].get("method") == "track.scrobble" and c[2].get("artist[0]") == "Glass Atlas" for c in posts)
    assert any(c[1] == "/1/submit-listens" and c[2]["payload"][0]["track_metadata"]["track_name"] == "Slow Orbit"
               for c in posts)

    sc.love(T(), True)
    sc.send_all()
    assert any(c[2].get("method") == "track.love" for c in Fake.calls if c[0] == "POST")
    assert any(c[1] == "/1/feedback/recording-feedback" and c[2] == {"recording_mbid": "mbid-1", "score": 1}
               for c in Fake.calls if c[0] == "POST")


def test_expired_session_keeps_queue(sc, clock, server):
    sc.connect_lastfm("expired", "lfuser")
    sc.begin(T())
    play(sc, clock, 200)
    assert sc.send_all() is False
    assert len(sc.pending) == 1 and sc.status()[0] == "error" and sc.status()[1].startswith("Last.fm: ")
    sc.disconnect("Last.fm")
    assert not sc.pending and sc.status()[0] == "off"
