# Machine d'état de Session (session.py) : distinction ERR <message> / OK
# <texte> / OK (vide) / OK cancelled — corrige exactement le symptôme
# remonté par Ronan (« --dictate-stop qui ne retourne aucun texte »), voir
# _CADRE/MEMOIRE/ADDENDUM_2026-09-11_correctif-libcublas-cuda12.md. La
# capture audio et le backend Whisper sont doublés : ces tests exercent la
# machine d'état, pas le matériel réel.

from __future__ import annotations

import time

import numpy as np
import pytest

from whispskrid import session as session_module
from whispskrid.session import Session


def _cfg(**post_processing_overrides):
    pp = {"trim": True, "capitalize_sentence_start": True}
    pp.update(post_processing_overrides)
    return {"post_processing": pp}


@pytest.fixture(autouse=True)
def _no_real_capture_or_injection(monkeypatch):
    """Par défaut : capture d'un tampon non vide, transcription fixe, aucune
    frappe réelle. Chaque test surcharge ce qui l'intéresse."""
    monkeypatch.setattr(
        session_module.audio, "capture_episode",
        lambda *a, **k: np.ones(1600, dtype=np.float32),
    )
    monkeypatch.setattr(session_module.backend, "transcribe", lambda audio, lang: "bonjour")
    monkeypatch.setattr(session_module.injection, "type_text", lambda text: True)
    monkeypatch.setattr(session_module.injection, "play_sound", lambda: None)


def _run_dictate_cycle(sess: Session) -> tuple[bool, str]:
    sess.start_capture()
    # _run_capture tourne dans un fil séparé ; stop_capture_and_inject()
    # attend _finished_event, donc ce test n'a pas besoin de polling manuel.
    return sess.stop_capture_and_inject()


def test_normal_cycle_returns_ok_with_transcribed_text():
    sess = Session({**_cfg()}, "base", None)

    ok, reply = _run_dictate_cycle(sess)

    assert ok
    assert reply == "OK Bonjour"  # capitalize_sentence_start par défaut
    assert sess.status() == "state=idle model=base language=auto"


def test_injection_is_called_with_post_processed_text(monkeypatch):
    calls = []
    monkeypatch.setattr(session_module.injection, "type_text", lambda text: calls.append(text) or True)
    sess = Session(_cfg(), "base", None)

    _run_dictate_cycle(sess)

    assert calls == ["Bonjour"]


def test_trim_disabled_keeps_raw_whitespace(monkeypatch):
    monkeypatch.setattr(session_module.backend, "transcribe", lambda audio, lang: "  bonjour  ")
    sess = Session(_cfg(trim=False, capitalize_sentence_start=False), "base", None)

    ok, reply = _run_dictate_cycle(sess)

    assert reply == "OK   bonjour  "


def test_empty_capture_returns_ok_without_text_and_skips_injection(monkeypatch):
    monkeypatch.setattr(session_module.audio, "capture_episode", lambda *a, **k: np.zeros(0, dtype=np.float32))
    calls = []
    monkeypatch.setattr(session_module.injection, "type_text", lambda text: calls.append(text) or True)
    sess = Session(_cfg(), "base", None)

    ok, reply = _run_dictate_cycle(sess)

    assert ok
    assert reply == "OK"  # jamais "OK <rien>" — la distinction vide/échec est le point de la loi
    assert calls == []


def test_transcription_failure_returns_err_not_silent_ok(monkeypatch):
    def _boom(audio, lang):
        raise RuntimeError("modèle indisponible")

    monkeypatch.setattr(session_module.backend, "transcribe", _boom)
    sess = Session(_cfg(), "base", None)

    ok, reply = _run_dictate_cycle(sess)

    assert not ok
    assert reply == "ERR modèle indisponible"
    # l'état revient à idle malgré l'échec : jamais bloqué en "capturing".
    assert sess.status() == "state=idle model=base language=auto"


def test_cancel_discards_capture_without_injecting(monkeypatch):
    calls = []
    monkeypatch.setattr(session_module.injection, "type_text", lambda text: calls.append(text) or True)
    sess = Session(_cfg(), "base", None)

    sess.start_capture()
    ok, reply = sess.cancel()

    assert ok
    assert reply == "OK"
    assert calls == []
    assert sess.status() == "state=idle model=base language=auto"


def test_start_capture_while_already_capturing_is_rejected(monkeypatch):
    # capture_episode qui ne rend jamais la main tant qu'on ne le débloque pas,
    # pour garder l'état "capturing" le temps du test.
    released = session_module.threading.Event()
    monkeypatch.setattr(
        session_module.audio, "capture_episode",
        lambda *a, **k: (released.wait(timeout=2), np.ones(1600, dtype=np.float32))[1],
    )
    sess = Session(_cfg(), "base", None)
    sess.start_capture()

    ok, reply = sess.start_capture()

    assert not ok
    assert reply == "ERR already-capturing"
    released.set()


def test_stop_while_idle_is_rejected():
    sess = Session(_cfg(), "base", None)

    ok, reply = sess.stop_capture_and_inject()

    assert not ok
    assert reply == "ERR not-capturing"
