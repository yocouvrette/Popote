---
name: menu-semaine
description: Analyse les circulaires de la semaine (Flipp), juge chaque rabais avec l'historique d'épiceries.ca et propose un menu dans la base Notion « Menus » à partir de la Banque de recettes ; pour la tâche planifiée du jeudi ou « propose le menu de la semaine ».
---

# Menu de la semaine

Utiliser pour la tâche planifiée du jeudi ou sur demande (« propose le menu », « quoi cuisiner avec les rabais »). Résultat : 6 à 8 propositions cochables dans la base Notion **Menus**, chacune avec ses rabais et leur verdict. Aucune question : en tâche planifiée personne ne répond.

## 1. Préparer

1. Dépôt public, lecture seule : `git clone --depth 1 https://github.com/yocouvrette/popote && cd popote && pip install -q httpx`. Ne rien committer.
2. Lire la page Notion **Popote · Réglages** (code postal, magasins, concurrents acceptés par notre Maxi, nombre de soupers et de dîners, difficulté max en semaine) et exporter `POSTAL_CODE`, `STORES`, `MAXI_MATCH`.
3. `python -m popote.semaine collecte` → ajoute les circulaires de la semaine à `data/historique.csv` (copie de la session ; sert aux comparaisons entre magasins).

## 2. Comparer et juger les rabais

1. **Banque de recettes** : propriétés seulement (Nom, Repas, Difficulté, Protéine, Ingrédients principaux, Statut, Note, Dernière fois cuisinée). Exclure Statut = Abandonnée.
2. Union des ingrédients principaux → `ingredients.txt` → `python -m popote.semaine rabais --fichier ingredients.txt`.
   Le script consulte épiceries.ca : chaque option peut porter un `verdict` (Prix plancher, Bon rabais, Rabais ordinaire, Faux rabais) comparant le prix de la circulaire au prix régulier et au plus bas de l'année du même produit, et sa `note` /10 en tient compte.
3. Contrôler chaque option :
   - Rejeter les formes transformées quand la recette veut l'ingrédient frais (pané, surgelé préparé, bouillon, dérivés).
   - Verdict présent : vérifier que `verdict.matched` est bien le même produit que l'article ; sinon ignorer le verdict (garder la note sans lui).
   - **Faux rabais** : ne compte pas comme un rabais. **Rabais ordinaire** : compte à moitié.
   - Sans verdict (produit frais, Super C, produit non trouvé) : utiliser la note du script (comparaison entre magasins et historique CSV).
4. Score de recette sur 100 = 100 × (Σ poids des ingrédients en vrai rabais ÷ Σ poids), poids : protéine 3, légume/fruit/laitier 1,5, reste 1 ; un rabais noté < 5 compte à moitié.
   Ajustements : −15 si cuisinée depuis moins de 14 jours, +5 Favorite, +2 jamais faite, exclue si difficulté > maximum. Les articles « Maxi — imbattables » ne comptent pas comme un magasin de plus.
5. Choisir les meilleures (défaut : 5 soupers + 2 dîners), pas plus de 2 fois la même protéine.
6. Moins de 4 recettes ≥ 35 : `python -m popote.semaine top` et inventer 2 ou 3 idées simples autour des meilleurs vrais rabais (protéine + 1–2 légumes), Type « Idée nouvelle ».

## 3. Écrire

Supprimer de **Menus** les lignes des semaines précédentes non cochées. Une ligne par proposition : Nom, Recette (relation, sauf idée), Semaine (jeudi), Type, Score, Rabais utilisés (ex. « brocoli 1,44 $ Metro → Maxi imbattable · prix plancher ; beurre 4,97 $ Maxi · bon rabais (−34 % vs régulier) »), Faux rabais évités (si utile), Coût estimé des articles en rabais (approximatif), Choisi = non, Dans la liste = non, Portions = celles de la recette. Idée nouvelle : 4–6 étapes dans le corps de la ligne.

## 4. Résumé

5 lignes : semaine, top 3 avec score, nombre de faux rabais écartés, nombre d'idées, et « Cochez vos choix dans Notion : la liste se fera automatiquement dans les 2 heures. »
