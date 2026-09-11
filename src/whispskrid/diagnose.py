"""`--diagnose` — vérifie l'environnement et quitte.

PHASE_EXECUTION, tranche distincte de l'assemblage cli.py (§7 conception) :
voir _CADRE/SPECIFICATIONS/CONCEPTION_WHISPSKRID.md §8 pour la liste des
points de contrôle et leur statut bloquant/informatif. Reprend la structure
du moule (`diagnose.py`), adaptée au backend Whisper.

Chaque point de contrôle est rendu en une ligne `ok` / `!!`. Code de sortie
0 si tout passe, non nul sinon — à une seule exception explicite (§8) : la
ligne GPU détecté mais `libcublas.so.12` introuvable est informative,
jamais bloquante, puisque `device: cpu` reste utilisable.
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

def _check_environnement() -> list[Check]:
    from whispskrid import injection

    session_type = os.environ.get("XDG_SESSION_TYPE") or (
        "wayland" if os.environ.get("WAYLAND_DISPLAY")
        else "x11" if os.environ.get("DISPLAY")
        else "inconnu"
    )
    checks = [
        Check("type de session", session_type != "inconnu", session_type, blocking=False),
    ]

    caps = injection.detect_capabilities()
    backend_name = caps["key_backend"]
    checks.append(
        Check(
            "backend d'injection retenu",
            backend_name is not None,
            backend_name or "aucun (ni ydotool ni xdotool) — mode dégradé",
        )
    )
    return checks


def _check_outils() -> list[Check]:
    from whispskrid import injection

    caps = injection.detect_capabilities()
    # Non bloquants : ce sont des détails par outil, pas la condition qui
    # compte. La condition bloquante réelle est « backend d'injection
    # retenu » (section Environnement) — ydotool absent avec xdotool présent
    # (ou l'inverse) reste un environnement pleinement fonctionnel.
    checks = [
        Check("ydotool (présence)", injection.check_command_exists("ydotool"),
              "présent" if injection.check_command_exists("ydotool") else "absent", blocking=False),
        Check("ydotoold (démon joignable)", caps["ydotool"],
              "joignable" if caps["ydotool"] else "absent ou injoignable", blocking=False),
        Check("xdotool (présence)", caps["xdotool"],
              "présent" if caps["xdotool"] else "absent", blocking=False),
    ]

    clipboard_tool_ok = caps["wl_copy"] and caps["wl_paste"] or caps["xclip"]
    checks.append(
        Check(
            "presse-papiers ligne de commande (wl-clipboard ou xclip)",
            clipboard_tool_ok,
            "wl-clipboard" if caps["wl_copy"] and caps["wl_paste"]
            else "xclip" if caps["xclip"]
            else "aucun — repli pyperclip",
            blocking=False,
        )
    )
    checks.append(
        Check("paplay (présence)", injection.check_command_exists("paplay"),
              "présent" if injection.check_command_exists("paplay") else "absent — signal sonore désactivé",
              blocking=False)
    )

    # Non bloquant, même raison que ydotool ci-dessus : /dev/uinput ne sert
    # qu'à ydotool, pas à xdotool.
    uinput = "/dev/uinput"
    if os.path.exists(uinput):
        rw = os.access(uinput, os.R_OK | os.W_OK)
        checks.append(Check("accès /dev/uinput (groupe input)", rw,
                             "lecture-écriture ok" if rw else "refusé — ajouter l'utilisateur au groupe input",
                             blocking=False))
    else:
        checks.append(Check("accès /dev/uinput (groupe input)", False,
                             "périphérique absent (module uinput non chargé ?)", blocking=False))
    return checks


def _check_backend(cfg: dict) -> list[Check]:
    checks: list[Check] = []

    try:
        import faster_whisper  # noqa: F401
        import ctranslate2  # noqa: F401
        import_ok = True
        import_detail = "faster-whisper et ctranslate2 importés"
    except ImportError as exc:
        import_ok = False
        import_detail = f"échec d'import : {exc}"
    checks.append(Check("import faster-whisper / ctranslate2", import_ok, import_detail))

    if not import_ok:
        return checks

    from whispskrid import backend

    models_cfg = cfg.get("models", {})
    requested_device = models_cfg.get("device", "auto")
    compute_type = models_cfg.get("compute_type", "auto")

    gpu_detected = backend._gpu_detected()
    checks.append(Check("GPU détecté", gpu_detected, "oui" if gpu_detected else "non", blocking=False))

    if gpu_detected:
        cublas_ok = backend._cublas_loadable()
        checks.append(
            Check(
                f"{backend._CUBLAS_SONAME} chargeable",
                cublas_ok,
                "oui" if cublas_ok else f"non — {backend._CUBLAS_REMEDY}",
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
    checks.append(Check("device effectif", device_ok, device_detail))
    checks.append(Check("compute_type configuré", True, compute_type, blocking=False))

    return checks


def _check_modeles(cfg: dict) -> list[Check]:
    from whispskrid.models import resolve_models_dir

    checks: list[Check] = []
    models_dir = resolve_models_dir()
    checks.append(Check("models.dir résolu", True, str(models_dir), blocking=False))

    model_name = cfg.get("models", {}).get("default", "base")
    present = models_dir.is_dir() and any(
        model_name in p.name for p in models_dir.rglob("*") if p.is_dir()
    )
    checks.append(
        Check(
            f"modèle « {model_name} » présent",
            present,
            "trouvé dans models.dir" if present
            else "absent — lancer --download-model (à défaut, téléchargement à la volée non testé ici)",
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
        checks.append(Check("chargement d'essai du modèle", True, "chargé puis libéré sans erreur"))
    except Exception as exc:
        checks.append(Check("chargement d'essai du modèle", False, str(exc)))

    return checks


def _safe_resolved_device(cfg: dict) -> str:
    from whispskrid import backend

    requested = cfg.get("models", {}).get("device", "auto")
    try:
        return backend._resolve_device(requested)
    except RuntimeError:
        return "cpu"


def _check_entree_audio(cfg: dict) -> list[Check]:
    from whispskrid import audio

    try:
        p, stream = audio.open_stream(cfg)
        audio.close_stream(p, stream)
        return [Check("ouverture du flux de capture audio", True, "ouvert puis fermé sans erreur")]
    except Exception as exc:
        return [Check("ouverture du flux de capture audio", False, str(exc))]


def _check_presse_papiers() -> list[Check]:
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
        return [Check("presse-papiers (aller-retour)", False, str(exc))]
    finally:
        if original is not None:
            try:
                pyperclip.copy(original)
            except Exception:
                pass

    return [Check("presse-papiers (aller-retour)", roundtrip_ok,
                  "lecture/écriture ok" if roundtrip_ok else "le contenu relu ne correspond pas")]


def _check_socket_controle() -> list[Check]:
    from whispskrid import control

    path = control.socket_path()
    parent = path.parent
    writable = parent.is_dir() and os.access(parent, os.W_OK)
    checks = [
        Check("socket de contrôle — répertoire accessible en écriture", writable, str(parent)),
    ]
    running = control.session_running()
    checks.append(
        Check("session résidente en cours", True,
              "oui" if running else "non (--diagnose peut être lancé sans session active)",
              blocking=False)
    )
    return checks


def _check_configuration() -> list[Check]:
    from whispskrid.config import resolve_config_path

    try:
        path = resolve_config_path()
        return [Check("config.yaml effectif", True, str(path))]
    except RuntimeError as exc:
        return [Check("config.yaml effectif", False, str(exc))]


# --------------------------------------------------------------------------- #
# Point d'entrée                                                              #
# --------------------------------------------------------------------------- #

def run(cfg: dict) -> int:
    """Exécute tous les points de contrôle, les imprime, renvoie le code de
    sortie (0 si tout ce qui est bloquant passe, 1 sinon)."""
    sections: list[tuple[str, list[Check]]] = [
        ("Environnement", _check_environnement()),
        ("Outils", _check_outils()),
        ("Backend", _check_backend(cfg)),
        ("Modèles", _check_modeles(cfg)),
        ("Entrée audio", _check_entree_audio(cfg)),
        ("Presse-papiers", _check_presse_papiers()),
        ("Socket de contrôle", _check_socket_controle()),
        ("Configuration", _check_configuration()),
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
