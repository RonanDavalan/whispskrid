# _client_timeout() (cli.py) : délai de réception client aligné sur
# capture.max_seconds pour dictate-stop/toggle (les deux commandes qui
# peuvent déclencher une transcription réelle) — corrige un faux échec
# observé sur un Raspberry Pi (ARM) où une transcription de ~90s dépassait
# l'ancien délai fixe de 30s : le client rapportait « aucune session en
# cours » alors que la session, elle, terminait la transcription et
# injectait quand même le texte, sans jamais recevoir cette réponse.

from __future__ import annotations

from whispskrid import cli


def test_status_uses_default_timeout():
    assert cli._client_timeout("status") is None


def test_dictate_uses_default_timeout():
    # démarrer une capture est un aller-retour rapide, pas une transcription.
    assert cli._client_timeout("dictate") is None


def test_dictate_stop_timeout_follows_capture_max_seconds(monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda: {"capture": {"max_seconds": 120}})

    assert cli._client_timeout("dictate-stop") == 120 + cli._TIMEOUT_MARGIN_S


def test_toggle_timeout_follows_capture_max_seconds(monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda: {"capture": {"max_seconds": 120}})

    assert cli._client_timeout("toggle") == 120 + cli._TIMEOUT_MARGIN_S


def test_dictate_stop_timeout_falls_back_to_default_capture_config(monkeypatch):
    # capture.max_seconds absent de la config -> défaut config.yaml (300s).
    monkeypatch.setattr(cli, "load_config", lambda: {})

    assert cli._client_timeout("dictate-stop") == 300 + cli._TIMEOUT_MARGIN_S


def test_dictate_stop_timeout_falls_back_to_none_if_config_unloadable(monkeypatch):
    def _boom():
        raise RuntimeError("config introuvable")

    monkeypatch.setattr(cli, "load_config", _boom)

    assert cli._client_timeout("dictate-stop") is None
