"""Windows: власне вікно консолі (сховати/показати/згорнуто?), закриття хрестиком, «завдання» для mpv."""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_u32 = ctypes.WinDLL("user32", use_last_error=True)

_k32.GetConsoleWindow.restype = wintypes.HWND
_u32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
_u32.IsIconic.argtypes = (wintypes.HWND,)
_u32.IsWindowVisible.argtypes = (wintypes.HWND,)
_u32.SetForegroundWindow.argtypes = (wintypes.HWND,)

SW_HIDE, SW_RESTORE = 0, 9


# ── «завдання»: mpv завершується разом із плеєром, навіть якщо плеєр вбито ──
class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class _BASIC_LIMIT(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD)]


class _EXT_LIMIT(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _BASIC_LIMIT), ("IoInfo", _IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


_job = None


def kill_with_parent(pid: int) -> None:
    global _job
    try:
        if _job is None:
            _k32.CreateJobObjectW.restype = wintypes.HANDLE
            _job = _k32.CreateJobObjectW(None, None)
            info = _EXT_LIMIT()
            info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            _k32.SetInformationJobObject(_job, 9, ctypes.byref(info), ctypes.sizeof(info))
        _k32.OpenProcess.restype = wintypes.HANDLE
        h = _k32.OpenProcess(0x0100 | 0x0001, False, pid)  # PROCESS_SET_QUOTA | PROCESS_TERMINATE
        if h:
            _k32.AssignProcessToJobObject(_job, h)
            _k32.CloseHandle(h)
    except Exception:
        pass


# ── вікно плеєра ──
def in_windows_terminal() -> bool:
    """У Windows Terminal вікно консолі «віртуальне»: сховати/показати його неможливо."""
    return bool(os.environ.get("WT_SESSION"))


def own_window() -> bool:
    return not in_windows_terminal() and bool(_k32.GetConsoleWindow())


def hide_window() -> bool:
    hwnd = _k32.GetConsoleWindow()
    if not hwnd or in_windows_terminal():
        return False
    _u32.ShowWindow(hwnd, SW_HIDE)
    return True


def show_window() -> None:
    hwnd = _k32.GetConsoleWindow()
    if hwnd:
        _u32.ShowWindow(hwnd, SW_RESTORE)
        _u32.SetForegroundWindow(hwnd)


def is_minimized() -> bool:
    hwnd = _k32.GetConsoleWindow()
    return bool(hwnd) and bool(_u32.IsIconic(hwnd)) and bool(_u32.IsWindowVisible(hwnd))


# ── закриття вікна хрестиком ──
_HANDLER = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
_keep = []


def on_close(callback) -> None:
    """Хрестик / вихід із системи: Windows дає кілька секунд — зберігаємо стан і виходимо."""
    def handler(ctrl_type):
        if ctrl_type in (2, 5, 6):  # CLOSE, LOGOFF, SHUTDOWN
            try:
                callback()
            except Exception:
                pass
            return True
        return False
    h = _HANDLER(handler)
    _keep.append(h)
    _k32.SetConsoleCtrlHandler(h, True)


# ── розмір вікна консолі (компактний вигляд згортається до смужки) ──
class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


_u32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.c_void_p)
_u32.GetClientRect.argtypes = (wintypes.HWND, ctypes.c_void_p)
_u32.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, wintypes.UINT)


def resize_rows(rows: int, current_rows: int) -> bool:
    """Змінити висоту власного вікна консолі до `rows` рядків (ширина та сама).

    Працює для класичного вікна консолі (conhost), у якому Платівку відкриває ярлик.
    Windows Terminal так змінювати не дозволяє — тоді нічого не робимо.
    """
    if not own_window() or current_rows <= 0 or rows <= 0:
        return False
    try:
        hwnd = _k32.GetConsoleWindow()
        win, cli = _RECT(), _RECT()
        if not (_u32.GetWindowRect(hwnd, ctypes.byref(win)) and _u32.GetClientRect(hwnd, ctypes.byref(cli))):
            return False
        row_px = (cli.bottom - cli.top) / current_rows
        if row_px <= 0:
            return False
        frame = (win.bottom - win.top) - (cli.bottom - cli.top)
        height = int(round(rows * row_px)) + frame
        SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE = 0x2, 0x4, 0x10
        return bool(_u32.SetWindowPos(hwnd, None, 0, 0, win.right - win.left, height,
                                      SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE))
    except Exception:
        return False
