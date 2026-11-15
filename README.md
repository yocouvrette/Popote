# Popote

Recettes dans Notion, rabais des circulaires analysés chaque jeudi par Claude, liste d'épicerie qui tient compte des imbattables de Maxi. Aucun serveur, aucun abonnement de plus.

| Élément | Où | Coût |
|---|---|---|
| Banque de recettes, menus, liste, garde-manger | Notion | gratuit |
| Rabais de la semaine | Flipp (endpoints publics) via `popote.semaine` | gratuit |
| Base de prix | historique d'un an d'épiceries.ca + `data/historique.csv` (circulaires de la semaine) | gratuit |
| Analyse, menu, liste | Claude : skills `menu-semaine`, `liste-epicerie` + tâches planifiées | inclus dans l'abonnement Claude |
| Import de reels | Claude : skill `capture-recette` via Apify (légende + transcription), repli `popote.reel` | ~0,015 $ US/reel, dans le crédit gratuit Apify (5 $ US/mois) |
| Verdict des rabais | `popote/epiceries.py` : historique d'un an d'épiceries.ca (prix plancher, bon, ordinaire, faux) | gratuit |

## Commandes

```bash
pip install httpx                       # (+ yt-dlp faster-whisper pour les reels)
python -m popote.semaine --postal H2X1Y4 collecte
python -m popote.semaine --postal H2X1Y4 rabais poulet brocoli "boeuf haché"
python -m popote.semaine --postal H2X1Y4 top
python -m popote.reel "https://www.tiktok.com/@…/video/…"
pip install pytest pytest-asyncio respx && pytest   # 40 tests sur des réponses Flipp réelles
```

Variables : `POSTAL_CODE`, `STORES` (défaut Maxi,IGA,Metro,Super C,Walmart,Provigo), `MAXI_MATCH` (concurrents acceptés par votre Maxi, défaut IGA,Metro,Super C,Walmart).

Usage personnel. Flipp n'a pas d'API officielle ; la politique des imbattables de Maxi peut changer et varie selon le magasin.
