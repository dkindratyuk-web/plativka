"""Мова інтерфейсу: українська або англійська.

Рядки в коді пишуться українською й обгортаються в _(). Англійський переклад
береться зі словника EN за українським оригіналом. Мова визначається один раз
під час запуску: з налаштувань, інакше за мовою системи.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from . import sysdeps

LANGS = ("uk", "en")


def _system_lang() -> str:
    try:
        if sys.platform == "darwin":
            out = subprocess.run(["defaults", "read", "-g", "AppleLanguages"],
                                 capture_output=True, text=True, timeout=2).stdout
            first = out.replace("(", "").replace('"', "").split(",")[0].strip().lower()
            if first.startswith("uk"):
                return "uk"
        elif sys.platform == "win32":
            import ctypes
            if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x22:  # LANG_UKRAINIAN
                return "uk"
        for var in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
            v = os.environ.get(var, "")
            if v:
                return "uk" if v.lower().startswith("uk") else "en"
    except Exception:
        pass
    return "en"


def _configured_lang() -> str | None:
    # віконна версія має свої налаштування (desktop.json), консольна — config.json
    names = ("desktop.json", "config.json") if os.environ.get("PLATIVKA_UI") == "desktop" else ("config.json",)
    for name in names:
        try:
            cfg = json.loads((sysdeps.config_dir() / name).read_text("utf-8"))
        except Exception:
            continue
        v = cfg.get("lang")
        if v in LANGS:
            return v
    return None


def _pick() -> str:
    for a in sys.argv[1:]:
        if a.startswith("--lang="):
            v = a.split("=", 1)[1].lower()[:2]
            if v in LANGS:
                return v
    return _configured_lang() or _system_lang()


LANG = _pick()


def _(s: str) -> str:
    return EN.get(s, s) if LANG == "en" else s


def n_tracks(n: int) -> str:
    if LANG == "en":
        return f"{n} track" if n == 1 else f"{n} tracks"
    m = abs(n) % 100
    if 11 <= m <= 14:
        w = "треків"
    else:
        m %= 10
        w = "трек" if m == 1 else "треки" if 2 <= m <= 4 else "треків"
    return f"{n} {w}"


# Назва файлового менеджера в різних системах (для підказок про перетягування).
def file_manager_from() -> str:
    if LANG == "en":
        return {"darwin": "Finder", "win32": "File Explorer"}.get(sys.platform, "your file manager")
    return {"darwin": "Finder", "win32": "Провідника"}.get(sys.platform, "файлового менеджера")


EN: dict[str, str] = {
    # віконна версія (Qt)
    '+ Додати…': '+ Add…',
    'Автор: {a}': 'Author: {a}',
    'Виконавці': 'Artists',
    'Відтворення': 'Playback',
    'Грає: {what}': 'Playing: {what}',
    'Для звуку потрібен mpv.': 'mpv is required for sound.',
    'Додано в кінець списку: {n}': 'Added to the end of the playlist: {n}',
    'Додати в кінець списку': 'Add to the end of the playlist',
    'Додати теку до медіатеки…': 'Add a folder to the library…',
    'Додати теку до списку': 'Add a folder to the playlist',
    'Знайти': 'Find',
    'Знайти…': 'Find…',
    'Компактний вигляд': 'Compact view',
    'Ліцензія MIT. Звук — mpv, інтерфейс — Qt.': 'MIT license. Sound: mpv, interface: Qt.',
    'Медіатека порожня.\n\nДодайте теку з музикою кнопкою «+ Тека» або просто перетягніть теку у вікно.': 'The library is empty.\n\nAdd a music folder with the “+ Folder” button or just drag a folder into the window.',
    'Медіатека стане порожньою. Файли на диску й список відтворення залишаться.': 'The library will be empty. Files on disk and the playlist stay.',
    'Мова: українська ⇄ English': 'Language: українська ⇄ English',
    'Мову буде змінено після перезапуску Платівки.': 'The language will change after Plativka restarts.',
    'Музичний плеєр у дусі Winamp для macOS, Windows і Linux.': 'A Winamp-style music player for macOS, Windows and Linux.',
    'Міні-плеєр': 'Mini player',
    'Очистити список': 'Clear the playlist',
    'Перемішувати': 'Shuffle',
    'Пересканувати': 'Rescan',
    'Поверх усіх вікон': 'Always on top',
    'Повтор: вимк → усе → один': 'Repeat: off → all → one',
    'Повідомити про помилку': 'Report a bug',
    'Позначте теки й натисніть «Прибрати позначені». Файли на диску залишаться.': 'Tick folders and press “Remove checked”. Files on disk stay.',
    'Прибрати всі теки?': 'Remove all folders?',
    'Прибрати зі списку': 'Remove from the playlist',
    'Прибрати позначені': 'Remove checked',
    'Про Платівку': 'About Plativka',
    'Розгорнути': 'Expand',
    'Сканую медіатеку…': 'Scanning the library…',
    'Сповіщення про трек': 'Track notifications',
    'Теки': 'Folders',
    'Теки медіатеки…': 'Library folders…',
    'Теку — у список відтворення': 'Folder to the playlist',
    'Тема: авто → світла → темна': 'Theme: auto → light → dark',
    'Тема: світла': 'Theme: light',
    'Тема: темна': 'Theme: dark',
    'Тема: як у системі': 'Theme: as in the system',
    'Уся медіатека в список': 'Whole library to the playlist',
    'Файл': 'File',
    'гучн': 'vol',
    'сканую…': 'scanning…',
    # назва
    "Платівка": "Plativka",
    # загальне
    "Скасувати": "Cancel",
    " Скасувати ": " Cancel ",
    "Закрити": "Close",
    "Вийти": "Quit",
    "Вихід": "Quit",
    "демо, без звуку": "demo, no sound",
    "стерео": "stereo",
    "моно": "mono",
    "{kbps} кбіт/с": "{kbps} kbps",
    "{khz} кГц": "{khz} kHz",
    "Без тегів": "Untagged",
    "Трек": "Track",
    "Час": "Time",
    # головне вікно
    "рівні недоступні": "levels unavailable",
    "гучн ": "vol  ",
    "перемішати": "shuffle",
    "повтор: вимк": "repeat: off",
    "повтор: все": "repeat: all",
    "повтор: один": "repeat: one",
    "сповіщ: вимк": "popups: off",
    "сповіщ: плеєр": "popups: player",
    "сповіщ: {os}": "popups: {os}",
    "{app} {ver} — оберіть, що послухати": "{app} {ver} — pick something to play",
    # нижній рядок клавіш
    "Попер.": "Prev",
    "Грати": "Play",
    "Пауза": "Pause",
    "Стоп": "Stop",
    "Наст.": "Next",
    "−5 с": "−5 s",
    "+5 с": "+5 s",
    "Гучн+": "Vol+",
    "Гучн−": "Vol−",
    "Тека→медіатека": "Add folder",
    "Пошук": "Search",
    "Перемішати": "Shuffle",
    "Повтор": "Repeat",
    "Сповіщення": "Popups",
    "Медіатека": "Library",
    "Тема": "Theme",
    "Обкладинка": "Cover",
    "Усе в список": "Play all",
    "Мова": "Language",
    "У трей": "To tray",
    # список відтворення
    "Список відтворення": "Playlist",
    "Прибрати": "Remove",
    " + Тека ": " + Folder ",
    " − Прибрати ": " − Remove ",
    " Очистити ": " Clear ",
    " Знайти ": " Search ",
    "Список порожній.\n\nОберіть альбом чи теку в медіатеці й натисніть Enter або P, "
    "або додайте теку кнопкою «+ Тека» нижче.":
        "The playlist is empty.\n\nPick an album or folder in the library and press Enter or P, "
        "or add a folder with the «+ Folder» button below.",
    # медіатека
    " Виконавці ": " Artists ",
    " Теки ": " Folders ",
    " − Тека ": " − Folder ",
    " ▶ Усе ": " ▶ All ",
    "Грати вузол": "Play node",
    "Додати в список": "Add to playlist",
    "Медіатека порожня.\n\nДодайте теку з музикою: клавіша L або кнопка «+ Тека».\n\n"
    "Або просто перетягніть теку з {fm} у вікно плеєра.":
        "The library is empty.\n\nAdd a music folder: press L or the «+ Folder» button.\n\n"
        "Or just drag a folder from {fm} into the player window.",
    "сканую {i} з {total}…": "scanning {i} of {total}…",
    # діалоги
    "Оберіть теку стрілками або впишіть шлях. Можна перетягнути теку з {fm} у поле.":
        "Pick a folder with the arrow keys or type a path. You can also drag a folder from {fm} into the field.",
    " ↑ Вище ": " ↑ Up ",
    " Додати цю теку ": " Add this folder ",
    "Такої теки немає": "No such folder",
    "Знайти трек": "Find a track",
    "виконавець, назва або альбом…": "artist, title or album…",
    "Enter — грати  ·  ↓ — до результатів  ·  Esc — закрити":
        "Enter — play  ·  ↓ — to results  ·  Esc — close",
    "Додати теку до медіатеки": "Add a folder to the library",
    "Додати теку до списку відтворення": "Add a folder to the playlist",
    "Прибрати теку з медіатеки": "Remove a folder from the library",
    "✕ Прибрати всі теки ({n})": "✕ Remove all folders ({n})",
    "Прибрати всі теки з медіатеки?": "Remove all folders from the library?",
    "Медіатека стане порожньою. Файли на диску залишаться, список відтворення теж. "
    "Теки можна буде додати знову клавішею L.":
        "The library will be empty. Files on disk stay, and so does the playlist. "
        "You can add folders again with L.",
    "Прибрати всі": "Remove all",
    "Так": "Yes",
    "Медіатеку очищено: прибрано тек — {n} (файли не видалено)":
        "Library cleared: {n} folders removed (files were not deleted)",
    "Файли на диску залишаться. Esc — скасувати.": "Files on disk stay untouched. Esc — cancel.",
    "Потрібен mpv": "mpv is required",
    "Платівка відтворює звук через mpv, але його не знайдено.\n\n{how}\n\n"
    "Подивитися інтерфейс без звуку: plativka --demo":
        "Plativka plays sound through mpv, but it was not found.\n\n{how}\n\n"
        "To look at the interface without sound: plativka --demo",
    "Встановіть його командою:\n\n    {cmd}\n\nі запустіть плеєр знову.":
        "Install it with:\n\n    {cmd}\n\nand start the player again.",
    "Перевстановіть Платівку: mpv входить до інсталятора.":
        "Reinstall Plativka: mpv ships with the installer.",
    # повідомлення
    "Не вдалося запустити mpv: {e}": "Could not start mpv: {e}",
    "Список порожній — оберіть музику в медіатеці": "The playlist is empty — pick some music in the library",
    "Список відтворення закінчився. Повтор усього: клавіша R":
        "End of playlist. To repeat everything press R",
    "Трек обірвався на {pos} з {dur}: файл, схоже, обрізаний або пошкоджений. "
    "Вмикаю наступний.":
        "The track stopped at {pos} of {dur}: the file looks truncated or damaged. Playing the next one.",
    "Не вдалося відтворити {name}": "Could not play {name}",
    "Пауза ззовні: навушники, медіаклавіша або інша програма":
        "Paused from outside: headphones, a media key or another app",
    "Зараз грає": "Now playing",
    "Сповіщення про трек: у плеєрі": "Track popups: in the player",
    "Сповіщення про трек: лише системні ({os})": "Track popups: system only ({os})",
    "Сповіщення про трек вимкнено": "Track popups: off",
    "Обкладинка: звичайна": "Cover: normal",
    "Обкладинка: велика": "Cover: large",
    "Обкладинки вимкнено, замість них платівка": "Covers off — a spinning record instead",
    " (потрібне вікно від 30 рядків)": " (needs a window at least 30 rows tall)",
    "Додано {n}": "Added {n}",
    "У списку вся медіатека: {n}": "The whole library is in the playlist: {n}",
    "Медіатека порожня — додайте теку клавішею L": "The library is empty — add a folder with L",
    "«{name}» уже в медіатеці": "«{name}» is already in the library",
    "У медіатеці ще немає тек": "There are no folders in the library yet",
    "Теку прибрано з медіатеки (файли не видалено)": "Folder removed from the library (files were not deleted)",
    "Помилка сканування: {e}": "Scan error: {e}",
    "Медіатека оновлена: {n}": "Library updated: {n}",
    "Перетягніть теку з музикою або аудіофайли": "Drop a music folder or audio files",
    "Мова інтерфейсу: українська. Зміниться після перезапуску плеєра.":
        "Interface language: Ukrainian. Restart the player to apply.",
    "Мова інтерфейсу: англійська. Зміниться після перезапуску плеєра.":
        "Interface language: English. Restart the player to apply.",
    "Платівка грає далі в треї. Вийти можна з меню її іконки.":
        "Plativka keeps playing in the tray. Quit from its icon menu.",
    "Сховати в трей можна лише у власному вікні плеєра (ярлик «Платівка»), не у Windows Terminal.":
        "Hiding to the tray works only in the player's own window (the «Plativka» shortcut), not in Windows Terminal.",
    # трей
    "Показати плеєр": "Show player",
    "Грати / пауза": "Play / pause",
    "Наступний трек": "Next track",
    "Попередній трек": "Previous track",
    "Згортати в трей": "Minimize to tray",
    "Вийти з Платівки": "Quit Plativka",
    # 1.1.0
    "  ⇄  (після перезапуску)": "  ⇄  (after restart)",
    " + Додати… ": " + Add… ",
    " GitHub — сторінка проєкту ": " GitHub — project page ",
    " Закрити ": " Close ",
    " Повідомити про помилку ": " Report a bug ",
    " Прибрати всі ": " Remove all ",
    " Прибрати позначені ": " Remove checked ",
    " Теки… ": " Folders… ",
    " — недоступно, діє гучність плеєра": " — unavailable, the player's own volume is used",
    "J або /": "J or /",
    "Відкриваю в браузері: {url}": "Opening in the browser: {url}",
    "Гучність:": "Volume:",
    "Довідка": "Help",
    "Вигляд": "View",
    "Згорнути": "Collapse",
    " Список ": " Playlist ",
    " Медіатека ": " Library ",
    " ▴ згорнути ": " ▴ collapse ",
    " ▾ розгорнути ": " ▾ expand ",
    "Вигляд: компактний": "View: compact",
    "Вигляд: Winamp": "View: Winamp",
    "оберіть, що послухати": "pick something to play",
    "вигляд: Winamp ⇄ компактний": "view: Winamp ⇄ compact",
    "компактний вигляд: згорнути до смужки / розгорнути": "compact view: collapse to a strip / expand",
    "назад · пауза · далі (медіаклавіші Mac)": "previous · pause · next (Mac media keys)",
    "Клавіші": "Keys",
    "Мова:": "Language:",
    "Музичний плеєр у дусі Winamp. Автор: {author}. Безкоштовно, з відкритим кодом (MIT).":
        "A Winamp-style music player. Author: {author}. Free and open source (MIT).",
    "Налаштування": "Settings",
    "Оберіть теки з музикою для медіатеки": "Choose music folders for the library",
    "Оберіть теку для списку відтворення": "Choose a folder for the playlist",
    "Панель": "Panel",
    "Платівка на GitHub": "Plativka on GitHub",
    "Позначте теки пробілом або кліком і натисніть «Прибрати позначені». Файли на диску залишаться.":
        "Check folders with Space or a click and press «Remove checked». Files on disk stay untouched.",
    "Прибрано тек: {n} (файли не видалено)": "Folders removed: {n} (files were not deleted)",
    "Пробіл": "Space",
    "Список": "Playlist",
    "Тек ще немає. Натисніть «+ Додати…», щоб обрати теку з музикою.":
        "No folders yet. Press «+ Add…» to choose a music folder.",
    "Тека": "Folder",
    "Теки медіатеки": "Library folders",
    "У медіатеці": "In the library",
    "без звуку ": "muted ",
    "вийти": "quit",
    "грати виконавця / альбом / теку": "play the artist / album / folder",
    "грати трек разом з альбомом": "play the track with its album",
    "гучність": "volume",
    "додати в кінець списку": "add to the end of the playlist",
    "додати теку до медіатеки": "add a folder to the library",
    "знайти трек": "find a track",
    "мова інтерфейсу": "interface language",
    "назад · грати · пауза · стоп · далі": "previous · play · pause · stop · next",
    "обкладинка: звичайна → велика → вимкнена": "cover: normal → large → off",
    "окрема гучність плеєра": "the player's own volume",
    "пауза / продовжити": "pause / resume",
    "перейти між списком відтворення й медіатекою": "switch between the playlist and the library",
    "перемотати на 5 секунд": "seek 5 seconds",
    "перемішування / повтор": "shuffle / repeat",
    "показати / сховати медіатеку": "show / hide the library",
    "прибрати трек зі списку": "remove a track from the playlist",
    "світла / темна тема": "light / dark theme",
    "список відтворення / медіатека": "playlist / library",
    "сповіщення про трек": "track popups",
    "сховати в трей": "hide to the tray",
    "уся медіатека в список": "the whole library to the playlist",
    "ця довідка": "this help",
    "як у системі (клавіші гучності керують і плеєром)": "follows the system (volume keys control the player too)",
    " · K — змінити": " · K to change",
    "Вийшла Платівка {v} — натисніть «⬆ {v}», щоб завантажити": "Plativka {v} is out — click “⬆ {v}” to download it",
    "Вийшла Платівка {v}. Клавіша U — відкрити сторінку завантаження": "Plativka {v} is out. Press U to open the download page",
    "Вийшла нова версія — клацніть, щоб завантажити": "A new version is out — click to download it",
    "Вимкнено": "Off",
    "Вирівнювання гучності": "Volume levelling",
    "Вирівнювання гучності (ReplayGain)": "Volume levelling (ReplayGain)",
    "Вирівнювання гучності вимкнено": "Volume levelling is off",
    "Вирівнювання гучності: за альбомом": "Volume levelling: by album",
    "Вирівнювання гучності: за треком": "Volume levelling: by track",
    "За альбомом": "By album",
    "За треком": "By track",
    "Клацніть, щоб вимкнути таймер сну": "Click to turn the sleep timer off",
    "Оновлення": "Updates",
    "Перевірити оновлення…": "Check for updates…",
    "Перевіряти оновлення автоматично": "Check for updates automatically",
    "Перевіряю оновлення…": "Checking for updates…",
    "Після цього треку": "After this track",
    "Таймер сну": "Sleep timer",
    "Таймер сну вимкнено": "Sleep timer is off",
    "Таймер сну: зупиню після цього треку": "Sleep timer: stopping after this track",
    "Таймер сну: зупиню через {n} хв": "Sleep timer: stopping in {n} min",
    "Таймер сну: музику поставлено на паузу": "Sleep timer: the music is paused",
    "Таймер сну: трек закінчився, музику зупинено": "Sleep timer: the track has ended, the music is stopped",
    "У вас найновіша версія ({v})": "You have the latest version ({v})",
    "Через {n} хв": "In {n} min",
    "вирівнювання гучності: за альбомом · за треком · вимк": "volume levelling: by album · by track · off",
    "перевірити оновлення / завантажити нову версію": "check for updates / download the new version",
    "сон: {t}": "sleep: {t}",
    "сон: після треку": "sleep: after track",
    "таймер сну: 15 · 30 · 45 · 60 · 90 хв · після треку · вимк": "sleep timer: 15 · 30 · 45 · 60 · 90 min · after track · off",
}
