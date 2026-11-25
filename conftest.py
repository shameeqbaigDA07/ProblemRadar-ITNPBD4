"""Shared test data. No test needs internet access or API keys."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ARTICLE_A = ("Independent vet clinics report that recruiting qualified veterinary nurses "
             "has become the single biggest operational problem, with vacancies left open "
             "for six months and locum costs rising sharply across rural practices.")
ARTICLE_B = ("A survey of practice managers found that appointment no-shows cost small "
             "clinics thousands of pounds every year because reminder systems are manual "
             "and owners rarely confirm bookings in advance.")
ARTICLE_C = ("On the forum, one practice owner wrote that the booking software they pay for "
             "still cannot send text reminders without an expensive add-on module.")


def make_source(sid, domain, text, url=None):
    return {
        "id": sid, "title": f"Title {sid}", "url": url or f"https://{domain}/{sid.lower()}",
        "domain": domain, "published": "2026-10-01", "origin": "Tavily",
        "query_label": "Problems and challenges", "snippet": text[:200], "text": text,
    }


@pytest.fixture
def sources():
    return [
        make_source("S1", "vettimes.co.uk", ARTICLE_A),
        make_source("S2", "news.vetsurvey.org", ARTICLE_B),
        make_source("S3", "news.ycombinator.com", ARTICLE_C,
                    url="https://news.ycombinator.com/item?id=111"),
    ]


def scores(value=3):
    return {f: {"score": value, "reason": "Based on S1"} for f in
            ("severity", "frequency", "market", "willingness_to_pay", "competition_gap")}


@pytest.fixture
def good_problem():
    return {
        "title": "Missed appointments",
        "who": "Small independent vet clinics",
        "situation": "When owners book and do not turn up",
        "consequence": "Lost revenue every week",
        "evidence": [
            {"source_id": "S2", "quote": "appointment no-shows cost small clinics thousands of pounds every year",
             "supports": "cost"},
            {"source_id": "S3", "quote": "still cannot send text reminders without an expensive add-on module",
             "supports": "tool gap"},
        ],
        "touchpoints": [{"where": "Booking", "consequence": "No confirmation"}],
        "micro_trends": [{"trend": "SMS reminders expected", "type": "behaviour", "source_ids": ["S3"]}],
        "existing_alternatives": [{"name": "Booking add-on", "offer": "Text reminders", "source_id": "S3"}],
        "market_size": {"can_estimate": False, "reason_if_not": "No clinic count found."},
        "scores": scores(4),
        "founder_fit": "Relevant", "riskiest_assumption": "Clinics will pay",
        "experiment": {"objective": "Test demand", "participants": "10 clinics",
                       "steps": ["Interview"], "success_criteria": "6 of 10",
                       "failure_criteria": "Fewer than 3"},
        "unverified_notes": [],
    }


@pytest.fixture
def answers():
    return {"sector": "independent vet clinics", "geography": "UK", "payer": "Businesses",
            "advantage": "Former practice manager", "exclude": ""}


@pytest.fixture(autouse=True)
def no_real_backup_keys(monkeypatch):
    """The app loads the real .env when imported. Remove the backup AI keys so
    no test can ever call Groq or Mistral over the internet; tests that need
    a key set a fake one themselves."""
    for name in ("GROQ_API_KEY", "MISTRAL_API_KEY", "AI_PROVIDER", "GROQ_MODEL", "MISTRAL_MODEL"):
        monkeypatch.delenv(name, raising=False)
