# Roadmap / Плани

Version 1.9 is out — see the [changelog](CHANGELOG.md). / Версія 1.9 вийшла — див. [історію змін](CHANGELOG.md).

## Next version / Наступна версія

- **Fix — done in `main`:** after a long idle or Mac sleep the player could ignore the Play button until restarted. Plativka now checks the sound engine (mpv) before playing, restarts it quietly with the same track at the same position, reconnects the audio after sleep and when playback stalls, and logs it.
  **Виправлення — уже в `main`:** після довгого простою чи сну Mac плеєр міг не реагувати на «грати» до перезапуску. Тепер Платівка перевіряє звуковий рушій (mpv) перед відтворенням, тихо перезапускає його з тим самим треком на тому ж місці, перепідключає звук після сну й коли відтворення «зависло», і пише це в журнал.
- **Last.fm scrobbling (optional, off by default).** Connect your Last.fm account once (approve in the browser); Plativka then sends what you listen to — "now playing" and a scrobble after half of the track or 4 minutes (tracks longer than 30 s). Hearts in Plativka become "loved tracks" on Last.fm and back off when removed. Offline listening is kept in a queue and sent when the internet is back, so the player still works without a network. Possibly ListenBrainz too (an open alternative, just a token).
  **Скроблінг на Last.fm (за бажанням, вимкнено за замовчуванням).** Один раз підключити акаунт Last.fm (підтвердити в браузері); далі Платівка надсилає, що ви слухаєте, — «зараз грає» і скробл після половини треку або 4 хвилин (для треків довших за 30 с). Сердечка в Платівці стають «улюбленими треками» на Last.fm і знімаються, коли їх прибрати. Прослухане без інтернету зберігається в черзі й надсилається, коли мережа з'явиться, — плеєр і далі працює офлайн. Можливо, також ListenBrainz (відкрита альтернатива, лише токен).

Ideas are welcome — open an issue on GitHub. / Ідеї вітаються — напишіть на GitHub.

## Not planned / Не плануємо

- Internet radio: Plativka stays a player for the music on your disk. / Інтернет-радіо: Платівка лишається плеєром для музики на диску.

## Later / Пізніше

- Packages: AUR, winget, Scoop, Flathub / пакети: AUR, winget, Scoop, Flathub.
