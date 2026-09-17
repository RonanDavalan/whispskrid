# capture_episode() doit purger le résidu PortAudio accumulé pendant
# l'inactivité avant de commencer à accumuler la vraie capture — sinon le
# début de chaque dictée contient de l'audio périmé (voir la docstring de
# _drain_stale_backlog() dans audio.py pour l'incident qui a motivé ce
# correctif : dégradation progressive de la transcription en session
# résidente longue).

from __future__ import annotations

import numpy as np

from whispskrid import audio


class _FakeStream:
    """Flux PyAudio doublé : `_backlog` simule le tampon PortAudio rempli
    pendant l'inactivité, `_live` la vraie parole capturée pendant l'appui."""

    def __init__(self, backlog: bytes, live_chunks: list[bytes]):
        self._backlog = backlog
        self._live_chunks = list(live_chunks)
        self.reads: list[int] = []

    def get_read_available(self) -> int:
        return len(self._backlog) // 2  # int16 -> 2 octets par trame

    def read(self, n_frames: int, exception_on_overflow: bool = False) -> bytes:
        self.reads.append(n_frames)
        n_bytes = n_frames * 2
        if self._backlog:
            out, self._backlog = self._backlog[:n_bytes], self._backlog[n_bytes:]
            return out
        if self._live_chunks:
            return self._live_chunks.pop(0)
        return b"\x00" * n_bytes


def _cfg():
    return {
        "audio": {"sample_rate": 16000, "channels": 1, "frames_per_buffer": 4},
        "capture": {"max_seconds": 10},
    }


def test_stale_backlog_is_dropped_before_real_capture():
    backlog = (np.full(6, 12345, dtype=np.int16)).tobytes()  # résidu périmé
    live = (np.full(4, 999, dtype=np.int16)).tobytes()       # vraie parole
    stream = _FakeStream(backlog, [live])

    calls = {"n": 0}

    def is_active():
        calls["n"] += 1
        return calls["n"] <= 1  # une seule itération de vraie capture

    result = audio.capture_episode(stream, _cfg(), is_active=is_active)

    assert not np.any(result == 12345 / 32768.0)
    assert np.all(result == 999 / 32768.0)


def test_no_backlog_leaves_capture_unaffected():
    live = (np.full(4, 999, dtype=np.int16)).tobytes()
    stream = _FakeStream(b"", [live])

    calls = {"n": 0}

    def is_active():
        calls["n"] += 1
        return calls["n"] <= 1

    result = audio.capture_episode(stream, _cfg(), is_active=is_active)

    assert np.all(result == 999 / 32768.0)


def test_drain_stops_on_oserror(monkeypatch):
    stream = _FakeStream(b"\x00" * 100, [])

    def raising_read(n, exception_on_overflow=False):
        raise OSError("périphérique disparu")

    monkeypatch.setattr(stream, "read", raising_read)

    audio._drain_stale_backlog(stream)  # ne doit jamais lever
