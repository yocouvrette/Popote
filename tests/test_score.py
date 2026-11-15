from popote.deals.score import ScoreInput, deal_score


def test_big_known_discount_on_rare_deal_is_top():
    s = deal_score(ScoreInput(discount=0.54, unit_price=14.31, price=6.49,
                              history=[22.0, 21.5, 19.8, 22.0, 20.9, 23.1]))
    assert s.tier == "top" and s.quality_source == "rabais" and s.rarity == 1.0


def test_no_info_is_low():
    s = deal_score(ScoreInput(discount=None, unit_price=None, price=8.99))
    assert s.value <= 4 and s.tier == "faible" and s.quality_source == "aucune"


def test_history_used_when_discount_unknown():
    s = deal_score(ScoreInput(discount=None, unit_price=8.0, price=8.0, history=[12, 11, 12.5, 11.8]))
    assert s.quality_source == "historique" and s.quality > 0.7


def test_peer_comparison_bootstraps_first_weeks():
    s = deal_score(ScoreInput(discount=None, unit_price=7.0, price=7.0, peers_this_week=[10, 11, 9.5]))
    assert s.quality_source == "semaine" and s.rarity == 0.5


def test_loyalty_points_count_as_discount():
    s = deal_score(ScoreInput(discount=None, unit_price=16.54, price=15, points_value=3))
    assert s.quality_source == "rabais" and s.quality > 0.3


def test_season_lifts_local_produce():
    in_season = deal_score(ScoreInput(discount=0.3, unit_price=3, price=3, canonical="pomme", is_produce=True, month=10))
    off_season = deal_score(ScoreInput(discount=0.3, unit_price=3, price=3, canonical="fraise", is_produce=True, month=1))
    assert in_season.value > off_season.value
