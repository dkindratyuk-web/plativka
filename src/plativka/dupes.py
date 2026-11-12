"""Пошук дублікатів: однакові файли (байт у байт) і та сама пісня в різних файлах
(той самий виконавець і назва, тривалість ±3 с). Яку копію лишити — вирішує людина;
типово пропонуємо найкращу: улюблену, без втрат, з вищим бітрейтом, частіше слухану."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

from .core import Track, real_path
from .favorites import fingerprint

LOSSLESS = {".flac", ".wav", ".aiff", ".aif", ".ape", ".wv", ".alac"}
LENGTH_TOLERANCE = 3.0


@dataclass
class Group:
    kind: str                         # "file" — однакові файли; "song" — та сама пісня
    paths: list[str] = field(default_factory=list)   # перший — що пропонуємо лишити
    keep: set[str] = field(default_factory=set)

    @property
    def extra(self) -> list[str]:
        return [p for p in self.paths if p not in self.keep]


def _hash(path: str, stop=None) -> str | None:
    h = hashlib.blake2b(digest_size=20)
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                if stop and stop():
                    return None
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def _size(t: Track) -> int:
    if t.size:
        return t.size
    try:
        return os.path.getsize(t.path)
    except OSError:
        return 0


def quality_key(t: Track, favs=None, hist=None):
    ext = os.path.splitext(t.path)[1].lower()
    return (bool(favs and t.path in favs), ext in LOSSLESS, t.bitrate or 0,
            hist.plays(t.path) if hist else 0, -len(t.path))


def find_duplicates(tracks, favs=None, hist=None, progress=None, stop=None) -> list[Group]:
    """tracks — ітерабельні Track. CUE-доріжки (шматки одного файлу) не розглядаємо."""
    ts = {t.path: t for t in tracks if not t.segment and os.path.isfile(real_path(t.path))}
    parent = {p: p for p in ts}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    # 1) однакові файли: спершу розмір, хеш — лише для збігів розміру
    by_size: dict[int, list[str]] = {}
    for p, t in ts.items():
        n = _size(t)
        if n:
            by_size.setdefault(n, []).append(p)
    cands = [ps for ps in by_size.values() if len(ps) > 1]
    total = sum(len(ps) for ps in cands)
    digests: dict[str, str] = {}
    done = 0
    for ps in cands:
        seen: dict[str, str] = {}
        for p in ps:
            if stop and stop():
                return []
            d = _hash(p, stop)
            done += 1
            if progress:
                progress(done, total)
            if d is None:
                continue
            digests[p] = d
            if d in seen:
                union(p, seen[d])
            else:
                seen[d] = p
    # 2) та сама пісня: виконавець + назва, тривалість близька
    by_fp: dict[tuple, list[Track]] = {}
    for t in ts.values():
        fp = fingerprint(t)
        if fp[0] and fp[1]:
            by_fp.setdefault(fp, []).append(t)
    for group in by_fp.values():
        group.sort(key=lambda t: t.length or 0)
        for a, b in zip(group, group[1:]):
            if a.length and b.length and abs(a.length - b.length) <= LENGTH_TOLERANCE:
                union(a.path, b.path)
    clusters: dict[str, list[str]] = {}
    for p in ts:
        clusters.setdefault(find(p), []).append(p)
    out = []
    for ps in clusters.values():
        if len(ps) < 2:
            continue
        ps.sort(key=lambda p: quality_key(ts[p], favs, hist), reverse=True)
        same = len({digests.get(p) for p in ps}) == 1 and ps[0] in digests
        out.append(Group("file" if same else "song", ps, {ps[0]}))
    out.sort(key=lambda g: ts[g.paths[0]].display.casefold())
    return out


def total_size(paths) -> int:
    n = 0
    for p in paths:
        try:
            n += os.path.getsize(p)
        except OSError:
            pass
    return n
