"""Збережені списки відтворення: M3U8, який читають і інші плеєри."""
from types import SimpleNamespace

import pytest

from plativka import playlists


def test_save_load_rename_delete(tmp_path):
    music = tmp_path / "m"
    music.mkdir()
    a, b = music / "a.mp3", music / "b.flac"
    a.write_bytes(b"x")
    b.write_bytes(b"x")
    d = tmp_path / "pl"
    track = lambda p: SimpleNamespace(length=200, display=p.rsplit("/", 1)[-1])
    f = playlists.save("Для: машини?", [str(a), str(b), str(b) + "#track2"], track, folder=d)
    assert f.name == "Для машини.m3u8"                       # недозволені символи прибрано
    text = f.read_text("utf-8")
    assert text.startswith("#EXTM3U") and "#EXTINF:200,a.mp3" in text
    assert playlists.load(f) == [str(a), str(b), str(b) + "#track2"]
    assert [n for n, _ in playlists.list_all(d)] == ["Для машини"]
    playlists.rename("Для машини", "Дорога", folder=d)
    assert [n for n, _ in playlists.list_all(d)] == ["Дорога"]
    assert "#PLAYLIST:Дорога" in (d / "Дорога.m3u8").read_text("utf-8")
    playlists.save("Інший", [str(a)], folder=d)
    with pytest.raises(FileExistsError):
        playlists.rename("Інший", "Дорога", folder=d)
    assert playlists.delete("Інший", folder=d)
    assert [n for n, _ in playlists.list_all(d)] == ["Дорога"]


def test_load_foreign_m3u(tmp_path):
    """Відносні шляхи, file://-адреси й cp1251 з чужих плеєрів."""
    (tmp_path / "sub").mkdir()
    f = tmp_path / "old.m3u"
    f.write_bytes("#EXTM3U\n\nsub/пісня.mp3\nfile:///music/x%20y.mp3\n".encode("cp1251"))
    got = playlists.load(f)
    assert got[0] == str((tmp_path / "sub" / "пісня.mp3").resolve())
    assert got[1] == "/music/x y.mp3"
