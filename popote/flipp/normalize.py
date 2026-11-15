"""Normalisation des articles Flipp : texte, prix unitaires, rabais.

Fonctions pures, sans réseau. Les formats traités viennent de réponses réelles
(fr-ca, Montréal, novembre 2026) enregistrées dans tests/fixtures/.

Formats observés :
  post_price_text / price_text : None, "lb", "/lb", "/LB", "/ch", "+TX", "+ TX",
      "/lb 14,31$/kg", "/lb - 19,82$/kg", "Membre Récompenses", "chacune Membre Récompenses"
  pre_price_text : None, "2/", "3 pour"
  sale_story : "35% de rabais", "PLUS DE 60% DE RABAIS", "7.57 $/lb de RABAIS",
      "$8 de RABAIS", "Chute de prix", "obtenez pc optimum 3 000 pts, valeur de 3$"
  name : "PILONS DE POULET | CHICKEN DRUMSTICKS" (bilingue), "AILES DE POULET PCM, 907 g",
      "... 550 -560 g", "... 4x113 G", "... 1,9 KG", "... 284/398 ML"
  flyer item (circulaire complète) : price "1.25" (chaîne), discount 45 (pourcentage)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

LB_PER_KG = 2.20462


# --------------------------------------------------------------------------- texte

def fold(text: str | None) -> str:
    """Minuscules, sans accents, espaces compactés."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", no_accents.casefold()).strip()


def french_name(name: str | None) -> str:
    """Garde la partie française d'un nom bilingue « FR | EN » et la remet en casse de phrase."""
    if not name:
        return ""
    fr = name.split("|")[0].strip(" ,-")
    if fr.isupper():
        fr = fr[:1] + fr[1:].lower()
    return fr


_STOP = {"de", "du", "des", "la", "le", "les", "a", "au", "aux", "en", "et", "d", "l", "ou", "avec", "pour"}


def _stem(tok: str) -> str:
    return tok[:-1] if len(tok) > 3 and tok.endswith(("s", "x")) else tok


def tokens(text: str | None) -> set[str]:
    return {_stem(t) for t in re.findall(r"[a-z0-9]+", fold(text)) if t not in _STOP}


def is_relevant(query: str, item_name: str | None) -> bool:
    """Tous les mots significatifs de la requête figurent dans le nom (pluriels et accents ignorés)."""
    q = tokens(query)
    return bool(q) and q.issubset(tokens(french_name(item_name)))


# Mots qui changent le produit : exclus sauf s'ils figurent dans la requête
# (« riz » ≠ « pouding au riz », « pomme de terre » ≠ « pommes de terre douces »).
PRODUCT_CHANGERS = [
    "pouding", "soupe", "bouillon", "pane", "croquette", "burger", "frite", "rondelle", "croustille",
    "chips", "biscuit", "barre", "gateau", "muffin", "beigne", "tarte", "vinaigrette", "trempette",
    "douce", "aromatise", "boisson", "jus", "nourriture pour", "gaterie", "sauce", "cretons", "pate a",
    "chocolat", "collation", "bonbon", "croquant",
]


def is_match(query: str, item_name: str | None) -> bool:
    """is_relevant + rejet des formes qui changent le produit."""
    if not is_relevant(query, item_name):
        return False
    name, q = fold(french_name(item_name)), fold(query)
    return not any(w in name and w not in q for w in PRODUCT_CHANGERS)


def store_matches(merchant: str | None, allowed: list[str] | None) -> bool:
    if not allowed:
        return True
    m = fold(merchant)
    return any(fold(a) and fold(a) == m or (len(fold(a)) > 3 and fold(a) in m) for a in allowed)


# --------------------------------------------------------------------------- nombres

def to_float(value) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = re.search(r"\d+(?:[.,]\d+)?", str(value).replace(" ", " "))
    return float(m.group(0).replace(",", ".")) if m else None


# --------------------------------------------------------------------------- formats

_SIZE = re.compile(
    r"(?:(?P<n>\d+)\s*[x×]\s*)?(?P<q>\d+(?:[.,]\d+)?)(?:\s*(?:-|/|à)\s*\d+(?:[.,]\d+)?)?\s*(?P<u>kg|g|ml|l)\b",
    re.I,
)


def parse_size(name: str | None) -> tuple[float, str] | None:
    """Format du produit tiré du nom → (quantité en kg ou L, "kg"|"L").

    Plages (« 550-560 g », « 284/398 ML ») : la plus petite valeur, prudente.
    Multipacks (« 4x113 G ») : multipliés. Retourne None si absent ou ambigu.
    """
    m = None
    for m in _SIZE.finditer(fold(name)):
        pass  # garde la dernière occurrence : le format est en fin de nom
    if not m:
        return None
    q = float(m.group("q").replace(",", ".")) * int(m.group("n") or 1)
    unit = m.group("u").lower()
    if unit == "g":
        return q / 1000, "kg"
    if unit == "kg":
        return q, "kg"
    if unit == "ml":
        return q / 1000, "L"
    return q, "L"


@dataclass
class PriceInfo:
    unit: str | None          # "lb" | "kg" | "100g" | "ea" | None
    multi_buy: int            # 2 pour « 2/5 $ »
    unit_price: float | None  # prix d'une unité (après achat multiple)
    per_kg: float | None
    per_l: float | None
    member_only: bool         # prix membre (Metro Récompenses, etc.)
    points_value: float       # valeur en $ des points promis (PC Optimum…)


def parse_price(price, pre_text: str | None, post_text: str | None,
                sale_story: str | None, name: str | None) -> PriceInfo:
    pre, post, story = fold(pre_text), fold(post_text), fold(sale_story)
    price = to_float(price)

    multi = 1
    if m := re.search(r"(\d+)\s*(?:/|pour|for)", pre) or re.match(r"^(\d+)\s*(?:pour|for)\s", story):
        multi = max(1, int(m.group(1)))

    explicit_kg = None
    if m := re.search(r"(\d+(?:[.,]\d+)?)\s*\$?\s*/\s*kg", post):
        explicit_kg = float(m.group(1).replace(",", "."))

    unit = None
    if re.search(r"\b100\s*g\b", post):
        unit = "100g"
    elif re.search(r"(^|[/\s])lb\b|\blivre\b", post):
        unit = "lb"
    elif re.search(r"(^|[/\s])kg\b", post):
        unit = "kg"
    elif re.search(r"(^|/)ch\b|chacun|\bea\b|\bunite\b", post):
        unit = "ea"

    unit_price = price / multi if price is not None else None
    per_kg = per_l = None
    if explicit_kg is not None:
        per_kg = explicit_kg
    elif unit_price is not None and unit in ("lb", "kg", "100g"):
        per_kg = {"lb": unit_price * LB_PER_KG, "kg": unit_price, "100g": unit_price * 10}[unit]
    elif unit_price is not None and unit in (None, "ea"):
        if size := parse_size(name):
            qty, kind = size
            if qty > 0:
                if kind == "kg":
                    per_kg = unit_price / qty
                else:
                    per_l = unit_price / qty

    points_value = 0.0
    if "pts" in story or "points" in story:
        if m := re.search(r"valeur de\s*(\d+(?:[.,]\d+)?)", story):
            points_value = float(m.group(1).replace(",", "."))

    return PriceInfo(
        unit=unit,
        multi_buy=multi,
        unit_price=round(unit_price, 2) if unit_price is not None else None,
        per_kg=round(per_kg, 2) if per_kg is not None else None,
        per_l=round(per_l, 2) if per_l is not None else None,
        member_only="membre" in post or "member" in post,
        points_value=points_value,
    )


def parse_discount(current, original, sale_story: str | None, flyer_discount=None) -> float | None:
    """Rabais en fraction (0,35 = 35 %), à partir de la meilleure information disponible."""
    cur = to_float(current)
    orig = to_float(original)
    if cur and orig and orig > cur:
        return round(1 - cur / orig, 3)
    if flyer_discount not in (None, "", 0):
        return round(float(flyer_discount) / 100, 3)
    story = fold(sale_story)
    if m := re.search(r"(\d+(?:[.,]\d+)?)\s*%", story):
        return round(float(m.group(1).replace(",", ".")) / 100, 3)
    if cur and (m := re.search(r"(\d+(?:[.,]\d+)?)\s*\$[^%]*rabais|\$\s*(\d+(?:[.,]\d+)?)\s*de rabais|economisez\s*(\d+(?:[.,]\d+)?)", story)):
        off = float(next(g for g in m.groups() if g).replace(",", "."))
        return round(off / (cur + off), 3)
    return None


# --------------------------------------------------------------------------- article

@dataclass
class Deal:
    item_id: int | None
    flyer_id: int | None
    store: str
    name: str            # nom français, casse de phrase
    raw_name: str
    price: float | None
    unit: str | None
    unit_price: float | None
    per_kg: float | None
    per_l: float | None
    discount: float | None
    sale_story: str | None
    member_only: bool
    points_value: float
    valid_from: str | None
    valid_to: str | None
    brand: str | None = None

    def compact(self) -> dict:
        d = asdict(self)
        for k in ("raw_name", "flyer_id", "points_value", "member_only", "brand"):
            if not d.get(k):
                d.pop(k, None)
        return {k: v for k, v in d.items() if v not in (None, "")}


def first(d: dict, *keys, default=None):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", []):
            return v
    return default


def deal_from_item(raw: dict, store_fallback: str | None = None) -> Deal:
    """Article de recherche (/items/search), de circulaire (/flyers/{id}) ou de détail (/items/{id})."""
    raw_name = str(first(raw, "name", "short_name", default="?")).strip()
    price = to_float(first(raw, "current_price", "price"))
    post = first(raw, "post_price_text", "price_text")
    pi = parse_price(price, raw.get("pre_price_text"), post, raw.get("sale_story"), raw_name)
    return Deal(
        item_id=first(raw, "flyer_item_id", "id"),
        flyer_id=raw.get("flyer_id"),
        store=str(first(raw, "merchant_name", "merchant", default=store_fallback or "?")),
        name=french_name(raw_name),
        raw_name=raw_name,
        price=price,
        unit=pi.unit,
        unit_price=pi.unit_price,
        per_kg=pi.per_kg,
        per_l=pi.per_l,
        discount=parse_discount(price, raw.get("original_price"), raw.get("sale_story"), raw.get("discount")),
        sale_story=raw.get("sale_story"),
        member_only=pi.member_only,
        points_value=pi.points_value,
        valid_from=raw.get("valid_from"),
        valid_to=raw.get("valid_to"),
        brand=raw.get("brand") if isinstance(raw.get("brand"), str) else None,
    )


def sort_key(d: Deal) -> tuple:
    """Prix au kg (ou au litre) connu d'abord, puis prix unitaire."""
    norm = d.per_kg if d.per_kg is not None else d.per_l
    return (norm is None, norm or 0, d.unit_price is None, d.unit_price or 0)
