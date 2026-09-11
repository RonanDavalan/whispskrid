"""WhispSkrid — dictée appui-pour-parler adossée à Whisper (faster-whisper)."""

import re

__version__ = "0.1.0a0"


def version_debian(version: str = __version__) -> str:
    """Convertit la forme PEP 440 de `__version__` en forme Debian (invariant
    GOUVERNANCE/PROTOCOLE_PUBLICATION.md n°1 : `X.Y.Z~alpha`, sans le `a0`
    PEP 440 requis par le paquet Python)."""
    return re.sub(r"a\d*$", "~alpha", version)
