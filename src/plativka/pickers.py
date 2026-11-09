"""Системне вікно вибору теки: Finder на macOS, «Вибір папки» на Windows, GNOME/KDE на Linux.

choose_folders(title) -> list[str]  — обрані теки ([] — користувач скасував)
                      -> None       — системного вікна немає, треба показати вибір у терміналі
Виклик блокує потік, тож його запускають у фоновому потоці.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import sysdeps


def _start_dir() -> str:
    music = Path.home() / "Music"
    return str(music if music.is_dir() else Path.home())


def _mac(title: str):
    script = [
        "-e", "on run argv",
        "-e", "activate",
        "-e", "set fs to choose folder with prompt (item 1 of argv) default location "
              "(POSIX file (item 2 of argv)) with multiple selections allowed",
        "-e", "set out to \"\"",
        "-e", "repeat with f in fs",
        "-e", "set out to out & POSIX path of f & linefeed",
        "-e", "end repeat",
        "-e", "return out",
        "-e", "end run",
    ]
    r = subprocess.run(["osascript", *script, title, _start_dir()], capture_output=True, text=True)
    if r.returncode != 0:
        return [] if "-128" in r.stderr else None  # -128 — «Скасувати»
    return [p.rstrip("/") or "/" for p in r.stdout.splitlines() if p.strip()]


_PS = r"""
Add-Type -AssemblyName System.Windows.Forms
$d = New-Object System.Windows.Forms.FolderBrowserDialog
$d.Description = $env:PLATIVKA_DLG_TITLE
$d.SelectedPath = $env:PLATIVKA_DLG_DIR
$d.ShowNewFolderButton = $false
try { $d.UseDescriptionForTitle = $true } catch {}
$owner = New-Object System.Windows.Forms.Form -Property @{TopMost = $true; ShowInTaskbar = $false}
if ($d.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  Write-Output $d.SelectedPath
}
"""


def _win(title: str):
    try:
        env = dict(os.environ, PLATIVKA_DLG_TITLE=title, PLATIVKA_DLG_DIR=_start_dir())
        r = subprocess.run(["powershell", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
                            "-Command", _PS], env=env,
                           capture_output=True, timeout=600, creationflags=0x08000000)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    out = r.stdout.decode("utf-8", "replace").strip()
    return [out] if out else []


def _linux(title: str):
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return None
    if shutil.which("zenity"):
        r = subprocess.run(["zenity", "--file-selection", "--directory", "--multiple",
                            "--separator=\n", f"--title={title}", f"--filename={_start_dir()}/"],
                           capture_output=True, text=True)
        if r.returncode == 1:
            return []
        if r.returncode == 0:
            return [p for p in r.stdout.splitlines() if p.strip()]
        return None
    if shutil.which("kdialog"):
        r = subprocess.run(["kdialog", "--title", title, "--getexistingdirectory", _start_dir()],
                           capture_output=True, text=True)
        if r.returncode == 1:
            return []
        if r.returncode == 0 and r.stdout.strip():
            return [r.stdout.strip()]
    return None


def available() -> bool:
    if os.environ.get("PLATIVKA_NO_NATIVE_DIALOG"):
        return False
    if sysdeps.IS_MAC or sysdeps.IS_WIN:
        return True
    return bool((os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
                and (shutil.which("zenity") or shutil.which("kdialog")))


def choose_folders(title: str):
    if not available():
        return None
    try:
        if sysdeps.IS_MAC:
            res = _mac(title)
        elif sysdeps.IS_WIN:
            res = _win(title)
        else:
            res = _linux(title)
    except Exception:
        return None
    if res is None:
        return None
    return [p for p in res if os.path.isdir(p)]
