"""Tests for the two-independent-source rule and the full process step."""

from conftest import ARTICLE_A, ARTICLE_B, make_source, scores
from scoring import independent_groups, process, registrable_domain


def by_id(sources):
    return {s["id"]: s for s in sources}


def test_registrable_domain_handles_uk_domains():
    assert registrable_domain("news.bbc.co.uk") == "bbc.co.uk"
    assert registrable_domain("blog.example.com") == "example.com"


def test_two_different_sites_are_independent():
    srcs = [make_source("S1", "a.com", ARTICLE_A), make_source("S2", "b.com", ARTICLE_B)]
    assert len(independent_groups(["S1", "S2"], by_id(srcs))) == 2


def test_two_pages_on_same_site_count_once():
    srcs = [make_source("S1", "a.com", ARTICLE_A), make_source("S2", "blog.a.com", ARTICLE_B)]
    assert len(independent_groups(["S1", "S2"], by_id(srcs))) == 1


def test_copied_article_on_another_site_counts_once():
    copied = "Republished: " + ARTICLE_A
    srcs = [make_source("S1", "a.com", ARTICLE_A), make_source("S2", "b.com", copied)]
    assert len(independent_groups(["S1", "S2"], by_id(srcs))) == 1


def test_separate_forum_threads_count_separately():
    srcs = [make_source("S1", "news.ycombinator.com", ARTICLE_A, url="https://news.ycombinator.com/item?id=1"),
            make_source("S2", "news.ycombinator.com", ARTICLE_B, url="https://news.ycombinator.com/item?id=2")]
    assert len(independent_groups(["S1", "S2"], by_id(srcs))) == 2


def test_same_source_cited_twice_counts_once():
    srcs = [make_source("S1", "a.com", ARTICLE_A)]
    assert len(independent_groups(["S1", "S1"], by_id(srcs))) == 1


def test_unknown_source_ids_are_ignored():
    srcs = [make_source("S1", "a.com", ARTICLE_A)]
    assert len(independent_groups(["S1", "S9"], by_id(srcs))) == 1


def test_problem_with_two_independent_verified_sources_is_kept(sources, good_problem):
    result = process({"problems": [good_problem]}, sources)
    assert len(result["ranked"]) == 1
    kept = result["ranked"][0]
    assert kept["independent_sources"] == 2
    assert kept["verified_quotes"] == 2
    assert kept["score"] == 80.0
    assert kept["rank"] == 1


def test_problem_with_one_source_is_dropped(sources, good_problem):
    good_problem["evidence"] = good_problem["evidence"][:1]
    result = process({"problems": [good_problem]}, sources)
    assert result["ranked"] == []
    assert "Only 1 independent source" in result["dropped"][0]["reason"]


def test_unverified_quote_does_not_count_towards_the_rule(sources, good_problem):
    good_problem["evidence"][1]["quote"] = "this sentence was invented by the model and is not real"
    result = process({"problems": [good_problem]}, sources)
    assert result["ranked"] == []


def test_quote_citing_unknown_source_is_labelled(sources, good_problem):
    good_problem["evidence"].append({"source_id": "S42", "quote": "made up words here and more", "supports": ""})
    kept = process({"problems": [good_problem]}, sources)["ranked"][0]
    assert kept["evidence"][-1]["status"] == "unknown_source"


def test_ranking_orders_by_score(sources, good_problem):
    weaker = {**good_problem, "title": "Weaker", "scores": scores(2)}
    result = process({"problems": [weaker, good_problem]}, sources)
    assert [p["title"] for p in result["ranked"]] == ["Missed appointments", "Weaker"]
    assert [p["rank"] for p in result["ranked"]] == [1, 2]


def test_trend_without_valid_source_is_unverified(sources, good_problem):
    good_problem["micro_trends"] = [{"trend": "x", "type": "market", "source_ids": ["S77"]}]
    kept = process({"problems": [good_problem]}, sources)["ranked"][0]
    assert kept["micro_trends"][0]["status"] == "unverified"
