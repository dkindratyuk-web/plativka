"""Копіювання списку відтворення на флешку / в теку: пронумеровані імена, щоб магнітола
в машині чи старий плеєр грали в тому самому порядку. Нічого не перезаписує без дозволу."""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field

from .core import is_cue_path, real_path

_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(s: str, limit: int = 120) -> str:
    """Ім'я, яке приймуть FAT32/exFAT/NTFS і будь-яка магнітола."""
    s = _BAD.sub("_", s).strip().rstrip(". ")
    s = re.sub(r"\s+", " ", s)
    return (s[:limit].rstrip(". ") or "track")


@dataclass
class CopyPlan:
    dest: str
    items: list[tuple[str, str]] = field(default_factory=list)   # (звідки, ім'я в теці призначення)
    total: int = 0
    existing: list[str] = field(default_factory=list)
    free: int | None = None

    @property
    def fits(self) -> bool:
        return self.free is None or self.total <= self.free


def plan_copy(paths, track, dest: str, numbered: bool = True) -> CopyPlan:
    """track(path) -> Track. Доріжки з CUE копіюються цілим файлом-образом разом із .cue
    під своїми іменами (інакше .cue не знайде свій файл)."""
    plan = CopyPlan(dest=dest)
    seen, names = set(), set()
    plain = []
    for p in paths:
        src = real_path(p)
        if src in seen:
            continue
        seen.add(src)
        if is_cue_path(p):
            for f in (src, os.path.splitext(src)[0] + ".cue"):
                if os.path.isfile(f):
                    plan.items.append((f, os.path.basename(f)))
        else:
            plain.append(p)
    width = max(2, len(str(len(plain))))
    out = []
    for n, p in enumerate(plain, 1):
        t = track(p)
        ext = os.path.splitext(p)[1].lower()
        base = f"{t.artist} - {t.title}" if t.artist and t.title else (t.title or os.path.splitext(os.path.basename(p))[0])
        name = safe_name((f"{n:0{width}d} - " if numbered else "") + base) + ext
        stem, k = name[:-len(ext)] if ext else name, 2
        while name.lower() in names:
            name = f"{stem} ({k}){ext}"
            k += 1
        names.add(name.lower())
        out.append((p, name))
    plan.items = out + plan.items
    for src, name in plan.items:
        try:
            plan.total += os.path.getsize(src)
        except OSError:
            pass
        if os.path.exists(os.path.join(dest, name)):
            plan.existing.append(name)
    try:
        plan.free = shutil.disk_usage(dest).free
    except OSError:
        plan.free = None
    return plan


def run_copy(plan: CopyPlan, replace: bool = False, progress=None, cancelled=None) -> tuple[int, int, list[str]]:
    """Копіює; повертає (скопійовано, пропущено, помилки). Пише спершу в .part, потім
    перейменовує — обірвана флешка не лишить «цілого» на вигляд, але битого файлу."""
    done = skipped = 0
    errors: list[str] = []
    existing = {n.lower() for n in plan.existing}
    os.makedirs(plan.dest, exist_ok=True)
    for i, (src, name) in enumerate(plan.items):
        if cancelled and cancelled():
            break
        dst = os.path.join(plan.dest, name)
        if name.lower() in existing and not replace:
            skipped += 1
        else:
            tmp = dst + ".part"
            try:
                shutil.copyfile(src, tmp)
                os.replace(tmp, dst)
                done += 1
            except OSError as e:
                errors.append(f"{name}: {e.strerror or e}")
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        if progress:
            progress(i + 1, len(plan.items), name)
    return done, skipped, errors
