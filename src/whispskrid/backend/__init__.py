"""Adaptateur de backend de reconnaissance vocale.

Interface étroite à trois fonctions, pour qu'un second backend
(whisper.cpp) puisse être ajouté plus tard sans toucher au reste du projet.
Voir _CADRE/SPECIFICATIONS/CONCEPTION_WHISPSKRID.md §4. Seule implémentation
livrée en v0.1.0 : `faster-whisper` (D3).

État chargé (modèle, paramètres effectifs) gardé au niveau du module : une
session résidente n'appelle `load()` qu'une fois (D2), tout le reste du
processus partage le même état.
"""

from __future__ import annotations

_model = None
_state: dict = {}


def load(
    model_name: str = "base",
    device: str = "auto",
    compute_type: str = "auto",
    beam_size: int = 5,
) -> None:
    """Charge le modèle en mémoire. Appelé une fois au démarrage de la
    session résidente. Lève une exception claire si le modèle est absent ou
    si l'import CTranslate2 échoue (§4.1)."""
    global _model, _state

    from whispskrid.models import resolve_models_dir

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # import CTranslate2/faster-whisper absent
        raise RuntimeError(
            "faster-whisper ou CTranslate2 introuvable dans l'environnement "
            "Python courant — vérifier l'installation (pip install faster-whisper)."
        ) from exc

    models_dir = resolve_models_dir()
    try:
        _model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            download_root=str(models_dir),
        )
    except Exception as exc:
        raise RuntimeError(
            f"impossible de charger le modèle « {model_name} » "
            f"(models.dir = {models_dir}) : {exc}"
        ) from exc

    _state = {
        "backend": "faster-whisper",
        "model_size_or_path": model_name,
        "models_dir": str(models_dir),
        "device": device,
        "compute_type": compute_type,
        "beam_size": beam_size,
    }


def transcribe(audio, language: str | None) -> str:
    """Transcrit un tampon audio mono 16 kHz float32. `language` est un code
    (« fr », « en »…) ou None pour autodétection. Retourne le texte brut,
    sans post-traitement (§4.2, §9 — le post-traitement est fait ailleurs)."""
    if _model is None:
        raise RuntimeError("backend non chargé : appeler load() avant transcribe()")

    segments, _info = _model.transcribe(
        audio,
        language=language,
        beam_size=_state.get("beam_size", 5),
        vad_filter=False,
    )
    return "".join(segment.text for segment in segments).strip()


def info() -> dict:
    """Dictionnaire lisible par --diagnose : nom du backend, chemin du
    modèle, device, compute_type, CUDA disponible ou non (§8)."""
    if _model is None:
        return {"backend": "faster-whisper", "loaded": False}

    try:
        import ctranslate2

        cuda_available = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        cuda_available = None

    return {**_state, "loaded": True, "cuda_available": cuda_available}
