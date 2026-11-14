"""Скіни віконної версії: «Платівка» (класичний), «macOS» і «Windows 11».

Розташування елементів однакове в усіх трьох — змінюються кнопки, іконки, повзунки,
заокруглення й прозорість. Колір обкладинки лишається акцентом у кожному скіні.
Тут — іконки в стилі SF Symbols / Fluent і напівпрозорий фон вікна на macOS.
"""
from __future__ import annotations

import os

from . import sysdeps
from .core import log

SKINS = ("classic", "mac", "fluent")

# 16×16, {c} — колір, {w} — товщина лінії. Спільні для обох «системних» скінів,
# транспорт у Fluent — свій (риска + трикутник, як у медіаплеєрі Windows).
_SVG = {
    "prev": '<path d="M7.6 3.2v9.6L1.2 8zM14.8 3.2v9.6L8.4 8z" fill="{c}"/>',
    "next": '<path d="M1.2 3.2v9.6L7.6 8zM8.4 3.2v9.6L14.8 8z" fill="{c}"/>',
    "play": '<path d="M4.2 2.6v10.8c0 .5.5.8.9.5l8.4-5.4a.6.6 0 0 0 0-1L5.1 2.1c-.4-.3-.9 0-.9.5z" fill="{c}"/>',
    "pause": '<rect x="3.4" y="2.4" width="3.2" height="11.2" rx="1" fill="{c}"/>'
             '<rect x="9.4" y="2.4" width="3.2" height="11.2" rx="1" fill="{c}"/>',
    "stop": '<rect x="3" y="3" width="10" height="10" rx="2" fill="{c}"/>',
    "eject": '<path d="M1.5 4.5V12a1 1 0 0 0 1 1h11a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1H8L6.5 3h-4a1 1 0 0 0-1 1z" '
             'fill="none" stroke="{c}" stroke-width="{w}" stroke-linejoin="round"/>',
    "menu": '<circle cx="3" cy="8" r="1.2" fill="{c}"/><circle cx="8" cy="8" r="1.2" fill="{c}"/>'
            '<circle cx="13" cy="8" r="1.2" fill="{c}"/>',
    "pin": '<path d="M5.5 1.8h5l-.7 4.4 2.2 2.3v1.2H4V8.5l2.2-2.3z" fill="none" stroke="{c}" stroke-width="{w}" '
           'stroke-linejoin="round"/><path d="M8 9.8v4.6" stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>',
    "up": '<path d="M3.5 10.5 8 6l4.5 4.5" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" '
          'stroke-linejoin="round"/>',
    "down": '<path d="M3.5 6 8 10.5 12.5 6" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" '
            'stroke-linejoin="round"/>',
    "shuffle": '<path d="M1.5 4.5h2.5c3 0 4 7 7 7h3M1.5 11.5H4c1.2 0 2-1 2.7-2.3M14.5 4.5H12c-1.2 0-2 1-2.7 2.3'
               'M12.5 2.5l2 2-2 2M12.5 9.5l2 2-2 2" fill="none" stroke="{c}" stroke-width="{w}" '
               'stroke-linecap="round" stroke-linejoin="round"/>',
    "repeat": '<path d="M2.5 7.5V6a2 2 0 0 1 2-2h9M11.5 2l2 2-2 2M13.5 8.5V10a2 2 0 0 1-2 2h-9M4.5 14l-2-2 2-2" '
              'fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>',
    "repeat1": '<path d="M2.5 7.5V6a2 2 0 0 1 2-2h9M11.5 2l2 2-2 2M13.5 8.5V10a2 2 0 0 1-2 2h-9M4.5 14l-2-2 2-2" '
               'fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
               '<path d="M7.3 7.1 8.4 6.3v3.6" fill="none" stroke="{c}" stroke-width="1.2" stroke-linecap="round" '
               'stroke-linejoin="round"/>',
    "bell": '<path d="M8 1.8a4 4 0 0 0-4 4v2.6L2.8 10.6h10.4L12 8.4V5.8a4 4 0 0 0-4-4zM6.3 12.6a1.8 1.8 0 0 0 3.4 0" '
            'fill="none" stroke="{c}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>',
    "bell_off": '<path d="M8 1.8a4 4 0 0 0-4 4v2.6L2.8 10.6h10.4L12 8.4V5.8a4 4 0 0 0-4-4zM6.3 12.6a1.8 1.8 0 0 0 '
                '3.4 0M2 2l12 12" fill="none" stroke="{c}" stroke-width="{w}" stroke-linejoin="round" '
                'stroke-linecap="round"/>',
    "phone": '<rect x="4.5" y="1.5" width="7" height="13" rx="1.8" fill="none" stroke="{c}" stroke-width="{w}"/>'
             '<path d="M7 12.2h2" stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>',
    "speaker": '<path d="M2 6h2.5L8 3v10L4.5 10H2z" fill="{c}"/><path d="M10.5 5.8a2.8 2.8 0 0 1 0 4.4" fill="none" '
               'stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>',
    "mute": '<path d="M2 6h2.5L8 3v10L4.5 10H2z" fill="{c}"/><path d="M10.5 6l3.5 4M14 6l-3.5 4" fill="none" '
            'stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>',
}
_FLUENT = {
    "prev": '<rect x="2" y="2.5" width="1.6" height="11" rx=".8" fill="{c}"/>'
            '<path d="M13.5 3.2v9.6a.8.8 0 0 1-1.2.7L5.6 8.7a.8.8 0 0 1 0-1.4l6.7-4.8a.8.8 0 0 1 1.2.7z" fill="{c}"/>',
    "next": '<rect x="12.4" y="2.5" width="1.6" height="11" rx=".8" fill="{c}"/>'
            '<path d="M2.5 3.2v9.6a.8.8 0 0 0 1.2.7l6.7-4.8a.8.8 0 0 0 0-1.4L3.7 2.5a.8.8 0 0 0-1.2.7z" fill="{c}"/>',
    "stop": '<rect x="2.5" y="2.5" width="11" height="11" rx="1.5" fill="{c}"/>',
}

_cache: dict = {}


def line_icon(kind: str, color: str, family: str = "mac", size: int = 16):
    """QIcon з векторного малюнка. None — якщо такої іконки немає чи немає QtSvg."""
    key = (kind, color, family, size)
    if key in _cache:
        return _cache[key]
    body = (_FLUENT.get(kind) if family == "fluent" else None) or _SVG.get(kind)
    if body is None:
        return None
    try:
        from PySide6.QtCore import QByteArray, QRectF, Qt
        from PySide6.QtGui import QIcon, QPainter, QPixmap
        from PySide6.QtSvg import QSvgRenderer
    except ImportError:
        return None
    w = "1.15" if family == "fluent" else "1.45"
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">{body.format(c=color, w=w)}</svg>'
    r = QSvgRenderer(QByteArray(svg.encode()))
    dpr = 3
    pix = QPixmap(size * dpr, size * dpr)
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    r.render(p, QRectF(0, 0, size, size))
    p.end()
    ic = QIcon(pix)
    _cache[key] = ic
    return ic


# ── macOS: матеріал вікна (NSVisualEffectView) під усім вмістом ──
def vibrancy_supported() -> bool:
    return sysdeps.IS_MAC and not os.environ.get("PLATIVKA_NO_VIBRANCY")


def set_vibrancy(widget, on: bool, dark: bool) -> bool:
    """Увімкнути/вимкнути розмиття шпалер під вікном. True — працює."""
    if not vibrancy_supported():
        return False
    try:
        import objc
        from AppKit import NSAppearance, NSVisualEffectView
        view = objc.objc_object(c_void_p=int(widget.winId()))
        win = view.window()
        if win is None:
            return False
        content = win.contentView()
        frame = content.superview()
        vev = getattr(widget, "_plativka_vev", None)
        if vev is None:
            if not on:
                return False
            vev = NSVisualEffectView.alloc().initWithFrame_(frame.bounds())
            vev.setAutoresizingMask_(2 | 16)          # NSViewWidthSizable | NSViewHeightSizable
            vev.setBlendingMode_(0)                   # BehindWindow — шпалери й вікна позаду
            vev.setMaterial_(7)                       # Sidebar — як бічні панелі Finder і Музики
            vev.setState_(0)                          # як у системи: тьмяніє, коли вікно неактивне
            frame.addSubview_positioned_relativeTo_(vev, -1, content)   # NSWindowBelow
            widget._plativka_vev = vev
        vev.setAppearance_(NSAppearance.appearanceNamed_("NSAppearanceNameDarkAqua" if dark
                                                         else "NSAppearanceNameAqua"))
        vev.setHidden_(not on)
        return on
    except Exception as e:
        log(f"vibrancy: {e}")
        return False
