"""Écouteur de raccourci local — voie de déclenchement `pynput`.

Observe le serveur X (`pynput`) : sous Wayland il ne capte que les
fenêtres passant par XWayland, jamais une fenêtre Wayland native — confort
best-effort.
`on_press` déclenche
la capture, `on_release` l'arrête et l'injecte : `pynput` distingue
nativement l'appui de la relâche, la sémantique maintien est donc native sur
cette voie — contrairement à la voie socket (control.py) qui doit basculer
faute de transmettre ce geste.

Mode `armed` : la touche arme/désarme uniquement (`Session.arm()` /
`Session.disarm()`), jamais de capture directe — le début et la fin de
chaque segment sont ensuite pilotés par la voix (voir session.py,
`_run_armed_listener`).
"""

from __future__ import annotations

import sys
import time

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
    "f1": keyboard.Key.f1,
    "f2": keyboard.Key.f2,
    "f3": keyboard.Key.f3,
    "f4": keyboard.Key.f4,
    "f5": keyboard.Key.f5,
    "f6": keyboard.Key.f6,
    "f7": keyboard.Key.f7,
    "f8": keyboard.Key.f8,
    "f9": keyboard.Key.f9,
    "f10": keyboard.Key.f10,
    "f11": keyboard.Key.f11,
    "f12": keyboard.Key.f12,
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
    session: Session, push_to_talk: list[str], mode: str = "hold", min_hold_ms: int = 250
) -> keyboard.Listener | None:
    """Démarre l'écouteur en tâche de fond. None si aucune touche valide dans
    `push_to_talk` — la session persistante reste pilotable par la socket seule.

    `mode` : "hold" (défaut) conserve le
    comportement historique — maintien = capture, relâche = transcription et
    injection. "toggle" appelle `Session.toggle()` (déjà exposée côté socket,
    control.py) sur l'appui ; la relâche ne fait plus rien. "armed"
    arme/désarme l'écoute continue du mot vocal sur l'appui ; la relâche ne
    fait rien non plus.

    `min_hold_ms` : en mode "hold" seulement,
    un appui relâché avant ce délai (en millisecondes) annule la capture
    (`Session.cancel()`) au lieu de la transcrire et l'injecter — garde
    contre un tap bref (touche partagée avec un autre usage du bureau) qui
    ouvrirait une capture sur du bruit ou du quasi-silence, que Whisper
    hallucine.

    Combinaison : quand `push_to_talk`
    contient plusieurs touches, elles forment une combinaison — toutes
    doivent être tenues simultanément pour engager l'action (peu importe
    l'ordre d'appui) ; en mode "hold", la relâche de n'importe laquelle
    d'entre elles arrête et injecte (ou annule, sous `min_hold_ms`). Une
    liste à une seule touche se comporte exactement comme avant (ensemble à
    un élément).
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
    engaged = False

    if mode == "toggle":

        def on_press(key) -> None:
            nonlocal engaged
            if key not in keys:
                return
            pressed.add(key)
            if pressed >= keys and not engaged:
                engaged = True
                session.toggle()

        def on_release(key) -> None:
            nonlocal engaged
            if key in keys:
                pressed.discard(key)
                if not pressed >= keys:
                    engaged = False

    elif mode == "armed":

        def on_press(key) -> None:
            nonlocal engaged
            if key not in keys:
                return
            pressed.add(key)
            if pressed >= keys and not engaged:
                engaged = True
                if session.is_armed():
                    ok, msg = session.disarm()
                else:
                    ok, msg = session.arm()
                if not ok:
                    print(f"whispskrid : {msg}", file=sys.stderr)

        def on_release(key) -> None:
            nonlocal engaged
            if key in keys:
                pressed.discard(key)
                if not pressed >= keys:
                    engaged = False

    else:
        combo_started_at: float | None = None

        def on_press(key) -> None:
            nonlocal engaged, combo_started_at
            if key not in keys:
                return
            pressed.add(key)
            if pressed >= keys and not engaged:
                engaged = True
                combo_started_at = time.monotonic()
                session.start_capture()

        def on_release(key) -> None:
            nonlocal engaged, combo_started_at
            if key not in keys:
                return
            was_engaged = engaged
            pressed.discard(key)
            if was_engaged and not pressed >= keys:
                engaged = False
                held_ms = (
                    (time.monotonic() - combo_started_at) * 1000
                    if combo_started_at is not None
                    else None
                )
                if held_ms is not None and held_ms < min_hold_ms:
                    session.cancel()
                else:
                    session.stop_capture_and_inject()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()
    return listener
