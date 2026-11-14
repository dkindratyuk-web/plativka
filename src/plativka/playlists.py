"""Збережені списки відтворення: звичайні файли M3U8 у теці налаштувань.

M3U8 — щоб списки відкривалися й в інших плеєрах (VLC, foobar2000, Музика…).
Треки з CUE (файл#trackN) зберігаються як є: їх розуміє лише Платівка.
Видалений список іде в Кошик, а не зникає назавжди.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .core import CONF_DIR, log

DIR = CONF_DIR / "playlists"
EXT = ".m3u8"
_BAD = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def clean_name(name: str) -> str:
    """Назва, яку можна зробити назвою файлу на будь-якій системі."""
    n = _BAD.sub(" ", name or "")
    n = re.sub(r"\s+", " ", n).strip(" .")
    return n[:80]


def path_for(name: str, folder: Path | None = None) -> Path:
    return (folder or DIR) / (clean_name(name) + EXT)


def list_all(folder: Path | None = None) -> list[tuple[str, Path]]:
    """[(назва, файл)] за абеткою."""
    d = folder or DIR
    try:
        files = [f for f in d.iterdir() if f.suffix.lower() in (".m3u8", ".m3u") and f.is_file()]
    except OSError:
        return []
    return sorted(((f.stem, f) for f in files), key=lambda x: x[0].casefold())


def save(name: str, paths: list[str], track=None, folder: Path | None = None) -> Path:
    """track(path) → Track — для рядків #EXTINF (тривалість і назва для інших плеєрів)."""
    name = clean_name(name)
    if not name:
        raise ValueError("empty name")
    d = folder or DIR
    d.mkdir(parents=True, exist_ok=True)
    lines = ["#EXTM3U", f"#PLAYLIST:{name}"]
    for p in paths:
        if track is not None:
            try:
                t = track(p)
                lines.append(f"#EXTINF:{int(t.length or -1)},{t.display}")
            except Exception:
                pass
        lines.append(p)
    dest = path_for(name, d)
    tmp = dest.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n", "utf-8")
    os.replace(tmp, dest)
    return dest


def load(file: str | Path) -> list[str]:
    """Шляхи з M3U/M3U8. Відносні — від теки самого списку. Порожні рядки й коментарі пропускаються."""
    f = Path(file)
    raw = f.read_bytes()
    for enc in ("utf-8-sig", "cp1251"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("file://"):
            from urllib.parse import unquote, urlparse
            line = unquote(urlparse(line).path)
            if os.name == "nt" and re.match(r"^/[A-Za-z]:", line):
                line = line[1:]
        p = line if os.path.isabs(line) else str((f.parent / line).resolve())
        out.append(p)
    return out


def rename(old: str, new: str, folder: Path | None = None) -> Path:
    src, dst = path_for(old, folder), path_for(new, folder)
    if not clean_name(new):
        raise ValueError("empty name")
    if dst.exists() and dst != src:
        raise FileExistsError(dst.name)
    os.replace(src, dst)
    # назва всередині файлу теж нова
    try:
        text = dst.read_text("utf-8")
        dst.write_text(re.sub(r"^#PLAYLIST:.*$", f"#PLAYLIST:{clean_name(new)}", text, count=1, flags=re.M), "utf-8")
    except OSError:
        pass
    return dst


def delete(name: str, folder: Path | None = None) -> bool:
    f = path_for(name, folder)
    try:
        from send2trash import send2trash
        send2trash(str(f))
        return True
    except Exception as e:
        log(f"список: не вдалося в Кошик ({e}), видаляю")
        try:
            f.unlink()
            return True
        except OSError:
            return False
