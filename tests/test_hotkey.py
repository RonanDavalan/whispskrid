# Écouteur pynput (hotkey.py) : couvre les deux valeurs de `hotkeys.mode`
# introduites par la décision D8 (CONCEPTION_WHISPSKRID.md) — "hold" (défaut,
# comportement historique inchangé) et "toggle" (appui bref démarre, appui
# bref suivant arrête et injecte). `pynput.keyboard.Listener` n'est jamais
# démarré ici : on appelle directement les callbacks `on_press`/`on_release`
# construits par `start_listener`, en doublant `Session` pour ne dépendre ni
# du matériel audio ni d'un serveur X réel.

from __future__ import annotations

from unittest.mock import MagicMock

from pynput import keyboard

from whispskrid import hotkey


def _fake_session() -> MagicMock:
    return MagicMock()


def _get_callbacks(monkeypatch, session, push_to_talk, mode):
    """Intercepte la construction du `keyboard.Listener` pour récupérer les
    callbacks `on_press`/`on_release` sans démarrer de fil ni de serveur X."""
    captured = {}

    class _FakeListener:
        def __init__(self, on_press=None, on_release=None):
            captured["on_press"] = on_press
            captured["on_release"] = on_release
            self.daemon = False

        def start(self) -> None:
            pass

    monkeypatch.setattr(keyboard, "Listener", _FakeListener)
    hotkey.start_listener(session, push_to_talk, mode)
    return captured["on_press"], captured["on_release"]


def test_hold_mode_starts_on_press_and_stops_on_release(monkeypatch):
    session = _fake_session()
    on_press, on_release = _get_callbacks(monkeypatch, session, ["ctrl_r"], "hold")

    on_press(keyboard.Key.ctrl_r)
    session.start_capture.assert_called_once()
    session.toggle.assert_not_called()

    on_release(keyboard.Key.ctrl_r)
    session.stop_capture_and_inject.assert_called_once()


def test_hold_mode_ignores_key_repeat_on_press(monkeypatch):
    session = _fake_session()
    on_press, _ = _get_callbacks(monkeypatch, session, ["ctrl_r"], "hold")

    on_press(keyboard.Key.ctrl_r)
    on_press(keyboard.Key.ctrl_r)  # répétition matérielle avant relâche

    session.start_capture.assert_called_once()


def test_toggle_mode_calls_toggle_on_press_only(monkeypatch):
    session = _fake_session()
    on_press, on_release = _get_callbacks(monkeypatch, session, ["ctrl_r"], "toggle")

    on_press(keyboard.Key.ctrl_r)
    session.toggle.assert_called_once()
    session.start_capture.assert_not_called()
    session.stop_capture_and_inject.assert_not_called()

    on_release(keyboard.Key.ctrl_r)
    session.toggle.assert_called_once()  # la relâche ne déclenche rien de plus


def test_toggle_mode_ignores_key_repeat_on_press(monkeypatch):
    session = _fake_session()
    on_press, on_release = _get_callbacks(monkeypatch, session, ["ctrl_r"], "toggle")

    on_press(keyboard.Key.ctrl_r)
    on_press(keyboard.Key.ctrl_r)  # répétition matérielle avant relâche
    session.toggle.assert_called_once()

    on_release(keyboard.Key.ctrl_r)
    on_press(keyboard.Key.ctrl_r)  # nouvel appui après relâche : un second toggle
    assert session.toggle.call_count == 2


def test_default_mode_is_hold(monkeypatch):
    session = _fake_session()
    on_press, _ = _get_callbacks(monkeypatch, session, ["ctrl_r"], mode="hold")
    # `start_listener(session, push_to_talk)` sans troisième argument doit se
    # comporter comme "hold" — signature par défaut vérifiée directement.
    assert hotkey.start_listener.__defaults__ == ("hold",)

    on_press(keyboard.Key.ctrl_r)
    session.start_capture.assert_called_once()


def test_armed_mode_arms_on_press_when_disarmed(monkeypatch):
    session = _fake_session()
    session.is_armed.return_value = False
    session.arm.return_value = (True, "OK")
    on_press, on_release = _get_callbacks(monkeypatch, session, ["ctrl_r"], "armed")

    on_press(keyboard.Key.ctrl_r)

    session.arm.assert_called_once()
    session.disarm.assert_not_called()
    session.start_capture.assert_not_called()
    session.toggle.assert_not_called()

    on_release(keyboard.Key.ctrl_r)
    session.arm.assert_called_once()  # la relâche ne déclenche rien de plus


def test_armed_mode_disarms_on_press_when_armed(monkeypatch):
    session = _fake_session()
    session.is_armed.return_value = True
    session.disarm.return_value = (True, "OK")
    on_press, _ = _get_callbacks(monkeypatch, session, ["ctrl_r"], "armed")

    on_press(keyboard.Key.ctrl_r)

    session.disarm.assert_called_once()
    session.arm.assert_not_called()


def test_armed_mode_ignores_key_repeat_on_press(monkeypatch):
    session = _fake_session()
    session.is_armed.return_value = False
    session.arm.return_value = (True, "OK")
    on_press, on_release = _get_callbacks(monkeypatch, session, ["ctrl_r"], "armed")

    on_press(keyboard.Key.ctrl_r)
    on_press(keyboard.Key.ctrl_r)  # répétition matérielle avant relâche

    session.arm.assert_called_once()

    on_release(keyboard.Key.ctrl_r)
    session.is_armed.return_value = True
    session.disarm.return_value = (True, "OK")
    on_press(keyboard.Key.ctrl_r)  # nouvel appui après relâche : désarme cette fois

    session.disarm.assert_called_once()


def test_armed_mode_prints_error_when_arm_fails(monkeypatch, capsys):
    session = _fake_session()
    session.is_armed.return_value = False
    session.arm.return_value = (False, "ERR modèles absents")
    on_press, _ = _get_callbacks(monkeypatch, session, ["ctrl_r"], "armed")

    on_press(keyboard.Key.ctrl_r)

    captured = capsys.readouterr()
    assert "ERR modèles absents" in captured.err


def test_no_valid_key_returns_none_and_starts_no_listener(monkeypatch, capsys):
    session = _fake_session()
    result = hotkey.start_listener(session, ["touche_inconnue"], "toggle")

    assert result is None
    captured = capsys.readouterr()
    assert "aucune touche valide" in captured.err
