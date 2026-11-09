# Installing Plativka on macOS

[Українською](../uk/install-macos.md) · [Back to README](../../README.md)

The DMG contains everything Plativka needs: the player itself, the mpv audio engine and its own window (based on kitty) that can show real album covers. You don't need Homebrew, Python or the Terminal app.

## 1. Pick the right file

Open the [latest release](https://github.com/dkindratyuk-web/plativka/releases/latest) and download one file:

| Your Mac | File |
|---|---|
| Apple Silicon (M1, M2, M3, M4…) | `Plativka-…-macos-arm64.dmg` |
| Intel | `Plativka-…-macos-x86_64.dmg` |

Not sure? Click  in the top-left corner → **About This Mac**. If the "Chip" line says *Apple M…*, take arm64. If it says *Processor … Intel*, take x86_64.

Minimum macOS: 14 Sonoma for Apple Silicon, 15 Sequoia for Intel (these come from the bundled mpv build).

## 2. Install

1. Double-click the downloaded `.dmg`. A window opens with **Plativka** and an **Applications** folder.
2. Drag **Plativka** onto **Applications**.
3. Close the window and eject the "Plativka" disk in Finder's sidebar (⏏).

## 3. First launch (one time only)

Plativka is free and is not signed with a paid Apple developer certificate, so macOS blocks the first launch. This is expected — here is how to allow it:

1. Open **Applications** and double-click **Plativka**.
2. macOS says *"Plativka" Not Opened* / *Apple could not verify…*. Click **Done** (not "Move to Trash").
3. Open  → **System Settings** → **Privacy & Security**.
4. Scroll down to the **Security** section. Next to *"Plativka" was blocked…* click **Open Anyway**.
5. Enter your Mac password or use Touch ID, then click **Open Anyway** once more.

From now on Plativka opens with a normal double-click. You can also drag it to the Dock.

> For advanced users: the same can be done in Terminal with
> `xattr -dr com.apple.quarantine /Applications/Plativka.app`

## 4. Add your music

- Press **L** and pick a folder (arrows to move, Enter to open a folder, then **Add this folder**), **or**
- just drag a music folder from Finder into the Plativka window.

Then, in the library on the right, open an artist → album and press **Enter** on a track. See [Using Plativka](usage.md) for everything else.

## Updating

Download the new DMG and drag Plativka to Applications again, replacing the old one. Your library, playlist and settings stay where they are.

## Uninstalling

Drag **Plativka** from Applications to the Bin. To also remove settings and the library cache, delete the folders `~/.config/plativka` and `~/.cache/plativka` (in Finder: **Go → Go to Folder…**).

## Running from the command line (optional)

If you prefer your own terminal (Ghostty, iTerm2, Terminal.app), you can install the command-line version instead of the DMG:

```bash
brew install mpv pipx
pipx install git+https://github.com/dkindratyuk-web/plativka
plativka
```

Terminal.app cannot show pictures, so covers there are drawn with coloured blocks; Ghostty, kitty, iTerm2 and WezTerm show real covers.
