#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Збирає Plativka.app і DMG для macOS. Запускається на Mac (локально або в GitHub Actions).
#
#  Усередині програми: Python + бібліотеки (PyInstaller), mpv (офіційна збірка
#  з GitHub mpv-player/mpv), Kitty (вікно плеєра з обкладинками) з назвою й іконкою
#  Платівки. Користувачу нічого не треба встановлювати окремо.
#
#  Використання:  packaging/macos/build_app.sh <arm64|x86_64>
#  Потрібні змінні: MPV_ZIP_URL, KITTY_DMG_URL (див. .github/workflows/release.yml)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
ARCH="${1:?arm64 або x86_64}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(python3 -c 'import re;print(re.search(r"__version__ = \"(.+?)\"",open("'"$ROOT"'/src/plativka/__init__.py").read()).group(1))')"
WORK="$ROOT/build/macos-$ARCH"
APP="$WORK/Plativka.app"
rm -rf "$WORK"; mkdir -p "$WORK"
cd "$WORK"

echo "→ Python-частина (PyInstaller)…"
python3 -m pip install -q --upgrade pip pyinstaller
python3 -m pip install -q "$ROOT"
python3 -m PyInstaller --noconfirm --clean --onedir --name plativka \
  --distpath "$WORK/dist" --workpath "$WORK/pyi" --specpath "$WORK" \
  --collect-all textual --collect-all textual_image --collect-data plativka \
  --collect-submodules plativka --collect-submodules rich --hidden-import segno --hidden-import certifi --collect-data certifi --collect-submodules send2trash \
  --exclude-module numpy --exclude-module yaml --exclude-module chardet \
  --exclude-module charset_normalizer --exclude-module tkinter --exclude-module pytest \
  "$ROOT/packaging/pyinstaller/plativka_entry.py"

echo "→ Структура Plativka.app…"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
mv "$WORK/dist/plativka" "$APP/Contents/Resources/player"
cp "$ROOT/packaging/icons/plativka.icns" "$APP/Contents/Resources/plativka.icns"
cp "$ROOT/packaging/kitty/plativka.conf" "$APP/Contents/Resources/kitty.conf"
cp "$ROOT/LICENSE" "$ROOT/THIRD_PARTY_LICENSES.md" "$APP/Contents/Resources/"

echo "→ mpv…"
curl -fsSL "$MPV_ZIP_URL" -o mpv.zip
mkdir -p mpvx && ditto -x -k mpv.zip mpvx
# офіційний zip містить ще й вкладений tar.gz — розпаковуємо все, що є
find mpvx -maxdepth 2 \( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.tar.xz' \) -exec tar -xf {} -C mpvx \;
MPV_APP="$(find mpvx -maxdepth 4 -name 'mpv.app' -type d | head -1)"
[ -n "$MPV_APP" ] || { echo "У архіві mpv не знайдено mpv.app"; find mpvx -maxdepth 3; exit 1; }
ditto "$MPV_APP" "$APP/Contents/Resources/mpv.app"

echo "→ Kitty…"
curl -fsSL "$KITTY_DMG_URL" -o kitty.dmg
MNT="$(mktemp -d)"
hdiutil attach -nobrowse -readonly -mountpoint "$MNT" kitty.dmg >/dev/null
ditto "$MNT/kitty.app" "$APP/Contents/Resources/kitty.app"
hdiutil detach "$MNT" >/dev/null
# Вікно плеєра має називатися «Платівка» й мати нашу іконку, а не Kitty
KP="$APP/Contents/Resources/kitty.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleName Plativka" "$KP"
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName Plativka" "$KP" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string Plativka" "$KP"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier io.github.dkindratyuk-web.plativka.window" "$KP"
KICON="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIconFile' "$KP" 2>/dev/null || echo kitty.icns)"
case "$KICON" in *.icns) ;; *) KICON="$KICON.icns" ;; esac
cp "$ROOT/packaging/icons/plativka.icns" "$APP/Contents/Resources/kitty.app/Contents/Resources/$KICON"
for lp in "$APP"/Contents/Resources/kitty.app/Contents/Resources/*.lproj/InfoPlist.strings; do
  [ -f "$lp" ] && rm -f "$lp"
done

echo "→ Запускач та Info.plist…"
cat > "$APP/Contents/MacOS/Plativka" <<'EOF'
#!/bin/bash
# Відкриває плеєр у власному вікні (вбудований Kitty з налаштуваннями Платівки).
R="$(cd "$(dirname "$0")/../Resources" && pwd)"
export PLATIVKA_MPV="$R/mpv.app/Contents/MacOS/mpv"
exec "$R/kitty.app/Contents/MacOS/kitty" --config "$R/kitty.conf" --title "Plativka" \
     --directory "$HOME" "$R/player/plativka" "$@"
EOF
chmod +x "$APP/Contents/MacOS/Plativka"

cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Plativka</string>
  <key>CFBundleDisplayName</key><string>Plativka</string>
  <key>CFBundleIdentifier</key><string>io.github.dkindratyuk-web.plativka</string>
  <key>CFBundleVersion</key><string>$VERSION</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleExecutable</key><string>Plativka</string>
  <key>CFBundleIconFile</key><string>plativka.icns</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleDevelopmentRegion</key><string>en</string>
  <key>CFBundleLocalizations</key><array><string>en</string><string>uk</string></array>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>LSApplicationCategoryType</key><string>public.app-category.music</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
EOF
mkdir -p "$APP/Contents/Resources/uk.lproj" "$APP/Contents/Resources/en.lproj"
printf '"CFBundleName" = "Платівка";\n"CFBundleDisplayName" = "Платівка";\n' > "$APP/Contents/Resources/uk.lproj/InfoPlist.strings"
printf '"CFBundleName" = "Plativka";\n"CFBundleDisplayName" = "Plativka";\n' > "$APP/Contents/Resources/en.lproj/InfoPlist.strings"

echo "→ Підпис (ad-hoc, без сертифіката Apple)…"
codesign --force --deep --sign - "$APP/Contents/Resources/mpv.app"
codesign --force --deep --sign - "$APP/Contents/Resources/kitty.app"
codesign --force --deep --sign - "$APP"

echo "→ Перевірка: плеєр і mpv запускаються…"
"$APP/Contents/Resources/player/plativka" --help | head -2
"$APP/Contents/Resources/mpv.app/Contents/MacOS/mpv" --version | head -1

echo "→ DMG…"
DMGROOT="$WORK/dmg"
mkdir -p "$DMGROOT"
ditto "$APP" "$DMGROOT/Plativka.app"
ln -s /Applications "$DMGROOT/Applications"
cp "$ROOT/packaging/macos/FIRST-LAUNCH.txt" "$DMGROOT/First launch — Перший запуск.txt"
OUT="$ROOT/dist"; mkdir -p "$OUT"
DMG="$OUT/Plativka-$VERSION-macos-$ARCH.dmg"
rm -f "$DMG"
hdiutil create -volname "Plativka $VERSION" -srcfolder "$DMGROOT" -ov -format UDZO "$DMG" >/dev/null
echo "✓ $DMG"
