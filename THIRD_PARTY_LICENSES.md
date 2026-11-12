# Third-party software / Стороннє програмне забезпечення

Plativka's own code is MIT-licensed (see [LICENSE](LICENSE)). The installers also ship the following programs and libraries, each under its own licence. Their source code is available at the links below.

Власний код Платівки поширюється за ліцензією MIT (див. [LICENSE](LICENSE)). Інсталятори також містять такі програми й бібліотеки, кожна — за своєю ліцензією. Їхній вихідний код доступний за посиланнями нижче.

| Component | Where | Licence | Source |
|---|---|---|---|
| **mpv** — audio engine (official build) | macOS DMG, Windows installer | GPL-2.0-or-later (with LGPL parts, FFmpeg and other libraries inside) | https://github.com/mpv-player/mpv |
| **kitty** — the player window | macOS DMG (renamed to "Plativka", icon replaced) | GPL-3.0 | https://github.com/kovidgoyal/kitty |
| **Python** | macOS DMG, Windows installer | PSF License | https://www.python.org |
| **Textual**, **Rich** | all | MIT | https://github.com/Textualize/textual · https://github.com/Textualize/rich |
| **mutagen** | all | GPL-2.0-or-later | https://github.com/quodlibet/mutagen |
| **Pillow** | all | MIT-CMU (HPND) | https://github.com/python-pillow/Pillow |
| **textual-image** | all | LGPL-3.0-or-later | https://github.com/lnqs/textual-image |
| **dbus-next** | Linux | MIT | https://github.com/altdesktop/python-dbus-next |
| **pystray** | Windows | LGPL-3.0 | https://github.com/moses-palmer/pystray |
| **Qt 6 / PySide6** | Plativka Desktop | LGPL-3.0 (Qt for Python, dynamically linked) | https://code.qt.io/cgit/pyside/pyside-setup.git |
| **qasync** | Plativka Desktop | BSD-2-Clause | https://github.com/CabbageDevelopment/qasync |
| **pycaw**, **comtypes** | Windows | MIT | https://github.com/AndreMiras/pycaw · https://github.com/enthought/comtypes |
| **PyWinRT** (winrt-*) | Windows | MIT | https://github.com/pywinrt/pywinrt |
| **segno** — QR code for the phone remote | all | BSD-3-Clause | https://github.com/heuer/segno |
| **Send2Trash** — moving files to the Trash | all | BSD-3-Clause | https://github.com/arsenetar/send2trash |

The versions of mpv and kitty used for a release are listed at the top of [.github/workflows/release.yml](.github/workflows/release.yml); the matching source is available from the links above under the same version tags. On Linux, mpv and kitty come from your distribution's packages.

Версії mpv і kitty, використані для релізу, вказано на початку [.github/workflows/release.yml](.github/workflows/release.yml); відповідний вихідний код доступний за посиланнями вище під тими самими тегами версій. На Linux mpv і kitty встановлюються з пакетів вашого дистрибутива.
