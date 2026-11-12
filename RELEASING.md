# Releasing / Як випускати нову версію

Every release ships with its description — on GitHub **and** on the website.
Кожен випуск виходить разом з описом — на GitHub **і** на сайті.

1. **Changelog** — `CHANGELOG.md`: what's new and what was fixed, in English and Ukrainian.
2. **How to use** — `docs/{en,uk}/desktop.md`, `docs/{en,uk}/terminal.md`: how to turn on and control each new feature (menu, keys, phone remote), in plain words.
3. **Why it's useful** — the advantage explained so that a beginner understands it (README feature list, website feature cards).
4. **Problems** — `docs/{en,uk}/troubleshooting.md`: what can go wrong and how to fix it.
5. **README** (`README.md`, `README.uk.md`): features and keys.
6. **Website** — `tools/build_site.py`: feature cards, sections for big features; then `python tools/build_site.py` (What's new and Help pages are built from the changelog and troubleshooting).
7. **Release notes** — `docs/release-notes/vX.Y.Z.md`: what's new + a short "How to use".
8. Version in `src/plativka/__init__.py` and `pyproject.toml`, tests green, then push `main` to the `release` branch.
9. After the release: check GitHub (8 files), the website and SourceForge.
