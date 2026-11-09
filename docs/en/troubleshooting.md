# Troubleshooting

[Українською](../uk/troubleshooting.md) · [Back to README](../../README.md)

## A track stops before its end and the next one starts

The file is truncated or damaged — this is common with "leaked" releases. The file claims to be longer than the sound it actually contains, so the player reaches the real end earlier. Plativka shows a message like *"The track stopped at 0:09 of 0:40: the file looks truncated or damaged"* and moves on. Re-download the file from another source.

## The music paused by itself

Usually something outside the player paused it: AirPods and many headphones pause when you take one out, a media key was pressed, or another app started playing sound. Plativka shows *"Paused from outside…"* in that case.

## Music stopped after the last track

That is the end of the playlist. Turn on **repeat: all** with **R** to loop it.

## A track shows 0:00 in the playlist

The duration could not be read from the file's tags. Plativka shows an estimate and takes the exact duration from mpv as soon as the track starts playing.

## The cover is an empty square

Your terminal said it can show pictures, but something went wrong. Start Plativka with `plativka --no-images` and tell us your terminal and its version in an [issue](https://github.com/dkindratyuk-web/plativka/issues).

## Covers look blocky

Your terminal cannot show pictures (Terminal.app on macOS, the classic Windows console, GNOME Terminal…), so covers are drawn with coloured blocks. The macOS DMG and the Linux script open Plativka in its own window that shows real covers. Or press **O** twice to replace covers with a record.

## macOS: "Plativka" cannot be opened / developer cannot be verified

Expected for a free app without a paid Apple certificate. See [first launch](install-macos.md#3-first-launch-one-time-only).

## Windows: "Windows protected your PC"

Expected for a free program without a paid certificate: **More info → Run anyway**. See [installing on Windows](install-windows.md).

## Windows: H does not hide the player to the tray

Hiding works only in the player's own window, which the **Plativka** shortcut opens. If you started `plativka.exe` inside Windows Terminal, use the shortcut instead.

## Linux: no sound / "mpv is required"

Install mpv with your package manager (see [installing on Linux](install-linux.md#what-exactly-happens-on-each-system)). On Fedora mpv may need the RPM Fusion repository.

## Linux: media keys don't work

They need a desktop session with D-Bus (GNOME, KDE, Xfce, Cinnamon… — practically all of them). Check with `playerctl -l` — `plativka.instance…` should be listed.

## No system notifications

- **macOS**: System Settings → Notifications → **Script Editor** → allow notifications.
- **Linux**: install `libnotify-bin` (Debian/Ubuntu) or `libnotify` (Fedora/Arch).
- **Windows**: notifications come from the tray icon; check Settings → System → Notifications.

## Logs

If something goes wrong, the logs show what happened:

| | Folder |
|---|---|
| macOS, Linux | `~/.cache/plativka/` |
| Windows | `%LOCALAPPDATA%\Plativka\cache\` |

- `plativka.log` — what the player did: which file it loaded, why a track ended, pauses from outside.
- `mpv.log` — the audio engine's own log.

Attach both files to an [issue](https://github.com/dkindratyuk-web/plativka/issues/new/choose) — it makes the problem much easier to find.
