"""End-to-end tests of the web pages, with the three pipeline steps faked."""

import pytest

import app as app_module
from errors import ResearchError
from scoring import process


@pytest.fixture
def client(tmp_path, sources, good_problem):
    flask_app = app_module.app
    flask_app.config.update(
        TESTING=True,
        RUNS_DIR=tmp_path,
        GATHER=lambda answers: {"sources": sources, "queries": [{"label": "Q", "query": "q"}],
                                "warnings": ["A Tavily search timed out."]},
        ANALYSE=lambda answers, evidence, progress=None: {
            "analysis": {"problems": [good_problem], "evidence_gaps": ["No pricing data"],
                         "rejected": []},
            "attempts": 1, "model": "fake-model", "prompt_chars": 100},
        PROCESS=process,
        RUN_IN_BACKGROUND=False,
    )
    return flask_app.test_client()


FORM = {"sector": "independent vet clinics", "geography": "UK", "payer": "Businesses",
        "advantage": "Former practice manager", "exclude": ""}


def test_home_page_shows_the_five_questions(client):
    html = client.get("/").get_data(as_text=True)
    for text in ("Which industry or sector", "Which geographical market", "Who would pay",
                 "founder advantage", "exclude"):
        assert text in html


def test_form_errors_are_shown_and_answers_kept(client):
    response = client.post("/analyse", data={**FORM, "sector": "", "geography": "Mars"})
    html = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "at least 3 characters" in html
    assert "choose a geographical market" in html
    assert "Former practice manager" in html


def test_full_run_saves_and_shows_results(client, tmp_path):
    response = client.post("/analyse", data=FORM)
    assert response.status_code == 302
    assert "/jobs/" in response.headers["Location"]
    page = client.get(response.headers["Location"], follow_redirects=True).get_data(as_text=True)
    assert len(list(tmp_path.glob("*.json"))) == 1
    for text in ("Top opportunities", "Ranked problems", "Missed appointments",
                 "Verified quote", "Customer touchpoints", "Micro-trends",
                 "Market size cannot yet be estimated", "Opportunity score breakdown",
                 "Founder fit", "Riskiest assumption", "Two-week validation experiment",
                 "Evidence gaps", "No pricing data", "A Tavily search timed out", "80.0",
                 "Final conclusion", "Recommended next step"):
        assert text in page, text


def test_research_error_is_shown_politely(client):
    def failing(answers):
        raise ResearchError("Your free Tavily credits for this month are used up.")
    app_module.app.config["GATHER"] = failing
    response = client.post("/analyse", data=FORM, follow_redirects=True)
    assert response.status_code == 502
    assert "credits for this month are used up" in response.get_data(as_text=True)


def test_unexpected_error_hides_the_traceback(client):
    def crash(answers):
        raise KeyError("secret internal detail")
    app_module.app.config["GATHER"] = crash
    response = client.post("/analyse", data=FORM, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 500
    assert "Something unexpected went wrong" in html
    assert "secret internal detail" not in html


def test_demo_mode_without_runs_explains_what_to_do(client):
    html = client.get("/demo").get_data(as_text=True)
    assert "needs at least one saved run" in html


def test_demo_mode_opens_newest_run_offline(client):
    client.post("/analyse", data=FORM)
    app_module.app.config["GATHER"] = None   # any network use would now crash
    response = client.get("/demo", follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Demo mode." in html and "Missed appointments" in html


def test_unknown_run_is_404(client):
    assert client.get("/runs/20260101-000000-nothing").status_code == 404
    assert client.get("/runs/not-a-valid-id").status_code == 404


def test_progress_steps_are_recorded_and_reported(client):
    response = client.post("/analyse", data=FORM)
    job_id = response.headers["Location"].rsplit("/", 1)[1]
    data = client.get(f"/jobs/{job_id}/status").get_json()
    assert data["status"] == "done"
    messages = [step["message"] for step in data["steps"]]
    assert messages[0].startswith("Searching the web")
    assert any("Collected 3 sources" in m for m in messages)
    assert any("passed the evidence rules" in m for m in messages)
    assert messages[-1] == "Report saved."


def test_running_job_shows_progress_page(client):
    job = {"id": "abc123", "answers": FORM, "status": "running",
           "steps": [{"seconds": 4, "message": "Searching the web"}],
           "started": 0, "run_id": None, "error": None}
    app_module.JOBS["abc123"] = job
    html = client.get("/jobs/abc123").get_data(as_text=True)
    assert "Research in progress" in html and "Searching the web" in html
    assert client.get("/jobs/abc123/status").get_json()["status"] == "running"


def test_unknown_job_is_404(client):
    assert client.get("/jobs/doesnotexist").status_code == 404
    assert client.get("/jobs/doesnotexist/status").status_code == 404


def test_background_mode_returns_immediately(client):
    import threading
    release = threading.Event()

    def slow_gather(answers):
        release.wait(5)
        raise RuntimeError("stop")
    app_module.app.config.update(RUN_IN_BACKGROUND=True, GATHER=slow_gather)
    response = client.post("/analyse", data=FORM)
    assert response.status_code == 302                  # did not wait for the research
    job_id = response.headers["Location"].rsplit("/", 1)[1]
    assert client.get(f"/jobs/{job_id}/status").get_json()["status"] == "running"
    release.set()



def test_status_polling_is_hidden_from_the_black_window():
    import logging
    record = logging.LogRecord("werkzeug", logging.INFO, "", 0,
                               '"GET /jobs/abc/status HTTP/1.1" 200 -', None, None)
    page = logging.LogRecord("werkzeug", logging.INFO, "", 0, '"GET / HTTP/1.1" 200 -', None, None)
    status_filter = app_module._HideStatusPolling()
    assert status_filter.filter(record) is False
    assert status_filter.filter(page) is True
