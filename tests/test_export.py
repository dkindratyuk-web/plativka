"""Копіювання списку на флешку."""
import os

from plativka.core import Track
from plativka.export import plan_copy, run_copy, safe_name


def tr(p):
    return Track(path=p, title="Song: Part 1?", artist="AC/DC", length=1)


def test_safe_name():
    assert safe_name('a<b>:"c"/d\\e|f?*. ') == "a_b___c__d_e_f__"
    assert safe_name("...") == "track"


def test_plan_and_copy(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    files = []
    for i in range(3):
        f = src / f"{i}.mp3"
        f.write_bytes(b"x" * (i + 1))
        files.append(str(f))
    dest = tmp_path / "usb"
    dest.mkdir()
    (dest / "02 - AC_DC - Song_ Part 1_.mp3").write_bytes(b"old")
    plan = plan_copy(files + [files[0]], tr, str(dest))
    names = [n for _, n in plan.items]
    assert names == ["01 - AC_DC - Song_ Part 1_.mp3", "02 - AC_DC - Song_ Part 1_.mp3",
                     "03 - AC_DC - Song_ Part 1_.mp3"]
    assert [n for _, n in plan_copy(files, tr, str(dest), numbered=False).items][1] == "AC_DC - Song_ Part 1_ (2).mp3"
    assert plan.total == 6 and plan.fits
    assert plan.existing == ["02 - AC_DC - Song_ Part 1_.mp3"]
    done, skipped, errors = run_copy(plan)
    assert (done, skipped, errors) == (2, 1, [])
    assert (dest / plan.existing[0]).read_bytes() == b"old"       # без дозволу не перезаписує
    assert not [f for f in os.listdir(dest) if f.endswith(".part")]
    assert run_copy(plan, replace=True)[0] == 3
    assert (dest / plan.existing[0]).read_bytes() == b"xx"
