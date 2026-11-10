# Installing Plativka on macOS

[Українською](../uk/install-macos.md) · [Back to README](../../README.md)

Plativka comes in two editions — pick one, or install both (the first time Plativka Desktop starts, it picks up the music folders and the playlist from the terminal edition):

| | **Plativka Desktop** (recommended) | **Plativka for the terminal** |
|---|---|---|
| What you get | a regular Mac app window | a text interface in its own terminal window |
| File | `Plativka-Desktop-…-macos-….dmg` | `Plativka-…-macos-….dmg` |
| App name | **Plativka Desktop** | **Plativka** |

Both DMGs contain everything: the player, the mpv sound engine and, for the terminal edition, its own kitty window with real covers. You don't need Homebrew, Python or the Terminal app.

## 1. Pick the right file

Open the [latest release](https://github.com/dkindratyuk-web/plativka/releases/latest) and download one file for your Mac:

| Your Mac | Plativka Desktop | Terminal edition |
|---|---|---|
| Apple Silicon (M1, M2, M3, M4…) | `Plativka-Desktop-…-macos-arm64.dmg` | `Plativka-…-macos-arm64.dmg` |
| Intel | `Plativka-Desktop-…-macos-x86_64.dmg` | `Plativka-…-macos-x86_64.dmg` |

Not sure which Mac you have? Click  in the top-left corner → **About This Mac**. If the "Chip" line says *Apple M…*, take arm64; if it says *Processor … Intel*, take x86_64.

Minimum macOS: 14 Sonoma on Apple Silicon, 15 Sequoia on Intel (this comes from the bundled mpv).

## 2. Install

1. Double-click the downloaded `.dmg`. A window opens with the app (**Plativka Desktop** or **Plativka**) and an **Applications** folder.
2. Drag the app onto **Applications**.
3. Close the window and eject the disk in Finder's sidebar (⏏).

## 3. First launch (one time only)

Plativka is free and is not signed with a paid Apple developer certificate, so macOS blocks the first launch. This is expected — here is how to allow it:

1. Open **Applications** and double-click **Plativka Desktop** (or **Plativka**).
2. macOS says *"Plativka Desktop" Not Opened* / *Apple could not verify…*. Click **Done** (not "Move to Trash").
3. Open  → **System Settings** → **Privacy & Security**.
4. Scroll down to the **Security** section. Next to *"Plativka Desktop" was blocked…* click **Open Anyway**.
5. Enter your Mac password or use Touch ID, then click **Open Anyway** once more.

From now on the app opens with a normal double-click. You can also drag it to the Dock.

> For advanced users: the same in Terminal —
> `xattr -dr com.apple.quarantine "/Applications/Plativka Desktop.app"` (or `/Applications/Plativka.app`).

**Plativka Desktop** then asks whether it may send **notifications** — allow it, and every new track pops up with its album cover. (You can change this later in System Settings → Notifications → Plativka Desktop.)

## 4. Add your music

- Press **L** (or **+ Folder** in the Library tab) — the usual Finder folder dialog opens; you can select several folders with ⌘. **Or**
- drag a music folder from Finder into the Plativka window.

Then open an artist → album in the library and double-click a track (or press **Enter**) — the whole album goes to the playlist. Everything else: [Plativka Desktop guide](desktop.md) · [terminal edition guide](terminal.md).

## Media keys and Now Playing

⏮ ⏯ ⏭ (F7 F8 F9) and headphone buttons control Plativka, and **Now Playing** in Control Center shows the track and the cover — in both editions. If the keyboard keys do nothing in *any* app, see [Troubleshooting](troubleshooting.md#macos-media-keys-dont-work-in-any-app-plativka-music-youtube).

## Updating

Download the new DMG and drag the app to Applications again, replacing the old one. Your library, playlist and settings are kept.

## Uninstalling

Drag **Plativka Desktop** (and/or **Plativka**) from Applications to the Bin. To also remove settings and the library cache, delete the folders `~/.config/plativka` and `~/.cache/plativka` (in Finder: **Go → Go to Folder…**).

## The terminal edition in your own terminal (optional)

If you'd rather run the terminal edition in Ghostty, iTerm2 or Terminal.app instead of its own window:

```bash
brew install mpv pipx
pipx install git+https://github.com/dkindratyuk-web/plativka
plativka
```

Terminal.app cannot show pictures, so covers there are drawn with coloured blocks; Ghostty, kitty, iTerm2 and WezTerm show real covers. See [Plativka for the terminal](terminal.md).
