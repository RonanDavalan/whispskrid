"""Résolution du dossier de modèles Whisper.

Voir _CADRE/SPECIFICATIONS/CONCEPTION_WHISPSKRID.md §5.1 (D4 — dossier de
modèles géré, cache Hugging Face en repli seulement seulement pour
faster-whisper lui-même, jamais le chemin nominal de WhispSkrid).
"""

from __future__ import annotations

import os
from pathlib import Path


def resolve_models_dir() -> Path:
    """Renvoie le dossier de modèles géré à utiliser comme `download_root`
    pour faster-whisper, dans cet ordre de priorité :

    1. surcharge explicite `WHISPSKRID_MODELS_DIR` ;
    2. dossier utilisateur `~/.local/share/whispskrid/whisper-models` s'il
       existe déjà et contient au moins un modèle ;
    3. dossier système `/usr/share/whispskrid/whisper-models` (mode paquet)
       s'il existe et contient au moins un modèle ;
    4. dossier des sources `whisper-models/` à la racine du dépôt de code
       (mode clone Git) s'il existe et contient au moins un modèle ;
    5. à défaut, le dossier utilisateur est créé et renvoyé : c'est
       l'emplacement nominal pour un futur téléchargement
       (`--download-model`, tranche suivante).
    """
    override = os.environ.get("WHISPSKRID_MODELS_DIR")
    if override:
        return Path(override)

    user_dir = Path.home() / ".local/share/whispskrid/whisper-models"
    system_dir = Path("/usr/share/whispskrid/whisper-models")
    # models.py -> whispskrid/ (package) -> src/ -> racine du dépôt de code
    source_dir = Path(__file__).resolve().parents[2] / "whisper-models"

    for candidate in (user_dir, system_dir, source_dir):
        if candidate.is_dir() and any(candidate.iterdir()):
            return candidate

    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir
