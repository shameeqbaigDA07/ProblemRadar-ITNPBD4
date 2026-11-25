"""Saved runs: each finished analysis is stored as one JSON file in runs/.

Saved runs can be reopened later with no internet connection, which is
what demo mode uses.
"""

import json
import re
from datetime import datetime
from pathlib import Path

from errors import StorageError

RUN_ID_PATTERN = re.compile(r"^\d{8}-\d{6}-[a-z0-9-]{1,40}$")


def _slug(text):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (slug or "run")[:40].strip("-") or "run"


def save_run(run, runs_dir, now=None):
    """Write a run to runs_dir and return its id."""
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    now = now or datetime.now()
    run_id = f"{now:%Y%m%d-%H%M%S}-{_slug(run.get('answers', {}).get('sector'))}"
    run["id"] = run_id
    try:
        (runs_dir / f"{run_id}.json").write_text(
            json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        raise StorageError("The result could not be saved to the runs folder.") from exc
    return run_id


def load_run(run_id, runs_dir):
    """Read one saved run. Only ids made by save_run are accepted."""
    if not RUN_ID_PATTERN.match(run_id or ""):
        raise StorageError("That saved run name is not valid.")
    path = Path(runs_dir) / f"{run_id}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StorageError("That saved run could not be found.") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise StorageError("That saved run is damaged and cannot be opened.") from exc


def list_runs(runs_dir):
    """Summaries of all readable saved runs, newest first."""
    runs_dir = Path(runs_dir)
    if not runs_dir.exists():
        return []
    summaries = []
    for path in runs_dir.glob("*.json"):
        if not RUN_ID_PATTERN.match(path.stem):
            continue
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        answers = run.get("answers", {})
        summaries.append({
            "id": path.stem,
            "sector": answers.get("sector", "Unknown sector"),
            "geography": answers.get("geography", ""),
            "created_at": run.get("meta", {}).get("created_at", ""),
            "problem_count": len(run.get("result", {}).get("ranked", [])),
        })
    return sorted(summaries, key=lambda s: s["id"], reverse=True)
