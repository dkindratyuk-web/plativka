#!/usr/bin/env bash
# Платівка — видалення з Linux. Системні пакети (mpv, kitty) не чіпає.
set -eu
case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in uk*) UK=1 ;; *) UK= ;; esac
t() { if [ -n "$UK" ]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
rm -rf "$HOME/.local/share/plativka"
rm -f  "$HOME/.local/bin/plativka" "$HOME/.local/bin/plativka-desktop" \
       "$DATA/applications/plativka.desktop" "$DATA/applications/plativka-desktop.desktop" \
       "$DATA/icons/hicolor/256x256/apps/plativka.png"
echo "✓ $(t "Платівку видалено." "Plativka removed.")"
if [ "${1:-}" = "--all" ]; then
  rm -rf "${XDG_CONFIG_HOME:-$HOME/.config}/plativka" "${XDG_CACHE_HOME:-$HOME/.cache}/plativka"
  echo "✓ $(t "Налаштування, список і медіатеку теж видалено." "Settings, playlist and library removed too.")"
else
  echo "  $(t "Налаштування й медіатека залишились. Видалити й їх:" "Settings and library were kept. To remove them too:") ./uninstall.sh --all"
fi
