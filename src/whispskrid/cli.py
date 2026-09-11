"""Point d'entrée CLI de WhispSkrid.

PHASE_EXECUTION, tranche 6 : assemblage complet de `config.py` + `backend/` +
`models.py` + `injection.py` + `audio.py` + `session.py` + `control.py` +
`hotkey.py`. Surface CLI conforme à
_CADRE/SPECIFICATIONS/CONCEPTION_WHISPSKRID.md §7, à l'exception de
`--diagnose` et `--download-model` : le 10_ROADMAP.md les distingue
explicitement de cette tranche d'assemblage et aucune des deux fonctions
qu'ils appelleraient n'est encore écrite (points de contrôle diagnose,
téléchargement de modèle) — stubs explicites ci-dessous, pas un silence.
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


def _run_client(args: argparse.Namespace) -> int:
    for attr, command in _CLIENT_COMMANDS.items():
        if getattr(args, attr):
            ok, reply = control.send_control_command(command)
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
        print("whispskrid : --diagnose n'est pas encore implémenté (tranche suivante, §8).", file=sys.stderr)
        return 1

    if any(getattr(args, attr) for attr in _CLIENT_COMMANDS):
        return _run_client(args)

    return _run_resident(args)


if __name__ == "__main__":
    raise SystemExit(main())
