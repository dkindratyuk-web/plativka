# Installing Plativka on Windows

[Українською](../uk/install-windows.md) · [Back to README](../../README.md)

The installer contains everything Plativka needs: the player and the mpv audio engine. Nothing else has to be installed. Works on Windows 10 and 11 (64-bit).

## 1. Download

Open the [latest release](https://github.com/dkindratyuk-web/plativka/releases/latest) and download `Plativka-…-windows-x64-setup.exe`.

## 2. Run the installer

1. Double-click the downloaded file.
2. Windows may show a blue window **"Windows protected your PC"** (SmartScreen). This happens with every free program that is not signed with a paid certificate. Click **More info**, then **Run anyway**.
3. Pick the installer language, accept the licence and click **Next** a few times. You can tick **Create a desktop shortcut**.
4. Leave **Start Plativka** ticked and click **Finish**.

Administrator rights are not required: by default Plativka installs for your user only.

## 3. Add your music

- Press **L** and pick a folder (arrows to move, Enter to open a folder, then **Add this folder**), **or**
- drag a music folder from File Explorer into the Plativka window.

Then, in the library on the right, open an artist → album and press **Enter** on a track. See [Using Plativka](usage.md) for everything else.

## The tray icon

While Plativka is running, its record icon sits in the tray next to the clock (if you don't see it, click the **^** arrow). Right-click it for **Play / pause**, **Next track**, **Previous track**, **Show player** and **Quit Plativka**. The icon shows the current album cover, and hovering over it shows the track.

- **Closing the window with ✕ quits Plativka**, just like any other program.
- To keep music playing without the window, press **H** (or minimise the window with the **Minimize to tray** option ticked in the tray menu). Bring it back with **Show player** or a click on the icon.

The Plativka shortcut opens the player in its own classic console window — that is what makes hiding to the tray possible. If you start `plativka.exe` inside Windows Terminal instead, everything works except hiding to the tray.

## Updating

Run the new installer — it replaces the old version. Your library, playlist and settings are kept.

## Uninstalling

**Settings → Apps → Installed apps → Plativka → Uninstall**. Settings and the library cache stay in `%APPDATA%\Plativka` and `%LOCALAPPDATA%\Plativka`; delete these folders if you want them gone too.
