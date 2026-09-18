# `whispskrid --version` : une version finale n'a qu'une forme (identique sous
# Debian), affichée seule, sur toute distribution ; une préversion affiche en
# plus sa forme Debian à tilde.

from __future__ import annotations

import sys

from whispskrid import cli


def _run_version(monkeypatch, capsys, version):
    monkeypatch.setattr(sys, "argv", ["whispskrid", "--version"])
    monkeypatch.setattr(cli, "__version__", version)
    code = cli.main()
    return code, capsys.readouterr().out.strip()


def test_final_version_is_printed_once_without_a_distribution_label(monkeypatch, capsys):
    code, sortie = _run_version(monkeypatch, capsys, "1.0.1")

    assert code == 0
    assert sortie == "whispskrid 1.0.1"
    assert "Debian" not in sortie


def test_prerelease_shows_both_forms(monkeypatch, capsys):
    code, sortie = _run_version(monkeypatch, capsys, "1.0.1a1")

    assert code == 0
    assert sortie == "whispskrid 1.0.1a1 (paquet Debian 1.0.1~alpha)"
