<p align="center">
  <img src="packaging/icons/plativka.png" width="128" alt="Plativka icon">
</p>

<h1 align="center">Plativka</h1>

<p align="center">
  A Winamp-style music player for macOS, Windows and Linux —<br>
  in its own window or right in your terminal. Offline, fast, no account, no ads.
</p>

<p align="center">
  <b>English</b> · <a href="README.uk.md">Українська</a>
</p>

<p align="center">
  <a href="https://github.com/dkindratyuk-web/plativka/releases/latest"><b>⬇ Download the latest release</b></a> · <a href="https://dkindratyuk-web.github.io/plativka/">Website</a>
</p>

<p align="center">
<img src="docs/img/desk-mac-en-full.png" width="32%" alt="Plativka Desktop on macOS">
<img src="docs/img/desk-win-full-dark.png" width="32%" alt="Plativka Desktop on Windows 11, dark theme">
<img src="docs/img/desk-mac-en-compact-dark.png" width="32%" alt="Plativka Desktop, compact view">
</p>

Plativka plays the music already on your disk — MP3 first of all, plus FLAC, M4A/AAC, OGG/Opus and WAV. It takes the layout everybody remembers from Winamp — a main window with a big time display and level meter, the playlist and the media library — and makes it light, colourful and quick.

It comes in two editions; install either one or both — the first time Plativka Desktop starts, it picks up the music folders and the playlist from the terminal edition:

| | **Plativka Desktop** (main) | **Plativka for the terminal** |
|---|---|---|
| Looks like | a regular app window | a text interface in a terminal window |
| Covers | real, on every system | real in kitty, Ghostty, iTerm2, WezTerm; pixel-art elsewhere |
| Mini player | small window, can stay on top | collapses the terminal window |
| Best for | everyone | people who live in the terminal |

---

## Plativka Desktop

### What it can do

- **Winamp layout**: the cover, an LCD-style clock, a level visualisation, the title and format, shuffle / repeat / notification switches, the seek bar, transport buttons and volume — with the playlist and the library underneath.
- **The colour comes from the album cover**: the clock, the visualisation, the window background, the panels and the highlighted track all change with every album. Light, dark or system theme (`T`).
- **Level visualisation**: vertical LED-style columns — the left channel on the left, the right channel on the right, what is playing now in the middle and the last few seconds fading out to the sides.
- **Three skins**: Plativka's own look, **macOS** or **Windows 11** — native-style buttons, sliders, tabs and translucency, with the same layout and the colour still taken from the cover. Switch in ☰ → View → Skin or with `Shift+T`, no restart.
- **Three sizes**: the full Winamp view, the **compact view** (`W`) with a small cover, the title and the controls in two rows above the playlist, and the **mini player** (`E`) — just those two rows, small enough for a corner of the screen, which can stay on top of all windows (📌).
- **Playlist and library** in tabs with instant search (`J`): the library by artist → album or by folder, double-click a track to play its whole album, right-click to add to the end of the playlist, `▶ All` to play everything.
- **Folders**: add them with the usual system folder dialog or drag them into the window; the **Folders…** window lists them with track counts.
- **System integration**: media keys ⏮ ⏯ ⏭ and headphone buttons, Now Playing / the Windows media overlay / MPRIS on Linux, track notifications **with the album cover**, a tray icon, the volume mirrors the system volume (your keyboard's volume keys move the slider).
- **Windows 11**: the translucent Mica background, tinted by the cover.
- **Plays like an album**: no pauses between tracks (gapless), volume levelling with ReplayGain (by album or by track), albums as one FLAC/APE/WAV file with a `.cue` sheet shown as separate tracks.
- **Equalizer** *(coming in 1.7)*: 10 bands, presets, automatic headroom so boosted bass never distorts, and **headphone correction** from [AutoEQ](https://autoeq.app) — measured settings for thousands of headphone models. `Shift+E`. [How to use it](docs/en/desktop.md#equalizer).
- **Favorites that don't get lost**: like a song with a heart (or `F`) and play only your favorites from all folders at once. Likes survive moving and renaming files — Plativka recognises the song by artist, title and length. Plus smart lists (*Recently added*, *Most played*, *Not played for a while*) and **Remove non-favorites** — from the list, or to the Trash, never permanently.
- **Play next**: `Shift+N` puts a song (or a whole album) right after the current one, without breaking the order of the list.
- **Copy to a USB stick** for the car: numbered files so the stereo keeps your order, the size and free space shown first, nothing overwritten without asking.
- **Find duplicates**: identical files and the same song in different files (MP3 and FLAC of one album); you choose which copy to keep, the extras go from the list or to the Trash.
- **Covers from the internet** (off by default): if a file has no cover, Plativka finds it on MusicBrainz or Apple — only a confident match, or pick one yourself from a few options.
- **Phone remote**: control the music from your phone on the same Wi-Fi — scan a QR code, nothing to install. Pause, next track, volume, sleep timer, any track from the playlist — on a page that looks like Plativka itself; only phones you paired, only in your home network.
- **Sleep timer**: stop after 15–90 minutes or after the current track, with a gentle fade-out.
- **Smart tags**: files without tags are read from their names ("01. Artist - Title.mp3"), old Windows-1251 tags are fixed automatically.
- **Remembers everything**: playlist, position, volume, view, window size and library.
- **English and Ukrainian**, chosen from your system language.

### Screenshots

**Skins** — Plativka, macOS and Windows 11 with the same song, and the new mini player in each of them:

<p><img src="docs/img/skins-en.png" width="100%" alt="Plativka, macOS and Windows 11 skins"></p>
<p><img src="docs/img/skins-mini.png" width="48%" alt="Mini player in the three skins"></p>

The same window on all three systems — screenshots from macOS, Windows 11 and Linux (version 1.5, the Plativka skin).

**macOS** — the full view, the compact view and the mini player in light and dark:

<p>
<img src="docs/img/desk-mac-en-full.png" width="32%" alt="Full view, macOS">
<img src="docs/img/desk-mac-en-compact.png" width="32%" alt="Compact view, macOS">
<img src="docs/img/desk-mac-en-compact-dark.png" width="32%" alt="Compact view, dark theme, macOS">
</p>
<p>
<img src="docs/img/desk-mac-en-mini.png" width="48%" alt="Mini player, macOS">
<img src="docs/img/desk-mac-en-mini-dark.png" width="48%" alt="Mini player, dark theme, macOS">
</p>

**Windows 11** — the Mica background lets the wallpaper shine through:

<p>
<img src="docs/img/desk-win-full.png" width="32%" alt="Full view, Windows 11">
<img src="docs/img/desk-win-full-dark.png" width="32%" alt="Dark theme, Windows 11">
<img src="docs/img/desk-win-full-dark2.png" width="32%" alt="Dark theme with a yellow cover, Windows 11">
</p>
<p>
<img src="docs/img/desk-win-compact.png" width="48%" alt="Compact view, Windows 11">
<img src="docs/img/desk-win-mini.png" width="48%" alt="Mini player, Windows 11">
</p>

**Linux** — Kubuntu 26.10 with KDE Plasma:

<p>
<img src="docs/img/desk-linux-en-full.png" width="32%" alt="Full view, Kubuntu">
<img src="docs/img/desk-linux-en-full-dark.png" width="32%" alt="Dark theme, Kubuntu">
<img src="docs/img/desk-linux-en-compact.png" width="32%" alt="Compact view, Kubuntu">
</p>
<p>
<img src="docs/img/desk-linux-en-compact-dark.png" width="32%" alt="Compact view, dark theme, Kubuntu">
<img src="docs/img/desk-linux-en-mini.png" width="32%" alt="Mini player, Kubuntu">
<img src="docs/img/desk-linux-en-mini-dark.png" width="32%" alt="Mini player, dark theme, Kubuntu">
</p>

**Phone remote** — the same song on the Mac and on the phone; the page takes the colours of the cover:

<p>
<img src="docs/img/remote-phone-en.png" width="24%" alt="Phone remote with the cover-tinted player">
<img src="docs/img/remote-phone-en-list.png" width="24%" alt="Phone remote: sleep timer and playlist">
<img src="docs/img/remote-window-en.png" width="46%" alt="Remote window on the Mac: QR code and connected phones">
</p>
<p><img src="docs/img/remote-player-en.png" width="60%" alt="Plativka Desktop playing the same song"></p>

### Download and install

| System | What to download |
|---|---|
| **macOS** (Apple Silicon) | `Plativka-Desktop-…-macos-arm64.dmg` |
| **macOS** (Intel) | `Plativka-Desktop-…-macos-x86_64.dmg` |
| **Windows 10/11** | `Plativka-Desktop-…-windows-x64-setup.exe` |
| **Linux** (Debian, Ubuntu, Kubuntu, Mint, Fedora, Arch, openSUSE) | `plativka-…-linux.tar.gz`, then `./install.sh --desktop` |

Everything is on the [Releases page](https://github.com/dkindratyuk-web/plativka/releases/latest); the macOS and Windows installers include everything, including the mpv sound engine. On macOS the first launch needs one confirmation in System Settings → Privacy & Security → "Open Anyway" ([details](docs/en/install-macos.md)); Windows may show "Windows protected your PC" → "More info" → "Run anyway" ([details](docs/en/install-windows.md)). Linux: [install guide](docs/en/install-linux.md).

### Keys

| Key | Action |
|---|---|
| `Space` or `X` | play / pause |
| `Z` · `B` (or `F7` · `F9`) | previous · next track |
| `V` · `C` | stop · pause |
| `←` `→` | seek 5 seconds |
| `+` `−` | volume (the same as the system volume keys) |
| `S` · `R` | shuffle · repeat (off → all → one) |
| `J`, `/` or `Ctrl+F` | search the playlist or the library |
| `Tab` · `1` · `2` | switch between the playlist and the library |
| `L` | add a folder to the library |
| `W` | full view ⇄ compact view |
| `E` | mini player / expand |
| `Ctrl+T` | keep the window on top |
| `N` | track notifications on / off |
| `T` | theme: system → light → dark |
| `Shift+T` | skin: Plativka → macOS → Windows 11 |
| `Shift+E` | equalizer *(1.7)* |
| `Delete` | remove the selected tracks from the playlist |
| `F1` | about Plativka |
| `Q` or `Ctrl+Q` (`⌘Q` on a Mac) | quit |

Everything is also in the menu: the menu bar on macOS, the ☰ button on Windows and Linux.

---

## Plativka for the terminal

The original edition: the same player as a text interface in a terminal window. It is light as a feather and works over SSH. On macOS and Linux it opens in its own kitty window with real covers; in other terminals covers are drawn with coloured blocks or replaced by a spinning record.

### Download and install

| System | What to download | Guide |
|---|---|---|
| **macOS** (Apple Silicon) | `Plativka-…-macos-arm64.dmg` | [Install on macOS](docs/en/install-macos.md) |
| **macOS** (Intel) | `Plativka-…-macos-x86_64.dmg` | [Install on macOS](docs/en/install-macos.md) |
| **Windows 10/11** | `Plativka-…-windows-x64-setup.exe` | [Install on Windows](docs/en/install-windows.md) |
| **Linux** | `plativka-…-linux.tar.gz`, then `./install.sh` (only this edition) or `./install.sh --desktop` (both) | [Install on Linux](docs/en/install-linux.md) |

### Screenshots

<p>
<img src="docs/img/macos-en-winamp.png" width="32%" alt="Terminal edition, Winamp layout">
<img src="docs/img/macos-en-dark2.png" width="32%" alt="Terminal edition, dark theme">
<img src="docs/img/macos-en-mini.png" width="32%" alt="Terminal edition, mini player">
</p>

| Dark theme | Covers off — a spinning record |
|---|---|
| ![Dark theme](docs/img/en-dark.png) | ![Record](docs/img/en-vinyl.png) |

| Quick search (`J`) | Compact view (`W`) |
|---|---|
| ![Search](docs/img/en-search.png) | ![Compact view](docs/img/en-compact.png) |

### Keys

| Key | Action |
|---|---|
| `Z` `X` `C` `V` `B` | previous · play · pause · stop · next (like Winamp) |
| `Space` | pause / resume |
| `F7` `F8` `F9` | previous · pause · next (Mac media keys, also on keyboards that send them as plain F-keys) |
| `←` `→` | seek 5 seconds |
| `+` `−` | volume (same as the system volume keys) |
| `S` / `R` | shuffle / repeat (off → all → one) |
| `K` | sleep timer: 15 · 30 · 45 · 60 · 90 min · after this track · off |
| `G` | volume levelling (ReplayGain): by album → by track → off |
| `U` | check for updates / open the download page |
| `F3` | phone remote: QR code, connected phones |
| `F` · `Shift+F` | add to / remove from favorites · play favorites only |
| `Shift+D` | remove non-favorites (from the list or to the Trash) |
| `Shift+N` | play next (the track or library node under the cursor; again — remove from the queue) |
| `Shift+C` · `Shift+X` | copy the playlist to a USB stick · find duplicates |
| `Shift+O` | find missing covers online: on / off |
| `J` or `/` | find a track |
| `L` | add a folder to the library (system folder dialog) |
| `Shift+P` | put the whole library in the playlist |
| `M` | show / hide the library |
| `O` | cover: normal → large → off (spinning record) |
| `N` | track popups: in the player → system → off |
| `W` | view: Winamp ⇄ compact |
| `E` | compact view: collapse to a mini player / expand |
| `T` | light / dark theme |
| `F2` | interface language (applies after restart) |
| `H` | hide to tray (Windows) |
| `Delete` | remove a track from the playlist |
| `Tab` · `1` · `2` | switch between the playlist and the library (the active panel has a bold frame and ●) |
| `F1` or `?` | help: all keys, settings, link to GitHub |
| `Q` | quit |

In the library: `Enter` on a track plays its whole album, `P` plays the selected artist/album/folder, `A` adds it to the end of the playlist. The mouse works too.

## Documentation

- [Using Plativka Desktop](docs/en/desktop.md) — views, library, playlist, notifications, tray, settings
- [Plativka for the terminal](docs/en/terminal.md) — what it is, how to start it, terminals and covers, keys
- [Troubleshooting](docs/en/troubleshooting.md) — tracks that stop early, pauses from outside, empty covers, logs
- [Changelog](CHANGELOG.md)

## Building from source

```bash
git clone https://github.com/dkindratyuk-web/plativka
cd plativka
pipx install .       # or: python3 -m venv .venv && .venv/bin/pip install .
plativka            # needs mpv in PATH
plativka --demo     # look around without mpv and without sound
```

The desktop edition: `pipx install ".[desktop]"`, then `plativka-desktop` (or `plativka-desktop --demo`).


## License

Plativka is released under the [MIT License](LICENSE). The installers also include [mpv](https://mpv.io) (GPL), the desktop edition uses [Qt / PySide6](https://www.qt.io/qt-for-python) (LGPL), and the terminal edition on macOS includes [kitty](https://sw.kovidgoyal.net/kitty/) (GPL); see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
