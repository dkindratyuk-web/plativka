# Changelog / Історія змін

## 1.5.2

**English**

- Phone remote: the icon on the phone's Home Screen no longer has a white frame around it. If you already added the remote to the Home Screen, remove the icon and add the page again to get the new one.

**Українська**

- Пульт з телефона: іконка на головному екрані телефона більше не має білої рамки. Якщо ви вже додали пульт на головний екран, видаліть іконку й додайте сторінку ще раз, щоб з'явилася нова.

## 1.5.1

**English**

- Phone remote: coming back to the remote after switching apps (Safari or the icon on the Home Screen) no longer ends with a white screen or "cannot connect". The page is kept on the phone, so it opens at once even while the phone is still reconnecting to Wi-Fi, and then catches up with Plativka by itself.
- Phone remote: the protection against guessing the code now only stops new phones from connecting; the page and phones that are already connected keep working.
- The remote window: the QR code no longer touches the "Connected phones" label.
- The log (`plativka.log`) now says why a phone was refused, to make remote problems easier to sort out.
- A like or unlike made in the other edition at the same moment is no longer missed.

**Українська**

- Пульт з телефона: повернення до пульта після перемикання на інший застосунок (у Safari чи з іконки на головному екрані) більше не закінчується білим екраном або «не вдалося під'єднатися». Сторінка зберігається на телефоні, тож відкривається одразу, навіть поки телефон ще під'єднується до Wi-Fi, а потім сама наздоганяє Платівку.
- Пульт з телефона: захист від вгадування коду тепер не пускає лише нові телефони; сторінка й уже підключені телефони працюють далі.
- Вікно пульта: QR-код більше не злипається з написом «Підключені телефони».
- У журналі (`plativka.log`) тепер видно, чому телефону відмовлено, — так простіше розібратися з пультом.
- Лайк чи зняття лайка в іншій версії Платівки в ту саму мить більше не губиться.

## 1.5.0

**English**

- **Play next**: `Shift+N` (or right-click → **Play next**) puts a song — or a whole album from the library — right after the current one, without reordering the playlist. Several songs can wait in the queue (marked →1, →2…); on the phone remote, touch and hold a song.
- **Copy to a USB stick** (☰ → File, terminal `Shift+C`): numbered file names so a car stereo keeps your order; the size and free space are shown first; nothing is overwritten without asking; names are safe for any stick.
- **Find duplicates** (☰ → File, terminal `Shift+X`): identical files and the same song in different files (for example MP3 and FLAC of one album). The best copy is ticked to keep — liked, lossless, higher bitrate — and you can change it; the extras go from the playlist only (default) or to the Trash, never permanently.
- **Covers from the internet** (off by default; ☰ → View → **Find missing covers online**, terminal `Shift+O`): for tracks with no cover in the file or folder, from MusicBrainz / Cover Art Archive, with Apple as a fallback. Only a confident match is used (Cyrillic and Latin spellings count: Океан Ельзи = Okean Elzy); **Find cover art…** lets you pick one yourself from up to six. Only the artist and album name are sent; found covers are cached and work offline.
- **The phone remote looks like Plativka**: tinted by the cover, the seven-segment clock, the same buttons, light or dark like the player on the computer; a sharper cover. The remote window on the computer is more compact, and the code is shown in large digits.
- The guides now describe favorites and smart lists (added in 1.4.0) in full.

**Українська**

- **Грати наступним**: `Shift+N` (або правий клік → **Грати наступним**) ставить пісню — чи цілий альбом із медіатеки — одразу після поточної, не змінюючи порядок списку. У черзі можуть чекати кілька пісень (позначені →1, →2…); на пульті з телефона — утримуйте пісню.
- **Копіювати на флешку** (☰ → Файл, консольна `Shift+C`): нумеровані назви, щоб магнітола тримала ваш порядок; спершу видно розмір і вільне місце; без питання нічого не перезаписується; назви безпечні для будь-якої флешки.
- **Знайти дублікати** (☰ → Файл, консольна `Shift+X`): однакові файли й та сама пісня в різних файлах (наприклад, MP3 і FLAC одного альбому). Галочкою позначено найкращу копію — улюблену, без втрат, з вищим бітрейтом — і її можна змінити; зайві прибираються лише зі списку (за замовчуванням) або в Кошик, ніколи назавжди.
- **Обкладинки з інтернету** (за замовчуванням вимкнено; ☰ → Вигляд → **Шукати обкладинки в інтернеті**, консольна `Shift+O`): для треків без обкладинки у файлі чи теці — з MusicBrainz / Cover Art Archive, запасний варіант — Apple. Береться лише впевнений збіг (кирилиця й латиниця теж: Океан Ельзи = Okean Elzy); **Знайти обкладинку…** дає обрати самому з шести варіантів. Надсилається лише виконавець і назва альбому; знайдені обкладинки лежать у кеші й працюють без інтернету.
- **Пульт з телефона схожий на Платівку**: підфарбований кольором обкладинки, семисегментний годинник, ті самі кнопки, світлий чи темний — як плеєр на комп'ютері; чіткіша обкладинка. Вікно пульта на комп'ютері компактніше, а код — великими цифрами.
- В інструкціях тепер повністю описано улюблені й розумні списки (з'явилися в 1.4.0).

## 1.4.1

**English**

- Phone remote: the page no longer stays white or shows “cannot connect to the server” when you come back to it. The phone opens several connections at once, and the protection added in 1.3.7 cut the extra ones; now they wait for their turn.
- If the remote page ever can't load, it says so and asks you to reload instead of staying blank.

**Українська**

- Пульт з телефона: сторінка більше не лишається білою й не пише «не вдалося під'єднатися до сервера», коли повертаєтеся до неї. Телефон відкриває кілька з'єднань водночас, а захист, доданий у 1.3.7, обривав зайві; тепер вони чекають своєї черги.
- Якщо сторінка пульта все ж не завантажилась, вона про це пише й просить оновити її, а не лишається порожньою.

## 1.4.0

**English**

- Favorites: like a song with the ♡ in the playlist, `F`, the Favorites menu, the tray or the phone remote, and play only your favorites (`Shift+F` or **♥ Favorites** at the top of the library). A filled ♥ is shown only for liked songs; an empty ♡ only on the row under the mouse/cursor or the selected one.
- Likes survive moving and renaming files: after a library scan Plativka finds the song by artist, title and length and moves the like to the new place.
- Smart lists at the top of the library: Recently added, Most played, Not played for a while — from the play history kept only on your computer.
- Remove non-favorites: from the list only (the default) or from the list and the disk — to the Trash, never permanently; songs that haven't played yet are kept by default.
- Save favorites as an M3U playlist.

**Українська**

- Улюблені: вподобайте пісню сердечком ♡ у списку, клавішею `F`, з меню «Улюблені», трею чи пульта з телефона — і слухайте лише улюблені (`Shift+F` або **♥ Улюблені** нагорі медіатеки). Заповнене ♥ видно лише біля вподобаних; порожнє ♡ — лише на рядку під мишкою/курсором чи на виділеному.
- Лайки не губляться при перенесенні й перейменуванні файлів: після сканування медіатеки Платівка знаходить пісню за виконавцем, назвою й тривалістю й переносить лайк на нове місце.
- Розумні списки нагорі медіатеки: «Нещодавно додані», «Найчастіше слухаю», «Давно не звучали» — з історії прослуховувань, яка зберігається лише на вашому комп'ютері.
- «Прибрати неулюблені»: лише зі списку (за замовчуванням) або зі списку й з диска — у Кошик, ніколи назавжди; пісні, які ще не звучали, за замовчуванням лишаються.
- Зберегти улюблені як плейлист M3U.

## 1.3.7

**English**

- Phone remote: control Plativka from a phone on the same Wi-Fi — scan the QR code, nothing to install. Pause, previous/next, seek, volume, sleep timer and any track from the playlist. Off until you turn it on; only phones you paired and only from your home network. Plativka Desktop: ☰ → Playback → Phone remote; terminal: `F3`.

**Українська**

- Пульт з телефона: керуйте Платівкою з телефона в тій самій Wi-Fi-мережі — відскануйте QR-код, нічого встановлювати не треба. Пауза, назад/далі, перемотування, гучність, таймер сну і будь-який трек зі списку. Вимкнено, доки ви не ввімкнете; лише телефони, які ви підключили, і лише з домашньої мережі. Віконна версія: ☰ → Відтворення → Пульт з телефона; консольна: `F3`.

## 1.3.6

**English**

- Gapless playback: tracks follow each other without a pause, as on the album (both editions).
- Volume levelling with ReplayGain: by album (default), by track or off — Plativka Desktop: ☰ → Playback; terminal: `G`.
- Albums as one file with a `.cue` sheet (FLAC, APE, WAV, WavPack) are shown as separate tracks and play without gaps; `.cue` files in UTF-8 or Windows-1251.
- Sleep timer: 15–90 minutes or after the current track, with a fade-out — Plativka Desktop: ☰ → Playback → Sleep timer; terminal: `K`.
- Update check: once a day Plativka asks GitHub whether a new version is out and shows "⬆ 1.x.x" next to shuffle and repeat. Can be turned off.
- APE and WavPack files are now recognised.
- macOS: the app icon is now the same size as other icons in the Dock (it has the standard margins and shadow).

**Українська**

- Без пауз між треками (gapless): треки йдуть один за одним, як на альбомі (обидві версії).
- Вирівнювання гучності за ReplayGain: за альбомом (типово), за треком або вимкнено — у віконній версії ☰ → Відтворення, у консольній — `G`.
- Альбоми одним файлом з `.cue` (FLAC, APE, WAV, WavPack) показуються окремими треками й грають без пауз; `.cue` в UTF-8 або Windows-1251.
- Таймер сну: 15–90 хвилин або після поточного треку, з м'яким стишуванням — у віконній версії ☰ → Відтворення → Таймер сну, у консольній — `K`.
- Перевірка оновлень: раз на добу Платівка питає GitHub, чи вийшла нова версія, і показує «⬆ 1.x.x» поруч із перемішуванням і повтором. Можна вимкнути.
- Тепер розпізнаються файли APE і WavPack.
- macOS: іконка програми тепер такого ж розміру, як інші в доці (зі стандартними полями й тінню).

## 1.3.5

**English**

- Plativka Desktop: the ☰ menu, right-click menus, dialogs and tooltips now follow the theme — in the dark theme the menu text was white on a white menu (Windows, Linux).
- Linux: after `./install.sh --desktop` the script points to "Plativka Desktop" in the menu.
- Documentation: install guides for both editions on every system, a new Plativka Desktop guide, a separate guide for the terminal edition.

**Українська**

- Віконна Платівка: меню ☰, контекстні меню, діалоги й підказки тепер у кольорах теми — у темній темі текст меню був білим на білому (Windows, Linux).
- Linux: після `./install.sh --desktop` скрипт підказує шукати в меню «Платівка (вікно)».
- Документація: інструкції зі встановлення обох версій для кожної системи, новий посібник для віконної Платівки, окремий посібник для консольної версії.

## 1.3.4

**English**

- Windows installers (both versions) close a running Plativka before updating, so the update no longer stops with "DeleteFile failed; code 5. Access is denied."

**Українська**

- Інсталятори для Windows (обидві версії) самі закривають запущену Платівку перед оновленням — більше немає помилки «DeleteFile збій; код 5. Access is denied».

## 1.3.3

**English**

- Plativka Desktop on macOS: track notifications show the album cover again — they now come from the app itself ("Plativka Desktop"), not from Script Editor. The first time macOS asks to allow notifications.

**Українська**

- Віконна Платівка на macOS: у сповіщеннях про трек знову є обкладинка — тепер їх надсилає сама програма («Plativka Desktop»), а не «Редактор скриптів». Уперше macOS спитає дозвіл на сповіщення.

## 1.3.2

**English**

- Plativka Desktop: new sound visualisation — vertical LED-style columns (left channel on the left, right on the right, the newest in the middle), in both the full and the compact view.
- The whole window now takes its colour from the album cover, not only the clock panel.
- Compact view and mini player are much tighter: less empty space, equal-sized title, buttons and sliders.
- macOS: playlist rows use the same compact font as the rest; the empty grey bar at the bottom of the window is gone.

**Українська**

- Віконна Платівка: нова візуалізація звуку — вертикальні «світлодіодні» стовпчики (ліворуч лівий канал, праворуч правий, найсвіжіше — посередині), і у великому, і в компактному вигляді.
- Тепер усе вікно, а не лише табло, бере колір з обкладинки.
- Компактний вигляд і міні-плеєр значно щільніші: менше порожнього місця, назва, кнопки й повзунки одного масштабу.
- macOS: рядки списку тим самим компактним шрифтом, що й решта; порожня сіра смуга внизу вікна зникла.

## 1.3.1

**English**

- Plativka Desktop: much more compact — smaller fonts, buttons, rows, cover and clock, closer to the terminal version.
- The playlist/library panel and the selected row now take their colour from the album cover too.
- Same-looking drawn button icons on every system (no colourful emoji buttons on Windows).
- Windows 11: the translucent Mica background is switched on before the window appears (it did not show in 1.3.0).

**Українська**

- Віконна Платівка: набагато компактніша — менші шрифти, кнопки, рядки, обкладинка й годинник, ближче до консольної версії.
- Панель списку/медіатеки й виділений рядок тепер теж беруть колір з обкладинки.
- Однакові намальовані значки кнопок на всіх системах (без кольорових емодзі на Windows).
- Windows 11: напівпрозорий фон Mica вмикається до появи вікна (у 1.3.0 він не з'являвся).

## 1.3.0

**English**

- **New: Plativka Desktop (beta)** — the same player in a regular window (Qt): real covers on every system, LCD clock and level meter, playlist and library tabs with search, compact view (`W`), mini player (`E`) with "always on top", light/dark/auto theme coloured by the album cover, Mica background on Windows 11, tray icon, media keys, notifications with covers, system volume mirroring, drag and drop. Downloads: `Plativka-Desktop-…` DMG / installer; on Linux `./install.sh --desktop`.
- The terminal version is unchanged; its core (library, tags, covers, mpv) is now shared with the desktop version.

**Українська**

- **Нове: віконна Платівка (бета)** — той самий плеєр у звичайному вікні (Qt): справжні обкладинки на всіх системах, годинник-табло й індикатор рівня, вкладки списку й медіатеки з пошуком, компактний вигляд (`W`), міні-плеєр (`E`) з «поверх усіх вікон», світла/темна/системна тема з кольором обкладинки, фон Mica на Windows 11, трей, медіаклавіші, сповіщення з обкладинками, дзеркало системної гучності, перетягування тек. Завантаження: `Plativka-Desktop-…` DMG / інсталятор; на Linux — `./install.sh --desktop`.
- Консольна версія не змінилась; її ядро (медіатека, теги, обкладинки, mpv) тепер спільне з віконною.

## 1.2.1

**English**

- Mini player: no scrollbar and no clipped tab row when the window comes out a row shorter than asked (kitty with padding); the key row is hidden in the mini player so the strip is one line shorter.
- Screenshots from a real Mac on the GitHub page.

**Українська**

- Міні-плеєр: більше немає смуги прокрутки й обрізаного рядка вкладок, коли вікно виходить на рядок нижчим, ніж просили (kitty з відступами); рядок клавіш у міні-плеєрі схований, тож смужка на рядок нижча.
- Знімки зі справжнього Mac на сторінці GitHub.

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
