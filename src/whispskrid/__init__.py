"""WhispSkrid — dictée appui-pour-parler adossée à Whisper (faster-whisper)."""

import re

__version__ = "1.0.0"


def version_debian(version: str = __version__) -> str:
    """Convertit la forme PEP 440 de `__version__` en forme Debian (invariant
    GOUVERNANCE/PROTOCOLE_PUBLICATION.md n°1) : retire le suffixe de
    pré-version PEP 440 (`aN`/`bN`/`rcN`) au profit de `~alpha`/`~beta`/`~rc`
    quand il y en a un ; une version finale comme `1.0.0` n'en a pas et
    reste inchangée sous forme Debian."""
    return re.sub(r"a\d*$", "~alpha", version)
