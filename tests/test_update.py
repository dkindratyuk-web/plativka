"""Перевірка оновлень: HTTPS із сертифікатами certifi, чесне «не вдалося», кеш."""
import json
import ssl

from plativka import core


def test_https_context_uses_certifi():
    import certifi
    ctx = core.https_context()
    assert isinstance(ctx, ssl.SSLContext) and ctx.verify_mode == ssl.CERT_REQUIRED
    assert certifi.where()


def test_offline_is_an_error_not_up_to_date(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "CACHE_DIR", tmp_path)
    def boom(*a, **k):
        raise OSError("CERTIFICATE_VERIFY_FAILED")
    monkeypatch.setattr("urllib.request.urlopen", boom)
    r = core.check_update(force=True)
    assert r and "error" in r
    assert not (tmp_path / "update.json").exists()      # невдачу не кешуємо


def test_newer_version_found_and_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "CACHE_DIR", tmp_path)
    calls = []

    class R:
        def __init__(self): self.b = json.dumps({"tag_name": "v99.0.0", "html_url": "https://x/r"}).encode()
        def read(self): return self.b
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def ok(req, timeout=0, context=None):
        calls.append(context)
        return R()
    monkeypatch.setattr("urllib.request.urlopen", ok)
    assert core.check_update(force=True)["version"] == "99.0.0"
    assert isinstance(calls[0], ssl.SSLContext)
    assert core.check_update()["version"] == "99.0.0" and len(calls) == 1   # з кешу, без запиту
