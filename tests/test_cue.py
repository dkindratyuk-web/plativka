"""Альбом одним файлом + .cue: треки, назви, межі, кодування cp1251."""
import os

from plativka import core


def _album(tmp_path, cue_text, enc="utf-8", audio="album.flac"):
    (tmp_path / audio).write_bytes(b"\0" * 10)
    (tmp_path / "album.cue").write_bytes(cue_text.encode(enc))
    return tmp_path


CUE = '''REM DATE 2001
PERFORMER "Гурт"
TITLE "Альбом"
FILE "album.wav" WAVE
  TRACK 01 AUDIO
    TITLE "Перша"
    INDEX 01 00:00:00
  TRACK 02 AUDIO
    TITLE "Друга"
    PERFORMER "Гість"
    INDEX 00 03:10:00
    INDEX 01 03:12:37
  TRACK 03 AUDIO
    TITLE "Третя"
    INDEX 01 07:00:00
'''


def test_cue_expands_into_tracks(tmp_path):
    d = _album(tmp_path, CUE, "cp1251")      # .cue у Windows-1251, а файл — .flac, не .wav
    paths = list(core.scan_dir(str(d)))
    assert [p.rsplit("#", 1)[1] for p in paths] == ["track01", "track02", "track03"]
    assert all(core.real_path(p) == str(d / "album.flac") for p in paths)
    t2 = core.read_track(paths[1])
    assert (t2.title, t2.artist, t2.album, t2.year, t2.track) == ("Друга", "Гість", "Альбом", "2001", 2)
    assert abs(t2.start - (192 + 37 / 75)) < 1e-6 and t2.end == 420.0
    t3 = core.read_track(paths[2])
    assert t3.artist == "Гурт" and t3.end == 0.0 and t3.segment == (420.0, 0.0)
    assert core.read_track(paths[0]).segment == (0.0, t2.start)


def test_plain_files_untouched(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"\0")
    (tmp_path / "b.mp3").write_bytes(b"\0")
    (tmp_path / "x.cue").write_text('FILE "missing.wav" WAVE\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n')
    assert [os.path.basename(p) for p in core.scan_dir(str(tmp_path))] == ["a.mp3", "b.mp3"]
    assert core.real_path(str(tmp_path / "a.mp3")) == str(tmp_path / "a.mp3")


def test_version_compare():
    assert core.version_tuple("v1.3.10") > core.version_tuple("1.3.9")
    assert core.version_tuple("1.4") > core.version_tuple("1.3.5")
