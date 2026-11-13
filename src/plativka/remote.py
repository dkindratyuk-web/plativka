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
import re
import secrets
import socket
import time
from urllib.parse import parse_qs, urlsplit

from . import __version__, sysdeps
from .core import fmt_time, load_cover, log

DEFAULT_PORT = 8765
MAX_HEADER = 8 * 1024
MAX_BODY = 4 * 1024
MAX_CONN = 32
MAX_CONN_PER_IP = 8          # браузер телефона відкриває до 6 з'єднань водночас
SLOT_WAIT = 5                 # зайві з'єднання чекають своєї черги, а не обриваються
HEADER_TIMEOUT = 3        # секунд на заголовки (повільні «висячі» запити відкидаємо швидко)
IO_TIMEOUT = 10
SECRET_TTL = 600          # QR-код живе 10 хвилин, потім змінюється сам
MAX_FAIL_ENTRIES = 1000
MAX_DEVICES = 10
CODE_TTL = 120            # секунд живе короткий код
CODE_TRIES = 5            # невдалих спроб — і код згорає
IP_FAIL_LIMIT = 10        # невдалих спроб з однієї адреси — блок на IP_BLOCK секунд
IP_BLOCK = 600
COMMANDS = {"toggle", "next", "prev", "seek", "volume", "play", "sleep", "fav", "queue"}

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


LOCAL_NETS = [ipaddress.ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "169.254.0.0/16",
    "::1/128", "fe80::/10", "fc00::/7")]


def peer_allowed(addr: str | None) -> bool:
    """Лише локальна мережа: явний перелік приватних, loopback і link-local мереж
    (не ip.is_private — він у різних версіях Python пропускає Teredo, 6to4 тощо)."""
    if not addr or not isinstance(addr, str):
        return False
    try:
        ip = ipaddress.ip_address(addr.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return any(ip in n for n in LOCAL_NETS if n.version == ip.version)


def _peer_key(addr: str) -> str:
    """Для лічильника невдалих спроб: IPv6 — уся підмережа /64 (адрес у ній мільярди)."""
    try:
        ip = ipaddress.ip_address(addr.split("%", 1)[0])
    except ValueError:
        return addr
    if isinstance(ip, ipaddress.IPv6Address) and not ip.ipv4_mapped:
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip.ipv4_mapped or ip) if isinstance(ip, ipaddress.IPv6Address) else str(ip)


def host_allowed(host: str | None) -> bool:
    """Host — IP-адреса, localhost або ім'я цього комп'ютера в .local (не чужий домен)."""
    if not host or not isinstance(host, str):
        return False
    h = host.strip().lower()
    if h.startswith("["):                      # [IPv6]:порт — після «]» лише порт
        m = re.fullmatch(r"\[([0-9a-f:.]+)\](?::\d{1,5})?", h)
        if not m:
            return False
        h = m.group(1)
    elif ":" in h:
        m = re.fullmatch(r"([^:]+):\d{1,5}", h)
        if not m:
            return False
        h = m.group(1)
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
        self.secret_until = time.monotonic() + SECRET_TTL
        self.code: str | None = None
        self.code_until = 0.0
        self.code_fails = 0
        self.code_locked = False
        self._ip_fails: dict[str, list] = {}
        self._conns = 0
        self._per_ip: dict[str, int] = {}
        self._cover: tuple[str | None, bytes | None] = (None, None)
        self._cover_lock = asyncio.Lock()

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
                # на Windows reuse_address дозволив би двом програмам ділити порт
                self.server = await asyncio.start_server(self._handle, host=None, port=port,
                                                         limit=MAX_HEADER,
                                                         reuse_address=not sysdeps.IS_WIN)
                self.port = port
                break
            except OSError as e:
                last = e
        if not self.server:
            raise last or OSError("no port")
        self.ip = lan_ip()
        self.rotate_secret()
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

    def rotate_secret(self):
        """Новий QR-код: старий більше не діє (на старті, при закритті вікна, раз на 10 хв)."""
        self.pair_secret = secrets.token_urlsafe(24)
        self.secret_until = time.monotonic() + SECRET_TTL

    def pair_url(self) -> str:
        if time.monotonic() > self.secret_until:
            self.rotate_secret()
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
        self.rotate_secret()
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
        f = self._ip_fails.get(_peer_key(ip))
        return bool(f and f[0] >= IP_FAIL_LIMIT and time.monotonic() - f[1] < IP_BLOCK)

    def _fail(self, ip: str):
        now = time.monotonic()
        if len(self._ip_fails) >= MAX_FAIL_ENTRIES:     # старі записи прибираємо, таблиця не росте без меж
            for k in [k for k, v in self._ip_fails.items() if now - v[1] > IP_BLOCK]:
                del self._ip_fails[k]
            if len(self._ip_fails) >= MAX_FAIL_ENTRIES:
                del self._ip_fails[min(self._ip_fails, key=lambda k: self._ip_fails[k][1])]
        ip = _peer_key(ip)
        f = self._ip_fails.setdefault(ip, [0, 0.0])
        if time.monotonic() - f[1] > IP_BLOCK:
            f[0] = 0
        f[0] += 1
        f[1] = time.monotonic()
        if f[0] == IP_FAIL_LIMIT:
            log(f"пульт: адреса {ip} заблокована на {IP_BLOCK // 60} хв після невдалих спроб")
            self.host.remote_event("blocked", ip)

    def _diag(self, kind: str, msg: str):
        """Пояснення в журнал, чому телефону відмовлено, — не частіше ніж раз на 30 с на причину."""
        now = time.monotonic()
        last = self.__dict__.setdefault("_diag_t", {})
        if now - last.get(kind, -1e9) >= 30:
            last[kind] = now
            log(msg)

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
        key = _peer_key(peer) if isinstance(peer, str) else ""
        if not peer_allowed(peer):
            self._diag("peer", f"пульт: з'єднання з {peer} відхилено — адреса не з домашньої мережі")
            writer.close()
            return
        # забагато з'єднань: зачекати, поки звільниться місце (висячі відпадають за HEADER_TIMEOUT),
        # і лише потім здатися — інакше сторінка на телефоні вантажилась би наполовину
        deadline = time.monotonic() + SLOT_WAIT
        while self._conns >= MAX_CONN or self._per_ip.get(key, 0) >= MAX_CONN_PER_IP:
            if time.monotonic() > deadline:
                self._diag("busy", f"пульт: {peer} — забагато одночасних з'єднань "
                           f"({self._per_ip.get(key, 0)} з цієї адреси, {self._conns} усього)")
                try:                            # коротка відповідь замість обірваного з'єднання (білого екрана)
                    writer.write(b"HTTP/1.1 503 Service Unavailable\r\nRetry-After: 1\r\nContent-Length: 0\r\n"
                                 b"Connection: close\r\n\r\n")
                    await asyncio.wait_for(writer.drain(), 2)
                except Exception:
                    pass
                writer.close()
                return
            await asyncio.sleep(0.05)
        self._conns += 1
        self._per_ip[key] = self._per_ip.get(key, 0) + 1
        try:
            await self._serve(reader, writer, peer)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError,
                ConnectionError, ValueError, UnicodeError):
            pass
        except Exception as e:          # сервер не має падати через один кривий запит
            log(f"пульт: помилка запиту: {type(e).__name__}")
        finally:
            self._conns -= 1
            self._per_ip[key] -= 1
            if self._per_ip[key] <= 0:
                del self._per_ip[key]
            try:
                writer.close()
            except Exception:
                pass

    async def _serve(self, reader, writer, peer: str):
        # тайм-аути лише на читання запиту — саму команду (play_index тощо) не обриваємо
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), HEADER_TIMEOUT)
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
                k = k.strip().lower()
                if k in headers and k in ("host", "content-length", "authorization", "origin"):
                    return await self._send(writer, 400, b"")      # подвійні заголовки — ні
                headers[k] = v.strip()
        if "transfer-encoding" in headers:
            return await self._send(writer, 400, b"")
        if not host_allowed(headers.get("host")):
            return await self._send(writer, 421, b"")
        body = b""
        if method == "POST":
            origin = headers.get("origin")
            if origin and origin != f"http://{headers.get('host')}":
                return await self._send(writer, 403, b"")
            cl = headers.get("content-length", "0")
            if not re.fullmatch(r"\d{1,7}", cl):
                return await self._send(writer, 400, b"")
            n = int(cl)
            if n > MAX_BODY:
                return await self._send(writer, 413, b"")
            body = await asyncio.wait_for(reader.readexactly(n), IO_TIMEOUT) if n else b""
        elif method != "GET":
            return await self._send(writer, 405, b"")
        url = urlsplit(target)
        path = url.path

        # сторінка — без ключа (у ній немає нічого, крім коду інтерфейсу)
        if method == "GET" and path in ("/", "/index.html"):
            from .remote_page import INDEX
            # сторінку й файли інтерфейсу браузер може тримати в кеші: повернувшись до згорнутого
            # пульта, телефон показує його одразу, навіть поки Wi-Fi ще «прокидається»
            return await self._send(writer, 200, INDEX.replace("{{V}}", __version__).encode(),
                                    "text/html; charset=utf-8", cache=600)
        if method == "GET" and path == "/app.js":
            from .remote_page import JS
            return await self._send(writer, 200, JS.replace("{{V}}", __version__).encode(),
                                    "text/javascript; charset=utf-8", cache=86400)
        if method == "GET" and path == "/app.css":
            from .remote_page import CSS
            return await self._send(writer, 200, CSS.encode(), "text/css; charset=utf-8", cache=86400)
        if method == "GET" and path == "/icon.png":
            from .remote_page import icon_png
            return await self._send(writer, 200, icon_png(), "image/png", cache=86400)
        if method == "GET" and path == "/apple-touch-icon.png":   # головний екран телефона: без прозорих кутів
            from .remote_page import icon_png
            return await self._send(writer, 200, icon_png("icon-touch.png"), "image/png", cache=86400)
        if method == "GET" and path == "/manifest.webmanifest":
            from .remote_page import MANIFEST
            return await self._send(writer, 200, MANIFEST.encode(), "application/manifest+json", cache=86400)

        # блок після невдалих спроб стосується лише підключення нових телефонів (вгадування коду):
        # сторінка й уже підключені телефони працюють завжди — інакше телефон міг заблокувати сам себе
        if method == "POST" and path == "/api/pair":
            if self._blocked(peer):
                self._diag("blocked", f"пульт: {peer} заблоковано — спроба підключення відхилена")
                return await self._send(writer, 429, b"")
            return await self._pair(writer, peer, body, headers)

        dev = self._device_for(headers.get("authorization"))
        if dev is None:
            # ключі телефонів — 256 біт, вгадати їх неможливо; тут лише пояснюємо в журналі, що сталося
            if path.startswith("/api/") or path == "/cover":
                self._diag("unauth", f"пульт: {peer} — запит без дійсного ключа ({path}); "
                           f"телефон відключено або його ключ загубився")
            return await self._send(writer, 401 if path.startswith("/api/") or path == "/cover" else 404, b"")
        if time.time() - dev.get("seen", 0) > 60:
            if time.time() - dev.get("seen", 0) > 300:
                log(f"пульт: {dev.get('name', '?')} ({peer}) знову на зв'язку")
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
        if cmd in ("toggle", "next", "prev", "fav"):
            return arg is None
        if cmd == "seek":
            return num and 0 <= arg <= 24 * 3600
        if cmd == "volume":
            return num and 0 <= arg <= 100
        if cmd in ("play", "queue"):
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
        if (secret is not None and not isinstance(secret, str)) or (code is not None and not isinstance(code, str)) \
                or (secret and code):
            return await self._send(writer, 400, b"")
        used = None
        if secret:
            if re.fullmatch(r"[A-Za-z0-9_-]{16,64}", secret) and time.monotonic() <= self.secret_until \
                    and hmac.compare_digest(secret.encode(), self.pair_secret.encode()):
                used = "secret"
        elif code:
            code = code.replace(" ", "")
            if self.code and not self.code_locked and time.monotonic() < self.code_until:
                if re.fullmatch(r"\d{6}", code) and hmac.compare_digest(code.encode(), self.code.encode()):
                    used = "code"
                else:
                    self.code_fails += 1
                    if self.code_fails >= CODE_TRIES:
                        self.code_locked = True
                        self.code = None
                        self.host.remote_event("code_locked", "")
        if used is None:
            self._fail(peer)
            return await self._send(writer, 403, b"")
        devs = self.store.setdefault("devices", [])
        if len(devs) >= MAX_DEVICES:         # нікого мовчки не витісняємо
            return await self._send(writer, 409, "Too many phones — disconnect one in Plativka".encode())
        token = secrets.token_urlsafe(32)
        dev = {"id": secrets.token_hex(6), "name": device_name(headers.get("user-agent", "")),
               "hash": _hash(token), "added": int(time.time()), "seen": int(time.time())}
        devs.append(dev)
        if used == "secret":
            self.rotate_secret()                # QR-код одноразовий
        else:
            self.code = None                    # і короткий код теж
        self.save()
        log(f"пульт: підключено {dev['name']} ({peer})")
        self.host.remote_event("paired", dev["name"])
        return await self._json(writer, {"token": token, "name": dev["name"]})

    async def _cover_bytes(self) -> bytes | None:
        path = self.host.remote_cover_path()
        if not path:
            return None
        async with self._cover_lock:            # одна обкладинка декодується один раз
            if self._cover[0] == path and self._cover[1] is not None:
                return self._cover[1]
            return await self._make_cover(path)

    async def _make_cover(self, path: str) -> bytes | None:

        def make():
            im = load_cover(path, 1000, track=self.host.track(path))
            if im is None:
                return None
            im.thumbnail((1000, 1000))
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=85)
            return buf.getvalue()
        data = await asyncio.to_thread(make)
        self._cover = (path, data)
        return data

    async def _json(self, writer, obj):
        return await self._send(writer, 200, json.dumps(obj, ensure_ascii=False).encode(),
                                "application/json; charset=utf-8")

    async def _send(self, writer, status: int, body: bytes, ctype: str = "text/plain; charset=utf-8",
                    cache: int = 0):
        reason = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
                  409: "Conflict",
                  405: "Method Not Allowed", 413: "Payload Too Large", 421: "Misdirected Request",
                  429: "Too Many Requests", 431: "Request Header Fields Too Large"}.get(status, "")
        hdr = {"Content-Type": ctype, "Content-Length": str(len(body)), "Connection": "close",
               **SECURITY_HEADERS}
        if cache:                       # лише код інтерфейсу; відповіді API й обкладинка — ніколи
            hdr["Cache-Control"] = f"private, max-age={cache}"
        writer.write((f"HTTP/1.1 {status} {reason}\r\n" + "".join(f"{k}: {v}\r\n" for k, v in hdr.items())
                      + "\r\n").encode() + body)
        await asyncio.wait_for(writer.drain(), IO_TIMEOUT)


class RemoteHost:
    """Спільна для обох версій «відповідь» серверу пульта. Потрібні від програми:
    player, playlist, current, track(), volume, toggle(), next(), prev(), play_index(),
    set_volume(), choose_sleep(), sleep_*; remote_accent() -> '#rrggbb'; remote_event()."""

    _pl_ver = 0
    _pl_sig = None

    def remote_dark(self) -> bool:
        return False

    def remote_state(self) -> dict:
        p = self.player
        st = {"version": __version__, "active": bool(p and p.active), "paused": bool(p and p.paused),
              "pos": round(p.time_pos, 1) if p and p.active else 0, "dur": 0, "volume": int(self.volume),
              "current": self.current, "title": "", "artist": "", "album": "", "year": "",
              "shuffle": bool(self.shuffle), "repeat": self.repeat,
              "sleep": ("track" if self.sleep_after_track else
                        (int(self.sleep_left) if self.sleep_until else None)),
              "accent": self.remote_accent(), "dark": bool(self.remote_dark()), "cover": None}
        if 0 <= self.current < len(self.playlist):
            path = self.playlist[self.current]
            t = self.track(path)
            st.update(title=t.title or t.display, artist=t.artist, album=t.album, year=t.year,
                      dur=round((p.duration if p and p.active and p.duration else t.length) or 0, 1),
                      cover=hashlib.sha1(f"{path}|{getattr(self, 'cover_rev', 0)}".encode()).hexdigest()[:12], fav=self.is_fav(path))
        sig = (len(self.playlist), tuple(self.playlist[:3]), tuple(self.playlist[-3:]), tuple(getattr(self, "queue", [])[:20]))
        if sig != self._pl_sig:
            self._pl_sig, self._pl_ver = sig, self._pl_ver + 1
        st["pl"] = self._pl_ver
        return st

    def remote_playlist(self) -> list:
        qpos = getattr(self, "queue_pos", lambda p: 0)
        out = []
        for path in self.playlist[:5000]:
            t = self.track(path)
            out.append([t.display, fmt_time(t.length), self.is_fav(path), qpos(path)])
        return out

    def remote_like(self, path: str):
        """Програма може перевизначити, щоб оновити свій інтерфейс."""
        self.toggle_fav(path)

    def remote_queue(self, path: str):
        """«Грати наступним» з телефона. Програма може перевизначити, щоб оновити свій інтерфейс."""
        self.queue_play_next([path])

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
        elif cmd == "queue":
            if arg < len(self.playlist):
                self.remote_queue(self.playlist[arg])
        elif cmd == "fav":
            if 0 <= self.current < len(self.playlist):
                self.remote_like(self.playlist[self.current])
