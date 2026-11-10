#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Платівка / Plativka — встановлення на Linux
#  Debian / Ubuntu / Mint · Fedora · Arch / Manjaro / EndeavourOS · openSUSE
#
#  Запуск:   ./install.sh              консольна Платівка (у вікні kitty)
#            ./install.sh --desktop    ще й віконна версія (Qt) — «Plativka Desktop» у меню
#  Що робить:
#    1. Ставить системні пакети: mpv (звук), kitty (вікно плеєра з обкладинками),
#       Python 3, libnotify (сповіщення). Спитає пароль sudo.
#    2. Створює окреме середовище Python у ~/.local/share/plativka
#    3. Додає команду `plativka` і ярлик у меню програм.
#  Нічого не змінює поза вашою домашньою текою, крім встановлення пакетів.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# Мова повідомлень: українська, якщо система українська; інакше англійська.
case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in uk*) UK=1 ;; *) UK= ;; esac
t()    { if [ -n "$UK" ]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }
say()  { printf '\033[1;36m→\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m✓\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# корінь проєкту: або поруч зі скриптом (архів релізу), або ../.. (репозиторій)
if   [ -f "$HERE/pyproject.toml" ];        then ROOT="$HERE"
elif [ -f "$HERE/../../pyproject.toml" ];  then ROOT="$(cd "$HERE/../.." && pwd)"
else die "$(t "Не знайдено файлів плеєра поруч зі скриптом. Розпакуйте архів повністю." "Player files not found next to the script. Unpack the whole archive.")"; fi

DESKTOP=
for a in "$@"; do [ "$a" = "--desktop" ] && DESKTOP=1; done

[ "$(id -u)" -eq 0 ] && die "$(t "Запускайте без sudo: ./install.sh (пароль спитають лише для пакетів)." "Run without sudo: ./install.sh (the password is asked only for packages).")"

# ── 1. Системні пакети ──
. /etc/os-release 2>/dev/null || true
ids=" ${ID:-} ${ID_LIKE:-} "
SUDO="sudo"; command -v sudo >/dev/null || SUDO=""

if [ -n "${PLATIVKA_SKIP_PACKAGES:-}" ]; then
  say "$(t "Пропускаю встановлення системних пакетів (PLATIVKA_SKIP_PACKAGES)." "Skipping system packages (PLATIVKA_SKIP_PACKAGES).")"
elif [[ "$ids" == *" arch "* || "$ids" == *" manjaro "* || "$ids" == *" endeavouros "* || "$ids" == *" cachyos "* ]]; then
  say "Arch: $(t "встановлюю" "installing") mpv, kitty, python, libnotify, zenity…"
  $SUDO pacman -S --needed --noconfirm mpv kitty python libnotify zenity
elif [[ "$ids" == *" fedora "* || "$ids" == *" rhel "* || "$ids" == *" centos "* ]]; then
  say "Fedora: $(t "встановлюю" "installing") mpv, kitty, python3, libnotify, zenity…"
  if ! $SUDO dnf install -y mpv kitty python3 libnotify zenity; then
    say "$(t "mpv немає в стандартних репозиторіях — підключаю RPM Fusion (free)…" "mpv is not in the default repositories — enabling RPM Fusion (free)…")"
    $SUDO dnf install -y "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm"
    $SUDO dnf install -y mpv kitty python3 libnotify zenity
  fi
elif [[ "$ids" == *" suse "* || "$ids" == *" opensuse "* ]]; then
  say "openSUSE: $(t "встановлюю" "installing") mpv, kitty, python3, libnotify-tools, zenity…"
  $SUDO zypper --non-interactive install mpv kitty python3 libnotify-tools zenity
elif [[ "$ids" == *" debian "* || "$ids" == *" ubuntu "* ]]; then
  say "Debian/Ubuntu: $(t "встановлюю" "installing") mpv, kitty, python3-venv, libnotify-bin, zenity…"
  $SUDO apt-get update
  $SUDO apt-get install -y mpv kitty python3 python3-venv libnotify-bin zenity
else
  say "$(t "Невідомий дистрибутив" "Unknown distribution") (${ID:-?}). $(t "Встановіть вручну: mpv, kitty, python3 з venv, notify-send." "Install manually: mpv, kitty, python3 with venv, notify-send.")"
fi

# Віконна версія: бібліотеки, без яких Qt не відкриє вікно (xcb-cursor, EGL, xkbcommon)
if [ -n "$DESKTOP" ] && [ -z "${PLATIVKA_SKIP_PACKAGES:-}" ]; then
  say "$(t "Бібліотеки для вікна Qt…" "Libraries for the Qt window…")"
  if   [[ "$ids" == *" arch "* || "$ids" == *" manjaro "* || "$ids" == *" endeavouros "* || "$ids" == *" cachyos "* ]]; then
    $SUDO pacman -S --needed --noconfirm xcb-util-cursor libxkbcommon-x11 || true
  elif [[ "$ids" == *" fedora "* || "$ids" == *" rhel "* || "$ids" == *" centos "* ]]; then
    $SUDO dnf install -y xcb-util-cursor libxkbcommon-x11 mesa-libEGL || true
  elif [[ "$ids" == *" suse "* || "$ids" == *" opensuse "* ]]; then
    $SUDO zypper --non-interactive install libxcb-cursor0 libxkbcommon-x11-0 libEGL1 || true
  elif [[ "$ids" == *" debian "* || "$ids" == *" ubuntu "* ]]; then
    $SUDO apt-get install -y libxcb-cursor0 libxkbcommon-x11-0 libegl1 || true
  fi
fi

command -v mpv >/dev/null     || die "$(t "mpv не встановився. Без нього плеєр не гратиме звук." "mpv was not installed. The player cannot play sound without it.")"
command -v python3 >/dev/null || die "$(t "python3 не встановився." "python3 was not installed.")"
ok "$(t "Системні пакети на місці" "System packages are in place")"

# ── 2. Середовище Python ──
DEST="$HOME/.local/share/plativka"
BIN="$HOME/.local/bin"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"
mkdir -p "$DEST" "$BIN" "$APPS" "$ICONS"

say "$(t "Готую середовище Python (1–2 хвилини)…" "Preparing the Python environment (1–2 minutes)…")"
rm -rf "$DEST/venv"
python3 -m venv "$DEST/venv" || die "$(t "Не вдалося створити venv. На Debian/Ubuntu:" "Could not create a venv. On Debian/Ubuntu:") sudo apt install python3-venv"
"$DEST/venv/bin/pip" install -q --upgrade pip
if [ -n "$DESKTOP" ]; then
  say "$(t "Ставлю й віконну версію (Qt, ~150 МБ)…" "Installing the desktop version too (Qt, ~150 MB)…")"
  "$DEST/venv/bin/pip" install -q "$ROOT[desktop]"
else
  "$DEST/venv/bin/pip" install -q "$ROOT"
fi
ok "$(t "Плеєр встановлено" "Player installed")"

# ── 3. Команда, вікно Kitty, ярлик ──
cp "$ROOT/packaging/kitty/plativka.conf" "$DEST/kitty.conf"
cp "$ROOT/packaging/icons/plativka.png" "$ICONS/plativka.png"

cat > "$BIN/plativka" <<EOF
#!/usr/bin/env bash
exec "$DEST/venv/bin/plativka" "\$@"
EOF
chmod +x "$BIN/plativka"

if command -v kitty >/dev/null; then
  EXEC="kitty --class plativka --title Plativka --config $DEST/kitty.conf $BIN/plativka"
  TERMINAL=false
else
  EXEC="$BIN/plativka"
  TERMINAL=true
fi
cat > "$APPS/plativka.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Plativka
Name[uk]=Платівка
GenericName=Music Player
GenericName[uk]=Музичний плеєр
Comment=Winamp-style music player
Comment[uk]=Музичний плеєр у дусі Winamp
Exec=$EXEC
Icon=plativka
Terminal=$TERMINAL
Categories=AudioVideo;Audio;Player;
Keywords=music;player;mp3;winamp;
StartupWMClass=plativka
EOF
if [ -n "$DESKTOP" ]; then
  cat > "$BIN/plativka-desktop" <<EOF
#!/usr/bin/env bash
exec "$DEST/venv/bin/plativka-desktop" "\$@"
EOF
  chmod +x "$BIN/plativka-desktop"
  cat > "$APPS/plativka-desktop.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Plativka Desktop
Name[uk]=Платівка (вікно)
GenericName=Music Player
GenericName[uk]=Музичний плеєр
Comment=Winamp-style music player in a window
Comment[uk]=Музичний плеєр у дусі Winamp у звичайному вікні
Exec=$BIN/plativka-desktop
Icon=plativka
Terminal=false
Categories=AudioVideo;Audio;Player;
Keywords=music;player;mp3;winamp;
StartupWMClass=Plativka
EOF
  ok "$(t "Ярлик «Платівка (вікно)» додано в меню програм" "\"Plativka Desktop\" added to the applications menu")"
fi
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q "${ICONS%/256x256/apps}" >/dev/null 2>&1 || true
ok "$(t "Ярлик «Платівка» додано в меню програм" "\"Plativka\" added to the applications menu")"

case ":$PATH:" in
  *":$BIN:"*) ;;
  *) for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
       [ -f "$rc" ] && ! grep -q 'local/bin' "$rc" && echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
     done
     say "$(t "Додав ~/.local/bin у PATH. Щоб команда plativka працювала в терміналі, відкрийте нове вікно терміналу." "Added ~/.local/bin to PATH. Open a new terminal window for the plativka command to work.")" ;;
esac

echo
if [ -n "$DESKTOP" ]; then
  ok "$(t "Готово! Запуск: знайдіть «Платівка (вікно)» в меню програм або наберіть plativka-desktop у терміналі." "Done! Start: find \"Plativka Desktop\" in the applications menu or type plativka-desktop in a terminal.")"
else
  ok "$(t "Готово! Запуск: знайдіть «Платівка» в меню програм або наберіть plativka у терміналі." "Done! Start: find \"Plativka\" in the applications menu or type plativka in a terminal.")"
fi
