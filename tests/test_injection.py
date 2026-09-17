# _paste_combo_for_target() (injection.py) doit choisir le combo terminal
# (ctrl+shift+v) quand la fenêtre active est un terminal listé dans
# injection.terminal_window_classes, et le combo générique (ctrl+v) sinon.
#
# La détection de classe reposait sur `xdotool getactivewindow
# getwindowclassname`, une sous-commande absente de la version xdotool
# packagée Debian (3.20160805.1) — la classe retournée était toujours vide,
# le combo terminal n'était donc jamais choisi. Défaut invisible dans un
# bash (ctrl+v y est lié à l'insertion verbatim, sans effet visible),
# démasqué par un collage réel dans un terminal graphique. Corrigé par
# `xprop -id <id> WM_CLASS`, régression couverte ici en doublant `_run`
# (aucun serveur X nécessaire pour le test).
#
# Second défaut : la détection
# de fenêtre n'était tentée que si `key_backend == "xdotool"`, alors que
# ydotool est prioritaire dès qu'il est présent (COMPATIBILITE_WAYLAND.md
# §2) — sur toute machine avec ydotool ET xdotool/xprop disponibles (le cas
# courant), le combo terminal n'était donc jamais choisi non plus, silencieux
# pour la même raison. Corrigé en testant `caps["xdotool"]` (présence de
# l'outillage de détection) au lieu du backend d'envoi retenu.

from __future__ import annotations

from whispskrid import injection


def _cfg():
    return {
        "injection": {
            "paste_combo": "ctrl+v",
            "terminal_paste_combo": "ctrl+shift+v",
            "terminal_window_classes": ["konsole", "gnome-terminal-server"],
        }
    }


def test_terminal_class_selects_terminal_combo(monkeypatch):
    injection.configure(_cfg())
    monkeypatch.setattr(injection, "_detect_caps", lambda: {"key_backend": "xdotool", "xdotool": True})
    monkeypatch.setattr(injection, "get_active_window_id", lambda: "12582920")

    def fake_run(cmd, timeout, stdin_text=None):
        assert cmd == ["xprop", "-id", "12582920", "WM_CLASS"]
        return True, 'WM_CLASS(STRING) = "konsole", "konsole"\n'

    monkeypatch.setattr(injection, "_run", fake_run)

    assert injection._paste_combo_for_target() == "ctrl+shift+v"


def test_non_terminal_class_selects_default_combo(monkeypatch):
    injection.configure(_cfg())
    monkeypatch.setattr(injection, "_detect_caps", lambda: {"key_backend": "xdotool", "xdotool": True})
    monkeypatch.setattr(injection, "get_active_window_id", lambda: "999")
    monkeypatch.setattr(
        injection, "_run",
        lambda cmd, timeout, stdin_text=None: (True, 'WM_CLASS(STRING) = "firefox", "Firefox"\n'),
    )

    assert injection._paste_combo_for_target() == "ctrl+v"


def test_xprop_failure_falls_back_to_default_combo(monkeypatch):
    # xprop absent, timeout, ou fenêtre déjà fermée : ne doit jamais lever,
    # juste retomber sur le combo générique.
    injection.configure(_cfg())
    monkeypatch.setattr(injection, "_detect_caps", lambda: {"key_backend": "xdotool", "xdotool": True})
    monkeypatch.setattr(injection, "get_active_window_id", lambda: "999")
    monkeypatch.setattr(injection, "_run", lambda cmd, timeout, stdin_text=None: (False, ""))

    assert injection._paste_combo_for_target() == "ctrl+v"


def test_no_active_window_falls_back_to_default_combo(monkeypatch):
    injection.configure(_cfg())
    monkeypatch.setattr(injection, "_detect_caps", lambda: {"key_backend": "xdotool", "xdotool": True})
    monkeypatch.setattr(injection, "get_active_window_id", lambda: None)

    assert injection._paste_combo_for_target() == "ctrl+v"


def test_terminal_detection_used_even_when_ydotool_is_the_key_backend(monkeypatch):
    # ydotool prioritaire (COMPATIBILITE_WAYLAND.md §2) mais xdotool/xprop
    # présents : la détection de fenêtre doit quand même se faire, elle ne
    # dépend pas du backend retenu pour l'envoi des touches.
    injection.configure(_cfg())
    monkeypatch.setattr(injection, "_detect_caps", lambda: {"key_backend": "ydotool", "xdotool": True})
    monkeypatch.setattr(injection, "get_active_window_id", lambda: "12582920")
    monkeypatch.setattr(
        injection, "_run",
        lambda cmd, timeout, stdin_text=None: (True, 'WM_CLASS(STRING) = "konsole", "konsole"\n'),
    )

    assert injection._paste_combo_for_target() == "ctrl+shift+v"


def test_terminal_detection_skipped_without_xdotool(monkeypatch):
    # Ni xdotool ni xprop disponibles (machine Wayland pure, sans XWayland) :
    # aucune détection possible, combo générique par construction.
    injection.configure(_cfg())
    monkeypatch.setattr(injection, "_detect_caps", lambda: {"key_backend": "ydotool", "xdotool": False})
    calls = []
    monkeypatch.setattr(injection, "get_active_window_id", lambda: calls.append(1) or "999")

    assert injection._paste_combo_for_target() == "ctrl+v"
    assert calls == []
