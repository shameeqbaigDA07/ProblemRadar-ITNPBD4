"""The report's final conclusion, written by Python from the checked results.

Why not ask the AI to write it? A conclusion written by Python can only
repeat what the evidence checks and the score formula produced, so it can
never contradict the ranking or add unverified claims. It also works for
runs saved before this feature existed, because it is built when the
report is shown.
"""


def _verdict(top):
    """One-line verdict from the top problem's score and confidence."""
    score, confidence = top["score"], top["confidence"]
    if score >= 75 and confidence in ("Medium", "High"):
        return "strong", "Strong candidate: worth testing now"
    if score >= 65 and confidence in ("Medium", "High"):
        return "good", "Worth testing"
    if score >= 65:
        return "promising", "Promising, but the evidence is thin: test it cheaply before committing"
    return "weak", "Weak signal: gather more evidence before testing"


def _strongest_and_weakest(breakdown):
    by_points = sorted(breakdown, key=lambda b: b["points"] / b["max_points"])
    return by_points[-1], by_points[0]


def _sentence(text):
    text = (text or "").strip()
    if not text:
        return ""
    text = text[0].lower() + text[1:] if not text[:2].isupper() else text
    return text.rstrip(".")


def build_conclusion(run):
    """Return {"level", "verdict", "paragraphs", "next_step", "caveat"}."""
    answers = run.get("answers", {})
    result = run.get("result", {})
    ranked = result.get("ranked") or []
    dropped = result.get("dropped") or []
    sources = run.get("evidence", {}).get("sources") or []
    analysis = run.get("ai", {}).get("analysis") or {}
    # count every problem the AI proposed, including ones rejected by the format check
    proposed = (len(analysis.get("problems") or []) + len(analysis.get("rejected") or [])) \
        or len(ranked) + len(dropped)
    sector, geography = answers.get("sector", "this sector"), answers.get("geography", "")

    removed = f", and {len(dropped)} {'was' if len(dropped) == 1 else 'were'} removed" if dropped else ""
    found = (f"Problem Radar searched {len(sources)} public sources about {sector}"
             f"{f' in the {geography} market' if geography else ''}. The AI proposed {proposed} "
             f"problem{'s' if proposed != 1 else ''}; after Python checked every quote, "
             f"{len(ranked)} had verified evidence from at least two independent websites{removed}.")

    if not ranked:
        return {
            "level": "none",
            "verdict": "No opportunity is ready to test yet",
            "paragraphs": [found, "None of the proposed problems had enough verified, independent "
                                  "evidence to be ranked. This is a result in itself: the public "
                                  "sources found do not yet show a clear, repeated pain point."],
            "next_step": "Try a narrower or differently worded sector, or interview five people in "
                         "the sector to find problems that are not yet written about online.",
            "caveat": "This conclusion was written by the app from the checks above, not by the AI.",
        }

    top = ranked[0]
    level, verdict = _verdict(top)
    strong, weak = _strongest_and_weakest(top["score_breakdown"])
    paragraphs = [found]

    lead = (f"The strongest opportunity is “{top['title']}”, scoring {top['score']:g}/100 "
            f"with {top['confidence'].lower()} confidence. It affects {_sentence(top['who'])}: "
            f"{_sentence(top['consequence'])}.")
    if strong["factor"] != weak["factor"]:
        lead += (f" Its score is driven mainly by {strong['label'].lower()} ({strong['score']}/5) "
                 f"and held back by {weak['label'].lower()} ({weak['score']}/5).")
    paragraphs.append(lead)

    if len(ranked) > 1:
        others = ", ".join(f"“{p['title']}” ({p['score']:g}/100)" for p in ranked[1:3])
        paragraphs.append(f"The next option{'s are' if len(ranked) > 2 else ' is'} {others}.")

    market = top.get("market") or {}
    if market.get("status") == "estimated":
        paragraphs.append(
            f"The market for the top problem is estimated at {market.get('currency', 'GBP')} "
            f"{market['low']:,.0f} to {market['high']:,.0f} {market.get('unit', 'per year')} "
            f"({market.get('confidence', 'Low').lower()} confidence), using the formula shown in its card.")
    else:
        paragraphs.append("The sources did not contain the figures needed to estimate the market "
                          "size of the top problem, so how big this opportunity is remains unknown.")

    if top.get("riskiest_assumption"):
        paragraphs.append(f"The riskiest assumption to test first, as identified by the AI, is: "
                          f"{_sentence(top['riskiest_assumption'])}.")

    experiment = top.get("experiment") or {}
    next_step = "Talk to five potential customers about this problem before building anything."
    if experiment.get("objective"):
        next_step = f"Run the two-week experiment for “{top['title']}”: {_sentence(experiment['objective'])}"
        if experiment.get("participants"):
            next_step += f", with {_sentence(experiment['participants'])}"
        next_step += "."
        if experiment.get("success_criteria"):
            next_step += f" Treat it as a success if {_sentence(experiment['success_criteria'])}."
        if experiment.get("failure_criteria"):
            fallback = f" and move to “{ranked[1]['title']}”" if len(ranked) > 1 else ""
            next_step += f" Stop{fallback} if {_sentence(experiment['failure_criteria'])}."

    verified = sum(p.get("verified_quotes", 0) for p in ranked)
    caveat = (f"This conclusion was written by the app from the checked results above, not by the AI. "
              f"It rests on {verified} verified quote{'s' if verified != 1 else ''} and has not been "
              f"reviewed by a person: open the source links before acting on it.")
    return {"level": level, "verdict": verdict, "paragraphs": paragraphs,
            "next_step": next_step, "caveat": caveat}
