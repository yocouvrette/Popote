---
name: capture-recette
description: Ajoute une recette à la base Notion « Banque de recettes » depuis un reel Instagram/TikTok (lien partagé, Boîte de réception Notion), des captures ou du texte ; lit légende et transcription via Apify, classe par repas et difficulté.
---

# Capture de recette → Notion

Utiliser dès qu'un reel, un lien de recette ou des captures sont envoyés, ou pour « traite la boîte de réception ». Objectif : une fiche complète dans **Banque de recettes**, sans question inutile. Au plus une question, seulement si la source est vide.

## 1. Sources, dans cet ordre

1. **Texte ou captures joints** : les lire attentivement (légende, liste à l'écran, photo du plat).
2. **Lien Instagram, connecteur Apify branché** (nettoyer le lien : garder `https://www.instagram.com/reel/<code>/`, retirer `?igsh=…`) :
   a. `call-actor` sur `steadyfetch/instagram-reel-transcript-scraper` avec `{"reelUrls": ["<lien>"], "includeOnScreenText": true, "maxItems": 1}` (≈ 0,015 $ US ; non facturé si le reel est privé ou introuvable), puis `get-dataset-items`. Une seule ligne donne `caption` (légende), `transcript` (ce qui est dit), `onScreenText` (texte affiché), `ownerUsername`, `thumbnailUrl`. Ignorer la ligne `_summary`.
   b. Si `status` n'est pas « transcribed » et que la légende manque : `apify/instagram-scraper` avec `{"directUrls": ["<lien>"], "resultsType": "posts", "resultsLimit": 1}` (≈ 0,003 $ US) pour récupérer au moins `caption`.
   Vérifier le schéma d'entrée avec `fetch-actor-details` si un appel est refusé. Ne lancer que ces deux acteurs.
3. **Lien TikTok, YouTube ou Apify indisponible** : dépôt public `popote` (`git clone --depth 1 https://github.com/yocouvrette/popote` s'il manque), `pip install -q yt-dlp faster-whisper httpx && python -m popote.reel "<lien>"` → légende, transcription gratuite, images dans `out/reel/` (les lire avec Read).
4. **Site de recettes** : WebFetch de la page.
5. **Rien n'a marché** : demander « Envoie-moi une capture de la légende dépliée (ou de la liste d'ingrédients) ». Ne jamais inventer une recette à partir du titre ou de la miniature.

## 2. Rédiger

- **Titre** court en français (traduire si besoin). **Créateur** @compte. **Portions**, **temps** préparation + cuisson.
- **Ingrédients** : `quantité unité ingrédient, précision`, unités métriques (original entre parenthèses si converti), groupés par composante si utile. Quantité absente → estimée, marquée « (estimé) ».
- **Étapes** réécrites à l'impératif, une action principale par étape, avec temps et température.
- **Ingrédients principaux** (clé de comparaison avec les circulaires) : français, singulier, sans marque ni préparation, ce qu'on taperait dans Flipp (`poulet`, `boeuf haché`, `brocoli`, `riz`, `tomate en conserve`, `pomme de terre`). Exclure le garde-manger : sel, poivre, huiles, épices et herbes séchées, farine, sucre, cassonade, miel, vinaigres, fécule, poudre à pâte, bouillon en poudre, sauce soya, moutarde, ketchup, mayonnaise, eau (sauf ingrédient vedette). Maximum 10.

## 3. Classer

- **Repas** (une ou plusieurs) : Déjeuner (œufs, gruau, crêpes, smoothie) · Dîner (se transporte ou se réchauffe : bols, wraps, salades-repas, soupes-repas) · Souper (plat principal chaud) · Collation · Dessert. Dans le doute Dîner + Souper.
- **Protéine** : Poulet, Bœuf, Porc, Dinde, Poisson, Fruits de mer, Tofu/légumineuses, Œufs, Aucune.
- **Difficulté** = somme de 4 critères notés 0–2 : étapes (1–5 / 6–10 / 11+), temps actif (≤ 20 / 21–45 / > 45 min), technique (base / intermédiaire : émulsion, pâte, friture, caramel / avancée : laminage, tempérage, sous-vide), composantes en parallèle (1 / 2 / 3+). 0–2 Facile, 3–5 Moyen, 6–8 Difficile.
- **Tags** seulement s'ils s'appliquent : Végé, Protéiné, Meal prep, Une casserole, Air fryer, Mijoteuse, BBQ, Rapide (≤ 30 min), Économique, Congélation OK.

## 4. Écrire dans Notion

Base **Banque de recettes** : `collection://41952de0-257f-8128-a2ef-000b3030eaab` (sinon chercher par nom). Propriétés : Nom, Repas, Difficulté, Nb d'étapes, Temps total (min), Portions, Protéine, Ingrédients principaux (multi), Tags, Statut (= « À essayer »), Source (URL), Plateforme, Créateur, Ajoutée par.
Doublon (même lien ou titre très proche) → ne pas recréer ; en conversation, montrer la fiche existante.
Icône de la page : un émoji du plat (🍗, 🍝, 🥗, 🍛, 🌮…). Couverture : aucune (les images Instagram expirent).
Corps de page (Notion Markdown), pensé pour cuisiner avec le téléphone :
```
<callout icon="⏱️" color="gray_bg">
<b>35 min</b> · 4 portions · Moyen (étapes 1 + temps 1 + technique 0 + composantes 1 = 3)
</callout>

## 🧾 Ingrédients

### Poulet
- [ ] 500 g cuisses de poulet désossées, en cubes
- [ ] 15 ml (1 c. à soupe) sauce soya

## 👩‍🍳 Étapes

1. <b>Préparer le riz.</b> Rincer le riz et le cuire 15 min.
2. …

<toggle heading="h2">
💡 Astuces et notes

- Substitutions, conservation, éléments estimés.
</toggle>

---

<span color="gray">Source : [@créateur](lien du reel)</span>
```
Les ingrédients sont des cases à cocher pour la mise en place ; chaque étape commence par un résumé en gras.

## 5. Boîte de réception (mode sans conversation)

« Traite la boîte de réception » ou tâche planifiée : base **Boîte de réception recettes** (`collection://41952de0-257f-8102-bdae-000b65605919`), lignes dont le Statut est vide ou « À traiter ». Le lien peut être dans Lien, dans le titre ou dans le contenu de la page (signet) : le recopier dans Lien. Sources = lien + Captures ; créer la fiche (Ajoutée par = auteur de la ligne) ; Statut « Traitée » + relation Fiche. Échec (reel privé, aucune recette trouvée) → Statut « À compléter » avec la raison dans Note (« ajoute une capture de la légende »). Aucune question.

## 6. Répondre (en conversation)

Trois lignes : titre et lien Notion ; Repas · Difficulté · temps ; ingrédients principaux. Puis « Quelque chose à corriger ? » seulement si des éléments ont été estimés.
