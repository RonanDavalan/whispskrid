# Guetteur de mots-clés vocaux (wakeword.py, D9) : module isolé, jamais
# mélangé à hotkey.py/session.py (session D du chantier « Modes de
# déclenchement étendus »). `openwakeword` n'est jamais réellement importé
# ici — doublure du module `openwakeword.model`, sur le modèle de
# test_models.py pour `huggingface_hub`/`faster_whisper`.

from __future__ import annotations

import sys

import numpy as np
import pytest

from whispskrid import wakeword


@pytest.fixture(autouse=True)
def _unload_after_each_test():
    yield
    wakeword.unload()


def _write_dummy_models(tmp_path, language: str) -> None:
    (tmp_path / f"{language}_open.onnx").write_bytes(b"")
    (tmp_path / f"{language}_close.onnx").write_bytes(b"")


class _FakeModel:
    """Doublure de `openwakeword.model.Model` : mémorise les chemins reçus,
    renvoie des scores fixés par le test via `_FakeModel.scores`."""

    scores: dict[str, float] = {}
    reset_calls = 0

    def __init__(self, wakeword_model_paths):
        self.wakeword_model_paths = wakeword_model_paths

    def predict(self, x):
        return dict(_FakeModel.scores)

    def reset(self):
        _FakeModel.reset_calls += 1


def _install_fake_openwakeword(monkeypatch):
    fake_module = type(sys)("openwakeword.model")
    fake_module.Model = _FakeModel
    monkeypatch.setitem(sys.modules, "openwakeword.model", fake_module)
    _FakeModel.scores = {}
    _FakeModel.reset_calls = 0


def test_resolve_wakeword_models_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("WHISPSKRID_WAKEWORD_MODELS_DIR", str(tmp_path))

    assert wakeword.resolve_wakeword_models_dir() == tmp_path


def test_load_raises_clear_error_when_models_missing(tmp_path):
    with pytest.raises(RuntimeError) as exc_info:
        wakeword.load("fr", models_dir=tmp_path)

    message = str(exc_info.value)
    assert "fr_open.onnx" in message
    assert "fr_close.onnx" in message


def test_load_raises_clear_error_when_openwakeword_absent(tmp_path, monkeypatch):
    """Un `sys.modules[nom] = None` fait lever `ImportError` à l'import quelle
    que soit la présence réelle du paquet sur la machine qui exécute le test
    (contrairement à un simple retrait du cache d'import) — nécessaire ici
    puisque openwakeword est réellement installé dans ce venv de
    développement pour le test d'intégration plomberie contre l'API réelle."""
    _write_dummy_models(tmp_path, "fr")
    monkeypatch.setitem(sys.modules, "openwakeword", None)
    monkeypatch.setitem(sys.modules, "openwakeword.model", None)

    with pytest.raises(RuntimeError) as exc_info:
        wakeword.load("fr", models_dir=tmp_path)

    assert "openwakeword" in str(exc_info.value)


def test_feed_before_load_raises(tmp_path):
    with pytest.raises(RuntimeError):
        wakeword.feed(np.zeros(1280, dtype=np.int16))


def test_load_then_feed_detects_open_phrase(tmp_path, monkeypatch):
    _write_dummy_models(tmp_path, "fr")
    _install_fake_openwakeword(monkeypatch)

    wakeword.load("fr", models_dir=tmp_path, threshold=0.5)
    _FakeModel.scores = {"fr_open": 0.9, "fr_close": 0.01}

    assert wakeword.feed(np.zeros(1280, dtype=np.int16)) == "open"


def test_feed_detects_close_phrase(tmp_path, monkeypatch):
    _write_dummy_models(tmp_path, "fr")
    _install_fake_openwakeword(monkeypatch)

    wakeword.load("fr", models_dir=tmp_path)
    _FakeModel.scores = {"fr_open": 0.02, "fr_close": 0.8}

    assert wakeword.feed(np.zeros(1280, dtype=np.int16)) == "close"


def test_feed_returns_none_below_threshold(tmp_path, monkeypatch):
    _write_dummy_models(tmp_path, "fr")
    _install_fake_openwakeword(monkeypatch)

    wakeword.load("fr", models_dir=tmp_path, threshold=0.5)
    _FakeModel.scores = {"fr_open": 0.49, "fr_close": 0.0}

    assert wakeword.feed(np.zeros(1280, dtype=np.int16)) is None


def test_reset_delegates_to_model(tmp_path, monkeypatch):
    _write_dummy_models(tmp_path, "fr")
    _install_fake_openwakeword(monkeypatch)
    wakeword.load("fr", models_dir=tmp_path)

    wakeword.reset()

    assert _FakeModel.reset_calls == 1


def test_reset_before_load_is_a_noop():
    wakeword.reset()  # ne doit pas lever


def test_unload_clears_state(tmp_path, monkeypatch):
    _write_dummy_models(tmp_path, "fr")
    _install_fake_openwakeword(monkeypatch)
    wakeword.load("fr", models_dir=tmp_path)

    wakeword.unload()

    assert wakeword.info() == {"loaded": False}
    with pytest.raises(RuntimeError):
        wakeword.feed(np.zeros(1280, dtype=np.int16))


def test_info_reports_language_and_threshold(tmp_path, monkeypatch):
    _write_dummy_models(tmp_path, "fr")
    _install_fake_openwakeword(monkeypatch)

    wakeword.load("fr", models_dir=tmp_path, threshold=0.42)

    info = wakeword.info()
    assert info["loaded"] is True
    assert info["language"] == "fr"
    assert info["threshold"] == 0.42
    assert info["models_dir"] == str(tmp_path)
