"""Lexique de catégories alimentaires pour l'outil top_deals (plan B).

Mots en minuscules sans accents ; un article est classé dans la première catégorie
dont un mot apparaît dans son nom. À enrichir au besoin.
"""

CATEGORIES: dict[str, list[str]] = {
    "proteines": [
        "poulet", "dinde", "boeuf", "porc", "veau", "agneau", "jambon", "bacon", "saucisse",
        "saumon", "truite", "morue", "aiglefin", "tilapia", "thon", "crevette", "petoncle",
        "tofu", "tempeh", "oeuf", "pois chiche", "lentille", "haricot", "cubes a ragout",
        "hache", "filet", "cuisse", "poitrine", "longe", "cotelette",
    ],
    "legumes": [
        "brocoli", "chou", "carotte", "poivron", "oignon", "ail", "tomate", "concombre",
        "laitue", "epinard", "courgette", "champignon", "patate", "pomme de terre",
        "celeri", "asperge", "haricots verts", "mais", "aubergine", "courge", "kale", "poireau",
    ],
    "fruits": [
        "pomme", "banane", "orange", "fraise", "bleuet", "framboise", "raisin", "poire",
        "mangue", "ananas", "citron", "lime", "avocat", "clementine", "peche", "melon",
    ],
    "laitiers": ["lait", "fromage", "yogourt", "yogourt grec", "creme", "beurre", "cheddar", "mozzarella", "feta"],
    "feculents": ["riz", "pates", "spaghetti", "pain", "tortilla", "quinoa", "couscous", "nouilles", "gnocchi"],
}

# Mots qui excluent un article (non alimentaire ou trop transformé pour cuisiner)
EXCLUDE = [
    "nourriture pour chat", "nourriture pour chien", "litiere", "shampoing", "detergent",
    "croquettes pour", "jouet", "vitamine",
]
