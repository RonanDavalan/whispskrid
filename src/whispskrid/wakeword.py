"""Guetteur de mots-clés vocaux — moteur `openwakeword` (D9).

PHASE_EXECUTION, session D du chantier « Modes de déclenchement étendus »
(_CADRE/SPECIFICATIONS/CONCEPTION_WHISPSKRID.md, décision D9). Module isolé,
jamais importé par hotkey.py ni session.py tant que `hotkeys.mode: armed`
n'est pas actif : aucune dépendance à `openwakeword` chargée sinon — même
principe que `backend/__init__.py` pour `faster-whisper` (§4.4).

Interface étroite à quatre fonctions (état de module, comme `backend/`) :
`load()` charge les deux modèles de phrase (ouverture/clôture) d'une langue,
`feed()` pousse un bloc d'audio brut et renvoie la phrase détectée ou None,
`reset()` efface le tampon glissant interne entre deux segments, `unload()`
libère tout. Un seul guetteur par processus : la session résidente n'arme
qu'une langue à la fois (§7, -l/--lang).

Convention de nommage des modèles, un couple par langue supportée
(fr/en/de/es, D9) : `<lang>_open.onnx` (phrase d'ouverture de segment) et
`<lang>_close.onnx` (phrase de clôture). Aucun de ces huit fichiers n'est
fourni par `openwakeword` (aucun modèle pré-entraîné fr/de/es n'existe, D9
« écarté ») — leur entraînement réel est un chantier séparé, non couvert ici
(voir 10_ROADMAP.md, « Modes de déclenchement étendus »).

API `openwakeword` 0.4.0 vérifiée directement sur le paquet (`Model.__init__`
attend `wakeword_model_paths`, dérive le nom de chaque modèle du nom de
fichier sans son extension `.onnx`, expose `.predict(x)` -> dict {nom: score}
et `.reset()`) — pas supposée depuis la documentation en ligne.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

_model = None
_state: dict = {}

_PHRASES = ("open", "close")

# Vocabulaire de déclenchement figé par D9 (CONCEPTION_WHISPSKRID.md) : une
# phrase à deux mots par langue, jamais un mot isolé (réduit le risque de
# faux positif face à un mot courant qui apparaîtrait par hasard dans une
# conversation). Purement déclaratif ici — sert à informer l'utilisateur
# (cli.py, bannière du mode armé) de la phrase à prononcer pour sa langue ;
# aucun rapport avec le contenu réel des modèles ONNX (leur entraînement est
# un chantier séparé, voir docstring de module).
PHRASES_PAR_LANGUE: dict[str, dict[str, str]] = {
    "fr": {"open": "active dictée", "close": "stop dictée"},
    "en": {"open": "start dictation", "close": "stop dictation"},
    "de": {"open": "diktat starten", "close": "diktat stoppen"},
    "es": {"open": "iniciar dictado", "close": "terminar dictado"},
}


def resolve_wakeword_models_dir() -> Path:
    """Dossier des modèles ONNX de phrase — même cascade que
    `models.resolve_models_dir()` (§5.1 CONCEPTION_WHISPSKRID.md), transposée
    au wakeword avec son propre dossier dédié : surcharge explicite, dossier
    utilisateur, dossier système (paquet), dossier des sources (clone Git) —
    le premier qui existe et contient au moins un fichier gagne ; à défaut le
    dossier utilisateur est créé et renvoyé."""
    override = os.environ.get("WHISPSKRID_WAKEWORD_MODELS_DIR")
    if override:
        return Path(override)

    user_dir = Path.home() / ".local/share/whispskrid/wakeword-models"
    system_dir = Path("/usr/share/whispskrid/wakeword-models")
    # wakeword.py -> whispskrid/ (package) -> src/ -> racine du dépôt de code
    source_dir = Path(__file__).resolve().parents[2] / "wakeword-models"

    for candidate in (user_dir, system_dir, source_dir):
        if candidate.is_dir() and any(candidate.iterdir()):
            return candidate

    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _model_paths(language: str, models_dir: Path) -> dict[str, Path]:
    return {phrase: models_dir / f"{language}_{phrase}.onnx" for phrase in _PHRASES}


def load(language: str, models_dir: Path | str | None = None, threshold: float = 0.5) -> None:
    """Charge les deux modèles de phrase (ouverture/clôture) de `language`.

    Lève `RuntimeError` si `openwakeword` n'est pas installé, ou si l'un des
    deux fichiers attendus est absent dans `models_dir` (par défaut
    `resolve_wakeword_models_dir()`) — l'entraînement réel des phrases D9 est
    un chantier séparé (10_ROADMAP.md), ce guetteur ne fabrique aucun modèle
    de secours et ne tente aucun repli silencieux."""
    global _model, _state

    resolved_dir = Path(models_dir) if models_dir is not None else resolve_wakeword_models_dir()
    paths = _model_paths(language, resolved_dir)
    missing = [str(p) for p in paths.values() if not p.is_file()]
    if missing:
        raise RuntimeError(
            f"modèles de phrase wakeword introuvables pour la langue « {language} » "
            f"dans {resolved_dir} : {', '.join(missing)} — entraînement réel non "
            "encore fait (D9, voir 10_ROADMAP.md « Modes de déclenchement étendus »)."
        )

    try:
        from openwakeword.model import Model
    except ImportError as exc:
        raise RuntimeError(
            "openwakeword introuvable dans l'environnement Python courant — "
            "vérifier l'installation (pip install openwakeword==0.4.0)."
        ) from exc

    model_paths = [str(paths[phrase]) for phrase in _PHRASES]
    _model = Model(wakeword_model_paths=model_paths)

    # openwakeword dérive le nom de chaque modèle chargé du nom de fichier
    # sans son extension `.onnx` (vérifié sur le code du paquet) : reconstruit
    # la correspondance inverse phrase logique -> nom de modèle une fois pour
    # toutes, plutôt que de la recalculer à chaque bloc audio dans feed().
    _state = {
        "language": language,
        "models_dir": str(resolved_dir),
        "threshold": threshold,
        "name_to_phrase": {paths[phrase].stem: phrase for phrase in _PHRASES},
    }


def feed(chunk: np.ndarray) -> str | None:
    """Pousse un bloc d'audio mono 16 kHz, renvoie « open », « close » ou
    None. `chunk` : entiers 16 bits signés (format natif attendu par
    `openwakeword.Model.predict()`), pas le flottant normalisé produit par
    `audio.capture_episode()` — l'appelant lit le flux PyAudio brut.

    Lève `RuntimeError` si appelé avant `load()`."""
    if _model is None:
        raise RuntimeError("wakeword non chargé : appeler load() avant feed()")

    scores = _model.predict(chunk)
    threshold = _state.get("threshold", 0.5)
    name_to_phrase = _state.get("name_to_phrase", {})
    for model_name, score in scores.items():
        if score >= threshold:
            phrase = name_to_phrase.get(model_name)
            if phrase is not None:
                return phrase
    return None


def reset() -> None:
    """Réinitialise le tampon glissant interne d'`openwakeword` entre deux
    segments — appelé à chaque retour à armé-attente pour qu'un score
    résiduel de la phrase de clôture ne redéclenche pas immédiatement une
    détection de la phrase d'ouverture."""
    if _model is not None:
        _model.reset()


def unload() -> None:
    """Libère l'état chargé — appelé au désarmement (D9 : aucune dépendance à
    `openwakeword` chargée hors du mode armé) et par les tests."""
    global _model, _state
    _model = None
    _state = {}


def info() -> dict:
    """Dictionnaire lisible par un futur --diagnose (§8) : langue chargée,
    dossier de modèles, seuil effectif — sur le modèle de `backend.info()`."""
    if _model is None:
        return {"loaded": False}
    return {"loaded": True, **{k: v for k, v in _state.items() if k != "name_to_phrase"}}
