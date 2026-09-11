"""Point d'entrée CLI de WhispSkrid.

Squelette de la tranche 1 (PHASE_EXECUTION) : la surface complète
(-l/--model, --dictate/--dictate-stop/--toggle/--cancel, --status/--stop,
--diagnose, --download-model) arrive dans les tranches suivantes. Voir
_CADRE/SPECIFICATIONS/CONCEPTION_WHISPSKRID.md §7.
"""

from __future__ import annotations

import sys

from whispskrid import __version__


def main() -> int:
    if "--version" in sys.argv[1:]:
        print(f"whispskrid {__version__}")
        return 0
    print(f"whispskrid {__version__} — squelette PHASE_EXECUTION, aucune session résidente encore implémentée.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
