# WhispSkrid

Outil CLI de dictée **appui-pour-parler** : tenir une touche, parler,
relâcher — le texte transcrit par Whisper (`faster-whisper`) est injecté
dans la fenêtre active. Conception complète :
`_CADRE/SPECIFICATIONS/CONCEPTION_WHISPSKRID.md` (dépôt de gouvernance
séparé, non public).

État : squelette PHASE_EXECUTION, tranche 1 — pas encore de dictée
fonctionnelle.

## Comment tester / comment lancer

```bash
cd ~/git/whispskrid/whispskrid
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/whispskrid --version
```
