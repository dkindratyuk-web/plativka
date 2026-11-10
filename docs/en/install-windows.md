# Installing Plativka on Windows

[Українською](../uk/install-windows.md) · [Back to README](../../README.md)

Plativka comes in two editions — pick one, or install both (the first time Plativka Desktop starts, it picks up the music folders and the playlist from the terminal edition). Both work on Windows 10 and 11 (64-bit), and each installer contains everything, including the mpv sound engine.

| | **Plativka Desktop** (recommended) | **Plativka for the terminal** |
|---|---|---|
| What you get | a regular window; Mica background on Windows 11 | a text interface in a classic console window |
| Covers | real pictures | drawn with coloured blocks |
| File | `Plativka-Desktop-…-windows-x64-setup.exe` | `Plativka-…-windows-x64-setup.exe` |
| Start menu | **Plativka Desktop** | **Plativka** |

## 1. Download

Open the [latest release](https://github.com/dkindratyuk-web/plativka/releases/latest) and download the installer of the edition you want.

## 2. Run the installer

1. Double-click the downloaded file.
2. Windows may show a blue window **"Windows protected your PC"** (SmartScreen). This happens with every free program that is not signed with a paid certificate. Click **More info**, then **Run anyway**.
3. Pick the installer language, accept the licence and click **Next** a few times. You can tick **Create a desktop shortcut**.
4. Leave **Start Plativka** ticked and click **Finish**.

Administrator rights are not required: by default Plativka installs for your user only.

## 3. Add your music

- Press **L** (or the **+ Folder** button in the library) — the usual Windows "Select folder" dialog opens. **Or**
- drag a music folder from File Explorer into the Plativka window.

Then open an artist → album in the library and double-click a track (or press **Enter**) — the whole album goes to the playlist. Everything else: [Plativka Desktop guide](desktop.md) · [terminal edition guide](terminal.md).

## Media keys, the media overlay and notifications

In both editions ⏮ ⏯ ⏭ on the keyboard and headphones control Plativka, the Windows media overlay (next to the volume popup) shows the track with its cover, and track notifications come with the cover (the notification on/off switch is `N`).

## The tray icon

While Plativka is running, its icon sits in the tray next to the clock (if you don't see it, click the **^** arrow).

**Plativka Desktop**: click the icon to show the window; right-click for **Play / pause**, **Next track**, **Previous track** and **Quit Plativka**. Closing the window with ✕ quits — unless you tick **☰ → View → Minimize to tray**: then ✕ and minimising hide the window to the tray and the music keeps playing.

**Terminal edition**: right-click the icon for **Play / pause**, **Next / Previous track**, **Show player**, **Plativka on GitHub** and **Quit Plativka**. ✕ quits; **H** hides the window to the tray (or tick **Minimize to tray** in the tray menu). The Start-menu shortcut opens the player in its own classic console window — that is what makes hiding to the tray and the mini player possible. Started inside Windows Terminal, everything works except those two.

## Updating

Run the new installer — it replaces the old version and keeps your library, playlist and settings. If Plativka is running, the installer closes it first (from version 1.3.4; with older versions quit Plativka from the tray before updating).

## Uninstalling

**Settings → Apps → Installed apps → Plativka Desktop** (or **Plativka**) **→ Uninstall**. Settings and the library cache stay in `%APPDATA%\Plativka` and `%LOCALAPPDATA%\Plativka`; delete these folders if you want them gone too.
