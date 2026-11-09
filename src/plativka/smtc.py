"""Windows: системна панель мультимедіа (SMTC).

Дає медіаклавіші (⏯ ⏭ ⏮ на клавіатурі й навушниках) і віконце з назвою треку й обкладинкою,
що з'являється над годинником при зміні гучності — як у Spotify чи браузера.
Якщо щось недоступно (стара Windows, немає пакетів winrt), модуль тихо вимикається.
"""
from __future__ import annotations

from pathlib import Path


class Smtc:
    def __init__(self, app):
        self.app = app
        self.ok = False
        self._status = None
        self._key = None
        self._player = None
        self._smtc = None

    def start(self) -> bool:
        try:
            from winrt.windows.media import MediaPlaybackType, SystemMediaTransportControlsButton as B
            from winrt.windows.media.playback import MediaPlayer
        except Exception:
            return False
        try:
            self._B = B
            self._player = MediaPlayer()
            self._player.command_manager.is_enabled = False  # звук грає mpv, а не цей плеєр
            s = self._smtc = self._player.system_media_transport_controls
            s.is_enabled = True
            s.is_play_enabled = s.is_pause_enabled = s.is_next_enabled = True
            s.is_previous_enabled = s.is_stop_enabled = True
            s.display_updater.type = MediaPlaybackType.MUSIC
            s.add_button_pressed(self._pressed)
            self.ok = True
        except Exception:
            self.ok = False
        return self.ok

    def _pressed(self, sender, args):
        B, app = self._B, self.app
        try:
            btn = args.button
        except Exception:
            return
        act = {B.PLAY: app.toggle_from_tray, B.PAUSE: app.toggle_from_tray,
               B.NEXT: app.next_from_tray, B.PREVIOUS: app.prev_from_tray,
               B.STOP: lambda: app.run_worker(app.stop())}.get(btn)
        if act:
            app.call_from_thread(act)

    def refresh(self, track, cover_file: Path | None):
        if not self.ok:
            return
        try:
            from winrt.windows.media import MediaPlaybackStatus as S
            app, p = self.app, self.app.player
            st = S.STOPPED if (app.stopped or not p.active) else (S.PAUSED if p.paused else S.PLAYING)
            if st != self._status:
                self._status = st
                self._smtc.playback_status = st
            key = (track.path if track else None, str(cover_file))
            if key != self._key:
                self._key = key
                du = self._smtc.display_updater
                mp = du.music_properties
                mp.title = (track.title if track else "") or ""
                mp.artist = (track.artist if track else "") or ""
                mp.album_title = (track.album if track else "") or ""
                if cover_file and cover_file.exists():
                    self.app.run_worker(self._set_thumb(str(cover_file)))
                else:
                    du.update()
        except Exception:
            self.ok = False

    async def _set_thumb(self, path: str):
        try:
            from winrt.windows.storage import StorageFile
            from winrt.windows.storage.streams import RandomAccessStreamReference
            f = await StorageFile.get_file_from_path_async(path)
            du = self._smtc.display_updater
            du.thumbnail = RandomAccessStreamReference.create_from_file(f)
            du.update()
        except Exception:
            try:
                self._smtc.display_updater.update()
            except Exception:
                pass

    def stop(self):
        try:
            if self._smtc is not None:
                self._smtc.is_enabled = False
        except Exception:
            pass
