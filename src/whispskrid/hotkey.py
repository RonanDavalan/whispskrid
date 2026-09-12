"""Écouteur de raccourci local — voie de déclenchement `pynput`.

PHASE_EXECUTION, tranche 5 ; session E (mode `armed`, D9). Observe le serveur
X (`pynput`) : sous Wayland il ne capte que les fenêtres passant par
XWayland, jamais une fenêtre Wayland native — confort best-effort, §2.4
CONCEPTION_WHISPSKRID.md et COMPATIBILITE_WAYLAND.md §5. `on_press` déclenche
la capture, `on_release` l'arrête et l'injecte : `pynput` distingue
nativement l'appui de la relâche, la sémantique maintien est donc native sur
cette voie — contrairement à la voie socket (control.py) qui doit basculer
faute de transmettre ce geste.

Mode `armed` (D9) : la touche arme/désarme uniquement (`Session.arm()` /
`Session.disarm()`), jamais de capture directe — le début et la fin de
chaque segment sont ensuite pilotés par la voix (voir session.py,
`_run_armed_listener`).
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


def start_listener(
    session: Session, push_to_talk: list[str], mode: str = "hold"
) -> keyboard.Listener | None:
    """Démarre l'écouteur en tâche de fond. None si aucune touche valide dans
    `push_to_talk` — la session résidente reste pilotable par la socket seule.

    `mode` (D8/D9, CONCEPTION_WHISPSKRID.md) : "hold" (défaut) conserve le
    comportement historique — maintien = capture, relâche = transcription et
    injection. "toggle" appelle `Session.toggle()` (déjà exposée côté socket,
    control.py) sur l'appui ; la relâche ne fait plus rien. "armed" (D9)
    arme/désarme l'écoute continue du mot vocal sur l'appui ; la relâche ne
    fait rien non plus.
    """
    keys = _resolve_keys(push_to_talk)
    if not keys:
        print(
            "whispskrid : hotkeys.push_to_talk ne contient aucune touche valide "
            "— écouteur pynput non démarré.",
            file=sys.stderr,
        )
        return None

    pressed: set = set()

    if mode == "toggle":

        def on_press(key) -> None:
            if key in keys and key not in pressed:
                pressed.add(key)
                session.toggle()

        def on_release(key) -> None:
            pressed.discard(key)

    elif mode == "armed":

        def on_press(key) -> None:
            if key in keys and key not in pressed:
                pressed.add(key)
                if session.is_armed():
                    ok, msg = session.disarm()
                else:
                    ok, msg = session.arm()
                if not ok:
                    print(f"whispskrid : {msg}", file=sys.stderr)

        def on_release(key) -> None:
            pressed.discard(key)

    else:

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
