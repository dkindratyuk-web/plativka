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
<link rel="stylesheet" href="/app.css?v={{V}}">
<script src="/app.js?v={{V}}" defer></script>
</head>
<body>
<p id="boot" class="boot">Plativka…<br><small>Якщо сторінка не з'являється — оновіть її. · If the page doesn't appear, reload it.</small></p>
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
  <header class="bar"><span class="brand">Plativka</span><span id="conn" class="dot" title=""></span></header>
  <section class="card">
    <div class="cover"><img id="cover" alt="" hidden><div id="vinyl" class="vinyl"><span></span></div></div>
    <div class="lcdrow">
      <div class="lcdbox"><svg id="lcd" class="lcd" viewBox="0 0 92 30" aria-label="time"></svg></div>
      <button id="fav" class="heart" aria-label="favorite" aria-pressed="false"><svg class="ic hfill" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-9.2-8.6C1.2 8.2 3 4.5 6.6 4.5c2.1 0 3.4 1.2 4.4 2.6 1-1.4 2.3-2.6 4.4-2.6 3.6 0 5.4 3.7 3.8 6.9C19 15.6 12 20 12 20z"/></svg><svg class="ic hline" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-9.2-8.6C1.2 8.2 3 4.5 6.6 4.5c2.1 0 3.4 1.2 4.4 2.6 1-1.4 2.3-2.6 4.4-2.6 3.6 0 5.4 3.7 3.8 6.9C19 15.6 12 20 12 20z" fill="none" stroke="currentColor" stroke-width="1.8"/></svg></button>
    </div>
    <h2 id="t-title" class="title"></h2>
    <p id="t-sub" class="sub"></p>
    <div id="seek" class="seek" role="slider" aria-label="position" tabindex="0"><div id="seek-fill"></div></div>
    <div class="times small"><span id="pos">0:00</span><span id="dur">0:00</span></div>
    <div class="controls">
      <button id="prev" class="round" aria-label="previous"><svg class="ic " viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5h2v14H7zM20 5v14L10 12z"/></svg></button>
      <button id="toggle" class="round big primary" aria-label="play/pause"><svg class="ic play" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg><svg class="ic pause" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5h4v14H7zM13 5h4v14h-4z"/></svg></button>
      <button id="next" class="round" aria-label="next"><svg class="ic " viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5h2v14h-2zM4 5v14l10-7z"/></svg></button>
    </div>
    <div class="vol"><span class="volic"><svg class="ic " viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M16 8.5a5 5 0 0 1 0 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></span><input id="vol" type="range" min="0" max="100" step="1" aria-label="volume"><span id="vol-n" class="small muted"></span></div>
  </section>
  <div class="row">
    <button id="sleep-btn" class="chip" data-t="sleep"></button>
  </div>
  <div id="sleep-menu" class="sheet" hidden></div>
  <section class="card listcard">
    <h3 class="small up" data-t="playlist"></h3>
    <p class="small muted hint" data-t="holdHint"></p>
    <ol id="list" class="list"></ol>
  </section>
  <p class="foot"><button id="forget" class="link" data-t="forget"></button></p>
  <div id="toast" class="toast" role="status" hidden></div>
</main>
</body>
</html>
"""

CSS = """
:root{--bg:#eceff4;--card:#f7f8fb;--ink:#1a1d24;--muted:rgba(0,0,0,.52);--line:rgba(0,0,0,.08);--accent:#0e7c84;
--accent-ink:#fff;--lcd:rgba(14,124,132,.08);--hl:rgba(14,124,132,.16);--btn:rgba(0,0,0,.055);color-scheme:light}
:root.dark{--ink:#f2f3f5;--muted:rgba(255,255,255,.58);--line:rgba(255,255,255,.09);--btn:rgba(255,255,255,.08);color-scheme:dark}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,Roboto,sans-serif;transition:background .4s}
main{max-width:460px;margin:0 auto;padding:max(10px,env(safe-area-inset-top)) 14px max(24px,env(safe-area-inset-bottom))}
[hidden]{display:none!important}
.boot{text-align:center;color:var(--muted);padding-top:30vh;font-size:1.2rem}.boot small{font-size:.8rem}
.muted{color:var(--muted)}.small{font-size:.85rem}.up{text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:2px 4px 8px}
h1{font-size:1.6rem;margin:.4em 0 .2em}
#pair{text-align:center;padding-top:12vh}.logo{border-radius:16px}
#pair form{display:flex;gap:8px;margin-top:22px}
#code{flex:1;min-width:0;font-size:1.6rem;letter-spacing:.2em;text-align:center;padding:12px;border:1px solid var(--line);border-radius:12px;background:var(--card);color:var(--ink)}
button{font:inherit;color:inherit;border:1px solid var(--line);background:var(--card);border-radius:12px;padding:12px 16px;cursor:pointer}
button.primary{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.err{color:#d03a2f;min-height:1.4em}
.bar{display:flex;justify-content:space-between;align-items:center;margin:0 4px 10px}
.brand{font-weight:700;letter-spacing:.02em;color:var(--muted)}
.dot{width:9px;height:9px;border-radius:50%;background:#2e9d5b}.dot.off{background:#9c958b}
.card{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:14px;transition:background .4s}
.cover{aspect-ratio:1;border-radius:14px;overflow:hidden;background:var(--accent);display:grid;place-items:center}
.cover img{width:100%;height:100%;object-fit:cover}
.vinyl{width:72%;aspect-ratio:1;border-radius:50%;background:radial-gradient(circle,#0000 0 31%,#26292f 32% 100%);display:grid;place-items:center;box-shadow:inset 0 0 0 10px #1c1e23}
.vinyl span{width:34%;aspect-ratio:1;border-radius:50%;background:var(--accent);box-shadow:inset 0 0 0 3px #0003}
.lcdrow{display:flex;align-items:center;gap:10px;margin-top:12px}
.lcdbox{flex:1;background:var(--lcd);border-radius:12px;padding:8px 12px;display:flex;justify-content:center}
.lcd{height:44px;width:auto;fill:var(--accent)}.lcd .off{opacity:.09}
.heart{border:0;background:none;padding:6px;color:var(--muted);line-height:0}
.heart .ic{width:34px;height:34px}.heart .hfill{display:none;fill:#e0245e}.heart.on .hfill{display:block}.heart.on .hline{display:none}
.title{font-size:1.3rem;margin:12px 2px 2px;overflow-wrap:anywhere}.sub{margin:0 2px;color:var(--muted);overflow-wrap:anywhere}
.seek{height:28px;margin-top:10px;position:relative;touch-action:none;cursor:pointer}
.seek::before{content:"";position:absolute;left:0;right:0;top:12px;height:5px;border-radius:5px;background:var(--line)}
#seek-fill{position:absolute;left:0;top:12px;height:5px;border-radius:5px;background:var(--accent);width:0}
.times{display:flex;justify-content:space-between;margin-top:-4px;color:var(--muted)}
.controls{display:flex;justify-content:center;align-items:center;gap:22px;margin:10px 0 4px}
.round{width:58px;height:58px;border-radius:50%;padding:0;display:grid;place-items:center;background:var(--btn);border:0;color:var(--ink)}
.round.big{width:76px;height:76px;background:var(--accent);color:var(--accent-ink)}
.ic{width:24px;height:24px;fill:currentColor}.round.big .ic{width:32px;height:32px}
#toggle .pause{display:none}#toggle.playing .pause{display:block}#toggle.playing .play{display:none}
.vol{display:flex;align-items:center;gap:10px;margin-top:8px;color:var(--muted)}.vol input{flex:1;accent-color:var(--accent)}
.volic .ic{width:22px;height:22px}
.row{display:flex;justify-content:center;margin:14px 0 0}.chip{border-radius:999px;padding:8px 16px;font-size:.95rem;background:var(--card)}
.chip.on{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.sheet{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px}.sheet button{padding:10px 4px;font-size:.92rem}
.listcard{margin-top:16px;padding:10px 6px}
.list{list-style:none;margin:0;padding:0}
.list li{display:flex;gap:8px;padding:10px 8px;border-radius:10px;cursor:pointer;font-size:.95rem}
.list li .n{color:var(--muted);min-width:2.2em;text-align:right}.list li .d{color:var(--muted);margin-left:auto;padding-left:8px}
.list li .t{overflow-wrap:anywhere}.list li .h{color:#e0245e;width:1em;flex:none}
.list li.cur{background:var(--hl);font-weight:600}.list li.cur .t,.list li.cur .n{color:var(--accent)}
.hint{margin:-4px 4px 6px}
.list li{-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}
.list li.q .n{color:var(--accent);font-weight:600}
.toast{position:fixed;left:50%;bottom:max(18px,env(safe-area-inset-bottom));transform:translateX(-50%);max-width:88vw;
background:var(--ink);color:var(--bg);padding:10px 16px;border-radius:12px;font-size:.92rem;box-shadow:0 6px 20px rgba(0,0,0,.25);z-index:9}
.foot{text-align:center;margin-top:24px}.link{border:0;background:none;color:var(--muted);text-decoration:underline;padding:6px}
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
    playlist: "Список відтворення", holdHint: "Утримуйте пісню — заграє наступною", queued: "Наступною: ", forget: "Відключити цей телефон", pick: "Оберіть, що послухати, у Платівці",
    forgetQ: "Відключити цей телефон від Платівки?",
    full: "Підключено забагато телефонів. Відключіть якийсь у вікні пульта в Платівці.",
    wait: "Забагато невдалих спроб. Спробуйте за 10 хвилин."
  } : {
    title: "Plativka", pairHelp: "Scan the QR code in Plativka (the “Phone remote” menu) or enter the code it shows.",
    connect: "Connect", badCode: "The code is wrong or no longer valid. Show a new one in Plativka.",
    badQr: "This QR code was already used. Open the remote window in Plativka again.", noConn: "No connection to Plativka",
    sleep: "Sleep timer", sleepOff: "Off", min: "min", afterTrack: "After track", sleepIn: "Sleep: ", sleepTrack: "Sleep: after track",
    playlist: "Playlist", holdHint: "Touch and hold a song to play it next", queued: "Up next: ", forget: "Disconnect this phone", pick: "Choose something to play in Plativka",
    forgetQ: "Disconnect this phone from Plativka?",
    full: "Too many phones are connected. Disconnect one in the remote window in Plativka.",
    wait: "Too many failed attempts. Try again in 10 minutes."
  };
  document.documentElement.lang = UK ? "uk" : "en";
  var boot = document.getElementById("boot"); if (boot) boot.remove();
  document.querySelectorAll("[data-t]").forEach(function (el) { el.textContent = S[el.dataset.t] || el.textContent; });
  var $ = function (id) { return document.getElementById(id); };
  var KEY = "plativka-token";
  var token = null;
  try { token = localStorage.getItem(KEY); } catch (e) {}
  var st = null, plVer = -1, coverKey = null, coverUrl = null, timer = null, volBusy = 0, fails = 0;
  var VERSION = "{{V}}";

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
        n.textContent = (it[3] ? "\u2192" + it[3] + " " : "") + (i + 1) + ".";
        if (it[3]) li.classList.add("q");
        t.textContent = it[0]; d.textContent = it[1];
        li.append(n, h, t, d);
        holdable(li, function () { cmd("play", i); }, function () {
          cmd("queue", i); toast(S.queued + it[0]); setTimeout(function () { plVer = -1; }, 300);
        });
        ol.appendChild(li);
      });
      markCurrent();
    }).catch(function () {});
  }
  // дотик — грати; утримання (~0,5 с) — грати наступною
  function holdable(el, tap, hold) {
    var tm = null, held = false, sx = 0, sy = 0;
    function start(x, y) { held = false; sx = x; sy = y; clearTimeout(tm);
      tm = setTimeout(function () { held = true; if (navigator.vibrate) navigator.vibrate(15); hold(); }, 520); }
    function cancel() { clearTimeout(tm); tm = null; }
    el.addEventListener("touchstart", function (e) { var t = e.touches[0]; start(t.clientX, t.clientY); }, { passive: true });
    el.addEventListener("touchmove", function (e) { var t = e.touches[0];
      if (Math.abs(t.clientX - sx) > 10 || Math.abs(t.clientY - sy) > 10) cancel(); }, { passive: true });
    el.addEventListener("touchend", cancel);
    el.addEventListener("touchcancel", cancel);
    el.addEventListener("mousedown", function (e) { start(e.clientX, e.clientY); });
    el.addEventListener("mouseup", cancel);
    el.addEventListener("mouseleave", cancel);
    el.addEventListener("contextmenu", function (e) { e.preventDefault(); });
    el.addEventListener("click", function () { if (held) { held = false; return; } tap(); });
  }
  var toastT = null;
  function toast(msg) {
    var el = $("toast"); el.textContent = msg; el.hidden = false;
    clearTimeout(toastT); toastT = setTimeout(function () { el.hidden = true; }, 2200);
  }
  function markCurrent() {
    var lis = $("list").children;
    for (var i = 0; i < lis.length; i++) lis[i].classList.toggle("cur", st && i === st.current);
  }
  // ── вигляд як у Платівці на комп'ютері: фон і картка підфарбовані кольором обкладинки ──
  function rgb(h) { return [1, 3, 5].map(function (i) { return parseInt(h.substr(i, 2), 16); }); }
  function mix(a, b, t) { return "rgb(" + a.map(function (x, i) { return Math.round(x + (b[i] - x) * t); }).join(",") + ")"; }
  function rgba(c, a) { return "rgba(" + c.join(",") + "," + a + ")"; }
  var lastTheme = "";
  function applyTheme(accent, dark) {
    var key = accent + dark;
    if (key === lastTheme) return;
    lastTheme = key;
    var a = rgb(accent), r = document.documentElement, cs = r.style;
    r.classList.toggle("dark", dark);
    cs.setProperty("--accent", accent);
    cs.setProperty("--bg", mix(rgb(dark ? "#16181e" : "#eceff4"), a, dark ? .10 : .08));
    cs.setProperty("--card", mix(rgb(dark ? "#1e2129" : "#f7f8fb"), a, dark ? .06 : .045));
    cs.setProperty("--lcd", rgba(a, dark ? .09 : .07));
    cs.setProperty("--hl", rgba(a, .18));
    var lum = (a[0] * 299 + a[1] * 587 + a[2] * 114) / 1000;
    cs.setProperty("--accent-ink", lum > 150 ? "#111" : "#fff");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", getComputedStyle(r).getPropertyValue("--bg"));
  }
  // ── семисегментне табло, як годинник у Платівці ──
  var SEG = { a: [2, 0, 10, 2], b: [12, 2, 2, 9], c: [12, 13, 2, 9], d: [2, 22, 10, 2], e: [0, 13, 2, 9], f: [0, 2, 2, 9], g: [2, 11, 10, 2] };
  var DIG = ["abcdef", "bc", "abdeg", "abcdg", "bcfg", "acdfg", "acdefg", "abc", "abcdefg", "abcdfg"];
  var NS = "http://www.w3.org/2000/svg", lcdDigits = [];
  (function buildLcd() {
    var svg = $("lcd"), xs = [0, 20, 46, 66];
    xs.forEach(function (x) {
      var g = document.createElementNS(NS, "g"), segs = {};
      g.setAttribute("transform", "translate(" + (x + 4) + ",3)");
      Object.keys(SEG).forEach(function (k) {
        var r = document.createElementNS(NS, "rect"), v = SEG[k];
        r.setAttribute("x", v[0]); r.setAttribute("y", v[1]); r.setAttribute("width", v[2]); r.setAttribute("height", v[3]);
        r.setAttribute("rx", 1); g.appendChild(r); segs[k] = r;
      });
      svg.appendChild(g); lcdDigits.push(segs);
    });
    [9, 19].forEach(function (y) {
      var c = document.createElementNS(NS, "rect");
      c.setAttribute("x", 39); c.setAttribute("y", y + 3); c.setAttribute("width", 3); c.setAttribute("height", 3); c.setAttribute("rx", 1);
      svg.appendChild(c);
    });
  })();
  function showLcd(sec) {
    sec = Math.max(0, Math.floor(sec || 0));
    var m = Math.min(99, Math.floor(sec / 60)), s2 = sec % 60;
    var ds = [Math.floor(m / 10), m % 10, Math.floor(s2 / 10), s2 % 10];
    ds.forEach(function (d, i) {
      var on = (i === 0 && d === 0) ? "" : DIG[d];
      Object.keys(SEG).forEach(function (k) { lcdDigits[i][k].setAttribute("class", on.indexOf(k) >= 0 ? "" : "off"); });
    });
  }
  function render() {
    applyTheme(/^#[0-9a-f]{6}$/i.test(st.accent) ? st.accent : "#0e7c84", !!st.dark);
    showLcd(st.pos);
    $("t-title").textContent = st.title || S.pick;
    $("fav").hidden = !st.title;
    $("fav").classList.toggle("on", !!st.fav); $("fav").setAttribute("aria-pressed", st.fav ? "true" : "false");
    $("t-sub").textContent = [st.artist, [st.album, st.year].filter(Boolean).join(" · ")].filter(Boolean).join(" — ");
    $("pos").textContent = fmt(st.pos); $("dur").textContent = fmt(st.dur);
    $("seek-fill").style.width = (st.dur ? Math.min(100, st.pos / st.dur * 100) : 0) + "%";
    $("toggle").classList.toggle("playing", !!(st.active && !st.paused));
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
      fails = 0; $("conn").className = "dot"; $("conn").title = "";
      if (j.version && j.version !== VERSION) {          // Платівку оновили — беремо нову сторінку
        var k = "plativka-reloaded-" + j.version, done = null;
        try { done = sessionStorage.getItem(k); sessionStorage.setItem(k, "1"); } catch (e) {}
        if (!done) { location.replace("/?v=" + encodeURIComponent(j.version)); return; }
      }
      st = j; render();
    }).catch(function () { if (++fails > 2) { $("conn").className = "dot off"; $("conn").title = S.noConn; } });
  }
  // повернулися до згорнутого пульта: одразу питаємо стан і кілька секунд пробуємо частіше,
  // поки телефон знову під'єднується до Wi-Fi
  function wake() {
    if (!token || document.hidden) return;
    fails = 0; showApp(); plVer = -1;
    [400, 1200, 2500, 4000].forEach(function (t) { setTimeout(poll, t); });
  }
  document.addEventListener("visibilitychange", wake);
  window.addEventListener("pageshow", wake);
  window.addEventListener("online", wake);
  window.addEventListener("focus", wake);

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
