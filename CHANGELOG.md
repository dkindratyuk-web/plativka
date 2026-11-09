# Changelog / Історія змін

## 1.2.0

**English**

- **Compact view** (`W`), inspired by the Sonata player: a small player strip (cover, title, artist — album, one-line level meter, seek bar with time, buttons, volume) with the playlist and the library as tabs below.
- **Mini player** (`E`): collapses the compact view to the strip and shrinks the window (macOS DMG and Linux kitty window, the classic Windows console, Terminal.app, iTerm2, xterm); expanding restores the previous height.
- The view, tab and collapsed state are remembered. Linux: re-run the install script to let the window resize itself.

**Українська**

- **Компактний вигляд** (`W`), натхненний плеєром Sonata: невелика смужка плеєра (обкладинка, назва, виконавець — альбом, індикатор рівня в один рядок, смуга перемотування з часом, кнопки, гучність), під нею список і медіатека у вкладках.
- **Міні-плеєр** (`E`): згортає компактний вигляд до смужки й зменшує вікно (вікно Платівки на macOS і Linux, класична консоль Windows, Термінал macOS, iTerm2, xterm); розгортання повертає попередню висоту.
- Вигляд, вкладка й згорнутий стан запам'ятовуються. Linux: запустіть скрипт встановлення ще раз, щоб вікно могло саме змінювати розмір.

## 1.1.2

**English**

- **F7 F8 F9** = previous · pause · next while the Plativka window is in front — for keyboards that send these keys as plain F-keys instead of media keys.

**Українська**

- **F7 F8 F9** = назад · пауза · далі, коли вікно Платівки попереду, — для клавіатур, що надсилають ці клавіші як звичайні F-клавіші, а не медіаклавіші.

## 1.1.1

**English**

- **macOS media keys**: ⏯ (F8) now pauses and resumes — macOS sends it as a different key than Linux/Windows, and Plativka only resumed on it.
- **Covers in system notifications**: macOS (from the DMG — the notification now comes from "Plativka" with the cover), Windows (installer version — a Windows notification with the cover), Linux (the cover as the notification icon).

**Українська**

- **Медіаклавіші на macOS**: ⏯ (F8) тепер ставить на паузу й продовжує — macOS надсилає її іншою клавішею, ніж Linux/Windows, і Платівка лише продовжувала гру.
- **Обкладинки в системних сповіщеннях**: macOS (у DMG — сповіщення тепер від «Платівки» з обкладинкою), Windows (версія з інсталятора — сповіщення Windows з обкладинкою), Linux (обкладинка як іконка сповіщення).

## 1.1.0

**English**

- **Volume keys**: the player's volume now mirrors the system volume, so the volume keys on your keyboard (F11/F12 on a Mac) and the system sound slider move it, and `+` `−` in the player change the system volume. A separate player volume can be chosen in F1.
- **Windows media keys**: ⏯ ⏭ ⏮ on keyboards and headphones, plus the Windows media overlay with the track and cover.
- **Adding folders** opens the usual system folder dialog (Finder / Windows / GNOME, KDE); several folders at once on macOS and Linux. The in-player picker stays as a fallback.
- **Folders…** window: all library folders with track counts; remove checked ones or all of them, add more.
- **Clear navigation**: Tab / Shift+Tab / 1 / 2 move between the playlist and the library; the active panel has a bold frame and ●.
- **Help (F1 or ?)**: version, author, GitHub and bug-report buttons, volume and language settings, all keys. The tray menu on Windows also links to GitHub.
- The bottom key row and the volume bar adapt to the window width.
- Linux install script also installs `zenity` (folder dialog).

**Українська**

- **Клавіші гучності**: гучність плеєра тепер дзеркалить системну — клавіші гучності на клавіатурі (F11/F12 на Mac) і системний повзунок рухають її, а `+` `−` у плеєрі змінюють системну гучність. Окрему гучність плеєра можна обрати в F1.
- **Медіаклавіші на Windows**: ⏯ ⏭ ⏮ на клавіатурі й навушниках, а також панель мультимедіа Windows із треком і обкладинкою.
- **Додавання тек** відкриває звичайне системне вікно вибору (Finder / Windows / GNOME, KDE); на macOS і Linux — кілька тек одразу. Вибір усередині плеєра лишився як запасний.
- Вікно **Теки…**: усі теки медіатеки з кількістю треків; прибрати позначені чи всі, додати ще.
- **Зрозуміла навігація**: Tab / Shift+Tab / 1 / 2 — перехід між списком і медіатекою; активна панель має жирну рамку й ●.
- **Довідка (F1 або ?)**: версія, автор, кнопки GitHub і «Повідомити про помилку», налаштування гучності й мови, усі клавіші. У меню трею на Windows теж є посилання на GitHub.
- Нижній рядок клавіш і шкала гучності підлаштовуються під ширину вікна.
- Скрипт встановлення на Linux ставить і `zenity` (вікно вибору теки).

## 1.0.1

**English**

- Library: **− Folder** now offers **✕ Remove all folders** to empty the library in one go (with a confirmation). Files on disk and the playlist are not touched.

**Українська**

- Медіатека: у вікні **− Тека** з'явився пункт **✕ Прибрати всі теки** — спорожнює медіатеку одним рухом (після підтвердження). Файли на диску й список відтворення не чіпає.

## 1.0.0

**English**

First public release.

- Winamp-style layout: main window with a big clock, level meter and scrolling title; playlist; media library.
- macOS (DMG with everything inside, real covers in its own window), Windows (installer, tray icon), Linux (install script for Debian/Ubuntu, Fedora, Arch, openSUSE; MPRIS media keys and desktop widget).
- Folder library by artist → album or by folder; drag and drop; quick search; play the whole library.
- Colours follow the album cover; real covers in terminals that support images; a spinning record when covers are off.
- Track popups in the player or as system notifications.
- Tags from file names for untagged files; automatic fix for Windows-1251 tags.
- Detects truncated files and pauses from outside, and explains them.
- English and Ukrainian interface.

**Українська**

Перший публічний реліз.

- Розкладка Winamp: головне вікно з великим годинником, індикатором рівня й біжучим рядком; список відтворення; медіатека.
- macOS (DMG з усім усередині, справжні обкладинки у власному вікні), Windows (інсталятор, іконка в треї), Linux (скрипт для Debian/Ubuntu, Fedora, Arch, openSUSE; медіаклавіші й віджет робочого столу через MPRIS).
- Медіатека з тек за виконавцями → альбомами або за теками; перетягування; швидкий пошук; уся медіатека в список.
- Кольори під обкладинку альбому; справжні обкладинки в терміналах, що вміють картинки; платівка, що крутиться, коли обкладинки вимкнено.
- Сповіщення про трек у плеєрі або системні.
- Теги з імен файлів для треків без тегів; автоматичне виправлення тегів у Windows-1251.
- Розпізнає обрізані файли й паузу ззовні та пояснює, що сталося.
- Інтерфейс англійською та українською.
