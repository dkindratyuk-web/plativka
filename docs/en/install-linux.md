# Installing Plativka on Linux

[Українською](../uk/install-linux.md) · [Back to README](../../README.md)

Plativka is installed with one script that works on **Debian, Ubuntu, Kubuntu, Linux Mint, Pop!_OS, Fedora, Arch, Manjaro, EndeavourOS, CachyOS and openSUSE**. It installs the system packages Plativka needs, puts the player into your home folder and adds it to your applications menu. Every step is below — no Linux experience required.

The same archive installs both editions:

| | **Plativka Desktop** (recommended) | **Plativka for the terminal** |
|---|---|---|
| What you get | a regular window (Qt), real covers | a text interface in its own kitty window, real covers |
| Command | `./install.sh --desktop` (installs **both** editions) | `./install.sh` |
| In the menu | **Plativka Desktop** / **Платівка (вікно)** | **Plativka** / **Платівка** |
| From a terminal | `plativka-desktop` | `plativka` |

## What the script installs

| Package | What for |
|---|---|
| `mpv` | plays the sound |
| `kitty` | the terminal edition's own window, which can show real covers |
| `python3` (+ `python3-venv` on Debian/Ubuntu) | the player is written in Python |
| `libnotify` / `notify-send` | track notifications |
| `zenity` | the system folder dialog |
| Qt libraries: `libxcb-cursor0`, `libxkbcommon-x11-0`, `libegl1` (names differ per system) | only with `--desktop`: the window of Plativka Desktop |

The player itself goes to `~/.local/share/plativka` and does not touch the rest of the system. With `--desktop` the script also downloads Qt (about 150 MB) into that folder.

## Step 1. Download

Open the [latest release](https://github.com/dkindratyuk-web/plativka/releases/latest) and download `plativka-…-linux.tar.gz`. Your browser puts it into the **Downloads** folder.

## Step 2. Open a terminal

- **Ubuntu, Linux Mint, Pop!_OS, Debian (GNOME)**: press **Ctrl + Alt + T**.
- **Fedora (GNOME)**: press the **Super** (Windows) key, type `terminal`, press **Enter**.
- **KDE Plasma** (Kubuntu, Fedora KDE, Manjaro KDE…): open the menu, type `konsole`, press **Enter**.
- **Arch**: you already know 🙂

A window with a blinking cursor opens. Commands below are typed (or pasted with **Ctrl + Shift + V**) into it, each followed by **Enter**.

## Step 3. Unpack and run the installer

Copy these lines one by one (the version number in the name may differ — the `*` takes care of it):

```bash
cd ~/Downloads
tar -xzf plativka-*-linux.tar.gz
cd plativka-*-linux
./install.sh --desktop      # Plativka Desktop + the terminal edition
```

Only want the terminal edition? Run `./install.sh` without `--desktop` instead.

> If your Downloads folder has a different name (for example `~/Завантаження` on a Ukrainian system), use it in the first line: `cd ~/Завантаження`.

The script asks for **your password** — this is needed to install system packages. **Nothing is shown while you type the password — that is normal.** Type it and press Enter.

Installation takes 1–5 minutes. At the end you see a line starting with `✓ Done!`.

## Step 4. Start Plativka

- Open the applications menu and search for **Plativka Desktop** (on a Ukrainian system: **Платівка (вікно)**), or **Plativka** for the terminal edition.
- Or type `plativka-desktop` (or `plativka`) in a terminal. If the command is not found, open a new terminal window first.

Then press **L** to add a music folder — or drag a folder from your file manager into the Plativka window. Everything else: [Plativka Desktop guide](desktop.md) · [terminal edition guide](terminal.md).

## What exactly happens on each system

You don't need this unless the script fails — then you can run the commands yourself.

### Debian / Ubuntu / Kubuntu / Linux Mint / Pop!_OS

```bash
sudo apt update
sudo apt install mpv kitty python3 python3-venv libnotify-bin zenity
sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libegl1      # only for Plativka Desktop
```

### Fedora

```bash
sudo dnf install mpv kitty python3 libnotify zenity
sudo dnf install xcb-util-cursor libxkbcommon-x11 mesa-libEGL   # only for Plativka Desktop
```

If `mpv` is not found, the script enables the free RPM Fusion repository first:

```bash
sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
sudo dnf install mpv
```

### Arch / Manjaro / EndeavourOS / CachyOS

```bash
sudo pacman -S --needed mpv kitty python libnotify zenity
sudo pacman -S --needed xcb-util-cursor libxkbcommon-x11        # only for Plativka Desktop
```

### openSUSE

```bash
sudo zypper install mpv kitty python3 libnotify-tools zenity
sudo zypper install libxcb-cursor0 libxkbcommon-x11-0 libEGL1   # only for Plativka Desktop
```

### Then, on every system

```bash
python3 -m venv ~/.local/share/plativka/venv
~/.local/share/plativka/venv/bin/pip install ".[desktop]"   # run inside the unpacked folder; "." for the terminal edition only
```

The script also creates `~/.local/bin/plativka` (and `plativka-desktop`) and the menu entries in `~/.local/share/applications/`.

Already have the packages, or don't want the script to touch them? Run `PLATIVKA_SKIP_PACKAGES=1 ./install.sh --desktop`.

## Desktop integration

- **Media keys** (Play/Pause, Next, Previous on your keyboard or headphones) work automatically in both editions.
- The **media widget** in GNOME (top bar → notifications/calendar) and KDE Plasma (system tray) shows the track and cover and controls Plativka. The same goes for `playerctl`.
- Track notifications show the album cover.
- Plativka Desktop also has a tray icon (KDE shows it right away; on GNOME it needs the AppIndicator extension, which Ubuntu has by default).

## Updating

Download the new archive and run `./install.sh --desktop` (or `./install.sh`) from it again. The library, playlist and settings are kept.

## Uninstalling

From the unpacked folder:

```bash
./uninstall.sh          # removes both editions, keeps settings and library
./uninstall.sh --all    # removes settings and library too
```

System packages (mpv, kitty, Qt libraries) stay installed — other programs may use them. Remove them with your package manager if you like.
