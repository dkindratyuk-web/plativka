"""Linux: MPRIS — медіаклавіші, віджет плеєра в GNOME/KDE, керування з playerctl.

Увага: без `from __future__ import annotations` — dbus-next читає D-Bus-типи з анотацій.
"""
import asyncio
import os
from pathlib import Path

from dbus_next import PropertyAccess, Variant
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, dbus_property, method, signal

OBJ = "/org/mpris/MediaPlayer2"
NO_TRACK = "/org/mpris/MediaPlayer2/TrackList/NoTrack"


def _spawn(coro):
    if coro is not None and asyncio.iscoroutine(coro):
        asyncio.get_running_loop().create_task(coro)


class Root(ServiceInterface):
    def __init__(self, app):
        super().__init__("org.mpris.MediaPlayer2")
        self.app = app

    @method()
    def Raise(self):
        pass

    @method()
    def Quit(self):
        _spawn(self.app.action_quit())

    @dbus_property(access=PropertyAccess.READ)
    def CanQuit(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanRaise(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def HasTrackList(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def Identity(self) -> "s":
        return "Plativka"

    @dbus_property(access=PropertyAccess.READ)
    def DesktopEntry(self) -> "s":
        return "plativka"

    @dbus_property(access=PropertyAccess.READ)
    def SupportedUriSchemes(self) -> "as":
        return ["file"]

    @dbus_property(access=PropertyAccess.READ)
    def SupportedMimeTypes(self) -> "as":
        return ["audio/mpeg", "audio/flac", "audio/mp4", "audio/ogg"]


class Player(ServiceInterface):
    def __init__(self, app):
        super().__init__("org.mpris.MediaPlayer2.Player")
        self.app = app
        self._status = "Stopped"
        self._meta = {}
        self._loop = "None"
        self._shuffle = False
        self._volume = app.volume / 100

    # ── команди ──
    @method()
    def Next(self):
        _spawn(self.app.next())

    @method()
    def Previous(self):
        _spawn(self.app.prev())

    @method()
    def Pause(self):
        if self.app.player.active and not self.app.player.paused:
            _spawn(self.app.player.set_pause(True))

    @method()
    def PlayPause(self):
        _spawn(self.app.toggle())

    @method()
    def Stop(self):
        _spawn(self.app.stop())

    @method()
    def Play(self):
        _spawn(self.app.play())

    @method()
    def Seek(self, offset: "x"):
        _spawn(self.app.seek_rel(offset / 1e6))

    @method()
    def SetPosition(self, track_id: "o", position: "x"):
        _spawn(self.app.player.seek(position / 1e6))

    @method()
    def OpenUri(self, uri: "s"):
        pass

    @signal()
    def Seeked(self) -> "x":
        return int(self.app.player.time_pos * 1e6)

    # ── стан ──
    @dbus_property(access=PropertyAccess.READ)
    def PlaybackStatus(self) -> "s":
        return self._status

    @dbus_property()
    def LoopStatus(self) -> "s":
        return self._loop

    @LoopStatus.setter
    def LoopStatus(self, val: "s"):
        self.app.repeat = {"None": "off", "Playlist": "all", "Track": "one"}.get(val, "off")
        self.app.update_flags()

    @dbus_property(access=PropertyAccess.READ)
    def Rate(self) -> "d":
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def MinimumRate(self) -> "d":
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def MaximumRate(self) -> "d":
        return 1.0

    @dbus_property()
    def Shuffle(self) -> "b":
        return self._shuffle

    @Shuffle.setter
    def Shuffle(self, val: "b"):
        self.app.shuffle = bool(val)
        self.app.update_flags()

    @dbus_property(access=PropertyAccess.READ)
    def Metadata(self) -> "a{sv}":
        return self._meta

    @dbus_property()
    def Volume(self) -> "d":
        return self._volume

    @Volume.setter
    def Volume(self, val: "d"):
        _spawn(self.app.set_volume(int(round(max(0.0, min(1.0, val)) * 100))))

    @dbus_property(access=PropertyAccess.READ)
    def Position(self) -> "x":
        return int((self.app.player.time_pos or 0) * 1e6)

    @dbus_property(access=PropertyAccess.READ)
    def CanGoNext(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanGoPrevious(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanPlay(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanPause(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanSeek(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanControl(self) -> "b":
        return True


class Mpris:
    """Тримає зв'язок із сесійною шиною й повідомляє робочий стіл про зміни стану."""

    def __init__(self, app):
        self.app = app
        self.bus = None
        self.player = Player(app)
        self.root = Root(app)
        self._meta_key = None

    async def start(self) -> bool:
        if not os.environ.get("DBUS_SESSION_BUS_ADDRESS") and not os.environ.get("XDG_RUNTIME_DIR"):
            return False
        try:
            self.bus = await MessageBus().connect()
            self.bus.export(OBJ, self.root)
            self.bus.export(OBJ, self.player)
            await self.bus.request_name(f"org.mpris.MediaPlayer2.plativka.instance{os.getpid()}")
            return True
        except Exception:
            self.bus = None
            return False

    def refresh(self, track, cover_file: Path | None):
        """Викликається кожні ~0,25 с; надсилає сигнал лише коли щось змінилось."""
        if self.bus is None:
            return
        app, p, pl = self.app, self.app.player, self.player
        changed = {}
        status = "Stopped" if (app.stopped or not p.active) else ("Paused" if p.paused else "Playing")
        if status != pl._status:
            pl._status = changed["PlaybackStatus"] = status
        loop = {"off": "None", "all": "Playlist", "one": "Track"}[app.repeat]
        if loop != pl._loop:
            pl._loop = changed["LoopStatus"] = loop
        if app.shuffle != pl._shuffle:
            pl._shuffle = changed["Shuffle"] = app.shuffle
        vol = app.volume / 100
        if abs(vol - pl._volume) > 1e-3:
            pl._volume = changed["Volume"] = vol
        dur = p.duration or (track.length if track else 0)
        key = (track.path if track else None, int(dur), str(cover_file))
        if key != self._meta_key:
            self._meta_key = key
            if track is None:
                meta = {"mpris:trackid": Variant("o", NO_TRACK)}
            else:
                meta = {
                    "mpris:trackid": Variant("o", f"/org/plativka/track/{abs(hash(track.path)) % 10**9}"),
                    "xesam:title": Variant("s", track.title or ""),
                    "xesam:artist": Variant("as", [track.artist] if track.artist else []),
                    "xesam:album": Variant("s", track.album or ""),
                    "xesam:url": Variant("s", Path(track.path).as_uri()),
                }
                if dur:
                    meta["mpris:length"] = Variant("x", int(dur * 1e6))
                if cover_file and cover_file.exists():
                    meta["mpris:artUrl"] = Variant("s", cover_file.as_uri())
            pl._meta = changed["Metadata"] = meta
        if changed:
            pl.emit_properties_changed(changed)

    def seeked(self):
        if self.bus is not None:
            self.player.Seeked()

    def stop(self):
        if self.bus is not None:
            try:
                self.bus.disconnect()
            except Exception:
                pass
