"""Résolution du dossier de modèles Whisper et téléchargement explicite.

Dossier de modèles géré par WhispSkrid ; le cache Hugging Face ne sert
qu'en repli à faster-whisper lui-même, jamais de chemin nominal.
"""

from __future__ import annotations

import os
from pathlib import Path

# Sous-ensemble figé du catalogue interne `faster_whisper.utils._MODELS`
# (dépôts CTranslate2 officiels, organisation Systran sur Hugging Face) :
# seuls les noms documentés (manpage, `--download-model`) sont proposés, jamais les variantes
# `distil-*`/`turbo` upstream, non couvertes. Taille
# approximative en Mo (ordre de grandeur, non remesurée).
MODEL_CATALOG: dict[str, tuple[str, int]] = {
    "tiny": ("Systran/faster-whisper-tiny", 75),
    "tiny.en": ("Systran/faster-whisper-tiny.en", 75),
    "base": ("Systran/faster-whisper-base", 145),
    "base.en": ("Systran/faster-whisper-base.en", 145),
    "small": ("Systran/faster-whisper-small", 480),
    "small.en": ("Systran/faster-whisper-small.en", 480),
    "medium": ("Systran/faster-whisper-medium", 1500),
    "medium.en": ("Systran/faster-whisper-medium.en", 1500),
    "large-v3": ("Systran/faster-whisper-large-v3", 3000),
}

# Motifs de fichiers réellement nécessaires à l'exécution (repris de
# `faster_whisper.utils.download_model`) : évite de rapatrier les poids
# PyTorch d'origine, présents dans le même dépôt à côté du modèle CTranslate2.
_MODEL_ALLOW_PATTERNS = [
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
]


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
       l'emplacement nominal utilisé par `--download-model`.
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


def model_cached(name: str, models_dir: Path) -> bool:
    """`True` si `name` (une clé de MODEL_CATALOG) est déjà présent dans
    `models_dir`, sous la convention de cache Hugging Face
    (`models--<org>--<repo>/`) — utilisé pour annoncer un téléchargement
    automatique avant qu'il ne démarre, plutôt que de laisser l'utilisateur
    face à un silence de plusieurs dizaines de secondes à plusieurs minutes
    sans explication (faster-whisper désactive sa propre barre de
    progression, voir `download_model()` ci-dessous)."""
    repo_id, _taille = MODEL_CATALOG.get(name, (None, 0))
    if repo_id is None:
        return False
    return (models_dir / f"models--{repo_id.replace('/', '--')}").is_dir()


def download_model(name: str) -> Path:
    """Télécharge `name` (une clé de MODEL_CATALOG) depuis Hugging Face Hub
    dans `resolve_models_dir()`, vérifie qu'il se charge réellement, et
    renvoie son chemin.

    Lève `ValueError` si `name` n'est pas dans MODEL_CATALOG, `RuntimeError`
    si le téléchargement ou le chargement de vérification échoue.

    N'appelle pas `faster_whisper.utils.download_model()` : ce dernier
    invoque `huggingface_hub.snapshot_download()` avec une barre de
    progression forcée à `disabled_tqdm`, ce qui rend un téléchargement de
    plusieurs centaines de Mo (jusqu'à ~3 Go pour `large-v3`) indiscernable
    d'un blocage. Le même appel est reproduit ici sans ce filtre.
    """
    if name not in MODEL_CATALOG:
        raise ValueError(name)

    import huggingface_hub

    repo_id, _taille = MODEL_CATALOG[name]
    models_dir = resolve_models_dir()

    try:
        huggingface_hub.snapshot_download(
            repo_id, cache_dir=str(models_dir), allow_patterns=_MODEL_ALLOW_PATTERNS
        )
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc

    try:
        from faster_whisper import WhisperModel

        WhisperModel(name, device="cpu", compute_type="int8", download_root=str(models_dir))
    except Exception as exc:
        raise RuntimeError(
            f"modèle téléchargé dans {models_dir} mais échec du chargement de vérification : {exc}"
        ) from exc

    return models_dir
