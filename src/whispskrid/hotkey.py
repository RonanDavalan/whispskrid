"""Écouteur de raccourci local — voie de déclenchement `pynput`.

PHASE_EXECUTION, tranche 5. Observe le serveur X (`pynput`) : sous Wayland il
ne capte que les fenêtres passant par XWayland, jamais une fenêtre Wayland
native — confort best-effort, §2.4 CONCEPTION_WHISPSKRID.md et
COMPATIBILITE_WAYLAND.md §5. `on_press` déclenche la capture, `on_release`
l'arrête et l'injecte : `pynput` distingue nativement l'appui de la relâche,
la sémantique maintien est donc native sur cette voie — contrairement à la
voie socket (control.py) qui doit basculer faute de transmettre ce geste.
"""

from __future__ import annotations

import sys

from pynput import keyboard

from whispskrid.session import Session

_NAME_TO_KEY = {
    "ctrl_r": keyboard.Key.ctrl_r,
    "ctrl_l": keyboard.Key.ctrl_l,
    "alt_r": keyboard.Key.alt_r,
    "alt_l": keyboard.Key.alt_l,
    "shift_r": keyboard.Key.shift_r,
    "shift_l": keyboard.Key.shift_l,
    "cmd": keyboard.Key.cmd,
}


def _resolve_keys(names: list[str]) -> set:
    keys = set()
    for name in names:
        key = _NAME_TO_KEY.get(name)
        if key is None:
            print(
                f"whispskrid : touche hotkeys.push_to_talk inconnue ignorée : {name!r}",
                file=sys.stderr,
            )
            continue
        keys.add(key)
    return keys


def start_listener(session: Session, push_to_talk: list[str]) -> keyboard.Listener | None:
    """Démarre l'écouteur en tâche de fond. None si aucune touche valide dans
    `push_to_talk` — la session résidente reste pilotable par la socket seule."""
    keys = _resolve_keys(push_to_talk)
    if not keys:
        print(
            "whispskrid : hotkeys.push_to_talk ne contient aucune touche valide "
            "— écouteur pynput non démarré.",
            file=sys.stderr,
        )
        return None

    pressed: set = set()

    def on_press(key) -> None:
        if key in keys and key not in pressed:
            pressed.add(key)
            session.start_capture()

    def on_release(key) -> None:
        if key in keys:
            pressed.discard(key)
            session.stop_capture_and_inject()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()
    return listener
