// Сайт Платівки: підставляє посилання на файли останнього випуску й підсвічує вашу систему.
(function () {
  "use strict";
  var cfg = window.PLATIVKA || {};
  var API = "https://api.github.com/repos/dkindratyuk-web/plativka/releases/latest";
  var PATTERNS = {
    "desk-mac-arm": /^Plativka-Desktop-.*-macos-arm64\.dmg$/,
    "desk-mac-intel": /^Plativka-Desktop-.*-macos-x86_64\.dmg$/,
    "desk-win": /^Plativka-Desktop-.*-windows-x64-setup\.exe$/,
    "term-mac-arm": /^Plativka-[0-9].*-macos-arm64\.dmg$/,
    "term-mac-intel": /^Plativka-[0-9].*-macos-x86_64\.dmg$/,
    "term-win": /^Plativka-[0-9].*-windows-x64-setup\.exe$/,
    "linux": /^plativka-.*-linux\.tar\.gz$/,
    "sums": /^SHA256SUMS/
  };
  var HERO_ASSET = { win: "desk-win", linux: "linux" };

  function detectOS() {
    var p = ((navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || "") + " " + navigator.userAgent;
    if (/iPhone|iPad|Android/i.test(p)) return "other";
    if (/Mac/i.test(p)) return "mac";
    if (/Win/i.test(p)) return "win";
    if (/Linux|X11|BSD/i.test(p)) return "linux";
    return "other";
  }

  var os = detectOS();
  var hero = document.getElementById("hero-dl");
  if (hero && cfg.dlFor && cfg.dlFor[os]) hero.textContent = cfg.dlFor[os];
  var mine = document.querySelector('.dl-card[data-os="' + os + '"]');
  if (mine) {
    mine.classList.add("is-mine");
    mine.parentNode.insertBefore(mine, mine.parentNode.firstChild);
  }

  // вкладки зі знімками
  var tabs = document.querySelectorAll(".tabs [data-tab]");
  function show(key) {
    tabs.forEach(function (b) { b.setAttribute("aria-selected", String(b.dataset.tab === key)); });
    document.querySelectorAll("[data-panel]").forEach(function (p) { p.hidden = p.dataset.panel !== key; });
  }
  tabs.forEach(function (b) { b.addEventListener("click", function () { show(b.dataset.tab); }); });
  if (os === "win" || os === "linux") show(os);

  // посилання на файли останнього випуску
  fetch(API, { headers: { Accept: "application/vnd.github+json" } })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (rel) {
      var urls = {};
      (rel.assets || []).forEach(function (a) {
        Object.keys(PATTERNS).forEach(function (k) {
          if (!urls[k] && PATTERNS[k].test(a.name)) urls[k] = a.browser_download_url;
        });
      });
      document.querySelectorAll("[data-asset]").forEach(function (el) {
        if (urls[el.dataset.asset]) el.href = urls[el.dataset.asset];
      });
      var v = (rel.tag_name || "").replace(/^v/, "");
      document.querySelectorAll("[data-version]").forEach(function (el) { el.textContent = v; });
      if (!hero) return;
      if (os === "mac") {
        // Safari не каже, який процесор, тож тоді кнопка веде до вибору Apple Silicon / Intel
        var uad = navigator.userAgentData;
        if (uad && uad.getHighEntropyValues) {
          uad.getHighEntropyValues(["architecture"]).then(function (h) {
            var k = h.architecture === "arm" ? "desk-mac-arm" : h.architecture === "x86" ? "desk-mac-intel" : null;
            if (k && urls[k]) hero.href = urls[k];
          }).catch(function () {});
        }
      } else if (HERO_ASSET[os] && urls[HERO_ASSET[os]]) {
        hero.href = urls[HERO_ASSET[os]];
      }
    })
    .catch(function () {
      document.querySelectorAll("[data-version]").forEach(function (el) { el.textContent = ""; });
      document.querySelectorAll("[data-version-label]").forEach(function (el) { el.hidden = true; });
      if (cfg.noList) console.warn(cfg.noList);
    });
})();
