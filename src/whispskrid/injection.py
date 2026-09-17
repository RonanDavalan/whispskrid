"""Injection de texte dans la fenêtre active — presse-papiers + collage.

Couche reprise du moule vosk-cli-dictation et réadaptée.
Voir _CADRE/SPECIFICATIONS/COMPATIBILITE_WAYLAND.md et
_CADRE/SPECIFICATIONS/CORRECTIF_INJECTION_COLLAGE.md pour la conception et les
raisons de chaque parade.

Écart assumé par rapport au code vosk actuel : la cascade de frappe retenue
ici est `ydotool` -> `xdotool` -> mode dégradé (COMPATIBILITE_WAYLAND.md §2-3),
sans `wtype` — décision figée dans la spécification WhispSkrid, que le fichier
`system_control.py` de vosk a depuis fait évoluer (ajout de `wtype`) sans que
cela ait été reporté ici. La spécification fait foi (Instruction n°4 du
protocole de démarrage).

Le cœur d'interaction vosk (bascule DICTÉE/ÉCOUTE, commandes vocales,
`press_key`/BackSpace) est retiré : WhispSkrid n'injecte que le texte
transcrit et joue un signal sonore court.
"""

from __future__ import annotations

import atexit
import shutil
import subprocess
import sys
import time

import pyperclip

# Keycodes physiques Linux (repli ydotool uniquement — dépendants de la
# disposition clavier). Vérifiés dans /usr/include/linux/input-event-codes.h.
KEYCODE = {"ctrl": 29, "shift": 42, "v": 47}

_KEY_TIMEOUT = 2.0
_CLIP_TIMEOUT = 2.0
_SOUND_TIMEOUT = 5.0

_cfg: dict = {}
_caps: dict | None = None
_last_warn = 0.0

# Restauration différée du presse-papiers (clipboard.defer_restore) : on
# mémorise le presse-papiers d'origine (celui d'avant la première dictée de la
# session) et on le restaure une seule fois — voir CORRECTIF_INJECTION_COLLAGE.md §2.
_deferred_clip = {"pending": False, "value": None}
_deferred_atexit_registered = False

_RESTORE_POLL_S = 0.025  # granularité de la fenêtre de restauration adaptative


# --------------------------------------------------------------------------- #
# Configuration                                                              #
# --------------------------------------------------------------------------- #

def configure(cfg: dict) -> None:
    """Enregistre la configuration effective (issue de load_config()).

    Réinitialise les capacités détectées : appelé une fois au démarrage de la
    session persistante, avant tout appel à type_text()/play_sound().
    """
    global _cfg, _caps
    _cfg = cfg
    _caps = None


def _get(section: str, key: str, default):
    return _cfg.get(section, {}).get(key, default)


# --------------------------------------------------------------------------- #
# Détection de l'environnement                                                #
# --------------------------------------------------------------------------- #

def check_command_exists(command: str) -> bool:
    """Vrai si la commande externe est présente dans le PATH."""
    return shutil.which(command) is not None


def _ydotool_ready() -> bool:
    """ydotool présent ET démon joignable (test non destructif `key 0:0`)."""
    if not check_command_exists("ydotool"):
        return False
    try:
        subprocess.run(
            ["ydotool", "key", "0:0"], check=True,
            capture_output=True, text=True, timeout=_KEY_TIMEOUT,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


def _detect_caps() -> dict:
    global _caps
    if _caps is not None:
        return _caps
    caps = {
        "xdotool": check_command_exists("xdotool"),
        "wl_copy": check_command_exists("wl-copy"),
        "wl_paste": check_command_exists("wl-paste"),
        "xclip": check_command_exists("xclip"),
        "ydotool": _ydotool_ready(),
    }
    # Cascade retenue (COMPATIBILITE_WAYLAND.md §2) : ydotool -> xdotool -> aucun.
    if caps["ydotool"]:
        caps["key_backend"] = "ydotool"
    elif caps["xdotool"]:
        caps["key_backend"] = "xdotool"
    else:
        caps["key_backend"] = None
    _caps = caps
    return _caps


def injection_backend_available() -> bool:
    """Vrai si au moins un backend de frappe est utilisable."""
    return _detect_caps()["key_backend"] is not None


def detect_capabilities() -> dict:
    """Point d'entrée public de `_detect_caps()`, pour `--diagnose` (§8) : ne
    nécessite pas `configure()` au préalable, aucune de ces sondes ne lit
    `_cfg`."""
    return _detect_caps()


# --------------------------------------------------------------------------- #
# Utilitaires                                                                 #
# --------------------------------------------------------------------------- #

def _warn(msg: str) -> None:
    """Avertissement throttlé (au plus un par seconde) sur stderr."""
    global _last_warn
    now = time.monotonic()
    if now - _last_warn >= 1.0:
        _last_warn = now
        print(msg, file=sys.stderr)


def _run(cmd: list[str], timeout: float, stdin_text: str | None = None):
    """Lance un sous-processus borné. Retourne (ok, stdout). Ne lève jamais."""
    try:
        r = subprocess.run(
            cmd, input=stdin_text, capture_output=True, text=True,
            timeout=timeout, check=True,
        )
        return True, r.stdout
    except subprocess.TimeoutExpired:
        _warn(f"« {cmd[0]} » a expiré (timeout) ; repli.")
        return False, ""
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False, ""


def _parse_combo(combo: str) -> tuple[list[str], str]:
    """'ctrl+shift+v' -> (['ctrl', 'shift'], 'v')."""
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    if not parts:
        return [], "v"
    return parts[:-1], parts[-1]


# --------------------------------------------------------------------------- #
# Presse-papiers                                                              #
# --------------------------------------------------------------------------- #

def _clipboard_is_text() -> bool:
    """Faux si le presse-papiers tient un contenu non textuel (image, fichier)."""
    caps = _detect_caps()
    if caps["wl_paste"]:
        ok, out = _run(["wl-paste", "--list-types"], _CLIP_TIMEOUT)
        if ok:
            return any(t.startswith("text/") or "STRING" in t for t in out.split())
        return True  # presse-papiers vide -> wl-paste échoue ; rien à préserver
    if caps["xclip"]:
        ok, out = _run(
            ["xclip", "-selection", "clipboard", "-o", "-t", "TARGETS"],
            _CLIP_TIMEOUT,
        )
        if ok:
            return any(
                t in out for t in ("UTF8_STRING", "STRING", "text/plain", "TEXT")
            )
        return True
    return True  # pas d'outil de sonde : on suppose du texte


def _clipboard_get() -> str:
    caps = _detect_caps()
    if caps["wl_paste"]:
        ok, out = _run(["wl-paste", "--no-newline"], _CLIP_TIMEOUT)
        return out if ok else ""
    if caps["xclip"]:
        ok, out = _run(["xclip", "-selection", "clipboard", "-o"], _CLIP_TIMEOUT)
        return out if ok else ""
    try:
        return pyperclip.paste()
    except Exception:
        return ""


def _wl_copy(text: str) -> bool:
    """`wl-copy` en fire-and-forget (démon détenteur de la sélection)."""
    try:
        p = subprocess.Popen(
            ["wl-copy"], stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        p.communicate(input=text.encode("utf-8"), timeout=_CLIP_TIMEOUT)
        return p.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


def _clipboard_set(text: str) -> bool:
    caps = _detect_caps()
    if caps["wl_copy"]:
        return _wl_copy(text)
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def _clipboard_confirm(text: str, timeout_ms: int) -> bool:
    """Attend que le presse-papiers contienne réellement `text`."""
    deadline = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < deadline:
        if _clipboard_get() == text:
            return True
        time.sleep(0.02)
    return _clipboard_get() == text


# --------------------------------------------------------------------------- #
# Frappe                                                                      #
# --------------------------------------------------------------------------- #

def get_active_window_id() -> str | None:
    """ID de la fenêtre active via xdotool (chemin X11 uniquement)."""
    ok, out = _run(["xdotool", "getactivewindow"], _KEY_TIMEOUT)
    return out.strip() if ok and out.strip() else None


def _active_window_class_x11() -> str:
    """Classe WM de la fenêtre active, via `xprop` (`WM_CLASS`).

    `xdotool getwindowclassname` n'existe pas dans la version packagée Debian
    (3.20160805.1, sans sous-commande de classe) : la détection de terminal
    échouait toujours silencieusement, et le combo de collage générique
    (`ctrl+v`) partait à la place du combo terminal (`ctrl+shift+v`),
    invisible dans un shell (`ctrl+v` y est lié à l'insertion verbatim).
    `xprop` fait partie du même paquet
    `x11-utils` que `xdotool` sur une machine X11.
    """
    wid = get_active_window_id()
    if not wid:
        return ""
    ok, out = _run(["xprop", "-id", wid, "WM_CLASS"], _KEY_TIMEOUT)
    if not ok:
        return ""
    _, _, value = out.partition("=")
    return value.replace('"', "").strip()


def _paste_combo_for_target() -> str:
    """Combo de collage : Ctrl+Shift+V si la fenêtre active est un terminal.

    Résolution de fenêtre disponible seulement côté xdotool/xprop (paquet
    x11-utils) — ydotool n'a aucune notion de fenêtre ciblée
    (COMPATIBILITE_WAYLAND.md §1). Mais cette disponibilité est indépendante
    du backend *retenu pour l'envoi des touches* : `key_backend` favorise
    ydotool dès qu'il est présent (COMPATIBILITE_WAYLAND.md §2), y compris sur
    une machine X11/XWayland où xdotool/xprop fonctionnent très bien pour la
    seule détection de fenêtre.

    La condition testait `key_backend == "xdotool"`, donc se désactivait
    silencieusement sur toute machine où `ydotool`/`ydotoold` sont présents et
    prioritaires — le cas le plus courant sur une machine WhispSkrid pensée
    Wayland-first. Le combo générique (`ctrl+v`) partait alors systématiquement
    dans un terminal, sans effet visible (`ctrl+v` y est lié à l'insertion
    verbatim par `readline`) : capture réelle 4 langues sans aucun texte
    collé, presse-papiers pourtant correct. Condition changée pour tester la
    présence de l'outillage de détection (`caps["xdotool"]`), plus le choix du
    backend d'envoi.
    """
    default = _get("injection", "paste_combo", "ctrl+v")
    term = _get("injection", "terminal_paste_combo", "ctrl+shift+v")
    classes = _get(
        "injection", "terminal_window_classes",
        ["konsole", "gnome-terminal-server", "xterm", "st",
         "alacritty", "kitty", "foot"],
    )
    if _detect_caps()["xdotool"]:
        cls = _active_window_class_x11().lower()
        if cls and any(c.lower() in cls for c in classes):
            return term
    return default


def _send_combo_ydotool(mods: list[str], key: str) -> bool:
    kc = dict(KEYCODE)
    kc.update(_get("injection", "ydotool_keycodes", {}))
    names = list(mods) + [key]
    if any(n not in kc for n in names):
        return False
    events = [f"{kc[n]}:1" for n in names] + [f"{kc[n]}:0" for n in reversed(names)]
    ok, _out = _run(["ydotool", "key"] + events, _KEY_TIMEOUT)
    return ok


def _send_combo_xdotool(combo: str) -> bool:
    wid = get_active_window_id()
    if not wid:
        return False
    ok, _out = _run(["xdotool", "key", "--window", wid, combo], _KEY_TIMEOUT)
    return ok


def _send_paste(combo: str) -> bool:
    backend = _detect_caps()["key_backend"]
    if backend == "ydotool":
        mods, key = _parse_combo(combo)
        return _send_combo_ydotool(mods, key)
    if backend == "xdotool":
        return _send_combo_xdotool(combo)
    return False


# --------------------------------------------------------------------------- #
# Restauration du presse-papiers après collage                                #
# --------------------------------------------------------------------------- #

def _settle_before_restore(text: str, budget_s: float) -> bool:
    """Fenêtre de restauration adaptative et bornée (CORRECTIF_INJECTION_COLLAGE.md §2.1).

    Attend jusqu'à `budget_s`, par courtes attentes successives, tant que
    le presse-papiers contient toujours `text`. Retourne False (abandon de
    la restauration) dès qu'un autre propriétaire l'a déjà remplacé.
    """
    deadline = time.monotonic() + budget_s
    while time.monotonic() < deadline:
        time.sleep(_RESTORE_POLL_S)
        if _clipboard_get() != text:
            return False
    return True


def _register_deferred_atexit() -> None:
    global _deferred_atexit_registered
    if not _deferred_atexit_registered:
        _deferred_atexit_registered = True
        atexit.register(flush_deferred_clipboard)


def flush_deferred_clipboard() -> None:
    """Restaure le presse-papiers mémorisé en mode `clipboard.defer_restore`.

    Idempotente : sans restauration en attente, ne fait rien. À appeler en fin
    de session persistante, et couverte par `atexit` pour une sortie brutale.
    """
    if not _deferred_clip["pending"]:
        return
    saved = _deferred_clip["value"]
    _deferred_clip["pending"] = False
    _deferred_clip["value"] = None
    if saved is not None:
        _clipboard_set(saved)


# --------------------------------------------------------------------------- #
# API publique                                                               #
# --------------------------------------------------------------------------- #

def type_text(text: str) -> bool:
    """Injecte `text` via presse-papiers + collage. False -> mode dégradé.

    Mécanisme et parades : CORRECTIF_INJECTION_COLLAGE.md §2. Appelée une fois
    par transcription livrée (une par relâche de la touche appui-pour-parler).
    """
    if not text:
        return False
    if _detect_caps()["key_backend"] is None:
        _warn(
            "aucun backend de frappe disponible (ni ydotool ni xdotool) — "
            "mode dégradé."
        )
        return False

    want_restore = _get("clipboard", "restore", True)
    defer_restore = _get("clipboard", "defer_restore", False)
    restore_delay = _get("clipboard", "restore_delay_ms", 400) / 1000.0
    confirm_ms = _get("clipboard", "confirm_timeout_ms", 500)

    saved = None
    if want_restore:
        if _clipboard_is_text():
            saved = _clipboard_get()
        else:
            _warn("le presse-papiers contient du contenu non textuel ; il ne sera pas restauré.")

    if not _clipboard_set(text):
        _warn("impossible d'écrire dans le presse-papiers.")
        return False

    if not _clipboard_confirm(text, confirm_ms):
        _warn("le presse-papiers n'a pas pris le texte à temps ; collage annulé.")
        if saved is not None:
            _clipboard_set(saved)
        return False

    ok = _send_paste(_paste_combo_for_target())

    if saved is None:
        return ok

    if defer_restore:
        # Pas de restauration en ligne : le presse-papiers d'origine (celui
        # d'avant la première dictée de la session) est remis en fin de
        # session par flush_deferred_clipboard().
        if not _deferred_clip["pending"]:
            _deferred_clip["pending"] = True
            _deferred_clip["value"] = saved
            _register_deferred_atexit()
        return ok

    if ok:
        if _settle_before_restore(text, restore_delay):
            _clipboard_set(saved)
    else:
        # Rien n'a été collé : restauration immédiate, sans fenêtre d'attente.
        _clipboard_set(saved)
    return ok


def play_sound() -> None:
    """Signal sonore court confirmant le début d'une capture (§2.1 conception)."""
    sound_file = _cfg.get("sound_file")
    if not sound_file or not check_command_exists("paplay"):
        return
    _run(["paplay", sound_file], _SOUND_TIMEOUT)
