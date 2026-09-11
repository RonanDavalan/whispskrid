"""Capture audio pendant l'appui — appui-pour-parler strict.

PHASE_EXECUTION, tranche 3. Voir
_CADRE/SPECIFICATIONS/CONCEPTION_WHISPSKRID.md §2.1-2.2 : la capture démarre à
l'appui, s'accumule tant que la touche est tenue, s'arrête à la relâche (ou au
garde-fou `capture.max_seconds`), et part en une seule passe vers l'adaptateur
de backend — pas de flux ni de VAD, contrairement au moule vosk-cli-dictation
(cœur d'interaction en continu, hors périmètre ici).

Le périphérique est ouvert une fois par `open_stream()` au démarrage de la
session résidente (§3.1) et reste ouvert entre les dictées ; `capture_episode()`
lit dessus le temps d'un seul épisode d'appui.
"""

from __future__ import annotations

import contextlib
import os
from typing import Callable

import numpy as np
import pyaudio


@contextlib.contextmanager
def _sans_bruit_alsa_jack():
    """Coupe le fd 2 pendant l'initialisation PyAudio.

    `PyAudio()` charge PortAudio, qui sonde tous les backends disponibles
    (ALSA, JACK...) et leurs bibliothèques C écrivent directement sur le
    descripteur de fichier stderr (pas sur `sys.stderr` : un `redirect_stderr`
    Python ne les intercepte pas). Ce sondage produit un bruit non pertinent
    (« ALSA lib pcm.c:... », « Cannot connect to server socket » JACK) sur une
    machine sans ces serveurs actifs, sans rapport avec un échec réel (relevé
    testeur `ada`, 12/09/2026) : le flux s'ouvre correctement malgré ce bruit.
    """
    stderr_fd = 2
    saved_fd = os.dup(stderr_fd)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull_fd, stderr_fd)
        yield
    finally:
        os.dup2(saved_fd, stderr_fd)
        os.close(devnull_fd)
        os.close(saved_fd)


def open_stream(cfg: dict) -> tuple[pyaudio.PyAudio, pyaudio.Stream]:
    """Ouvre le périphérique de capture au format attendu (§6 audio.*).

    Lève l'exception PyAudio telle quelle si aucun périphérique d'entrée
    n'est disponible — à l'appelant (session résidente, --diagnose) de la
    traduire en message clair.
    """
    audio_cfg = cfg.get("audio", {})
    with _sans_bruit_alsa_jack():
        p = pyaudio.PyAudio()
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=audio_cfg.get("channels", 1),
                rate=audio_cfg.get("sample_rate", 16000),
                input=True,
                frames_per_buffer=audio_cfg.get("frames_per_buffer", 4096),
            )
        except Exception:
            p.terminate()
            raise
    return p, stream


def close_stream(p: pyaudio.PyAudio, stream: pyaudio.Stream) -> None:
    """Ferme proprement le flux et le périphérique. À appeler une fois, à
    l'arrêt de la session résidente (`quit`)."""
    try:
        if stream.is_active():
            stream.stop_stream()
        stream.close()
    except Exception:
        pass
    p.terminate()


def _drain_stale_backlog(stream: pyaudio.Stream) -> None:
    """Purge l'audio bufférisé par PortAudio pendant l'inactivité.

    Le flux reste ouvert en continu entre les dictées (voir docstring de
    module) mais n'est lu par personne tant qu'aucune capture n'est en
    cours : le tampon interne continue de se remplir en silence. Défaut
    trouvé en session de validation le 11/09/2026 : jusqu'à ~0,77 s d'audio
    périmé (mesuré empiriquement, capacité fixe du tampon PortAudio, quelle
    que soit la durée d'inactivité) se retrouvait en tête de chaque nouvelle
    capture — assez pour faire dériver un petit modèle Whisper vers une
    hallucination complète, avec une dégradation qui s'aggrave à mesure que
    les cycles s'enchaînent dans une même session résidente. Sans effet sur
    une capture qui démarre juste après l'ouverture du flux (rien à purger).
    """
    try:
        avail = stream.get_read_available()
        while avail > 0:
            stream.read(avail, exception_on_overflow=False)
            avail = stream.get_read_available()
    except OSError:
        pass


def capture_episode(
    stream: pyaudio.Stream,
    cfg: dict,
    is_active: Callable[[], bool],
    on_max_seconds: Callable[[], None] | None = None,
) -> np.ndarray:
    """Accumule l'audio tant que `is_active()` rend vrai (touche tenue), et au
    plus `capture.max_seconds` (§2.2, garde-fou contre une touche bloquée).

    Retourne un tableau mono float32 normalisé dans [-1, 1], au format attendu
    par `backend.transcribe(audio, language)` (§4.1). Tableau vide si aucune
    trame n'a été capturée (relâche immédiate).
    """
    audio_cfg = cfg.get("audio", {})
    sample_rate = audio_cfg.get("sample_rate", 16000)
    frames_per_buffer = audio_cfg.get("frames_per_buffer", 4096)
    max_seconds = cfg.get("capture", {}).get("max_seconds", 300)
    max_frames = int(max_seconds * sample_rate)

    _drain_stale_backlog(stream)

    chunks: list[bytes] = []
    total_frames = 0

    while is_active() and total_frames < max_frames:
        try:
            data = stream.read(frames_per_buffer, exception_on_overflow=False)
        except OSError:
            break
        chunks.append(data)
        total_frames += frames_per_buffer

    if total_frames >= max_frames and on_max_seconds is not None:
        on_max_seconds()

    if not chunks:
        return np.zeros(0, dtype=np.float32)

    raw = b"".join(chunks)
    audio_int16 = np.frombuffer(raw, dtype=np.int16)
    return audio_int16.astype(np.float32) / 32768.0
