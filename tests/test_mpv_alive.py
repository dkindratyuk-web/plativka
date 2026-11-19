"""mpv завершився (сон Mac, збій звуку) — плеєр це помічає, а не мовчки ігнорує кнопки."""
import asyncio
import shutil

import pytest

from plativka import core


@pytest.mark.skipif(not shutil.which("mpv"), reason="потрібен mpv")
def test_lost_mpv_is_detected(monkeypatch):
    monkeypatch.setenv("PLATIVKA_MPV_ARGS", "--ao=null")

    async def run():
        p = core.MpvPlayer(lambda *a: None, lambda *a: None, lambda *a: None)
        await p.start(50)
        assert p.alive and await p.ping()
        p.proc.kill()
        for _ in range(50):
            if not p.alive:
                break
            await asyncio.sleep(0.05)
        assert not p.alive and not await p.ping()
        await p._safe("set_property", "pause", False)      # не зависає й не падає
        await p.close()
    asyncio.run(run())


def test_not_started_player_is_not_alive():
    p = core.MpvPlayer(lambda *a: None, lambda *a: None, lambda *a: None)
    assert not p.alive and not asyncio.run(p.ping())
