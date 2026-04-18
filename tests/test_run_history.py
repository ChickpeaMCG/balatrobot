"""Tests for run_history label helpers."""
import json
from unittest.mock import patch

from balatrobot.utils.run_history import (
    best_run_for_label,
    format_best_run_markdown,
    record_run,
    runs_for_label,
)

EMPTY_HISTORY = {"best_run": None, "runs": []}


def _history(*runs):
    return {"best_run": None, "runs": list(runs)}


def _run(ante, hands=10, label=None, seed="AAAAAAA"):
    r = {"ante_reached": ante, "hands_played": hands, "seed": seed}
    if label is not None:
        r["label"] = label
    return r


@patch("balatrobot.utils.run_history.HISTORY_FILE")
def test_record_run_stores_label(mock_path):
    mock_path.exists.return_value = False
    written = {}

    def fake_write(text):
        written["data"] = json.loads(text)

    mock_path.write_text.side_effect = fake_write
    entry = record_run("ABC1234", "Blue Deck", 1, 2, "loss", 15, "Flush", label="phase4")
    assert entry["label"] == "phase4"
    assert written["data"]["runs"][0]["label"] == "phase4"


@patch("balatrobot.utils.run_history.HISTORY_FILE")
def test_record_run_omits_label_when_none(mock_path):
    mock_path.exists.return_value = False
    written = {}
    mock_path.write_text.side_effect = lambda t: written.update({"data": json.loads(t)})
    entry = record_run("ABC1234", "Blue Deck", 1, 2, "loss", 15, "Flush")
    assert "label" not in entry
    assert "label" not in written["data"]["runs"][0]


def test_runs_for_label_filters_correctly():
    history = _history(
        _run(2, label="phase3"),
        _run(3, label="phase4"),
        _run(1, label="phase3"),
    )
    result = runs_for_label(history, "phase3")
    assert len(result) == 2
    assert all(r["label"] == "phase3" for r in result)


def test_best_run_for_label_by_ante():
    history = _history(_run(2, label="x"), _run(4, label="x"), _run(3, label="x"))
    best = best_run_for_label(history, "x")
    assert best is not None
    assert best["ante_reached"] == 4


def test_best_run_for_label_tiebreak_hands():
    history = _history(_run(3, hands=20, label="x"), _run(3, hands=35, label="x"))
    best = best_run_for_label(history, "x")
    assert best is not None
    assert best["hands_played"] == 35


def test_best_run_for_label_returns_none_if_no_match():
    history = _history(_run(2, label="other"))
    assert best_run_for_label(history, "unknown") is None


def test_format_best_run_markdown_contains_seed():
    entry = _run(4, hands=30, seed="XYZ9999", label="phase4")
    md = format_best_run_markdown("phase4", entry, total_runs=50)
    assert "XYZ9999" in md
    assert "phase4" in md
    assert "50 runs" in md
    assert "4" in md  # ante
