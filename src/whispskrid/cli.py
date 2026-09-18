"""Point d'entrée CLI de WhispSkrid.

Assemblage complet de `config.py` + `backend/` +
`models.py` + `injection.py` + `audio.py` + `session.py` + `control.py` +
`hotkey.py` + `diagnose.py`. Surface CLI décrite dans `docs/whispskrid.1.md`.
`--download-model` télécharge réellement (`whispskrid.models.download_model()`).
"""

from __future__ import annotations

import argparse
import sys
import textwrap

from whispskrid import __version__, control, version_debian
from whispskrid.config import load_config
from whispskrid.i18n import installer
from whispskrid.session import Session


def _peek_lang(argv: list[str]) -> str | None:
    """Lit `-l`/`--lang` dans `argv` sans dépendre d'`argparse` — la langue
    doit être connue avant de construire le parseur, pour que l'aide
    (`--help`) elle-même s'affiche dans la bonne langue."""
    for i, arg in enumerate(argv):
        if arg in ("-l", "--lang") and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--lang="):
            return arg.split("=", 1)[1]
    return None


def _build_parser(_) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="whispskrid")
    parser.add_argument("--version", action="store_true", help=_("affiche la version et quitte"))
    parser.add_argument("-l", "--lang", metavar="LANG", default=None,
                         help=_("force la langue de l'interface et de la reconnaissance"))
    parser.add_argument("--model", metavar="NOM", default=None,
                         help=_("surcharge models.default pour cette session"))

    group = parser.add_mutually_exclusive_group()
    group_actions = [
        group.add_argument("--dictate", action="store_true", help=_("démarre la capture (session en cours)")),
        group.add_argument("--dictate-stop", action="store_true", help=_("arrête la capture, transcrit, injecte")),
        group.add_argument("--toggle", action="store_true", help=_("dictate ou dictate-stop selon l'état")),
        group.add_argument("--cancel", action="store_true", help=_("jette la capture en cours sans injecter")),
        group.add_argument("--status", action="store_true", help=_("imprime l'état de la session en cours")),
        group.add_argument("--stop", action="store_true", help=_("arrête la session persistante en cours")),
        group.add_argument("--diagnose", action="store_true", help=_("vérifie l'environnement et quitte")),
        group.add_argument("--download-model", nargs="?", const="base", default=None, metavar="NOM",
                            help=_("télécharge un modèle et quitte")),
    ]
    parser.usage = _build_usage(parser.prog, group_actions)

    return parser


def _build_usage(prog: str, group_actions: list[argparse.Action]) -> str:
    """Usage manuel replié à 80 colonnes (`CHARTE_SORTIE_CLI.md`) : le
    formateur `argparse` par défaut traite un groupe mutuellement exclusif
    comme un bloc indivisible et ne le replie jamais, quelle que soit la
    largeur de terminal détectée."""
    tokens = []
    for action in group_actions:
        flag = action.option_strings[-1]
        tokens.append(f"{flag} [{action.metavar}]" if action.nargs == "?" else flag)
    body = "[" + " | ".join(tokens) + "]"

    first_line = f"{prog} [-h] [--version] [-l LANG] [--model NOM]"
    indent = " " * (len("usage: ") + len(prog) + 1)
    wrapped = textwrap.wrap(body, width=80 - len(indent), break_long_words=False, break_on_hyphens=False)
    return "\n".join([first_line] + [indent + line for line in wrapped])


# Association attribut argparse -> commande socket.
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


def _run_resident(args: argparse.Namespace, _) -> int:
    if control.session_running():
        print(
            _("whispskrid : une session persistante tourne déjà — "
              "arrêtez-la (--stop) avant d'en ouvrir une seconde."),
            file=sys.stderr,
        )
        return 1

    try:
        cfg = load_config()
    except RuntimeError as exc:
        print(_("whispskrid : {erreur}").format(erreur=exc), file=sys.stderr)
        return 1

    models_cfg = cfg.get("models", {})
    language = args.lang or (cfg.get("default_language") or None)
    model_name = args.model or models_cfg.get("default", "base")

    if cfg.get("vad", {}).get("enabled", False):
        print(
            _("whispskrid : vad.enabled=true non encore implémenté — "
              "poursuite en appui-pour-parler strict."),
            file=sys.stderr,
        )

    from whispskrid import backend
    from whispskrid.models import MODEL_CATALOG, model_cached, resolve_models_dir

    if model_name in MODEL_CATALOG and not model_cached(model_name, resolve_models_dir()):
        # `WhisperModel()` télécharge automatiquement un modèle absent (repli
        # déjà existant) mais faster-whisper désactive sa barre de
        # progression (voir models.download_model()) : sans cette annonce,
        # un premier lancement sans modèle ressemble à un blocage silencieux
        # de plusieurs dizaines de secondes à plusieurs minutes (relevé
        # testeur — friction « pas de service d'installation »).
        _repo_id, taille_mo = MODEL_CATALOG[model_name]
        print(
            _("whispskrid : modèle « {nom} » absent, téléchargement automatique "
              "en cours (~{taille} Mo, depuis huggingface.co/Systran) — aucune "
              "barre de progression, patientez...").format(nom=model_name, taille=taille_mo)
        )

    try:
        backend.load(
            model_name=model_name,
            device=models_cfg.get("device", "auto"),
            compute_type=models_cfg.get("compute_type", "auto"),
            beam_size=cfg.get("backend", {}).get("beam_size", 5),
        )
    except RuntimeError as exc:
        print(_("whispskrid : {erreur}").format(erreur=exc), file=sys.stderr)
        return 1

    session = Session(cfg, model_name, language)
    try:
        session.open()
    except Exception as exc:
        print(_("whispskrid : impossible d'ouvrir l'entrée audio : {erreur}").format(erreur=exc), file=sys.stderr)
        return 1

    server = None
    listener = None
    try:
        if cfg.get("control_socket", True):
            server = control.run_server(session)

        if cfg.get("hotkeys", {}).get("pynput_enabled", True):
            # `pynput` est un serveur X (Xlib) : son import lève une ImportError
            # non rattrapée sur une machine sans serveur X (SSH pur, conteneur,
            # ARM headless) et faisait planter toute la session persistante, alors
            # que ce chemin est documenté « best-effort » et que le pilotage par
            # socket seul (control.py) est une voie complète à part entière.
            try:
                from whispskrid import hotkey
                listener = hotkey.start_listener(
                    session,
                    cfg.get("hotkeys", {}).get("push_to_talk", ["shift_r"]),
                    cfg.get("hotkeys", {}).get("mode", "hold"),
                    cfg.get("hotkeys", {}).get("min_hold_ms", 250),
                )
            except Exception as exc:
                print(
                    _("whispskrid : écouteur pynput indisponible ({erreur}) — "
                      "session pilotable par la socket de contrôle seule.").format(erreur=exc),
                    file=sys.stderr,
                )

        hotkeys_mode = cfg.get("hotkeys", {}).get("mode", "hold")
        if hotkeys_mode == "armed":
            if listener is None:
                print(
                    _("whispskrid : hotkeys.mode: armed exige l'écouteur pynput "
                      "(armement/désarmement exclusivement au clavier) — "
                      "indisponible ici, le mode armé ne peut pas être utilisé."),
                    file=sys.stderr,
                )
            else:
                from whispskrid.wakeword import PHRASES_PAR_LANGUE

                phrases = PHRASES_PAR_LANGUE.get(language or "fr", PHRASES_PAR_LANGUE["fr"])
                print(
                    _("whispskrid : mode armé — appuyez sur la touche pour armer "
                      "l'écoute, dites « {ouverture} » pour commencer un segment "
                      "et « {cloture} » pour le terminer ; un second appui "
                      "désarme.").format(ouverture=phrases["open"], cloture=phrases["close"])
                )

        print(
            _("whispskrid {version} — prêt (modèle {modele}, langue {langue}).").format(
                version=__version__, modele=model_name, langue=language or _("auto")
            )
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


def _run_download_model(name: str, _) -> int:
    from whispskrid.models import MODEL_CATALOG, download_model, model_cached, resolve_models_dir

    if name not in MODEL_CATALOG:
        print(
            _("whispskrid : modèle « {nom} » inconnu — modèles disponibles : {liste}.").format(
                nom=name, liste=", ".join(sorted(MODEL_CATALOG))
            ),
            file=sys.stderr,
        )
        return 1

    models_dir = resolve_models_dir()
    if model_cached(name, models_dir):
        print(_("whispskrid : modèle « {nom} » déjà présent dans {chemin}.").format(
            nom=name, chemin=models_dir
        ))
        return 0

    _repo_id, taille_mo = MODEL_CATALOG[name]
    print(
        _("whispskrid : téléchargement du modèle « {nom} » (~{taille} Mo, "
          "depuis huggingface.co/Systran) — aucune barre de progression, "
          "patientez jusqu'au message final...").format(nom=name, taille=taille_mo)
    )
    try:
        chemin = download_model(name)
    except RuntimeError as exc:
        print(_("whispskrid : échec du téléchargement : {erreur}").format(erreur=exc), file=sys.stderr)
        return 1

    print(_("whispskrid : modèle « {nom} » prêt dans {chemin}.").format(nom=name, chemin=chemin))
    return 0


def main() -> int:
    _ = installer(_peek_lang(sys.argv[1:]))

    parser = _build_parser(_)
    args = parser.parse_args()

    if args.version:
        # __version__ (ex. "1.0.1") est la forme technique du paquet Python ;
        # le paquet Debian porte la même forme (invariant
        # GOUVERNANCE/PROTOCOLE_PUBLICATION.md n°1). Les deux désignent la
        # même version : les afficher ensemble évite qu'un utilisateur
        # comparant `dpkg -l whispskrid` et `whispskrid --version` ne les
        # lise comme deux versions différentes.
        print(f"whispskrid {__version__} (paquet Debian {version_debian()})")
        return 0

    if args.download_model is not None:
        return _run_download_model(args.download_model, _)

    if args.diagnose:
        from whispskrid import diagnose

        try:
            cfg = load_config()
        except RuntimeError as exc:
            print(_("whispskrid : {erreur}").format(erreur=exc), file=sys.stderr)
            return 1
        return diagnose.run(cfg, _)

    if any(getattr(args, attr) for attr in _CLIENT_COMMANDS):
        return _run_client(args)

    return _run_resident(args, _)


if __name__ == "__main__":
    raise SystemExit(main())
