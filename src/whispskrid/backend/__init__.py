"""Adaptateur de backend de reconnaissance vocale.

Interface étroite à trois fonctions, pour qu'un second backend
(whisper.cpp) puisse être ajouté plus tard sans toucher au reste du projet.
Seule implémentation livrée en v1.0.1 : `faster-whisper`.

État chargé (modèle, paramètres effectifs) gardé au niveau du module : une
session persistante n'appelle `load()` qu'une fois, tout le reste du
processus partage le même état.
"""

from __future__ import annotations

import sys

_model = None
_state: dict = {}

_CUBLAS_SONAME = "libcublas.so.12"
_CUBLAS_REMEDY = "apt install libcublas12 libcublaslt12"


def _gpu_detected() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def _cublas_loadable() -> bool:
    """Sonde directe de `libcublas.so.12`, indépendante de la résolution
    interne de CTranslate2 : CTranslate2 ne
    vérifie que la présence d'un GPU pour `device="auto"`, pas le chargement
    réel de cette lib, qui n'est fait par `dlopen` qu'au premier
    `transcribe()` — d'où un échec tardif si elle manque."""
    import ctypes

    try:
        ctypes.CDLL(_CUBLAS_SONAME)
        return True
    except OSError:
        return False


def _resolve_device(requested: str) -> str:
    """Résout `device` avant l'appel à `WhisperModel`. Ne
    transmet jamais `"auto"` tel quel à CTranslate2."""
    if requested == "cpu":
        return "cpu"

    gpu_present = _gpu_detected()

    if requested == "cuda":
        if gpu_present and _cublas_loadable():
            return "cuda"
        raise RuntimeError(
            f"device: cuda demandé explicitement, mais {_CUBLAS_SONAME} est "
            f"introuvable ({'GPU détecté' if gpu_present else 'aucun GPU détecté'}) "
            f"— installer la bibliothèque CUDA requise ({_CUBLAS_REMEDY} sur "
            "Debian/Ubuntu) ou passer device: cpu."
        )

    # requested == "auto"
    if gpu_present and not _cublas_loadable():
        print(
            f"whispskrid : GPU détecté mais {_CUBLAS_SONAME} introuvable — "
            f"repli sur device: cpu ({_CUBLAS_REMEDY} pour activer le GPU).",
            file=sys.stderr,
        )
        return "cpu"
    return "cuda" if gpu_present else "cpu"


def load(
    model_name: str = "base",
    device: str = "auto",
    compute_type: str = "auto",
    beam_size: int = 5,
) -> None:
    """Charge le modèle en mémoire. Appelé une fois au démarrage de la
    session persistante. Lève une exception claire si le modèle est absent, si
    l'import CTranslate2 échoue, ou si `device: cuda` est demandé
    explicitement sans que CUDA soit réellement utilisable."""
    global _model, _state

    from whispskrid.models import resolve_models_dir

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # import CTranslate2/faster-whisper absent
        raise RuntimeError(
            "faster-whisper ou CTranslate2 introuvable dans l'environnement "
            "Python courant — vérifier l'installation (pip install faster-whisper)."
        ) from exc

    resolved_device = _resolve_device(device)

    models_dir = resolve_models_dir()
    try:
        _model = WhisperModel(
            model_name,
            device=resolved_device,
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
        "device": resolved_device,
        "compute_type": compute_type,
        "beam_size": beam_size,
    }


def transcribe(audio, language: str | None) -> str:
    """Transcrit un tampon audio mono 16 kHz float32. `language` est un code
    (« fr », « en »…) ou None pour autodétection. Retourne le texte brut,
    sans post-traitement (le post-traitement est fait ailleurs)."""
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
    modèle, device, compute_type, GPU détecté et `libcublas.so.12`
    chargeable ou non."""
    if _model is None:
        return {"backend": "faster-whisper", "loaded": False}

    gpu_detected = _gpu_detected()
    return {
        **_state,
        "loaded": True,
        "cuda_available": gpu_detected,
        "cublas_loadable": _cublas_loadable() if gpu_detected else None,
    }
