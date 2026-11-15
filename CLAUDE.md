# Popote : consignes pour Claude

Pas d'application : Notion + Claude (skills et tâches planifiées) + ce dépôt pour les scripts.

- `popote/flipp/` : client et normalisation Flipp, validés sur des réponses réelles (`tests/fixtures/`). Ne changer un format qu'avec une fixture réelle qui le prouve.
- `popote/maxi.py` : règle des imbattables (où acheter chaque article).
- `popote/semaine.py` : CLI `collecte | rabais | top`, sortie JSON compacte.
- `popote/historique.py` : base de prix CSV (`data/historique.csv`).
- `popote/epiceries.py` : verdict d'un rabais via l'historique d'épiceries.ca (appariement strict, ambiguïté → pas de verdict).
- `popote/reel.py` : extraction gratuite d'un reel (yt-dlp, ffmpeg, faster-whisper).
- `skills/` : sources des skills Claude (`capture-recette`, `menu-semaine`, `liste-epicerie`).

Règles : aucun test ne touche le réseau ; toute règle de normalisation ou d'imbattable a un test ; ne jamais committer de cookies ni de jeton ; commits courts en anglais. Dépôt public : les tâches planifiées le clonent en lecture seule et ne committent rien ; ne jamais y mettre d'adresse, de courriel ni de code postal réel.

Commandes : `pytest` (40 tests) · `python -m popote.semaine --postal H2X1Y4 rabais poulet`.
