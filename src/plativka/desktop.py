"""Точка входу віконної версії: plativka-desktop."""
import os


def main():
    os.environ["PLATIVKA_UI"] = "desktop"   # до імпорту i18n: мова з налаштувань віконної версії
    from .gui import main as run
    run()


if __name__ == "__main__":
    main()
