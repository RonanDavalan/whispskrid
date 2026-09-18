# models.download_model()/model_cached()  :
# implémentation réelle de --download-model, corrigeant le stub qui répondait
# « pas encore implémenté » (le stub ne proposait aucun service
# d'installation de modèle). Le réseau n'est jamais sollicité ici :
# huggingface_hub.snapshot_download et faster_whisper.WhisperModel sont
# remplacés par des doublures.

from __future__ import annotations

from whispskrid import models


def test_model_cached_true_when_hf_cache_folder_present(tmp_path):
    repo_id, _taille = models.MODEL_CATALOG["base"]
    (tmp_path / f"models--{repo_id.replace('/', '--')}").mkdir()

    assert models.model_cached("base", tmp_path) is True


def test_model_cached_false_when_absent(tmp_path):
    assert models.model_cached("base", tmp_path) is False


def test_model_cached_false_for_unknown_name(tmp_path):
    assert models.model_cached("nom-inconnu", tmp_path) is False


def test_download_model_rejects_unknown_name():
    try:
        models.download_model("nom-inconnu")
        assert False, "ValueError attendue"
    except ValueError:
        pass


def test_download_model_downloads_then_verifies_load(monkeypatch, tmp_path):
    monkeypatch.setattr(models, "resolve_models_dir", lambda: tmp_path)

    appels = {}

    def _snapshot_download(repo_id, cache_dir, allow_patterns):
        appels["repo_id"] = repo_id
        appels["cache_dir"] = cache_dir
        appels["allow_patterns"] = allow_patterns

    class _FakeHfHub:
        snapshot_download = staticmethod(_snapshot_download)

    monkeypatch.setitem(__import__("sys").modules, "huggingface_hub", _FakeHfHub)

    charges = []

    class _FakeWhisperModel:
        def __init__(self, name, device, compute_type, download_root):
            charges.append((name, device, compute_type, download_root))

    class _FakeFasterWhisper:
        WhisperModel = _FakeWhisperModel

    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", _FakeFasterWhisper)

    chemin = models.download_model("base")

    assert chemin == tmp_path
    assert appels["repo_id"] == "Systran/faster-whisper-base"
    assert appels["cache_dir"] == str(tmp_path)
    assert charges == [("base", "cpu", "int8", str(tmp_path))]


def test_download_model_wraps_download_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(models, "resolve_models_dir", lambda: tmp_path)

    class _FakeHfHub:
        @staticmethod
        def snapshot_download(*a, **k):
            raise OSError("réseau indisponible")

    monkeypatch.setitem(__import__("sys").modules, "huggingface_hub", _FakeHfHub)

    try:
        models.download_model("base")
        assert False, "RuntimeError attendue"
    except RuntimeError as exc:
        assert "réseau indisponible" in str(exc)


def test_download_model_wraps_verification_load_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(models, "resolve_models_dir", lambda: tmp_path)

    class _FakeHfHub:
        @staticmethod
        def snapshot_download(*a, **k):
            return None

    monkeypatch.setitem(__import__("sys").modules, "huggingface_hub", _FakeHfHub)

    class _FakeWhisperModel:
        def __init__(self, *a, **k):
            raise RuntimeError("modèle corrompu")

    class _FakeFasterWhisper:
        WhisperModel = _FakeWhisperModel

    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", _FakeFasterWhisper)

    try:
        models.download_model("base")
        assert False, "RuntimeError attendue"
    except RuntimeError as exc:
        assert "chargement de vérification" in str(exc)
