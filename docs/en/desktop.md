# Using Plativka Desktop

[Українською](../uk/desktop.md) · [Back to README](../../README.md) · [Terminal edition](terminal.md)

Plativka Desktop is the main edition of Plativka: a regular app window for macOS, Windows and Linux. Installation: [macOS](install-macos.md) · [Windows](install-windows.md) · [Linux](install-linux.md).

## The window

From top to bottom:

- **The player**: the album cover, the display with a big clock, the level visualisation, the track title and its format (MP3, bitrate, sample rate, album, year), the **shuffle · repeat · notifications** switches, the seek bar, the buttons ⏮ ▶ ⏸ ⏹ ⏭ ⏏ and the volume.
- **The tabs** — **Playlist** and **Library** — with the search field and the **☰** menu (on macOS the menu is in the menu bar at the top of the screen).

Almost everything is clickable: the switches toggle, a click on the seek bar jumps there, a click on the clock shows the remaining time instead of the elapsed time, a click on the cover switches between the full and the compact view, ⏏ adds a folder straight into the playlist.

**The level visualisation**: vertical LED-style columns. The left half is the left channel, the right half the right channel; what is playing *now* is in the middle, and the last few seconds move out to the edges, fading. Loud passages light the top segments yellow and red.

**Colours**: the clock, the visualisation, the window background, the panels and the highlighted track take their colour from the album cover. **T** switches the theme: as in the system → light → dark. On Windows 11 the window has the translucent Mica background, tinted by the cover.

## Three sizes

| | How | What you see |
|---|---|---|
| **Full view** | default, **W** to return | the large cover, the big clock, the playlist and library below |
| **Compact view** | **W** or a click on the cover | a small cover, the title in large type, "artist — album · year", the visualisation next to it |
| **Mini player** | **E** or the **▴** button | only the player strip — the window shrinks to it |

In the compact view and the mini player the **📌** button (or **Ctrl+T**) keeps the window on top of all others — handy for a mini player in a corner of the screen. **E** or **▾** expands the window back to its previous height; clicking a tab does too. The view, the window size and position are remembered.

## Adding music

Plativka never copies or changes your files — it only reads them.

- **L**, **Ctrl+O** or **+ Folder** in the Library tab opens the usual system folder dialog. Folders go to the **library**.
- **Drag and drop**: drag folders from Finder / File Explorer / your file manager into the window — they go to the library; individual audio files go to the end of the playlist.
- **⏏** or **+ Folder** in the Playlist tab adds a folder straight into the playlist without adding it to the library.
- **Folders…** (Library tab, or **☰ → File**) lists the library folders with the number of tracks in each: tick folders and press **Remove checked**, or **Remove all**; **+ Add…** adds more. Files on disk stay untouched.
- **↻** rescans the library after you put new files into a folder.

Supported formats: MP3, FLAC, M4A/AAC/ALAC, OGG/Opus, WAV, AIFF, WMA. Tags are read from the files; files without tags are read from their names (`01. Artist - Title.mp3`), and old Windows-1251 tags (gibberish like "Ïðèâ³ò") are fixed automatically. Covers are taken from the files or from `cover.jpg` / `folder.jpg` / `front.jpg` next to them.

## Library and playlist

The **Library** tab shows your music by **Artists** (artist → album → tracks) or by **Folders** — switch with the two buttons above the list.

| In the library | What happens |
|---|---|
| double-click a track (or **Enter**) | its whole album/folder goes to the playlist, that track plays |
| double-click an artist, album or folder | it replaces the playlist and starts playing |
| right-click → **Add to the end of the playlist** | adds the selection without stopping the music |
| **▶ All** | the whole library into the playlist (from a random track if shuffle is on) |

In the **Playlist** tab: double-click or **Enter** plays a track, **Delete** (or **− Remove**) removes the selected tracks, **Clear** empties the list. The playing track is marked with ▶ and highlighted in the cover colour.

**Search**: **J**, **/** or **Ctrl+F** jumps to the search field; it filters the current tab as you type. **Enter** in the search field plays the first match in the playlist, or jumps to it in the library. **Esc** clears the search.

## Playback

| Key | Action |
|---|---|
| `Space` or `X` | play / pause |
| `Z` · `B` (also `F7` · `F9`, `Ctrl+←` · `Ctrl+→`) | previous · next track |
| `C` (`F8`) · `V` | pause · stop |
| `←` `→` | seek 5 seconds |
| `+` `−` | volume |
| `S` | shuffle on / off |
| `R` | repeat: off → all → one |
| `N` | track notifications on / off |
| `Tab` · `1` · `2` | switch tabs |
| `F1` | about Plativka |
| `Q`, `Ctrl+Q` (`⌘Q`) | quit |

**Volume** mirrors the system volume: the volume keys on your keyboard move the slider, and the slider changes the system volume. On Linux this needs PipeWire (`wpctl`) or PulseAudio (`pactl`), which every modern desktop has.

"Previous" goes to the start of the current track if more than 3 seconds have played, otherwise to the previous track (with shuffle — to the one that actually played before). At the end of the playlist Plativka stops; turn on **repeat: all** to loop.

## Notifications, media keys, tray

- **Track notifications** with the album cover appear when the window is in the background or collapsed to the mini player. **N** or the **notifications** switch turns them off.
  - macOS: the first time, allow notifications for "Plativka Desktop".
  - Windows: a regular Windows notification; a new track replaces the previous one.
  - Linux: the cover is the notification icon.
- **Media keys** ⏮ ⏯ ⏭ and headphone buttons work on all three systems; **Now Playing** (macOS), the Windows media overlay and the GNOME/KDE media widget (MPRIS) show the track and cover.
- **Tray icon**: a click shows the window; right-click for play/pause, next, previous and quit. On Windows and Linux, **☰ → View → Minimize to tray** makes ✕ and minimising hide the window to the tray instead of quitting.

## Language

**☰ → View → Language** (on macOS: **View** in the menu bar) switches between English and Ukrainian; it applies after a restart. By default the language follows the system.

## Where Plativka keeps its data

| | Settings, playlist | Library cache, logs |
|---|---|---|
| macOS, Linux | `~/.config/plativka/desktop.json` | `~/.cache/plativka/` |
| Windows | `%APPDATA%\Plativka\desktop.json` | `%LOCALAPPDATA%\Plativka\cache\` |

The first time Plativka Desktop starts, it takes the music folders and the playlist from the terminal edition (if it is installed); after that each edition keeps its own settings. The library cache is shared.

## Command-line options

`plativka-desktop --demo` — look around without sound and without mpv; `--lang=en` / `--lang=uk` — interface language.
