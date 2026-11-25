"""Tests for the score formula, confidence levels and market-size checks."""

import pytest

from conftest import scores
from scoring import WEIGHTS, check_market_size, compute_score, confidence_level


def test_weights_add_up_to_100_percent():
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_all_fives_scores_100():
    total, _ = compute_score(scores(5))
    assert total == 100.0


def test_all_ones_scores_20():
    total, _ = compute_score(scores(1))
    assert total == 20.0


def test_mixed_scores_match_hand_calculation():
    mixed = scores(1)
    mixed["severity"]["score"] = 5          # 20 * 0.30 * 5 = 30
    mixed["frequency"]["score"] = 4         # 20 * 0.20 * 4 = 16
    mixed["market"]["score"] = 3            # 20 * 0.20 * 3 = 12
    mixed["willingness_to_pay"]["score"] = 2  # 20 * 0.15 * 2 = 6
    mixed["competition_gap"]["score"] = 1   # 20 * 0.15 * 1 = 3
    total, breakdown = compute_score(mixed)
    assert total == 67.0
    assert [b["points"] for b in breakdown] == [30.0, 16.0, 12.0, 6.0, 3.0]


@pytest.mark.parametrize("bad", [0, 6, 3.5, "4", None, True])
def test_invalid_factor_score_is_rejected(bad):
    broken = scores(3)
    broken["market"]["score"] = bad
    with pytest.raises(ValueError):
        compute_score(broken)


def test_missing_factor_is_rejected():
    broken = scores(3)
    del broken["competition_gap"]
    with pytest.raises(ValueError):
        compute_score(broken)


@pytest.mark.parametrize("independent, verified, total, expected", [
    (4, 6, 6, "High"),
    (3, 4, 4, "Medium"),
    (2, 2, 2, "Low"),
    (4, 1, 6, "Medium"),   # most quotes unverified: dropped one level
    (2, 1, 4, "Low"),      # cannot go below Low
])
def test_confidence_levels(independent, verified, total, expected):
    assert confidence_level(independent, verified, total) == expected


def numbered_sources():
    from conftest import make_source
    return {"S1": make_source("S1", "vetstats.co.uk", "There are about 5,000 independent clinics in the UK."),
            "S2": make_source("S2", "survey.org", "Clinics spend roughly £400 a year on reminder tools.")}


def test_market_size_accepted_when_sourced_and_bottom_up():
    market = {"can_estimate": True, "low": 1_000_000, "high": 3_000_000, "currency": "GBP",
              "formula": "clinics x annual spend",
              "inputs": [{"name": "clinics", "value": "5,000", "source_id": "S1"},
                         {"name": "spend", "value": "£400", "source_id": "S2"}]}
    result = check_market_size(market, numbered_sources())
    assert result["status"] == "estimated"
    assert result["confidence"] == "Medium"


def test_market_size_rejects_input_not_in_its_source():
    market = {"can_estimate": True, "low": 1_000_000, "high": 3_000_000, "formula": "clinics x spend",
              "inputs": [{"name": "clinics", "value": "9,000", "source_id": "S1"},
                         {"name": "spend", "value": "£400", "source_id": "S2"}]}
    result = check_market_size(market, numbered_sources())
    assert result["status"] == "not_estimated"
    assert "not found in their sources: clinics" in result["reason"]


def test_market_size_rejects_whole_market_valuation_from_live_run():
    """Regression: run 20261117-211227 used a 2025 market value and a 2035
    forecast as a low-high range, with no calculation."""
    from conftest import make_source
    s6 = make_source("S6", "wiseguyreports.com",
                     "Market Size, 2025 : USD 48.1 Billion Forecast, 2035 : USD 100 Billion")
    market = {"can_estimate": True, "low": 48100000000, "high": 100000000000, "currency": "USD",
              "formula": "Total Shopify Market Valuation range from 2025 to 2035",
              "inputs": [{"name": "Shopify Market 2025 Value", "value": "48100000000", "source_id": "S6"},
                         {"name": "Shopify Market 2035 Forecast", "value": "100000000000", "source_id": "S6"}]}
    result = check_market_size(market, {"S6": s6})
    assert result["status"] == "not_estimated"
    assert "not a bottom-up calculation" in result["reason"]


def test_numbers_are_matched_with_scale_words():
    from scoring import number_in_source
    assert number_in_source("48100000000", "valued at USD 48.1 Billion in 2025")
    assert number_in_source("£1,200", "between £400 and £1,200 a year")
    assert not number_in_source("£1,500", "between £400 and £1,200 a year")
    assert not number_in_source("about half", "half of all clinics")


def test_market_size_rejected_without_sources(sources):
    by_id = {s["id"]: s for s in sources}
    market = {"can_estimate": True, "low": 1, "high": 2, "formula": "x",
              "inputs": [{"name": "clinics", "value": "5,000", "source_id": "S99"}]}
    result = check_market_size(market, by_id)
    assert result["status"] == "not_estimated"
    assert "no valid source" in result["reason"]


def test_market_size_rejects_gdp(sources):
    by_id = {s["id"]: s for s in sources}
    market = {"can_estimate": True, "low": 1e9, "high": 2e9, "formula": "share x UK GDP",
              "inputs": [{"name": "UK GDP", "value": "2.7tn", "source_id": "S1"}]}
    assert check_market_size(market, by_id)["status"] == "not_estimated"


def test_market_size_rejects_reversed_range(sources):
    by_id = {s["id"]: s for s in sources}
    market = {"can_estimate": True, "low": 5, "high": 1, "formula": "a x b",
              "inputs": [{"name": "a", "value": "1", "source_id": "S1"}]}
    assert check_market_size(market, by_id)["status"] == "not_estimated"


def test_market_size_not_estimated_when_ai_says_so(sources):
    result = check_market_size({"can_estimate": False, "reason_if_not": "No data"}, {})
    assert result == {"status": "not_estimated", "reason": "No data"}



def test_breakdown_marks_reasons_without_a_source():
    mixed = scores(3)
    mixed["frequency"]["reason"] = "Happens every day."
    _, breakdown = compute_score(mixed)
    cited = {b["factor"]: b["cites_source"] for b in breakdown}
    assert cited["severity"] is True       # "Based on S1"
    assert cited["frequency"] is False


def test_dropped_problem_keeps_its_checked_quotes_for_the_report():
    from scoring import process
    sources = [{"id": "S1", "title": "t", "url": "https://a.co.uk/x", "domain": "a.co.uk",
                "origin": "Tavily", "text": "clinics are overbooked every single week in winter"}]
    problem = {"title": "Overbooking", "evidence": [
        {"source_id": "S1", "quote": "clinics are overbooked every single week", "supports": "x"},
        {"source_id": "S9", "quote": "made up", "supports": "y"}]}
    dropped = process({"problems": [problem]}, sources)["dropped"][0]
    assert [e["status"] for e in dropped["evidence"]] == ["verified", "unknown_source"]
