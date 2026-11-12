# Plativka for the terminal

[Українською](../uk/terminal.md) · [Back to README](../../README.md) · [Plativka Desktop](desktop.md)

## What it is and who it's for

The terminal edition is the original Plativka: the same player, but drawn with text in a terminal window instead of a regular app window. It uses very little memory and works over SSH. If you just want a nice music player, take [Plativka Desktop](desktop.md); the terminal edition is for people who like the terminal.

You can install both editions side by side. The first time Plativka Desktop starts, it picks up the music folders and the playlist from the terminal edition; after that each edition keeps its own settings.

## How to start it

| System | Installed with | Starts |
|---|---|---|
| **macOS** | `Plativka-…-macos-….dmg` → app **Plativka** | in its own window (kitty inside the app) with real covers |
| **Windows** | `Plativka-…-windows-x64-setup.exe` → Start menu **Plativka** | in a classic console window; covers drawn with blocks |
| **Linux** | `./install.sh` (or `./install.sh --desktop`) → menu **Plativka** | in its own kitty window with real covers |
| any terminal | `plativka` command | in the terminal you typed it in |

Installation step by step: [macOS](install-macos.md) · [Windows](install-windows.md) · [Linux](install-linux.md).

**Which terminal shows real covers**: kitty, Ghostty, iTerm2, WezTerm and recent Windows Terminal. Terminal.app, the classic Windows console, GNOME Terminal and Konsole draw covers with coloured blocks (or press **O** to turn covers off and get a spinning record instead).

**Window size**: at least 80 × 24 characters; from about 100 characters wide the library sits next to the playlist, below that the parts are stacked.

## The window

Plativka is laid out like Winamp:

- **Main window** (top left): the album cover, a big clock, the left/right level meter, the scrolling track title, the format (MP3, bitrate, sample rate), the shuffle / repeat / popup switches, the seek bar, the transport buttons and the volume.
- **Playlist** (bottom left): what plays next. The playing track is marked with ▶.
- **Library** (right): all music from the folders you added, by artist → album or by folder.

In a narrow window (under ~100 characters) the parts are stacked, and **M** switches the bottom part between the playlist and the library.

**Moving between the panels**: **Tab** (or **Shift+Tab**) jumps between the playlist and the library; **1** goes to the playlist, **2** to the library. The active panel has a bold frame and a ● before its name. A mouse click on a panel works too.

The row of keys at the very bottom adapts to the window width: in a narrow window it shows only the most important keys. **F1** (or **?**) always opens the full help — every key, the settings, the version and the GitHub links.

Everything can be clicked with the mouse: buttons, the seek bar (jump to a point), the clock (elapsed ↔ remaining), the volume bar (click or scroll), the switches.

## Compact view

**W** switches between the Winamp layout and the **compact view** (inspired by the Sonata player): a small strip with the cover, title, "artist — album · year", a one-line level meter, the seek bar with the time, the buttons and the volume. Below it, one panel with tabs — **Playlist** and **Library** (click them, or press **1** / **2** / **Tab**).

**E** (or **▴ collapse**) collapses the compact view to just the strip — a mini player you can keep in a corner of the screen. Plativka shrinks its window to the strip and restores the previous height when you expand it again (**E**, **▾ expand**, or a tab). Resizing works in the Plativka window on macOS (DMG) and Linux (kitty), in the classic Windows console window (the Start-menu shortcut), and in Terminal.app, iTerm2 and xterm; in other terminals resize the window yourself.

The view, the tab and the collapsed state are remembered.

> Linux: if you installed Plativka before 1.2.0, run the install script again so the Plativka window is allowed to resize itself.

## Adding music

Plativka never copies or changes your files — it only reads them.

- **L** or the **+ Folder** button in the library opens the usual system folder dialog (Finder on macOS, "Select folder" on Windows, the GNOME/KDE dialog on Linux). On macOS and Linux you can select several folders at once with Cmd/Ctrl. If there is no system dialog (e.g. over SSH), a folder picker opens inside the player: arrow keys to move, Enter opens a folder, **↑ Up** goes one level up, **Add this folder** confirms; you can also type or paste a path.
- **Drag and drop**: drag a folder from Finder / File Explorer / your file manager into the Plativka window. Folders go to the library; individual audio files go to the end of the playlist.
- **Folders…** opens the list of library folders with the number of tracks in each. Tick folders with Space or a click and press **Remove checked**; **Remove all** empties the library after a confirmation; **+ Add…** adds more. Files on disk stay untouched. **↻** rescans the library — use it after you added new files to a folder.

Supported formats: MP3, FLAC, M4A/AAC/ALAC, OGG/Opus, WAV, AIFF, WMA.

Tags are read from the files. Files without tags are read from their names: `01. Artist - Title.mp3` becomes artist *Artist*, title *Title*. Old tags written in the Windows-1251 encoding (gibberish like "Ïðèâ³ò") are fixed automatically.

## Library → playlist

| In the library | What happens |
|---|---|
| **Enter** on a track (or double-click) | the whole album/folder goes to the playlist, that track plays |
| **P** on an artist, album or folder | replace the playlist with it and play |
| **A** on anything | add it to the end of the playlist |
| **▶ All** button or **Shift+P** | the whole library into the playlist (from a random track if shuffle is on) |

In the playlist: **Enter** or a double-click plays a track, **Delete** removes it, **Clear** empties the list, **+ Folder** adds a folder straight into the playlist without adding it to the library.

**J** (or **/**) opens quick search across the library and playlist: type a few letters of an artist, title or album, press Enter.

## Playback

| Key | Action |
|---|---|
| `Z` `X` `C` `V` `B` | previous · play · pause · stop · next |
| `Space` | pause / resume |
| `F7` `F8` `F9` | previous · pause · next |
| `←` `→` | seek 5 seconds |
| `+` `−` | volume |
| `S` | shuffle on/off |
| `R` | repeat: off → all → one |
| `K` | sleep timer: 15 · 30 · 45 · 60 · 90 min · after this track · off |
| `G` | volume levelling: by album → by track → off |
| `U` | check for updates / open the download page |
| `F3` | phone remote: QR code, connected phones |

**Volume** mirrors the system volume: the volume keys on your keyboard (F11/F12 or the speaker keys on a Mac, the volume keys or the Windows/Linux sound slider) move the player's volume bar, and `+` `−` in the player change the system volume. If you prefer a separate player volume, switch it in **F1 → Volume**. On Linux this needs PipeWire (`wpctl`) or PulseAudio (`pactl`), which every modern desktop has.

At the end of the playlist Plativka stops and says so. Turn on **repeat: all** to loop.

"Previous" goes to the start of the current track if more than 3 seconds have played, otherwise to the previous track (in shuffle mode — to the one that actually played before).

### Sleep timer

Plativka can stop the music for you: press `K` repeatedly to go through 15, 30, 45, 60 or 90 minutes, or **after this track**. While the timer runs, the time left is shown next to shuffle and repeat (**sleep: 29:41**; click it to cancel). When it runs out, the music fades out over a few seconds and pauses.

### Gapless playback and volume levelling

Tracks follow each other without a pause, as on the album — live recordings and DJ mixes are not cut into pieces. Nothing to turn on: it just works.

**Volume levelling (ReplayGain)** makes quiet and loud albums play at the same volume, if the files carry ReplayGain tags (most rips and many shops add them; foobar2000, MusicBrainz Picard and others can add them). `G` switches it: by album (default) → by track → off. **By album** keeps the difference between quiet and loud songs of one album, as the artist intended; **by track** makes every song equally loud. Files without the tags play as they are.

### Albums as one file with a .cue sheet

If an album is one big FLAC, APE or WAV file with a `.cue` file next to it, Plativka shows it as separate tracks with their own titles, and they play one after another without a gap. The `.cue` file can be in UTF-8 or in the old Windows encoding (Cyrillic `.cue` files from the 2000s too).

## Covers and colours

- The colour of the frames and the clock is taken from the cover of the album that is playing.
- **O** cycles: normal cover → large cover (needs a window at least 30 rows tall) → covers off. With covers off a record is drawn in their place, and it spins while music plays.
- Covers are read from the files themselves or from `cover.jpg` / `folder.jpg` / `front.jpg` next to them.
- **Kitty, Ghostty, iTerm2, WezTerm** and recent **Windows Terminal** show real pictures. Other terminals (Terminal.app, the classic Windows console, GNOME Terminal…) draw covers with coloured blocks. The macOS DMG and the Linux script open Plativka in its own kitty window, so covers are real there.
- If a cover shows up empty, start with `plativka --no-images`.

## Track popups

**N** cycles: **popups: player** (a small window inside the player) → **popups: macOS / Windows / Linux** (a system notification, visible even when the player is in the background) → **popups: off**.

System notifications show the **album cover**:

- **macOS** (the DMG): the notification comes from "Plativka" with the cover on the right. The first time macOS asks whether Plativka may show notifications — allow it. In Terminal.app and other terminals the notification is shown by "Script Editor" (a system component), without a cover.
- **Windows** (installed with the installer): a Windows notification with the cover; a new track replaces the previous notification. Without the installer the tray icon shows a notification without a cover.
- **Linux**: the cover is shown as the notification icon (GNOME, KDE and most desktops).

## Phone remote

Control Plativka from your phone while lying on the sofa: pause, next or previous track, seek, volume, the sleep timer and any track from the playlist. Nothing to install on the phone — it is a web page that Plativka itself serves in your home network.

1. Press `F3` and then `Space` to turn the remote on; the QR code is drawn right in the terminal (make the window at least 36 rows tall).
2. Point the phone's camera at the QR code and open the link. That's it — the phone is connected and remembers it: next time just open the same page (add it to the home screen: Safari → Share → **Add to Home Screen**, Chrome → ⋮ → **Add to Home screen**).
3. If the camera cannot read the code from the screen, open the address shown next to it on the phone, press **C** and type the 6-digit code.

The phone and the computer must be on the same Wi-Fi network. The first time, macOS or Windows may ask whether Plativka may accept incoming connections — allow it for private networks.

If the page does not open on the phone, see [Troubleshooting](troubleshooting.md#the-phone-remote-does-not-open-on-the-phone).

**Security.** The remote is off until you turn it on, and works only while Plativka is open.

- Only devices in your home network can reach it — requests from the internet are refused, even if a port is forwarded on the router.
- A phone gets in only through the QR code (a long one-time key) or the short code you show yourself: it is valid for 2 minutes, and after 5 wrong tries it is switched off. An address that keeps guessing is blocked for 10 minutes.
- Every phone has its own key; Plativka keeps only its fingerprint. The list of connected phones shows each of them; **D** disconnects them all at once.
- The remote can only control the music — it has no access to files, settings or anything else on the computer.
- Inside the home network the page uses plain HTTP (a real certificate cannot be issued for a home address). That is fine on a Wi-Fi network with a password; do not turn the remote on in public Wi-Fi (cafés, hotels).

## System integration

- **Windows — media keys**: ⏯ ⏭ ⏮ on the keyboard and headphones control Plativka, and the Windows media overlay (next to the volume popup) shows the track and its cover.
- **Windows — tray icon**: play/pause, next, previous, show the player, Plativka on GitHub, quit. **H** hides the window to the tray; the **Minimize to tray** option in the tray menu makes minimising do the same. Closing the window with ✕ quits.
- **Linux — MPRIS**: media keys, the GNOME/KDE media widget and `playerctl` control Plativka and show the track and cover.
- **macOS — media keys**: ⏮ ⏯ ⏭ (F7 F8 F9) and headphone buttons control Plativka, and the **Now Playing** widget in Control Center shows the track and cover. macOS sends these keys to the app that started playing most recently — if a browser or Music played something after Plativka, press play in Plativka once and the keys come back.

## Updates

Once a day Plativka asks GitHub whether a new version is out. If it is, **⬆ 1.x.x — U** appears in the player — press `U` to open the download page. Nothing is downloaded or installed by itself, and nothing about you is sent. `U` also checks right away. To turn the daily check off, set `"check_updates": false` in `config.json`.

## Themes and language

- **T** switches between the light and the dark theme.
- The language and the volume mode can also be changed in **F1** (help).
- **F2** switches the interface language (English ↔ Ukrainian). It applies after a restart. By default the language follows the system. You can also start with `plativka --lang=en` or `--lang=uk`.

## Where Plativka keeps its data

| | Settings, playlist | Library cache, logs |
|---|---|---|
| macOS, Linux | `~/.config/plativka/config.json` | `~/.cache/plativka/` |
| Windows | `%APPDATA%\Plativka\config.json` | `%LOCALAPPDATA%\Plativka\cache\` |

The playlist, the position in the current track, the volume, the theme and all switches are saved automatically.

## Command-line options

| Option | Meaning |
|---|---|
| `--demo` | no sound and no mpv — just look around |
| `--lang=en`, `--lang=uk` | interface language |
| `--no-images` | draw covers with blocks even if the terminal can show pictures |
| `--256`, `--truecolor` | force 256 colours or 24-bit colour |
