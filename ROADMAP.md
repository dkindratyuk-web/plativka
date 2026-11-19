# Roadmap / Плани

Version 1.9 is out — see the [changelog](CHANGELOG.md). / Версія 1.9 вийшла — див. [історію змін](CHANGELOG.md).

## Next version / Наступна версія

- **Fix — done in `main`:** after a long idle or Mac sleep the player could ignore the Play button until restarted. Plativka now checks the sound engine (mpv) before playing, restarts it quietly with the same track at the same position, reconnects the audio after sleep and when playback stalls, and logs it.
  **Виправлення — уже в `main`:** після довгого простою чи сну Mac плеєр міг не реагувати на «грати» до перезапуску. Тепер Платівка перевіряє звуковий рушій (mpv) перед відтворенням, тихо перезапускає його з тим самим треком на тому ж місці, перепідключає звук після сну й коли відтворення «зависло», і пише це в журнал.

Ideas are welcome — open an issue on GitHub. / Ідеї вітаються — напишіть на GitHub.

## Not planned / Не плануємо

- Internet radio: Plativka stays a player for the music on your disk. / Інтернет-радіо: Платівка лишається плеєром для музики на диску.

## Later / Пізніше

- Packages: AUR, winget, Scoop, Flathub / пакети: AUR, winget, Scoop, Flathub.
