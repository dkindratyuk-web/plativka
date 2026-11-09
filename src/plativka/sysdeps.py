"""Усе, що відрізняється між macOS, Linux і Windows: шляхи, пошук mpv, сповіщення."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")
OS_NAME = "macOS" if IS_MAC else "Windows" if IS_WIN else "Linux"
FROZEN = bool(getattr(sys, "frozen", False))  # зібрано PyInstaller-ом (DMG / інсталятор)


def config_dir() -> Path:
    if IS_WIN:
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "Plativka"
    if IS_LINUX and os.environ.get("XDG_CONFIG_HOME"):
        return Path(os.environ["XDG_CONFIG_HOME"]) / "plativka"
    return Path.home() / ".config" / "plativka"


def cache_dir() -> Path:
    if IS_WIN:
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "Plativka" / "cache"
    if IS_LINUX and os.environ.get("XDG_CACHE_HOME"):
        return Path(os.environ["XDG_CACHE_HOME"]) / "plativka"
    return Path.home() / ".cache" / "plativka"


def app_dir() -> Path | None:
    """Тека встановленої програми (для вкладених mpv, іконок). None — запуск із вихідного коду."""
    if FROZEN:
        return Path(sys.executable).resolve().parent
    return None


def find_mpv() -> str | None:
    env = os.environ.get("PLATIVKA_MPV")
    if env and os.path.exists(env):
        return env
    base = app_dir()
    if base is not None:
        for c in (base / "mpv" / "mpv.exe", base / "mpv.exe", base / "mpv" / "mpv",
                  base.parent / "Resources" / "mpv" / "mpv"):
            if c.exists():
                return str(c)
    exe = shutil.which("mpv")
    if exe:
        return exe
    for c in ("/opt/homebrew/bin/mpv", "/usr/local/bin/mpv", "/usr/bin/mpv"):
        if os.path.exists(c):
            return c
    return None


def mpv_install_hint() -> str | None:
    """Команда встановлення mpv для цієї системи; None — якщо mpv має бути в інсталяторі."""
    if FROZEN:
        return None
    if IS_MAC:
        return "brew install mpv"
    if IS_WIN:
        return "winget install mpv"
    try:
        osr = Path("/etc/os-release").read_text()
    except OSError:
        osr = ""
    low = osr.lower()
    if "arch" in low or "manjaro" in low or "endeavour" in low or "cachyos" in low:
        return "sudo pacman -S mpv"
    if "fedora" in low or "rhel" in low or "centos" in low:
        return "sudo dnf install mpv"
    if "suse" in low:
        return "sudo zypper install mpv"
    return "sudo apt install mpv"


def icon_path() -> str | None:
    for base in filter(None, (app_dir(), Path(__file__).resolve().parent)):
        for c in (base / "assets" / "icon.png", base / "icon.png"):
            if c.exists():
                return str(c)
    return None


def in_kitty() -> bool:
    """Платівка працює у вікні kitty (так запускає DMG і скрипт для Linux)."""
    return bool(os.environ.get("KITTY_WINDOW_ID")) and os.environ.get("TERM") == "xterm-kitty"


def resize_rows_seq(rows: int, cols: int) -> str:
    """Escape-послідовність, що змінює висоту вікна термінала до `rows` рядків.

    kitty: команда керування resize-os-window (у вікні Платівки дозволено лише її).
    Термінал macOS, iTerm2, xterm та інші: стандартний код xterm «CSI 8 ; рядки ; стовпці t».
    """
    if in_kitty():
        import json
        cmd = {"cmd": "resize-os-window", "version": [0, 45, 0], "no_response": True,
               "payload": {"self": True, "action": "resize", "unit": "cells", "width": 0, "height": int(rows)}}
        return "\x1bP@kitty-cmd" + json.dumps(cmd) + "\x1b\\"
    return f"\x1b[8;{int(rows)};{int(cols)}t"


def kitty_notification(title: str, body: str, image: bytes | None = None, ident: str = "plativka") -> str:
    """Escape-послідовність OSC 99: kitty сам показує системне сповіщення, з обкладинкою.

    На macOS сповіщення приходить від «Платівки» (а не від «Редактора скриптів»),
    і праворуч у ньому — обкладинка альбому.
    """
    import base64

    def b64(x) -> str:
        return base64.b64encode(x if isinstance(x, bytes) else x.encode("utf-8")).decode("ascii")

    head = f"i={ident}:f={b64('Plativka')}:s={b64('silent')}:o=always"
    out = [f"\x1b]99;{head}:d=0:e=1:p=title;{b64(title)}\x1b\\"]
    if image:
        data = b64(image)
        for k in range(0, len(data), 4096):
            out.append(f"\x1b]99;i={ident}:d=0:e=1:p=icon;{data[k:k + 4096]}\x1b\\")
    out.append(f"\x1b]99;i={ident}:d=1:e=1:p=body;{b64(body)}\x1b\\")
    return "".join(out)


def system_notify(title: str, body: str, sub: str = "", image: str | None = None) -> bool:
    """Системне сповіщення. True — показано (або передано системі)."""
    try:
        if IS_MAC:
            script = ["-e", "on run argv",
                      "-e", "display notification (item 2 of argv) with title (item 1 of argv) "
                            "subtitle (item 3 of argv)",
                      "-e", "end run"]
            subprocess.run(["osascript", *script, title, body, sub], timeout=5,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        if IS_LINUX and shutil.which("notify-send"):
            args = ["notify-send", "-a", "Plativka", "-t", "4000"]
            ic = image or icon_path()
            if ic:
                args += ["-i", ic]
            subprocess.run([*args, title, body + (f"\n{sub}" if sub else "")], timeout=5,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception:
        pass
    return False  # Windows: сповіщення показує іконка в треї


def can_system_notify() -> bool:
    return IS_MAC or IS_WIN or (IS_LINUX and shutil.which("notify-send") is not None)
