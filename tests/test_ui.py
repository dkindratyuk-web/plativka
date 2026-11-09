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
        title = app.main.query_one("#pl-win").border_title
        assert title == ("Список відтворення" if lang == "uk" else "Playlist")


@pytest.mark.asyncio
@pytest.mark.parametrize("confirm,expected_left", [("y", 0), ("escape", 2)])
async def test_remove_all_library_folders(tmp_path, confirm, expected_left):
    from plativka.app import ConfirmScreen, ListPicker
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    app = Plativka(demo=True)
    async with app.run_test(size=(120, 34)) as pilot:
        await pilot.pause(0.5)
        app.lib.folders = [str(a), str(b)]
        app.remove_library_folder()
        await pilot.pause(0.3)
        assert isinstance(app.screen, ListPicker)
        await pilot.press("enter")          # перший пункт — «Прибрати всі теки»
        await pilot.pause(0.3)
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press(confirm)
        await pilot.pause(0.3)
        assert app.screen is app.main
        assert len(app.lib.folders) == expected_left
