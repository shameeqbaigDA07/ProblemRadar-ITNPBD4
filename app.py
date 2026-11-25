"""Problem Radar: the Flask web app.

Start it with:  python app.py
Then open:      http://127.0.0.1:5000 in Chrome
"""

import logging
import re
import sys
import threading
import time
import uuid
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
from markupsafe import Markup, escape

from analyse import analyse
from brief import build_brief, money_range
from errors import ProblemRadarError, StorageError
from research import gather_evidence
from scoring import FACTOR_LABELS, WEIGHTS, process
from storage import list_runs, load_run, save_run
from summary import build_conclusion

load_dotenv()  # reads API keys from the .env file next to this script

APP_VERSION = "1.0"
BASE_DIR = Path(__file__).resolve().parent

GEOGRAPHIES = ["UK", "EU", "US", "Global"]
PAYERS = ["Businesses", "Consumers", "Either"]
LIMITS = {"sector": 120, "advantage": 400, "exclude": 200}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("problem_radar")


class _HideStatusPolling(logging.Filter):
    """The progress page asks for /status every 2 seconds; hiding those
    lines keeps the real progress messages visible in the black window."""

    def filter(self, record):
        return "/status" not in record.getMessage()


logging.getLogger("werkzeug").addFilter(_HideStatusPolling())

app = Flask(__name__)
app.config["RUNS_DIR"] = BASE_DIR / "runs"
# The three pipeline steps live in config so tests can swap in fakes
# that need no internet or API keys.
app.config["GATHER"] = gather_evidence
app.config["ANALYSE"] = analyse
app.config["PROCESS"] = process
# Research runs in a background thread so the browser can show live
# progress. Tests switch this off to run each job straight away.
app.config["RUN_IN_BACKGROUND"] = True

JOBS = {}             # job id -> progress record (kept in memory while the app runs)
JOBS_LOCK = threading.Lock()


def validate_form(form):
    """Check the five answers. Returns (answers, errors)."""
    answers = {
        "sector": form.get("sector", "").strip(),
        "geography": form.get("geography", "").strip(),
        "payer": form.get("payer", "").strip(),
        "advantage": form.get("advantage", "").strip(),
        "exclude": form.get("exclude", "").strip(),
    }
    errors = []
    if len(answers["sector"]) < 3:
        errors.append("Please describe the sector in at least 3 characters, "
                      "for example 'independent vet clinics'.")
    if answers["geography"] not in GEOGRAPHIES:
        errors.append("Please choose a geographical market.")
    if answers["payer"] not in PAYERS:
        errors.append("Please choose who would pay.")
    if len(answers["advantage"]) < 3:
        errors.append("Please describe your founder advantage in a sentence.")
    for field, limit in LIMITS.items():
        if len(answers[field]) > limit:
            errors.append(f"Please keep the {field} answer under {limit} characters.")
    return answers, errors


def run_pipeline(answers, progress=None):
    """Gather evidence -> AI analysis -> Python checks and scoring."""
    progress = progress or (lambda message: None)
    started = datetime.now(timezone.utc)
    progress("Searching the web (6 searches) and Hacker News...")
    evidence = app.config["GATHER"](answers)
    log.info("Collected %d sources", len(evidence["sources"]))
    progress(f"Collected {len(evidence['sources'])} sources. Sending them to Gemini "
             "(usually under a minute)...")
    ai = app.config["ANALYSE"](answers, evidence, progress=progress)
    log.info("AI returned %d problems after %d attempt(s)",
             len(ai["analysis"]["problems"]), ai["attempts"])
    progress(f"The AI proposed {len(ai['analysis']['problems'])} problems. "
             "Checking every quote against its source and scoring in Python...")
    result = app.config["PROCESS"](ai["analysis"], evidence["sources"])
    log.info("%d problems passed the evidence rules, %d dropped",
             len(result["ranked"]), len(result["dropped"]))
    progress(f"{len(result['ranked'])} problems passed the evidence rules; "
             f"{len(result['dropped'])} were removed.")
    return {
        "answers": answers,
        "evidence": evidence,
        "ai": ai,
        "result": result,
        "meta": {
            "created_at": started.isoformat(timespec="seconds"),
            "seconds_taken": round((datetime.now(timezone.utc) - started).total_seconds()),
            "model": ai.get("model", ""),
            "app_version": APP_VERSION,
        },
    }


def run_job(job):
    """Run one research job, recording progress for the progress page."""
    def progress(message):
        with JOBS_LOCK:
            job["steps"].append({"seconds": round(time.monotonic() - job["started"]),
                                 "message": message})
        log.info("Progress: %s", message)

    try:
        run = run_pipeline(job["answers"], progress)
        run_id = save_run(run, app.config["RUNS_DIR"])
        progress("Report saved.")
        with JOBS_LOCK:
            job.update(status="done", run_id=run_id)
    except ProblemRadarError as exc:
        log.warning("Analysis stopped: %s", exc)
        with JOBS_LOCK:
            job.update(status="error", error=str(exc), error_status=502)
    except Exception:  # noqa: BLE001 - never show a raw traceback to the user
        log.exception("Unexpected error during analysis")
        with JOBS_LOCK:
            job.update(status="error", error_status=500,
                       error="Something unexpected went wrong. The details are in the "
                             "terminal window. Please try again.")


def render_home(answers=None, errors=None, message=None, status=200):
    return render_template(
        "index.html",
        answers=answers or {},
        errors=errors or [],
        message=message,
        geographies=GEOGRAPHIES,
        payers=PAYERS,
        runs=list_runs(app.config["RUNS_DIR"]),
    ), status


@app.route("/")
def home():
    return render_home()


@app.route("/analyse", methods=["POST"])
def analyse_route():
    answers, errors = validate_form(request.form)
    if errors:
        return render_home(answers, errors, status=400)
    job = {"id": uuid.uuid4().hex[:12], "answers": answers, "status": "running",
           "steps": [], "started": time.monotonic(), "run_id": None, "error": None}
    with JOBS_LOCK:
        JOBS[job["id"]] = job
    if app.config["RUN_IN_BACKGROUND"]:
        threading.Thread(target=run_job, args=(job,), daemon=True).start()
    else:
        run_job(job)
    return redirect(url_for("job_page", job_id=job["id"]))


def _get_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if job is None:
        abort(404)
    return job


@app.route("/jobs/<job_id>")
def job_page(job_id):
    """Live progress while research runs; then the report or the error."""
    job = _get_job(job_id)
    if job["status"] == "done":
        return redirect(url_for("show_run", run_id=job["run_id"]))
    if job["status"] == "error":
        return render_home(job["answers"], [job["error"]], status=job.get("error_status", 500))
    return render_template("progress.html", job=job)


@app.route("/jobs/<job_id>/status")
def job_status(job_id):
    job = _get_job(job_id)
    with JOBS_LOCK:
        return jsonify({
            "status": job["status"],
            "elapsed": round(time.monotonic() - job["started"]),
            "steps": list(job["steps"]),
        })


@app.route("/runs/<run_id>")
def show_run(run_id):
    try:
        run = load_run(run_id, app.config["RUNS_DIR"])
    except StorageError:
        abort(404)
    return render_template(
        "results.html",
        run=run,
        result=run.get("result", {}),
        sources=run.get("evidence", {}).get("sources", []),
        weights=WEIGHTS,
        factor_labels=FACTOR_LABELS,
        conclusion=build_conclusion(run),
        demo=request.args.get("demo") == "1",
    )


@app.route("/runs/<run_id>/brief")
def show_brief(run_id):
    """The 5-page brief: key insights first, laid out for A4 printing."""
    try:
        run = load_run(run_id, app.config["RUNS_DIR"])
    except StorageError:
        abort(404)
    return render_template("brief.html", b=build_brief(run), run_id=run_id, money_range=money_range)


@app.route("/demo")
def demo():
    """Open the newest saved run. Works with no internet connection."""
    runs = list_runs(app.config["RUNS_DIR"])
    if not runs:
        return render_home(message="Demo mode needs at least one saved run. "
                                   "Run one analysis while online first.")
    return redirect(url_for("show_run", run_id=runs[0]["id"], demo=1))


@app.errorhandler(404)
def not_found(_error):
    return render_home(errors=["That page or saved run could not be found."], status=404)


@app.template_filter("link_sources")
def link_sources(text):
    """Turn source IDs such as S12 into links to the source list."""
    escaped = str(escape(text or ""))
    return Markup(re.sub(r"\b(S\d{1,3})\b", r'<a class="src" href="#src-\1">\1</a>', escaped))


@app.template_filter("money")
def money(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    for size, suffix in ((1e9, "bn"), (1e6, "m"), (1e3, "k")):
        if value >= size:
            return f"{value / size:,.1f}{suffix}"
    return f"{value:,.0f}"


if __name__ == "__main__":
    url = "http://127.0.0.1:5000"
    print(f"\nProblem Radar is running. Open {url} in Chrome.")
    print("Press Ctrl+C in this window (or close it) to stop it.\n")
    if "--open" in sys.argv:  # used by start_app.bat
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
