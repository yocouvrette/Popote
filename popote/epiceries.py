"""Verdict sur un rabais à partir de l'historique d'épiceries.ca (API publique, gratuite, sans clé).

But : savoir si le prix de la circulaire (Flipp) est un vrai rabais, en le comparant au prix
régulier habituel et au plus bas de l'année du MÊME produit, dans le MÊME magasin.

Constats du 2026-11-15 (tests directs) :
- Historique d'environ un an par produit, un relevé par semaine environ ; dernier relevé le 2026-10-29.
- Super C n'a pas de données ; les produits frais sans marque s'apparient mal.
- Le verdict intégré (`storeproduct` → `deal`) revient souvent null : on calcule le nôtre.
- La recherche plein texte de plusieurs mots ne renvoie rien ; la recherche d'un mot (souvent la
  marque) avec filtre de magasin fonctionne.
Règles d'usage : cache, pas de rafales, quelques requêtes par seconde au plus, usage personnel.
"""

from __future__ import annotations

import asyncio
import datetime as dt
from dataclasses import asdict, dataclass
from statistics import median

import httpx

from .flipp.normalize import PRODUCT_CHANGERS, Deal, fold, parse_size, tokens

BASE = "https://epiceries.ca/api"
STORE_CODES = {"maxi": "maxi", "iga": "iga", "metro": "metro", "provigo": "provigo", "walmart": "walmart"}
_NOISE = {"ou", "emb", "format", "selectionne", "selectionnes", "variete", "varietes", "frais", "fraiche"}

PLANCHER, BON, ORDINAIRE, FAUX = "Prix plancher", "Bon rabais", "Rabais ordinaire", "Faux rabais"


@dataclass
class Verdict:
    label: str
    flyer_price: float
    regular: float          # médiane des prix hors rabais sur 52 semaines
    low: float              # plus bas prix observé sur 52 semaines
    weeks: int              # nombre de relevés
    matched: str            # produit apparié sur épiceries.ca
    url: str

    def as_dict(self) -> dict:
        d = asdict(self)
        d["vs_regulier"] = f"{round((1 - self.flyer_price / self.regular) * 100)} %" if self.regular else None
        return d


def classify(price: float, regular: float, low: float) -> str:
    if price <= low * 1.01:
        return PLANCHER
    if price <= regular * 0.85:
        return BON
    if price < regular * 0.97:
        return ORDINAIRE
    return FAUX


def _content_tokens(text: str | None) -> set[str]:
    return {t for t in tokens(text) if not t.isdigit() and len(t) > 1 and t not in _NOISE}


def match_score(flyer_name: str, brand: str | None, candidate: str) -> float:
    """Similarité stricte (0–1) entre un article de circulaire et un produit d'épiceries.ca.

    Exige que TOUS les mots de contenu de l'article soient présents dans le candidat
    (« oignons verts » n'apparie pas « croustilles crème sure et oignon »), refuse les mots qui
    changent le produit (jus, pizza, burger…), puis pénalise les mots en trop (Jaccard).
    """
    want = _content_tokens(flyer_name) | (_content_tokens(brand) if brand else set())
    have = _content_tokens(candidate)
    if not want or not have or not want <= have:
        return 0.0
    extra = fold(candidate)
    if any(w in extra and w not in fold(flyer_name) for w in PRODUCT_CHANGERS + _EXTRA_CHANGERS):
        return 0.0
    return len(want) / len(want | have)


_EXTRA_CHANGERS = ["pizza", "shot", "foie", "riz frit", "salade de", "farci", "marine", "fume", "croustille"]


def _sizes_compatible(a: str | None, b: str | None) -> bool:
    sa, sb = parse_size(a), parse_size(b)
    if not sa or not sb:
        return True
    return sa[1] == sb[1] and abs(sa[0] - sb[0]) <= 0.1 * max(sa[0], sb[0])


class Epiceries:
    def __init__(self, http: httpx.AsyncClient | None = None, max_concurrency: int = 2, pause: float = 0.35):
        self._http = http or httpx.AsyncClient(timeout=25, headers={"User-Agent": "popote/0.3 (usage personnel)"})
        self._sem = asyncio.Semaphore(max_concurrency)
        self._pause = pause
        self._cache: dict = {}

    async def aclose(self):
        await self._http.aclose()

    async def _get(self, **params) -> dict | None:
        key = tuple(sorted(params.items()))
        if key in self._cache:
            return self._cache[key]
        async with self._sem:
            try:
                r = await self._http.get(BASE, params=params)
                r.raise_for_status()
                body = r.json()
            except (httpx.HTTPError, ValueError):
                body = {}
            await asyncio.sleep(self._pause)
        data = body.get("data") if body.get("ok") else None
        self._cache[key] = data
        return data

    async def match(self, deal: Deal) -> dict | None:
        """Produit épiceries.ca du même magasin le plus semblable à l'article de circulaire."""
        store = STORE_CODES.get(fold(deal.store))
        want = _content_tokens(deal.name)
        if not store or len(want) < 1:
            return None
        # Nom générique = marque + une catégorie (« Céréales General Mills ») : trop de variétés.
        brand_toks = _content_tokens(deal.brand) if deal.brand else set()
        if not brand_toks:
            brand_toks = {t for t in want if t in {"general", "mills", "kellogg", "hubert", "st", "pc", "compliments"}}
        if brand_toks and len(want - brand_toks) <= 1:
            return None
        queries = []
        if deal.brand:
            queries.append(fold(deal.brand).split()[0])
        queries += sorted(want, key=len, reverse=True)[:2]
        scored: dict[str, tuple[float, dict]] = {}
        for q in dict.fromkeys(queries):
            data = await self._get(endpoint="search", q=q, store=store, limit=100)
            for p in (data or {}).get("results", []):
                cand = f"{p.get('brand') or ''} {p.get('name')}"
                score = match_score(deal.name, deal.brand, cand)
                if score >= 0.5 and _sizes_compatible(deal.raw_name, f"{p.get('name')} {p.get('size') or ''}"):
                    scored[fold(p.get("name"))] = (score, p)
            if any(s >= 0.8 for s, _ in scored.values()):
                break
        if not scored:
            return None
        ranked = sorted(scored.values(), key=lambda x: -x[0])
        # Article générique (« Sauce St-Hubert », « Céréales General Mills ») : plusieurs produits
        # différents aussi plausibles → on ne devine pas.
        if len(ranked) > 1 and ranked[1][0] >= ranked[0][0] - 0.05:
            return None
        return ranked[0][1]

    async def verdict(self, deal: Deal) -> Verdict | None:
        if deal.price is None:
            return None
        p = await self.match(deal)
        if not p:
            return None
        hist = await self._get(endpoint="history", id=p["id"], store=STORE_CODES[fold(deal.store)], limit=500)
        rows = (hist or {}).get("history", [])
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)
        rows = [r for r in rows if r.get("price") and dt.datetime.fromisoformat(r["date"]) >= cutoff]

        by_weight = deal.unit in ("lb", "kg", "100g") and deal.per_kg is not None
        if by_weight:
            # Prix au poids : comparer en $/kg avec le prix unitaire « /100 g » d'épiceries.ca.
            def per_kg(r):
                up = r.get("unitPrice") or {}
                return up.get("value") * 10 if up.get("unit") == "100 g" and up.get("value") else None
            pts = [(per_kg(r), r.get("discounted")) for r in rows]
            pts = [(v, d) for v, d in pts if v]
            price = deal.per_kg
        else:
            pts = [(r["price"], r.get("discounted")) for r in rows]
            price = deal.unit_price if deal.unit_price is not None else deal.price
        regular_pts = [v for v, d in pts if not d]
        if len(pts) < 4 or len(regular_pts) < 2:
            return None
        regular, low = median(regular_pts), min(v for v, _ in pts)
        if price < low * 0.5:  # moins de la moitié du plus bas de l'année : appariement ou format douteux
            return None
        return Verdict(classify(price, regular, low), round(price, 2), round(regular, 2), round(low, 2),
                       len(pts), p["name"], p.get("url") or "")
