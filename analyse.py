"""Step 3 of the pipeline: ask Gemini to interpret the evidence.

Gemini receives the founder's answers and the numbered sources, and must
reply with JSON in a fixed shape. This module builds the prompt, calls
Gemini, parses the reply and rejects anything that does not fit the shape.
It does NOT decide scores or rankings: scoring.py does that in Python.
"""

import json
import logging
import os
import re
import time

import requests

from errors import AnalysisError, ConfigError, ServiceUnavailableError

log = logging.getLogger("problem_radar")

PROMPT_EXCERPT = 1000  # characters of each source sent to Gemini
MAX_PROMPT_SOURCES = 30  # cap keeps Gemini's reply time reasonable
MAX_PROBLEMS = 7

SCORE_FACTORS = ["severity", "frequency", "market", "willingness_to_pay", "competition_gap"]

JSON_SHAPE = """{
  "problems": [
    {
      "title": "short name of the problem",
      "who": "who experiences it (specific customer type)",
      "situation": "when and where it happens",
      "consequence": "what it costs them (time, money, risk, stress)",
      "evidence": [
        {"source_id": "S3", "quote": "exact words copied from that source, 8-30 words",
         "supports": "what this quote shows"}
      ],
      "touchpoints": [
        {"where": "point in the customer's journey or workflow",
         "consequence": "what goes wrong there"}
      ],
      "micro_trends": [
        {"trend": "a change in behaviour, technology or the market",
         "type": "behaviour | technology | market | regulation",
         "source_ids": ["S5"]}
      ],
      "existing_alternatives": [
        {"name": "a real competitor or workaround named in a source",
         "offer": "what it actually offers, as stated in the source",
         "source_id": "S7"}
      ],
      "market_size": {
        "can_estimate": false,
        "low": null, "high": null,
        "currency": "GBP", "unit": "per year",
        "formula": "e.g. number of businesses x annual spend per business",
        "inputs": [{"name": "number of UK vet clinics", "value": "5,000", "source_id": "S2"}],
        "assumptions": ["each stated assumption"],
        "reason_if_not": "why it cannot be estimated yet"
      },
      "scores": {
        "severity": {"score": 3, "reason": "one sentence citing source IDs"},
        "frequency": {"score": 3, "reason": "..."},
        "market": {"score": 3, "reason": "..."},
        "willingness_to_pay": {"score": 3, "reason": "..."},
        "competition_gap": {"score": 3, "reason": "..."}
      },
      "founder_fit": "how the founder's stated advantage helps or does not help",
      "riskiest_assumption": "the single belief that would kill this idea if false",
      "experiment": {
        "type": "customer interviews | landing page | concierge test | other",
        "objective": "what the experiment will find out",
        "participants": "who to recruit and how many",
        "steps": ["step 1", "step 2"],
        "budget": "cost estimate, or 'not estimated'",
        "success_criteria": "a measurable pass threshold",
        "failure_criteria": "a measurable fail threshold"
      },
      "unverified_notes": ["claims from your general knowledge, not from the sources"]
    }
  ],
  "evidence_gaps": ["important questions the sources could not answer"]
}"""

RULES = """RULES (follow every one):
1. Use ONLY the numbered sources for evidence. Never invent sources, quotes, statistics, companies or customer opinions.
2. Every quote must be copied word for word from the source it cites, 8-30 words long. Do not fix spelling or join separate sentences.
3. Only quote a source that is about this sector. A sentence from a page or thread on another topic cannot support a problem, even if it sounds relevant. If a source is about a different country than the founder's market, say which country in "supports". Use each quote for one problem only.
3b. Each problem needs quotes from at least 2 different sources from different websites. Look across ALL the sources: the founder wants 3 to 7 distinct problems, so return every distinct problem that meets this rule, up to 7. Leave out only problems with fewer than 2 supporting websites.
4. Be specific: name WHO has the problem, in WHAT situation, with WHAT consequence. Do not use vague phrases such as "leverage AI", "digital transformation", "streamline processes" or "enhance efficiency".
5. Scores are whole numbers from 1 (weak) to 5 (strong). Each reason must cite source IDs or say "no evidence". Low evidence means a low score.
   - severity: how painful the problem is. frequency: how often and how widely it happens.
   - market: how many customers and how much money. willingness_to_pay: signs that people already pay to solve it.
   - competition_gap: 5 means few good existing solutions, 1 means a crowded market.
6. market_size: a bottom-up estimate for THIS problem only: (number of customers who have the problem) x (what each would pay per year). Set can_estimate to true ONLY if the sources give both numbers; every input needs a source_id and must be copied as written in the source. Give a low-high range for the same year. Never use a whole-industry valuation, a future forecast, national GDP or a whole economy as the market size. If unsure, set can_estimate to false and explain why.
7. existing_alternatives: only companies or workarounds actually named in a source, with that source_id.
8. Anything from your own general knowledge goes in unverified_notes, never in evidence.
9. The experiment must be cheap, take two weeks or less, and have measurable success and failure thresholds. It is a recommendation, not a result.
10. Respect the founder's exclusions. Return 3 to 7 problems, best first, when the sources support them; never invent evidence to reach 3.
11. Be concise: every text field under 35 words; at most 3 quotes, 3 touchpoints, 3 micro-trends and 3 alternatives per problem; at most 5 experiment steps.
12. Reply with JSON only, exactly in the shape below. No markdown, no commentary."""


def select_prompt_sources(sources, limit=MAX_PROMPT_SOURCES):
    """Pick up to `limit` sources, taking turns between the searches so
    every kind of evidence (complaints, market, regulation...) is represented."""
    groups = {}
    for s in sources:
        groups.setdefault(s.get("query_label", ""), []).append(s)
    picked, queues = [], [list(g) for g in groups.values()]
    while len(picked) < limit and any(queues):
        for queue in queues:
            if queue and len(picked) < limit:
                picked.append(queue.pop(0))
    order = {s["id"]: i for i, s in enumerate(sources)}
    return sorted(picked, key=lambda s: order[s["id"]])


def excerpt(text, limit=PROMPT_EXCERPT):
    """First `limit` characters, cut back to the last whole word.

    Cutting mid-word made Gemini copy half-words into quotes, which the
    quote checker then (correctly) could not find in the source.
    """
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    return (cut[:space] if space > limit * 0.6 else cut) + " [...]"


def format_sources(sources):
    blocks = []
    for s in sources:
        header = f"[{s['id']}] {s['title']} | {s['domain']}"
        if s.get("published"):
            header += f" | published {s['published']}"
        header += f" | via {s['origin']} ({s['query_label']})"
        blocks.append(f"{header}\n{excerpt(s['text'])}")
    return "\n\n".join(blocks)


def build_prompt(answers, sources):
    founder = (
        f"Sector: {answers['sector']}\n"
        f"Geography: {answers['geography']}\n"
        f"Who would pay: {answers['payer']}\n"
        f"Founder advantage: {answers['advantage']}\n"
        f"Exclude: {answers.get('exclude') or 'nothing stated'}"
    )
    chosen = select_prompt_sources(sources)
    return (
        "You are a careful startup research analyst helping a founder find real, "
        "evidence-backed business problems worth testing.\n\n"
        f"FOUNDER ANSWERS\n{founder}\n\n"
        f"{RULES}\n\n"
        f"JSON SHAPE\n{JSON_SHAPE}\n\n"
        f"SOURCES ({len(chosen)})\n{format_sources(chosen)}"
    )


def parse_json_reply(text):
    """Turn Gemini's reply into a Python dict, tolerating code fences."""
    if not text or not text.strip():
        raise ValueError("empty reply")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found")
    data = json.loads(cleaned[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("reply is not a JSON object")
    return data


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def _list_of_dicts(value):
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _list_of_text(value):
    return [v.strip() for v in value if isinstance(v, str) and v.strip()] if isinstance(value, list) else []


def validate_analysis(data):
    """Check Gemini's JSON against the fixed shape.

    Returns {"problems": [...], "evidence_gaps": [...], "rejected": [...]}.
    A problem missing a required part is rejected with a reason rather than
    silently repaired.
    """
    raw_problems = data.get("problems")
    if not isinstance(raw_problems, list):
        raise AnalysisError("Gemini's reply had no list of problems. Please try again.")

    problems, rejected = [], []
    for index, raw in enumerate(raw_problems[:MAX_PROBLEMS], start=1):
        if not isinstance(raw, dict):
            rejected.append(f"Problem {index}: not a valid object.")
            continue
        title = _text(raw.get("title")) or f"Problem {index}"
        missing = [k for k in ("who", "situation", "consequence") if not _text(raw.get(k))]
        if missing:
            rejected.append(f"'{title}': missing {', '.join(missing)}.")
            continue

        scores, score_problems = {}, []
        raw_scores = raw.get("scores") if isinstance(raw.get("scores"), dict) else {}
        for factor in SCORE_FACTORS:
            item = raw_scores.get(factor)
            value = item.get("score") if isinstance(item, dict) else None
            if isinstance(value, bool) or not isinstance(value, (int, float)) \
                    or int(value) != value or not 1 <= value <= 5:
                score_problems.append(factor)
                continue
            scores[factor] = {"score": int(value), "reason": _text(item.get("reason"))}
        if score_problems:
            rejected.append(f"'{title}': invalid or missing scores for {', '.join(score_problems)}.")
            continue

        evidence = []
        for item in _list_of_dicts(raw.get("evidence")):
            if _text(item.get("source_id")) and _text(item.get("quote")):
                evidence.append({
                    "source_id": _text(item.get("source_id")).upper(),
                    "quote": _text(item.get("quote")),
                    "supports": _text(item.get("supports")),
                })

        experiment = raw.get("experiment") if isinstance(raw.get("experiment"), dict) else {}
        market = raw.get("market_size") if isinstance(raw.get("market_size"), dict) else {}

        problems.append({
            "title": title,
            "who": _text(raw.get("who")),
            "situation": _text(raw.get("situation")),
            "consequence": _text(raw.get("consequence")),
            "evidence": evidence,
            "touchpoints": [
                {"where": _text(t.get("where")), "consequence": _text(t.get("consequence"))}
                for t in _list_of_dicts(raw.get("touchpoints")) if _text(t.get("where"))
            ],
            "micro_trends": [
                {"trend": _text(t.get("trend")), "type": _text(t.get("type")),
                 "source_ids": [s.upper() for s in _list_of_text(t.get("source_ids"))]}
                for t in _list_of_dicts(raw.get("micro_trends")) if _text(t.get("trend"))
            ],
            "existing_alternatives": [
                {"name": _text(a.get("name")), "offer": _text(a.get("offer")),
                 "source_id": _text(a.get("source_id")).upper()}
                for a in _list_of_dicts(raw.get("existing_alternatives")) if _text(a.get("name"))
            ],
            "market_size": market,
            "scores": scores,
            "founder_fit": _text(raw.get("founder_fit")),
            "riskiest_assumption": _text(raw.get("riskiest_assumption")),
            "experiment": {
                "type": _text(experiment.get("type")),
                "objective": _text(experiment.get("objective")),
                "participants": _text(experiment.get("participants")),
                "steps": _list_of_text(experiment.get("steps")),
                "budget": _text(experiment.get("budget")),
                "success_criteria": _text(experiment.get("success_criteria")),
                "failure_criteria": _text(experiment.get("failure_criteria")),
            },
            "unverified_notes": _list_of_text(raw.get("unverified_notes")),
        })

    return {
        "problems": problems,
        "evidence_gaps": _list_of_text(data.get("evidence_gaps")),
        "rejected": rejected,
    }


def _gemini_error_message(exc):
    """Translate a Gemini SDK error into advice a beginner can act on."""
    code = getattr(exc, "code", None)
    text = str(exc).lower()
    if code == TIMED_OUT:
        return (f"Gemini did not answer within {GEMINI_TIMEOUT} seconds, and the other "
                "models tried were also slow or busy.")
    if code == 429 or "resource_exhausted" in text or "quota" in text:
        return ("Gemini's free quota is used up for now. Wait a minute and try again, "
                "or open a saved run.")
    if code == 404 or "not found" in text:
        return ("Gemini could not find the model named in GEMINI_MODEL. Open Google AI "
                "Studio, copy the name of a current Flash model, put it in .env and restart.")
    if code in (401, 403) or "api key" in text or "permission" in text:
        return "Gemini rejected the API key. Check GEMINI_API_KEY in your .env file."
    if isinstance(code, int) and code >= 500:
        return ("Gemini is busy or unavailable right now. The app already retried and tried "
                "other Gemini models.")
    detail = str(exc)[:200]
    return f"Gemini returned an error ({code or type(exc).__name__}): {detail}"


GEMINI_TIMEOUT = 90  # seconds per model; a slower model is skipped, not waited on
FAST_MODEL = "gemini-flash-lite-latest"  # tried first: answered in seconds in live runs
TIMED_OUT = 408  # our own marker status for "this model took too long"
MAX_OUTPUT_TOKENS = 16384
RETRY_WAITS = (5,)  # one short retry, then switch model rather than wait
MAX_OTHER_MODELS = 5      # busy Lite models answer "503" in about 2 s, so trying several is cheap
TIME_BUDGET = 200         # seconds: no new model is started after this
FINAL_RETRY_WAIT = 15     # one last try of the first model if everything was busy
TEMPORARY_STATUSES = {500, 503, 504}
SWITCH_MODEL_STATUSES = {404, 408, 429} | TEMPORARY_STATUSES
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class _TimedOut:
    """Stands in for a response when a model did not answer in time."""
    status_code = TIMED_OUT
    text = ""

    def json(self):
        return {"error": {"message": "timed out"}}


class GeminiHTTPError(Exception):
    """Gemini answered with an HTTP error status."""

    def __init__(self, code, message=""):
        super().__init__(message or f"HTTP {code}")
        self.code = code


def extract_reply_text(data):
    """Pull the reply text out of Gemini's generateContent response."""
    candidates = data.get("candidates") or []
    if not candidates:
        reason = (data.get("promptFeedback") or {}).get("blockReason", "no reason given")
        raise AnalysisError(f"Gemini returned no answer ({reason}). Try rewording the sector.")
    if candidates[0].get("finishReason") == "MAX_TOKENS":
        log.warning("Gemini stopped at the output limit; the reply may be cut off")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if isinstance(p, dict))


GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Model families that are not general text models.
_NOT_TEXT_MODELS = ("image", "tts", "live", "audio", "embedding", "robotics", "computer-use", "veo")


def rank_flash_models(models):
    """From a models.list reply, return usable Flash model ids, best first.

    Best = a full Flash model (not Lite), stable before preview/experimental,
    newest version first.
    """
    ranked = []
    for m in models:
        name = (m.get("name") or "").removeprefix("models/")
        methods = m.get("supportedGenerationMethods") or []
        if "flash" not in name or "generateContent" not in methods:
            continue
        if any(word in name for word in _NOT_TEXT_MODELS):
            continue
        version = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
        version_number = float(version.group(1)) if version else 0.0
        is_lite = "lite" in name
        is_unstable = any(word in name for word in ("preview", "exp"))
        ranked.append(((is_lite, is_unstable, -version_number, name), name))
    return [name for _, name in sorted(ranked)]


def overload_order(names):
    """When Google is overloaded, lighter models are usually less busy:
    try Flash-Lite models first, then the rest."""
    return [n for n in names if "lite" in n] + [n for n in names if "lite" not in n]


def list_flash_models(api_key, http_get=None):
    """Ask Gemini which Flash models this API key can use."""
    http_get = http_get or requests.get
    models, page_token = [], None
    for _ in range(5):  # at most 5 pages
        params = {"pageSize": 1000}
        if page_token:
            params["pageToken"] = page_token
        try:
            response = http_get(GEMINI_MODELS_URL, headers={"x-goog-api-key": api_key},
                                params=params, timeout=30)
            if response.status_code >= 400:
                return []
            data = response.json()
        except (requests.RequestException, ValueError):
            return []
        models.extend(data.get("models") or [])
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return rank_flash_models(models)


def make_gemini_generator(api_key=None, model=None, http_post=None, http_get=None, sleep=None,
                          progress=None, clock=None):
    """Return a function prompt -> reply text that calls the real Gemini API.

    Uses plain HTTP via `requests` instead of the google-genai library, so
    no compiled files are needed (Windows Smart App Control blocked one in
    another library on the student's PC).

    If Google is overloaded (HTTP 500/503/504) the same model is retried
    once after 5 seconds. If it is still overloaded, out of free quota (429)
    or not recognised (404), the app asks Google which Flash models this key
    can use and tries two others (Flash-Lite first when overloaded).
    """
    api_key = (api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")).strip()
    if model:
        preferred = [model]
    else:
        configured = os.getenv("GEMINI_MODEL", "").strip() or "gemini-flash-latest"
        # Speed first: in live runs the full Flash model was overloaded (503)
        # or took over 3 minutes, while Flash-Lite answered in seconds.
        # Set AI_SPEED=quality in .env to try the configured model first.
        if os.getenv("AI_SPEED", "").strip().lower() == "quality":
            preferred = [configured, FAST_MODEL]
        else:
            preferred = [FAST_MODEL, configured]
        preferred = list(dict.fromkeys(preferred))
    model = preferred[0]
    if not api_key:
        raise ConfigError("GEMINI_API_KEY is missing. Add it to your .env file "
                          "(see README step 4), then restart the app.")
    http_post = http_post or requests.post
    state = {"model": model, "extra": preferred[1:], "candidates": None,
             "thinking_config": True, "tried": set()}
    sleep = sleep or time.sleep
    clock = clock or time.monotonic
    note = progress or (lambda message: None)

    def call(model_id, prompt):
        # No temperature setting: Google recommends Gemini 3's default (1.0);
        # lower values can cause looping. The output cap stops a runaway reply.
        config = {"responseMimeType": "application/json", "maxOutputTokens": MAX_OUTPUT_TOKENS}
        if state["thinking_config"]:
            # Gemini 3 models think at "high" by default, which was slow for a
            # long prompt; "low" was fast but returned only 1 problem.
            # "medium" is Google's balanced setting.
            config["thinkingConfig"] = {"thinkingLevel": "medium"}
        started = time.monotonic()
        try:
            response = http_post(
                GEMINI_URL.format(model=model_id),
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config},
                timeout=GEMINI_TIMEOUT,
            )
        except requests.Timeout:
            log.warning("Gemini (%s) gave no answer within %ds; skipping it", model_id, GEMINI_TIMEOUT)
            note(f"{model_id} is too slow right now (no answer in {GEMINI_TIMEOUT} s); skipping it...")
            return _TimedOut()
        except requests.RequestException as exc:
            raise AnalysisError("Could not reach Gemini. Check your internet connection.") from exc
        log.info("Gemini (%s) answered HTTP %s in %.0fs", model_id, response.status_code,
                 time.monotonic() - started)
        if response.status_code == 400 and state["thinking_config"] and "thinking" in response.text.lower():
            state["thinking_config"] = False   # this model does not accept thinkingLevel
            return call(model_id, prompt)
        return response

    def error_for(response):
        try:
            detail = response.json().get("error", {}).get("message", "")
        except ValueError:
            detail = ""
        message = _gemini_error_message(GeminiHTTPError(response.status_code, detail))
        if response.status_code in SWITCH_MODEL_STATUSES:
            return ServiceUnavailableError(message)
        return AnalysisError(message)

    def candidates(overloaded):
        """Models to try next: the remaining preferred ones, then other Flash
        models this key can use (asked from Google once). Never repeats one."""
        if state["candidates"] is None:
            state["candidates"] = list_flash_models(api_key, http_get) or [FAST_MODEL]
        names = list(dict.fromkeys(state["extra"] + state["candidates"]))
        if overloaded:
            # Lite models first (fast "busy" answers, usually less loaded);
            # the full model, which once gave no answer for 3+ minutes, last.
            names = overload_order(names)
        return [m for m in names if m != state["model"] and m not in state["tried"]]

    def generate(prompt):
        note(f"Waiting for Gemini ({state['model']}) to read the sources and reply...")
        started = clock()
        first_model = state["model"]
        state["tried"].add(state["model"])
        response = call(state["model"], prompt)

        # 1. Temporary server trouble (overloaded): wait and retry the same model.
        for wait in RETRY_WAITS:
            if response.status_code not in TEMPORARY_STATUSES:
                break
            log.warning("Gemini (%s) answered HTTP %s; retrying in %ds",
                        state["model"], response.status_code, wait)
            note(f"Gemini is busy (HTTP {response.status_code}); retrying in {wait} seconds...")
            sleep(wait)
            response = call(state["model"], prompt)

        # 2. Model not found, out of free quota, too slow or still overloaded:
        #    try other Flash models, within the time budget.
        if response.status_code in SWITCH_MODEL_STATUSES:
            others = candidates(response.status_code != 404)[:MAX_OTHER_MODELS]
            log.warning("Gemini model '%s' failed with HTTP %s; trying %s",
                        state["model"], response.status_code, others)
            for candidate in others:
                if clock() - started > TIME_BUDGET:
                    log.warning("Time budget of %ds used up; not trying more models", TIME_BUDGET)
                    break
                note(f"Trying another Gemini model: {candidate}...")
                state["tried"].add(candidate)
                attempt = call(candidate, prompt)
                response = attempt          # the last answer decides the error message
                if attempt.status_code < 400:
                    state["model"] = candidate
                    generate.model_name = candidate
                    log.info("Switched to Gemini model '%s'", candidate)
                    break

        # 3. Everything was busy: one last try of the first model after a pause.
        if response.status_code in TEMPORARY_STATUSES and clock() - started <= TIME_BUDGET:
            note(f"All Gemini models were busy; one last try in {FINAL_RETRY_WAIT} seconds...")
            sleep(FINAL_RETRY_WAIT)
            attempt = call(first_model, prompt)
            if attempt.status_code < 400:
                state["model"] = first_model
                generate.model_name = first_model
            response = attempt

        if response.status_code >= 400:
            raise error_for(response)
        try:
            data = response.json()
        except ValueError as exc:
            raise AnalysisError("Gemini's reply could not be read. Please try again.") from exc
        return extract_reply_text(data)

    generate.model_name = model
    return generate


MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


def make_mistral_generator(api_key=None, model=None, http_post=None, progress=None):
    """Return a function prompt -> reply text that calls Mistral's API.

    Used as a second AI service when Gemini is busy. Mistral's free
    "Experiment" plan allows about 2 requests a minute, enough for this app.
    """
    api_key = (api_key if api_key is not None else os.getenv("MISTRAL_API_KEY", "")).strip()
    model = model or os.getenv("MISTRAL_MODEL", "").strip() or "mistral-medium-latest"
    if not api_key:
        raise ConfigError("MISTRAL_API_KEY is missing.")
    http_post = http_post or requests.post
    note = progress or (lambda message: None)

    def generate(prompt):
        note(f"Waiting for Mistral ({model}) to read the sources and reply...")
        started = time.monotonic()
        try:
            response = http_post(
                MISTRAL_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "response_format": {"type": "json_object"},
                      "max_tokens": MAX_OUTPUT_TOKENS},
                timeout=GEMINI_TIMEOUT,
            )
        except requests.Timeout as exc:
            raise ServiceUnavailableError("Mistral took too long to answer.") from exc
        except requests.RequestException as exc:
            raise AnalysisError("Could not reach Mistral. Check your internet connection.") from exc
        log.info("Mistral (%s) answered HTTP %s in %.0fs", model, response.status_code,
                 time.monotonic() - started)
        status = response.status_code
        if status == 401:
            raise AnalysisError("Mistral rejected the API key. Check MISTRAL_API_KEY in your .env file.")
        if status == 429:
            raise ServiceUnavailableError("Mistral's free limit was reached (about 2 requests a "
                                          "minute). Wait a minute and try again.")
        if status >= 500 or status == 404:
            raise ServiceUnavailableError(f"Mistral is busy or unavailable right now (HTTP {status}).")
        if status >= 400:
            raise AnalysisError(f"Mistral returned an error (HTTP {status}).")
        try:
            choices = response.json().get("choices") or []
            return choices[0]["message"]["content"] or ""
        except (ValueError, IndexError, KeyError, TypeError) as exc:
            raise AnalysisError("Mistral's reply could not be read. Please try again.") from exc

    generate.model_name = model
    return generate


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
# Preferred Groq models, best first. Groq retires models often, so the app
# also asks Groq which models the key can use and falls back to those.
GROQ_MODELS = (
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
)
# Words in model names that are not general chat models (speech, safety, agents).
GROQ_SKIP_WORDS = ("allam", "whisper", "tts", "guard", "compound", "orpheus", "playai",
                   "distil", "embed", "vision", "audio", "speech")
GROQ_MAX_TOKENS = 3500  # reply budget, including the model's thinking
GROQ_PROMPT_CHARS = 16000  # about 4,500 tokens: Groq's free plan allows ~8,000 tokens a minute
GROQ_TIMEOUT = 60


def shrink_prompt(prompt, max_chars=GROQ_PROMPT_CHARS):
    """Make the prompt fit a smaller AI service by shortening and, if
    needed, dropping sources from the end. Rules and JSON shape are kept."""
    if len(prompt) <= max_chars:
        return prompt
    head, marker, body = prompt.partition("\nSOURCES (")
    if not marker:
        return prompt[:max_chars]
    blocks = re.split(r"\n\n(?=\[S\d+\] )", body.split("\n", 1)[1] if "\n" in body else "")
    for limit in (600, 450, 300):
        short = []
        for block in blocks:
            header, _, text = block.partition("\n")
            short.append(f"{header}\n{excerpt(text, limit)}")
        # take turns between searches so every kind of evidence stays represented
        groups = {}
        for position, block in enumerate(short):
            label = re.search(r"\(([^()]*)\)$", block.partition("\n")[0])
            groups.setdefault(label.group(1) if label else "", []).append(position)
        turns, queues = [], [list(g) for g in groups.values()]
        while any(queues):
            for queue in queues:
                if queue:
                    turns.append(queue.pop(0))
        for keep in range(len(turns), 11, -1):
            chosen = [short[i] for i in sorted(turns[:keep])]
            candidate = f"{head}\nSOURCES ({len(chosen)})\n" + "\n\n".join(chosen)
            if len(candidate) <= max_chars:
                return candidate
    return candidate[:max_chars]


def has_problems(reply):
    """True if the reply is JSON with at least one proposed problem."""
    try:
        return bool(parse_json_reply(reply).get("problems"))
    except (ValueError, AttributeError):
        return True  # not JSON: let the normal retry and error handling deal with it


def strip_thinking(text):
    """Some models put their reasoning in <think>...</think> before the JSON."""
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


def groq_request(model, prompt):
    """Request body for Groq. Reasoning models (gpt-oss) are asked to think
    briefly, because their thinking uses the same small token budget."""
    body = {"model": model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "max_tokens": GROQ_MAX_TOKENS}
    if "gpt-oss" in model:
        body["reasoning_effort"] = "medium"  # "low" was tried: it returned 0 problems
    return body


def groq_model_order(available, preferred=None):
    """Models to try, best first: preferred ones the key can use, then any
    other chat model Groq lists. Without a list, use the preferred ones."""
    wanted = ([preferred] if preferred else []) + [m for m in GROQ_MODELS if m != preferred]
    if not available:
        return wanted
    order = [m for m in wanted if m in available]
    extras = sorted(m for m in available
                    if m not in order and not any(w in m.lower() for w in GROQ_SKIP_WORDS))
    return (order + extras)[:5] or wanted


def make_groq_generator(api_key=None, model=None, http_post=None, http_get=None, progress=None):
    """Return a function prompt -> reply text that calls Groq's free API.

    Used as a backup when Gemini is busy. Tries several Groq models in turn
    if one is busy, retired, or over its free per-minute limit.
    """
    api_key = (api_key if api_key is not None else os.getenv("GROQ_API_KEY", "")).strip()
    preferred = model or os.getenv("GROQ_MODEL", "").strip() or None
    if not api_key:
        raise ConfigError("GROQ_API_KEY is missing.")
    http_post = http_post or requests.post
    http_get = http_get or requests.get
    note = progress or (lambda message: None)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def available_models():
        try:
            response = http_get(GROQ_MODELS_URL, headers=headers, timeout=15)
            if response.status_code == 200:
                ids = {m.get("id") for m in response.json().get("data", []) if m.get("id")}
                log.info("Groq models this key can use: %s", ", ".join(sorted(ids)))
                return ids
            log.warning("Groq model list answered HTTP %s", response.status_code)
        except (requests.RequestException, ValueError, AttributeError):
            log.warning("Could not get Groq's model list")
        return set()

    def generate(prompt):
        last_reply = [None]
        small = shrink_prompt(prompt)
        log.info("Prompt for Groq: %d characters (full prompt %d)", len(small), len(prompt))
        reasons = []
        for name in groq_model_order(available_models(), preferred):
            for attempt_prompt in (small, shrink_prompt(small, GROQ_PROMPT_CHARS * 2 // 3)):
                note(f"Waiting for Groq ({name}) to read the sources and reply...")
                started = time.monotonic()
                try:
                    response = http_post(
                        GROQ_URL, headers=headers,
                        json=groq_request(name, attempt_prompt),
                        timeout=GROQ_TIMEOUT,
                    )
                except requests.Timeout:
                    reasons.append(f"{name}: too slow")
                    break
                except requests.RequestException as exc:
                    raise AnalysisError("Could not reach Groq. Check your internet connection.") from exc
                status = response.status_code
                log.info("Groq (%s) answered HTTP %s in %.0fs", name, status, time.monotonic() - started)
                if status == 401:
                    raise AnalysisError("Groq rejected the API key. Check GROQ_API_KEY in your .env file.")
                if status == 200:
                    try:
                        choices = response.json().get("choices") or []
                        reply = strip_thinking(choices[0]["message"]["content"])
                    except (ValueError, IndexError, KeyError, TypeError) as exc:
                        raise AnalysisError("Groq's reply could not be read. Please try again.") from exc
                    if not has_problems(reply):
                        # a lazy or cut-off answer: give the next model a chance
                        log.warning("Groq (%s) proposed no problems; trying the next model", name)
                        reasons.append(f"{name}: no problems proposed")
                        last_reply[0] = reply
                        break
                    generate.model_name = name
                    return reply
                if status == 413:  # prompt too large for this model's free limit: try smaller once
                    log.warning("Groq (%s): prompt too large; trying a shorter one", name)
                    reasons.append(f"{name}: too large")
                    continue
                reasons.append(f"{name}: HTTP {status}")
                log.warning("Groq (%s) answered HTTP %s; trying the next model", name, status)
                break
        if last_reply[0] is not None:  # every model answered but proposed nothing: report that honestly
            generate.model_name = name
            return last_reply[0]
        raise ServiceUnavailableError("Groq is busy or over its free limit right now ("
                                      + "; ".join(reasons) + ").")

    generate.model_name = preferred or GROQ_MODELS[0]
    return generate

def chain_generators(named_generators, progress=None):
    """Try each AI service in turn; move to the next one only when the
    current one is busy, out of quota, or does not know the model."""
    note = progress or (lambda message: None)

    def generate(prompt):
        for position, (name, generator) in enumerate(named_generators):
            try:
                reply = generator(prompt)
                generate.model_name = f"{name}: {getattr(generator, 'model_name', '')}"
                return reply
            except ServiceUnavailableError as exc:
                if position == len(named_generators) - 1:
                    if len(named_generators) == 1 and name == "Gemini":
                        raise ServiceUnavailableError(
                            f"{exc} Please try again in a few minutes. Tip: add a free "
                            "GROQ_API_KEY to your .env file so the app can switch to "
                            "Groq when Gemini is busy (see README).") from exc
                    raise ServiceUnavailableError(f"{exc} Please try again in a few minutes.") from exc
                next_name = named_generators[position + 1][0]
                log.warning("%s unavailable (%s); switching to %s", name, exc, next_name)
                note(f"{name} is unavailable right now; switching to {next_name}...")

    generate.model_name = ", ".join(name for name, _ in named_generators)
    return generate


def make_ai_generator(progress=None):
    """Build the AI service chain from the keys in .env.

    Order: Gemini, then Groq, then Mistral. AI_PROVIDER=groq or
    AI_PROVIDER=mistral moves that service to the front. A service is
    only included when its key is present.
    """
    available = []
    if os.getenv("GEMINI_API_KEY", "").strip():
        available.append(("Gemini", make_gemini_generator(progress=progress)))
    if os.getenv("GROQ_API_KEY", "").strip():
        available.append(("Groq", make_groq_generator(progress=progress)))
    if os.getenv("MISTRAL_API_KEY", "").strip():
        available.append(("Mistral", make_mistral_generator(progress=progress)))
    if not available:
        raise ConfigError("GEMINI_API_KEY is missing. Add it to your .env file "
                          "(see README step 4), then restart the app.")
    first = os.getenv("AI_PROVIDER", "").strip().lower()
    if first in ("groq", "mistral"):
        available.sort(key=lambda item: item[0].lower() != first)
    return chain_generators(available, progress=progress)


def analyse(answers, evidence, generate=None, progress=None):
    """Run the AI step. Retries once if the reply is not valid JSON.

    Returns {"analysis": validated dict, "prompt_chars": int, "attempts": int, "model": str}.
    """
    generate = generate or make_ai_generator(progress=progress)
    prompt = build_prompt(answers, evidence["sources"])

    reply = generate(prompt)
    attempts = 1
    try:
        data = parse_json_reply(reply)
    except (ValueError, json.JSONDecodeError):
        attempts = 2
        if progress:
            progress("Gemini's reply was not valid JSON; asking once more...")
        retry_prompt = (prompt + "\n\nYOUR PREVIOUS REPLY WAS NOT VALID JSON. "
                        "Reply again with one JSON object only, in the exact shape above.")
        try:
            data = parse_json_reply(generate(retry_prompt))
        except (ValueError, json.JSONDecodeError) as exc:
            raise AnalysisError("Gemini replied twice without valid JSON. "
                                "Please try again, or try a more specific sector.") from exc

    analysis = validate_analysis(data)
    if not analysis["problems"] and not analysis["rejected"] and not analysis["evidence_gaps"]:
        raise AnalysisError("Gemini returned no problems for this sector. "
                            "Try a broader or differently worded sector.")
    return {
        "analysis": analysis,
        "prompt_chars": len(prompt),
        "attempts": attempts,
        "model": getattr(generate, "model_name", "test"),
    }
