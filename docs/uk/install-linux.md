# Встановлення Платівки на Linux

[English](../en/install-linux.md) · [До README](../../README.uk.md)

Платівка встановлюється одним скриптом, який працює на **Debian, Ubuntu, Kubuntu, Linux Mint, Pop!_OS, Fedora, Arch, Manjaro, EndeavourOS, CachyOS і openSUSE**. Він ставить потрібні системні пакети, кладе плеєр у вашу домашню теку й додає його в меню програм. Нижче — кожен крок, досвід роботи з Linux не потрібен.

Той самий архів встановлює обидві версії:

| | **Віконна Платівка** (рекомендовано) | **Платівка для термінала** |
|---|---|---|
| Що це | звичайне вікно (Qt), справжні обкладинки | текстовий інтерфейс у власному вікні kitty, справжні обкладинки |
| Команда | `./install.sh --desktop` (ставить **обидві** версії) | `./install.sh` |
| У меню | **Платівка (вікно)** / **Plativka Desktop** | **Платівка** / **Plativka** |
| З термінала | `plativka-desktop` | `plativka` |

## Що встановлює скрипт

| Пакет | Для чого |
|---|---|
| `mpv` | відтворює звук |
| `kitty` | власне вікно консольної версії, що вміє показувати справжні обкладинки |
| `python3` (+ `python3-venv` на Debian/Ubuntu) | плеєр написаний на Python |
| `libnotify` / `notify-send` | сповіщення про трек |
| `zenity` | системне вікно вибору теки |
| бібліотеки Qt: `libxcb-cursor0`, `libxkbcommon-x11-0`, `libegl1` (назви різняться між системами) | лише з `--desktop`: вікно віконної Платівки |

Сам плеєр ставиться в `~/.local/share/plativka` і решти системи не чіпає. З `--desktop` скрипт ще завантажує туди Qt (близько 150 МБ).

## Крок 1. Завантаження

Відкрийте [останній реліз](https://github.com/dkindratyuk-web/plativka/releases/latest) і завантажте `plativka-…-linux.tar.gz`. Браузер покладе його в теку **Завантаження**.

## Крок 2. Відкрийте термінал

- **Ubuntu, Linux Mint, Pop!_OS, Debian (GNOME)**: натисніть **Ctrl + Alt + T**.
- **Fedora (GNOME)**: натисніть клавішу **Super** (Windows), наберіть `terminal`, натисніть **Enter**.
- **KDE Plasma** (Kubuntu, Fedora KDE, Manjaro KDE…): відкрийте меню, наберіть `konsole`, натисніть **Enter**.
- **Arch**: ви й так знаєте 🙂

Відкриється вікно з блимаючим курсором. Команди нижче набирайте (або вставляйте через **Ctrl + Shift + V**) у нього, після кожної — **Enter**.

## Крок 3. Розпакуйте і запустіть інсталятор

Скопіюйте ці рядки по одному (номер версії в назві може відрізнятися — `*` про це подбає):

```bash
cd ~/Завантаження
tar -xzf plativka-*-linux.tar.gz
cd plativka-*-linux
./install.sh --desktop      # віконна Платівка + консольна версія
```

Потрібна лише консольна версія? Запустіть `./install.sh` без `--desktop`.

> Якщо тека завантажень називається інакше (наприклад, `~/Downloads` в англомовній системі), використайте її в першому рядку: `cd ~/Downloads`.

Скрипт попросить **ваш пароль** — він потрібен, щоб встановити системні пакети. **Поки ви набираєте пароль, на екрані нічого не з'являється — так і має бути.** Наберіть його і натисніть Enter.

Встановлення триває 1–5 хвилин. Наприкінці з'явиться рядок, що починається з `✓ Готово!`.

## Крок 4. Запустіть Платівку

- Відкрийте меню програм і знайдіть **Платівка (вікно)** (в англомовній системі — **Plativka Desktop**) або **Платівка** для консольної версії.
- Або наберіть у терміналі `plativka-desktop` (чи `plativka`). Якщо команду не знайдено, спершу відкрийте нове вікно термінала.

Далі натисніть **L**, щоб додати теку з музикою, — або перетягніть теку з файлового менеджера у вікно Платівки. Решта: [як користуватися віконною Платівкою](desktop.md) · [консольною версією](terminal.md).

## Що саме відбувається на кожній системі

Це знадобиться, лише якщо скрипт не спрацював, — тоді команди можна виконати самому.

### Debian / Ubuntu / Kubuntu / Linux Mint / Pop!_OS

```bash
sudo apt update
sudo apt install mpv kitty python3 python3-venv libnotify-bin zenity
sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libegl1      # лише для віконної Платівки
```

### Fedora

```bash
sudo dnf install mpv kitty python3 libnotify zenity
sudo dnf install xcb-util-cursor libxkbcommon-x11 mesa-libEGL   # лише для віконної Платівки
```

Якщо `mpv` не знаходиться, скрипт спершу вмикає безкоштовний репозиторій RPM Fusion:

```bash
sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
sudo dnf install mpv
```

### Arch / Manjaro / EndeavourOS / CachyOS

```bash
sudo pacman -S --needed mpv kitty python libnotify zenity
sudo pacman -S --needed xcb-util-cursor libxkbcommon-x11        # лише для віконної Платівки
```

### openSUSE

```bash
sudo zypper install mpv kitty python3 libnotify-tools zenity
sudo zypper install libxcb-cursor0 libxkbcommon-x11-0 libEGL1   # лише для віконної Платівки
```

### Далі — на будь-якій системі

```bash
python3 -m venv ~/.local/share/plativka/venv
~/.local/share/plativka/venv/bin/pip install ".[desktop]"   # у розпакованій теці; "." — лише консольна версія
```

Скрипт також створює `~/.local/bin/plativka` (і `plativka-desktop`) та пункти меню в `~/.local/share/applications/`.

Пакети вже є або не хочете, щоб скрипт їх чіпав? Запустіть `PLATIVKA_SKIP_PACKAGES=1 ./install.sh --desktop`.

## Інтеграція з робочим столом

- **Медіаклавіші** (грати/пауза, наступний, попередній на клавіатурі чи навушниках) працюють самі, в обох версіях.
- **Віджет плеєра** в GNOME (верхня панель → сповіщення/календар) і KDE Plasma (системний лоток) показує трек і обкладинку та керує Платівкою. Так само працює `playerctl`.
- Сповіщення про трек показують обкладинку альбому.
- Віконна Платівка має ще й іконку в треї (KDE показує її одразу; у GNOME потрібне розширення AppIndicator, яке в Ubuntu є за замовчуванням).

## Оновлення

Завантажте новий архів і знову запустіть із нього `./install.sh --desktop` (або `./install.sh`). Медіатека, список і налаштування зберігаються.

## Видалення

З розпакованої теки:

```bash
./uninstall.sh          # прибирає обидві версії, налаштування й медіатеку лишає
./uninstall.sh --all    # прибирає й налаштування з медіатекою
```

Системні пакети (mpv, kitty, бібліотеки Qt) лишаються — ними можуть користуватися інші програми. За бажання видаліть їх менеджером пакетів.
