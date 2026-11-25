"""Tests for saved research runs."""

from datetime import datetime

import pytest

from errors import StorageError
from storage import list_runs, load_run, save_run


def sample_run(sector="independent vet clinics"):
    return {"answers": {"sector": sector, "geography": "UK"},
            "result": {"ranked": [{"title": "A"}, {"title": "B"}]},
            "meta": {"created_at": "2026-11-17T19:00:00+00:00"}}


def test_save_then_load_returns_the_same_run(tmp_path):
    run_id = save_run(sample_run(), tmp_path, now=datetime(2026, 11, 17, 19, 0, 0))
    assert run_id == "20261117-190000-independent-vet-clinics"
    loaded = load_run(run_id, tmp_path)
    assert loaded["answers"]["sector"] == "independent vet clinics"
    assert loaded["id"] == run_id


def test_list_runs_newest_first_with_counts(tmp_path):
    save_run(sample_run("older"), tmp_path, now=datetime(2026, 11, 1, 9, 0, 0))
    save_run(sample_run("newer"), tmp_path, now=datetime(2026, 11, 2, 9, 0, 0))
    runs = list_runs(tmp_path)
    assert [r["sector"] for r in runs] == ["newer", "older"]
    assert runs[0]["problem_count"] == 2


def test_damaged_files_are_skipped_in_the_list(tmp_path):
    save_run(sample_run(), tmp_path, now=datetime(2026, 11, 1, 9, 0, 0))
    (tmp_path / "20261101-100000-broken.json").write_text("{not json", encoding="utf-8")
    assert len(list_runs(tmp_path)) == 1


def test_damaged_file_gives_friendly_error(tmp_path):
    (tmp_path / "20261101-100000-broken.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(StorageError, match="damaged"):
        load_run("20261101-100000-broken", tmp_path)


@pytest.mark.parametrize("bad_id", ["../app", "..\\secrets", "abc", "", "20261101-100000-UPPER"])
def test_unsafe_or_invalid_ids_are_refused(tmp_path, bad_id):
    with pytest.raises(StorageError):
        load_run(bad_id, tmp_path)


def test_missing_run_gives_friendly_error(tmp_path):
    with pytest.raises(StorageError, match="could not be found"):
        load_run("20261101-100000-nothing", tmp_path)


def test_unicode_survives_round_trip(tmp_path):
    run = sample_run("café owners")
    run["result"]["note"] = "£400 – “quoted”"
    run_id = save_run(run, tmp_path, now=datetime(2026, 11, 17, 19, 0, 0))
    assert load_run(run_id, tmp_path)["result"]["note"] == "£400 – “quoted”"


def test_empty_folder_lists_nothing(tmp_path):
    assert list_runs(tmp_path / "does-not-exist") == []
