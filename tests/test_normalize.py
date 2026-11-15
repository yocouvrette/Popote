"""Normalisation : cas tirés de réponses Flipp réelles (fr-ca, Montréal, 2026-11-15)."""

import json
from pathlib import Path

import pytest

from popote.flipp.normalize import (
    deal_from_item, french_name, is_relevant, parse_discount, parse_price, parse_size, store_matches,
)

FIX = Path(__file__).parent / "fixtures"


def test_french_name_keeps_french_half_in_sentence_case():
    assert french_name("PILONS DE POULET | CHICKEN DRUMSTICKS") == "Pilons de poulet"
    assert french_name("Poitrines de poulet Olymel") == "Poitrines de poulet Olymel"


def test_relevance_handles_plural_accents_and_bilingual():
    assert is_relevant("poulet", "POITRINES DE POULET FRAIS DÉSOSSÉES MAPLE LEAF PRIME")
    assert is_relevant("pilon poulet", "PILONS DE POULET | CHICKEN DRUMSTICKS")
    assert not is_relevant("poulet", "SAUCISSES FUMÉES HYGRADE")
    assert not is_relevant("chicken", "PILONS DE POULET | CHICKEN DRUMSTICKS")  # partie anglaise ignorée


def test_store_matching():
    assert store_matches("Super C", ["super c"])
    assert store_matches("Maxi", ["Maxi"])
    assert not store_matches("Maxi & Cie", ["IGA"])
    assert not store_matches("Pharmaprix", ["IGA", "Maxi"])


@pytest.mark.parametrize("name,expected", [
    ("AILES DE POULET PCM, 907 g", (0.907, "kg")),
    ("Burgers de poulet pané 550 -560 g", (0.55, "kg")),
    ("POUDING AU RIZ KOZY SHACK, 4x113 G", (0.452, "kg")),
    ("GÂTERIES PEDIGREE, 100 G - 1,9 KG", (1.9, "kg")),
    ("SAUCE CORDON BLEU, 284/398 ML", (0.284, "L")),
    ("OIGNONS VERTS | GREEN ONIONS", None),
])
def test_parse_size(name, expected):
    got = parse_size(name)
    if expected is None:
        assert got is None
    else:
        assert got[1] == expected[1] and got[0] == pytest.approx(expected[0], rel=1e-3)


def test_price_with_explicit_kg_text_uses_it():
    p = parse_price(6.49, None, "/lb 14,31$/kg", None, "Poitrines de poulet")
    assert p.unit == "lb" and p.per_kg == 14.31


def test_price_per_lb_converted():
    p = parse_price(1.97, None, "/lb", None, "Pilons")
    assert p.per_kg == round(1.97 * 2.20462, 2)
    assert parse_price(5.66, None, "lb", None, "x").unit == "lb"
    assert parse_price(5.66, None, "/LB", None, "x").unit == "lb"


def test_price_multi_buy_member_points_and_size():
    assert parse_price(5.0, "2/", None, None, "x").unit_price == 2.5
    assert parse_price(3.99, None, "chacune Membre Récompenses", None, "x").member_only
    p = parse_price(15, None, None, "obtenez pc optimum 3 000 pts, valeur de 3$", "AILES DE POULET PCM, 907 g")
    assert p.points_value == 3.0 and p.per_kg == round(15 / 0.907, 2)
    assert parse_price(14.99, None, "+TX", None, "Poulet entier").unit is None


@pytest.mark.parametrize("cur,orig,story,disc,expected", [
    (4.98, 7.87, "Chute de prix", None, 0.367),
    (3.25, None, "35% de rabais", None, 0.35),
    (1.97, None, "PLUS DE 60% DE RABAIS", None, 0.6),
    (6.49, None, "7.57 $/lb de RABAIS", None, 0.538),
    (8.99, None, "$8 de RABAIS", None, 0.471),
    ("1.25", None, None, 45, 0.45),
    (8.99, None, None, None, None),
])
def test_parse_discount(cur, orig, story, disc, expected):
    got = parse_discount(cur, orig, story, disc)
    assert (got is None) if expected is None else got == pytest.approx(expected, abs=0.002)


def test_every_real_search_item_parses():
    items = json.loads((FIX / "flipp_search_poulet.json").read_text(encoding="utf-8"))["items"]
    deals = [deal_from_item(it) for it in items]
    assert len(deals) == len(items) > 20
    assert all(d.store != "?" and d.name for d in deals)
    with_kg = [d for d in deals if d.per_kg]
    assert len(with_kg) >= 10
    assert all(1 < d.per_kg < 80 for d in with_kg)  # prix au kg plausibles pour du poulet


def test_real_flyer_and_detail_items_parse():
    flyer = json.loads((FIX / "flipp_flyer_iga.json").read_text(encoding="utf-8"))["items"]
    deals = [deal_from_item(it, store_fallback="IGA") for it in flyer]
    assert all(d.store == "IGA" for d in deals)
    assert sum(1 for d in deals if d.discount) >= 10
    detail = json.loads((FIX / "flipp_item_detail.json").read_text(encoding="utf-8"))["item"]
    d = deal_from_item(detail)
    assert d.store == "IGA" and d.per_kg == 14.31 and d.discount == pytest.approx(0.538, abs=0.002)
