"""Step 4 of the pipeline: check the AI's work and rank the problems.

Everything here is plain Python, so the same input always gives the same
output and every rule can be unit-tested:

- quote verification against the retrieved source text
- the two-independent-source rule (copies and same-site pages count once)
- market-size checks (sourced inputs only, never GDP)
- the opportunity score and confidence level
"""

import re
import unicodedata

# Initial weights from the MVP plan. These are assumptions, not research
# findings, and are documented as such in docs/development_log.md.
WEIGHTS = {
    "severity": 0.30,
    "frequency": 0.20,
    "market": 0.20,
    "willingness_to_pay": 0.15,
    "competition_gap": 0.15,
}
FACTOR_LABELS = {
    "severity": "Problem severity",
    "frequency": "Frequency",
    "market": "Market potential",
    "willingness_to_pay": "Willingness to pay",
    "competition_gap": "Competition gap",
}

MIN_QUOTE_WORDS = 6
MIN_INDEPENDENT_SOURCES = 2
DUPLICATE_SIMILARITY = 0.5  # share of overlapping 5-word phrases that marks a copy

# On these sites each thread is written by different people, so separate
# threads count as separate sources. Everywhere else, one website = one source.
FORUM_DOMAINS = {"news.ycombinator.com", "reddit.com", "quora.com",
                 "stackexchange.com", "trustpilot.com"}

_PUNCTUATION_MAP = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
})


# ---------------------------------------------------------------- quotes

def normalise_for_match(text):
    """Lower-case, unify quote marks, drop punctuation, collapse spaces."""
    text = unicodedata.normalize("NFKC", text or "").translate(_PUNCTUATION_MAP).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def verify_quote(quote, source_text):
    """True only if the quote appears word for word in the source text.

    Capitals, punctuation and spacing are ignored; words are not.
    Very short quotes are never treated as verified.
    """
    q = normalise_for_match(quote)
    words = q.split()
    if len(words) < MIN_QUOTE_WORDS:
        return False
    text = f" {normalise_for_match(source_text)} "
    if f" {q} " in text:
        return True
    # A quote that stops mid-way through its final word ("tighter regul")
    # still matches, as long as every earlier word matches exactly.
    head, last = " ".join(words[:-1]), words[-1]
    if len(last) >= 3 and re.search(rf" {re.escape(head)} {re.escape(last)}[a-z0-9]* ", text):
        return True
    return False


# --------------------------------------------------------- independence

def registrable_domain(domain):
    """'news.bbc.co.uk' -> 'bbc.co.uk', 'blog.example.com' -> 'example.com'."""
    parts = (domain or "").lower().split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in {"co", "ac", "gov", "org", "com", "net"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _identity(source):
    site = registrable_domain(source.get("domain", ""))
    if site in FORUM_DOMAINS or source.get("domain") in FORUM_DOMAINS:
        return source.get("url", site)
    return site


def _shingles(text, size=5):
    words = normalise_for_match(text)[:4000].split()
    return {tuple(words[i:i + size]) for i in range(max(0, len(words) - size + 1))}


def text_similarity(a, b):
    sa, sb = _shingles(a), _shingles(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def independent_groups(source_ids, sources_by_id):
    """Group sources that are NOT independent of each other.

    Two sources are grouped if they come from the same website (forum
    threads excepted) or if one largely copies the other's text.
    Returns a list of groups; its length is the number of independent sources.
    """
    ids = [i for i in dict.fromkeys(source_ids) if i in sources_by_id]
    parent = {i: i for i in ids}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for x_pos, x in enumerate(ids):
        for y in ids[x_pos + 1:]:
            sx, sy = sources_by_id[x], sources_by_id[y]
            same = _identity(sx) == _identity(sy) or \
                text_similarity(sx.get("text", ""), sy.get("text", "")) >= DUPLICATE_SIMILARITY
            if same:
                parent[find(y)] = find(x)

    groups = {}
    for i in ids:
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


# ---------------------------------------------------------------- scores

def compute_score(scores):
    """Weighted score on a 20-100 scale from five 1-5 factor scores.

    Returns (total, breakdown). Raises ValueError for a missing or invalid score.
    """
    breakdown, total = [], 0.0
    for factor, weight in WEIGHTS.items():
        item = scores.get(factor)
        value = item.get("score") if isinstance(item, dict) else None
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"invalid score for {factor}: {value!r}")
        weighted = 20 * weight * value
        total += weighted
        breakdown.append({
            "factor": factor,
            "label": FACTOR_LABELS[factor],
            "weight_pct": round(weight * 100),
            "score": value,
            "points": round(weighted, 1),
            "max_points": round(20 * weight * 5, 1),
            "reason": item.get("reason", ""),
            "cites_source": bool(re.search(r"\bS\d+\b", item.get("reason", ""))),
        })
    return round(total, 1), breakdown


def confidence_level(independent_sources, verified_quotes, total_quotes):
    """Evidence-based confidence: more independent verified sources = higher.

    Dropped one level when fewer than half of the quotes could be verified.
    """
    levels = ["Low", "Medium", "High"]
    if independent_sources >= 4:
        index = 2
    elif independent_sources == 3:
        index = 1
    else:
        index = 0
    if total_quotes and verified_quotes / total_quotes < 0.5:
        index = max(0, index - 1)
    return levels[index]


# ----------------------------------------------------------- market size

_GDP = re.compile(r"\bgdp\b|gross domestic product|whole economy|national economy", re.I)


def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d.]", "", value)
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    return None


_SCALES = {"thousand": 1e3, "k": 1e3, "million": 1e6, "mn": 1e6, "m": 1e6,
           "billion": 1e9, "bn": 1e9, "b": 1e9, "trillion": 1e12, "tn": 1e12}
_NUMBER = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(thousand|million|billion|trillion|bn|mn|tn|k|m|b)?\b", re.I)
_MULTIPLY = re.compile(r"\s[x\u00d7*]\s|\u00d7|\*|\btimes\b|multipl", re.I)


def _numbers(text):
    """All numbers in a text, with scale words applied ("48.1 Billion" -> 48.1e9)."""
    found = []
    for digits, scale in _NUMBER.findall(text or ""):
        try:
            value = float(digits.replace(",", ""))
        except ValueError:
            continue
        found.append(value * _SCALES.get(scale.lower(), 1) if scale else value)
    return found


def number_in_source(value, source_text):
    """True if the first number in `value` appears in the source (within 1%)."""
    wanted = _numbers(str(value))
    if not wanted:
        return False
    target = wanted[0]
    return any(abs(n - target) <= 0.01 * max(abs(target), 1) for n in _numbers(source_text))


def check_market_size(market, sources_by_id):
    """Accept a market-size range only when it is transparent and sourced."""
    market = market if isinstance(market, dict) else {}
    not_yet = {
        "status": "not_estimated",
        "reason": market.get("reason_if_not") or "The sources did not give the inputs needed.",
    }
    if not market.get("can_estimate"):
        return not_yet

    low, high = _number(market.get("low")), _number(market.get("high"))
    formula = (market.get("formula") or "").strip()
    inputs = [i for i in market.get("inputs", []) if isinstance(i, dict)]
    problems = []
    if low is None or high is None or low <= 0 or high < low:
        problems.append("the low-high range is missing or invalid")
    if not formula:
        problems.append("no formula was given")
    if not inputs:
        problems.append("no inputs were listed")
    unsourced = [i.get("name", "an input") for i in inputs
                 if str(i.get("source_id", "")).upper() not in sources_by_id]
    if unsourced:
        problems.append("these inputs have no valid source: " + ", ".join(unsourced))
    text_to_check = " ".join([formula] + [f"{i.get('name', '')} {i.get('value', '')}" for i in inputs])
    if _GDP.search(text_to_check):
        problems.append("it used national GDP or the whole economy as a market size")
    # Added 17 Nov 2026: a live run passed off a whole-market valuation
    # (2025 value as "low", 2035 forecast as "high") as a market size.
    if formula and (len(inputs) < 2 or not _MULTIPLY.search(f" {formula} ")):
        problems.append("it is not a bottom-up calculation (customers multiplied by spend); "
                        "a whole-industry valuation or forecast is not this problem's market")
    not_found = [i.get("name", "an input") for i in inputs
                 if str(i.get("source_id", "")).upper() in sources_by_id
                 and not number_in_source(i.get("value", ""),
                                          sources_by_id[str(i["source_id"]).upper()].get("text", ""))]
    if not_found:
        problems.append("these input figures were not found in their sources: " + ", ".join(not_found))
    if problems:
        return {"status": "not_estimated",
                "reason": "The AI's estimate was rejected because " + "; ".join(problems) + "."}

    input_sites = {registrable_domain(sources_by_id[str(i["source_id"]).upper()]["domain"])
                   for i in inputs}
    confidence = "Medium" if len(input_sites) >= 2 else "Low"
    return {
        "status": "estimated",
        "low": low,
        "high": high,
        "currency": market.get("currency") or "GBP",
        "unit": market.get("unit") or "per year",
        "formula": formula,
        "inputs": [{"name": i.get("name", ""), "value": str(i.get("value", "")),
                    "source_id": str(i.get("source_id", "")).upper()} for i in inputs],
        "assumptions": [a for a in market.get("assumptions", []) if isinstance(a, str)],
        "confidence": confidence,
    }


# --------------------------------------------------------------- process

def process(analysis, sources):
    """Apply every evidence rule, score the survivors and rank them.

    Returns {"ranked", "top_three", "dropped", "evidence_gaps"}.
    """
    sources_by_id = {s["id"]: s for s in sources}
    ranked, dropped = [], []

    for problem in analysis.get("problems", []):
        checked_evidence = []
        for item in problem.get("evidence", []):
            source = sources_by_id.get(item["source_id"])
            if source is None:
                status = "unknown_source"
            elif verify_quote(item["quote"], source.get("text", "")):
                status = "verified"
            else:
                status = "unverified"
            summary = None
            if source is not None:
                summary = {k: source.get(k, "") for k in
                           ("id", "title", "url", "domain", "published", "origin")}
            checked_evidence.append({**item, "status": status, "source": summary})

        verified = [e for e in checked_evidence if e["status"] == "verified"]
        groups = independent_groups([e["source_id"] for e in verified], sources_by_id)
        independent = len(groups)
        quotes_with_source = [e for e in checked_evidence if e["status"] != "unknown_source"]

        if independent < MIN_INDEPENDENT_SOURCES:
            dropped.append({
                "title": problem["title"],
                "reason": (f"Only {independent} independent source(s) with a verified quote; "
                           f"at least {MIN_INDEPENDENT_SOURCES} are required."),
                "evidence": checked_evidence,  # shown in the report so the reader can judge
            })
            continue

        try:
            score, breakdown = compute_score(problem["scores"])
        except ValueError as exc:
            dropped.append({"title": problem["title"], "reason": f"Could not be scored: {exc}."})
            continue

        trends = []
        for trend in problem.get("micro_trends", []):
            valid = [s for s in trend.get("source_ids", []) if s in sources_by_id]
            trends.append({**trend, "source_ids": valid,
                           "status": "sourced" if valid else "unverified"})

        alternatives = []
        for alt in problem.get("existing_alternatives", []):
            alternatives.append({**alt, "status": "sourced" if alt.get("source_id") in sources_by_id
                                 else "unverified"})

        ranked.append({
            **problem,
            "evidence": checked_evidence,
            "micro_trends": trends,
            "existing_alternatives": alternatives,
            "independent_sources": independent,
            "independent_groups": groups,
            "verified_quotes": len(verified),
            "total_quotes": len(quotes_with_source),
            "confidence": confidence_level(independent, len(verified), len(quotes_with_source)),
            "score": score,
            "score_breakdown": breakdown,
            "market": check_market_size(problem.get("market_size"), sources_by_id),
        })

    ranked.sort(key=lambda p: (p["score"], p["independent_sources"]), reverse=True)
    for rank, problem in enumerate(ranked, start=1):
        problem["rank"] = rank

    gaps = list(analysis.get("evidence_gaps", []))
    return {
        "ranked": ranked,
        "top_three": ranked[:3],
        "dropped": dropped + [{"title": "Rejected by format check", "reason": r}
                              for r in analysis.get("rejected", [])],
        "evidence_gaps": gaps,
    }
