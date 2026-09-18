"""WhispSkrid — dictée appui-pour-parler adossée à Whisper (faster-whisper)."""

import re

__version__ = "1.0.1"


def version_debian(version: str = __version__) -> str:
    """Convertit la forme PEP 440 de `__version__` en forme Debian : le suffixe
    de pré-version `aN` devient `~alpha`, que Debian trie avant la version
    finale ; une version finale comme `1.0.1` n'en a pas et reste inchangée
    sous forme Debian."""
    return re.sub(r"a\d*$", "~alpha", version)
