"""Розбити довгий запис на треки за списком із таймкодами.

Довгий запис одним файлом — оцифрована платівка, концерт, мікс, лекція — і список
«00:00 Виконавець — Назва» (з опису, буклета чи власних нотаток). Платівка пише поруч
файл .cue, і далі показує запис окремими треками. Сам аудіофайл не змінюється.

Якщо в теку із записом писати не можна, .cue кладеться в теку налаштувань Платівки.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .core import data_cue, name_from_file
MARK = 'REM COMMENT "Plativka split"'

# 1:02:03, 02:03, 2:03 — зокрема в дужках [02:03] (02:03)
_TS = r"(?:(\d{1,2}):)?(\d{1,3}):(\d{2})(?:[.,]\d+)?"
_HEAD = re.compile(r"^\s*(?:\d{1,3}\s*[.)]\s*)?[\[(]?\s*" + _TS + r"\s*[\])]?\s*(?:[-–—|:•·.]\s*)?(.*)$")
_TAIL = re.compile(r"^\s*(?:\d{1,3}\s*[.)]\s*)?(.*?)\s*[\[(]?\s*" + _TS + r"\s*[\])]?\s*$")


@dataclass
class Item:
    start: float
    artist: str
    title: str


def _secs(h, m, s) -> float:
    return int(h or 0) * 3600 + int(m) * 60 + int(s)


def _name(text: str) -> tuple[str, str]:
    text = text.strip(" \t-–—|:•·")
    text = re.sub(r"\s+", " ", text)
    artist, title = name_from_file(text)
    return artist, title or text


def parse_tracklist(text: str, duration: float = 0.0) -> tuple[list[Item], list[str]]:
    """Розібрати вставлений текст. Повертає (треки, рядки, які не вдалося прочитати).

    Таймкод на початку («03:42 Виконавець — Назва») або в кінці («Виконавець — Назва 03:42»).
    Рядки без таймкоду пропускаються; треки впорядковуються за часом; дублікати часу й
    позначки за межами запису відкидаються.
    """
    items, skipped = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _HEAD.match(line)
        if m and m.group(4).strip():
            start, rest = _secs(m.group(1), m.group(2), m.group(3)), m.group(4)
        else:
            m = _TAIL.match(line)
            if not m or not m.group(1).strip():
                skipped.append(line)
                continue
            start, rest = _secs(m.group(2), m.group(3), m.group(4)), m.group(1)
        artist, title = _name(rest)
        if not title:
            skipped.append(line)
            continue
        items.append(Item(float(start), artist, title))
    items.sort(key=lambda i: i.start)
    out: list[Item] = []
    for it in items:
        if duration and it.start >= duration - 1:
            skipped.append(f"{fmt(it.start)} {it.title}")
            continue
        if out and it.start - out[-1].start < 1:
            continue
        out.append(it)
    if out and out[0].start <= 15:          # перший трек — з самого початку запису
        out[0].start = 0.0
    return out, skipped


def fmt(sec: float) -> str:
    sec = int(sec)
    h, m, s = sec // 3600, sec // 60 % 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _cue_time(sec: float) -> str:
    frames = int(round(sec * 75))
    return f"{frames // 4500:02d}:{frames // 75 % 60:02d}:{frames % 75:02d}"


def _q(s: str) -> str:
    return s.replace('"', "'").strip()


def cue_text(audio: str, items: list[Item], name_in_cue: str, album: str = "") -> str:
    ext = Path(audio).suffix.lower()
    kind = "MP3" if ext == ".mp3" else "WAVE"
    lines = [MARK, f'TITLE "{_q(album or Path(audio).stem)}"', f'FILE "{_q(name_in_cue)}" {kind}']
    for n, it in enumerate(items, 1):
        lines.append(f"  TRACK {n:02d} AUDIO")
        lines.append(f'    TITLE "{_q(it.title)}"')
        if it.artist:
            lines.append(f'    PERFORMER "{_q(it.artist)}"')
        lines.append(f"    INDEX 01 {_cue_time(it.start)}")
    return "\n".join(lines) + "\n"


def side_cue(audio: str) -> Path:
    return Path(audio).with_suffix(".cue")


def existing(audio: str) -> Path | None:
    """Розбивка, яку зробила Платівка (поруч чи в теці налаштувань). Чужі .cue не чіпаємо."""
    for p in (side_cue(audio), data_cue(audio)):
        try:
            if p.is_file() and p.read_text("utf-8", errors="replace").startswith(MARK):
                return p
        except OSError:
            pass
    return None


def foreign_cue(audio: str) -> bool:
    """Поруч уже лежить .cue, який зробила не Платівка (наприклад, від альбому) — його не перезаписуємо."""
    p = side_cue(audio)
    try:
        return p.is_file() and not p.read_text("utf-8", errors="replace").startswith(MARK)
    except OSError:
        return False


def save(audio: str, items: list[Item], album: str = "") -> Path:
    """Записати розбивку. Поруч із файлом, якщо можна, інакше — у теку налаштувань."""
    if len(items) < 2:
        raise ValueError("need at least two tracks")
    old = existing(audio)
    side = side_cue(audio)
    if not foreign_cue(audio):
        try:
            side.write_text(cue_text(audio, items, Path(audio).name, album), "utf-8")
            if old and old != side:
                old.unlink(missing_ok=True)
            return side
        except OSError:
            pass
    dest = data_cue(audio)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(cue_text(audio, items, os.path.abspath(audio), album), "utf-8")
    return dest


def remove(audio: str) -> bool:
    p = existing(audio)
    if not p:
        return False
    try:
        p.unlink()
        return True
    except OSError:
        return False


def read_back(audio: str) -> str:
    """Збережена розбивка назад у текст «0:00 Виконавець — Назва» — щоб поправити."""
    p = existing(audio)
    if not p:
        return ""
    from .core import parse_cue
    d = parse_cue(str(p)).get(audio) or next(iter(parse_cue(str(p)).values()), None)
    if not d:
        return ""
    rows = []
    for n in sorted(d["tracks"]):
        t = d["tracks"][n]
        who = f"{t['performer']} — " if t["performer"] else ""
        rows.append(f"{fmt(t['start'])} {who}{t['title']}")
    return "\n".join(rows)
