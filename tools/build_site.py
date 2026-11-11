"""Збирає сайт Платівки для GitHub Pages у теку docs/.

    python3 tools/build_site.py

Створює docs/index.html (англійська), docs/uk/index.html (українська),
docs/sitemap.xml, docs/robots.txt і docs/.nojekyll. Стилі й скрипт —
docs/site.css і docs/site.js, їх редагують руками. Файли для завантаження
сайт не зберігає: кнопки ведуть на останній випуск на GitHub.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SITE = "https://dkindratyuk-web.github.io/plativka/"
REPO = "https://github.com/dkindratyuk-web/plativka"
LATEST = REPO + "/releases/latest"

T = {
    "en": {
        "lang": "en", "path": "", "other": "uk/", "other_label": "Українська",
        "title": "Plativka — a Winamp-style music player for macOS, Windows and Linux",
        "desc": "Free, open-source Winamp-style music player for the music on your disk. "
                "Colours from the album cover, compact view and mini player, media keys, "
                "notifications with covers. For macOS, Windows and Linux.",
        "nav": ["Features", "Screenshots", "Download", "What's new", "Help"],
        "cl_title": "What's new in Plativka",
        "cl_lead": "Every version with its new features and fixes, newest first.",
        "cl_latest": "latest",
        "cl_dl": "Download the latest version",
        "help_title": "Help: common problems and how to fix them",
        "help_lead": "Something does not work as expected? Find your case below.",
        "help_toc": "On this page",
        "help_more": "Did not find your problem? <a href=\"{issues}\">Tell us about it on GitHub</a> — attach the logs, it helps a lot.",
        "h1": "Your music,<br>Winamp-style.",
        "lead": "A free player for the music already on your disk — for macOS, Windows and Linux. "
                "Offline, fast, no account, no ads.",
        "dl_for": {"mac": "Download for macOS", "win": "Download for Windows",
                   "linux": "Download for Linux", "other": "Download"},
        "hero_note": "Free and open source · MIT license",
        "all_dl": "All downloads",
        "github": "Source on GitHub",
        "feat_h": "What it can do",
        "features": [
            ("🎨", "Colour from the cover",
             "The clock, the level meter, the window and the playlist take their colour "
             "from the album art and change with every album. Light, dark or system theme."),
            ("🗔", "Three sizes",
             "The full Winamp view, a compact view with large type, and a mini player that "
             "can stay on top of all windows."),
            ("📚", "Playlist and library",
             "Your library by artist and album or by folder, instant search, drag folders "
             "into the window, play a whole album with a double-click."),
            ("⌨️", "Fits into your system",
             "Media keys and headphone buttons, Now Playing, MPRIS on Linux, track "
             "notifications with the album cover, a tray icon."),
            ("🎧", "Plays what you have",
             "MP3, FLAC, M4A/AAC, OGG/Opus, WAV, APE and WavPack through mpv. Files without tags are "
             "named from the file name, old Windows-1251 tags are fixed automatically."),
            ("💿", "Plays like an album",
             "No pauses between tracks, so live albums and mixes flow on. Volume levelling by album "
             "or by track (ReplayGain). One-file albums with a .cue sheet show up as separate tracks."),
            ("🌙", "Sleep timer",
             "Fall asleep to music: stop in 15–90 minutes or after the current track, "
             "with a gentle fade-out instead of a sudden stop."),
            ("💾", "Remembers everything",
             "Playlist, position, volume, view and window size are there next time. "
             "Tells you when a new version is out. English and Ukrainian interface."),
        ],
        "shots_h": "The same player on every system",
        "tabs": ["macOS", "Windows 11", "Linux"],
        "shots": {
            "mac": [("desk-mac-en-full.png", "Full view, macOS"),
                    ("desk-mac-en-compact.png", "Compact view, macOS"),
                    ("desk-mac-en-compact-dark.png", "Compact view, dark theme, macOS")],
            "win": [("desk-win-full.png", "Full view with the Mica background, Windows 11"),
                    ("desk-win-full-dark.png", "Dark theme, Windows 11"),
                    ("desk-win-compact.png", "Compact view, Windows 11")],
            "linux": [("desk-linux-en-full.png", "Full view, Kubuntu"),
                      ("desk-linux-en-full-dark.png", "Dark theme, Kubuntu"),
                      ("desk-linux-en-compact.png", "Compact view, Kubuntu")],
        },
        "mini": [("desk-mac-en-mini.png", "Mini player, macOS"),
                 ("desk-mac-en-mini-dark.png", "Mini player, dark theme, macOS")],
        "mini_cap": "The mini player — just the player strip, pinned above other windows.",
        "dl_h": "Download",
        "dl_sub": "Plativka Desktop is the main edition. The terminal edition is for people who live in the terminal; you can install both.",
        "version": "Latest version",
        "desktop": "Plativka Desktop",
        "terminal": "Terminal edition",
        "mac_arm": "Apple Silicon (M1 and newer)",
        "mac_intel": "Intel Mac",
        "mac_note": "macOS 12 or newer. On the first launch macOS asks for confirmation: "
                    "System Settings → Privacy &amp; Security → <b>Open Anyway</b>.",
        "win_btn": "Installer, 64-bit",
        "win_note": "Windows 10 and 11. If SmartScreen appears, click <b>More info</b> → <b>Run anyway</b> — "
                    "it shows up for every free program without a paid certificate.",
        "linux_btn": "Archive for all distributions",
        "linux_note": "Debian, Ubuntu, Mint, Fedora, Arch, Manjaro, openSUSE and others. "
                      "Unpack and run the installer:",
        "guide": "Step-by-step guide",
        "checksums": "Checksums",
        "term_h": "Plativka for the terminal",
        "term_p": "The same player as a text interface: the Winamp layout, real album covers in "
                  "kitty, Ghostty, iTerm2 and WezTerm (pixel-art covers elsewhere), a mini player "
                  "that shrinks the terminal window, and everything controlled from the keyboard.",
        "term_more": "About the terminal edition",
        "term_shots": [("macos-en-winamp.png", "Terminal edition, Winamp layout"),
                       ("macos-en-dark2.png", "Terminal edition, dark theme"),
                       ("macos-en-mini.png", "Terminal edition, mini player")],
        "foot": ["Changelog", "Report a problem", "Documentation"],
        "foot_note": "Plativka is free software under the MIT license.",
        "docs": "docs/en/",
        "readme": "README.md",
        "js_no": "Could not load the list of files — open the release page.",
    },
    "uk": {
        "lang": "uk", "path": "uk/", "other": "", "other_label": "English",
        "title": "Платівка — музичний плеєр у дусі Winamp для macOS, Windows і Linux",
        "desc": "Безплатний плеєр з відкритим кодом у дусі Winamp для музики на вашому диску. "
                "Колір з обкладинки, компактний вигляд і міні-плеєр, медіаклавіші, "
                "сповіщення з обкладинкою. Для macOS, Windows і Linux.",
        "nav": ["Можливості", "Знімки", "Завантажити", "Що нового", "Допомога"],
        "cl_title": "Що нового в Платівці",
        "cl_lead": "Кожна версія з новими можливостями й виправленнями, найновіша — вгорі.",
        "cl_latest": "остання",
        "cl_dl": "Завантажити останню версію",
        "help_title": "Допомога: поширені проблеми та як їх розв'язати",
        "help_lead": "Щось працює не так, як очікували? Знайдіть свій випадок нижче.",
        "help_toc": "На цій сторінці",
        "help_more": "Не знайшли своєї проблеми? <a href=\"{issues}\">Напишіть про неї на GitHub</a> і додайте журнали — це дуже допомагає.",
        "h1": "Ваша музика —<br>як у Winamp.",
        "lead": "Безплатний плеєр для музики, яка вже є на вашому диску, — для macOS, Windows і Linux. "
                "Офлайн, швидкий, без акаунтів і реклами.",
        "dl_for": {"mac": "Завантажити для macOS", "win": "Завантажити для Windows",
                   "linux": "Завантажити для Linux", "other": "Завантажити"},
        "hero_note": "Безплатно, відкритий код · ліцензія MIT",
        "all_dl": "Усі завантаження",
        "github": "Код на GitHub",
        "feat_h": "Що вміє",
        "features": [
            ("🎨", "Колір з обкладинки",
             "Годинник, індикатор рівня, вікно й список треків беруть колір з обкладинки "
             "й змінюються з кожним альбомом. Світла, темна або системна тема."),
            ("🗔", "Три розміри",
             "Повний вигляд як у Winamp, компактний з великою назвою треку і міні-плеєр, "
             "який може бути поверх усіх вікон."),
            ("📚", "Плейлист і бібліотека",
             "Бібліотека за виконавцями й альбомами або за теками, миттєвий пошук, теки "
             "можна просто перетягнути у вікно, подвійний клік грає весь альбом."),
            ("⌨️", "Дружить із системою",
             "Медіаклавіші й кнопки навушників, «Зараз грає», MPRIS у Linux, сповіщення "
             "про трек з обкладинкою, іконка в треї."),
            ("🎧", "Грає те, що у вас є",
             "MP3, FLAC, M4A/AAC, OGG/Opus, WAV, APE і WavPack через mpv. Файли без тегів підписуються "
             "з назви файлу, старі теги у Windows-1251 виправляються самі."),
            ("💿", "Грає як альбом",
             "Без пауз між треками — концертні альбоми й мікси не розриваються. Вирівнювання "
             "гучності за альбомом або за треком (ReplayGain). Альбом одним файлом з .cue — окремими треками."),
            ("🌙", "Таймер сну",
             "Засинайте під музику: зупинка через 15–90 хвилин або після поточного треку, "
             "з м'яким стишуванням, а не різким обривом."),
            ("💾", "Усе пам'ятає",
             "Плейлист, позиція, гучність, вигляд і розмір вікна — наступного разу все "
             "на місці. Підкаже, коли вийде нова версія. Українська й англійська мова інтерфейсу."),
        ],
        "shots_h": "Той самий плеєр на кожній системі",
        "tabs": ["macOS", "Windows 11", "Linux"],
        "shots": {
            "mac": [("desk-mac-uk-full.png", "Повний вигляд, macOS"),
                    ("desk-mac-uk-compact-dark.png", "Компактний вигляд, темна тема, macOS"),
                    ("desk-mac-uk-full-dark.png", "Повний вигляд, темна тема, macOS")],
            "win": [("desk-win-full.png", "Повний вигляд з фоном Mica, Windows 11"),
                    ("desk-win-full-dark.png", "Темна тема, Windows 11"),
                    ("desk-win-compact.png", "Компактний вигляд, Windows 11")],
            "linux": [("desk-linux-uk-full-dark.png", "Повний вигляд, темна тема, Kubuntu"),
                      ("desk-linux-uk-compact.png", "Компактний вигляд, Kubuntu"),
                      ("desk-linux-uk-compact-dark.png", "Компактний вигляд, темна тема, Kubuntu")],
        },
        "mini": [("desk-mac-uk-mini-dark.png", "Міні-плеєр, темна тема, macOS"),
                 ("desk-linux-uk-mini.png", "Міні-плеєр, Kubuntu")],
        "mini_cap": "Міні-плеєр — лише смужка керування, закріплена поверх інших вікон.",
        "dl_h": "Завантажити",
        "dl_sub": "Основна версія — Платівка у власному вікні (Plativka Desktop). Версія для термінала — для тих, хто живе в терміналі; можна встановити обидві.",
        "version": "Остання версія",
        "desktop": "Plativka Desktop",
        "terminal": "Версія для термінала",
        "mac_arm": "Apple Silicon (M1 і новіші)",
        "mac_intel": "Mac з Intel",
        "mac_note": "macOS 12 або новіша. Під час першого запуску macOS попросить підтвердження: "
                    "Системні параметри → Приватність і безпека → <b>Усе одно відкрити</b>.",
        "win_btn": "Інсталятор, 64-біт",
        "win_note": "Windows 10 і 11. Якщо з'явиться SmartScreen, натисніть <b>Докладніше</b> → "
                    "<b>Усе одно запустити</b> — так буває з кожною безплатною програмою без платного сертифіката.",
        "linux_btn": "Архів для всіх дистрибутивів",
        "linux_note": "Debian, Ubuntu, Mint, Fedora, Arch, Manjaro, openSUSE та інші. "
                      "Розпакуйте й запустіть інсталятор:",
        "guide": "Покрокова інструкція",
        "checksums": "Контрольні суми",
        "term_h": "Платівка для термінала",
        "term_p": "Той самий плеєр як текстовий інтерфейс: розкладка Winamp, справжні обкладинки "
                  "в kitty, Ghostty, iTerm2 і WezTerm (піксельні — в інших терміналах), міні-плеєр, "
                  "що зменшує вікно термінала, і все керується з клавіатури.",
        "term_more": "Докладніше про версію для термінала",
        "term_shots": [("macos-winamp.png", "Версія для термінала, вигляд Winamp"),
                       ("macos-compact.png", "Версія для термінала, компактний вигляд"),
                       ("macos-mini.png", "Версія для термінала, міні-плеєр")],
        "foot": ["Історія змін", "Повідомити про проблему", "Документація"],
        "foot_note": "Платівка — вільна програма під ліцензією MIT.",
        "docs": "docs/uk/",
        "readme": "README.uk.md",
        "js_no": "Не вдалося завантажити список файлів — відкрийте сторінку випуску.",
    },
}


def img(prefix: str, name: str, alt: str, cls: str = "", lazy: bool = True) -> str:
    from PIL import Image
    w, h = Image.open(DOCS / "img" / name).size
    return (f'<img src="{prefix}img/{name}" alt="{html.escape(alt)}" width="{w}" height="{h}"'
            f'{" loading=\"lazy\"" if lazy else ""}{f" class=\"{cls}\"" if cls else ""}>')


def dl(asset: str, label: str, sub: str = "", primary: bool = False) -> str:
    return (f'<a class="btn{" btn-primary" if primary else ""}" data-asset="{asset}" href="{LATEST}">'
            f'<span>{label}</span>{f"<small>{sub}</small>" if sub else ""}</a>')


def page(t: dict) -> str:
    p = "../" if t["path"] else ""
    url = SITE + t["path"]
    other = SITE + t["other"]
    docs = f"{REPO}/blob/main/{t['docs']}"
    ld = {
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": "Plativka", "alternateName": "Платівка",
        "applicationCategory": "MultimediaApplication",
        "operatingSystem": "macOS, Windows, Linux",
        "description": t["desc"], "url": url, "downloadUrl": LATEST,
        "license": "https://opensource.org/licenses/MIT",
        "image": SITE + "img/og.png",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "author": {"@type": "Person", "name": "dkindratyuk-web", "url": "https://github.com/dkindratyuk-web"},
    }
    features = "\n".join(
        f'<li><span class="f-ico" aria-hidden="true">{i}</span><h3>{h}</h3><p>{d}</p></li>'
        for i, h, d in t["features"])
    tabs = "".join(
        f'<button role="tab" data-tab="{k}" aria-selected="{"true" if k == "mac" else "false"}">{name}</button>'
        for k, name in zip(("mac", "win", "linux"), t["tabs"]))
    panels = "".join(
        f'<div class="shots" data-panel="{k}"{"" if k == "mac" else " hidden"}>'
        + "".join(f"<figure>{img(p, n, a)}<figcaption>{a}</figcaption></figure>" for n, a in v)
        + "</div>" for k, v in t["shots"].items())
    mini = "".join(f"<figure>{img(p, n, a)}<figcaption>{a}</figcaption></figure>" for n, a in t["mini"])
    term = "".join(f"<figure>{img(p, n, a)}<figcaption>{a}</figcaption></figure>" for n, a in t["term_shots"])
    hero_shots = (img(p, t["shots"]["mac"][0][0], t["shots"]["mac"][0][1], "h1-shot", lazy=False)
                  + img(p, "desk-win-full-dark.png", t["shots"]["win"][1][1], "h2-shot", lazy=False)
                  + img(p, t["mini"][0][0], t["mini"][0][1], "h3-shot", lazy=False))
    body = f"""<main>
<section class="hero">
  <div class="wrap hero-in">
    <div class="hero-text">
      <h1>{t['h1']}</h1>
      <p class="lead">{t['lead']}</p>
      <div class="cta">
        <a class="btn btn-primary btn-big" id="hero-dl" href="#download">{t['dl_for']['other']}</a>
        <a class="btn btn-ghost btn-big" href="{REPO}">{t['github']}</a>
      </div>
      <p class="hero-note"><span data-version-label>{t['version']}</span> <b data-version>…</b> · {t['hero_note']}</p>
    </div>
    <div class="hero-shots" aria-hidden="false">{hero_shots}</div>
  </div>
</section>

<section id="features" class="wrap sec">
  <h2>{t['feat_h']}</h2>
  <ul class="features">
{features}
  </ul>
</section>

<section id="screenshots" class="sec sec-tint">
  <div class="wrap">
    <h2>{t['shots_h']}</h2>
    <div class="tabs" role="tablist">{tabs}</div>
    {panels}
    <div class="shots shots-mini">{mini}</div>
    <p class="cap">{t['mini_cap']}</p>
  </div>
</section>

<section id="download" class="wrap sec">
  <h2>{t['dl_h']} <span class="ver" data-version></span></h2>
  <p class="sub">{t['dl_sub']}</p>
  <div class="dl-grid">
    <article class="dl-card" data-os="mac">
      <h3>macOS</h3>
      <h4>{t['desktop']}</h4>
      {dl("desk-mac-arm", t['mac_arm'], ".dmg", True)}
      {dl("desk-mac-intel", t['mac_intel'], ".dmg")}
      <h4>{t['terminal']}</h4>
      <div class="row">{dl("term-mac-arm", "Apple Silicon")}{dl("term-mac-intel", "Intel")}</div>
      <p class="note">{t['mac_note']}</p>
      <a class="more" href="{docs}install-macos.md">{t['guide']} →</a>
    </article>
    <article class="dl-card" data-os="win">
      <h3>Windows</h3>
      <h4>{t['desktop']}</h4>
      {dl("desk-win", t['win_btn'], ".exe", True)}
      <h4>{t['terminal']}</h4>
      {dl("term-win", t['win_btn'], ".exe")}
      <p class="note">{t['win_note']}</p>
      <a class="more" href="{docs}install-windows.md">{t['guide']} →</a>
    </article>
    <article class="dl-card" data-os="linux">
      <h3>Linux</h3>
      <h4>{t['desktop']} + {t['terminal'][0].lower() + t['terminal'][1:]}</h4>
      {dl("linux", t['linux_btn'], ".tar.gz", True)}
      <p class="note">{t['linux_note']}</p>
      <pre><code>tar -xzf plativka-*-linux.tar.gz
cd plativka-*-linux
./install.sh --desktop</code></pre>
      <a class="more" href="{docs}install-linux.md">{t['guide']} →</a>
    </article>
  </div>
  <p class="dl-foot"><a href="{LATEST}">{t['all_dl']}</a> · <a data-asset="sums" href="{LATEST}">{t['checksums']}</a></p>
</section>

<section id="terminal" class="sec sec-tint">
  <div class="wrap term">
    <div>
      <h2>{t['term_h']}</h2>
      <p>{t['term_p']}</p>
      <a class="more" href="{docs}terminal.md">{t['term_more']} →</a>
    </div>
    <div class="shots shots-term">{term}</div>
  </div>
</section>
</main>
"""
    return shell(t, "", t["title"], t["desc"], body, ld=ld, page_js=True)


SUBPAGES = ("", "whats-new/", "help/")


def shell(t: dict, sub: str, title: str, desc: str, body: str, ld: dict | None = None, page_js=False) -> str:
    depth = (1 if t["path"] else 0) + (1 if sub else 0)
    p = "../" * depth                       # до кореня сайту
    home = p + t["path"]                    # головна сторінка цієї мови
    url = SITE + t["path"] + sub
    other = SITE + t["other"] + sub
    olang = "uk" if t["lang"] == "en" else "en"
    nav = t["nav"]
    cur = {"whats-new/": 3, "help/": 4}.get(sub)
    links = [(home or "./") + "#features", (home or "./") + "#screenshots", (home or "./") + "#download",
             home + "whats-new/", home + "help/"]
    if not sub:
        links[:3] = ["#features", "#screenshots", "#download"]
    nav_html = "".join(f'<a href="{h}"{" aria-current=\"page\"" if i == cur else ""}>{n}</a>'
                       for i, (h, n) in enumerate(zip(links, nav)))
    dl_for = json.dumps(t["dl_for"], ensure_ascii=False)
    ld_html = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n' if ld else ""
    js = (f'<script>window.PLATIVKA = {{dlFor: {dl_for}, noList: {json.dumps(t["js_no"], ensure_ascii=False)}}};</script>\n'
          f'<script src="{p}site.js" defer></script>\n') if page_js else ""
    return f"""<!doctype html>
<html lang="{t['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="{t['lang']}" href="{url}">
<link rel="alternate" hreflang="{olang}" href="{other}">
<link rel="alternate" hreflang="x-default" href="{SITE + sub}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}img/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#f6f3ee">
<link rel="icon" type="image/png" href="{p}img/favicon.png">
<link rel="apple-touch-icon" href="{p}img/icon-256.png">
<link rel="stylesheet" href="{p}site.css">
{ld_html}</head>
<body>
<header class="top">
  <div class="wrap top-in">
    <a class="brand" href="{home or './'}"><img src="{p}img/icon-256.png" alt="" width="32" height="32">Plativka</a>
    <nav aria-label="Main">{nav_html}</nav>
    <a class="lang" href="{p}{t['other']}{sub}" hreflang="{olang}">{t['other_label']}</a>
  </div>
</header>

{body}
<footer class="foot">
  <div class="wrap foot-in">
    <p><a href="{REPO}">GitHub</a> · <a href="https://sourceforge.net/projects/plativka/">SourceForge</a> · <a href="https://alternativeto.net/software/plativka/about/">AlternativeTo</a> · <a href="{home}whats-new/">{nav[3]}</a> · <a href="{home}help/">{nav[4]}</a> · <a href="{REPO}/issues">{t['foot'][1]}</a> · <a href="{REPO}/blob/main/{t['readme']}">{t['foot'][2]}</a></p>
    <p class="muted">{t['foot_note']}</p>
  </div>
</footer>
{js}</body>
</html>
"""


# ───────────── «Що нового» з CHANGELOG.md ─────────────
def changelog(lang: str) -> list[tuple[str, str]]:
    """[(версія, html списку змін)] мовою lang, найновіша перша."""
    import markdown
    text = (ROOT / "CHANGELOG.md").read_text("utf-8")
    want = "**English**" if lang == "en" else "**Українська**"
    out = []
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        ver, _, rest = block.partition("\n")
        parts = re.split(r"^\*\*(?:English|Українська)\*\*\s*$", rest, flags=re.M)
        heads = re.findall(r"^(\*\*(?:English|Українська)\*\*)\s*$", rest, flags=re.M)
        body = dict(zip(heads, parts[1:])).get(want, rest)
        out.append((ver.strip(), markdown.markdown(body.strip())))
    return out


def page_changelog(t: dict) -> str:
    items = []
    for i, (ver, body) in enumerate(changelog(t["lang"])):
        badge = f' <span class="badge">{t["cl_latest"]}</span>' if i == 0 else ""
        items.append(f'<section class="ver-block" id="v{ver}"><h2>{ver}{badge}</h2>{body}</section>')
    body = f"""<main class="wrap sec prose">
  <h1>{t['cl_title']}</h1>
  <p class="sub">{t['cl_lead']} <a href="{LATEST}">{t['cl_dl']} →</a></p>
  {''.join(items)}
</main>
"""
    return shell(t, "whats-new/", t["cl_title"] + " — Plativka", t["cl_lead"], body)


# ───────────── «Допомога» з docs/<мова>/troubleshooting.md ─────────────
def page_help(t: dict) -> str:
    import markdown
    md = (DOCS / t["lang"] / "troubleshooting.md").read_text("utf-8")
    md = re.sub(r"\A# .*\n+(\[.*\n+)?", "", md)       # заголовок і рядок «мова · назад»
    base = f"{REPO}/blob/main/docs/{t['lang']}/"

    def fix(m):
        href = m.group(2)
        if re.match(r"[a-z]+://|#|mailto:", href):
            return m.group(0)
        if href.startswith("../../"):
            return f"]({REPO}/blob/main/{href[6:]})"
        return f"]({base}{href})"
    md = re.sub(r"\]\((([^)]+))\)", fix, md)
    m = markdown.Markdown(extensions=["toc", "fenced_code", "tables"], extension_configs={"toc": {"toc_depth": "2"}})
    body_html = m.convert(md)
    toc = "".join(f'<li><a href="#{e["id"]}">{e["name"]}</a></li>' for e in m.toc_tokens)
    body = f"""<main class="wrap sec prose">
  <h1>{t['help_title']}</h1>
  <p class="sub">{t['help_lead']}</p>
  <nav class="toc" aria-label="{t['help_toc']}"><h2>{t['help_toc']}</h2><ul>{toc}</ul></nav>
  {body_html}
  <p class="help-more">{t['help_more'].format(issues=REPO + "/issues/new/choose")}</p>
</main>
"""
    return shell(t, "help/", t["help_title"] + " — Plativka", t["help_lead"], body)


def main():
    from PIL import Image
    (DOCS / "uk").mkdir(exist_ok=True)
    for t in T.values():
        (DOCS / t["path"] / "index.html").write_text(page(t), encoding="utf-8")
        for sub, fn in (("whats-new/", page_changelog), ("help/", page_help)):
            (DOCS / t["path"] / sub).mkdir(parents=True, exist_ok=True)
            (DOCS / t["path"] / sub / "index.html").write_text(fn(t), encoding="utf-8")
    (DOCS / ".nojekyll").write_text("")
    (DOCS / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n")
    urls = "".join(
        f"  <url><loc>{SITE}{t['path']}{sub}</loc>"
        + "".join(f'<xhtml:link rel="alternate" hreflang="{o["lang"]}" href="{SITE}{o["path"]}{sub}"/>' for o in T.values())
        + "</url>\n" for sub in SUBPAGES for t in T.values())
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + urls + "</urlset>\n")
    icon = Image.open(ROOT / "packaging" / "icons" / "plativka.png").convert("RGBA")
    icon.resize((256, 256), Image.LANCZOS).save(DOCS / "img" / "icon-256.png", optimize=True)
    icon.resize((64, 64), Image.LANCZOS).save(DOCS / "img" / "favicon.png", optimize=True)


if __name__ == "__main__":
    main()
