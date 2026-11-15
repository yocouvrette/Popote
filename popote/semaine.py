"""Outil en ligne de commande utilisé par Claude chaque semaine (tâche planifiée).

    python -m popote.semaine collecte                 # circulaires de la semaine → data/historique.csv
    python -m popote.semaine rabais poulet brocoli riz # où acheter chaque ingrédient (JSON)
    python -m popote.semaine rabais --fichier ingredients.txt
    python -m popote.semaine top --n 25               # meilleurs rabais alimentaires (idées de recettes)

Configuration par variables d'environnement ou fichier .env à la racine :
    POSTAL_CODE   ex. H2X1Y4
    STORES        magasins où vous allez, ex. "Maxi,IGA,Metro,Super C,Walmart"
    MAXI_MATCH    concurrents acceptés par VOTRE Maxi pour les imbattables, ex. "IGA,Metro,Super C,Walmart"
Sortie : JSON sur la sortie standard, compact, prêt à être lu par Claude.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import sys
from pathlib import Path

from .deals.categories import CATEGORIES, EXCLUDE
from .deals.score import ScoreInput, deal_score
from .flipp.client import FlippClient
from .flipp.normalize import PRODUCT_CHANGERS, Deal, fold, is_match, sort_key, store_matches, tokens
from .epiceries import BON, FAUX, ORDINAIRE, PLANCHER, Epiceries
from .historique import append, weekly_min_per_kg
from .maxi import place, price_label

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "historique.csv"


def _load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def _list(name: str, default: str) -> list[str]:
    return [s.strip() for s in os.getenv(name, default).split(",") if s.strip()]


def week_label(today: dt.date | None = None) -> str:
    """Jeudi de début du cycle des circulaires québécoises (jeudi → mercredi)."""
    today = today or dt.date.today()
    return (today - dt.timedelta(days=(today.weekday() - 3) % 7)).isoformat()


def food_category(name: str) -> str | None:
    """Catégorie alimentaire par mots entiers (« alimentation » ne contient pas « lime »).

    Les mots-clés de plusieurs mots passent en premier : « pomme de terre » → légumes, pas fruits.
    """
    n = fold(name)
    if any(x in n for x in EXCLUDE) or any(w in n for w in PRODUCT_CHANGERS):
        return None
    toks = tokens(name)
    pairs = sorted(((w, cat) for cat, ws in CATEGORIES.items() for w in ws), key=lambda p: -len(p[0].split()))
    for w, cat in pairs:
        if tokens(w) and tokens(w) <= toks:
            return cat
    return None


def _score(d: Deal, peers: list[float], history: list[float], cat: str | None = None) -> dict:
    s = deal_score(ScoreInput(
        discount=d.discount, unit_price=d.per_kg or d.unit_price, price=d.price,
        points_value=d.points_value, history=history or None, peers_this_week=peers or None,
        canonical=None, is_produce=cat in ("legumes", "fruits"), month=dt.date.today().month,
    ))
    return {"note": s.value, "palier": s.tier, "base": s.quality_source}


async def cmd_collecte(c: FlippClient, postal: str, stores: list[str]) -> dict:
    flyers = await c.grocery_flyers(postal, stores)
    batches = await asyncio.gather(*(c.flyer_items(f["flyer_id"], f["store"]) for f in flyers))
    week = week_label()
    added = append(HISTORY, week, [d for b in batches for d in b])
    return {"semaine": week, "circulaires": [
        {"magasin": f["store"], "id": f["flyer_id"], "du": (f["valid_from"] or "")[:10], "au": (f["valid_to"] or "")[:10]}
        for f in flyers], "articles_ajoutes": added, "historique": str(HISTORY.relative_to(ROOT))}


def adjust_with_verdict(score: dict, verdict: dict | None) -> dict:
    """La note /10 tient compte du verdict d'épiceries.ca quand il existe (prix régulier sur un an)."""
    if not verdict:
        return score
    label, note = verdict["label"], score["note"]
    note = {PLANCHER: max(note, 9.0), BON: max(note, 7.5), ORDINAIRE: min(note, 5.5), FAUX: min(note, 2.0)}[label]
    tier = "top" if note >= 8 else "moyen" if note >= 5 else "faible"
    return {**score, "note": note, "palier": tier, "base": "epiceries.ca"}


async def cmd_rabais(c: FlippClient, postal: str, stores: list[str], match: list[str], ingredients: list[str],
                     epiceries: Epiceries | None = None) -> dict:
    uniq = list(dict.fromkeys(i.strip().lower() for i in ingredients if i.strip()))[:60]
    results = await asyncio.gather(*(c.search(i, postal) for i in uniq), return_exceptions=True)
    week = week_label()
    out, sans, erreurs = {}, [], {}
    per_ing: list[tuple[str, list[Deal]]] = []
    for ing, res in zip(uniq, results):
        if isinstance(res, Exception):
            erreurs[ing] = str(res)
            continue
        deals = sorted((d for d in res if store_matches(d.store, stores) and is_match(ing, d.name)), key=sort_key)
        if not deals:
            sans.append(ing)
            continue
        per_ing.append((ing, deals))

    verdicts: dict[int, dict | None] = {}
    if epiceries:
        tops = [d for _, deals in per_ing for d in deals[:3]]
        found = await asyncio.gather(*(epiceries.verdict(d) for d in tops), return_exceptions=True)
        verdicts = {id(d): (v.as_dict() if v and not isinstance(v, Exception) else None) for d, v in zip(tops, found)}

    for ing, deals in per_ing:
        hist = weekly_min_per_kg(HISTORY, ing, exclude_week=week)
        p = place(ing, deals, match, stores)
        options = []
        for d in deals[:3]:
            peers = [x.per_kg for x in deals if x.per_kg and x.store != d.store]
            v = verdicts.get(id(d))
            opt = {"magasin": d.store, "article": d.name, "prix": price_label(d),
                   "rabais": f"{round(d.discount * 100)} %" if d.discount else None,
                   "jusqu_au": (d.valid_to or "")[:10], **adjust_with_verdict(_score(d, peers, hist), v)}
            if v:
                opt["verdict"] = {k: v[k] for k in ("label", "regular", "low", "vs_regulier", "matched", "url")}
            options.append(opt)
        out[ing] = {**p.as_dict(), "options": options}
    res = {"semaine": week, "code_postal": postal, "magasins": stores, "concurrents_maxi": match,
           "en_rabais": out, "sans_rabais": sans}
    if erreurs:
        res["erreurs"] = erreurs
    return res


async def cmd_top(c: FlippClient, postal: str, stores: list[str], n: int) -> dict:
    flyers = await c.grocery_flyers(postal, stores)
    batches = await asyncio.gather(*(c.flyer_items(f["flyer_id"], f["store"]) for f in flyers))
    rows, seen = [], set()
    for d in (d for b in batches for d in b):
        key = (d.store, fold(d.name), d.price)
        if key in seen:
            continue
        seen.add(key)
        cat = food_category(d.name)
        if cat in ("proteines", "legumes", "fruits") and d.price is not None and d.discount:
            rows.append((d, cat))
    scored = []
    for d, cat in rows:
        s = _score(d, [], [], cat)
        scored.append({"categorie": cat, "magasin": d.store, "article": d.name, "prix": price_label(d),
                       "rabais": f"{round(d.discount * 100)} %", **s})
    scored.sort(key=lambda r: -r["note"])
    by_cat: dict[str, list] = {}
    for r in scored:
        by_cat.setdefault(r["categorie"], [])
        if len(by_cat[r["categorie"]]) < n:
            by_cat[r["categorie"]].append(r)
    return {"semaine": week_label(), "meilleurs": by_cat}


def main(argv: list[str] | None = None) -> None:
    _load_env()
    ap = argparse.ArgumentParser(prog="popote.semaine")
    ap.add_argument("--postal", default=os.getenv("POSTAL_CODE", ""))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("collecte")
    r = sub.add_parser("rabais")
    r.add_argument("ingredients", nargs="*")
    r.add_argument("--fichier")
    r.add_argument("--sans-epiceries", action="store_true", help="ne pas consulter épiceries.ca")
    t = sub.add_parser("top")
    t.add_argument("--n", type=int, default=12)
    a = ap.parse_args(argv)
    if not a.postal:
        sys.exit("Code postal manquant : --postal H2X1Y4 ou POSTAL_CODE dans .env")
    stores = _list("STORES", "Maxi,IGA,Metro,Super C,Walmart,Provigo")
    match = _list("MAXI_MATCH", "IGA,Metro,Super C,Walmart")

    async def run():
        c = FlippClient()
        try:
            if a.cmd == "collecte":
                return await cmd_collecte(c, a.postal, stores)
            if a.cmd == "rabais":
                ings = list(a.ingredients)
                if a.fichier:
                    ings += [l for l in Path(a.fichier).read_text(encoding="utf-8").splitlines() if l.strip()]
                e = None if a.sans_epiceries else Epiceries()
                try:
                    return await cmd_rabais(c, a.postal, stores, match, ings, e)
                finally:
                    if e:
                        await e.aclose()
            return await cmd_top(c, a.postal, stores, a.n)
        finally:
            await c.aclose()

    print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
