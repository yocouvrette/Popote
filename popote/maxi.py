"""Règle des « imbattables » de Maxi : où acheter chaque article de la liste.

Politique Maxi (« Imbattable. Point final. ») telle que décrite publiquement :
- Maxi égale le prix d'un article IDENTIQUE (marque, format, unité) annoncé dans la circulaire
  d'un grand concurrent du même secteur. Les bannières acceptées varient selon le magasin :
  à confirmer à ton Maxi (exemple rapporté : Super C, Walmart, Metro, IGA, Tigre Géant).
- Marques maison des concurrents exclues, sauf œufs, beurre et pommes de terre.
- Fruits, légumes, viandes, poissons : même type et même format ou poids.
- 4 unités par article ; caisse avec caissier ; preuve = circulaire papier ou app du concurrent,
  avec les dates de validité ; offre encore valide le jour de l'achat.
- Exclus : liquidations, remises postales, « achetez X obtenez Y », points de fidélité.
Maxi peut changer cette politique sans préavis.
"""

from __future__ import annotations

from dataclasses import dataclass

from .flipp.normalize import Deal, fold, sort_key

MAXI_MATCH_DEFAULT = ["IGA", "Metro", "Super C", "Walmart"]

# Marques maison des concurrents (non égalées). Loblaw (Sans nom, PC) est la famille de Maxi : pas concernée.
STORE_BRANDS = [
    "compliments", "panache", "notre meilleur", "our finest",           # Sobeys / IGA
    "irresistibles", "selection", "life smart",                          # Metro / Super C
    "great value", "mainstays", "equate",                               # Walmart
]
STORE_BRAND_EXCEPTIONS = ["oeuf", "beurre", "pomme de terre", "patate"]

MAXI = "Maxi"
MAXI_IMBATTABLE = "Maxi — imbattables"
SANS_RABAIS = "Sans rabais (n'importe où)"


def is_store_brand(deal: Deal) -> bool:
    text = fold(f"{deal.brand or ''} {deal.raw_name or deal.name}")
    return any(b in text for b in STORE_BRANDS)


def imbattable_eligible(deal: Deal, canonical: str, match_stores: list[str]) -> tuple[bool, str | None]:
    """L'article de ce concurrent peut-il être égalé chez Maxi ? Retourne (oui/non, raison du refus)."""
    if fold(deal.store) not in {fold(s) for s in match_stores}:
        return False, f"{deal.store} n'est pas dans la liste des concurrents acceptés"
    if deal.price is None:
        return False, "prix non numérique"
    if deal.member_only:
        return False, "prix réservé aux membres"
    if deal.points_value and not deal.discount:
        return False, "rabais en points seulement"
    if is_store_brand(deal) and not any(x in fold(canonical) for x in STORE_BRAND_EXCEPTIONS):
        return False, "marque maison du concurrent"
    return True, None


@dataclass
class Placement:
    canonical: str
    magasin: str            # MAXI, MAXI_IMBATTABLE, autre magasin, ou SANS_RABAIS
    deal: Deal | None
    preuve: str | None      # à montrer à la caisse
    note: str | None        # remarque (raison de non-appariement, limite de 4…)

    def as_dict(self) -> dict:
        return {
            "ingredient": self.canonical,
            "magasin": self.magasin,
            "article": self.deal.name if self.deal else None,
            "prix": price_label(self.deal) if self.deal else None,
            "preuve": self.preuve,
            "note": self.note,
        }


def price_label(d: Deal) -> str:
    if d.per_kg and d.unit in ("lb", "kg", "100g"):
        return f"{d.unit_price:.2f} $/{d.unit} ({d.per_kg:.2f} $/kg)"
    if d.unit_price is not None:
        base = f"{d.unit_price:.2f} $"
        return f"{base} ({d.per_kg:.2f} $/kg)" if d.per_kg else base
    return "?"


def place(canonical: str, deals: list[Deal], match_stores: list[str] | None = None,
          stores: list[str] | None = None) -> Placement:
    """Choisit où acheter un ingrédient cette semaine.

    1. Meilleur rabais parmi les magasins permis (prix au kg d'abord).
    2. S'il est chez Maxi → « Maxi ».
    3. S'il est chez un concurrent accepté et égalable → « Maxi — imbattables », avec la preuve.
    4. Sinon → ce magasin, avec la raison ; on signale aussi le meilleur rabais égalable s'il existe.
    """
    match_stores = match_stores or MAXI_MATCH_DEFAULT
    pool = [d for d in deals if d.price is not None and (not stores or fold(d.store) in {fold(s) for s in stores})]
    if not pool:
        return Placement(canonical, SANS_RABAIS, None, None, None)
    pool.sort(key=sort_key)
    best = pool[0]
    if fold(best.store) == fold(MAXI):
        return Placement(canonical, MAXI, best, None, None)
    ok, why = imbattable_eligible(best, canonical, match_stores)
    if ok:
        proof = f"Circulaire {best.store} : {best.name}, {price_label(best)}, jusqu'au {(best.valid_to or '')[:10]}"
        return Placement(canonical, MAXI_IMBATTABLE, best, proof, "4 unités max ; caisse avec caissier")
    alt = next((d for d in pool[1:] if fold(d.store) == fold(MAXI)
                or imbattable_eligible(d, canonical, match_stores)[0]), None)
    note = why
    if alt is not None:
        note += f" ; sinon chez Maxi via {alt.store} à {price_label(alt)}"
    return Placement(canonical, best.store, best, None, note)
