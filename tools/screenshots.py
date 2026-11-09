"""Скріншоти для README: демо-бібліотека з вигаданими виконавцями, обидві мови.

Потрібні ffmpeg і Chrome/Chromium + playwright (щоб перетворити SVG на PNG).
Запуск:  python tools/screenshots.py
"""
import asyncio
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
TMP = Path(tempfile.mkdtemp(prefix="plativka-shots-"))

ALBUMS = [
    ("Northern Lights", "Midnight Ferry", 2024, ((18, 40, 90), (240, 170, 70)),
     ["Harbour Lights", "Midnight Ferry", "Salt & Static", "Slow Tide"]),
    ("Сині Птахи", "Ранкова кава", 2023, ((190, 60, 50), (250, 210, 120)),
     ["Ранкова кава", "Трамвай №5", "Дощ над Подолом"]),
    ("Tape Deck Heroes", "Rewind", 2021, ((40, 120, 90), (230, 240, 200)),
     ["Rewind", "Side B", "Chrome Dioxide"]),
    ("Vela Nova", "Paper Planets", 2025, ((90, 40, 120), (120, 220, 230)),
     ["Paper Planets", "Orbit", "Low Gravity", "Satellite Hearts"]),
]


def make_library():
    from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TRCK
    from PIL import Image, ImageDraw
    music = TMP / "Music"
    for artist, album, year, cols, titles in ALBUMS:
        d = music / artist / f"{year} - {album}"
        d.mkdir(parents=True, exist_ok=True)
        im = Image.new("RGB", (400, 400), cols[0])
        dr = ImageDraw.Draw(im)
        for i in range(0, 400, 8):
            t = i / 400
            dr.line([(0, i), (400, i)], fill=tuple(int(cols[0][k] + (cols[1][k] - cols[0][k]) * t * .6) for k in range(3)), width=8)
        dr.ellipse((110, 110, 290, 290), fill=cols[1])
        dr.ellipse((175, 175, 225, 225), fill=cols[0])
        buf = io.BytesIO()
        im.save(buf, "JPEG")
        for n, title in enumerate(titles, 1):
            f = d / f"{n:02d} {title}.mp3"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                            f"sine=frequency={200 + 70 * n}:duration={150 + 23 * n}", "-ac", "2", "-b:a", "96k", str(f)],
                           check=True)
            tags = ID3()
            tags.add(TIT2(encoding=3, text=title))
            tags.add(TPE1(encoding=3, text=artist))
            tags.add(TALB(encoding=3, text=album))
            tags.add(TRCK(encoding=3, text=str(n)))
            tags.add(TDRC(encoding=3, text=str(year)))
            tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="", data=buf.getvalue()))
            tags.save(f)
    return music


async def shoot(lang: str, music: Path):
    home = TMP / f"home-{lang}"
    shutil.rmtree(home, ignore_errors=True)
    for v in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
        os.environ[v] = str(home)
    (home / "plativka").mkdir(parents=True)
    first = sorted((music / "Northern Lights").rglob("*.mp3"))
    (home / "plativka" / "config.json").write_text(json.dumps({
        "folders": [str(music)], "playlist": [str(p) for p in first], "current": 1, "position": 63,
        "lang": lang, "theme": "light", "show_library": True, "volume": 80}), "utf-8")
    for m in [m for m in sys.modules if m.startswith("plativka")]:
        del sys.modules[m]
    sys.argv = ["plativka", "--demo", f"--lang={lang}"]
    import plativka.app as P
    shots = []
    app = P.Plativka(demo=True)
    async with app.run_test(size=(132, 36)) as pilot:
        await pilot.pause(2.0)
        await pilot.press("x")
        await pilot.pause(2.2)
        tree = app.main.query_one(P.LibraryTree)
        for n in tree.root.children[:2]:
            n.expand()
        await pilot.pause(0.6)
        shots.append(("main", app.save_screenshot(filename=f"{lang}-main.svg", path=str(TMP))))
        await pilot.press("t")
        await pilot.pause(1.2)
        shots.append(("dark", app.save_screenshot(filename=f"{lang}-dark.svg", path=str(TMP))))
        await pilot.press("t", "o", "o")
        await pilot.pause(1.0)
        shots.append(("vinyl", app.save_screenshot(filename=f"{lang}-vinyl.svg", path=str(TMP))))
        await pilot.press("o")
        await pilot.press("j")
        await pilot.pause(0.4)
        await pilot.press(*list("pla"))
        await pilot.pause(0.6)
        shots.append(("search", app.save_screenshot(filename=f"{lang}-search.svg", path=str(TMP))))
        await pilot.press("escape")
    app2 = P.Plativka(demo=True)
    async with app2.run_test(size=(84, 26)) as pilot:
        await pilot.pause(1.5)
        await pilot.press("x")
        await pilot.pause(1.5)
        if app2.show_library:
            await pilot.press("m")
        await pilot.pause(0.5)
        shots.append(("narrow", app2.save_screenshot(filename=f"{lang}-narrow.svg", path=str(TMP))))
    return shots


async def to_png(svgs):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        exe = shutil.which("google-chrome") or shutil.which("chromium")
        b = await p.chromium.launch(executable_path=exe, args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 1800, "height": 1200}, device_scale_factor=1)
        for svg in svgs:
            await pg.goto(Path(svg).as_uri())
            await pg.wait_for_timeout(250)
            el = await pg.query_selector("svg")
            await el.screenshot(path=str(OUT / (Path(svg).stem + ".png")))
        await b.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    music = make_library()
    svgs = []
    for lang in ("en", "uk"):
        svgs += [p for _, p in asyncio.run(shoot(lang, music))]
    asyncio.run(to_png(svgs))
    print("Saved to", OUT)


if __name__ == "__main__":
    main()
