"""Системна гучність: смужка гучності плеєра — дзеркало гучності системи.

Клавіші гучності (F11/F12 на Mac, клавіші на клавіатурах і навушниках) керують гучністю
системи. Щоб у плеєрі не було «другої» гучності, вона завжди 100 %, а смужка показує
й змінює системну. Якщо системну гучність прочитати не вдалося, плеєр повертається
до власної гучності (mpv).
"""
from __future__ import annotations

import re
import shutil
import subprocess

from . import sysdeps


def _run(args, timeout=2.0) -> str | None:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                           creationflags=0x08000000 if sysdeps.IS_WIN else 0)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


class _Mac:
    name = "macOS"

    def get(self):
        out = _run(["osascript", "-e", "set v to get volume settings",
                    "-e", "return (output volume of v as text) & \",\" & (output muted of v as text)"])
        if not out or "missing" in out:
            return None
        vol, muted = out.strip().split(",")
        return int(vol), muted.strip() == "true"

    def set(self, v: int):
        _run(["osascript", "-e", f"set volume output volume {int(v)} without output muted"])


class _Wpctl:
    name = "PipeWire"

    def get(self):
        out = _run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
        m = re.search(r"Volume:\s*([\d.]+)", out or "")
        if not m:
            return None
        return int(round(float(m.group(1)) * 100)), "MUTED" in out

    def set(self, v: int):
        _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"])
        _run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{max(0, min(100, int(v))) / 100:.2f}"])


class _Pactl:
    name = "PulseAudio"

    def get(self):
        out = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
        m = re.search(r"(\d+)%", out or "")
        if not m:
            return None
        mute = _run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"]) or ""
        return int(m.group(1)), "yes" in mute

    def set(self, v: int):
        _run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"])
        _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{max(0, min(100, int(v)))}%"])


class _Win:
    name = "Windows"

    def __init__(self):
        self._ep = None

    def _endpoint(self):
        if self._ep is None:
            import comtypes  # noqa: F401
            from pycaw.pycaw import AudioUtilities
            spk = AudioUtilities.GetSpeakers()
            ep = getattr(spk, "EndpointVolume", None)
            if ep is None:  # старі версії pycaw
                from ctypes import POINTER, cast
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import IAudioEndpointVolume
                iface = spk.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                ep = cast(iface, POINTER(IAudioEndpointVolume))
            self._ep = ep
        return self._ep

    def get(self):
        try:
            ep = self._endpoint()
            return int(round(ep.GetMasterVolumeLevelScalar() * 100)), bool(ep.GetMute())
        except Exception:
            self._ep = None
            return None

    def set(self, v: int):
        try:
            ep = self._endpoint()
            ep.SetMute(0, None)
            ep.SetMasterVolumeLevelScalar(max(0, min(100, int(v))) / 100, None)
        except Exception:
            self._ep = None


def detect():
    """Повертає об'єкт із методами get() -> (гучність, вимкнено) | None і set(гучність), або None."""
    cands = []
    if sysdeps.IS_MAC:
        cands = [_Mac()]
    elif sysdeps.IS_WIN:
        cands = [_Win()]
    elif sysdeps.IS_LINUX:
        if shutil.which("wpctl"):
            cands.append(_Wpctl())
        if shutil.which("pactl"):
            cands.append(_Pactl())
    for c in cands:
        try:
            if c.get() is not None:
                return c
        except Exception:
            pass
    return None


def init_thread():
    """Windows: кожен потік, що працює з гучністю, має ініціалізувати COM."""
    if sysdeps.IS_WIN:
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            pass
