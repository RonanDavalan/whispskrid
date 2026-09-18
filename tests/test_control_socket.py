# Socket de contrôle Unix (control.py) :
# protocole texte ligne à ligne, une commande par ligne, réponse préfixée
# OK/ERR. Le serveur tourne réellement (vrai socket AF_UNIX dans tmp_path),
# la Session est un double minimal — ces tests exercent le protocole, pas la
# capture/transcription réelle (couverte par test_session.py).

from __future__ import annotations

import threading
import time

import pytest

from whispskrid import control


class FakeSession:
    def __init__(self):
        self.stop_requested = threading.Event()
        self._reply = ("OK", "status ok")

    def status(self):
        return "state=idle model=base language=auto"

    def start_capture(self):
        return True, "OK"

    def stop_capture_and_inject(self):
        return True, "OK bonjour le monde"

    def cancel(self):
        return True, "OK"

    def toggle(self):
        return True, "OK"


@pytest.fixture
def running_server(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    session = FakeSession()
    server = control.run_server(session)
    time.sleep(0.05)  # laisser le fil d'acceptation démarrer
    yield session
    session.stop_requested.set()
    control.close_server(server)


def test_status_round_trip(running_server):
    ok, reply = control.send_control_command("status")
    assert ok
    assert reply == "OK state=idle model=base language=auto"


def test_dictate_stop_returns_transcribed_text(running_server):
    ok, reply = control.send_control_command("dictate-stop")
    assert ok
    assert reply == "OK bonjour le monde"


def test_unknown_command_is_rejected(running_server):
    ok, reply = control.send_control_command("nimportequoi")
    assert not ok
    assert reply == "ERR unknown-command"


def test_no_session_running_is_reported_cleanly(tmp_path, monkeypatch):
    # Aucun serveur démarré sur cette socket : cas normal, jamais une
    # exception qui remonte à l'appelant.
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    ok, reply = control.send_control_command("status", timeout=0.5)
    assert not ok
    assert "aucune session" in reply


def test_session_running_reflects_server_state(running_server):
    assert control.session_running() is True


def test_session_running_false_without_server(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    assert control.session_running() is False
