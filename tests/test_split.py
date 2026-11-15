"""Розбивка довгого запису на треки: список із таймкодами → .cue, який Платівка читає як треки."""
import os

from plativka import core, split

LIST = """Tracklist:
0:00 Northwind Hollow - Harbour Lights
03:18 Northwind Hollow – Lantern Coast
[6:54] Мавка Бенд — Полонина
Glass Atlas - Slow Orbit 10:18
1:02:03 Останній трек
42:00 поза записом? ні — це просто трек
"""


def test_parse_tracklist():
    items, skipped = split.parse_tracklist(LIST, duration=3800)
    assert [round(i.start) for i in items] == [0, 198, 414, 618, 2520, 3723]
    assert (items[0].artist, items[0].title) == ("Northwind Hollow", "Harbour Lights")
    assert (items[2].artist, items[2].title) == ("Мавка Бенд", "Полонина")
    assert (items[3].artist, items[3].title) == ("Glass Atlas", "Slow Orbit")   # час у кінці рядка
    assert items[4].title == "Останній трек" or items[5].title == "Останній трек"
    assert skipped == ["Tracklist:"]
    items, skipped = split.parse_tracklist("0:00 A - B\n1:30:00 C - D", duration=1200)
    assert len(items) == 1 and len(skipped) == 1                                # позначка поза записом


def test_save_and_read_as_tracks(tmp_path, monkeypatch):
    audio = tmp_path / "Live at the club.mp3"
    audio.write_bytes(b"\xff\xfb" + b"\0" * 2000)
    items, _ = split.parse_tracklist("0:05 A - One\n2:00 B - Two\n4:30 Three", 600)
    cue = split.save(str(audio), items)
    assert cue == audio.with_suffix(".cue") and split.existing(str(audio)) == cue
    tracks = core.expand_file(str(audio))
    assert tracks == [core.cue_path(str(audio), n) for n in (1, 2, 3)]
    t2 = core.read_cue_track(tracks[1])
    assert (t2.artist, t2.title, t2.start, t2.end) == ("B", "Two", 120.0, 270.0)
    assert list(core.scan_dir(str(tmp_path))) == tracks
    assert "2:00 B — Two" in split.read_back(str(audio))
    assert split.remove(str(audio)) and core.expand_file(str(audio)) == [str(audio)]


def test_foreign_cue_is_kept(tmp_path, monkeypatch):
    """Чужий .cue поруч не перезаписуємо — розбивка йде в теку налаштувань і теж читається."""
    monkeypatch.setattr(core, "SPLITS_DIR", tmp_path / "splits")
    audio = tmp_path / "rip.flac"
    audio.write_bytes(b"fLaC" + b"\0" * 100)
    (tmp_path / "rip.cue").write_text("REM something else\n", "utf-8")
    items, _ = split.parse_tracklist("0:00 X\n1:00 Y", 300)
    cue = split.save(str(audio), items)
    assert cue.parent == tmp_path / "splits" and (tmp_path / "rip.cue").read_text("utf-8") == "REM something else\n"
    assert len(core.expand_file(str(audio))) == 2
    assert len(list(core.scan_dir(str(tmp_path)))) == 2
    assert os.path.exists(cue)
