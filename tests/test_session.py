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
    # capture.max_seconds très haut : les tests du mode armé lisent une
    # doublure de flux sans aucun rythme temps réel (voir _FakeStream plus
    # bas) — au débit d'itération réel d'un test, la valeur par défaut (300 s)
    # serait franchie en une fraction de seconde et déclencherait le
    # garde-fou avant que le test n'ait eu la main pour désarmer lui-même.
    return {"post_processing": pp, "capture": {"max_seconds": 1_000_000}}


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


# --------------------------------------------------------------------- #
# Mode armé (D9) — fil unique _run_armed_listener, seul lecteur du flux  #
# tant qu'armé (voir docstring de module : écart assumé à la lettre de   #
# D9 pour éviter deux lecteurs concurrents sur le même flux PyAudio).    #
# --------------------------------------------------------------------- #

class _FakeStream:
    """Flux micro doublé : `read()` renvoie du silence de la bonne taille,
    sans jamais bloquer ni lever — la détection est pilotée par la doublure
    de `wakeword.feed`, pas par le contenu de ce flux."""

    def read(self, n, exception_on_overflow=False):
        return b"\x00\x00" * n

    def get_read_available(self):
        return 0


def _fake_wakeword(monkeypatch, feed=lambda chunk: None, load=None):
    monkeypatch.setattr(session_module.wakeword, "load", load or (lambda *a, **k: None))
    monkeypatch.setattr(session_module.wakeword, "feed", feed)
    monkeypatch.setattr(session_module.wakeword, "reset", lambda: None)
    monkeypatch.setattr(session_module.wakeword, "unload", lambda: None)


def _wait_until(predicate, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_arm_then_disarm_round_trip(monkeypatch):
    _fake_wakeword(monkeypatch)
    sess = Session(_cfg(), "base", "fr")
    sess._stream = _FakeStream()

    ok, msg = sess.arm()
    assert ok and msg == "OK"
    assert sess.is_armed()
    assert _wait_until(lambda: sess.status() == "state=idle model=base language=fr armed=waiting")

    ok, msg = sess.disarm()
    assert ok and msg == "OK"
    assert not sess.is_armed()
    assert sess.status() == "state=idle model=base language=fr"


def test_arm_defaults_to_french_when_no_language(monkeypatch):
    captured = {}

    def fake_load(language, models_dir=None, threshold=0.5):
        captured["language"] = language

    _fake_wakeword(monkeypatch, load=fake_load)
    sess = Session(_cfg(), "base", None)
    sess._stream = _FakeStream()

    sess.arm()

    assert captured["language"] == "fr"
    sess.disarm()


def test_arm_fails_cleanly_when_wakeword_load_raises(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("modèles absents")

    _fake_wakeword(monkeypatch, load=_boom)
    sess = Session(_cfg(), "base", "fr")
    sess._stream = _FakeStream()

    ok, msg = sess.arm()

    assert not ok
    assert msg == "ERR modèles absents"
    assert not sess.is_armed()


def test_double_arm_is_rejected(monkeypatch):
    _fake_wakeword(monkeypatch)
    sess = Session(_cfg(), "base", "fr")
    sess._stream = _FakeStream()
    sess.arm()

    ok, msg = sess.arm()

    assert not ok
    assert msg == "ERR already-armed"
    sess.disarm()


def test_disarm_while_not_armed_is_rejected():
    sess = Session(_cfg(), "base", "fr")

    ok, msg = sess.disarm()

    assert not ok
    assert msg == "ERR not-armed"


def test_socket_commands_rejected_while_armed(monkeypatch):
    _fake_wakeword(monkeypatch)
    sess = Session(_cfg(), "base", "fr")
    sess._stream = _FakeStream()
    sess.arm()

    assert sess.start_capture() == (False, "ERR armed-mode-active")
    assert sess.stop_capture_and_inject() == (False, "ERR armed-mode-active")
    assert sess.cancel() == (False, "ERR armed-mode-active")
    assert sess.toggle() == (False, "ERR armed-mode-active")

    sess.disarm()


def _gated_feed(allow_close: "session_module.threading.Event", state: dict):
    """Guetteur doublé synchronisé par événement plutôt que par un décompte
    d'appels : `_FakeStream.read()` ne rythme rien (aucune latence réelle),
    donc l'état armé-segment peut ne durer qu'une poignée d'itérations —
    trop bref pour qu'un polling de `status()` l'observe de façon fiable
    (constaté : la première version de ces tests, basée sur une séquence de
    N appels, échouait par une vraie course, pas par un défaut du code —
    « close » pouvait survenir avant le premier polling de « segment »).
    Ici la phrase de clôture n'est renvoyée qu'une fois le test prêt à
    l'observer, via `allow_close.set()` : le déroulement est déterministe."""

    def fake_feed(chunk):
        if not state["opened"]:
            state["opened"] = True
            return "open"
        if allow_close.is_set() and not state.get("closed"):
            state["closed"] = True
            return "close"
        return None

    return fake_feed


def test_open_phrase_starts_segment_and_close_phrase_transcribes(monkeypatch):
    allow_close = session_module.threading.Event()
    fake_feed = _gated_feed(allow_close, {"opened": False})
    _fake_wakeword(monkeypatch, feed=fake_feed)
    sess = Session(_cfg(), "base", "fr")
    sess._stream = _FakeStream()
    sess.arm()

    assert _wait_until(lambda: sess.status().endswith("armed=segment"))

    allow_close.set()

    assert _wait_until(
        lambda: sess.status() == "state=idle model=base language=fr armed=waiting"
    )

    sess.disarm()


def test_open_phrase_plays_sound_and_close_phrase_injects_text(monkeypatch):
    allow_close = session_module.threading.Event()
    fake_feed = _gated_feed(allow_close, {"opened": False})
    _fake_wakeword(monkeypatch, feed=fake_feed)
    sound_calls = []
    monkeypatch.setattr(session_module.injection, "play_sound", lambda: sound_calls.append(1))
    injected = []
    monkeypatch.setattr(session_module.injection, "type_text", lambda text: injected.append(text) or True)

    sess = Session(_cfg(), "base", "fr")
    sess._stream = _FakeStream()
    sess.arm()

    assert _wait_until(lambda: sound_calls)

    allow_close.set()

    assert _wait_until(lambda: injected)
    assert sound_calls == [1]
    assert injected == ["Bonjour"]  # capitalize_sentence_start par défaut, backend doublé "bonjour"

    sess.disarm()


def test_disarm_during_segment_discards_without_injecting(monkeypatch):
    never_close = session_module.threading.Event()  # jamais levé : pas de "close"
    fake_feed = _gated_feed(never_close, {"opened": False})
    _fake_wakeword(monkeypatch, feed=fake_feed)
    injected = []
    monkeypatch.setattr(session_module.injection, "type_text", lambda text: injected.append(text) or True)

    sess = Session(_cfg(), "base", "fr")
    sess._stream = _FakeStream()
    sess.arm()

    assert _wait_until(lambda: sess.status().endswith("armed=segment"))

    ok, msg = sess.disarm()

    assert ok
    assert msg == "OK"
    assert injected == []
    assert sess.status() == "state=idle model=base language=fr"
