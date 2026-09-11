"""État interne de la session résidente — capture, transcription, injection.

PHASE_EXECUTION, tranche 5. Machine à deux états (`idle` / `capturing`),
pilotée symétriquement par l'écouteur `pynput` (hotkey.py) et par la socket
de contrôle (control.py) — §2.4, §3.3 CONCEPTION_WHISPSKRID.md. Un verrou
sérialise les transitions : les deux voies peuvent démarrer/arrêter/annuler
la même capture sans se marcher dessus.

La transcription et l'injection se font toujours dans le fil de capture
lui-même, qu'il se termine par une relâche explicite (active_event effacé)
ou par le garde-fou `capture.max_seconds` (§2.2, boucle de audio.py qui sort
d'elle-même) : ainsi une touche restée bloquée produit quand même une
injection, sans qu'aucune commande externe n'ait besoin d'intervenir.
"""

from __future__ import annotations

import sys
import threading

from whispskrid import audio, backend, injection


class Session:
    def __init__(self, cfg: dict, model_name: str, language: str | None) -> None:
        self.cfg = cfg
        self.model_name = model_name
        self.language = language

        self._lock = threading.Lock()
        self._state = "idle"  # idle | capturing
        self._cancel_flag = False
        self._active_event = threading.Event()
        self._finished_event = threading.Event()
        self._finished_event.set()  # rien en cours au démarrage
        self._capture_thread: threading.Thread | None = None
        self._last_text = ""
        self._last_cancelled = False

        self._pa = None
        self._stream = None

        self.stop_requested = threading.Event()

    # --------------------------------------------------------------- #
    # Cycle de vie du périphérique audio                               #
    # --------------------------------------------------------------- #

    def open(self) -> None:
        self._pa, self._stream = audio.open_stream(self.cfg)
        injection.configure(self.cfg)

    def close(self) -> None:
        if self._stream is not None:
            audio.close_stream(self._pa, self._stream)
        injection.flush_deferred_clipboard()

    # --------------------------------------------------------------- #
    # État                                                             #
    # --------------------------------------------------------------- #

    def status(self) -> str:
        with self._lock:
            state = self._state
        return f"state={state} model={self.model_name} language={self.language or 'auto'}"

    # --------------------------------------------------------------- #
    # Transitions — appelées par hotkey.py et control.py               #
    # --------------------------------------------------------------- #

    def start_capture(self) -> tuple[bool, str]:
        with self._lock:
            if self._state == "capturing":
                return False, "ERR already-capturing"
            self._state = "capturing"
            self._cancel_flag = False
            self._last_text = ""
            self._last_cancelled = False
            self._active_event.set()
            self._finished_event = threading.Event()
            self._capture_thread = threading.Thread(target=self._run_capture, daemon=True)
            self._capture_thread.start()
        injection.play_sound()
        return True, "OK"

    def stop_capture_and_inject(self) -> tuple[bool, str]:
        with self._lock:
            if self._state != "capturing":
                return False, "ERR not-capturing"
            self._active_event.clear()
        self._finished_event.wait()
        with self._lock:
            cancelled = self._last_cancelled
            text = self._last_text
        if cancelled:
            return True, "OK cancelled"
        return True, (f"OK {text}" if text else "OK")

    def cancel(self) -> tuple[bool, str]:
        with self._lock:
            if self._state != "capturing":
                return False, "ERR not-capturing"
            self._cancel_flag = True
            self._active_event.clear()
        self._finished_event.wait()
        return True, "OK"

    def toggle(self) -> tuple[bool, str]:
        with self._lock:
            capturing = self._state == "capturing"
        if capturing:
            return self.stop_capture_and_inject()
        return self.start_capture()

    # --------------------------------------------------------------- #
    # Fil de capture                                                   #
    # --------------------------------------------------------------- #

    def _run_capture(self) -> None:
        def on_max_seconds() -> None:
            print(
                "whispskrid : capture.max_seconds atteint — capture arrêtée d'elle-même.",
                file=sys.stderr,
            )

        result = audio.capture_episode(
            self._stream,
            self.cfg,
            is_active=self._active_event.is_set,
            on_max_seconds=on_max_seconds,
        )

        with self._lock:
            cancelled = self._cancel_flag

        text = ""
        try:
            if not cancelled:
                text = self._transcribe_and_inject(result)
        except Exception as exc:
            # Une transcription ou une injection qui lève ne doit jamais bloquer
            # indéfiniment stop_capture_and_inject()/cancel() (qui attendent
            # _finished_event) : l'épisode est perdu, journalisé, l'état revient
            # à idle comme pour une capture vide.
            print(f"whispskrid : échec de la transcription ou de l'injection : {exc}", file=sys.stderr)

        with self._lock:
            self._last_text = text
            self._last_cancelled = cancelled
            self._state = "idle"
            self._capture_thread = None
        self._finished_event.set()

    def _transcribe_and_inject(self, audio_data) -> str:
        if audio_data is None or audio_data.size == 0:
            return ""
        text = backend.transcribe(audio_data, self.language)
        text = self._post_process(text)
        if text:
            injection.type_text(text)
        return text

    def _post_process(self, text: str) -> str:
        pp = self.cfg.get("post_processing", {})
        if pp.get("trim", True):
            text = text.strip()
        if pp.get("capitalize_sentence_start", True) and text:
            text = text[0].upper() + text[1:]
        return text
