"""Пошук дублікатів."""
from plativka.core import Track
from plativka.dupes import find_duplicates


def test_groups(tmp_path):
    def mk(name, data, **kw):
        f = tmp_path / name
        f.write_bytes(data)
        return Track(path=str(f), size=len(data), **kw)
    a = mk("a.mp3", b"same-bytes", title="X", artist="Y", length=100, bitrate=128)
    b = mk("copy of a.mp3", b"same-bytes", title="X", artist="Y", length=100, bitrate=128)
    c = mk("x.flac", b"other-bytes-longer", title="X (Remastered)", artist="y", length=101.5, bitrate=900)
    d = mk("z.mp3", b"zzz", title="X", artist="Y", length=200)           # інша тривалість — інша версія
    e = mk("solo.mp3", b"same-bytes!", title="Other", artist="Y", length=100)
    cue = Track(path=str(tmp_path / "a.mp3") + "#track01", title="X", artist="Y", length=100, end=100)
    gs = find_duplicates([a, b, c, d, e, cue])
    assert len(gs) == 1
    g = gs[0]
    assert g.kind == "song" and set(g.paths) == {a.path, b.path, c.path}
    assert g.paths[0] == c.path and g.keep == {c.path}         # без втрат — лишаємо його
    assert set(g.extra) == {a.path, b.path}
    gs = find_duplicates([a, b])
    assert gs[0].kind == "file"
