"""Client Flipp avec l'API simulée par les réponses réelles enregistrées."""

import json
from pathlib import Path

import httpx
import respx

from popote.flipp.client import BASE_URL, FlippClient
from popote.flipp.normalize import is_relevant, sort_key

FIX = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


@respx.mock
async def test_grocery_flyers_keeps_one_weekly_flyer_per_chain():
    respx.get(f"{BASE_URL}/flyers").mock(return_value=httpx.Response(200, json=_load("flipp_flyers.json")))
    c = FlippClient()
    flyers = await c.grocery_flyers("H2X 1Y4")
    stores = {f["store"] for f in flyers}
    assert {"IGA", "Maxi", "Metro", "Super C", "Walmart"} <= stores
    walmart = next(f for f in flyers if f["store"] == "Walmart")
    assert walmart["name"] == "Circulaire"  # pas le « Livret des marques maison » mensuel
    assert all("Pharmaprix" != f["store"] for f in flyers)


@respx.mock
async def test_search_relevance_and_sorting_on_real_data():
    respx.get(f"{BASE_URL}/items/search").mock(return_value=httpx.Response(200, json=_load("flipp_search_poulet.json")))
    c = FlippClient()
    deals = [d for d in await c.search("poitrine poulet", "H2X1Y4") if is_relevant("poitrine poulet", d.name)]
    assert deals and all("poitrine" in d.name.lower() for d in deals)
    deals.sort(key=sort_key)
    kg = [d.per_kg for d in deals if d.per_kg]
    assert kg == sorted(kg)


@respx.mock
async def test_http_error_becomes_flipp_error():
    respx.get(f"{BASE_URL}/flyers").mock(return_value=httpx.Response(503))
    c = FlippClient()
    try:
        await c.flyers("H2X1Y4")
    except Exception as e:
        assert "503" in str(e)
    else:
        raise AssertionError("FlippError attendue")
