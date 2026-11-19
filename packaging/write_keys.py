"""Збірка: записати ключі Last.fm (з секретів GitHub) у src/plativka/_keys.py.

Файл не входить у репозиторій (.gitignore). Без секретів нічого не пише — тоді в збірці
Last.fm недоступний, а ListenBrainz працює (йому ключ застосунку не потрібен)."""
import os
import pathlib

key, secret = os.environ.get("LASTFM_API_KEY", "").strip(), os.environ.get("LASTFM_SECRET", "").strip()
if key and secret:
    out = pathlib.Path(__file__).resolve().parent.parent / "src" / "plativka" / "_keys.py"
    out.write_text(f"LASTFM_KEY = {key!r}\nLASTFM_SECRET = {secret!r}\n", encoding="utf-8")
    print("Last.fm: ключі записано")
else:
    print("Last.fm: секретів немає — збірка без Last.fm")
