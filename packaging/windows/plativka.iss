; Інсталятор Платівки для Windows (Inno Setup 6).
; Збирається з packaging\windows\build.ps1 — він передає AppVersion, SourceDir і OutDir.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{531D648D-F4E8-4E0F-AD48-5F7704782A7B}
AppName=Plativka
AppVersion={#AppVersion}
AppVerName=Plativka {#AppVersion}
AppPublisher=dkindratyuk-web
AppPublisherURL=https://github.com/dkindratyuk-web/plativka
AppSupportURL=https://github.com/dkindratyuk-web/plativka/issues
DefaultDirName={autopf}\Plativka
DefaultGroupName=Plativka
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#OutDir}
OutputBaseFilename=Plativka-{#AppVersion}-windows-x64-setup
SetupIconFile={#SourceDir}\plativka.ico
UninstallDisplayIcon={app}\plativka.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile={#SourceDir}\LICENSE

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "uk"; MessagesFile: "compiler:Languages\Ukrainian.isl"

[CustomMessages]
en.DesktopIcon=Create a desktop shortcut
uk.DesktopIcon=Створити ярлик на робочому столі
en.LaunchNow=Start Plativka
uk.LaunchNow=Запустити Платівку
en.AppComment=Winamp-style music player
uk.AppComment=Музичний плеєр у дусі Winamp

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
; Плеєр відкривається у власному класичному вікні консолі (conhost), а не у Windows Terminal:
; лише таке вікно можна згорнути в трей і повернути звідти.
Name: "{group}\Plativka"; Filename: "{sys}\conhost.exe"; Parameters: """{app}\plativka.exe"""; \
  WorkingDir: "{userdocs}"; IconFilename: "{app}\plativka.ico"; Comment: "{cm:AppComment}"; \
  AppUserModelID: "dkindratyuk.Plativka"
Name: "{autodesktop}\Plativka"; Filename: "{sys}\conhost.exe"; Parameters: """{app}\plativka.exe"""; \
  WorkingDir: "{userdocs}"; IconFilename: "{app}\plativka.ico"; Comment: "{cm:AppComment}"; Tasks: desktopicon

[Run]
Filename: "{sys}\conhost.exe"; Parameters: """{app}\plativka.exe"""; WorkingDir: "{userdocs}"; \
  Description: "{cm:LaunchNow}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// Перед встановленням/оновленням закриваємо Платівку, що запущена з цієї теки (разом з її mpv),
// інакше Windows не дасть замінити файли («DeleteFile збій; код 5»).
procedure StopRunningPlayer();
var R: Integer;
begin
  Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -ExecutionPolicy Bypass -Command "Get-Process -ErrorAction SilentlyContinue | ' +
    'Where-Object { $_.Path -like ''' + ExpandConstant('{app}') + '\*'' } | Stop-Process -Force"',
    '', SW_HIDE, ewWaitUntilTerminated, R);
  Sleep(700);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopRunningPlayer();
  Result := '';
end;

function InitializeUninstall(): Boolean;
begin
  StopRunningPlayer();
  Result := True;
end;
