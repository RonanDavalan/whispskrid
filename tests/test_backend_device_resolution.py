# _resolve_device() (backend/__init__.py, CONCEPTION_WHISPSKRID.md §4.4) :
# ne transmet jamais "auto" tel quel à CTranslate2, sonde libcublas.so.12
# par dlopen avant tout appel WhisperModel, pour éviter un échec tardif au
# premier transcribe().

from __future__ import annotations

from whispskrid import backend


def test_cpu_requested_short_circuits_probing(monkeypatch):
    # cpu explicite ne doit jamais sonder le GPU ni cublas.
    called = []
    monkeypatch.setattr(backend, "_gpu_detected", lambda: called.append("gpu") or True)
    monkeypatch.setattr(backend, "_cublas_loadable", lambda: called.append("cublas") or True)

    assert backend._resolve_device("cpu") == "cpu"
    assert called == []


def test_auto_with_gpu_and_cublas_present_resolves_cuda(monkeypatch):
    monkeypatch.setattr(backend, "_gpu_detected", lambda: True)
    monkeypatch.setattr(backend, "_cublas_loadable", lambda: True)

    assert backend._resolve_device("auto") == "cuda"


def test_auto_with_gpu_but_cublas_missing_falls_back_to_cpu_silently(monkeypatch, capsys):
    monkeypatch.setattr(backend, "_gpu_detected", lambda: True)
    monkeypatch.setattr(backend, "_cublas_loadable", lambda: False)

    resolved = backend._resolve_device("auto")

    assert resolved == "cpu"
    # "silencieux" = pas d'exception, mais un avertissement journalisé sur
    # stderr (§4.4) : la différence avec un échec muet est observable.
    assert "libcublas.so.12" in capsys.readouterr().err


def test_auto_without_gpu_resolves_cpu(monkeypatch):
    monkeypatch.setattr(backend, "_gpu_detected", lambda: False)

    assert backend._resolve_device("auto") == "cpu"


def test_cuda_explicit_with_cublas_present_resolves_cuda(monkeypatch):
    monkeypatch.setattr(backend, "_gpu_detected", lambda: True)
    monkeypatch.setattr(backend, "_cublas_loadable", lambda: True)

    assert backend._resolve_device("cuda") == "cuda"


def test_cuda_explicit_with_cublas_missing_raises_with_remedy(monkeypatch):
    monkeypatch.setattr(backend, "_gpu_detected", lambda: True)
    monkeypatch.setattr(backend, "_cublas_loadable", lambda: False)

    try:
        backend._resolve_device("cuda")
        assert False, "RuntimeError attendue"
    except RuntimeError as exc:
        assert backend._CUBLAS_REMEDY in str(exc)


def test_cuda_explicit_without_gpu_raises_with_remedy(monkeypatch):
    monkeypatch.setattr(backend, "_gpu_detected", lambda: False)

    try:
        backend._resolve_device("cuda")
        assert False, "RuntimeError attendue"
    except RuntimeError as exc:
        assert "aucun GPU détecté" in str(exc)
