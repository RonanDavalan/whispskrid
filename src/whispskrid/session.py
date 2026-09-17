"""État interne de la session résidente — capture, transcription, injection.

Machine à deux états (`idle` / `capturing`), plus une couche armée au-dessus
(mode armé par mot vocal), pilotée symétriquement par l'écouteur `pynput`
(hotkey.py) et par la socket de contrôle (control.py) — §2.4, §3.3
CONCEPTION_WHISPSKRID.md. Un verrou sérialise les transitions : les deux
voies peuvent démarrer/arrêter/annuler la même capture sans se marcher
dessus.

La transcription et l'injection se font toujours dans le fil de capture
lui-même, qu'il se termine par une relâche explicite (active_event effacé)
ou par le garde-fou `capture.max_seconds` (§2.2, boucle de audio.py qui sort
d'elle-même) : ainsi une touche restée bloquée produit quand même une
injection, sans qu'aucune commande externe n'ait besoin d'intervenir.

**Couche armée, en englobante au-dessus de idle/capturing.** `arm()` /
`disarm()` démarrent et arrêtent un fil unique et dédié
(`_run_armed_listener`) qui est, tant qu'il tourne, le SEUL lecteur du flux
micro : `audio.capture_episode()` (utilisé par `start_capture()`) fait des
`stream.read()` bloquants dans sa propre boucle, incompatibles avec un second
lecteur concurrent sur le même flux (l'API bloquante de PortAudio n'est pas
conçue pour ça — deux lecteurs se partageraient les échantillons de façon
imprévisible, corrompant guetteur et transcription à la fois). Écart
volontaire à la conception initiale (« `Session.start_capture()` est appelée
telle quelle », CONCEPTION_WHISPSKRID.md) : `_run_armed_listener` réutilise
directement `_transcribe_and_inject()` (déjà privée) au lieu de passer par
`start_capture()`/`stop_capture_and_inject()`, pour obtenir le même effet
observable (son de confirmation, transition idle/capturing, transcription et
injection) sans ouvrir de second lecteur — la conception initiale s'est
révélée non exécutable telle quelle (deux lecteurs concurrents impossibles
sur ce flux). Les modes `hold`/`toggle` ne sont pas touchés par ce choix.
`start_capture()`/`stop_capture_and_inject()`/`cancel()` refusent
(`ERR armed-mode-active`) tant que l'armement est engagé : la socket ne peut
pas ouvrir un second lecteur pendant que `_run_armed_listener` tourne.
"""

from __future__ import annotations

import sys
import threading

import numpy as np

from whispskrid import audio, backend, injection, wakeword


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
        self._last_error: str | None = None

        self._armed = False
        self._armed_substate: str | None = None  # None | "waiting" | "segment"
        self._armed_thread: threading.Thread | None = None
        self._armed_stop = threading.Event()

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
            armed = self._armed
            armed_substate = self._armed_substate
        base = f"state={state} model={self.model_name} language={self.language or 'auto'}"
        return f"{base} armed={armed_substate}" if armed else base

    def is_armed(self) -> bool:
        with self._lock:
            return self._armed

    # --------------------------------------------------------------- #
    # Transitions — appelées par hotkey.py et control.py               #
    # --------------------------------------------------------------- #

    def start_capture(self) -> tuple[bool, str]:
        with self._lock:
            if self._armed:
                return False, "ERR armed-mode-active"
            if self._state == "capturing":
                return False, "ERR already-capturing"
            self._state = "capturing"
            self._cancel_flag = False
            self._last_text = ""
            self._last_cancelled = False
            self._last_error = None
            self._active_event.set()
            self._finished_event = threading.Event()
            self._capture_thread = threading.Thread(target=self._run_capture, daemon=True)
            self._capture_thread.start()
        injection.play_sound()
        return True, "OK"

    def stop_capture_and_inject(self) -> tuple[bool, str]:
        with self._lock:
            if self._armed:
                return False, "ERR armed-mode-active"
            if self._state != "capturing":
                return False, "ERR not-capturing"
            self._active_event.clear()
        self._finished_event.wait()
        with self._lock:
            cancelled = self._last_cancelled
            error = self._last_error
            text = self._last_text
        if cancelled:
            return True, "OK cancelled"
        if error:
            return False, f"ERR {error}"
        return True, (f"OK {text}" if text else "OK")

    def cancel(self) -> tuple[bool, str]:
        with self._lock:
            if self._armed:
                return False, "ERR armed-mode-active"
            if self._state != "capturing":
                return False, "ERR not-capturing"
            self._cancel_flag = True
            self._active_event.clear()
        self._finished_event.wait()
        return True, "OK"

    def toggle(self) -> tuple[bool, str]:
        with self._lock:
            if self._armed:
                return False, "ERR armed-mode-active"
            capturing = self._state == "capturing"
        if capturing:
            return self.stop_capture_and_inject()
        return self.start_capture()

    # --------------------------------------------------------------- #
    # Mode armé — armement/désarmement, exclusivement au clavier   #
    # --------------------------------------------------------------- #

    def arm(self) -> tuple[bool, str]:
        """Passe en armé-attente : charge les modèles de phrase de la langue
        active (repli français si aucune langue explicite — pas de notion
        de phrase « auto ») et démarre le fil unique qui lit le flux
        micro en continu jusqu'au désarmement. Échoue proprement, sans rien
        démarrer, si les modèles de phrase de cette langue sont absents
        (entraînement réel non encore fait, voir wakeword.py)."""
        with self._lock:
            if self._armed:
                return False, "ERR already-armed"
            if self._state == "capturing":
                return False, "ERR already-capturing"

            language = self.language or "fr"
            wakeword_cfg = self.cfg.get("wakeword", {})
            try:
                wakeword.load(
                    language,
                    models_dir=wakeword_cfg.get("models_dir") or None,
                    threshold=wakeword_cfg.get("threshold", 0.5),
                )
            except RuntimeError as exc:
                return False, f"ERR {exc}"

            self._armed = True
            self._armed_substate = "waiting"
            self._armed_stop.clear()
            self._armed_thread = threading.Thread(target=self._run_armed_listener, daemon=True)
            self._armed_thread.start()
        return True, "OK"

    def disarm(self) -> tuple[bool, str]:
        """Repasse en désarmé depuis n'importe lequel des deux états armés
        : un segment en cours au moment du désarmement est jeté, jamais
        injecté à moitié — même principe que `cancel()`."""
        with self._lock:
            if not self._armed:
                return False, "ERR not-armed"
            self._armed_stop.set()
        thread = self._armed_thread
        if thread is not None:
            thread.join()
        with self._lock:
            self._armed = False
            self._armed_substate = None
            self._armed_thread = None
            if self._state == "capturing":
                self._state = "idle"
        wakeword.unload()
        return True, "OK"

    # --------------------------------------------------------------- #
    # Fil unique du mode armé — seul lecteur du flux tant qu'armé  #
    # --------------------------------------------------------------- #

    def _run_armed_listener(self) -> None:
        audio_cfg = self.cfg.get("audio", {})
        frames_per_buffer = audio_cfg.get("frames_per_buffer", 4096)
        sample_rate = audio_cfg.get("sample_rate", 16000)
        max_seconds = self.cfg.get("capture", {}).get("max_seconds", 300)
        max_frames = int(max_seconds * sample_rate)

        # Même raison qu'en appui-pour-parler classique (audio.py,
        # `_drain_stale_backlog`) : sans purge, l'audio bufférisé par
        # PortAudio pendant que la session était désarmée se retrouverait en
        # tête de la première détection.
        audio._drain_stale_backlog(self._stream)

        segment_chunks: list[bytes] = []
        segment_frames = 0

        while not self._armed_stop.is_set():
            try:
                data = self._stream.read(frames_per_buffer, exception_on_overflow=False)
            except OSError:
                break

            chunk = np.frombuffer(data, dtype=np.int16)
            try:
                detected = wakeword.feed(chunk)
            except Exception as exc:
                print(f"whispskrid : échec du guetteur wakeword : {exc}", file=sys.stderr)
                detected = None

            with self._lock:
                substate = self._armed_substate

            if substate == "waiting":
                if detected == "open":
                    with self._lock:
                        self._armed_substate = "segment"
                        self._state = "capturing"
                    injection.play_sound()
                    wakeword.reset()
                    segment_chunks = []
                    segment_frames = 0

            elif substate == "segment":
                segment_chunks.append(data)
                segment_frames += frames_per_buffer
                closed = detected == "close"
                exhausted = segment_frames >= max_frames
                if exhausted and not closed:
                    print(
                        "whispskrid : capture.max_seconds atteint (mode armé) — "
                        "segment arrêté d'elle-même.",
                        file=sys.stderr,
                    )
                if closed or exhausted:
                    raw = b"".join(segment_chunks)
                    audio_int16 = np.frombuffer(raw, dtype=np.int16)
                    audio_data = audio_int16.astype(np.float32) / 32768.0
                    try:
                        self._transcribe_and_inject(audio_data)
                    except Exception as exc:
                        print(
                            f"whispskrid : échec de la transcription ou de "
                            f"l'injection (mode armé) : {exc}",
                            file=sys.stderr,
                        )
                    with self._lock:
                        self._armed_substate = "waiting"
                        self._state = "idle"
                    wakeword.reset()
                    segment_chunks = []
                    segment_frames = 0

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
        error: str | None = None
        try:
            if not cancelled:
                text = self._transcribe_and_inject(result)
        except Exception as exc:
            # Une transcription ou une injection qui lève ne doit jamais bloquer
            # indéfiniment stop_capture_and_inject()/cancel() (qui attendent
            # _finished_event) : l'épisode est perdu, journalisé, l'état revient
            # à idle comme pour une capture vide. L'échec remonte au client par
            # ERR (§3.3 CONCEPTION_WHISPSKRID.md) — jamais un OK sans texte qui
            # masquerait la différence avec une capture simplement vide.
            error = str(exc)
            print(f"whispskrid : échec de la transcription ou de l'injection : {exc}", file=sys.stderr)

        with self._lock:
            self._last_text = text
            self._last_cancelled = cancelled
            self._last_error = error
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
