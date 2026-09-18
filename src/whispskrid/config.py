"""Chargement de `config.yaml` — cascade XDG et fusion clé à clé.

Cascade de résolution du fichier : le premier niveau qui résout un fichier existant
gagne, les suivants ne sont jamais consultés.

1. `$WHISPSKRID_CONFIG` — surcharge explicite, aucune création automatique.
2. Mode développement — `<racine>/config/config.yaml`, actif si
   `<racine>/.git` existe et que le fichier existe. Modifié en place.
3. Fichier utilisateur XDG — `$XDG_CONFIG_HOME/whispskrid/config.yaml`
   (défaut `~/.config/whispskrid/config.yaml`), créé automatiquement au
   premier lancement par copie du modèle d'usine.
4. Modèle d'usine — `/usr/share/whispskrid/config.yaml` (paquet Debian),
   sinon `<racine>/config/config.yaml` (checkout git sans `.git` déréférencé),
   sinon la copie embarquée à côté du module `config.py` lui-même — seule
   celle-ci survit à `pip install .` en mode non éditable, où le module est
   copié dans `site-packages/` et perd son chemin relatif vers la racine du
   dépôt (couvre l'installation depuis le tarball de sources).

Le fichier résolu peut être partiel : les clés absentes sont complétées par
les valeurs du modèle d'usine, fusion clé à clé (la cascade XDG permet à l'utilisateur de
surcharger clé à clé), jamais un remplacement de bloc entier.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import yaml

ENV_OVERRIDE = "WHISPSKRID_CONFIG"


def _project_root() -> Path:
    # config.py -> whispskrid/ (package) -> src/ -> racine du dépôt de code
    return Path(__file__).resolve().parents[2]


def _dev_mode_path() -> Path:
    return _project_root() / "config" / "config.yaml"


def _system_template_path() -> Path:
    return Path("/usr/share/whispskrid/config.yaml")


def _bundled_template_path() -> Path:
    return Path(__file__).resolve().parent / "config.yaml"


def _factory_template_path() -> Path | None:
    system = _system_template_path()
    if system.is_file():
        return system
    embedded = _dev_mode_path()
    if embedded.is_file():
        return embedded
    bundled = _bundled_template_path()
    return bundled if bundled.is_file() else None


def _xdg_user_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(xdg_config_home) / "whispskrid" / "config.yaml"


def resolve_config_path() -> Path:
    """Applique la cascade et renvoie le chemin du fichier à charger. Crée le
    fichier utilisateur XDG par copie du modèle d'usine s'il n'existe pas
    encore et qu'aucun niveau prioritaire n'est actif."""
    override = os.environ.get(ENV_OVERRIDE)
    if override:
        return Path(override)

    dev_path = _dev_mode_path()
    if (_project_root() / ".git").exists() and dev_path.is_file():
        return dev_path

    user_path = _xdg_user_path()
    if user_path.is_file():
        return user_path

    template = _factory_template_path()
    if template is None:
        raise RuntimeError(
            "aucun modèle d'usine de config.yaml trouvé "
            "(/usr/share/whispskrid/config.yaml, config/config.yaml ni "
            "copie embarquée du package) — installation incomplète."
        )
    user_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, user_path)
    print(f"whispskrid : fichier de configuration créé — {user_path}")
    return user_path


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> dict[str, Any]:
    """Résout et charge la configuration effective : fichier résolu par la
    cascade, fusionné clé à clé sur les valeurs du modèle d'usine. Lève une
    exception claire si le fichier résolu (notamment une surcharge
    `$WHISPSKRID_CONFIG` pointant dans le vide) n'existe pas."""
    path = resolve_config_path()
    if not path.is_file():
        raise RuntimeError(f"fichier de configuration introuvable : {path}")

    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    template = _factory_template_path()
    if template is None:
        defaults: dict[str, Any] = {}
    elif template == path:
        defaults = raw  # le fichier résolu EST le modèle d'usine
    else:
        with template.open(encoding="utf-8") as f:
            defaults = yaml.safe_load(f) or {}

    return _deep_merge(defaults, raw)
