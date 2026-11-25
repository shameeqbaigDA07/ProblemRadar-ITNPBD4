"""Tests for evidence gathering and API error handling (all APIs are faked)."""

import pytest

from errors import ConfigError, ResearchError
from research import build_queries, gather_evidence, normalise_url


class FakeTavily:
    """Pretends to be the Tavily client. Can be told to fail."""

    def __init__(self, results=None, fail_with=None, fail_on=()):
        self.results = results
        self.fail_with = fail_with
        self.fail_on = set(fail_on)
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append((query, kwargs))
        if self.fail_with and (not self.fail_on or len(self.calls) in self.fail_on):
            raise self.fail_with
        if self.results is not None:
            return {"results": self.results}
        n = len(self.calls)
        return {"results": [{
            "title": f"Article {n}", "url": f"https://site{n}.com/page",
            "content": f"Snippet {n}", "raw_content": f"<p>Full text of article {n}</p>",
            "published_date": "2026-09-30T10:00:00Z",
        }]}


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status = payload, status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    def json(self):
        return self.payload


HN_PAYLOAD = {"hits": [
    {"objectID": "42", "title": None, "story_title": "Running a vet clinic",
     "comment_text": "<p>Our clinic loses hours every week chasing owners who miss appointments "
                     "and never answer the phone.</p>", "created_at": "2026-05-01T00:00:00Z",
     "author": "someone"},
    {"objectID": "43", "comment_text": "too short", "created_at": "2026-05-01T00:00:00Z"},
]}


def hn_ok(*args, **kwargs):
    return FakeResponse(HN_PAYLOAD)


def hn_down(*args, **kwargs):
    return FakeResponse({}, status=503)


# Exceptions named like the real tavily-python ones.
class UsageLimitExceededError(Exception):
    pass


class InvalidAPIKeyError(Exception):
    pass


class TimeoutError(Exception):  # noqa: A001 - mirrors tavily's own name
    pass


def test_six_queries_are_built(answers):
    queries = build_queries(answers, year=2026)
    assert len(queries) == 6
    assert queries[0]["query"].startswith("independent vet clinics UK")
    assert "include_domains" in queries[5]["options"]


def test_sources_are_numbered_and_cleaned(answers):
    out = gather_evidence(answers, tavily_client=FakeTavily(), http_get=hn_ok)
    ids = [s["id"] for s in out["sources"]]
    assert ids == [f"S{i}" for i in range(1, len(ids) + 1)]
    assert out["sources"][0]["text"] == "Full text of article 1"   # HTML removed
    assert out["sources"][0]["published"] == "2026-09-30"
    hn = [s for s in out["sources"] if s["origin"] == "Hacker News"]
    assert len(hn) == 1                                   # short comment skipped
    assert "someone" not in str(hn[0])                    # usernames not stored


def test_duplicate_urls_are_removed(answers):
    same = [{"title": "A", "url": "https://www.example.com/page/", "content": "x y z"}]
    out = gather_evidence(answers, tavily_client=FakeTavily(results=same), http_get=hn_down)
    assert len(out["sources"]) == 1


def test_missing_tavily_key_raises_config_error(answers, monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="TAVILY_API_KEY"):
        gather_evidence(answers)


def test_used_up_quota_stops_the_run(answers):
    client = FakeTavily(fail_with=UsageLimitExceededError("limit"))
    with pytest.raises(ResearchError, match="credits"):
        gather_evidence(answers, tavily_client=client, http_get=hn_ok)


def test_bad_key_stops_the_run(answers):
    client = FakeTavily(fail_with=InvalidAPIKeyError("bad"))
    with pytest.raises(ResearchError, match="API key"):
        gather_evidence(answers, tavily_client=client, http_get=hn_ok)


def test_one_failed_search_is_skipped_with_a_warning(answers):
    client = FakeTavily(fail_with=TimeoutError("slow"), fail_on={2})
    out = gather_evidence(answers, tavily_client=client, http_get=hn_ok)
    assert len(client.calls) == 6
    assert any("Market size" in w for w in out["warnings"])
    assert len(out["sources"]) == 6   # 5 Tavily results + 1 HN


def test_hacker_news_outage_is_only_a_warning(answers):
    out = gather_evidence(answers, tavily_client=FakeTavily(), http_get=hn_down)
    assert any("Hacker News" in w for w in out["warnings"])
    assert len(out["sources"]) == 6


def test_no_evidence_at_all_raises(answers):
    with pytest.raises(ResearchError, match="No public evidence"):
        gather_evidence(answers, tavily_client=FakeTavily(results=[]), http_get=hn_down)


def test_normalise_url():
    assert normalise_url("https://www.Example.com/a/?utm_source=x") == "example.com/a"
    assert normalise_url("https://news.ycombinator.com/item?id=5") == "news.ycombinator.com/item?id=5"


# ---- the direct HTTP connection to Tavily (replaces the tavily-python library)

import requests as _requests

from research import TAVILY_SEARCH_URL, TavilyHTTPClient


class FakeHTTPResponse:
    def __init__(self, status, payload=None):
        self.status_code, self.payload = status, payload or {}

    def json(self):
        return self.payload


def recording_post(status, payload=None):
    calls = []

    def post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers})
        return FakeHTTPResponse(status, payload)

    post.calls = calls
    return post


def test_http_client_sends_key_as_bearer_and_returns_results():
    post = recording_post(200, {"results": [{"url": "https://a.com", "content": "x"}]})
    client = TavilyHTTPClient("tvly-test", http_post=post)
    out = client.search("vet clinics", max_results=5, include_domains=None)
    assert out["results"][0]["url"] == "https://a.com"
    call = post.calls[0]
    assert call["url"] == TAVILY_SEARCH_URL
    assert call["headers"]["Authorization"] == "Bearer tvly-test"
    assert call["json"] == {"query": "vet clinics", "max_results": 5}   # None values dropped


@pytest.mark.parametrize("status, expected", [
    (401, "API key"), (432, "credits"), (433, "credits"),
])
def test_http_client_fatal_statuses_stop_the_run(answers, status, expected):
    client = TavilyHTTPClient("tvly-test", http_post=recording_post(status))
    with pytest.raises(ResearchError, match=expected):
        gather_evidence(answers, tavily_client=client, http_get=hn_ok)


def test_http_client_server_error_is_only_a_warning(answers):
    client = TavilyHTTPClient("tvly-test", http_post=recording_post(500))
    out = gather_evidence(answers, tavily_client=client, http_get=hn_ok)
    assert len(out["warnings"]) == 6
    assert "HTTP 500" in out["warnings"][0]
    assert len(out["sources"]) == 1   # only Hacker News left


def test_http_client_timeout_is_only_a_warning(answers):
    def slow(*args, **kwargs):
        raise _requests.Timeout()
    client = TavilyHTTPClient("tvly-test", http_post=slow)
    out = gather_evidence(answers, tavily_client=client, http_get=hn_ok)
    assert "timed out" in out["warnings"][0]



def test_hacker_news_does_not_broaden_the_search_when_nothing_matches(answers):
    """Regression (17 Nov 2026): an optional-words fallback pulled in
    unrelated threads (Treasury yields, Splunk onboarding). Removed."""
    calls = []

    def hn(url, params=None, timeout=None):
        calls.append(params)
        return FakeResponse({"hits": []})

    out = gather_evidence(answers, tavily_client=FakeTavily(), http_get=hn)
    assert len(calls) == 1
    assert "optionalWords" not in calls[0]
    assert not any(s["origin"] == "Hacker News" for s in out["sources"])
