"""Обкладинки з інтернету: лише впевнений збіг, кеш, нічого без потреби."""
import io
import json

from PIL import Image

from plativka import covers
from plativka.core import Track, load_cover


def png(color=(200, 30, 30)):
    b = io.BytesIO()
    Image.new("RGB", (40, 40), color).save(b, "PNG")
    return b.getvalue()


def fake_get(responses, calls):
    def get(url, accept="application/json", limit=0):
        calls.append(url)
        for k, v in responses.items():
            if k in url:
                return v
        raise OSError("offline")
    return get


def test_matching():
    assert covers.same("Океан Ельзи", "Okean Elzy")
    assert covers.same("Abbey Road (Remastered 2009)", "Abbey Road")
    assert not covers.same("Love", "Live")
    assert not covers.same("", "x")


def test_auto_fetch_and_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(covers, "COVERS_DIR", tmp_path / "c")
    monkeypatch.setattr(covers, "_mb_last", 0.0)
    mb = {"release-groups": [
        {"id": "wrong", "score": 100, "title": "Земля (Live)", "artist-credit": [{"name": "Інший гурт"}]},
        {"id": "rg1", "score": 100, "title": "Земля", "artist-credit": [{"name": "Океан Ельзи"}]}]}
    calls = []
    monkeypatch.setattr(covers, "_get", fake_get({"musicbrainz.org": json.dumps(mb).encode(),
                                                  "release-group/rg1/front-500": png(),
                                                  "itunes.apple.com": b'{"results": []}'}, calls))
    t = Track(path=str(tmp_path / "b.mp3"), artist="Someone Else", album="Земля", title="x")
    t3 = Track(path=str(tmp_path / "c.mp3"), artist="Okean Elzy", album="Zemlia", title="x")
    t2 = Track(path=str(tmp_path / "a.mp3"), artist="Океан Ельзи", album="Земля", title="x")
    assert covers.fetch_auto(t2)
    assert not any("wrong" in c for c in calls)
    assert covers.cached(t2)
    (tmp_path / "a.mp3").write_bytes(b"")
    im = load_cover(str(tmp_path / "a.mp3"), track=t2)
    assert im is not None and im.size == (40, 40)
    calls.clear()
    assert covers.fetch_auto(t3)                          # латиницею теж збігається
    calls.clear()
    assert covers.fetch_auto(t) is None                   # чужий виконавець — не вгадуємо
    assert covers.fetch_auto(t) is None and len([c for c in calls if "musicbrainz" in c]) <= 1   # промах запам'ятали


def test_offline_is_quiet_and_not_remembered(tmp_path, monkeypatch):
    monkeypatch.setattr(covers, "COVERS_DIR", tmp_path / "c")
    monkeypatch.setattr(covers, "_get", fake_get({}, []))
    t = Track(path="/x/a.mp3", artist="A", album="B")
    assert covers.fetch_auto(t) is None
    assert not (tmp_path / "c").exists() or not list((tmp_path / "c").glob("*.none"))
