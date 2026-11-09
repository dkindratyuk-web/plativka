"""Windows: сповіщення «Зараз грає» з обкладинкою (системний toast Windows 10/11).

Toast показується від імені ярлика «Plativka» в меню «Пуск» — інсталятор задає йому
AppUserModelID нижче. Без такого ярлика (запуск із pip) Windows toast не покаже,
тож тоді повертаємо False, і сповіщення показує іконка в треї (без обкладинки).
"""
from __future__ import annotations

import os
from pathlib import Path
from xml.sax.saxutils import escape

AUMID = "dkindratyuk.Plativka"
SHORTCUT = ("Plativka", "Plativka.lnk")   # тека й ярлик у меню «Пуск», які створює інсталятор


def use_desktop_app():
    """Віконна версія має свій ярлик і свій AppUserModelID."""
    global AUMID, SHORTCUT, _ok
    AUMID = "dkindratyuk.Plativka.Desktop"
    SHORTCUT = ("Plativka Desktop", "Plativka Desktop.lnk")
    _ok = None


def _shortcut_exists() -> bool:
    for base in (os.environ.get("APPDATA"), os.environ.get("PROGRAMDATA")):
        if base and (Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
                     / SHORTCUT[0] / SHORTCUT[1]).exists():
            return True
    return False


_ok: bool | None = None


def available() -> bool:
    global _ok
    if _ok is None:
        try:
            from winrt.windows.data.xml.dom import XmlDocument  # noqa: F401
            from winrt.windows.ui.notifications import ToastNotificationManager  # noqa: F401
            _ok = _shortcut_exists()
        except Exception:
            _ok = False
    return _ok


def show(title: str, body: str, image: str | None = None) -> bool:
    global _ok
    if not available():
        return False
    try:
        from winrt.windows.data.xml.dom import XmlDocument
        from winrt.windows.ui.notifications import ToastNotification, ToastNotificationManager
        img = ""
        if image and Path(image).exists():
            img = f'<image placement="appLogoOverride" src="{escape(Path(image).resolve().as_uri())}"/>'
        lines = "".join(f"<text>{escape(x)}</text>" for x in body.split("\n") if x)
        xml = (f'<toast><visual><binding template="ToastGeneric"><text>{escape(title)}</text>'
               f'{lines}{img}</binding></visual><audio silent="true"/></toast>')
        doc = XmlDocument()
        doc.load_xml(xml)
        toast = ToastNotification(doc)
        toast.tag = "now-playing"   # новий трек замінює попереднє сповіщення, а не накопичується
        toast.group = "plativka"
        ToastNotificationManager.create_toast_notifier(AUMID).show(toast)
        return True
    except Exception:
        _ok = False
        return False
