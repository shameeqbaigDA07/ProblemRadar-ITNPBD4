"""Step 2 of the pipeline: collect public evidence.

Runs six Tavily web searches and one Hacker News search, then returns a
numbered list of sources (S1, S2, ...). Nothing here uses AI: it only
collects and tidies what the search services return.
"""

import html
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

from errors import ConfigError, ResearchError

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"

# How much text we keep per source. TEXT_LIMIT is what the quote checker
# searches; the analysis prompt sends a shorter excerpt (see analyse.py).
SNIPPET_LIMIT = 600
TEXT_LIMIT = 6000

RESULTS_PER_QUERY = 5
HN_RESULTS = 10

# Discussion sites for the forum-focused search. Pages from these sites
# arrive only as ordinary search results (title, snippet, link); the app
# never scrapes them directly.
FORUM_DOMAINS = [
    "reddit.com",
    "quora.com",
    "news.ycombinator.com",
    "stackexchange.com",
    "trustpilot.com",
]

GEOGRAPHY_WORDS = {"UK": "UK", "EU": "Europe EU", "US": "US", "Global": "global"}
PAYER_WORDS = {"Businesses": "businesses B2B", "Consumers": "consumers", "Either": ""}


def build_queries(answers, year=None):
    """Turn the founder's form answers into the six search queries.

    Returns a list of dicts: {"label", "query", "options"}.
    """
    year = year or datetime.now().year
    sector = answers["sector"].strip()
    geo = GEOGRAPHY_WORDS.get(answers.get("geography"), "")
    payer = PAYER_WORDS.get(answers.get("payer"), "")

    def tidy(text):
        return re.sub(r"\s+", " ", text).strip()

    return [
        {"label": "Problems and challenges",
         "query": tidy(f"{sector} {geo} {payer} biggest problems challenges pain points"),
         "options": {}},
        {"label": "Market size",
         "query": tidy(f"{sector} {geo} market size revenue number of businesses"),
         "options": {}},
        {"label": "Customer complaints",
         "query": tidy(f"{sector} {geo} {payer} customer complaints reviews frustrations"),
         "options": {}},
        {"label": "Regulation changes",
         "query": tidy(f"{sector} {geo} new regulation rules changes {year}"),
         "options": {}},
        {"label": "Funding and developments",
         "query": tidy(f"{sector} {geo} startups funding investment {year}"),
         "options": {}},
        {"label": "Forum discussions",
         "query": tidy(f"{sector} problems frustrations discussion"),
         "options": {"include_domains": FORUM_DOMAINS}},
    ]


def normalise_url(url):
    """Make two spellings of the same address compare equal."""
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/")
    # Keep the query string only where it identifies the page (e.g. HN item ids).
    keep_query = parsed.query if "id=" in parsed.query else ""
    return f"{host}{path}" + (f"?{keep_query}" if keep_query else "")


def domain_of(url):
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def clean_text(raw):
    """Remove HTML tags and extra spaces."""
    if not raw:
        return ""
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(raw)))
    return re.sub(r"\s+", " ", text).strip()


TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilyError(Exception):
    """A Tavily request failed."""


class InvalidAPIKeyError(TavilyError):
    """Tavily answered 401: the key is missing, wrong or expired."""


class UsageLimitExceededError(TavilyError):
    """Tavily answered 432/433: the plan's credits are used up."""


class TavilyTimeoutError(TavilyError):
    """Tavily did not answer in time."""


class TavilyHTTPClient:
    """Calls Tavily's web API directly with `requests`.

    We do not use the tavily-python library: on the student's Windows PC,
    Smart App Control blocked a compiled file (tiktoken) that the library
    loads. Plain HTTP needs no compiled files.
    """

    def __init__(self, api_key, http_post=None, timeout=60):
        self.api_key = api_key
        self.http_post = http_post or requests.post
        self.timeout = timeout

    def search(self, query, **options):
        body = {"query": query, **{k: v for k, v in options.items() if v is not None}}
        try:
            response = self.http_post(
                TAVILY_SEARCH_URL,
                json=body,
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise TavilyTimeoutError("timed out") from exc
        except requests.RequestException as exc:
            raise TavilyError(f"network error ({type(exc).__name__})") from exc

        status = response.status_code
        if status == 401:
            raise InvalidAPIKeyError("invalid key")
        if status in (432, 433):
            raise UsageLimitExceededError("usage limit")
        if status >= 400:
            raise TavilyError(f"HTTP {status}")
        return response.json()


def _classify_tavily_error(exc):
    """Decide whether a Tavily error should stop the whole run.

    Returns (is_fatal, message).
    """
    name = type(exc).__name__
    if name in ("InvalidAPIKeyError", "MissingAPIKeyError", "ForbiddenError"):
        return True, ("Tavily rejected the API key. Check TAVILY_API_KEY in your "
                      ".env file, then restart the app.")
    if name == "UsageLimitExceededError":
        return True, ("Your free Tavily credits for this month are used up. "
                      "Open a saved run instead, or wait for the monthly reset.")
    if name in ("TimeoutError", "TavilyTimeoutError"):
        return False, "A Tavily search timed out."
    return False, f"A Tavily search failed ({exc})."


def search_tavily(client, query_spec):
    """Run one Tavily search and return a list of raw source dicts."""
    response = client.search(
        query=query_spec["query"],
        search_depth="basic",
        max_results=RESULTS_PER_QUERY,
        include_raw_content=True,
        **query_spec["options"],
    )
    sources = []
    for item in response.get("results", []) or []:
        url = item.get("url") or ""
        if not url:
            continue
        snippet = clean_text(item.get("content"))
        text = clean_text(item.get("raw_content")) or snippet
        if not text:
            continue
        sources.append({
            "title": clean_text(item.get("title")) or domain_of(url),
            "url": url,
            "domain": domain_of(url),
            "published": (item.get("published_date") or "")[:10],
            "origin": "Tavily",
            "query_label": query_spec["label"],
            "snippet": snippet[:SNIPPET_LIMIT],
            "text": text[:TEXT_LIMIT],
        })
    return sources


def search_hacker_news(sector, http_get=None, now=None):
    """Search Hacker News stories and comments from the last two years.

    Usernames are deliberately not stored.
    """
    http_get = http_get or requests.get
    now = now or time.time()
    two_years_ago = int(now - 2 * 365 * 24 * 3600)
    response = http_get(
        HN_SEARCH_URL,
        params={
            "query": sector,
            "tags": "(story,comment)",
            "hitsPerPage": HN_RESULTS,
            "numericFilters": f"created_at_i>{two_years_ago}",
        },
        timeout=20,
    )
    response.raise_for_status()
    # Exact search only. A broader "optional words" search was tried on
    # 17 Nov 2026 and removed: it filled the evidence with unrelated threads.
    hits = response.json().get("hits", [])
    sources = []
    for hit in hits:
        object_id = hit.get("objectID")
        if not object_id:
            continue
        text = clean_text(hit.get("comment_text") or hit.get("story_text") or hit.get("title"))
        if len(text) < 80:  # too short to be useful evidence
            continue
        title = clean_text(hit.get("title") or hit.get("story_title")) or "Hacker News discussion"
        url = f"https://news.ycombinator.com/item?id={object_id}"
        sources.append({
            "title": f"HN: {title}",
            "url": url,
            "domain": "news.ycombinator.com",
            "published": (hit.get("created_at") or "")[:10],
            "origin": "Hacker News",
            "query_label": "Hacker News discussions",
            "snippet": text[:SNIPPET_LIMIT],
            "text": text[:TEXT_LIMIT],
        })
    return sources


def gather_evidence(answers, tavily_client=None, http_get=None, api_key=None):
    """Collect, de-duplicate and number all evidence for one analysis.

    Returns {"sources": [...], "queries": [...], "warnings": [...]}.
    Raises ConfigError or ResearchError with a message for the user.
    """
    if tavily_client is None:
        api_key = api_key if api_key is not None else os.getenv("TAVILY_API_KEY", "")
        if not api_key.strip():
            raise ConfigError("TAVILY_API_KEY is missing. Add it to your .env file "
                              "(see README step 4), then restart the app.")
        tavily_client = TavilyHTTPClient(api_key.strip())

    queries = build_queries(answers)
    collected, warnings = [], []

    for spec in queries:
        try:
            collected.extend(search_tavily(tavily_client, spec))
        except Exception as exc:  # noqa: BLE001 - we classify and report it
            fatal, message = _classify_tavily_error(exc)
            if fatal:
                raise ResearchError(message) from exc
            warnings.append(f"{message} Query skipped: {spec['label']}.")

    try:
        collected.extend(search_hacker_news(answers["sector"], http_get=http_get))
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Hacker News search failed ({type(exc).__name__}); "
                        "continuing without it.")

    # Remove exact duplicates (the same page found by two searches).
    unique, seen = [], set()
    for source in collected:
        key = normalise_url(source["url"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(source)

    if not unique:
        raise ResearchError("No public evidence was found. Try a broader sector name, "
                            "or check your internet connection.")

    for number, source in enumerate(unique, start=1):
        source["id"] = f"S{number}"

    return {
        "sources": unique,
        "queries": [{"label": q["label"], "query": q["query"]} for q in queries],
        "warnings": warnings,
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
