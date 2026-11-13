# Releasing / Як випускати нову версію

Every release ships with its description — on GitHub **and** on the website.
Кожен випуск виходить разом з описом — на GitHub **і** на сайті.

**When to release / Коли випускати.** Do not bump the version or publish after every fix or feature on your own. Commit changes (with docs) to `main` and ask; release only when the author says to make the new version — more changes fit into one version, and GitHub isn't loaded with needless builds.
Нову версію не випускаємо самі після кожного виправлення чи функції: зміни (з документацією) йдуть у `main`, а випуск — лише коли автор скаже зробити нову версію.

1. **Changelog** — `CHANGELOG.md`: what's new and what was fixed, in English and Ukrainian.
2. **How to use** — `docs/{en,uk}/desktop.md`, `docs/{en,uk}/terminal.md`: how to turn on and control each new feature (menu, keys, phone remote), in plain words.
3. **Why it's useful** — the advantage explained so that a beginner understands it (README feature list, website feature cards).
4. **Problems** — `docs/{en,uk}/troubleshooting.md`: what can go wrong and how to fix it.
5. **README** (`README.md`, `README.uk.md`): features and keys.
6. **Website** — `tools/build_site.py`: feature cards, sections for big features; then `python tools/build_site.py` (What's new and Help pages are built from the changelog and troubleshooting).
7. **Release notes** — `docs/release-notes/vX.Y.Z.md`: what's new + a short "How to use".
8. Version in `src/plativka/__init__.py` and `pyproject.toml`, tests green. Push `main` first and **wait until CI has finished**; only then push `main` to the `release` branch. CI and the release build both need macOS machines, and GitHub may not give enough of them at once — then the Apple Silicon builds wait 15 minutes and get cancelled. (If that happens anyway: Actions → the Release run → **Re-run failed jobs**.)
9. After the release: check GitHub (8 files), the website and SourceForge.
