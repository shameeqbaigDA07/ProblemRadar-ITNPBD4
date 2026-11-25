"""Tests for the 5-page brief: insights come from checked results, and every page fits."""

import json
from pathlib import Path

import pytest

from brief import build_brief, build_insights, clip, money_range, quotes_saved, radar_points


def ranked_problem(rank, score, sources=2):
    bars = [{"factor": f, "label": f.title(), "weight_pct": w, "score": s, "points": s * w / 5,
             "max_points": w, "reason": "r (S1)"}
            for f, w, s in (("severity", 30, 5), ("frequency", 20, 4), ("market", 20, 3),
                            ("willingness_to_pay", 15, 2), ("competition_gap", 15, 3))]
    return {"rank": rank, "title": f"Problem {rank}", "who": "Clinic owners", "situation": "Mondays",
            "consequence": "Lost revenue", "score": score, "confidence": "Low",
            "independent_sources": sources, "verified_quotes": 2, "total_quotes": 2,
            "evidence": [{"source_id": "S1", "quote": "a real quote", "supports": "x", "status": "verified",
                          "source": {"domain": "a.co.uk", "url": "https://a.co.uk", "title": "A"}},
                         {"source_id": "S2", "quote": "another", "supports": "y", "status": "verified",
                          "source": {"domain": "b.org", "url": "https://b.org", "title": "B"}}],
            "score_breakdown": bars, "market": {"status": "not_estimated", "reason": "no data"},
            "riskiest_assumption": "They will pay", "experiment": {"objective": "Test", "steps": ["a", "b"]},
            "touchpoints": [], "micro_trends": [], "existing_alternatives": []}


def run_with(ranked, dropped=()):
    return {"answers": {"sector": "vet clinics", "geography": "UK", "payer": "Businesses", "advantage": "vet"},
            "evidence": {"sources": [{"id": "S1"}, {"id": "S2"}]},
            "ai": {"analysis": {"problems": ranked + [{}] * len(dropped)}},
            "result": {"ranked": ranked, "dropped": list(dropped), "evidence_gaps": ["gap"]},
            "meta": {"created_at": "2026-11-23T10:00:00", "model": "Gemini: test"}}


def test_insights_lead_with_the_top_score_and_survival_rate():
    insights = build_insights(run_with([ranked_problem(1, 87), ranked_problem(2, 70)]))
    assert insights[0]["figure"] == "87" and insights[1]["figure"] == "2 of 2"
    assert insights[2]["figure"] == "5/5" and "willingness" in insights[2]["text"].lower()
    assert insights[3]["figure"] == "2"  # independent websites, because market size is unknown


def test_brief_without_ranked_problems_gives_a_research_plan():
    dropped = [{"title": "Overbooking", "reason": "Only 1 source", "evidence": [
        {"status": "verified", "quote": "q", "source": {"domain": "a.co.uk"}}]}]
    b = build_brief(run_with([], dropped))
    assert b["verdict"] == "No opportunity is ready to test yet"
    assert b["lead"]["title"] == "Overbooking" and not b["lead"]["ranked"]
    assert b["plan"]["type"] == "problem-discovery interviews"
    assert b["insights"][0]["figure"] == "0 of 1"


def test_old_runs_without_saved_quotes_are_described_honestly():
    b = build_brief(run_with([], [{"title": "Old", "reason": "Only 1 source"}]))
    assert not quotes_saved([{"title": "Old", "reason": "x"}])
    assert "not saved" in b["insights"][1]["text"] or "saved before" in b["insights"][1]["text"]


def test_radar_puts_higher_scores_nearer_the_centre():
    r = radar_points([ranked_problem(1, 90), ranked_problem(2, 40)], dropped_count=1)
    c = r["centre"]
    dist = [((p["x"] - c) ** 2 + (p["y"] - c) ** 2) ** .5 for p in r["points"]]
    assert dist[0] < dist[1] and len(r["removed"]) == 1


def test_clip_and_money_range():
    assert clip("one two three", 2) == "One two…"
    assert clip("a real quote", 5, capital=False) == "a real quote"
    assert money_range({"low": 2_100_000, "high": 4_800_000, "currency": "GBP"}) == "£2.1m–£4.8m"


def test_brief_page_renders_five_pages(tmp_path):
    from app import app
    app.config.update(TESTING=True, RUNS_DIR=tmp_path)
    run = run_with([ranked_problem(1, 87)])
    run["id"] = "20261123-100000-vet-clinics"
    (tmp_path / f"{run['id']}.json").write_text(json.dumps(run))
    html = app.test_client().get(f"/runs/{run['id']}/brief").get_data(as_text=True)
    assert html.count('class="page"') == 5 and "Problem 1" in html and "Save as PDF" in html
