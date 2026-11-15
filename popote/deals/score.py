"""Note des rabais sur 10, inspirée des trois critères publiés par Glouton.

Glouton note chaque article selon la qualité (rabais vs prix régulier), la rareté
(fréquence de la promotion) et la saisonnalité, sans publier sa formule.
Ceci en est une approximation transparente :

    note = 10 × (wq·qualité + wr·rareté + ws·saison)
    produits frais : wq=0,55  wr=0,30  ws=0,15
    autres         : wq=0,65  wr=0,35  ws=0

Qualité (0–1), par ordre de préférence de la source :
  1. rabais connu (prix d'origine Flipp, % de la circulaire, « 7,57 $ de rabais ») : min(rabais / 0,50, 1)
  2. historique : 1 − prix unitaire / médiane des 8 dernières semaines (tous magasins), ramené sur 0,40
  3. comparaison de la semaine : même calcul contre la médiane des autres magasins
  Les points de fidélité comptent comme un rabais (valeur $ / prix).
Rareté (0–1) : part des semaines d'historique où ce produit était PLUS CHER qu'aujourd'hui.
  Sans historique (premières semaines) : 0,5.
Paliers d'affichage (ceux de Glouton) : 8–10 à ne pas manquer · 5–7 selon le besoin · ≤ 4 peu intéressant.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from .season import season_factor


@dataclass
class ScoreInput:
    discount: float | None             # fraction, ex. 0,35
    unit_price: float | None           # $/kg, $/L ou $/unité, même base que l'historique
    price: float | None                # prix affiché (pour les points)
    points_value: float = 0.0
    history: list[float] | None = None     # prix unitaires hebdomadaires passés (min par semaine)
    peers_this_week: list[float] | None = None  # prix unitaires du même produit dans d'autres magasins
    canonical: str | None = None
    is_produce: bool = False
    month: int = 1


@dataclass
class Score:
    value: float          # 0–10, une décimale
    tier: str             # "top" | "moyen" | "faible"
    quality: float
    rarity: float
    season: float
    quality_source: str   # "rabais" | "historique" | "semaine" | "aucune"


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def deal_score(i: ScoreInput) -> Score:
    discount = i.discount or 0.0
    if i.points_value and i.price:
        discount = max(discount, 0.0) + i.points_value / (i.price + i.points_value)

    if discount > 0:
        quality, source = _clamp(discount / 0.50), "rabais"
    elif i.unit_price and i.history and len(i.history) >= 3:
        quality, source = _clamp((1 - i.unit_price / median(i.history)) / 0.40), "historique"
    elif i.unit_price and i.peers_this_week:
        quality, source = _clamp((1 - i.unit_price / median(i.peers_this_week)) / 0.40), "semaine"
    else:
        quality, source = 0.0, "aucune"

    if i.unit_price and i.history and len(i.history) >= 3:
        rarity = sum(1 for p in i.history if p > i.unit_price * 1.02) / len(i.history)
    else:
        rarity = 0.5

    season = season_factor(i.canonical, i.month, i.is_produce)
    wq, wr, ws = (0.55, 0.30, 0.15) if i.is_produce else (0.65, 0.35, 0.0)
    value = round(10 * (wq * quality + wr * rarity + ws * season), 1)
    tier = "top" if value >= 8 else "moyen" if value >= 5 else "faible"
    return Score(value, tier, round(quality, 2), round(rarity, 2), season, source)
