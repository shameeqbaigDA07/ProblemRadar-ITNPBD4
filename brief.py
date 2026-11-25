"""The 5-page brief: key insights from a run, worked out by Python.

The full report shows everything. The brief picks what a founder (or a
partner, investor or tutor) needs to decide quickly, and fits it on five
A4 pages:

  1. Verdict and key insights, with the radar of problems
  2. Opportunity landscape: every problem, its score and why
  3. The lead opportunity: who hurts, how, and the verified evidence
  4. Market, competition and founder fit
  5. The next 14 days: riskiest assumption, experiment, open questions

Insights are chosen first (build_insights), then the pages are built
around them. Like summary.py, nothing here asks the AI: every number comes
from the checked results, so the brief cannot contradict the full report.
"""

import math

from summary import build_conclusion

RADAR_SIZE = 300          # the radar SVG is drawn in a 300 x 300 box
RADAR_RADIUS = 128        # outer ring: score 20 (weakest possible)
MAX_PROBLEMS = 6          # more would not fit on page 2
STRONG_SCORE = 65         # same threshold as the conclusion's verdict

# When nothing survives the checks, the next step is first-hand evidence.
NO_SIGNAL_PLAN = {
    "assumption": "That people in this sector share a painful, repeated problem that has not yet been written about online.",
    "type": "problem-discovery interviews",
    "objective": "Find problems the public sources missed, in the words of the people who have them.",
    "participants": "Five to eight people who work in or buy from this sector.",
    "steps": ["List fifteen people to contact through your own network and local groups.",
              "Ask each for a 20-minute call about the hardest part of their week.",
              "Write down exact words; do not pitch any solution.",
              "Group what you hear into repeated problems.",
              "Run Problem Radar again using their words as the sector description."],
    "budget": "£0",
    "success": "At least three people describe the same problem without being prompted.",
    "failure": "Every person names a different problem: widen or change the sector.",
}

PAYER_WORDS = {"Businesses": "businesses", "Consumers": "consumers", "Either": "customers"}


def clip(text, words=40, capital=True):
    """Shorten text to a number of words so every page stays one page.
    AI text sometimes starts in lower case; capital=True fixes that
    (quotes are passed with capital=False so they stay word for word)."""
    parts = (text or "").split()
    out = " ".join(parts) if len(parts) <= words else " ".join(parts[:words]).rstrip(",;:.") + "…"
    return out[:1].upper() + out[1:] if capital else out


def _short_money(value):
    value = float(value)
    for size, suffix in ((1e9, "bn"), (1e6, "m"), (1e3, "k")):
        if value >= size:
            return f"{value / size:.3g}{suffix}"
    return f"{value:,.0f}"


def money_range(market):
    """'£2.1m–£4.8m' style range for an estimated market."""
    symbol = {"GBP": "£", "USD": "$", "EUR": "€"}.get(market.get("currency", "GBP"), "")
    low, high = market.get("low"), market.get("high")
    if low is None or high is None:
        return "Unknown"
    return f"{symbol}{_short_money(low)}–{symbol}{_short_money(high)}"


def _lower_first(text):
    text = (text or "").strip().rstrip(".")
    return text[:1].lower() + text[1:] if text and not text[:2].isupper() else text


def _domains(problem):
    return sorted({(e.get("source") or {}).get("domain", "") for e in problem.get("evidence", [])
                   if e.get("status") == "verified"} - {""})


def _quotes(problem, limit=3):
    """Verified quotes first, then the rest, each with its source."""
    evidence = sorted(problem.get("evidence", []), key=lambda e: e.get("status") != "verified")
    out = []
    for e in evidence[:limit]:
        source = e.get("source") or {}
        out.append({"quote": clip(e.get("quote"), 34, capital=False), "supports": clip(e.get("supports"), 18),
                    "verified": e.get("status") == "verified", "source_id": e.get("source_id"),
                    "domain": source.get("domain", ""), "url": source.get("url", ""),
                    "title": clip(source.get("title"), 12)})
    return out


def _factor_bars(problem):
    return [{"label": b["label"], "score": b["score"], "points": b["points"],
             "max_points": b["max_points"], "weight": b["weight_pct"],
             "share": round(100 * b["points"] / b["max_points"]) if b["max_points"] else 0,
             "reason": clip(b.get("reason"), 22), "cited": b.get("cites_source", True)}
            for b in problem.get("score_breakdown", [])]


def radar_points(ranked, dropped_count):
    """Place each problem on the radar: the closer to the centre, the higher
    the score. Blip size grows with the number of independent sources."""
    centre = RADAR_SIZE / 2
    shown = ranked[:MAX_PROBLEMS]
    points = []
    for i, p in enumerate(shown):
        angle = math.radians(-90 + i * 360 / max(len(shown), 1) + (20 if len(shown) > 1 else 0))
        distance = max(18.0, RADAR_RADIUS * (100 - p["score"]) / 80)
        points.append({
            "rank": p["rank"], "title": p["title"], "score": p["score"],
            "x": round(centre + distance * math.cos(angle), 1),
            "y": round(centre + distance * math.sin(angle), 1),
            "r": 5 + 2 * min(p.get("independent_sources", 2), 5),
            "strong": p["score"] >= STRONG_SCORE,
        })
    removed = []
    for i in range(min(dropped_count, 8)):
        angle = math.radians(200 + i * 22)
        removed.append({"x": round(centre + (RADAR_RADIUS + 8) * math.cos(angle), 1),
                        "y": round(centre + (RADAR_RADIUS + 8) * math.sin(angle), 1)})
    rings = [{"score": s, "r": round(RADAR_RADIUS * (100 - s) / 80, 1)} for s in (20, 40, 60, 80)]
    return {"size": RADAR_SIZE, "centre": centre, "points": points, "removed": removed, "rings": rings}


def build_insights(run):
    """The three or four facts that matter most, each as a number + a line.
    Chosen before the pages are laid out: the pages then explain them."""
    result = run.get("result", {})
    ranked = result.get("ranked") or []
    dropped = result.get("dropped") or []
    analysis = run.get("ai", {}).get("analysis") or {}
    proposed = len(analysis.get("problems") or []) + len(analysis.get("rejected") or []) \
        or len(ranked) + len(dropped)
    sources = run.get("evidence", {}).get("sources") or []

    if ranked:
        top = ranked[0]
        bars = sorted(top.get("score_breakdown", []), key=lambda b: b["points"] / b["max_points"])
        strong, weak = bars[-1], bars[0]
        insights = [
            {"figure": f"{top['score']:g}", "unit": "/100",
             "label": "Strongest opportunity",
             "text": f"{clip(top['title'], 10)}. Felt most by: {clip(top.get('who'), 14)}"},
            {"figure": f"{len(ranked)} of {proposed}", "unit": "",
             "label": "Problems that survived the evidence checks",
             "text": (f"{sum(p.get('verified_quotes', 0) for p in ranked)} verified quotes from "
                      f"{len(sources)} sources searched. Each survivor has at least two "
                      f"independent websites behind it.")},
            {"figure": f"{strong['score']}/5", "unit": "",
             "label": f"Value driver: {strong['label'].lower()}",
             "text": (f"Weakest point is {weak['label'].lower()} ({weak['score']}/5), "
                      f"so that is what to test first.") if weak is not strong else
                     "All five factors scored the same."},
        ]
        market = top.get("market") or {}
        if market.get("status") == "estimated":
            insights.append({"figure": money_range(market), "unit": "",
                             "label": "Estimated market for the top problem",
                             "text": f"{market.get('confidence', 'Low')} confidence, from a bottom-up formula."})
        else:  # no market size: show what the top problem's evidence rests on instead
            domains = _domains(top)
            insights.append({"figure": str(len(domains)), "unit": "",
                             "label": "Independent websites behind the top problem",
                             "text": (", ".join(domains[:3]) + ". Market size could not be estimated "
                                      "from the sources.")})
        return insights

    best = _best_lead(dropped)
    gaps = result.get("evidence_gaps") or []
    if best:
        lead_insight = {"figure": str(len(best["evidence_verified"])), "unit": "",
                        "label": "Verified quotes on the closest lead",
                        "text": f"{clip(best['title'], 12)} came nearest."}
    elif not quotes_saved(dropped):
        lead_insight = {"figure": str(len(dropped)), "unit": "", "label": "Problems removed",
                        "text": "This run was saved before quotes were kept for removed problems; reasons are on page 2."}
    else:
        lead_insight = {"figure": "0", "unit": "", "label": "Verified quotes on any lead",
                        "text": "No proposed problem had a quote that could be found in its source."}
    return [
        {"figure": f"0 of {proposed}", "unit": "", "label": "Problems that survived the evidence checks",
         "text": f"None had verified quotes from two independent websites, across {len(sources)} sources."},
        lead_insight,
        {"figure": str(len(gaps)), "unit": "", "label": "Questions the sources could not answer",
         "text": clip(gaps[0], 20) if gaps else "No specific gaps were recorded."},
        {"figure": "5", "unit": "", "label": "Interviews to run next",
         "text": "Talk to five people in the sector to find problems not yet written about online."},
    ]


def quotes_saved(dropped):
    """Runs saved before 23 Nov 2026 did not keep the quotes of removed problems."""
    return all("evidence" in d for d in dropped if d.get("title") != "Rejected by format check")


def _best_lead(dropped):
    """The removed problem that came closest: the one with most verified quotes."""
    best = None
    for d in dropped:
        verified = [e for e in d.get("evidence") or [] if e.get("status") == "verified"]
        if d.get("evidence") and (best is None or len(verified) > len(best["evidence_verified"])):
            best = {**d, "evidence_verified": verified}
    return best


def build_brief(run):
    """Everything the 5-page template needs, already trimmed to fit."""
    answers = run.get("answers", {})
    result = run.get("result", {})
    ranked = result.get("ranked") or []
    dropped = result.get("dropped") or []
    sources = run.get("evidence", {}).get("sources") or []
    conclusion = build_conclusion(run)
    payer = PAYER_WORDS.get(answers.get("payer"), "customers")

    brief = {
        "market": {"sector": answers.get("sector", ""),
                   "title": (answers.get("sector", "")[:1].upper() + answers.get("sector", "")[1:]), "geography": answers.get("geography", ""),
                   "payer": answers.get("payer", ""), "advantage": clip(answers.get("advantage"), 40),
                   "date": (run.get("meta", {}).get("created_at") or "")[:10],
                   "model": run.get("meta", {}).get("model", ""), "sources": len(sources)},
        "verdict": conclusion["verdict"], "level": conclusion["level"],
        "next_step": clip(conclusion["next_step"], 60),
        "insights": build_insights(run),
        "radar": radar_points(ranked, len(dropped)),
        "has_ranked": bool(ranked),
        "quotes_saved": quotes_saved(dropped),
        "landscape": [{"rank": p["rank"], "title": clip(p["title"], 10), "score": p["score"],
                       "confidence": p["confidence"], "sources": p.get("independent_sources", 0),
                       "who": clip(p.get("who"), 14), "bars": _factor_bars(p)}
                      for p in ranked[:MAX_PROBLEMS]],
        "removed": [{"title": clip(d["title"], 10), "reason": clip(d["reason"], 24)} for d in dropped[:5]],
        "gaps": [clip(g, 26) for g in (result.get("evidence_gaps") or [])[:4]],
        "sources_used": [],
    }

    if ranked:
        top = ranked[0]
        brief["value_statement"] = (
            f"The clearest value in {answers.get('sector', '')} ({answers.get('geography', '')}) "
            f"is solving “{clip(top['title'], 10)}”.")
        brief["value_cost"] = clip(top.get("consequence"), 30)
        lead = top
    else:
        lead = _best_lead(dropped)
        brief["value_statement"] = (
            f"No problem in {answers.get('sector', '')} ({answers.get('geography', '')}) had enough "
            f"independent, verified evidence to rank.")
        brief["value_cost"] = ("The value of this brief is knowing where the public evidence runs out, "
                               "before time or money is spent building.")

    if not lead:
        brief["plan"] = NO_SIGNAL_PLAN
    if lead:
        brief["lead"] = {
            "title": lead["title"], "ranked": bool(ranked),
            "who": clip(lead.get("who"), 22), "situation": clip(lead.get("situation"), 24),
            "consequence": clip(lead.get("consequence"), 26),
            "quotes": _quotes(lead, 4), "domains": _domains(lead),
            "touchpoints": [{"where": clip(t.get("where"), 10), "consequence": clip(t.get("consequence"), 18)}
                            for t in (lead.get("touchpoints") or [])[:3]],
            "reason": lead.get("reason", ""),
        }
        if ranked:
            market = lead.get("market") or {}
            scores = {b["factor"]: b for b in lead.get("score_breakdown", [])}
            gap = scores.get("competition_gap", {})
            brief["market_view"] = {
                "status": market.get("status"),
                "low": market.get("low"), "high": market.get("high"),
                "currency": market.get("currency", "GBP"), "unit": market.get("unit", "per year"),
                "formula": clip(market.get("formula"), 30),
                "confidence": market.get("confidence", "Low"),
                "reason": clip(market.get("reason"), 40),
                "trends": [{"trend": clip(t.get("trend"), 16), "type": t.get("type", ""),
                            "sourced": t.get("status") == "sourced"}
                           for t in (lead.get("micro_trends") or [])[:3]],
                "alternatives": [{"name": clip(a.get("name"), 6), "offer": clip(a.get("offer"), 16),
                                  "sourced": a.get("status") == "sourced"}
                                 for a in (lead.get("existing_alternatives") or [])[:4]],
                "gap_score": gap.get("score"), "gap_reason": clip(gap.get("reason"), 30),
                "founder_fit": clip(lead.get("founder_fit"), 45),
            }
            if len(ranked) > 1:
                second = ranked[1]
                brief["runner_up"] = {"title": clip(second["title"], 12), "score": second["score"],
                                      "who": clip(second.get("who"), 18),
                                      "consequence": clip(second.get("consequence"), 26),
                                      "sources": second.get("independent_sources", 0)}
            experiment = lead.get("experiment") or {}
            brief["plan"] = {
                "assumption": clip(lead.get("riskiest_assumption"), 40),
                "type": experiment.get("type", ""),
                "objective": clip(experiment.get("objective"), 36),
                "participants": clip(experiment.get("participants"), 24),
                "steps": [clip(s, 20) for s in (experiment.get("steps") or [])[:5]],
                "budget": experiment.get("budget", ""),
                "success": clip(experiment.get("success_criteria"), 30),
                "failure": clip(experiment.get("failure_criteria"), 30),
            }
        if not ranked:
            brief["plan"] = NO_SIGNAL_PLAN
        cited = {q["source_id"] for q in brief["lead"]["quotes"] if q["verified"]}
        brief["sources_used"] = [{"id": s["id"], "title": clip(s.get("title"), 12), "domain": s.get("domain", ""),
                                  "url": s.get("url", "")} for s in sources if s.get("id") in cited]
    return brief
