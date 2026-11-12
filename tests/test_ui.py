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
        for key in ["x", "c", "s", "r", "r", "r", "n", "o", "o", "o", "t", "t", "m", "m", "f2", "f2", "left", "right",
                    "k", "k", "g", "g", "g"]:
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


@pytest.mark.asyncio
async def test_compact_view_and_collapse():
    app = Plativka(demo=True)
    async with app.run_test(size=(80, 30)) as pilot:
        await pilot.pause(0.5)
        await pilot.press("w")
        await pilot.pause(0.2)
        s = app.main
        assert s.has_class("compact") and not s.has_class("narrow")
        assert s.query_one("#c-tabs").display and not s.query_one("#lcd-row").display
        await pilot.press("2")
        await pilot.pause(0.2)
        assert app.compact_tab == "library" and s.query_one("#ct-library").has_class("on")
        await pilot.press("e")
        await pilot.pause(0.2)
        assert s.has_class("collapsed")
        assert not s.query_one("#library-win").display and not s.query_one("#pl-win").display
        await pilot.press("1")           # вкладка розгортає назад
        await pilot.pause(0.2)
        assert not s.has_class("collapsed")
        await pilot.press("w")
        await pilot.pause(0.2)
        assert not s.has_class("compact") and s.query_one("#lcd-row").display


@pytest.mark.asyncio
async def test_sleep_timer_and_update_flags():
    app = Plativka(demo=True)
    async with app.run_test(size=(120, 34)) as pilot:
        await pilot.pause(0.5)
        await pilot.press("k")
        await pilot.pause(0.1)
        sub = app.main.query_one("#main-win").border_subtitle
        assert app.sleep_minutes == 15 and ("сон" in sub or "sleep" in sub)
        app.choose_sleep("track")
        assert app.sleep_after_track and app.sleep_consume_eof() and not app.sleep_after_track
        app.update_info = {"version": "99.0", "url": "https://example.invalid"}
        app.update_flags()
        await pilot.pause(0.1)
        assert "99.0" in app.main.query_one("#main-win").border_subtitle


@pytest.mark.asyncio
async def test_queue_copy_and_duplicates_screens(tmp_path):
    from plativka.app import CopyScreen, DuplicatesScreen, PlaylistTable
    from plativka.core import Track
    files = []
    for i, data in enumerate([b"aaaa", b"aaaa", b"bbbbbb"]):
        f = tmp_path / f"{i}.mp3"
        f.write_bytes(data)
        files.append(str(f))
    app = Plativka(demo=True)
    async with app.run_test(size=(130, 36)) as pilot:
        await pilot.pause(0.3)
        for i, p in enumerate(files):
            app.lib.tracks[p] = Track(path=p, title=f"T{i}", artist="A", length=60, size=4)
        app.add_to_playlist(files, quiet=True)
        app.current = 0
        tbl = app.main.query_one(PlaylistTable)
        tbl.focus()
        tbl.move_cursor(row=len(app.playlist) - 1)
        await pilot.press("N")
        await pilot.pause(0.1)
        assert app.queue == [app.playlist[-1]]
        await pilot.press("N")                       # ще раз — прибрати з черги
        assert app.queue == []
        await pilot.press("X")
        await pilot.pause(0.8)
        scr = app.screen
        assert isinstance(scr, DuplicatesScreen) and scr.groups and scr.groups[0].kind == "file"
        await pilot.press("enter")                   # лише зі списку
        await pilot.pause(0.2)
        assert sum(p in app.playlist for p in files[:2]) == 1 and files[2] in app.playlist
        dest = tmp_path / "usb"
        dest.mkdir()
        app.push_screen(CopyScreen(list(app.playlist), str(dest)))
        await pilot.pause(0.3)
        await pilot.press("enter")
        await pilot.pause(0.8)
        assert app.screen is app.main
        assert len([f for f in dest.iterdir() if f.suffix == ".mp3"]) == 2
