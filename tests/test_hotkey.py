# Écouteur pynput (hotkey.py) : couvre les deux valeurs de `hotkeys.mode`
# (CONCEPTION_WHISPSKRID.md) — "hold" (défaut,
# comportement historique inchangé) et "toggle" (appui bref démarre, appui
# bref suivant arrête et injecte) — ainsi que la garde de durée minimale
# (`hotkeys.min_hold_ms`) sur le mode "hold". `pynput.keyboard.Listener` n'est
# jamais démarré ici : on appelle directement les callbacks
# `on_press`/`on_release` construits par `start_listener`, en doublant
# `Session` pour ne dépendre ni du matériel audio ni d'un serveur X réel.

from __future__ import annotations

from unittest.mock import MagicMock

from pynput import keyboard

from whispskrid import hotkey


def _fake_session() -> MagicMock:
    return MagicMock()


def _get_callbacks(monkeypatch, session, push_to_talk, mode, min_hold_ms=250):
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
    hotkey.start_listener(session, push_to_talk, mode, min_hold_ms)
    return captured["on_press"], captured["on_release"]


def test_hold_mode_starts_on_press_and_stops_on_release(monkeypatch):
    session = _fake_session()
    times = iter([100.0, 101.0])  # 1 s tenu, largement au-dessus de min_hold_ms
    monkeypatch.setattr(hotkey.time, "monotonic", lambda: next(times))
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


def test_hold_mode_cancels_press_shorter_than_min_hold_ms(monkeypatch):
    session = _fake_session()
    times = iter([100.0, 100.1])  # 100 ms < min_hold_ms (250 ms par défaut)
    monkeypatch.setattr(hotkey.time, "monotonic", lambda: next(times))
    on_press, on_release = _get_callbacks(monkeypatch, session, ["ctrl_r"], "hold")

    on_press(keyboard.Key.ctrl_r)
    on_release(keyboard.Key.ctrl_r)

    session.cancel.assert_called_once()
    session.stop_capture_and_inject.assert_not_called()


def test_hold_mode_injects_press_at_least_min_hold_ms(monkeypatch):
    session = _fake_session()
    times = iter([100.0, 100.3])  # 300 ms >= min_hold_ms (250 ms par défaut)
    monkeypatch.setattr(hotkey.time, "monotonic", lambda: next(times))
    on_press, on_release = _get_callbacks(monkeypatch, session, ["ctrl_r"], "hold")

    on_press(keyboard.Key.ctrl_r)
    on_release(keyboard.Key.ctrl_r)

    session.stop_capture_and_inject.assert_called_once()
    session.cancel.assert_not_called()


def test_hold_mode_respects_custom_min_hold_ms(monkeypatch):
    session = _fake_session()
    times = iter([100.0, 100.05])  # 50 ms, sous un seuil custom de 30 ms
    monkeypatch.setattr(hotkey.time, "monotonic", lambda: next(times))
    on_press, on_release = _get_callbacks(
        monkeypatch, session, ["ctrl_r"], "hold", min_hold_ms=30
    )

    on_press(keyboard.Key.ctrl_r)
    on_release(keyboard.Key.ctrl_r)

    session.stop_capture_and_inject.assert_called_once()
    session.cancel.assert_not_called()


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
    # `start_listener(session, push_to_talk)` sans troisième/quatrième argument
    # doit se comporter comme "hold" à 250 ms — signature par défaut vérifiée
    # directement.
    assert hotkey.start_listener.__defaults__ == ("hold", 250)

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


def test_hold_mode_combo_starts_only_when_both_keys_held(monkeypatch):
    session = _fake_session()
    times = iter([100.0, 101.0])  # 1 s tenu, largement au-dessus de min_hold_ms
    monkeypatch.setattr(hotkey.time, "monotonic", lambda: next(times))
    on_press, on_release = _get_callbacks(
        monkeypatch, session, ["alt_l", "shift_r"], "hold"
    )

    on_press(keyboard.Key.alt_l)
    session.start_capture.assert_not_called()  # une seule des deux touches

    on_press(keyboard.Key.shift_r)
    session.start_capture.assert_called_once()  # combinaison complète

    on_release(keyboard.Key.shift_r)
    session.stop_capture_and_inject.assert_called_once()

    on_release(keyboard.Key.alt_l)  # relâche restante : pas de second arrêt
    session.stop_capture_and_inject.assert_called_once()


def test_hold_mode_combo_order_of_press_does_not_matter(monkeypatch):
    session = _fake_session()
    times = iter([100.0, 100.3])
    monkeypatch.setattr(hotkey.time, "monotonic", lambda: next(times))
    on_press, on_release = _get_callbacks(
        monkeypatch, session, ["alt_l", "shift_r"], "hold"
    )

    on_press(keyboard.Key.shift_r)
    on_press(keyboard.Key.alt_l)
    session.start_capture.assert_called_once()

    on_release(keyboard.Key.alt_l)
    session.stop_capture_and_inject.assert_called_once()
    session.cancel.assert_not_called()


def test_hold_mode_combo_cancels_if_released_before_min_hold_ms(monkeypatch):
    session = _fake_session()
    times = iter([100.0, 100.1])  # 100 ms < min_hold_ms (250 ms par défaut)
    monkeypatch.setattr(hotkey.time, "monotonic", lambda: next(times))
    on_press, on_release = _get_callbacks(
        monkeypatch, session, ["alt_l", "shift_r"], "hold"
    )

    on_press(keyboard.Key.alt_l)
    on_press(keyboard.Key.shift_r)
    on_release(keyboard.Key.shift_r)

    session.cancel.assert_called_once()
    session.stop_capture_and_inject.assert_not_called()


def test_toggle_mode_combo_fires_once_per_full_press_cycle(monkeypatch):
    session = _fake_session()
    on_press, on_release = _get_callbacks(
        monkeypatch, session, ["alt_l", "shift_r"], "toggle"
    )

    on_press(keyboard.Key.alt_l)
    session.toggle.assert_not_called()
    on_press(keyboard.Key.shift_r)
    session.toggle.assert_called_once()

    on_press(keyboard.Key.shift_r)  # répétition matérielle, combinaison déjà engagée
    session.toggle.assert_called_once()

    on_release(keyboard.Key.alt_l)
    on_release(keyboard.Key.shift_r)
    on_press(keyboard.Key.alt_l)
    on_press(keyboard.Key.shift_r)  # nouveau cycle complet : second toggle
    assert session.toggle.call_count == 2


def test_hold_mode_accepts_function_key(monkeypatch):
    session = _fake_session()
    times = iter([100.0, 101.0])
    monkeypatch.setattr(hotkey.time, "monotonic", lambda: next(times))
    on_press, on_release = _get_callbacks(monkeypatch, session, ["f4"], "hold")

    on_press(keyboard.Key.f4)
    session.start_capture.assert_called_once()

    on_release(keyboard.Key.f4)
    session.stop_capture_and_inject.assert_called_once()


def test_no_valid_key_returns_none_and_starts_no_listener(monkeypatch, capsys):
    session = _fake_session()
    result = hotkey.start_listener(session, ["touche_inconnue"], "toggle")

    assert result is None
    captured = capsys.readouterr()
    assert "aucune touche valide" in captured.err
