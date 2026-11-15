"""Client HTTP du backend public de Flipp (non officiel, validé le 2026-11-15).

Endpoints confirmés (réponses réelles dans tests/fixtures/) :
  GET {BASE}/items/search?locale=fr-ca&postal_code=H2X1Y4&q=poulet
      → items[] avec current_price, original_price, pre/post_price_text, sale_story, merchant_name
  GET {BASE}/flyers?locale=fr-ca&postal_code=H2X1Y4
      → flyers[] avec id, merchant, categories_csv ("All Flyers,Groceries"), valid_from/to
  GET {BASE}/flyers/{flyer_id}?locale=fr-ca
      → items[] (250–400 par circulaire) avec name, price (chaîne), discount (%), brand
  GET {BASE}/items/{item_id}?locale=fr-ca
      → détail : price_text ("/lb 14,31$/kg"), category, percent_off, description

Politesse : cache, 4 requêtes simultanées au plus, identifiant explicite. Usage personnel.
"""

from __future__ import annotations

import asyncio
import os
import time

import httpx

from .normalize import Deal, deal_from_item, fold, store_matches

BASE_URL = os.getenv("FLIPP_BASE_URL", "https://backflipp.wishabi.com/flipp")
USER_AGENT = os.getenv("FLIPP_USER_AGENT", "popote/0.2 (usage personnel)")
GROCERY_CHAINS = ["IGA", "Maxi", "Metro", "Super C", "Provigo", "Walmart"]  # les 6 chaînes analysées par Glouton


class FlippError(RuntimeError):
    pass


class _TTLCache:
    def __init__(self, ttl: int):
        self.ttl, self._d = ttl, {}

    def get(self, k):
        hit = self._d.get(k)
        return hit[1] if hit and time.monotonic() - hit[0] < self.ttl else None

    def set(self, k, v):
        self._d[k] = (time.monotonic(), v)


class FlippClient:
    def __init__(self, locale: str = "fr-ca", timeout: float = 20.0, cache_ttl: int = 6 * 3600,
                 max_concurrency: int = 4, http: httpx.AsyncClient | None = None):
        self.locale = locale
        self._http = http or httpx.AsyncClient(base_url=BASE_URL, timeout=timeout,
                                               headers={"User-Agent": USER_AGENT})
        self._cache = _TTLCache(cache_ttl)
        self._sem = asyncio.Semaphore(max_concurrency)

    async def aclose(self):
        await self._http.aclose()

    async def _get(self, path: str, params: dict) -> dict:
        key = (path, tuple(sorted(params.items())))
        if (hit := self._cache.get(key)) is not None:
            return hit
        async with self._sem:
            try:
                r = await self._http.get(path, params=params)
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as e:
                raise FlippError(f"Flipp a répondu {e.response.status_code} pour {path}") from e
            except (httpx.HTTPError, ValueError) as e:
                raise FlippError(f"Appel Flipp impossible ({path}) : {e}") from e
        self._cache.set(key, data)
        return data

    @staticmethod
    def postal(pc: str) -> str:
        return pc.replace(" ", "").upper()

    async def search(self, query: str, postal_code: str) -> list[Deal]:
        data = await self._get("/items/search", {"locale": self.locale, "postal_code": self.postal(postal_code), "q": query})
        return [deal_from_item(it) for it in data.get("items", [])]  # ecom_items ignorés

    async def flyers(self, postal_code: str) -> list[dict]:
        data = await self._get("/flyers", {"locale": self.locale, "postal_code": self.postal(postal_code)})
        out = []
        for f in data.get("flyers", []):
            cats = f.get("categories") or f.get("categories_csv") or []
            if isinstance(cats, str):
                cats = [c.strip() for c in cats.split(",") if c.strip()]
            out.append({"flyer_id": f.get("id"), "store": f.get("merchant") or "?", "name": f.get("name"),
                        "valid_from": f.get("valid_from"), "valid_to": f.get("valid_to"), "categories": cats})
        return out

    async def grocery_flyers(self, postal_code: str, stores: list[str] | None = None) -> list[dict]:
        """Circulaires d'épicerie hebdomadaires des magasins choisis (une par chaîne, la plus courte)."""
        best: dict[str, dict] = {}
        for f in await self.flyers(postal_code):
            if "groceries" not in [fold(c) for c in f["categories"]]:
                continue
            if not store_matches(f["store"], stores or GROCERY_CHAINS):
                continue
            k = fold(f["store"])
            # garder la circulaire hebdomadaire (fin la plus proche), pas les livrets mensuels
            if k not in best or (f["valid_to"] or "9") < (best[k]["valid_to"] or "9"):
                best[k] = f
        return list(best.values())

    async def flyer_items(self, flyer_id: int, store: str | None = None) -> list[Deal]:
        data = await self._get(f"/flyers/{flyer_id}", {"locale": self.locale})
        deals = []
        for it in data.get("items", []):
            d = deal_from_item(it, store_fallback=store)
            d.flyer_id = d.flyer_id or flyer_id
            deals.append(d)
        return deals

    async def item_detail(self, item_id: int) -> Deal:
        data = await self._get(f"/items/{item_id}", {"locale": self.locale})
        return deal_from_item(data.get("item", data))
