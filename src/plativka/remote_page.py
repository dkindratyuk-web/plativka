"""Сторінка пульта для телефона (HTML + CSS + JS без зовнішніх файлів і бібліотек).

Увесь текст із сервера показується через textContent — назви треків не можуть
виконати код у браузері. Ключ телефона зберігається в localStorage і йде лише
в заголовку Authorization.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

INDEX = """<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#f6f3ee">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Plativka">
<meta name="referrer" content="no-referrer">
<title>Plativka</title>
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/icon.png">
<link rel="apple-touch-icon" href="/icon.png">
<link rel="stylesheet" href="/app.css">
<script src="/app.js" defer></script>
</head>
<body>
<main id="pair" hidden>
  <img class="logo" src="/icon.png" alt="" width="72" height="72">
  <h1 data-t="title">Plativka</h1>
  <p class="muted" data-t="pairHelp"></p>
  <form id="pair-form" autocomplete="off">
    <input id="code" inputmode="numeric" pattern="[0-9 ]*" maxlength="7" placeholder="000000" aria-label="code">
    <button type="submit" class="primary" data-t="connect"></button>
  </form>
  <p id="pair-err" class="err" role="alert"></p>
</main>

<main id="app" hidden>
  <header class="bar"><span class="muted small" id="where">Plativka</span><span id="conn" class="dot" title=""></span></header>
  <div class="cover"><img id="cover" alt="" hidden><div id="vinyl" class="vinyl"><span></span></div></div>
  <div class="trow"><h2 id="t-title" class="title"></h2><button id="fav" class="heart" aria-label="favorite" aria-pressed="false">&#x2661;</button></div>
  <p id="t-sub" class="muted sub"></p>
  <div id="seek" class="seek" role="slider" aria-label="position" tabindex="0"><div id="seek-fill"></div></div>
  <div class="times muted small"><span id="pos">0:00</span><span id="dur">0:00</span></div>
  <div class="controls">
    <button id="prev" class="round" aria-label="previous">&#x23EE;&#xFE0E;</button>
    <button id="toggle" class="round big primary" aria-label="play/pause">&#x25B6;&#xFE0E;</button>
    <button id="next" class="round" aria-label="next">&#x23ED;&#xFE0E;</button>
  </div>
  <div class="vol"><span class="muted" aria-hidden="true">&#x1F508;&#xFE0E;</span><input id="vol" type="range" min="0" max="100" step="1" aria-label="volume"><span id="vol-n" class="muted small"></span></div>
  <div class="row">
    <button id="sleep-btn" class="chip" data-t="sleep"></button>
  </div>
  <div id="sleep-menu" class="sheet" hidden></div>
  <h3 class="muted small up" data-t="playlist"></h3>
  <ol id="list" class="list"></ol>
  <p class="foot"><button id="forget" class="link" data-t="forget"></button></p>
</main>
</body>
</html>
"""

CSS = """
:root{--bg:#f6f3ee;--card:#fff;--ink:#1d1a16;--muted:#6c645a;--line:#e2dbd0;--accent:#0e7c84;--accent-ink:#fff;color-scheme:light}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,Roboto,sans-serif}
main{max-width:460px;margin:0 auto;padding:max(14px,env(safe-area-inset-top)) 18px max(24px,env(safe-area-inset-bottom))}
[hidden]{display:none!important}
.muted{color:var(--muted)}.small{font-size:.85rem}.up{text-transform:uppercase;letter-spacing:.06em}
h1{font-size:1.6rem;margin:.4em 0 .2em}h3{margin:26px 0 8px}
#pair{text-align:center;padding-top:12vh}.logo{border-radius:16px}
#pair form{display:flex;gap:8px;margin-top:22px}
#code{flex:1;min-width:0;font-size:1.6rem;letter-spacing:.2em;text-align:center;padding:12px;border:1px solid var(--line);border-radius:12px;background:var(--card)}
button{font:inherit;color:inherit;border:1px solid var(--line);background:var(--card);border-radius:12px;padding:12px 16px;cursor:pointer}
button.primary{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.err{color:#b3261e;min-height:1.4em}
.bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.dot{width:9px;height:9px;border-radius:50%;background:#2e9d5b}.dot.off{background:#c9c2b7}
.cover{aspect-ratio:1;border-radius:18px;overflow:hidden;background:var(--accent);display:grid;place-items:center}
.cover img{width:100%;height:100%;object-fit:cover}
.vinyl{width:72%;aspect-ratio:1;border-radius:50%;background:radial-gradient(circle,#0000 0 31%,#26292f 32% 100%);display:grid;place-items:center;box-shadow:inset 0 0 0 10px #1c1e23}
.vinyl span{width:34%;aspect-ratio:1;border-radius:50%;background:var(--accent);box-shadow:inset 0 0 0 3px #0003}
.trow{display:flex;align-items:flex-start;gap:8px}.trow .title{flex:1}
.heart{border:0;background:none;font-size:1.7rem;line-height:1;padding:12px 4px 0;color:var(--muted)}.heart.on{color:#e0245e}
.list li .h{color:#e0245e;width:1em}
.title{font-size:1.35rem;margin:16px 0 2px;overflow-wrap:anywhere}.sub{margin:0;overflow-wrap:anywhere}
.seek{height:28px;margin-top:14px;position:relative;touch-action:none;cursor:pointer}
.seek::before{content:"";position:absolute;left:0;right:0;top:12px;height:5px;border-radius:5px;background:var(--line)}
#seek-fill{position:absolute;left:0;top:12px;height:5px;border-radius:5px;background:var(--accent);width:0}
.times{display:flex;justify-content:space-between;margin-top:-4px}
.controls{display:flex;justify-content:center;align-items:center;gap:22px;margin:12px 0 6px}
.round{width:58px;height:58px;border-radius:50%;padding:0;font-size:1.3rem;display:grid;place-items:center}
.round.big{width:76px;height:76px;font-size:1.8rem}
.vol{display:flex;align-items:center;gap:10px;margin-top:6px}.vol input{flex:1;accent-color:var(--accent)}
.row{display:flex;justify-content:center;margin-top:14px}.chip{border-radius:999px;padding:8px 16px;font-size:.95rem}
.chip.on{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.sheet{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px}.sheet button{padding:10px 4px;font-size:.92rem}
.list{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}
.list li{display:flex;gap:10px;padding:11px 4px;border-bottom:1px solid var(--line);cursor:pointer}
.list li .n{color:var(--muted);min-width:2.2em;text-align:right}.list li .d{color:var(--muted);margin-left:auto;padding-left:8px}
.list li .t{overflow-wrap:anywhere}.list li.cur{color:var(--accent);font-weight:600}.list li.cur .n{color:var(--accent)}
.foot{text-align:center;margin-top:28px}.link{border:0;background:none;color:var(--muted);text-decoration:underline;padding:6px}
"""

JS = r"""
"use strict";
(function () {
  var UK = /^uk|^ru|^be/i.test(navigator.language || "");
  var S = UK ? {
    title: "Платівка", pairHelp: "Відскануйте QR-код у Платівці (меню «Пульт з телефона») або введіть код, який вона показує.",
    connect: "Підключити", badCode: "Код не підійшов або вже не діє. Покажіть новий у Платівці.",
    badQr: "Цей QR-код уже використано. Відкрийте вікно пульта в Платівці ще раз.", noConn: "Немає зв'язку з Платівкою",
    sleep: "Таймер сну", sleepOff: "Вимк", min: "хв", afterTrack: "Після треку", sleepIn: "Сон: ", sleepTrack: "Сон: після треку",
    playlist: "Список відтворення", forget: "Відключити цей телефон", pick: "Оберіть, що послухати, у Платівці",
    forgetQ: "Відключити цей телефон від Платівки?",
    full: "Підключено забагато телефонів. Відключіть якийсь у вікні пульта в Платівці.",
    wait: "Забагато невдалих спроб. Спробуйте за 10 хвилин."
  } : {
    title: "Plativka", pairHelp: "Scan the QR code in Plativka (the “Phone remote” menu) or enter the code it shows.",
    connect: "Connect", badCode: "The code is wrong or no longer valid. Show a new one in Plativka.",
    badQr: "This QR code was already used. Open the remote window in Plativka again.", noConn: "No connection to Plativka",
    sleep: "Sleep timer", sleepOff: "Off", min: "min", afterTrack: "After track", sleepIn: "Sleep: ", sleepTrack: "Sleep: after track",
    playlist: "Playlist", forget: "Disconnect this phone", pick: "Choose something to play in Plativka",
    forgetQ: "Disconnect this phone from Plativka?",
    full: "Too many phones are connected. Disconnect one in the remote window in Plativka.",
    wait: "Too many failed attempts. Try again in 10 minutes."
  };
  document.documentElement.lang = UK ? "uk" : "en";
  document.querySelectorAll("[data-t]").forEach(function (el) { el.textContent = S[el.dataset.t] || el.textContent; });
  var $ = function (id) { return document.getElementById(id); };
  var KEY = "plativka-token";
  var token = null;
  try { token = localStorage.getItem(KEY); } catch (e) {}
  var st = null, plVer = -1, coverKey = null, coverUrl = null, timer = null, volBusy = 0, fails = 0;

  function fmt(s) {
    s = Math.max(0, Math.floor(s || 0));
    var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60;
    return (h ? h + ":" + String(m).padStart(2, "0") : m) + ":" + String(x).padStart(2, "0");
  }
  function api(method, path, body) {
    var h = {};
    if (token) h["Authorization"] = "Bearer " + token;
    if (body !== undefined) h["Content-Type"] = "application/json";
    return fetch(path, { method: method, headers: h, body: body === undefined ? undefined : JSON.stringify(body),
                         cache: "no-store", credentials: "omit" });
  }
  function save(t) { token = t; try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY); } catch (e) {} }
  function showPair(msg) {
    $("app").hidden = true; $("pair").hidden = false; $("pair-err").textContent = msg || "";
    if (timer) { clearInterval(timer); timer = null; }
  }
  function showApp() { $("pair").hidden = true; $("app").hidden = false; poll(); if (!timer) timer = setInterval(poll, 1000); }

  function pair(body, errMsg) {
    return api("POST", "/api/pair", body).then(function (r) {
      if (r.status === 409) { errMsg = S.full; throw new Error(409); }
      if (r.status === 429) { errMsg = S.wait; throw new Error(429); }
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (j) { save(j.token); showApp(); }).catch(function () {
      if (token && body.secret) showApp(); else showPair(errMsg);   // старий QR, але телефон уже підключений
    });
  }

  $("pair-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var c = $("code").value.replace(/\D/g, "");
    if (c.length !== 6) { $("pair-err").textContent = S.badCode; return; }
    pair({ code: c }, S.badCode);
  });

  function cmd(c, a) {
    return api("POST", "/api/cmd", { cmd: c, arg: a === undefined ? null : a }).then(function (r) {
      if (r.status === 401) { save(null); showPair(); }
      setTimeout(poll, 150);
    }).catch(function () {});
  }
  $("toggle").onclick = function () { cmd("toggle"); };
  $("next").onclick = function () { cmd("next"); };
  $("prev").onclick = function () { cmd("prev"); };
  $("fav").onclick = function () { cmd("fav"); setTimeout(function () { plVer = -1; }, 300); };
  var vt = null;
  $("vol").addEventListener("input", function () {
    volBusy = Date.now(); $("vol-n").textContent = this.value;
    var v = +this.value; clearTimeout(vt); vt = setTimeout(function () { cmd("volume", v); }, 120);
  });
  function seekAt(ev) {
    if (!st || !st.dur) return;
    var r = $("seek").getBoundingClientRect(), x = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
    var f = Math.min(1, Math.max(0, x / r.width));
    $("seek-fill").style.width = (f * 100) + "%";
    cmd("seek", Math.round(f * st.dur * 10) / 10);
  }
  $("seek").addEventListener("click", seekAt);
  $("seek").addEventListener("keydown", function (e) {
    if (!st) return;
    if (e.key === "ArrowRight") cmd("seek", Math.min(st.dur, st.pos + 5));
    if (e.key === "ArrowLeft") cmd("seek", Math.max(0, st.pos - 5));
  });
  var menu = $("sleep-menu");
  [[null, S.sleepOff], [15, "15 " + S.min], [30, "30 " + S.min], [45, "45 " + S.min], [60, "60 " + S.min],
   [90, "90 " + S.min], ["track", S.afterTrack]].forEach(function (o) {
    var b = document.createElement("button"); b.textContent = o[1];
    b.onclick = function () { menu.hidden = true; cmd("sleep", o[0]); };
    menu.appendChild(b);
  });
  $("sleep-btn").onclick = function () { menu.hidden = !menu.hidden; };
  $("forget").onclick = function () {
    if (!confirm(S.forgetQ)) return;
    api("POST", "/api/forget", {}).finally(function () { save(null); showPair(); });
  };

  function loadCover(key) {
    coverKey = key;
    if (!key) { $("cover").hidden = true; $("vinyl").hidden = false; return; }
    api("GET", "/cover").then(function (r) { return r.ok ? r.blob() : null; }).then(function (b) {
      if (key !== coverKey) return;
      if (coverUrl) URL.revokeObjectURL(coverUrl);
      coverUrl = b ? URL.createObjectURL(b) : null;
      $("cover").hidden = !b; $("vinyl").hidden = !!b;
      if (b) $("cover").src = coverUrl;
    }).catch(function () {});
  }
  function loadList() {
    api("GET", "/api/playlist").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (!j) return;
      var ol = $("list"); ol.textContent = "";
      j.items.forEach(function (it, i) {
        var li = document.createElement("li"), n = document.createElement("span"), t = document.createElement("span"),
            d = document.createElement("span");
        n.className = "n"; t.className = "t"; d.className = "d";
        var h = document.createElement("span"); h.className = "h"; h.textContent = it[2] ? "\u2665" : "";
        n.textContent = (i + 1) + "."; t.textContent = it[0]; d.textContent = it[1];
        li.append(n, h, t, d); li.onclick = function () { cmd("play", i); };
        ol.appendChild(li);
      });
      markCurrent();
    }).catch(function () {});
  }
  function markCurrent() {
    var lis = $("list").children;
    for (var i = 0; i < lis.length; i++) lis[i].classList.toggle("cur", st && i === st.current);
  }
  function render() {
    document.documentElement.style.setProperty("--accent", /^#[0-9a-f]{6}$/i.test(st.accent) ? st.accent : "#0e7c84");
    $("t-title").textContent = st.title || S.pick;
    $("fav").hidden = !st.title;
    $("fav").textContent = st.fav ? "\u2665" : "\u2661";
    $("fav").classList.toggle("on", !!st.fav); $("fav").setAttribute("aria-pressed", st.fav ? "true" : "false");
    $("t-sub").textContent = [st.artist, [st.album, st.year].filter(Boolean).join(" · ")].filter(Boolean).join(" — ");
    $("pos").textContent = fmt(st.pos); $("dur").textContent = fmt(st.dur);
    $("seek-fill").style.width = (st.dur ? Math.min(100, st.pos / st.dur * 100) : 0) + "%";
    $("toggle").textContent = st.active && !st.paused ? "❚❚" : "▶︎";
    if (Date.now() - volBusy > 1500) { $("vol").value = st.volume; $("vol-n").textContent = st.volume; }
    var sb = $("sleep-btn");
    sb.textContent = st.sleep === "track" ? S.sleepTrack : (st.sleep != null ? S.sleepIn + fmt(st.sleep) : S.sleep);
    sb.classList.toggle("on", st.sleep != null);
    if (st.cover !== coverKey) loadCover(st.cover);
    if (st.pl !== plVer) { plVer = st.pl; loadList(); } else markCurrent();
  }
  function poll() {
    if (!token || document.hidden) return;
    api("GET", "/api/state").then(function (r) {
      if (r.status === 401) { save(null); showPair(); return null; }
      return r.ok ? r.json() : null;
    }).then(function (j) {
      if (!j) return;
      fails = 0; $("conn").className = "dot"; st = j; render();
    }).catch(function () { if (++fails > 2) { $("conn").className = "dot off"; $("conn").title = S.noConn; } });
  }
  document.addEventListener("visibilitychange", poll);

  var m = /#p=([A-Za-z0-9_-]{16,})/.exec(location.hash);
  if (m) {
    history.replaceState(null, "", location.pathname);
    pair({ secret: m[1] }, S.badQr);
  } else if (token) {
    showApp();
  } else {
    showPair();
  }
})();
"""

MANIFEST = """{"name": "Plativka", "short_name": "Plativka", "start_url": "/", "display": "standalone",
"background_color": "#f6f3ee", "theme_color": "#f6f3ee",
"icons": [{"src": "/icon.png", "sizes": "256x256", "type": "image/png"}]}"""


@lru_cache(maxsize=1)
def icon_png() -> bytes:
    p = Path(__file__).resolve().parent / "assets" / "icon.png"
    try:
        return p.read_bytes()
    except OSError:
        return b""
