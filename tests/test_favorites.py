"""Улюблені: лайки, перенесені файли, історія, розумні списки, «Прибрати неулюблені»."""
import os
import time

from plativka import favorites as F
from plativka.core import Track


def _t(path, artist="Kane Brown", title="Woman", length=166.0, album="X", added=0.0):
    return Track(path=path, artist=artist, title=title, length=length, album=album, added=added)


def test_like_toggle_and_shared_file(tmp_path):
    f = F.Favorites(tmp_path / "fav.json")
    t = _t("/m/a.mp3")
    assert f.toggle(t) is True and "/m/a.mp3" in f
    other = F.Favorites(tmp_path / "fav.json")          # друга версія Платівки бачить те саме
    assert "/m/a.mp3" in other
    other.toggle(t)
    f.reload()
    assert "/m/a.mp3" not in f and len(f) == 0


def test_likes_survive_moved_and_renamed_files(tmp_path):
    f = F.Favorites(tmp_path / "fav.json")
    f.set(_t("/old/01 woman.mp3"), True)
    f.set(_t("/old/live.mp3", title="Woman (Live)", length=240.0, album="Live"), True)
    lib = {p: t for p, t in {
        "/new/Kane Brown - Woman.mp3": _t("/new/Kane Brown - Woman.mp3", length=167.0),
        "/new/Woman live.mp3": _t("/new/Woman live.mp3", title="Woman [Live]", length=241.0, album="Live"),
        "/new/other.mp3": _t("/new/other.mp3", title="Body", artist="Don Toliver"),
    }.items()}
    assert f.relink(lib) == 2
    assert set(f.paths()) == {"/new/Kane Brown - Woman.mp3", "/new/Woman live.mp3"}


def test_relink_needs_matching_length(tmp_path):
    f = F.Favorites(tmp_path / "fav.json")
    f.set(_t("/old/a.mp3", length=166), True)
    assert f.relink({"/new/b.mp3": _t("/new/b.mp3", length=300)}) == 0     # інша версія пісні — не чіпаємо


def test_history_and_smart_lists(tmp_path):
    h = F.History(tmp_path / "hist.json")
    h.note("/m/a.mp3", 5, 200)                          # 5 секунд і не перемикали — не рахуємо
    assert not h.heard("/m/a.mp3")
    h.note("/m/a.mp3", 4, 200, skipped=True)            # перемкнули вручну — «звучав», але не «прослухано»
    assert h.heard("/m/a.mp3") and h.plays("/m/a.mp3") == 0
    for _ in range(3):
        h.note("/m/b.mp3", 45, 200)
    h.note("/m/c.mp3", 199, 200)
    h.data["tracks"]["/m/c.mp3"][1] = int(time.time()) - 40 * 86400
    lib = {p: _t(p, added=i) for i, p in enumerate(["/m/a.mp3", "/m/b.mp3", "/m/c.mp3"])}
    assert F.most_played(lib, h) == ["/m/b.mp3"]
    assert F.not_played_lately(lib, h) == ["/m/c.mp3"]
    assert F.recently_added(lib)[0] == "/m/c.mp3"


def test_removal_plan_is_safe(tmp_path):
    for n in ("a", "b", "c", "d"):
        (tmp_path / f"{n}.mp3").write_bytes(b"x" * 1000)
    paths = [str(tmp_path / f"{n}.mp3") for n in "abcd"] + [str(tmp_path / "album.flac") + "#track02"]
    favs = F.Favorites(tmp_path / "fav.json")
    favs.set(_t(paths[0]), True)
    h = F.History(tmp_path / "hist.json")
    for p in (paths[1], paths[2], paths[4]):
        h.note(p, 60, 200)
    plan = F.removal_plan(paths, favs, h, only_heard=True)
    assert plan["keep"] == [paths[0], paths[3]] and plan["unheard"] == 1          # незвучалий d лишається
    assert plan["remove"] == [paths[1], paths[2], paths[4]]
    assert plan["files"] == [paths[1], paths[2]] and plan["cue"] == 1 and plan["size"] == 2000
    plan = F.removal_plan(paths, favs, h, only_heard=False)
    assert paths[3] in plan["remove"] and paths[0] not in plan["remove"]


def test_trash_never_deletes_permanently(tmp_path, monkeypatch):
    moved = []
    import send2trash
    monkeypatch.setattr(send2trash, "send2trash", lambda f: moved.append(f))
    p = tmp_path / "x.mp3"
    p.write_bytes(b"x")
    done, failed = F.move_to_trash([str(p)])
    assert done == [str(p)] and moved == [str(p)] and os.path.exists(p)    # лише через send2trash, без os.remove
