"""Інтерфейс у демо-режимі (без звуку): відкривається, клавіші не ламають його, обидві мови."""
import pytest

from plativka import i18n
from plativka.app import Plativka


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [(130, 36), (80, 24)])
async def test_ui_keys_do_not_crash(size):
    app = Plativka(demo=True)
    async with app.run_test(size=size) as pilot:
        await pilot.pause(0.5)
        assert app.main is not None
        for key in ["x", "c", "s", "r", "r", "r", "n", "o", "o", "o", "t", "t", "m", "m", "f2", "f2", "left", "right"]:
            await pilot.press(key)
            await pilot.pause(0.05)
        await pilot.press("j")
        await pilot.pause(0.2)
        await pilot.press("escape")
        await pilot.press("l")
        await pilot.pause(0.2)
        await pilot.press("escape")
        await pilot.pause(0.2)
        assert app.screen is app.main


@pytest.mark.asyncio
@pytest.mark.parametrize("lang", ["uk", "en"])
async def test_ui_both_languages(lang, monkeypatch):
    monkeypatch.setattr(i18n, "LANG", lang)
    app = Plativka(demo=True)
    async with app.run_test(size=(120, 34)) as pilot:
        await pilot.pause(0.5)
        title = app.main.query_one("#pl-win").border_title.lstrip("● ")
        assert title == ("Список відтворення" if lang == "uk" else "Playlist")


@pytest.mark.asyncio
async def test_folders_window_remove_checked_and_all(tmp_path):
    from plativka.app import ConfirmScreen, FoldersScreen
    dirs = []
    for n in "abc":
        d = tmp_path / n
        d.mkdir()
        dirs.append(str(d))
    app = Plativka(demo=True)
    async with app.run_test(size=(120, 34)) as pilot:
        await pilot.pause(0.5)
        app.lib.folders = list(dirs)
        app.remove_library_folder()
        await pilot.pause(0.3)
        scr = app.screen
        assert isinstance(scr, FoldersScreen)
        await pilot.press("space")                 # позначити першу теку
        scr.action_remove_checked()
        await pilot.pause(0.2)
        assert app.lib.folders == dirs[1:]
        scr.action_remove_all()
        await pilot.pause(0.3)
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press("escape")                # скасувати
        await pilot.pause(0.2)
        assert app.lib.folders == dirs[1:]
        scr.action_remove_all()
        await pilot.pause(0.3)
        await pilot.press("y")                     # підтвердити
        await pilot.pause(0.3)
        assert app.lib.folders == []
        await pilot.press("escape")
        await pilot.pause(0.2)
        assert app.screen is app.main


@pytest.mark.asyncio
async def test_help_and_panels():
    from plativka.app import HelpScreen
    app = Plativka(demo=True)
    async with app.run_test(size=(130, 36)) as pilot:
        await pilot.pause(0.5)
        await pilot.press("f1")
        await pilot.pause(0.3)
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("escape")
        await pilot.pause(0.2)
        assert app.screen is app.main
        await pilot.press("1")
        await pilot.pause(0.1)
        assert app.focused.id in ("playlist", "pl-empty")
        await pilot.press("tab")
        await pilot.pause(0.1)
        assert app.focused.id in ("library", "lib-empty")
        assert app.main.query_one("#library-win").border_title.startswith("●")
        await pilot.press("tab")
        await pilot.pause(0.1)
        assert app.focused.id in ("playlist", "pl-empty")


@pytest.mark.asyncio
@pytest.mark.parametrize("width", [60, 80, 140])
async def test_keybar_fits(width):
    app = Plativka(demo=True)
    async with app.run_test(size=(width, 30)) as pilot:
        await pilot.pause(0.6)
        bar = app.main.query_one("#keybar")
        shown = [w for w in bar.children if w.display]
        assert shown, "at least the most important keys are shown"
        assert sum(w.size.width for w in shown) <= width
        assert any("F1" in str(w.render()) for w in shown)
