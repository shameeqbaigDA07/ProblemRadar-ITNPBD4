"""Tests for the final conclusion written by Python from the checked results."""

from scoring import process
from summary import build_conclusion
from conftest import scores


def make_run(sources, problems, answers=None):
    analysis = {"problems": problems, "evidence_gaps": [], "rejected": []}
    return {"answers": answers or {"sector": "independent vet clinics", "geography": "UK"},
            "evidence": {"sources": sources},
            "ai": {"analysis": analysis},
            "result": process(analysis, sources)}


def test_conclusion_names_the_top_problem_with_its_score(sources, good_problem):
    c = build_conclusion(make_run(sources, [good_problem]))
    text = " ".join(c["paragraphs"])
    assert "“Missed appointments”, scoring 80/100 with low confidence" in text
    assert "searched 3 public sources about independent vet clinics in the UK market" in text
    assert "1 had verified evidence from at least two independent websites" in text


def test_low_confidence_gives_cautious_verdict(sources, good_problem):
    c = build_conclusion(make_run(sources, [good_problem]))
    assert c["level"] == "promising"
    assert c["verdict"].startswith("Promising, but the evidence is thin")


def test_weak_score_gives_weak_verdict(sources, good_problem):
    good_problem["scores"] = scores(2)
    c = build_conclusion(make_run(sources, [good_problem]))
    assert c["level"] == "weak"


def test_no_market_size_is_stated_not_invented(sources, good_problem):
    text = " ".join(build_conclusion(make_run(sources, [good_problem]))["paragraphs"])
    assert "remains unknown" in text
    assert "GBP" not in text


def test_next_step_uses_the_experiment_and_falls_back_to_second_problem(sources, good_problem):
    second = {**good_problem, "title": "Second idea", "scores": scores(3)}
    c = build_conclusion(make_run(sources, [good_problem, second]))
    assert c["next_step"].startswith("Run the two-week experiment for “Missed appointments”")
    assert "success if 6 of 10" in c["next_step"]
    assert "move to “Second idea”" in c["next_step"]
    assert "The next option is “Second idea” (60/100)" in " ".join(c["paragraphs"])


def test_no_ranked_problems_gives_an_honest_conclusion(sources, good_problem):
    good_problem["evidence"] = good_problem["evidence"][:1]
    c = build_conclusion(make_run(sources, [good_problem]))
    assert c["level"] == "none"
    assert "1 was removed" in c["paragraphs"][0]


def test_caveat_says_it_was_written_by_the_app(sources, good_problem):
    c = build_conclusion(make_run(sources, [good_problem]))
    assert "written by the app" in c["caveat"] and "2 verified quotes" in c["caveat"]


def test_proposed_count_includes_format_rejected_problems():
    from summary import build_conclusion
    run = {"answers": {"sector": "vets", "geography": "UK"},
           "evidence": {"sources": [{}] * 28},
           "ai": {"analysis": {"problems": [{"title": "a"}], "rejected": ["'b': missing scores"]}},
           "result": {"ranked": [], "dropped": [{"title": "a", "reason": "x"},
                                               {"title": "Rejected by format check", "reason": "y"}]}}
    text = build_conclusion(run)["paragraphs"][0]
    assert "The AI proposed 2 problems" in text and "2 were removed" in text
