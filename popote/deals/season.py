"""Calendrier simplifié des fruits et légumes du Québec (mois de pleine saison, récolte + entreposage).

Sert à la composante « saisonnalité » de la note des rabais. Approximation à affiner ;
source à consulter en phase 4 : calendrier des récoltes d'Aliments du Québec / Mangez Québec.
"""

# ingrédient canonique → mois (1–12) où le produit québécois est disponible en abondance
QUEBEC_SEASON: dict[str, set[int]] = {
    "asperge": {5, 6},
    "fraise": {6, 7, 8, 9},
    "framboise": {7, 8},
    "bleuet": {7, 8, 9},
    "mais": {8, 9},
    "tomate": {7, 8, 9},
    "concombre": {7, 8, 9},
    "poivron": {8, 9},
    "courgette": {7, 8, 9},
    "brocoli": {7, 8, 9, 10},
    "chou-fleur": {8, 9, 10},
    "laitue": {6, 7, 8, 9},
    "haricot vert": {7, 8, 9},
    "pomme": {9, 10, 11, 12, 1, 2, 3},
    "poire": {9, 10},
    "canneberge": {10, 11, 12},
    "courge": {9, 10, 11, 12},
    "citrouille": {9, 10},
    "carotte": {8, 9, 10, 11, 12, 1, 2, 3},
    "pomme de terre": {8, 9, 10, 11, 12, 1, 2, 3},
    "oignon": {8, 9, 10, 11, 12, 1, 2},
    "betterave": {8, 9, 10, 11, 12},
    "chou": {8, 9, 10, 11, 12},
    "panais": {9, 10, 11, 12, 1, 2},
    "navet": {9, 10, 11, 12},
    "poireau": {8, 9, 10, 11},
    "champignon": set(range(1, 13)),  # culture en serre toute l'année
}


def season_factor(canonical: str | None, month: int, is_produce: bool) -> float:
    """1,0 en saison au Québec ; 0,3 hors saison ; 0,5 neutre (non-produit ou inconnu)."""
    if not is_produce or not canonical:
        return 0.5
    months = QUEBEC_SEASON.get(canonical)
    if months is None:
        return 0.5
    return 1.0 if month in months else 0.3
