"""Пульт з телефона: усе, що не має пройти, — не проходить."""
import asyncio
import json

import pytest

from plativka import remote


class FakeHost(remote.RemoteHost):
    def __init__(self):
        self.events, self.cmds = [], []
        self.player = None
        self.playlist, self.current, self.volume = ["/m/a.mp3", "/m/b.mp3"], 0, 50
        self.shuffle, self.repeat = False, "off"
        self.sleep_after_track, self.sleep_until, self.sleep_left = False, None, None

    def track(self, p):
        from plativka.core import Track
        return Track(path=p, title='<img src=x onerror=alert(1)>', artist="A", length=60)

    def is_fav(self, p):
        return False

    def remote_accent(self):
        return "#123456"

    def remote_event(self, kind, text):
        self.events.append((kind, text))

    async def remote_command(self, cmd, arg):
        self.cmds.append((cmd, arg))


async def req(port, method, path, headers=None, body=b"", host=None, raw=None):
    r, w = await asyncio.open_connection("127.0.0.1", port)
    if raw is not None:
        w.write(raw)
    else:
        h = {"Host": host or f"127.0.0.1:{port}", **(headers or {})}
        if body:
            h["Content-Length"] = str(len(body))
        w.write((f"{method} {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in h.items())
                 + "\r\n").encode() + body)
    await w.drain()
    try:
        data = await asyncio.wait_for(r.read(), 5)
    finally:
        w.close()
    if not data:
        return 0, {}, b""
    head, _, payload = data.partition(b"\r\n\r\n")
    lines = head.decode().split("\r\n")
    hdrs = {k.lower(): v.strip() for k, v in (x.split(":", 1) for x in lines[1:])}
    return int(lines[0].split()[1]), hdrs, payload


@pytest.fixture
def server():
    async def make():
        host = FakeHost()
        store = {"port": 18765}
        srv = remote.RemoteServer(host, store, lambda: None)
        await srv.start()
        return srv, host, store
    return make


async def pair_qr(srv):
    s, _, b = await req(srv.port, "POST", "/api/pair", {"Content-Type": "application/json", "User-Agent": "iPhone Safari"},
                        json.dumps({"secret": srv.pair_secret}).encode())
    assert s == 200
    return json.loads(b)["token"]


@pytest.mark.asyncio
async def test_page_public_api_needs_key(server):
    srv, host, store = await server()
    try:
        s, h, b = await req(srv.port, "GET", "/")
        assert s == 200 and b"Plativka" in b
        assert "script-src 'self'" in h["content-security-policy"] and h["x-frame-options"] == "DENY"
        for path in ("/api/state", "/api/playlist", "/cover"):
            assert (await req(srv.port, "GET", path))[0] == 401
        assert (await req(srv.port, "GET", "/api/state", {"Authorization": "Bearer nope"}))[0] == 401
        s, _, _ = await req(srv.port, "POST", "/api/cmd", {"Content-Type": "application/json"}, b'{"cmd":"next"}')
        assert s == 401 and host.cmds == []
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_qr_pairing_is_single_use_and_token_works(server):
    srv, host, store = await server()
    try:
        old = srv.pair_secret
        tok = await pair_qr(srv)
        assert srv.pair_secret != old and len(store["devices"]) == 1 and tok not in json.dumps(store)
        assert host.events[-1][0] == "paired"
        s, _, _ = await req(srv.port, "POST", "/api/pair", {}, json.dumps({"secret": old}).encode())
        assert s == 403
        auth = {"Authorization": f"Bearer {tok}"}
        s, _, b = await req(srv.port, "GET", "/api/state", auth)
        assert s == 200 and json.loads(b)["accent"] == "#123456"
        s, _, _ = await req(srv.port, "POST", "/api/cmd", {**auth, "Content-Type": "application/json"},
                            b'{"cmd":"volume","arg":40}')
        assert s == 200 and host.cmds == [("volume", 40)]
        srv.reset_pairing()
        assert (await req(srv.port, "GET", "/api/state", auth))[0] == 401
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_bad_commands_rejected(server):
    srv, host, _ = await server()
    try:
        auth = {"Authorization": f"Bearer {await pair_qr(srv)}", "Content-Type": "application/json"}
        for body in (b'{"cmd":"shell","arg":"rm -rf /"}', b'{"cmd":"volume","arg":1000}', b'{"cmd":"volume","arg":true}',
                     b'{"cmd":"play","arg":-1}', b'{"cmd":"play","arg":"../../etc/passwd"}', b'{"cmd":"seek","arg":-5}',
                     b'{"cmd":"sleep","arg":"forever"}', b'{"cmd":"next","arg":1}', b'[1,2]', b'not json'):
            assert (await req(srv.port, "POST", "/api/cmd", auth, body))[0] == 400, body
        assert host.cmds == []
        assert (await req(srv.port, "POST", "/api/cmd", auth, b"x" * 5000))[0] == 413
        assert (await req(srv.port, "DELETE", "/api/state", auth))[0] == 405
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_short_code_limits(server):
    srv, host, _ = await server()
    try:
        s, _, _ = await req(srv.port, "POST", "/api/pair", {}, b'{"code":"000000"}')
        assert s == 403                                   # код ще не показували — не діє
        code = srv.new_code()
        wrong = f"{(int(code) + 1) % 10 ** 6:06d}"
        for _ in range(remote.CODE_TRIES):
            assert (await req(srv.port, "POST", "/api/pair", {}, json.dumps({"code": wrong}).encode()))[0] == 403
        assert srv.code_locked and ("code_locked", "") in host.events
        assert (await req(srv.port, "POST", "/api/pair", {}, json.dumps({"code": code}).encode()))[0] in (403, 429)
        code = srv.new_code()
        srv._ip_fails.clear()
        assert (await req(srv.port, "POST", "/api/pair", {}, json.dumps({"code": code}).encode()))[0] == 200
        assert (await req(srv.port, "POST", "/api/pair", {}, json.dumps({"code": code}).encode()))[0] == 403
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_brute_force_blocks_address(server):
    srv, host, _ = await server()
    try:
        for _ in range(remote.IP_FAIL_LIMIT):
            await req(srv.port, "GET", "/api/state", {"Authorization": "Bearer guess"})
        tok_ok = srv.pair_secret
        s, _, _ = await req(srv.port, "POST", "/api/pair", {}, json.dumps({"secret": tok_ok}).encode())
        assert s == 429 and any(e[0] == "blocked" for e in host.events)
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_dns_rebinding_and_cross_site(server):
    srv, host, _ = await server()
    try:
        assert (await req(srv.port, "GET", "/", host="evil.example.com"))[0] == 421
        assert (await req(srv.port, "GET", "/api/state", host="evil.example.com:18765"))[0] == 421
        assert (await req(srv.port, "GET", "/", raw=b"GET / HTTP/1.1\r\n\r\n"))[0] == 421     # без Host
        tok = await pair_qr(srv)
        s, _, _ = await req(srv.port, "POST", "/api/cmd", {"Authorization": f"Bearer {tok}", "Origin": "http://evil.example.com",
                                                          "Content-Type": "application/json"}, b'{"cmd":"next"}')
        assert s == 403 and host.cmds == []
        assert (await req(srv.port, "GET", "/", raw=b"GARBAGE\r\n\r\n"))[0] == 400
        assert (await req(srv.port, "GET", "/", raw=b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nX: " + b"a" * 20000 + b"\r\n\r\n"))[0] == 0
    finally:
        await srv.stop()


def test_address_rules():
    for ok in ("192.168.1.5", "10.0.0.2", "172.16.4.4", "127.0.0.1", "::1", "fe80::1", "::ffff:192.168.0.3", "fd00::5"):
        assert remote.peer_allowed(ok), ok
    for bad in ("8.8.8.8", "1.1.1.1", "100.64.1.1", "2001:4860::8888", "::ffff:8.8.8.8", "", None, "garbage"):
        assert not remote.peer_allowed(bad), bad
    for ok in ("192.168.1.24:8765", "[fe80::1]:8765", "localhost:8765", "127.0.0.1"):
        assert remote.host_allowed(ok), ok
    for bad in ("evil.com", "evil.com:8765", "192.168.1.24.nip.io", "", None):
        assert not remote.host_allowed(bad), bad


def test_state_text_is_data_not_html():
    h = FakeHost()
    st = h.remote_state()
    assert st["title"].startswith("<img")        # віддаємо як є — сторінка показує через textContent
    from plativka import remote_page
    assert "innerHTML" not in remote_page.JS and "insertAdjacentHTML" not in remote_page.JS


@pytest.mark.asyncio
async def test_review_findings_fixed(server):
    srv, host, store = await server()
    try:
        # короткий код — одноразовий, і разом із «secret» не приймається
        code = srv.new_code()
        assert (await req(srv.port, "POST", "/api/pair", {}, json.dumps({"secret": 1, "code": code}).encode()))[0] == 400
        assert (await req(srv.port, "POST", "/api/pair", {}, json.dumps({"code": code}).encode()))[0] == 200
        assert (await req(srv.port, "POST", "/api/pair", {}, json.dumps({"code": code}).encode()))[0] == 403
        # не-ASCII — звичайна невдала спроба, а не виняток
        srv._ip_fails.clear()
        code = srv.new_code()
        assert (await req(srv.port, "POST", "/api/pair", {}, json.dumps({"code": "é12345"}).encode()))[0] == 403
        assert (await req(srv.port, "POST", "/api/pair", {}, json.dumps({"secret": "ґ" * 20}).encode()))[0] == 403
        assert srv.code_fails == 1 and srv._ip_fails
        # переповнений список — нікого не витісняємо
        srv._ip_fails.clear()
        store["devices"] = [{"id": str(i), "hash": "x"} for i in range(remote.MAX_DEVICES)]
        assert (await req(srv.port, "POST", "/api/pair", {}, json.dumps({"secret": srv.pair_secret}).encode()))[0] == 409
        assert len(store["devices"]) == remote.MAX_DEVICES
        # суворий розбір заголовків
        base = f"Host: 127.0.0.1:{srv.port}\r\n".encode()
        assert (await req(srv.port, "GET", "/", raw=b"GET / HTTP/1.1\r\n" + base + b"Host: evil.com\r\n\r\n"))[0] == 400
        assert (await req(srv.port, "POST", "/api/pair", raw=b"POST /api/pair HTTP/1.1\r\n" + base
                          + b"Content-Length: 1_0\r\n\r\n0123456789"))[0] == 400
        assert (await req(srv.port, "POST", "/api/pair", raw=b"POST /api/pair HTTP/1.1\r\n" + base
                          + b"Transfer-Encoding: chunked\r\n\r\n0\r\n\r\n"))[0] == 400
        # QR-код змінюється сам і після закриття вікна
        old = srv.pair_secret
        srv.secret_until = 0
        srv.pair_url()
        assert srv.pair_secret != old
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_connections_per_address_limited_but_not_dropped(server):
    srv, host, _ = await server()
    try:
        # телефон відкриває багато з'єднань водночас — усі мають отримати відповідь, а не обрив
        paths = ["/", "/app.js", "/app.css", "/icon.png", "/manifest.webmanifest"] * 4
        res = await asyncio.gather(*[req(srv.port, "GET", p) for p in paths])
        assert [r[0] for r in res] == [200] * len(paths)
        # «висячі» з'єднання займають місця лише до тайм-ауту заголовків, потім черга рушає
        held = [await asyncio.open_connection("127.0.0.1", srv.port) for _ in range(remote.MAX_CONN_PER_IP)]
        for _, w in held:
            w.write(b"GET / HTTP/1.1\r\n")
            await w.drain()
        await asyncio.sleep(0.1)
        t0 = asyncio.get_running_loop().time()
        assert (await req(srv.port, "GET", "/"))[0] == 200
        assert asyncio.get_running_loop().time() - t0 < remote.HEADER_TIMEOUT + 2
        for _, w in held:
            w.close()
    finally:
        await srv.stop()


def test_ipv6_tricks_not_local():
    for bad in ("2001:0:4136:e378:8000:63bf:3fff:fdd2", "2002:c0a8:101::1", "2001:db8::1", "192.0.2.1",
                "198.18.0.1", "::ffff:198.18.0.1", "64:ff9b::c0a8:101"):
        assert not remote.peer_allowed(bad), bad
    for bad in ("[::1]@evil.com", "[::1]:80x", "127.0.0.1:80:90", "127.0.0.1:abc"):
        assert not remote.host_allowed(bad), bad


def test_queue_command_args():
    ok = remote.RemoteServer._arg_ok
    assert ok("queue", 3) and not ok("queue", -1) and not ok("queue", "3") and not ok("queue", True)
    assert "queue" in remote.COMMANDS
