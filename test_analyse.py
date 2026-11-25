"""Tests for handling missing, broken or invalid AI responses."""

import json

import pytest

from analyse import analyse, build_prompt, parse_json_reply, validate_analysis, _gemini_error_message
from errors import AnalysisError, ConfigError


def fake_generator(*replies):
    """A stand-in for Gemini that returns the given replies in order."""
    calls = []

    def generate(prompt):
        calls.append(prompt)
        return replies[min(len(calls) - 1, len(replies) - 1)]

    generate.calls = calls
    return generate


def test_prompt_contains_rules_answers_and_numbered_sources(answers, sources):
    prompt = build_prompt(answers, sources)
    assert "[S1]" in prompt and "[S3]" in prompt
    assert "independent vet clinics" in prompt
    assert "national GDP" in prompt and "bottom-up" in prompt
    assert "Reply with JSON only" in prompt


def test_parse_handles_code_fences():
    assert parse_json_reply('```json\n{"problems": []}\n```') == {"problems": []}


@pytest.mark.parametrize("reply", ["", "   ", "Sorry, I cannot help", "[1, 2]", '{"problems": ['])
def test_parse_rejects_non_json(reply):
    with pytest.raises((ValueError, json.JSONDecodeError)):
        parse_json_reply(reply)


def test_valid_reply_passes(answers, sources, good_problem):
    reply = json.dumps({"problems": [good_problem], "evidence_gaps": ["No pricing data"]})
    out = analyse(answers, {"sources": sources}, generate=fake_generator(reply))
    assert out["attempts"] == 1
    assert len(out["analysis"]["problems"]) == 1
    assert out["analysis"]["evidence_gaps"] == ["No pricing data"]


def test_invalid_json_is_retried_once(answers, sources, good_problem):
    gen = fake_generator("not json at all", json.dumps({"problems": [good_problem]}))
    out = analyse(answers, {"sources": sources}, generate=gen)
    assert out["attempts"] == 2
    assert "NOT VALID JSON" in gen.calls[1]


def test_two_invalid_replies_raise_a_friendly_error(answers, sources):
    with pytest.raises(AnalysisError, match="twice without valid JSON"):
        analyse(answers, {"sources": sources}, generate=fake_generator("nope", "still nope"))


def test_reply_without_problem_list_raises(answers, sources):
    with pytest.raises(AnalysisError):
        analyse(answers, {"sources": sources}, generate=fake_generator('{"ideas": []}'))


def test_empty_problem_list_raises(answers, sources):
    with pytest.raises(AnalysisError, match="no problems"):
        analyse(answers, {"sources": sources}, generate=fake_generator('{"problems": []}'))


def test_problem_missing_who_is_rejected_with_reason(good_problem):
    del good_problem["who"]
    out = validate_analysis({"problems": [good_problem]})
    assert out["problems"] == []
    assert "missing who" in out["rejected"][0]


@pytest.mark.parametrize("bad_score", [0, 7, "five", None, 2.5])
def test_problem_with_bad_score_is_rejected(good_problem, bad_score):
    good_problem["scores"]["frequency"]["score"] = bad_score
    out = validate_analysis({"problems": [good_problem]})
    assert out["problems"] == []
    assert "frequency" in out["rejected"][0]


def test_whole_number_float_score_is_accepted(good_problem):
    good_problem["scores"]["market"]["score"] = 4.0
    out = validate_analysis({"problems": [good_problem]})
    assert out["problems"][0]["scores"]["market"]["score"] == 4


def test_more_than_seven_problems_are_cut_to_seven(good_problem):
    out = validate_analysis({"problems": [dict(good_problem) for _ in range(10)]})
    assert len(out["problems"]) == 7


def test_missing_gemini_key_raises_config_error(answers, sources, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        analyse(answers, {"sources": sources})


class FakeApiError(Exception):
    def __init__(self, code, message="error"):
        super().__init__(message)
        self.code = code


@pytest.mark.parametrize("code, expected", [
    (429, "quota"), (404, "GEMINI_MODEL"), (403, "API key"), (503, "busy"),
])
def test_gemini_errors_become_plain_english(code, expected):
    assert expected in _gemini_error_message(FakeApiError(code))


# ---- the direct HTTP connection to Gemini (replaces the google-genai library)

import requests as _requests

from analyse import extract_reply_text, make_gemini_generator


class FakeHTTPResponse:
    def __init__(self, status, payload=None):
        self.status_code, self.payload = status, payload
        self.text = __import__("json").dumps(payload) if payload is not None else ""

    def json(self):
        if self.payload is None:
            raise ValueError("not json")
        return self.payload


def gemini_post(status, payload=None):
    calls = []

    def post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        return FakeHTTPResponse(status, payload)

    post.calls = calls
    return post


OK_REPLY = {"candidates": [{"content": {"parts": [{"text": '{"problems": '}, {"text": "[]}"}]}}]}


def test_gemini_http_sends_key_header_and_json_mode():
    post = gemini_post(200, OK_REPLY)
    generate = make_gemini_generator(api_key="AQ.test", model="gemini-test", http_post=post)
    assert generate("hello") == '{"problems": []}'
    call = post.calls[0]
    assert call["url"].endswith("/models/gemini-test:generateContent")
    assert call["headers"]["x-goog-api-key"] == "AQ.test"
    assert call["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert call["json"]["contents"][0]["parts"][0]["text"] == "hello"
    assert generate.model_name == "gemini-test"


@pytest.mark.parametrize("status, payload, expected", [
    (429, {"error": {"message": "Resource exhausted"}}, "quota"),
    (404, {"error": {"message": "models/x is not found"}}, "GEMINI_MODEL"),
    (400, {"error": {"message": "API key not valid. Please pass a valid API key."}}, "API key"),
    (503, None, "busy"),
])
def test_gemini_http_errors_become_plain_english(status, payload, expected):
    generate = make_gemini_generator(api_key="AQ.test", http_post=gemini_post(status, payload),
                                     http_get=lambda *a, **k: FakeHTTPResponse(403, {}),
                                     sleep=lambda seconds: None)
    with pytest.raises(AnalysisError, match=expected):
        generate("hello")


def test_gemini_network_failure_is_explained():
    def offline(*args, **kwargs):
        raise _requests.ConnectionError()
    generate = make_gemini_generator(api_key="AQ.test", http_post=offline)
    with pytest.raises(AnalysisError, match="internet connection"):
        generate("hello")


def test_blocked_reply_without_candidates_is_explained():
    with pytest.raises(AnalysisError, match="SAFETY"):
        extract_reply_text({"promptFeedback": {"blockReason": "SAFETY"}})


# ---- automatic choice of a Flash model when the configured one is not found

from analyse import list_flash_models, rank_flash_models

MODEL_LIST = {"models": [
    {"name": "models/gemini-3.5-flash", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.6-flash-preview", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.6-flash-lite", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.6-flash", "supportedGenerationMethods": ["generateContent", "countTokens"]},
    {"name": "models/gemini-3.6-flash-image", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.6-flash-tts", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.6-pro", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/text-embedding-9", "supportedGenerationMethods": ["embedContent"]},
]}


def test_flash_models_ranked_newest_stable_full_first():
    assert rank_flash_models(MODEL_LIST["models"]) == [
        "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.6-flash-preview", "gemini-3.6-flash-lite"]


def test_model_list_failure_returns_empty():
    def offline(*a, **k):
        raise _requests.ConnectionError()
    assert list_flash_models("AQ.test", http_get=offline) == []


def test_unknown_model_switches_to_an_available_flash_model():
    calls = []

    def post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        if "gemini-flash-latest" in url:
            return FakeHTTPResponse(404, {"error": {"message": "models/gemini-flash-latest is not found"}})
        return FakeHTTPResponse(200, OK_REPLY)

    generate = make_gemini_generator(api_key="AQ.test", model="gemini-flash-latest", http_post=post,
                                     http_get=lambda *a, **k: FakeHTTPResponse(200, MODEL_LIST))
    assert generate("hello") == '{"problems": []}'
    assert generate.model_name == "gemini-3.6-flash"
    assert calls[-1].endswith("/models/gemini-3.6-flash:generateContent")
    generate("again")                      # later calls go straight to the working model
    assert calls[-1].endswith("/models/gemini-3.6-flash:generateContent")
    assert len(calls) == 3


def test_unknown_model_with_no_alternatives_gives_clear_message():
    generate = make_gemini_generator(
        api_key="AQ.test", model="gemini-nope",
        http_post=gemini_post(404, {"error": {"message": "not found"}}),
        http_get=lambda *a, **k: FakeHTTPResponse(200, {"models": []}))
    with pytest.raises(AnalysisError, match="GEMINI_MODEL"):
        generate("hello")


# ---- speed: low thinking level, fallback, and a capped prompt

from analyse import MAX_PROMPT_SOURCES, select_prompt_sources
from conftest import make_source


def test_requests_ask_for_medium_thinking():
    post = gemini_post(200, OK_REPLY)
    make_gemini_generator(api_key="AQ.test", http_post=post)("hi")
    assert post.calls[0]["json"]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "medium"}


def test_model_that_rejects_thinking_config_is_retried_without_it():
    calls = []

    def post(url, headers=None, json=None, timeout=None):
        calls.append(json["generationConfig"])
        if "thinkingConfig" in json["generationConfig"]:
            return FakeHTTPResponse(400, {"error": {"message": "Thinking level is not supported for this model."}})
        return FakeHTTPResponse(200, OK_REPLY)

    generate = make_gemini_generator(api_key="AQ.test", http_post=post)
    assert generate("hi") == '{"problems": []}'
    assert "thinkingConfig" not in calls[-1]
    generate("again")
    assert len(calls) == 3   # the second prompt goes straight without it


def test_gemini_timeout_on_every_model_is_explained():
    def slow(*a, **k):
        raise _requests.Timeout()
    with pytest.raises(AnalysisError, match="did not answer within 90 seconds"):
        make_gemini_generator(api_key="AQ.test", http_post=slow,
                              http_get=lambda *a, **k: FakeHTTPResponse(403, {}),
                              sleep=lambda s: None)("hi")


def test_prompt_uses_at_most_30_sources_from_every_search():
    labels = ["Problems", "Market", "Complaints", "Regulation", "Funding", "Forums", "HN"]
    sources = []
    for n in range(42):
        src = make_source(f"S{n + 1}", f"site{n}.com", f"text number {n} " * 20)
        src["query_label"] = labels[n // 6]
        sources.append(src)
    chosen = select_prompt_sources(sources)
    assert len(chosen) == MAX_PROMPT_SOURCES
    assert {s["query_label"] for s in chosen} == set(labels)
    assert [s["id"] for s in chosen] == sorted((s["id"] for s in chosen), key=lambda i: int(i[1:]))
    prompt = build_prompt({"sector": "x", "geography": "UK", "payer": "Either", "advantage": "y"}, sources)
    assert "SOURCES (30)" in prompt


# ---- overloaded Gemini: wait and retry, then switch model

def scripted_post(script):
    """Answer each call with the next (status, payload) for that model."""
    calls = []

    def post(url, headers=None, json=None, timeout=None):
        model = url.split("/models/")[1].split(":")[0]
        calls.append(model)
        status, payload = script[model].pop(0) if len(script[model]) > 1 else script[model][0]
        return FakeHTTPResponse(status, payload)

    post.calls = calls
    return post


BUSY = (503, {"error": {"message": "The model is overloaded. Please try again later."}})


def test_overloaded_model_is_retried_once_after_waiting():
    waits = []
    post = scripted_post({"gemini-a": [BUSY, (200, OK_REPLY)]})
    generate = make_gemini_generator(api_key="AQ.test", model="gemini-a", http_post=post,
                                     sleep=waits.append)
    assert generate("hi") == '{"problems": []}'
    assert waits == [5]
    assert post.calls == ["gemini-a"] * 2


def test_still_overloaded_model_switches_to_flash_lite_first():
    post = scripted_post({"gemini-a": [BUSY], "gemini-3.6-flash-lite": [(200, OK_REPLY)]})
    generate = make_gemini_generator(api_key="AQ.test", model="gemini-a", http_post=post,
                                     http_get=lambda *a, **k: FakeHTTPResponse(200, MODEL_LIST),
                                     sleep=lambda s: None)
    assert generate("hi") == '{"problems": []}'
    assert generate.model_name == "gemini-3.6-flash-lite"
    assert post.calls == ["gemini-a", "gemini-a", "gemini-3.6-flash-lite"]


def test_out_of_quota_model_switches_without_waiting():
    waits = []
    quota = (429, {"error": {"message": "Quota exceeded for this model"}})
    post = scripted_post({"gemini-a": [quota], "gemini-3.6-flash-lite": [(200, OK_REPLY)]})
    generate = make_gemini_generator(api_key="AQ.test", model="gemini-a", http_post=post,
                                     http_get=lambda *a, **k: FakeHTTPResponse(200, MODEL_LIST),
                                     sleep=waits.append)
    assert generate("hi") == '{"problems": []}'
    assert waits == []


def test_model_list_failure_still_tries_flash_lite_alias():
    post = scripted_post({"gemini-a": [BUSY], "gemini-flash-lite-latest": [(200, OK_REPLY)]})
    generate = make_gemini_generator(api_key="AQ.test", model="gemini-a", http_post=post,
                                     http_get=lambda *a, **k: FakeHTTPResponse(500, {}),
                                     sleep=lambda s: None)
    assert generate("hi") == '{"problems": []}'
    assert generate.model_name == "gemini-flash-lite-latest"


def test_everything_overloaded_raises_service_unavailable():
    from errors import ServiceUnavailableError
    post = scripted_post({"gemini-a": [BUSY], "gemini-3.6-flash-lite": [BUSY], "gemini-3.6-flash": [BUSY],
                          "gemini-3.5-flash": [BUSY], "gemini-3.6-flash-preview": [BUSY]})
    generate = make_gemini_generator(api_key="AQ.test", model="gemini-a", http_post=post,
                                     http_get=lambda *a, **k: FakeHTTPResponse(200, MODEL_LIST),
                                     sleep=lambda s: None)
    with pytest.raises(ServiceUnavailableError, match="busy"):
        generate("hi")
    # 2 tries of the first model, every other usable Flash model once (Lite first), 1 last try
    assert post.calls == ["gemini-a", "gemini-a", "gemini-3.6-flash-lite", "gemini-3.6-flash",
                          "gemini-3.5-flash", "gemini-3.6-flash-preview", "gemini-a"]


def test_no_low_temperature_and_output_is_capped():
    post = gemini_post(200, OK_REPLY)
    make_gemini_generator(api_key="AQ.test", http_post=post)("hi")
    config = post.calls[0]["json"]["generationConfig"]
    assert "temperature" not in config          # Gemini 3 default (1.0) is used
    assert config["maxOutputTokens"] == 16384


def test_progress_messages_are_sent():
    messages = []
    generate = make_gemini_generator(api_key="AQ.test", http_post=gemini_post(200, OK_REPLY),
                                     progress=messages.append)
    generate("hi")
    assert messages and messages[0].startswith("Waiting for Gemini")


# ---- Mistral as a second AI service, and switching between services

from analyse import MISTRAL_URL, chain_generators, make_ai_generator, make_mistral_generator
from errors import ServiceUnavailableError


def mistral_post(status, payload=None):
    calls = []

    def post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        return FakeHTTPResponse(status, payload)

    post.calls = calls
    return post


MISTRAL_OK = {"choices": [{"message": {"content": '{"problems": []}'}}]}


def test_mistral_request_and_reply():
    post = mistral_post(200, MISTRAL_OK)
    generate = make_mistral_generator(api_key="mk-test", model="mistral-test", http_post=post)
    assert generate("hello") == '{"problems": []}'
    call = post.calls[0]
    assert call["url"] == MISTRAL_URL
    assert call["headers"]["Authorization"] == "Bearer mk-test"
    assert call["json"]["response_format"] == {"type": "json_object"}
    assert call["json"]["messages"] == [{"role": "user", "content": "hello"}]


@pytest.mark.parametrize("status, error, expected", [
    (401, AnalysisError, "API key"),
    (429, ServiceUnavailableError, "free limit"),
    (503, ServiceUnavailableError, "busy"),
])
def test_mistral_errors(status, error, expected):
    generate = make_mistral_generator(api_key="mk-test", http_post=mistral_post(status, {}))
    with pytest.raises(error, match=expected):
        generate("hello")


def busy_generator(*a):
    raise ServiceUnavailableError("Gemini is busy or unavailable right now.")


def test_chain_switches_to_mistral_when_gemini_is_busy():
    notes = []
    mistral = make_mistral_generator(api_key="mk-test", model="mistral-test",
                                     http_post=mistral_post(200, MISTRAL_OK))
    generate = chain_generators([("Gemini", busy_generator), ("Mistral", mistral)], progress=notes.append)
    assert generate("hi") == '{"problems": []}'
    assert generate.model_name == "Mistral: mistral-test"
    assert any("switching to Mistral" in n for n in notes)


def test_chain_does_not_switch_on_a_real_error():
    def bad_key(prompt):
        raise AnalysisError("Gemini rejected the API key.")
    called = []
    generate = chain_generators([("Gemini", bad_key), ("Mistral", lambda p: called.append(p))])
    with pytest.raises(AnalysisError, match="API key"):
        generate("hi")
    assert called == []


def test_gemini_only_and_busy_suggests_adding_groq():
    generate = chain_generators([("Gemini", busy_generator)])
    with pytest.raises(ServiceUnavailableError, match="GROQ_API_KEY"):
        generate("hi")


def test_ai_generator_uses_keys_present_and_provider_choice(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test")
    monkeypatch.setenv("MISTRAL_API_KEY", "mk-test")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    assert make_ai_generator().model_name == "Gemini, Mistral"
    monkeypatch.setenv("AI_PROVIDER", "mistral")
    assert make_ai_generator().model_name == "Mistral, Gemini"
    monkeypatch.delenv("GEMINI_API_KEY")
    assert make_ai_generator().model_name == "Mistral"


def test_no_ai_key_at_all_is_a_config_error(monkeypatch):
    from errors import ConfigError
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        make_ai_generator()



# ---- excerpts must end on a whole word (bug found in the first live run)

from analyse import excerpt


def test_excerpt_ends_on_a_whole_word():
    text = "rising wage pressure, tighter regulation and workforce shortages " * 40
    cut = excerpt(text, limit=1000)
    assert cut.endswith(" [...]")
    body = cut[:-len(" [...]")]
    assert text.startswith(body) and text[len(body)] == " "   # next char is a space: no half word


def test_short_text_is_not_cut():
    assert excerpt("short text", limit=1000) == "short text"


def test_prompt_asks_for_three_to_seven_problems(answers, sources):
    assert "Return 3 to 7 problems" in build_prompt(answers, sources)



def test_prompt_requires_relevant_sources_and_names_other_countries(answers, sources):
    prompt = build_prompt(answers, sources)
    assert "Only quote a source that is about this sector" in prompt
    assert "different country than the founder's market" in prompt
    assert "Use each quote for one problem only" in prompt



# ---- speed: fast model first, slow models skipped (17 Nov 2026, live run took > 3 min)

from analyse import FAST_MODEL, GEMINI_TIMEOUT


def test_fast_model_is_tried_first_by_default(monkeypatch):
    monkeypatch.delenv("AI_SPEED", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-flash-latest")
    post = gemini_post(200, OK_REPLY)
    generate = make_gemini_generator(api_key="AQ.test", http_post=post)
    generate("hi")
    assert post.calls[0]["url"].endswith(f"/models/{FAST_MODEL}:generateContent")


def test_quality_setting_tries_the_configured_model_first(monkeypatch):
    monkeypatch.setenv("AI_SPEED", "quality")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-flash-latest")
    post = gemini_post(200, OK_REPLY)
    make_gemini_generator(api_key="AQ.test", http_post=post)("hi")
    assert "/models/gemini-flash-latest:" in post.calls[0]["url"]


def test_slow_model_is_skipped_for_the_next_one(monkeypatch):
    monkeypatch.delenv("AI_SPEED", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-flash-latest")
    calls, notes = [], []

    def post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        assert timeout == GEMINI_TIMEOUT == 90
        if FAST_MODEL in url:
            raise _requests.Timeout()
        return FakeHTTPResponse(200, OK_REPLY)

    generate = make_gemini_generator(api_key="AQ.test", http_post=post, progress=notes.append,
                                     http_get=lambda *a, **k: FakeHTTPResponse(403, {}),
                                     sleep=lambda s: None)
    assert generate("hi") == '{"problems": []}'
    assert generate.model_name == "gemini-flash-latest"
    assert len(calls) == 2                       # no same-model retry after a timeout
    assert any("too slow" in n for n in notes)


def test_switching_never_repeats_a_model():
    calls = []

    def post(url, headers=None, json=None, timeout=None):
        calls.append(url.split("/models/")[1].split(":")[0])
        return FakeHTTPResponse(503, {"error": {"message": "overloaded"}})

    listing = {"models": [{"name": "models/gemini-a", "supportedGenerationMethods": ["generateContent"]},
                          {"name": "models/gemini-9-flash", "supportedGenerationMethods": ["generateContent"]}]}
    generate = make_gemini_generator(api_key="AQ.test", model="gemini-a", http_post=post,
                                     http_get=lambda *a, **k: FakeHTTPResponse(200, listing),
                                     sleep=lambda s: None)
    with pytest.raises(AnalysisError):
        generate("hi")
    # the switching round never repeats a model; the final call is the planned last try
    assert calls == ["gemini-a", "gemini-a", "gemini-9-flash", "gemini-a"]



# ---- live run 17 Nov 21:08: Lite models answered "busy" in 2 s, the full model gave no answer in 90 s

LIVE_LIST = {"models": [
    {"name": "models/gemini-flash-latest", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.5-flash-lite", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.1-flash-lite", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.6-flash", "supportedGenerationMethods": ["generateContent"]},
]}


def test_when_busy_all_lite_models_are_tried_before_the_slow_full_model(monkeypatch):
    monkeypatch.delenv("AI_SPEED", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-flash-latest")
    busy = (503, {"error": {"message": "overloaded"}})
    post = scripted_post({FAST_MODEL: [busy], "gemini-3.5-flash-lite": [busy],
                          "gemini-3.1-flash-lite": [(200, OK_REPLY)],
                          "gemini-flash-latest": [busy], "gemini-3.6-flash": [busy]})
    generate = make_gemini_generator(api_key="AQ.test", http_post=post,
                                     http_get=lambda *a, **k: FakeHTTPResponse(200, LIVE_LIST),
                                     sleep=lambda s: None)
    assert generate("hi") == '{"problems": []}'
    assert generate.model_name == "gemini-3.1-flash-lite"
    assert "gemini-flash-latest" not in post.calls        # the slow model was never needed
    assert post.calls == [FAST_MODEL, FAST_MODEL, "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]


def test_full_models_come_last_when_busy(monkeypatch):
    monkeypatch.delenv("AI_SPEED", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-flash-latest")
    busy = (503, {"error": {"message": "overloaded"}})
    post = scripted_post({FAST_MODEL: [busy], "gemini-3.5-flash-lite": [busy],
                          "gemini-3.1-flash-lite": [busy], "gemini-flash-latest": [busy],
                          "gemini-3.6-flash": [busy]})
    generate = make_gemini_generator(api_key="AQ.test", http_post=post,
                                     http_get=lambda *a, **k: FakeHTTPResponse(200, LIVE_LIST),
                                     sleep=lambda s: None)
    with pytest.raises(AnalysisError):
        generate("hi")
    order = post.calls[2:-1]
    assert order == ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-latest", "gemini-3.6-flash"]


def test_no_new_model_is_started_after_the_time_budget():
    from analyse import TIME_BUDGET
    now = [0.0]
    busy = (503, {"error": {"message": "overloaded"}})
    post = scripted_post({"gemini-a": [busy], "gemini-3.5-flash-lite": [busy],
                          "gemini-3.1-flash-lite": [busy], "gemini-flash-latest": [busy],
                          "gemini-3.6-flash": [busy]})

    def slow_post(url, **kwargs):
        now[0] += TIME_BUDGET / 2          # every call "takes" half the budget
        return post(url, **kwargs)

    generate = make_gemini_generator(api_key="AQ.test", model="gemini-a", http_post=slow_post,
                                     http_get=lambda *a, **k: FakeHTTPResponse(200, LIVE_LIST),
                                     sleep=lambda s: None, clock=lambda: now[0])
    with pytest.raises(AnalysisError):
        generate("hi")
    assert len(post.calls) == 3            # first model twice, one other, then the budget stops it


def test_last_try_after_a_pause_can_succeed():
    waits = []
    busy = (503, {"error": {"message": "overloaded"}})
    post = scripted_post({"gemini-a": [busy, busy, (200, OK_REPLY)], "gemini-3.6-flash-lite": [busy],
                          "gemini-3.6-flash": [busy], "gemini-3.5-flash": [busy],
                          "gemini-3.6-flash-preview": [busy]})
    generate = make_gemini_generator(api_key="AQ.test", model="gemini-a", http_post=post,
                                     http_get=lambda *a, **k: FakeHTTPResponse(200, MODEL_LIST),
                                     sleep=waits.append)
    assert generate("hi") == '{"problems": []}'
    assert waits == [5, 15]
    assert generate.model_name == "gemini-a"


# ---- Groq as a free backup AI service

from analyse import (GROQ_MODELS, GROQ_MODELS_URL, GROQ_PROMPT_CHARS, GROQ_URL, build_prompt,
                     groq_model_order, make_groq_generator, shrink_prompt, strip_thinking)


GROQ_REPLY = '{"problems": [{"title": "x"}]}'
GROQ_OK = {"choices": [{"message": {"content": GROQ_REPLY}}]}


def groq_post(statuses):
    """Fake POST that answers each call with the next status in the list."""
    calls = []

    def post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        status = statuses[min(len(calls) - 1, len(statuses) - 1)]
        return FakeHTTPResponse(status, GROQ_OK if status == 200 else {})

    post.calls = calls
    return post


def groq_get(ids=None, status=200):
    def get(url, headers=None, timeout=None):
        assert url == GROQ_MODELS_URL
        return FakeHTTPResponse(status, {"data": [{"id": i} for i in (ids or [])]})
    return get


def test_groq_request_and_reply():
    post = groq_post([200])
    generate = make_groq_generator(api_key="gsk-test", http_post=post, http_get=groq_get(list(GROQ_MODELS)))
    assert generate("hello json") == GROQ_REPLY
    call = post.calls[0]
    assert call["url"] == GROQ_URL
    assert call["headers"]["Authorization"] == "Bearer gsk-test"
    assert call["json"]["model"] == GROQ_MODELS[0]
    assert call["json"]["response_format"] == {"type": "json_object"}
    assert generate.model_name == GROQ_MODELS[0]


def test_groq_tries_next_model_when_busy_or_over_limit():
    post = groq_post([503, 404, 200])
    generate = make_groq_generator(api_key="gsk-test", http_post=post, http_get=groq_get(list(GROQ_MODELS)))
    assert generate("hi") == GROQ_REPLY
    assert [c["json"]["model"] for c in post.calls] == list(GROQ_MODELS[:3])
    assert generate.model_name == GROQ_MODELS[2]


def test_groq_too_large_retries_same_model_with_shorter_prompt():
    post = groq_post([413, 200])
    generate = make_groq_generator(api_key="gsk-test", http_post=post, http_get=groq_get(list(GROQ_MODELS)))
    assert generate("hi") == GROQ_REPLY
    assert [c["json"]["model"] for c in post.calls] == [GROQ_MODELS[0], GROQ_MODELS[0]]


def test_groq_all_models_busy_raises_service_unavailable():
    generate = make_groq_generator(api_key="gsk-test", http_post=groq_post([429]), http_get=groq_get([]))
    with pytest.raises(ServiceUnavailableError, match="Groq is busy"):
        generate("hi")


def test_groq_bad_key_stops_immediately():
    post = groq_post([401])
    generate = make_groq_generator(api_key="gsk-bad", http_post=post, http_get=groq_get([], status=401))
    with pytest.raises(AnalysisError, match="API key"):
        generate("hi")
    assert len(post.calls) == 1


def test_groq_model_order_skips_models_the_key_cannot_use():
    assert groq_model_order({"llama-3.3-70b-versatile"}) == ["llama-3.3-70b-versatile"]
    assert groq_model_order(set()) == list(GROQ_MODELS)
    # retired favourites: use other chat models Groq lists, never speech or safety models
    listed = {"whisper-large-v3", "meta-llama/llama-guard-5", "groq/compound", "allam-2-7b",
              "qwen/qwen3.8-27b", "newmodel-70b"}
    assert groq_model_order(listed) == ["qwen/qwen3.8-27b", "newmodel-70b"]
    assert groq_model_order(set(GROQ_MODELS), preferred=GROQ_MODELS[1])[0] == GROQ_MODELS[1]


def test_chain_switches_to_groq_when_gemini_is_busy():
    notes = []
    groq = make_groq_generator(api_key="gsk-test", http_post=groq_post([200]), http_get=groq_get(list(GROQ_MODELS)))
    generate = chain_generators([("Gemini", busy_generator), ("Groq", groq)], progress=notes.append)
    assert generate("hi") == GROQ_REPLY
    assert generate.model_name == f"Groq: {GROQ_MODELS[0]}"
    assert any("switching to Groq" in n for n in notes)


def test_ai_generator_includes_groq_and_provider_choice(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    assert make_ai_generator().model_name == "Gemini, Groq"
    monkeypatch.setenv("AI_PROVIDER", "groq")
    assert make_ai_generator().model_name == "Groq, Gemini"


def test_shrink_prompt_keeps_rules_and_fits_groq_limit():
    sources = [{"id": f"S{i}", "title": f"Title {i}", "domain": "example.com", "origin": "Tavily",
                "query_label": f"q{i % 6}", "text": "word " * 400} for i in range(1, 31)]
    answers = {"sector": "cafes", "geography": "UK", "payer": "Businesses",
               "advantage": "barista", "exclude": ""}
    full = build_prompt(answers, sources)
    small = shrink_prompt(full)
    assert len(full) > GROQ_PROMPT_CHARS >= len(small)
    assert "JSON SHAPE" in small and "FOUNDER ANSWERS" in small and "[S1] Title 1" in small
    assert shrink_prompt("short") == "short"


def test_strip_thinking():
    assert strip_thinking('<think>{maybe}</think>\n{"problems": []}') == '{"problems": []}'


def test_groq_asks_reasoning_models_to_think_briefly():
    from analyse import groq_request
    assert groq_request("openai/gpt-oss-120b", "p")["reasoning_effort"] == "medium"
    assert "reasoning_effort" not in groq_request("llama-3.3-70b-versatile", "p")


def test_groq_tries_next_model_when_no_problems_proposed():
    replies = [{"choices": [{"message": {"content": '{"problems": []}'}}]},
               {"choices": [{"message": {"content": '{"problems": [{"title": "x"}]}'}}]}]
    calls = []

    def post(url, headers=None, json=None, timeout=None):
        calls.append(json["model"])
        return FakeHTTPResponse(200, replies[min(len(calls) - 1, 1)])

    generate = make_groq_generator(api_key="gsk-test", http_post=post, http_get=groq_get(list(GROQ_MODELS)))
    assert "x" in generate("hi")
    assert calls == list(GROQ_MODELS[:2])
