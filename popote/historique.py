"""Base de prix : un simple fichier CSV versionné dans le dépôt (data/historique.csv).

Chaque jeudi, toutes les circulaires d'épicerie retenues y sont ajoutées (une ligne par article).
Gratuit, lisible dans Excel, et l'historique sert à noter la rareté d'un rabais.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .flipp.normalize import Deal, is_match

FIELDS = ["semaine", "magasin", "item_id", "nom", "marque", "prix", "unite", "prix_unitaire",
          "prix_kg", "prix_l", "rabais", "valide_jusqu"]


def append(path: Path, week: str, deals: list[Deal]) -> int:
    """Ajoute les articles de la semaine ; ignore ceux déjà présents (même semaine + item_id)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    seen: set[tuple[str, str]] = set()
    if path.exists():
        with path.open(encoding="utf-8", newline="") as f:
            seen = {(r["semaine"], r["item_id"]) for r in csv.DictReader(f)}
    new = [d for d in deals if (week, str(d.item_id)) not in seen]
    write_header = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        for d in new:
            w.writerow({
                "semaine": week, "magasin": d.store, "item_id": d.item_id, "nom": d.name,
                "marque": d.brand or "", "prix": d.price, "unite": d.unit or "",
                "prix_unitaire": d.unit_price, "prix_kg": d.per_kg or "", "prix_l": d.per_l or "",
                "rabais": d.discount or "", "valide_jusqu": (d.valid_to or "")[:10],
            })
    return len(new)


def weekly_min_per_kg(path: Path, canonical: str, exclude_week: str | None = None) -> list[float]:
    """Prix au kg minimal par semaine passée pour un ingrédient (tous magasins)."""
    if not path.exists():
        return []
    best: dict[str, float] = defaultdict(lambda: float("inf"))
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["semaine"] == exclude_week or not r["prix_kg"]:
                continue
            if is_match(canonical, r["nom"]):
                best[r["semaine"]] = min(best[r["semaine"]], float(r["prix_kg"]))
    return [v for _, v in sorted(best.items())][-8:]
