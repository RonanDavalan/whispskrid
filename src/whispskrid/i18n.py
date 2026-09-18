"""Sélection de la langue d'interface (gettext, catalogue `locales/`).

Catalogue interne au paquet (`src/whispskrid/locales/<lang>/LC_MESSAGES/`) —
pas à la racine du dépôt — pour qu'il voyage avec le paquet installé sans
étape de packaging séparée (`pip install`/`.whl`/`.deb` embarquent
`src/whispskrid/` tel quel). Le français est la langue source : les chaînes
du code sont déjà en français, aucun catalogue `fr.po` n'est donc nécessaire
— seuls `en`, `de`, `es` ont un `.po`/`.mo`.

`-l`/`--lang` force la langue de l'interface ET
de la reconnaissance pour la session — la même valeur sert aux deux. Sans
`-l`, repli sur `LANG` de l'environnement, puis français par défaut.
"""

from __future__ import annotations

import gettext
import os
from pathlib import Path

DOMAINE = "whispskrid"
LANGUES_SUPPORTEES = ("en", "fr", "de", "es")

_LOCALES_DIR = Path(__file__).resolve().parent / "locales"


def resoudre_langue(lang: str | None = None) -> str:
    """Langue effective : `lang` explicite, sinon `LANG` de l'environnement,
    sinon français. Le français n'a pas de catalogue : c'est la langue
    source des chaînes du code, `gettext` la sert nativement (`fallback`)."""
    if lang and lang in LANGUES_SUPPORTEES:
        return lang
    env_lang = (os.environ.get("LANG", "") or "").split("_")[0].split(".")[0].lower()
    if env_lang in LANGUES_SUPPORTEES:
        return env_lang
    return "fr"


def installer(lang: str | None = None):
    """Renvoie la fonction `_()` liée à la langue résolue.

    `fallback=True` : une langue sans catalogue compilé (français, ou un
    catalogue absent) renvoie les chaînes source telles quelles plutôt que
    de lever une exception — jamais un plantage pour un défaut de traduction.
    """
    langue = resoudre_langue(lang)
    traduction = gettext.translation(
        DOMAINE, localedir=str(_LOCALES_DIR), languages=[langue], fallback=True
    )
    return traduction.gettext
