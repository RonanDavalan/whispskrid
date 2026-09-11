"""Adaptateur de backend de reconnaissance vocale.

Interface étroite à trois fonctions, pour qu'un second backend
(whisper.cpp) puisse être ajouté plus tard sans toucher au reste du projet.
Voir _CADRE/SPECIFICATIONS/CONCEPTION_WHISPSKRID.md §4.

Squelette de la tranche 1 (PHASE_EXECUTION) : l'implémentation
faster-whisper (chargement du modèle, transcription réelle) arrive dans une
tranche suivante.
"""

from __future__ import annotations


def load() -> None:
    """Charge le modèle en mémoire. Appelé une fois au démarrage de la
    session résidente. Lève une exception claire si le modèle est absent ou
    si l'import CTranslate2 échoue."""
    raise NotImplementedError


def transcribe(audio, language: str | None) -> str:
    """Transcrit un tampon audio mono 16 kHz float32. `language` est un code
    (« fr », « en »…) ou None pour autodétection. Retourne le texte brut,
    sans post-traitement."""
    raise NotImplementedError


def info() -> dict:
    """Dictionnaire lisible par --diagnose : nom du backend, chemin du
    modèle, device, compute_type, CUDA disponible ou non."""
    raise NotImplementedError
