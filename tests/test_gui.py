"""Віконна версія (Qt): відкривається в демо-режимі, перемикає вигляди. Пропускається без PySide6."""
import asyncio
import os

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("qasync")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_desktop_window_views():
    import qasync
    from PySide6.QtWidgets import QApplication
    from plativka import gui

    app = QApplication.instance() or QApplication([])
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    win = gui.MainWindow(demo=True)
    win.show()

    async def run():
        await win.start_player()
        win.add_to_playlist(["/nonexistent/a.mp3", "/nonexistent/b.mp3"], replace=True)
        assert win.table.rowCount() == 2
        win.toggle_view()
        assert win.view == "compact" and not win.clock.isVisible()
        win.toggle_collapsed()
        assert win.collapsed and not win.lists.isVisible()
        win.set_tab("library")             # вкладка розгортає міні-плеєр
        assert not win.collapsed and win.stack.currentIndex() == 1
        win.toggle_view()
        assert win.view == "full" and win.clock.isVisible()
        win.cycle_theme()
        # скіни перемикаються на льоту; у компактному вигляді — одна кнопка «грати/пауза»
        for sk in ("mac", "fluent", "classic"):
            win.set_skin(sk, toast=False)
            assert win.skin == sk and win.a_skin[sk].isChecked()
            win.toggle_view()
            assert win.buttons["toggle"].isVisible() and not win.buttons["play"].isVisible()
            assert win.icon_flags["shuffle"].isVisible() and not win.f_shuffle.isVisible()
            win.toggle_view()
            assert win.buttons["play"].isVisible() == (sk == "classic")
        win.set_eq(on=True, gains=[3] * 10, preset="custom")      # еквалайзер: вікно й прапорець «екв»
        win.open_equalizer()
        assert win.f_eq.isVisible() and win.eq_headroom < 0 and win._eq_dialog.on.isChecked()
        win.set_eq(on=False)
        assert not win.f_eq.isVisible() and win.eq_headroom == 0
        h = win.height()
        win.toggle_view()
        win.toggle_view()
        assert win.height() == h           # перемикання вигляду не розтягує вікно
        win.search.setText("b.mp3")
        win.set_tab("playlist")
        win.apply_filter("b")
        await win.player.close()

    with loop:
        loop.run_until_complete(run())
    win.close()
