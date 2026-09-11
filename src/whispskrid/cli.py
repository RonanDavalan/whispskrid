"""Point d'entrée CLI de WhispSkrid.

PHASE_EXECUTION, tranche 6 : assemblage complet de `config.py` + `backend/` +
`models.py` + `injection.py` + `audio.py` + `session.py` + `control.py` +
`hotkey.py` + `diagnose.py`. Surface CLI conforme à
_CADRE/SPECIFICATIONS/CONCEPTION_WHISPSKRID.md §7. `--download-model` reste un
stub explicite (§5.2, tranche non ouverte) — pas un silence.
"""

from __future__ import annotations

import argparse
import sys

from whispskrid import __version__, control
from whispskrid.config import load_config
from whispskrid.session import Session


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="whispskrid")
    parser.add_argument("--version", action="store_true", help="affiche la version et quitte")
    parser.add_argument("-l", "--lang", metavar="LANG", default=None,
                         help="force la langue de l'interface et de la reconnaissance")
    parser.add_argument("--model", metavar="NOM", default=None,
                         help="surcharge models.default pour cette session")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dictate", action="store_true", help="démarre la capture (session en cours)")
    group.add_argument("--dictate-stop", action="store_true", help="arrête la capture, transcrit, injecte")
    group.add_argument("--toggle", action="store_true", help="dictate ou dictate-stop selon l'état")
    group.add_argument("--cancel", action="store_true", help="jette la capture en cours sans injecter")
    group.add_argument("--status", action="store_true", help="imprime l'état de la session en cours")
    group.add_argument("--stop", action="store_true", help="arrête la session résidente en cours")
    group.add_argument("--diagnose", action="store_true", help="vérifie l'environnement et quitte")
    group.add_argument("--download-model", nargs="?", const="base", default=None, metavar="NOM",
                        help="télécharge un modèle et quitte")

    return parser


# Association attribut argparse -> commande socket (§3.3).
_CLIENT_COMMANDS = {
    "dictate": "dictate",
    "dictate_stop": "dictate-stop",
    "toggle": "toggle",
    "cancel": "cancel",
    "status": "status",
    "stop": "quit",
}


# Commandes qui peuvent déclencher une transcription (dictate-stop toujours,
# toggle si la session est en train de capturer) : le délai de réception par
# défaut de control.py (30 s) est calibré pour un aller-retour de commande,
# pas pour le temps de transcription réel — insuffisant sur matériel lent
# (ARM) ou modèle lourd. On l'aligne sur capture.max_seconds (le plafond que
# la configuration se donne elle-même), plus une marge fixe.
_TRANSCRIBING_COMMANDS = {"dictate-stop", "toggle"}
_TIMEOUT_MARGIN_S = 60.0


def _client_timeout(command: str) -> float | None:
    """None => délai par défaut de control.send_control_command()."""
    if command not in _TRANSCRIBING_COMMANDS:
        return None
    try:
        cfg = load_config()
    except RuntimeError:
        return None
    max_seconds = cfg.get("capture", {}).get("max_seconds", 300)
    return float(max_seconds) + _TIMEOUT_MARGIN_S


def _run_client(args: argparse.Namespace) -> int:
    for attr, command in _CLIENT_COMMANDS.items():
        if getattr(args, attr):
            timeout = _client_timeout(command)
            kwargs = {} if timeout is None else {"timeout": timeout}
            ok, reply = control.send_control_command(command, **kwargs)
            print(reply)
            return 0 if ok else 1
    return 1  # inatteignable : main() n'appelle _run_client que si un attribut est vrai


def _run_resident(args: argparse.Namespace) -> int:
    if control.session_running():
        print(
            "whispskrid : une session résidente tourne déjà — "
            "arrêtez-la (--stop) avant d'en ouvrir une seconde (§3.2).",
            file=sys.stderr,
        )
        return 1

    try:
        cfg = load_config()
    except RuntimeError as exc:
        print(f"whispskrid : {exc}", file=sys.stderr)
        return 1

    models_cfg = cfg.get("models", {})
    language = args.lang or (cfg.get("default_language") or None)
    model_name = args.model or models_cfg.get("default", "base")

    if cfg.get("vad", {}).get("enabled", False):
        print(
            "whispskrid : vad.enabled=true non encore implémenté — "
            "poursuite en appui-pour-parler strict (§2.3).",
            file=sys.stderr,
        )

    from whispskrid import backend

    try:
        backend.load(
            model_name=model_name,
            device=models_cfg.get("device", "auto"),
            compute_type=models_cfg.get("compute_type", "auto"),
            beam_size=cfg.get("backend", {}).get("beam_size", 5),
        )
    except RuntimeError as exc:
        print(f"whispskrid : {exc}", file=sys.stderr)
        return 1

    session = Session(cfg, model_name, language)
    try:
        session.open()
    except Exception as exc:
        print(f"whispskrid : impossible d'ouvrir l'entrée audio : {exc}", file=sys.stderr)
        return 1

    server = None
    listener = None
    try:
        if cfg.get("control_socket", True):
            server = control.run_server(session)

        if cfg.get("hotkeys", {}).get("pynput_enabled", True):
            from whispskrid import hotkey
            listener = hotkey.start_listener(
                session, cfg.get("hotkeys", {}).get("push_to_talk", ["ctrl_r"])
            )

        print(
            f"whispskrid {__version__} — prêt "
            f"(modèle {model_name}, langue {language or 'auto'})."
        )
        session.stop_requested.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if listener is not None:
            listener.stop()
        if server is not None:
            control.close_server(server)
        session.close()

    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.version:
        print(f"whispskrid {__version__}")
        return 0

    if args.download_model is not None:
        print("whispskrid : --download-model n'est pas encore implémenté (tranche suivante, §5.2).", file=sys.stderr)
        return 1

    if args.diagnose:
        from whispskrid import diagnose

        try:
            cfg = load_config()
        except RuntimeError as exc:
            print(f"whispskrid : {exc}", file=sys.stderr)
            return 1
        return diagnose.run(cfg)

    if any(getattr(args, attr) for attr in _CLIENT_COMMANDS):
        return _run_client(args)

    return _run_resident(args)


if __name__ == "__main__":
    raise SystemExit(main())
