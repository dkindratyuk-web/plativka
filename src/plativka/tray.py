"""Іконка в треї Windows: грати/пауза, наступний, попередній, показати плеєр, згортати в трей, вихід."""
from __future__ import annotations

import threading

from PIL import Image

from .i18n import _


class Tray:
    def __init__(self, app, image: Image.Image):
        import pystray  # імпорт тут: на macOS/Linux пакет не потрібен
        self.app = app
        self._pystray = pystray
        M, I = pystray.Menu, pystray.MenuItem
        call = self._call
        menu = M(
            I(_("Показати плеєр"), lambda: call(app.show_from_tray), default=True),
            M.SEPARATOR,
            I(_("Грати / пауза"), lambda: call(app.toggle_from_tray)),
            I(_("Наступний трек"), lambda: call(app.next_from_tray)),
            I(_("Попередній трек"), lambda: call(app.prev_from_tray)),
            M.SEPARATOR,
            I(_("Згортати в трей"), lambda: call(app.toggle_minimize_to_tray),
              checked=lambda item: app.minimize_to_tray),
            M.SEPARATOR,
            I(_("Вийти з Платівки"), lambda: call(app.quit_from_tray)),
        )
        self.icon = pystray.Icon("plativka", image, _("Платівка"), menu)
        self._thread = None

    def _call(self, fn):
        # меню працює у своєму потоці — передаємо дію в потік інтерфейсу
        self.app.call_from_thread(fn)

    def start(self):
        self._thread = threading.Thread(target=self.icon.run, daemon=True)
        self._thread.start()

    def set_title(self, text: str):
        try:
            self.icon.title = text[:120]
        except Exception:
            pass

    def set_image(self, image: Image.Image):
        try:
            self.icon.icon = image
        except Exception:
            pass

    def notify(self, title: str, body: str):
        try:
            self.icon.notify(body, title)
        except Exception:
            pass

    def stop(self):
        try:
            self.icon.stop()
        except Exception:
            pass
