"""Règles hebdomadaires : appariement strict, catégories, imbattables Maxi, historique CSV."""

import datetime as dt

from popote.flipp.normalize import Deal, is_match
from popote.historique import append, weekly_min_per_kg
from popote.maxi import MAXI, MAXI_IMBATTABLE, SANS_RABAIS, place
from popote.semaine import food_category, week_label


def deal(store, name, price, unit=None, per_kg=None, brand=None, discount=None, member=False):
    return Deal(item_id=hash((store, name)) % 10**6, flyer_id=1, store=store, name=name, raw_name=name,
                price=price, unit=unit, unit_price=price, per_kg=per_kg, per_l=None, discount=discount,
                sale_story=None, member_only=member, points_value=0.0, valid_from="2026-11-12",
                valid_to="2026-11-18T23:59:59-05:00", brand=brand)


def test_is_match_rejects_products_that_change_the_ingredient():
    assert is_match("riz", "Riz basmati 2 kg")
    assert not is_match("riz", "POUDING AU RIZ OU TAPIOCA KOZY SHACK")
    assert not is_match("pomme de terre", "pommes de terre douces violettes")
    assert is_match("patate douce", "Patates douces")
    assert not is_match("poulet", "Burgers de poulet pané")


def test_food_category_uses_whole_words():
    assert food_category("Pommes de terre russet") == "legumes"
    assert food_category("Bloc d'alimentation pour démarrage") is None
    assert food_category("Pizza cuire à la maison") is None
    assert food_category("Couronne de brocoli") == "legumes"


def test_week_label_is_thursday():
    assert week_label(dt.date(2026, 11, 15)) == "2026-11-12"
    assert week_label(dt.date(2026, 11, 12)) == "2026-11-12"
    assert week_label(dt.date(2026, 11, 18)) == "2026-11-12"


def test_cheapest_at_competitor_goes_to_maxi_imbattables_with_proof():
    p = place("brocoli", [deal("Metro", "Couronne de brocoli", 1.44), deal("Maxi", "Brocoli", 2.49)])
    assert p.magasin == MAXI_IMBATTABLE and "Metro" in p.preuve and "1.44" in p.preuve


def test_cheapest_at_maxi_stays_maxi():
    p = place("poulet", [deal("Maxi", "Cuisses de poulet", 3.0, "lb", 6.61), deal("Metro", "Pilons", 3.99, "lb", 8.8)])
    assert p.magasin == MAXI and p.preuve is None


def test_competitor_store_brand_is_not_matched_except_eggs():
    p = place("carotte", [deal("IGA", "Carottes compliments", 1.77, brand="Compliments")])
    assert p.magasin == "IGA" and "marque maison" in p.note
    eggs = place("oeuf", [deal("Super C", "Oeufs blancs Sélection", 2.97, brand="Sélection")])
    assert eggs.magasin == MAXI_IMBATTABLE


def test_member_price_and_unlisted_store_are_not_matched():
    assert place("bacon", [deal("Metro", "Bacon", 3.99, member=True)]).magasin == "Metro"
    p = place("saumon", [deal("Provigo", "Saumon", 9.0, "lb", 19.8), deal("IGA", "Saumon", 10.0, "lb", 22.0)])
    assert p.magasin == "Provigo" and "sinon chez Maxi via IGA" in p.note


def test_no_deal_means_anywhere():
    assert place("ail", []).magasin == SANS_RABAIS


def test_history_csv_append_dedupes_and_feeds_weekly_minimum(tmp_path):
    f = tmp_path / "h.csv"
    d1 = deal("Maxi", "Cuisses de poulet", 3.0, "lb", 6.61)
    d2 = deal("Metro", "Pilons de poulet", 3.99, "lb", 8.8)
    assert append(f, "2026-11-05", [d1, d2]) == 2
    assert append(f, "2026-11-05", [d1]) == 0
    append(f, "2026-11-12", [deal("IGA", "Poitrines de poulet", 6.49, "lb", 14.31)])
    assert weekly_min_per_kg(f, "poulet") == [6.61, 14.31]
    assert weekly_min_per_kg(f, "poulet", exclude_week="2026-11-12") == [6.61]


def test_epiceries_match_score_is_strict():
    from popote.epiceries import match_score, classify, PLANCHER, BON, ORDINAIRE, FAUX
    assert match_score("Oignons verts", None, "Croustilles saveur de crème sure et oignon") == 0
    assert match_score("Bleuets", None, "Shots de mélange de jus avec bleuets") == 0
    assert match_score("Couronne de brocoli", None, "Couronne de brocoli enveloppée") >= 0.5
    assert match_score("Pavés de saumon", None, "Pavé de saumon avec crevettes") < 0.67
    assert classify(4.0, 6.0, 4.0) == PLANCHER
    assert classify(4.9, 6.0, 4.0) == BON
    assert classify(5.6, 6.0, 4.0) == ORDINAIRE
    assert classify(6.0, 6.0, 4.0) == FAUX
