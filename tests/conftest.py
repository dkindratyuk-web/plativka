"""Ізольоване середовище для тестів: власні теки налаштувань, без трею й без звуку."""
import os
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="plativka-test-")
for var in ("HOME", "USERPROFILE", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "APPDATA", "LOCALAPPDATA"):
    os.environ[var] = _tmp
os.environ["PLATIVKA_NO_TRAY"] = "1"
os.environ["PLATIVKA_NO_NATIVE_DIALOG"] = "1"
os.environ["TEXTUAL_COLOR_SYSTEM"] = "truecolor"
sys.argv = ["plativka", "--demo"]
