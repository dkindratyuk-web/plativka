# ─────────────────────────────────────────────────────────────────────────────
#  Збирає інсталятор віконної Платівки (Qt) для Windows:
#  Plativka-Desktop-<версія>-windows-x64-setup.exe. Усередині: Python + Qt, mpv, іконка.
#
#  Використання:  powershell -File packaging\windows\build_desktop.ps1 -MpvZipUrl <url>
# ─────────────────────────────────────────────────────────────────────────────
param([Parameter(Mandatory = $true)][string]$MpvZipUrl)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
$Version = (Select-String -Path "$Root\src\plativka\__init__.py" -Pattern '__version__ = "(.+?)"').Matches[0].Groups[1].Value
$Work = "$Root\build\desktop-windows"
if (Test-Path $Work) { Remove-Item -Recurse -Force $Work }
New-Item -ItemType Directory -Force -Path $Work | Out-Null

Write-Host "→ Python + Qt (PyInstaller)…"
python -m pip install -q --upgrade pip pyinstaller
python -m pip install -q "$Root[desktop]"
python -m PyInstaller --noconfirm --clean --onedir --windowed --name Plativka `
  --icon "$Root\packaging\icons\plativka.ico" `
  --distpath "$Work\dist" --workpath "$Work\pyi" --specpath "$Work" `
  --collect-data plativka --collect-submodules plativka --hidden-import segno --hidden-import certifi --collect-data certifi --collect-submodules send2trash `
  --collect-submodules comtypes --collect-submodules pycaw --collect-all winrt `
  --exclude-module textual --exclude-module textual_image --exclude-module rich --exclude-module pystray `
  --exclude-module numpy --exclude-module yaml --exclude-module tkinter --exclude-module pytest `
  "$Root\packaging\pyinstaller\plativka_desktop_entry.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Write-Host "→ mpv…"
$MpvZip = "$Work\mpv.zip"
Invoke-WebRequest -Uri $MpvZipUrl -OutFile $MpvZip
Expand-Archive -Path $MpvZip -DestinationPath "$Work\mpvx" -Force
Get-ChildItem -Path "$Work\mpvx" -Recurse -Include *.tar.gz, *.tgz, *.tar.xz, *.7z, *.zip | ForEach-Object {
  tar -xf $_.FullName -C "$Work\mpvx"
}
$MpvExe = Get-ChildItem -Path "$Work\mpvx" -Recurse -Filter "mpv.exe" | Select-Object -First 1
if (-not $MpvExe) { throw "mpv.exe not found in the archive" }
New-Item -ItemType Directory -Force -Path "$Work\dist\Plativka\mpv" | Out-Null
Copy-Item -Recurse -Force "$($MpvExe.DirectoryName)\*" "$Work\dist\Plativka\mpv\"
Copy-Item "$Root\LICENSE", "$Root\THIRD_PARTY_LICENSES.md" "$Work\dist\Plativka\"
Copy-Item "$Root\packaging\icons\plativka.ico" "$Work\dist\Plativka\"
if (-not (Test-Path "$Work\dist\Plativka\Plativka.exe")) { throw "Plativka.exe not built" }
& "$Work\dist\Plativka\mpv\mpv.exe" --version | Select-Object -First 1

Write-Host "→ Інсталятор (Inno Setup)…"
$Iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) { throw "Inno Setup 6 not found" }
New-Item -ItemType Directory -Force -Path "$Root\dist" | Out-Null
& $Iscc "/DAppVersion=$Version" "/DSourceDir=$Work\dist\Plativka" "/DOutDir=$Root\dist" `
        "$Root\packaging\windows\plativka-desktop.iss"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed" }
Write-Host "✓ dist\Plativka-Desktop-$Version-windows-x64-setup.exe"
