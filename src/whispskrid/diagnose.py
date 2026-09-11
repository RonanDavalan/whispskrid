"""`--diagnose` — vérifie l'environnement et quitte.

PHASE_EXECUTION, tranche distincte de l'assemblage cli.py (§7 conception) :
voir _CADRE/SPECIFICATIONS/CONCEPTION_WHISPSKRID.md §8 pour la liste des
points de contrôle et leur statut bloquant/informatif. Reprend la structure
du moule (`diagnose.py`), adaptée au backend Whisper.

Chaque point de contrôle est rendu en une ligne `ok` / `!!`. Code de sortie
0 si tout passe, non nul sinon — à une seule exception explicite (§8) : la
ligne GPU détecté mais `libcublas.so.12` introuvable est informative,
jamais bloquante, puisque `device: cpu` reste utilisable.

Catalogue gettext (§`ADDENDUM_2026-09-11_diagnose-i18n.md`) : seuls les
libellés et détails statiques passent par `_()` — chemins de fichiers,
noms d'outils techniques (`xdotool`, `wl-clipboard`...) et messages
d'exception Python/système ne sont jamais traduits, ils sont déjà en
anglais ou spécifiques à la machine quelle que soit la langue d'interface.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass
class Check:
    label: str
    ok: bool
    detail: str
    blocking: bool = True


def _render(check: Check) -> str:
    mark = "ok" if check.ok else "!!"
    return f"{mark}  {check.label} — {check.detail}"


# --------------------------------------------------------------------------- #
# Points de contrôle                                                          #
# --------------------------------------------------------------------------- #

def _check_environnement(_) -> list[Check]:
    from whispskrid import injection

    session_type = os.environ.get("XDG_SESSION_TYPE") or (
        "wayland" if os.environ.get("WAYLAND_DISPLAY")
        else "x11" if os.environ.get("DISPLAY")
        else None
    )
    checks = [
        Check(_("type de session"), session_type is not None,
              session_type or _("inconnu"), blocking=False),
    ]

    caps = injection.detect_capabilities()
    backend_name = caps["key_backend"]
    checks.append(
        Check(
            _("backend d'injection retenu"),
            backend_name is not None,
            backend_name or _("aucun (ni ydotool ni xdotool) — mode dégradé"),
        )
    )
    return checks


def _check_outils(_) -> list[Check]:
    from whispskrid import injection

    caps = injection.detect_capabilities()
    # Non bloquants : ce sont des détails par outil, pas la condition qui
    # compte. La condition bloquante réelle est « backend d'injection
    # retenu » (section Environnement) — ydotool absent avec xdotool présent
    # (ou l'inverse) reste un environnement pleinement fonctionnel.
    checks = [
        Check(_("ydotool (présence)"), injection.check_command_exists("ydotool"),
              _("présent") if injection.check_command_exists("ydotool") else _("absent"),
              blocking=False),
        Check(_("ydotoold (démon joignable)"), caps["ydotool"],
              _("joignable") if caps["ydotool"] else _("absent ou injoignable"), blocking=False),
        Check(_("xdotool (présence)"), caps["xdotool"],
              _("présent") if caps["xdotool"] else _("absent"), blocking=False),
    ]

    clipboard_tool_ok = caps["wl_copy"] and caps["wl_paste"] or caps["xclip"]
    checks.append(
        Check(
            _("presse-papiers ligne de commande (wl-clipboard ou xclip)"),
            clipboard_tool_ok,
            "wl-clipboard" if caps["wl_copy"] and caps["wl_paste"]
            else "xclip" if caps["xclip"]
            else _("aucun — repli pyperclip"),
            blocking=False,
        )
    )
    checks.append(
        Check(_("paplay (présence)"), injection.check_command_exists("paplay"),
              _("présent") if injection.check_command_exists("paplay")
              else _("absent — signal sonore désactivé"),
              blocking=False)
    )

    # Non bloquant, même raison que ydotool ci-dessus : /dev/uinput ne sert
    # qu'à ydotool, pas à xdotool.
    uinput = "/dev/uinput"
    if os.path.exists(uinput):
        rw = os.access(uinput, os.R_OK | os.W_OK)
        checks.append(Check(_("accès /dev/uinput (groupe input)"), rw,
                             _("lecture-écriture ok") if rw
                             else _("refusé — ajouter l'utilisateur au groupe input"),
                             blocking=False))
    else:
        checks.append(Check(_("accès /dev/uinput (groupe input)"), False,
                             _("périphérique absent (module uinput non chargé ?)"), blocking=False))
    return checks


def _check_backend(cfg: dict, _) -> list[Check]:
    checks: list[Check] = []

    try:
        import faster_whisper  # noqa: F401
        import ctranslate2  # noqa: F401
        import_ok = True
        import_detail = _("faster-whisper et ctranslate2 importés")
    except ImportError as exc:
        import_ok = False
        import_detail = _("échec d'import : {erreur}").format(erreur=exc)
    checks.append(Check(_("import faster-whisper / ctranslate2"), import_ok, import_detail))

    if not import_ok:
        return checks

    from whispskrid import backend

    models_cfg = cfg.get("models", {})
    requested_device = models_cfg.get("device", "auto")
    compute_type = models_cfg.get("compute_type", "auto")

    gpu_detected = backend._gpu_detected()
    checks.append(Check(_("GPU détecté"), gpu_detected,
                         _("oui") if gpu_detected else _("non"), blocking=False))

    if gpu_detected:
        cublas_ok = backend._cublas_loadable()
        checks.append(
            Check(
                _("{soname} chargeable").format(soname=backend._CUBLAS_SONAME),
                cublas_ok,
                _("oui") if cublas_ok
                else _("non — {remede}").format(remede=backend._CUBLAS_REMEDY),
                blocking=False,
            )
        )

    try:
        resolved_device = backend._resolve_device(requested_device)
        device_detail = f"{requested_device!r} -> {resolved_device!r}"
        device_ok = True
    except RuntimeError as exc:
        device_detail = str(exc)
        device_ok = False
    checks.append(Check(_("device effectif"), device_ok, device_detail))
    checks.append(Check(_("compute_type configuré"), True, compute_type, blocking=False))

    return checks


def _check_modeles(cfg: dict, _) -> list[Check]:
    from whispskrid.models import resolve_models_dir

    checks: list[Check] = []
    models_dir = resolve_models_dir()
    checks.append(Check(_("models.dir résolu"), True, str(models_dir), blocking=False))

    model_name = cfg.get("models", {}).get("default", "base")
    present = models_dir.is_dir() and any(
        model_name in p.name for p in models_dir.rglob("*") if p.is_dir()
    )
    checks.append(
        Check(
            _("modèle « {nom} » présent").format(nom=model_name),
            present,
            _("trouvé dans models.dir") if present
            else _("absent — lancer --download-model (à défaut, téléchargement à la volée non testé ici)"),
        )
    )

    if not present:
        return checks

    try:
        from faster_whisper import WhisperModel

        resolved_device = _safe_resolved_device(cfg)
        m = WhisperModel(
            model_name,
            device=resolved_device,
            compute_type=cfg.get("models", {}).get("compute_type", "auto"),
            download_root=str(models_dir),
        )
        del m
        checks.append(Check(_("chargement d'essai du modèle"), True, _("chargé puis libéré sans erreur")))
    except Exception as exc:
        checks.append(Check(_("chargement d'essai du modèle"), False, str(exc)))

    return checks


def _safe_resolved_device(cfg: dict) -> str:
    from whispskrid import backend

    requested = cfg.get("models", {}).get("device", "auto")
    try:
        return backend._resolve_device(requested)
    except RuntimeError:
        return "cpu"


def _check_entree_audio(cfg: dict, _) -> list[Check]:
    from whispskrid import audio

    try:
        p, stream = audio.open_stream(cfg)
        audio.close_stream(p, stream)
        return [Check(_("ouverture du flux de capture audio"), True, _("ouvert puis fermé sans erreur"))]
    except Exception as exc:
        return [Check(_("ouverture du flux de capture audio"), False, str(exc))]


def _check_presse_papiers(_) -> list[Check]:
    import pyperclip

    probe = "whispskrid-diagnose-probe"
    try:
        original = pyperclip.paste()
    except Exception:
        original = None

    try:
        pyperclip.copy(probe)
        roundtrip_ok = pyperclip.paste() == probe
    except Exception as exc:
        return [Check(_("presse-papiers (aller-retour)"), False, str(exc))]
    finally:
        if original is not None:
            try:
                pyperclip.copy(original)
            except Exception:
                pass

    return [Check(_("presse-papiers (aller-retour)"), roundtrip_ok,
                  _("lecture/écriture ok") if roundtrip_ok else _("le contenu relu ne correspond pas"))]


def _check_socket_controle(_) -> list[Check]:
    from whispskrid import control

    path = control.socket_path()
    parent = path.parent
    writable = parent.is_dir() and os.access(parent, os.W_OK)
    checks = [
        Check(_("socket de contrôle — répertoire accessible en écriture"), writable, str(parent)),
    ]
    running = control.session_running()
    checks.append(
        Check(_("session résidente en cours"), True,
              _("oui") if running else _("non (--diagnose peut être lancé sans session active)"),
              blocking=False)
    )
    return checks


def _check_configuration(_) -> list[Check]:
    from whispskrid.config import resolve_config_path

    try:
        path = resolve_config_path()
        return [Check(_("config.yaml effectif"), True, str(path))]
    except RuntimeError as exc:
        return [Check(_("config.yaml effectif"), False, str(exc))]


# --------------------------------------------------------------------------- #
# Point d'entrée                                                              #
# --------------------------------------------------------------------------- #

def run(cfg: dict, _) -> int:
    """Exécute tous les points de contrôle, les imprime, renvoie le code de
    sortie (0 si tout ce qui est bloquant passe, 1 sinon)."""
    sections: list[tuple[str, list[Check]]] = [
        (_("Environnement"), _check_environnement(_)),
        (_("Outils"), _check_outils(_)),
        (_("Backend"), _check_backend(cfg, _)),
        (_("Modèles"), _check_modeles(cfg, _)),
        (_("Entrée audio"), _check_entree_audio(cfg, _)),
        (_("Presse-papiers"), _check_presse_papiers(_)),
        (_("Socket de contrôle"), _check_socket_controle(_)),
        (_("Configuration"), _check_configuration(_)),
    ]

    all_blocking_ok = True
    for title, checks in sections:
        print(f"-- {title}")
        for check in checks:
            print(_render(check))
            if check.blocking and not check.ok:
                all_blocking_ok = False
        print()

    return 0 if all_blocking_ok else 1
