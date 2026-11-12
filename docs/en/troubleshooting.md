# Troubleshooting

[Українською](../uk/troubleshooting.md) · [Back to README](../../README.md)

Sections marked *(terminal)* or *(desktop)* apply only to that edition of Plativka; the rest apply to both.

## A track stops before its end and the next one starts

The file is truncated or damaged — this is common with "leaked" releases. The file claims to be longer than the sound it actually contains, so the player reaches the real end earlier. Plativka shows a message like *"The track stopped at 0:09 of 0:40: the file looks truncated or damaged"* and moves on. Re-download the file from another source.

## The music paused by itself

Usually something outside the player paused it: AirPods and many headphones pause when you take one out, a media key was pressed, or another app started playing sound. Plativka shows *"Paused from outside…"* in that case.

## Music stopped after the last track

That is the end of the playlist. Turn on **repeat: all** with **R** to loop it.

## A track shows 0:00 in the playlist

The duration could not be read from the file's tags. Plativka shows an estimate and takes the exact duration from mpv as soon as the track starts playing.

## The cover is an empty square *(terminal)*

Your terminal said it can show pictures, but something went wrong. Start Plativka with `plativka --no-images` and tell us your terminal and its version in an [issue](https://github.com/dkindratyuk-web/plativka/issues).

## Covers look blocky *(terminal)*

Your terminal cannot show pictures (Terminal.app on macOS, the classic Windows console, GNOME Terminal…), so covers are drawn with coloured blocks. The macOS DMG and the Linux script open the terminal edition in its own window that shows real covers. Or press **O** twice to replace covers with a record — or use [Plativka Desktop](desktop.md), which shows real covers everywhere.

## macOS: "Plativka Desktop" / "Plativka" cannot be opened, developer cannot be verified

Expected for a free app without a paid Apple certificate. See [first launch](install-macos.md#3-first-launch-one-time-only).

## Windows: "Windows protected your PC"

Expected for a free program without a paid certificate: **More info → Run anyway**. See [installing on Windows](install-windows.md).

## Windows: the installer says "DeleteFile failed; code 5. Access is denied"

Plativka was still running, so Windows would not let the installer replace it. Quit it (tray icon → **Quit Plativka**) and click **Retry**. Installers from version 1.3.4 on close Plativka by themselves.

## Windows 11: no translucent background *(desktop)*

The Mica background needs **Settings → Personalization → Colors → Transparency effects** turned on. In some virtual machines transparency is not available at all — then the window simply has a solid background.

## Windows: H does not hide the player to the tray *(terminal)*

Hiding works only in the player's own window, which the **Plativka** shortcut opens. If you started `plativka.exe` inside Windows Terminal, use the shortcut instead. In Plativka Desktop use **☰ → View → Minimize to tray**.

## Linux: no sound / "mpv is required"

Install mpv with your package manager (see [installing on Linux](install-linux.md#what-exactly-happens-on-each-system)). On Fedora mpv may need the RPM Fusion repository.

## Linux: Plativka Desktop does not open

Start `plativka-desktop` in a terminal to see the error. *"Could not load the Qt platform plugin xcb"* means Qt's system libraries are missing — install them (`sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libegl1` on Debian/Ubuntu/Kubuntu; see [installing on Linux](install-linux.md#what-exactly-happens-on-each-system) for other systems) or run `./install.sh --desktop` again.

## Linux: media keys don't work

They need a desktop session with D-Bus (GNOME, KDE, Xfce, Cinnamon… — practically all of them). Check with `playerctl -l` — `plativka.instance…` should be listed.

## No system notifications

First check that notifications are on in Plativka (`N`, the **notifications** switch). Plativka Desktop only shows them when its window is in the background or collapsed to the mini player.

- **macOS**: System Settings → Notifications → **Plativka Desktop** (for the terminal edition: **Plativka**, or **Script Editor** if you run it in Terminal.app) → allow notifications.
- **Windows**: Settings → System → Notifications → make sure notifications and **Plativka Desktop** / **Plativka** are on. Notifications with a cover need the Start-menu shortcut made by the installer.
- **Linux**: install `libnotify-bin` (Debian/Ubuntu) or `libnotify` (Fedora/Arch).

## macOS: the "Help" menu at the top of the screen opens the wrong site *(terminal)*

The menu bar in the macOS DMG belongs to kitty, the window Plativka runs in, so its **Help** menu leads to kitty's website. Plativka's own help is **F1** (or **?**) inside the player — it has the keys, the settings and links to Plativka's GitHub page.

## The volume keys don't change the player's volume

The player's volume mirrors the system volume. On Linux this needs PipeWire's `wpctl` or PulseAudio's `pactl`; without them the player uses its own volume. In the terminal edition check **F1 → Volume**: if it says *unavailable*, the system volume can't be read (on Linux install PipeWire's `wpctl` or PulseAudio's `pactl`), and the player uses its own volume. You can also switch to a separate player volume there on purpose.

## L shows a folder list inside the player instead of a system window *(terminal)*

The system folder dialog is used when one is available. On Linux it needs `zenity` (GNOME and most desktops) or `kdialog` (KDE) — the install script installs zenity; or install it yourself, e.g. `sudo apt install zenity`. Over SSH there is no system dialog, so the in-player picker is used.

## macOS: media keys don't work in any app (Plativka, Music, YouTube)

If ⏮ ⏯ ⏭ in Control Center's **Now Playing** work, but F7 F8 F9 on the keyboard do nothing anywhere while volume keys work, the system service that handles media keys (`rcd`) may be turned off for your user — an old "stop media keys from opening iTunes" tip or a utility could have done that. Check in Terminal:

```
launchctl print-disabled gui/$(id -u) | grep -i rcd
```

If it says `"com.apple.rcd" => disabled`, turn it back on:

```
launchctl enable gui/$(id -u)/com.apple.rcd
launchctl bootstrap gui/$(id -u) /System/Library/LaunchAgents/com.apple.rcd.plist
```

(or log out and back in after the first command).

## macOS: ⏮ ⏯ ⏭ in Control Center work, but the keyboard keys don't

Some keyboards (most non-Apple ones, or a Mac with "Use F1, F2, etc. keys as standard function keys" turned on) send F7 F8 F9 as plain function keys instead of media keys. Since 1.1.2 Plativka treats F7 F8 F9 as previous · pause · next while its window is in front. To control it from other apps too, use the media keys (on Apple keyboards — without Fn, or with Fn if that setting is on).

## The phone remote does not open on the phone

- **Same network.** The phone must be on the same Wi-Fi as the computer — not on mobile data, and not on a guest network (guest networks usually isolate devices from each other).
- **Firewall.** The first time, macOS or Windows asks whether Plativka may accept incoming connections. If you clicked “Deny”: on a Mac — System Settings → Network → Firewall → Options, allow Plativka; on Windows — Windows Security → Firewall → “Allow an app through firewall”, tick Plativka for private networks. On Linux, open the port Plativka shows (8765 by default) if you use a firewall (`sudo ufw allow 8765/tcp`).
- **The QR code says “already used”.** Each QR code works once and changes every 10 minutes and when the remote window is closed. Open the remote window again and scan the new one.
- **“Too many failed attempts”.** After many wrong codes, the address is blocked for 10 minutes — wait, then show a new code.
- **The phone was connected but now shows the code screen.** It was disconnected in Plativka (or “Disconnect all” was pressed). Scan the QR code again.
- **The address changed.** If the router gave the computer a new address, the old bookmark stops working; scan the QR code again. To avoid it, reserve a fixed address for the computer in the router (DHCP reservation).

## Logs

If something goes wrong, the logs show what happened:

| | Folder |
|---|---|
| macOS, Linux | `~/.cache/plativka/` |
| Windows | `%LOCALAPPDATA%\Plativka\cache\` |

- `plativka.log` — what the player did: which file it loaded, why a track ended, pauses from outside.
- `mpv.log` — the audio engine's own log.

Both editions write to the same files.

Attach both files to an [issue](https://github.com/dkindratyuk-web/plativka/issues/new/choose) — it makes the problem much easier to find.
