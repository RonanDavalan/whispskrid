# Résolution de la langue d'interface (i18n.py) et rendu réel du catalogue
# gettext — pas seulement l'absence d'exception : chaque test vérifie qu'une
# chaîne connue du catalogue source (français) devient bien la chaîne
# attendue du catalogue compilé, pour chacune des trois langues traduites.

from __future__ import annotations

import pytest

from whispskrid import i18n

_CHAINE_SOURCE = "affiche la version et quitte"


@pytest.fixture(autouse=True)
def _isolate_lang(monkeypatch):
    monkeypatch.delenv("LANG", raising=False)


class TestResoudreLangue:
    def test_lang_explicite_supportee_prioritaire(self, monkeypatch):
        monkeypatch.setenv("LANG", "de_DE.UTF-8")
        assert i18n.resoudre_langue("es") == "es"

    def test_env_lang_utilisee_si_supportee(self, monkeypatch):
        monkeypatch.setenv("LANG", "de_DE.UTF-8")
        assert i18n.resoudre_langue(None) == "de"

    def test_repli_francais_si_rien_de_supporte(self, monkeypatch):
        monkeypatch.setenv("LANG", "it_IT.UTF-8")
        assert i18n.resoudre_langue(None) == "fr"

    def test_repli_francais_si_aucune_variable(self):
        assert i18n.resoudre_langue(None) == "fr"

    def test_lang_explicite_non_supportee_repasse_par_env(self, monkeypatch):
        monkeypatch.setenv("LANG", "es_ES.UTF-8")
        assert i18n.resoudre_langue("it") == "es"


class TestInstaller:
    def test_francais_source_sans_catalogue(self):
        _ = i18n.installer("fr")
        assert _(_CHAINE_SOURCE) == _CHAINE_SOURCE

    def test_anglais_traduit(self):
        _ = i18n.installer("en")
        assert _(_CHAINE_SOURCE) == "show the version and exit"

    def test_allemand_traduit(self):
        _ = i18n.installer("de")
        assert _(_CHAINE_SOURCE) == "Version anzeigen und beenden"

    def test_espagnol_traduit(self):
        _ = i18n.installer("es")
        assert _(_CHAINE_SOURCE) == "mostrar la versión y salir"

    def test_langue_inconnue_replie_sur_source_sans_lever(self):
        # fallback=True (i18n.installer) : jamais de plantage pour un
        # catalogue absent, même appelé avec une valeur hors LANGUES_SUPPORTEES.
        _ = i18n.installer("it")
        assert _(_CHAINE_SOURCE) == _CHAINE_SOURCE

    def test_interpolation_apres_traduction(self):
        _ = i18n.installer("en")
        gabarit = _("whispskrid : {erreur}")
        assert gabarit.format(erreur="boom") == "whispskrid: boom"
