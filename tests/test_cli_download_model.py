# cli._run_download_model() (§5.2 CONCEPTION_WHISPSKRID.md) : implémentation
# réelle de --download-model, remplaçant le stub qui répondait « pas encore
# implémenté ». Identité : ces tests exercent la
# validation du nom et le report des issues de models.download_model(), pas
# la traduction (déjà couverte par test_i18n.py) — _() n'a rien à faire ici
# que renvoyer sa chaîne telle quelle.

from __future__ import annotations

from whispskrid import cli

_NOOP = lambda s: s  # noqa: E731


def test_unknown_model_name_rejected_without_calling_download(monkeypatch, capsys):
    appele = []
    monkeypatch.setattr(
        "whispskrid.models.download_model", lambda name: appele.append(name)
    )

    code = cli._run_download_model("nom-inconnu", _NOOP)

    assert code == 1
    assert appele == []
    assert "nom-inconnu" in capsys.readouterr().err


def test_known_model_downloads_and_reports_path(monkeypatch, capsys):
    from pathlib import Path

    monkeypatch.setattr("whispskrid.models.model_cached", lambda name, models_dir: False)
    monkeypatch.setattr(
        "whispskrid.models.download_model", lambda name: Path("/tmp/modeles")
    )

    code = cli._run_download_model("base", _NOOP)

    assert code == 0
    assert "/tmp/modeles" in capsys.readouterr().out


def test_already_cached_model_shortcuts_without_downloading(monkeypatch, capsys):
    appele = []
    monkeypatch.setattr("whispskrid.models.model_cached", lambda name, models_dir: True)
    monkeypatch.setattr(
        "whispskrid.models.download_model", lambda name: appele.append(name)
    )

    code = cli._run_download_model("base", _NOOP)

    assert code == 0
    assert appele == []
    assert "déjà présent" in capsys.readouterr().out


def test_download_failure_reported_and_returns_nonzero(monkeypatch, capsys):
    def _boom(name):
        raise RuntimeError("réseau indisponible")

    monkeypatch.setattr("whispskrid.models.model_cached", lambda name, models_dir: False)
    monkeypatch.setattr("whispskrid.models.download_model", _boom)

    code = cli._run_download_model("base", _NOOP)

    assert code == 1
    assert "réseau indisponible" in capsys.readouterr().err
