"""Socket de contrôle Unix — pilotage d'une session persistante en cours.

Protocole texte ligne à ligne, §3.3 CONCEPTION_WHISPSKRID.md : une commande
par ligne, réponse préfixée `OK`/`ERR`.
Le serveur tourne dans la session persistante (un fil par connexion, §3.1) ; le
client est invoqué par `whispskrid --dictate`/`--status`/… (cli.py, mode
client), ou par `session_running()` pour la vérification d'instance unique
(§3.2) avant d'ouvrir une nouvelle session persistante.
"""

from __future__ import annotations

import os
import socket
import threading
from pathlib import Path

from whispskrid.session import Session

_CONNECT_TIMEOUT = 2.0
_RECV_TIMEOUT = 30.0  # une transcription peut prendre plusieurs secondes


def socket_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    base = Path(runtime_dir) if runtime_dir else Path("/tmp")
    return base / "whispskrid.sock"


# --------------------------------------------------------------------- #
# Client (mode sous-commande de contrôle, cli.py)                       #
# --------------------------------------------------------------------- #

def send_control_command(command: str, timeout: float = _RECV_TIMEOUT) -> tuple[bool, str]:
    """Envoie une commande à la session persistante en cours et attend sa
    réponse d'une ligne. (ok, texte de réponse) — jamais d'exception remontée
    à l'appelant : une socket injoignable est un cas normal (aucune session)."""
    path = socket_path()
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(_CONNECT_TIMEOUT)
            sock.connect(str(path))
            sock.settimeout(timeout)
            sock.sendall((command.strip() + "\n").encode("utf-8"))
            data = b""
            while not data.endswith(b"\n"):
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
    except OSError:
        return False, "aucune session whispskrid en cours (socket injoignable)"
    reply = data.decode("utf-8", errors="replace").strip()
    return reply.startswith("OK"), reply


def session_running() -> bool:
    """Vrai si une session persistante répond déjà (§3.2, instance unique)."""
    ok, _reply = send_control_command("status", timeout=_CONNECT_TIMEOUT)
    return ok


# --------------------------------------------------------------------- #
# Serveur (session persistante)                                           #
# --------------------------------------------------------------------- #

def _dispatch(session: Session, command: str) -> str:
    if command == "status":
        return f"OK {session.status()}"
    if command == "dictate":
        _ok, msg = session.start_capture()
        return msg
    if command == "dictate-stop":
        _ok, msg = session.stop_capture_and_inject()
        return msg
    if command == "toggle":
        _ok, msg = session.toggle()
        return msg
    if command == "cancel":
        _ok, msg = session.cancel()
        return msg
    if command == "quit":
        session.stop_requested.set()
        return "OK"
    return "ERR unknown-command"


def _handle_client(session: Session, conn: socket.socket) -> None:
    with conn:
        buf = b""
        try:
            while b"\n" not in buf:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                buf += chunk
        except OSError:
            return
        command = buf.decode("utf-8", errors="replace").strip()
        reply = _dispatch(session, command)
        try:
            conn.sendall((reply + "\n").encode("utf-8"))
        except OSError:
            pass


def run_server(session: Session) -> socket.socket:
    """Ouvre la socket de contrôle et démarre son fil d'acceptation.

    À appeler seulement après que l'appelant (cli.py) a vérifié
    `session_running()` : cette fonction ne revérifie pas elle-même, elle
    remplace inconditionnellement une socket-fichier résiduelle (session
    précédente arrêtée sans nettoyage propre)."""
    path = socket_path()
    if path.exists():
        path.unlink()

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    os.chmod(path, 0o700)
    server.listen(5)
    server.settimeout(0.5)

    def accept_loop() -> None:
        while not session.stop_requested.is_set():
            try:
                conn, _addr = server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=_handle_client, args=(session, conn), daemon=True).start()

    threading.Thread(target=accept_loop, daemon=True).start()
    return server


def close_server(server: socket.socket) -> None:
    try:
        server.close()
    finally:
        path = socket_path()
        if path.exists():
            path.unlink()
