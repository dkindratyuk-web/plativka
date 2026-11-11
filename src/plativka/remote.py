"""Пульт з телефона: маленький вебсервер у локальній мережі.

Безпека (див. docs/*/desktop.md → «Пульт з телефона»):
- вимкнено, доки користувач сам не увімкне; працює лише поки відкрита Платівка;
- приймає з'єднання тільки з приватних адрес (домашня мережа, localhost);
- Host має бути IP-адресою, localhost або <ім'я>.local — захист від DNS rebinding;
- кожен телефон має свій випадковий ключ (зберігаємо лише його SHA-256);
  ключ видається тільки через QR-код (довгий одноразовий секрет) або короткий код,
  який користувач сам показав, живе 2 хвилини і згорає після 5 невдалих спроб;
- команди лише для музики (грати, пауза, далі, гучність…), жодних файлів чи налаштувань;
- обмеження розміру запитів, тайм-аути, кількість з'єднань; суворий CSP на сторінці.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import io
import ipaddress
import json
import secrets
import socket
import time
from urllib.parse import parse_qs, urlsplit

from . import __version__
from .core import fmt_time, load_cover, log, real_path

DEFAULT_PORT = 8765
MAX_HEADER = 8 * 1024
MAX_BODY = 4 * 1024
MAX_CONN = 32
IO_TIMEOUT = 10
MAX_DEVICES = 10
CODE_TTL = 120            # секунд живе короткий код
CODE_TRIES = 5            # невдалих спроб — і код згорає
IP_FAIL_LIMIT = 10        # невдалих спроб з однієї адреси — блок на IP_BLOCK секунд
IP_BLOCK = 600
COMMANDS = {"toggle", "next", "prev", "seek", "volume", "play", "sleep"}

SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": ("default-src 'none'; script-src 'self'; style-src 'self'; "
                                "img-src 'self' blob:; connect-src 'self'; manifest-src 'self'; "
                                "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"),
}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def peer_allowed(addr: str | None) -> bool:
    """Лише локальна мережа: приватні, loopback і link-local адреси."""
    if not addr:
        return False
    try:
        ip = ipaddress.ip_address(addr.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_loopback or ip.is_link_local or (ip.is_private and not ip.is_unspecified
                                                  and not ip.is_reserved and not ip.is_multicast)


def host_allowed(host: str | None) -> bool:
    """Host — IP-адреса, localhost або ім'я цього комп'ютера в .local (не чужий домен)."""
    if not host:
        return False
    h = host.strip().lower()
    if h.startswith("["):                      # [IPv6]:порт
        h = h[1:h.find("]")] if "]" in h else ""
    elif h.count(":") == 1:
        h = h.rsplit(":", 1)[0]
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        pass
    me = socket.gethostname().lower().split(".")[0]
    return h in ("localhost", f"{me}.local", f"{me}.lan")


def lan_ip() -> str:
    """Адреса цього комп'ютера в домашній мережі (для QR-коду)."""
    for probe in ("10.255.255.255", "192.168.255.255"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((probe, 1))              # пакет не надсилається — лише вибір інтерфейсу
            ip = s.getsockname()[0]
            if peer_allowed(ip) and not ipaddress.ip_address(ip).is_loopback:
                return ip
        except OSError:
            pass
        finally:
            s.close()
    return "127.0.0.1"


def device_name(ua: str) -> str:
    ua = ua or ""
    dev = next((n for k, n in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"),
                               ("Macintosh", "Mac"), ("Windows", "Windows"), ("Linux", "Linux"))
                if k in ua), "")
    br = next((n for k, n in (("EdgA", "Edge"), ("Edg/", "Edge"), ("OPR", "Opera"), ("Firefox", "Firefox"),
                              ("FxiOS", "Firefox"), ("CriOS", "Chrome"), ("SamsungBrowser", "Samsung Internet"),
                              ("Chrome", "Chrome"), ("Safari", "Safari"))
               if k in ua), "")
    return " · ".join(x for x in (dev, br) if x) or "?"


class RemoteServer:
    """Сервер пульта. host — програма (консольна чи віконна) з методами remote_*:

    remote_state() -> dict, remote_playlist() -> list, remote_cover_path() -> str | None,
    async remote_command(cmd, arg), remote_event(kind, text) — сповіщення в інтерфейсі.
    store — словник у конфігу програми (зберігаються пристрої й порт), save() — зберегти конфіг.
    """

    def __init__(self, host, store: dict, save):
        self.host, self.store, self.save = host, store, save
        self.store.setdefault("devices", [])
        self.server = None
        self.port = int(store.get("port") or DEFAULT_PORT)
        self.ip = "127.0.0.1"
        self.pair_secret = secrets.token_urlsafe(24)
        self.code: str | None = None
        self.code_until = 0.0
        self.code_fails = 0
        self.code_locked = False
        self._ip_fails: dict[str, list] = {}
        self._conns = 0
        self._cover: tuple[str | None, bytes | None] = (None, None)

    # ── керування ──
    @property
    def running(self) -> bool:
        return self.server is not None

    async def start(self):
        if self.server:
            return
        last = None
        for port in range(self.port, self.port + 20):
            try:
                self.server = await asyncio.start_server(self._handle, host=None, port=port,
                                                         limit=MAX_HEADER, reuse_address=True)
                self.port = port
                break
            except OSError as e:
                last = e
        if not self.server:
            raise last or OSError("no port")
        self.ip = lan_ip()
        self.store["port"] = self.port
        log(f"пульт: слухаю порт {self.port}, адреса {self.ip}")

    async def stop(self):
        if self.server:
            self.server.close()
            try:
                await asyncio.wait_for(self.server.wait_closed(), 2)
            except Exception:
                pass
            self.server = None
            log("пульт: вимкнено")

    def pair_url(self) -> str:
        host = f"[{self.ip}]" if ":" in self.ip else self.ip
        return f"http://{host}:{self.port}/#p={self.pair_secret}"

    def base_url(self) -> str:
        host = f"[{self.ip}]" if ":" in self.ip else self.ip
        return f"http://{host}:{self.port}"

    def new_code(self) -> str:
        """Короткий код для ручного введення: 2 хвилини, 5 спроб."""
        self.code = f"{secrets.randbelow(10 ** 6):06d}"
        self.code_until = time.monotonic() + CODE_TTL
        self.code_fails = 0
        self.code_locked = False
        return self.code

    def code_left(self) -> int:
        if not self.code or self.code_locked:
            return 0
        return max(0, int(self.code_until - time.monotonic()))

    def reset_pairing(self):
        """«Новий код»: усі телефони відключено, старі QR-код і код більше не діють."""
        self.store["devices"] = []
        self.pair_secret = secrets.token_urlsafe(24)
        self.code = None
        self.save()

    def forget(self, dev_id: str):
        self.store["devices"] = [d for d in self.store["devices"] if d.get("id") != dev_id]
        self.save()

    @property
    def devices(self) -> list[dict]:
        return list(self.store.get("devices", []))

    # ── допоміжне ──
    def _blocked(self, ip: str) -> bool:
        f = self._ip_fails.get(ip)
        return bool(f and f[0] >= IP_FAIL_LIMIT and time.monotonic() - f[1] < IP_BLOCK)

    def _fail(self, ip: str):
        f = self._ip_fails.setdefault(ip, [0, 0.0])
        if time.monotonic() - f[1] > IP_BLOCK:
            f[0] = 0
        f[0] += 1
        f[1] = time.monotonic()
        if f[0] == IP_FAIL_LIMIT:
            log(f"пульт: адреса {ip} заблокована на {IP_BLOCK // 60} хв після невдалих спроб")
            self.host.remote_event("blocked", ip)

    def _device_for(self, auth: str | None):
        if not auth or not auth.startswith("Bearer "):
            return None
        h = _hash(auth[7:].strip())
        found = None
        for d in self.store.get("devices", []):
            if hmac.compare_digest(d.get("hash", ""), h):
                found = d
        return found

    # ── HTTP ──
    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = (writer.get_extra_info("peername") or [None])[0]
        if self._conns >= MAX_CONN or not peer_allowed(peer):
            writer.close()
            return
        self._conns += 1
        try:
            await asyncio.wait_for(self._serve(reader, writer, peer), IO_TIMEOUT)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError,
                ConnectionError, ValueError):
            pass
        except Exception as e:          # сервер не має падати через один кривий запит
            log(f"пульт: помилка запиту: {e!r}")
        finally:
            self._conns -= 1
            try:
                writer.close()
            except Exception:
                pass

    async def _serve(self, reader, writer, peer: str):
        head = await reader.readuntil(b"\r\n\r\n")
        if len(head) > MAX_HEADER:
            return await self._send(writer, 431, b"")
        lines = head.decode("latin-1").split("\r\n")
        try:
            method, target, _ver = lines[0].split(" ", 2)
        except ValueError:
            return await self._send(writer, 400, b"")
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        if not host_allowed(headers.get("host")):
            return await self._send(writer, 421, b"")
        if self._blocked(peer):
            return await self._send(writer, 429, b"")
        body = b""
        if method == "POST":
            origin = headers.get("origin")
            if origin and origin != f"http://{headers.get('host')}":
                return await self._send(writer, 403, b"")
            try:
                n = int(headers.get("content-length", "0"))
            except ValueError:
                return await self._send(writer, 400, b"")
            if n < 0 or n > MAX_BODY:
                return await self._send(writer, 413, b"")
            body = await reader.readexactly(n) if n else b""
        elif method != "GET":
            return await self._send(writer, 405, b"")
        url = urlsplit(target)
        path = url.path

        # сторінка — без ключа (у ній немає нічого, крім коду інтерфейсу)
        if method == "GET" and path in ("/", "/index.html"):
            from .remote_page import INDEX
            return await self._send(writer, 200, INDEX.encode(), "text/html; charset=utf-8")
        if method == "GET" and path == "/app.js":
            from .remote_page import JS
            return await self._send(writer, 200, JS.encode(), "text/javascript; charset=utf-8")
        if method == "GET" and path == "/app.css":
            from .remote_page import CSS
            return await self._send(writer, 200, CSS.encode(), "text/css; charset=utf-8")
        if method == "GET" and path == "/icon.png":
            from .remote_page import icon_png
            return await self._send(writer, 200, icon_png(), "image/png")
        if method == "GET" and path == "/manifest.webmanifest":
            from .remote_page import MANIFEST
            return await self._send(writer, 200, MANIFEST.encode(), "application/manifest+json")

        if method == "POST" and path == "/api/pair":
            return await self._pair(writer, peer, body, headers)

        dev = self._device_for(headers.get("authorization"))
        if dev is None:
            if path.startswith("/api/") or path == "/cover":
                self._fail(peer)
            return await self._send(writer, 401 if path.startswith("/api/") or path == "/cover" else 404, b"")
        if time.time() - dev.get("seen", 0) > 60:
            dev["seen"] = int(time.time())
            self.save()

        if method == "GET" and path == "/api/state":
            return await self._json(writer, self.host.remote_state())
        if method == "GET" and path == "/api/playlist":
            return await self._json(writer, {"items": self.host.remote_playlist()})
        if method == "GET" and path == "/cover":
            data = await self._cover_bytes()
            if not data:
                return await self._send(writer, 404, b"")
            return await self._send(writer, 200, data, "image/jpeg")
        if method == "POST" and path == "/api/cmd":
            try:
                req = json.loads(body or b"{}")
            except ValueError:
                return await self._send(writer, 400, b"")
            if not isinstance(req, dict):
                return await self._send(writer, 400, b"")
            cmd, arg = req.get("cmd"), req.get("arg")
            if cmd not in COMMANDS or not self._arg_ok(cmd, arg):
                return await self._send(writer, 400, b"")
            await self.host.remote_command(cmd, arg)
            return await self._json(writer, {"ok": True})
        if method == "POST" and path == "/api/forget":
            self.forget(dev["id"])
            self.host.remote_event("left", dev.get("name", "?"))
            return await self._json(writer, {"ok": True})
        return await self._send(writer, 404, b"")

    @staticmethod
    def _arg_ok(cmd: str, arg) -> bool:
        num = isinstance(arg, (int, float)) and not isinstance(arg, bool)
        if cmd in ("toggle", "next", "prev"):
            return arg is None
        if cmd == "seek":
            return num and 0 <= arg <= 24 * 3600
        if cmd == "volume":
            return num and 0 <= arg <= 100
        if cmd == "play":
            return isinstance(arg, int) and not isinstance(arg, bool) and arg >= 0
        if cmd == "sleep":
            return arg is None or arg == "track" or (isinstance(arg, int) and not isinstance(arg, bool)
                                                     and 1 <= arg <= 600)
        return False

    async def _pair(self, writer, peer, body, headers):
        try:
            req = json.loads(body or b"{}")
        except ValueError:
            return await self._send(writer, 400, b"")
        if not isinstance(req, dict):
            return await self._send(writer, 400, b"")
        secret, code = req.get("secret"), req.get("code")
        ok = False
        if isinstance(secret, str) and secret:
            ok = hmac.compare_digest(secret, self.pair_secret)
        elif isinstance(code, str) and code:
            if self.code and not self.code_locked and time.monotonic() < self.code_until:
                ok = hmac.compare_digest(code.strip().replace(" ", ""), self.code)
                if not ok:
                    self.code_fails += 1
                    if self.code_fails >= CODE_TRIES:
                        self.code_locked = True
                        self.code = None
                        self.host.remote_event("code_locked", "")
        if not ok:
            self._fail(peer)
            return await self._send(writer, 403, b"")
        token = secrets.token_urlsafe(32)
        dev = {"id": secrets.token_hex(6), "name": device_name(headers.get("user-agent", "")),
               "hash": _hash(token), "added": int(time.time()), "seen": int(time.time())}
        devs = self.store.setdefault("devices", [])
        devs.append(dev)
        del devs[:-MAX_DEVICES]
        if secret:
            self.pair_secret = secrets.token_urlsafe(24)   # QR-код одноразовий
        else:
            self.code = None
        self.save()
        log(f"пульт: підключено {dev['name']} ({peer})")
        self.host.remote_event("paired", dev["name"])
        return await self._json(writer, {"token": token, "name": dev["name"]})

    async def _cover_bytes(self) -> bytes | None:
        path = self.host.remote_cover_path()
        if not path:
            return None
        if self._cover[0] == path:
            return self._cover[1]

        def make():
            im = load_cover(real_path(path))
            if im is None:
                return None
            im.thumbnail((600, 600))
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=85)
            return buf.getvalue()
        data = await asyncio.to_thread(make)
        self._cover = (path, data)
        return data

    async def _json(self, writer, obj):
        return await self._send(writer, 200, json.dumps(obj, ensure_ascii=False).encode(),
                                "application/json; charset=utf-8")

    async def _send(self, writer, status: int, body: bytes, ctype: str = "text/plain; charset=utf-8"):
        reason = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
                  405: "Method Not Allowed", 413: "Payload Too Large", 421: "Misdirected Request",
                  429: "Too Many Requests", 431: "Request Header Fields Too Large"}.get(status, "")
        hdr = {"Content-Type": ctype, "Content-Length": str(len(body)), "Connection": "close",
               **SECURITY_HEADERS}
        writer.write((f"HTTP/1.1 {status} {reason}\r\n" + "".join(f"{k}: {v}\r\n" for k, v in hdr.items())
                      + "\r\n").encode() + body)
        await writer.drain()


class RemoteHost:
    """Спільна для обох версій «відповідь» серверу пульта. Потрібні від програми:
    player, playlist, current, track(), volume, toggle(), next(), prev(), play_index(),
    set_volume(), choose_sleep(), sleep_*; remote_accent() -> '#rrggbb'; remote_event()."""

    _pl_ver = 0
    _pl_sig = None

    def remote_state(self) -> dict:
        p = self.player
        st = {"version": __version__, "active": bool(p and p.active), "paused": bool(p and p.paused),
              "pos": round(p.time_pos, 1) if p and p.active else 0, "dur": 0, "volume": int(self.volume),
              "current": self.current, "title": "", "artist": "", "album": "", "year": "",
              "shuffle": bool(self.shuffle), "repeat": self.repeat,
              "sleep": ("track" if self.sleep_after_track else
                        (int(self.sleep_left) if self.sleep_until else None)),
              "accent": self.remote_accent(), "cover": None}
        if 0 <= self.current < len(self.playlist):
            path = self.playlist[self.current]
            t = self.track(path)
            st.update(title=t.title or t.display, artist=t.artist, album=t.album, year=t.year,
                      dur=round((p.duration if p and p.active and p.duration else t.length) or 0, 1),
                      cover=hashlib.sha1(path.encode()).hexdigest()[:12])
        sig = (len(self.playlist), tuple(self.playlist[:3]), tuple(self.playlist[-3:]))
        if sig != self._pl_sig:
            self._pl_sig, self._pl_ver = sig, self._pl_ver + 1
        st["pl"] = self._pl_ver
        return st

    def remote_playlist(self) -> list:
        out = []
        for path in self.playlist[:5000]:
            t = self.track(path)
            out.append([t.display, fmt_time(t.length)])
        return out

    def remote_cover_path(self):
        return self.playlist[self.current] if 0 <= self.current < len(self.playlist) else None

    async def remote_command(self, cmd: str, arg):
        if cmd == "toggle":
            await self.toggle()
        elif cmd == "next":
            await self.next()
        elif cmd == "prev":
            await self.prev()
        elif cmd == "seek":
            if self.player and self.player.active:
                await self.player.seek(float(arg))
        elif cmd == "volume":
            await self.set_volume(int(arg))
        elif cmd == "play":
            if arg < len(self.playlist):
                await self.play_index(arg)
        elif cmd == "sleep":
            self.choose_sleep(arg)
