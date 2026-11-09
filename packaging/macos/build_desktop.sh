#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Збирає віконну Платівку (Qt) для macOS: Plativka Desktop.app і DMG.
#  Усередині: Python + Qt (PyInstaller) і mpv (офіційна збірка). Kitty не потрібен.
#
#  Використання:  packaging/macos/build_desktop.sh <arm64|x86_64>
#  Потрібна змінна: MPV_ZIP_URL (див. .github/workflows/release.yml)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
ARCH="${1:?arm64 або x86_64}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(python3 -c 'import re;print(re.search(r"__version__ = \"(.+?)\"",open("'"$ROOT"'/src/plativka/__init__.py").read()).group(1))')"
WORK="$ROOT/build/desktop-macos-$ARCH"
rm -rf "$WORK"; mkdir -p "$WORK"
cd "$WORK"

echo "→ Python + Qt (PyInstaller)…"
python3 -m pip install -q --upgrade pip pyinstaller
python3 -m pip install -q "$ROOT[desktop]"
python3 -m PyInstaller --noconfirm --clean --windowed --onedir --name "Plativka Desktop" \
  --icon "$ROOT/packaging/icons/plativka.icns" \
  --osx-bundle-identifier io.github.dkindratyuk-web.plativka.desktop \
  --distpath "$WORK/dist" --workpath "$WORK/pyi" --specpath "$WORK" \
  --collect-data plativka --collect-submodules plativka \
  --exclude-module textual --exclude-module textual_image --exclude-module rich \
  --exclude-module numpy --exclude-module yaml --exclude-module tkinter --exclude-module pytest \
  "$ROOT/packaging/pyinstaller/plativka_desktop_entry.py"
APP="$WORK/dist/Plativka Desktop.app"
[ -d "$APP" ] || { echo "PyInstaller не створив .app"; ls -la "$WORK/dist"; exit 1; }

echo "→ mpv…"
curl -fsSL "$MPV_ZIP_URL" -o mpv.zip
mkdir -p mpvx && ditto -x -k mpv.zip mpvx
find mpvx -maxdepth 2 \( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.tar.xz' \) -exec tar -xf {} -C mpvx \;
MPV_APP="$(find mpvx -maxdepth 4 -name 'mpv.app' -type d | head -1)"
[ -n "$MPV_APP" ] || { echo "У архіві mpv не знайдено mpv.app"; exit 1; }
ditto "$MPV_APP" "$APP/Contents/Resources/mpv.app"
cp "$ROOT/LICENSE" "$ROOT/THIRD_PARTY_LICENSES.md" "$APP/Contents/Resources/"

echo "→ Info.plist…"
P="$APP/Contents/Info.plist"
pb() { /usr/libexec/PlistBuddy -c "$1" "$P" 2>/dev/null || true; }
pb "Set :CFBundleDisplayName Plativka"; pb "Add :CFBundleDisplayName string Plativka"
pb "Set :CFBundleShortVersionString $VERSION"; pb "Set :CFBundleVersion $VERSION"
pb "Add :LSApplicationCategoryType string public.app-category.music"
pb "Add :LSMinimumSystemVersion string 12.0"
pb "Add :NSHighResolutionCapable bool true"
pb "Add :NSRequiresAquaSystemAppearance bool false"
pb "Add :CFBundleLocalizations array"; pb "Add :CFBundleLocalizations:0 string en"; pb "Add :CFBundleLocalizations:1 string uk"
mkdir -p "$APP/Contents/Resources/uk.lproj" "$APP/Contents/Resources/en.lproj"
printf '"CFBundleName" = "Платівка";\n"CFBundleDisplayName" = "Платівка";\n' > "$APP/Contents/Resources/uk.lproj/InfoPlist.strings"
printf '"CFBundleName" = "Plativka";\n"CFBundleDisplayName" = "Plativka";\n' > "$APP/Contents/Resources/en.lproj/InfoPlist.strings"

echo "→ Підпис (ad-hoc)…"
codesign --force --deep --sign - "$APP/Contents/Resources/mpv.app"
codesign --force --deep --sign - "$APP"

echo "→ Перевірка…"
"$APP/Contents/MacOS/Plativka Desktop" --help | head -2
"$APP/Contents/Resources/mpv.app/Contents/MacOS/mpv" --version | head -1

echo "→ DMG…"
DMGROOT="$WORK/dmg"; mkdir -p "$DMGROOT"
ditto "$APP" "$DMGROOT/Plativka Desktop.app"
ln -s /Applications "$DMGROOT/Applications"
cp "$ROOT/packaging/macos/FIRST-LAUNCH.txt" "$DMGROOT/First launch — Перший запуск.txt"
OUT="$ROOT/dist"; mkdir -p "$OUT"
DMG="$OUT/Plativka-Desktop-$VERSION-macos-$ARCH.dmg"
rm -f "$DMG"
hdiutil create -volname "Plativka Desktop $VERSION" -srcfolder "$DMGROOT" -ov -format UDZO "$DMG" >/dev/null
echo "✓ $DMG"
