---
name: liste-epicerie
description: Construit ou met à jour la liste d'épicerie Notion à partir des recettes cochées dans « Menus » : quantités fusionnées, garde-manger exclu, articles par magasin avec une section « Maxi — imbattables » et la preuve à montrer. Utilisée automatiquement par la tâche de veille, ou sur « fais la liste ».
---

# Liste d'épicerie

Utiliser quand les choix du menu changent (tâche de veille) ou sur « fais la liste ». Résultat : la base Notion **Liste d'épicerie** à jour, groupée par magasin. Peut être relancée sans risque : elle ne défait jamais ce que vous avez coché.

## 0. Faut-il agir ? (mode veille)

**Menus**, semaine courante (jeudi) : il y a du travail si une ligne a Choisi = oui et Dans la liste = non, ou Choisi = non et Dans la liste = oui. Sinon, arrêter sans rien écrire ni notifier.

## 1. Lire

1. Lignes de **Menus** de la semaine avec Choisi = oui. Ouvrir chaque recette pour les quantités ; ajuster aux Portions de la ligne. Idée nouvelle : quantités raisonnables pour 4 portions.
2. **Garde-manger** : ingrédients avec Toujours = oui → exclus. Garde-manger de base (sel, huile, épices…) toujours exclu.

## 2. Fusionner

Regrouper par ingrédient canonique ; additionner les quantités de même unité (g/kg, ml/L) ; garder les recettes d'origine. Arrondir à un format achetable (« 1 kg poulet », « 2 couronnes de brocoli »).

## 3. Placer (rabais et imbattables)

Dépôt public `popote` (`git clone --depth 1 https://github.com/yocouvrette/popote && cd popote`), `pip install -q httpx`, réglages de **Popote · Réglages** exportés, puis `python -m popote.semaine rabais <ingrédients…>`. Pour chaque ingrédient, `magasin` vaut :
- **Maxi — imbattables** : meilleur prix chez un concurrent accepté, égalable chez Maxi → recopier `preuve` ; rappel : produit identique (marque, format), 4 unités max, caisse avec caissier, montrer la circulaire ou l'app.
- **Maxi** : le meilleur prix est déjà chez Maxi.
- **Autre magasin** : non égalable (marque maison du concurrent, prix membre…) → raison dans Note. Si un seul article irait dans ce magasin et que l'écart est faible, le mettre dans « Maxi » et le dire.
- **N'importe où** : pas de rabais.
Si le meilleur rabais est un **Faux rabais** selon épiceries.ca, l'écrire dans Note (« pas un vrai rabais : prix régulier habituel ») et ne pas faire de détour pour lui.

## 4. Écrire (sans écraser vos coches)

- Lignes de la semaine dont Statut = « On l'a déjà » ou « Acheté » : ne jamais les modifier ; ne pas recréer ces articles.
- Ingrédients qui ne sont plus nécessaires (recette décochée) et encore « À acheter » : supprimer.
- Nouveaux ingrédients ou quantités changées : créer ou mettre à jour. Colonnes : Article, Quantité, Magasin, Rayon (Fruits et légumes, Viandes et poissons, Produits laitiers et œufs, Boulangerie, Épicerie, Surgelés), Prix, Preuve, Note, Recettes (relation), Statut = « À acheter », Semaine.
- Lignes des semaines précédentes : supprimer.
- Dans **Menus**, mettre Dans la liste = Choisi pour chaque ligne de la semaine.

## 5. Résumé (seulement si quelque chose a changé)

Articles par magasin, total estimé des articles en rabais, rappel des imbattables (« 6 articles à faire égaler chez Maxi : préparez l'app Flipp »).
