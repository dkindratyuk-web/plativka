# Using Plativka

[Українською](../uk/usage.md) · [Back to README](../../README.md)

## The window

Plativka is laid out like Winamp:

- **Main window** (top left): the album cover, a big clock, the left/right level meter, the scrolling track title, the format (MP3, bitrate, sample rate), the shuffle / repeat / popup switches, the seek bar, the transport buttons and the volume.
- **Playlist** (bottom left): what plays next. The playing track is marked with ▶.
- **Library** (right): all music from the folders you added, by artist → album or by folder.

In a narrow window (under ~100 characters) the parts are stacked, and **M** switches the bottom part between the playlist and the library.

Everything can be clicked with the mouse: buttons, the seek bar (jump to a point), the clock (elapsed ↔ remaining), the volume bar (click or scroll), the switches.

## Adding music

Plativka never copies or changes your files — it only reads them.

- **L** or the **+ Folder** button in the library: pick a folder with the arrow keys, Enter opens a folder, **↑ Up** goes one level up, **Add this folder** confirms. You can also type or paste a path.
- **Drag and drop**: drag a folder from Finder / File Explorer / your file manager into the Plativka window. Folders go to the library; individual audio files go to the end of the playlist.
- **− Folder** removes a folder from the library (files on disk stay untouched). With two or more folders the list starts with **✕ Remove all folders** — it empties the library after a confirmation. **↻** rescans the library — use it after you added new files to a folder.

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
| `←` `→` | seek 5 seconds |
| `+` `−` | volume |
| `S` | shuffle on/off |
| `R` | repeat: off → all → one |

At the end of the playlist Plativka stops and says so. Turn on **repeat: all** to loop.

"Previous" goes to the start of the current track if more than 3 seconds have played, otherwise to the previous track (in shuffle mode — to the one that actually played before).

## Covers and colours

- The colour of the frames and the clock is taken from the cover of the album that is playing.
- **O** cycles: normal cover → large cover (needs a window at least 30 rows tall) → covers off. With covers off a record is drawn in their place, and it spins while music plays.
- Covers are read from the files themselves or from `cover.jpg` / `folder.jpg` / `front.jpg` next to them.
- **Kitty, Ghostty, iTerm2, WezTerm** and recent **Windows Terminal** show real pictures. Other terminals (Terminal.app, the classic Windows console, GNOME Terminal…) draw covers with coloured blocks. The macOS DMG and the Linux script open Plativka in its own kitty window, so covers are real there.
- If a cover shows up empty, start with `plativka --no-images`.

## Track popups

**N** cycles: **popups: player** (a small window inside the player) → **popups: macOS / Windows / Linux** (a system notification, visible even when the player is in the background) → **popups: off**.

On macOS the first system notification may ask for permission for "Script Editor" — that is the system component that shows the notification.

## System integration

- **Windows — tray icon**: play/pause, next, previous, show the player, quit. **H** hides the window to the tray; the **Minimize to tray** option in the tray menu makes minimising do the same. Closing the window with ✕ quits.
- **Linux — MPRIS**: media keys, the GNOME/KDE media widget and `playerctl` control Plativka and show the track and cover.
- **macOS — media keys** on the keyboard and headphones usually work while Plativka is playing.

## Themes and language

- **T** switches between the light and the dark theme.
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
