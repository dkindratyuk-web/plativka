# ─────────────────────────────────────────────────────────────────────────────
#  Збирає інсталятор Платівки для Windows (Plativka-<версія>-windows-x64-setup.exe).
#  Усередині: Python + бібліотеки (PyInstaller), mpv (офіційна збірка), іконка.
#  Запускається на Windows (локально або в GitHub Actions). Потрібні: Python 3.12, Inno Setup 6.
#
#  Використання:  powershell -File packaging\windows\build.ps1 -MpvZipUrl <url>
# ─────────────────────────────────────────────────────────────────────────────
param([Parameter(Mandatory = $true)][string]$MpvZipUrl)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
$Version = (Select-String -Path "$Root\src\plativka\__init__.py" -Pattern '__version__ = "(.+?)"').Matches[0].Groups[1].Value
$Work = "$Root\build\windows"
if (Test-Path $Work) { Remove-Item -Recurse -Force $Work }
New-Item -ItemType Directory -Force -Path $Work | Out-Null

Write-Host "→ Python-частина (PyInstaller)…"
python -m pip install -q --upgrade pip pyinstaller
python -m pip install -q "$Root"
python -m PyInstaller --noconfirm --clean --onedir --console --name plativka `
  --icon "$Root\packaging\icons\plativka.ico" `
  --distpath "$Work\dist" --workpath "$Work\pyi" --specpath "$Work" `
  --collect-all textual --collect-all textual_image --collect-data plativka `
  --collect-submodules plativka --collect-submodules rich --hidden-import segno --collect-submodules send2trash --collect-submodules pystray `
  --collect-submodules comtypes --collect-submodules pycaw --collect-all winrt `
  --hidden-import pystray._win32 `
  --exclude-module numpy --exclude-module yaml --exclude-module chardet `
  --exclude-module charset_normalizer --exclude-module tkinter --exclude-module pytest `
  "$Root\packaging\pyinstaller\plativka_entry.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Write-Host "→ mpv…"
$MpvZip = "$Work\mpv.zip"
Invoke-WebRequest -Uri $MpvZipUrl -OutFile $MpvZip
Expand-Archive -Path $MpvZip -DestinationPath "$Work\mpvx" -Force
# офіційний zip може містити ще один архів (tar.gz / 7z) — розпаковуємо вбудованим tar.exe
Get-ChildItem -Path "$Work\mpvx" -Recurse -Include *.tar.gz, *.tgz, *.tar.xz, *.7z, *.zip | ForEach-Object {
  tar -xf $_.FullName -C "$Work\mpvx"
}
$MpvExe = Get-ChildItem -Path "$Work\mpvx" -Recurse -Filter "mpv.exe" | Select-Object -First 1
if (-not $MpvExe) { Get-ChildItem -Recurse "$Work\mpvx" | Select-Object -First 40 | Format-Table FullName; throw "mpv.exe not found in the archive" }
New-Item -ItemType Directory -Force -Path "$Work\dist\plativka\mpv" | Out-Null
Copy-Item -Recurse -Force "$($MpvExe.DirectoryName)\*" "$Work\dist\plativka\mpv\"
Copy-Item "$Root\LICENSE", "$Root\THIRD_PARTY_LICENSES.md" "$Work\dist\plativka\"
Copy-Item "$Root\packaging\icons\plativka.ico" "$Work\dist\plativka\"

Write-Host "→ Перевірка: плеєр і mpv запускаються…"
& "$Work\dist\plativka\plativka.exe" --help | Select-Object -First 2
& "$Work\dist\plativka\mpv\mpv.exe" --version | Select-Object -First 1

Write-Host "→ Інсталятор (Inno Setup)…"
$Iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) { throw "Inno Setup 6 not found" }
New-Item -ItemType Directory -Force -Path "$Root\dist" | Out-Null
& $Iscc "/DAppVersion=$Version" "/DSourceDir=$Work\dist\plativka" "/DOutDir=$Root\dist" `
        "$Root\packaging\windows\plativka.iss"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed" }
Write-Host "✓ dist\Plativka-$Version-windows-x64-setup.exe"
