# Installing Plativka on Linux

[Українською](../uk/install-linux.md) · [Back to README](../../README.md)

Plativka is installed with one script that works on **Debian, Ubuntu, Linux Mint, Pop!_OS, Fedora, Arch, Manjaro, EndeavourOS and openSUSE**. It installs the system packages Plativka needs, puts the player into your home folder and adds **Plativka** to your applications menu. Every step is below — no Linux experience required.

## What the script installs

| Package | What for |
|---|---|
| `mpv` | plays the sound |
| `kitty` | Plativka's own window, which can show real album covers |
| `python3` (+ `python3-venv` on Debian/Ubuntu) | the player is written in Python |
| `libnotify` / `notify-send` | track notifications |

The player itself goes to `~/.local/share/plativka` and does not touch the rest of the system.

## Step 1. Download

Open the [latest release](https://github.com/dkindratyuk-web/plativka/releases/latest) and download `plativka-…-linux.tar.gz`. Your browser puts it into the **Downloads** folder.

## Step 2. Open a terminal

- **Ubuntu, Linux Mint, Pop!_OS, Debian (GNOME)**: press **Ctrl + Alt + T**.
- **Fedora (GNOME)**: press the **Super** (Windows) key, type `terminal`, press **Enter**.
- **KDE Plasma** (Kubuntu, Fedora KDE, Manjaro KDE…): open the menu, type `konsole`, press **Enter**.
- **Arch**: you already know 🙂

A window with a blinking cursor opens. Commands below are typed (or pasted with **Ctrl + Shift + V**) into it, each followed by **Enter**.

## Step 3. Unpack and run the installer

Copy these three lines one by one (the version number in the name may differ — the `*` takes care of it):

```bash
cd ~/Downloads
tar -xzf plativka-*-linux.tar.gz
cd plativka-*-linux && ./install.sh
```

> If your Downloads folder has a different name (for example `~/Завантаження` on a Ukrainian system), use it in the first line: `cd ~/Завантаження`.

The script asks for **your password** — this is needed to install system packages. **Nothing is shown while you type the password — that is normal.** Type it and press Enter.

Installation takes 1–3 minutes. At the end you see:

```
✓ Done! Start: find "Plativka" in the applications menu or type plativka in a terminal.
```

## Step 4. Start Plativka

- Open the applications menu and search for **Plativka** (or **Платівка**). It opens in its own window.
- Or type `plativka` in a terminal (if the command is not found, open a new terminal window first).

Then press **L** to add a music folder — or drag a folder from your file manager into the Plativka window. See [Using Plativka](usage.md).

## What exactly happens on each system

You don't need this unless the script fails — then you can run the commands yourself.

### Debian / Ubuntu / Linux Mint / Pop!_OS

```bash
sudo apt update
sudo apt install mpv kitty python3 python3-venv libnotify-bin
```

### Fedora

```bash
sudo dnf install mpv kitty python3 libnotify
```

If `mpv` is not found, the script enables the free RPM Fusion repository first:

```bash
sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
sudo dnf install mpv
```

### Arch / Manjaro / EndeavourOS / CachyOS

```bash
sudo pacman -S --needed mpv kitty python libnotify
```

### openSUSE

```bash
sudo zypper install mpv kitty python3 libnotify-tools
```

### Then, on every system

```bash
python3 -m venv ~/.local/share/plativka/venv
~/.local/share/plativka/venv/bin/pip install .      # run inside the unpacked folder
```

The script also creates `~/.local/bin/plativka` and the menu entry `~/.local/share/applications/plativka.desktop`.

Already have the packages, or don't want the script to touch them? Run `PLATIVKA_SKIP_PACKAGES=1 ./install.sh`.

## Desktop integration

- **Media keys** (Play/Pause, Next, Previous on your keyboard or headphones) work automatically.
- The **media widget** in GNOME (top bar → notifications/calendar) and KDE Plasma (system tray) shows the track and cover and controls Plativka. The same goes for `playerctl`.
- Closing the window closes Plativka.

## Updating

Download the new archive and run `./install.sh` from it again. The library, playlist and settings are kept.

## Uninstalling

From the unpacked folder:

```bash
./uninstall.sh          # removes the player, keeps settings and library
./uninstall.sh --all    # removes settings and library too
```

System packages (mpv, kitty) stay installed — other programs may use them. Remove them with your package manager if you like.
