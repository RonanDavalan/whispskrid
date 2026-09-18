# Cascade de résolution de config.yaml et fusion clé à clé (config.py, voir
# _CADRE/SPECIFICATIONS/CONCEPTION_WHISPSKRID.md §6 et son docstring de
# module) : premier niveau qui résout un fichier existant gagne, les
# suivants ne sont jamais consultés ; le fichier résolu peut être partiel,
# complété clé à clé par le modèle d'usine.

from __future__ import annotations

import pytest

from whispskrid import config


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """HOME / XDG vierges, pas de WHISPSKRID_CONFIG hérité de l'environnement
    réel — sans ça, un test qui tourne sur une machine de développement (mode
    .git actif) donnerait un résultat différent en CI. Le modèle d'usine
    système est également substitué : une machine où le paquet `.deb` est
    réellement installé (`/usr/share/whispskrid/config.yaml` présent, voir
    TACHE_construire-paquet-debian.md) sans cette substitution faisait
    dépendre le résultat des tests de l'état d'installation de la machine qui
    les exécute — découvert en lançant la suite complète après
    l'ajout de wakeword.py."""
    monkeypatch.delenv(config.ENV_OVERRIDE, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(config, "_project_root", lambda: tmp_path / "repo")
    monkeypatch.setattr(config, "_system_template_path", lambda: tmp_path / "no-such-system-template.yaml")
    monkeypatch.setattr(config, "_bundled_template_path", lambda: tmp_path / "no-such-bundled-template.yaml")
    return tmp_path


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_env_override_wins(tmp_path, monkeypatch):
    target = _write(tmp_path / "elsewhere.yaml", "default_language: fr\n")
    monkeypatch.setenv(config.ENV_OVERRIDE, str(target))
    # même si un mode dev existe, l'override explicite prime.
    _write(tmp_path / "repo" / ".git" / "HEAD", "ref: refs/heads/main\n")
    _write(tmp_path / "repo" / "config" / "config.yaml", "default_language: de\n")

    assert config.resolve_config_path() == target


def test_dev_mode_wins_over_xdg(tmp_path):
    (tmp_path / "repo" / ".git").mkdir(parents=True)
    dev_cfg = _write(tmp_path / "repo" / "config" / "config.yaml", "default_language: de\n")

    assert config.resolve_config_path() == dev_cfg


def test_existing_xdg_file_wins_over_template(tmp_path, monkeypatch):
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    user_cfg = _write(xdg / "whispskrid" / "config.yaml", "default_language: es\n")
    # pas de .git -> mode dev inactif, la cascade doit s'arrêter sur le fichier XDG.
    _write(tmp_path / "repo" / "config" / "config.yaml", "default_language: de\n")

    assert config.resolve_config_path() == user_cfg


def test_first_run_seeds_xdg_from_bundled_template(tmp_path, monkeypatch):
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    _write(tmp_path / "repo" / "config" / "config.yaml", "default_language: de\n")
    # pas de .git : template embarqué utilisé comme modèle d'usine, copié vers XDG.

    resolved = config.resolve_config_path()

    expected = xdg / "whispskrid" / "config.yaml"
    assert resolved == expected
    assert expected.read_text(encoding="utf-8") == "default_language: de\n"


def test_bundled_package_template_used_when_no_dev_mode_and_no_system_template(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    bundled = _write(tmp_path / "bundled" / "config.yaml", "default_language: es\n")
    monkeypatch.setattr(config, "_bundled_template_path", lambda: bundled)
    # ni .git, ni config/config.yaml embarqué à l'ancien sens (racine du
    # dépôt) : seule la copie à côté du module doit servir de modèle
    # d'usine — cas d'un `pip install .` non éditable, où config.py est
    # copié dans site-packages/ sans le reste de l'arborescence du dépôt.

    resolved = config.resolve_config_path()

    expected = tmp_path / "xdg" / "whispskrid" / "config.yaml"
    assert resolved == expected
    assert expected.read_text(encoding="utf-8") == "default_language: es\n"


def test_bundled_config_matches_dev_template():
    # Garde-fou anti-dérive : la copie embarquée à côté du module (seule
    # source survivant à un `pip install .` non éditable) doit rester
    # identique au modèle d'usine canonique du dépôt — jamais éditée à la
    # main séparément.
    from pathlib import Path as _Path

    repo_root = _Path(__file__).resolve().parents[1]
    dev_template = (repo_root / "config" / "config.yaml").read_text(encoding="utf-8")
    bundled_template = (repo_root / "src" / "whispskrid" / "config.yaml").read_text(encoding="utf-8")

    assert bundled_template == dev_template


def test_no_config_anywhere_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    # ni .git, ni config/config.yaml embarqué, ni modèle système.

    with pytest.raises(RuntimeError):
        config.resolve_config_path()


def test_deep_merge_overrides_key_by_key_not_whole_block():
    defaults = {
        "models": {"default": "base", "device": "auto", "compute_type": "auto"},
        "capture": {"max_seconds": 300},
    }
    override = {"models": {"device": "cpu"}}

    merged = config._deep_merge(defaults, override)

    assert merged["models"] == {"default": "base", "device": "cpu", "compute_type": "auto"}
    assert merged["capture"] == {"max_seconds": 300}


def test_load_config_merges_partial_user_file_over_factory_defaults(tmp_path, monkeypatch):
    (tmp_path / "repo" / ".git").mkdir(parents=True)
    _write(
        tmp_path / "repo" / "config" / "config.yaml",
        "default_language: \"\"\n"
        "models:\n"
        "  default: base\n"
        "  device: auto\n"
        "  compute_type: auto\n"
        "capture:\n"
        "  max_seconds: 300\n",
    )
    # L'utilisateur ne force qu'une seule clé, via WHISPSKRID_CONFIG : le
    # reste doit être complété par le modèle d'usine (config/config.yaml en
    # mode dev), pas remplacé en bloc.
    override_file = _write(tmp_path / "override.yaml", "models:\n  device: cpu\n")
    monkeypatch.setenv(config.ENV_OVERRIDE, str(override_file))

    cfg = config.load_config()

    assert cfg["models"]["device"] == "cpu"
    assert cfg["models"]["default"] == "base"
    assert cfg["capture"]["max_seconds"] == 300
