import ast
import re
from pathlib import Path

from plativka import i18n
from plativka.app import fix_text, fmt_time, name_from_file

SRC = Path(__file__).resolve().parents[1] / "src" / "plativka"


def _translatable_strings():
    """Усі рядки, обгорнуті в _(...) у коді плеєра й трею."""
    found = set()
    for f in ("app.py", "tray.py", "core.py", "gui.py"):
        tree = ast.parse((SRC / f).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "_" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    found.add(arg.value)
                elif isinstance(arg, ast.Dict):  # _({...}[key])
                    pass
    return found


def test_every_ui_string_has_english_translation():
    cyr = re.compile("[Ѐ-ӿ]")
    missing = sorted(s for s in _translatable_strings() if cyr.search(s) and s not in i18n.EN)
    assert not missing, f"No English translation for: {missing}"


def test_english_placeholders_match():
    for uk, en in i18n.EN.items():
        assert set(re.findall(r"{\w+}", uk)) == set(re.findall(r"{\w+}", en)), uk


def test_plural_tracks():
    i18n.LANG, old = "uk", i18n.LANG
    try:
        assert [i18n.n_tracks(n) for n in (1, 2, 5, 11, 21, 22)] == \
            ["1 трек", "2 треки", "5 треків", "11 треків", "21 трек", "22 треки"]
        i18n.LANG = "en"
        assert i18n.n_tracks(1) == "1 track" and i18n.n_tracks(3) == "3 tracks"
    finally:
        i18n.LANG = old


def test_name_from_file():
    assert name_from_file("01. Tyla - Water") == ("Tyla", "Water")
    assert name_from_file("50 Cent - In Da Club") == ("50 Cent", "In Da Club")
    assert name_from_file("03 Free Me") == ("", "Free Me")
    assert name_from_file("Lil Baby – Mrs. Trendsetter") == ("Lil Baby", "Mrs. Trendsetter")


def test_fix_cp1251_mojibake():
    broken = "Океан Ельзи".encode("cp1251").decode("latin-1")
    assert fix_text(broken) == "Океан Ельзи"
    assert fix_text("Café") == "Café"


def test_fmt_time():
    assert fmt_time(0) == "0:00" and fmt_time(75) == "1:15" and fmt_time(3725) == "1:02:05"
    assert fmt_time(None) == "-:--"


def test_kitty_notification_escape():
    import base64
    import re
    from plativka import sysdeps
    img = bytes(range(256)) * 40          # ~10 КБ — кілька шматків
    seq = sysdeps.kitty_notification("Виконавець", "Назва\nАльбом", img, ident="plativka-1")
    parts = re.findall(r"\x1b\]99;([^;]*);([^\x1b]*)\x1b\\", seq)
    assert "".join(f"\x1b]99;{m};{p}\x1b\\" for m, p in parts) == seq
    meta = [dict(kv.split("=", 1) for kv in m.split(":")) for m, _ in parts]
    assert all(m["i"] == "plativka-1" and m["e"] == "1" for m in meta)
    assert [m["d"] for m in meta][-1] == "1" and set(m["d"] for m in meta[:-1]) == {"0"}
    assert all(len(p) <= 4096 for _, p in parts)
    by = {}
    for m, (_, p) in zip(meta, parts):
        by.setdefault(m["p"], "")
        by[m["p"]] += p
    assert base64.b64decode(by["title"]).decode() == "Виконавець"
    assert base64.b64decode(by["body"]).decode() == "Назва\nАльбом"
    assert base64.b64decode(by["icon"]) == img
    assert base64.b64decode(meta[0]["s"]) == b"silent"
