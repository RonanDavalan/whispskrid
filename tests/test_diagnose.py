# diagnose.run() (§8 CONCEPTION_WHISPSKRID.md) : code de sortie 0 si tout ce
# qui est bloquant passe, non nul sinon — trois exceptions explicites dans la
# spec (GPU détecté mais libcublas.so.12 introuvable ; ydotool/xdotool absent
# isolément ; presse-papiers en échec sans session graphique), toutes
# informatives. Les sections réelles touchent le matériel (audio,
# presse-papiers, sockets) : ces tests doublent les sections pour exercer
# uniquement l'agrégation ok/bloquant -> code de sortie.

from __future__ import annotations

from whispskrid import diagnose

# Identité : ces tests exercent l'agrégation ok/bloquant -> code de sortie,
# pas la traduction (déjà couverte par test_i18n.py) — _() n'a rien à faire
# ici que renvoyer sa chaîne telle quelle.
_NOOP = lambda s: s  # noqa: E731


def test_all_ok_returns_zero(monkeypatch, capsys):
    monkeypatch.setattr(diagnose, "_check_environnement", lambda _: [diagnose.Check("x", True, "ok")])
    for name in (
        "_check_outils", "_check_backend", "_check_modeles",
        "_check_entree_audio", "_check_presse_papiers",
        "_check_socket_controle", "_check_configuration",
    ):
        monkeypatch.setattr(diagnose, name, lambda *a, **k: [diagnose.Check("x", True, "ok")])

    assert diagnose.run({}, _NOOP) == 0


def test_blocking_failure_returns_nonzero(monkeypatch):
    monkeypatch.setattr(diagnose, "_check_environnement", lambda _: [diagnose.Check("x", True, "ok")])
    monkeypatch.setattr(diagnose, "_check_outils", lambda _: [diagnose.Check("uinput", False, "refusé")])
    for name in (
        "_check_backend", "_check_modeles", "_check_entree_audio",
        "_check_presse_papiers", "_check_socket_controle", "_check_configuration",
    ):
        monkeypatch.setattr(diagnose, name, lambda *a, **k: [diagnose.Check("x", True, "ok")])

    assert diagnose.run({}, _NOOP) == 1


def test_non_blocking_failure_still_returns_zero(monkeypatch):
    # Cas explicite de la spec : GPU détecté mais cublas introuvable.
    monkeypatch.setattr(diagnose, "_check_environnement", lambda _: [diagnose.Check("x", True, "ok")])
    monkeypatch.setattr(
        diagnose, "_check_backend",
        lambda cfg, _: [diagnose.Check("libcublas.so.12 chargeable", False, "non", blocking=False)],
    )
    for name in (
        "_check_outils", "_check_modeles", "_check_entree_audio",
        "_check_presse_papiers", "_check_socket_controle", "_check_configuration",
    ):
        monkeypatch.setattr(diagnose, name, lambda *a, **k: [diagnose.Check("x", True, "ok")])

    assert diagnose.run({}, _NOOP) == 0


def test_render_marks_ok_and_failure():
    assert diagnose._render(diagnose.Check("x", True, "détail")) == "ok  x — détail"
    assert diagnose._render(diagnose.Check("x", False, "détail")) == "!!  x — détail"


def test_clipboard_failure_headless_is_not_blocking(monkeypatch):
    # Défaut trouvé sur une machine ARM de test (SSH/tty pur, ni DISPLAY ni WAYLAND_DISPLAY) :
    # pyperclip échoue faute de compositeur, --diagnose sortait en code 1
    # sans expliquer la cause. L'échec doit rester visible (!!) mais
    # informatif, jamais bloquant, dans ce cas précis.
    import pyperclip

    # pyperclip.copy() non mocké réexécute determine_clipboard() en interne
    # (lazy_load_stub_copy/paste partagent leur résolution) et écraserait le
    # mock de paste() : il faut aussi neutraliser copy() pour isoler le test.
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr(pyperclip, "copy", lambda text: None)
    monkeypatch.setattr(pyperclip, "paste", lambda: (_ for _ in ()).throw(
        pyperclip.PyperclipException("no mechanism")
    ))

    checks = diagnose._check_presse_papiers(_NOOP)

    assert len(checks) == 1
    assert checks[0].ok is False
    assert checks[0].blocking is False
    assert "session graphique" in checks[0].detail


def test_clipboard_failure_with_display_stays_blocking(monkeypatch):
    # Même échec, mais dans une vraie session graphique (DISPLAY présent) :
    # ce n'est plus une limitation d'environnement, l'échec reste bloquant.
    import pyperclip

    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr(pyperclip, "copy", lambda text: None)
    monkeypatch.setattr(pyperclip, "paste", lambda: (_ for _ in ()).throw(
        pyperclip.PyperclipException("no mechanism")
    ))

    checks = diagnose._check_presse_papiers(_NOOP)

    assert len(checks) == 1
    assert checks[0].ok is False
    assert checks[0].blocking is True


def test_ydotool_absent_with_xdotool_present_is_not_blocking(monkeypatch):
    # Défaut trouvé sur une machine X11 pure sans ydotool/uinput :
    # xdotool suffit comme repli fonctionnel — ydotool/uinput absents ne
    # doivent jamais, à eux seuls, faire échouer --diagnose.
    from whispskrid import injection

    monkeypatch.setattr(injection, "check_command_exists",
                         lambda cmd: cmd == "xdotool" or cmd == "paplay")
    monkeypatch.setattr(injection, "detect_capabilities", lambda: {
        "xdotool": True, "wl_copy": False, "wl_paste": False,
        "xclip": True, "ydotool": False, "key_backend": "xdotool",
    })
    monkeypatch.setattr(diagnose.os.path, "exists", lambda p: False if p == "/dev/uinput" else True)

    checks = diagnose._check_outils(_NOOP)

    blocking_failures = [c for c in checks if c.blocking and not c.ok]
    assert blocking_failures == []
