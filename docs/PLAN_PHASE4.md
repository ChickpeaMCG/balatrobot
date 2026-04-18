# Phase 4: Run Analytics — Implementation Record

## Context

Phase 3 delivered a typed game mechanics catalogue and feature encoder. Phase 4 turns the run data into actionable insight — starting with the infrastructure to group and surface results across experiments.

Before correlating outcomes with jokers or identifying failure modes (4b), runs need to be labelled by experiment so batches can be compared and the best result from each phase documented automatically.

**Key design decisions:**
- **Git branch as default label** — no flag needed in normal usage; switching to a feature branch automatically groups runs. Works naturally with worktrees: each worktree has its own `run_history.json` and branch, so two agents benchmarking in parallel are isolated by default.
- **Warning on `main`/`master`** — non-blocking, just a reminder to branch or pass `--label`.
- **`--doc` appends, never overwrites** — safe to run multiple times; each call adds a new block.
- **No schema migration** — old entries without `label` are simply excluded from label-filtered queries.

---

## What Was Planned

### 4a. Run labelling & best-run capture

**`balatrobot/utils/run_history.py`**
- `record_run()` gains optional `label` param — stored in entry when set, omitted when `None`
- `runs_for_label(history, label)` — filters runs by label
- `best_run_for_label(history, label)` — highest `ante_reached`, tiebreak `hands_played`
- `format_best_run_markdown(label, entry, total_runs)` — markdown table for doc insertion

**`balatrobot/runners/recording.py`**
- `get_git_branch()` helper — `git rev-parse --abbrev-ref HEAD`, falls back to `"unlabelled"`
- Default label = `get_git_branch()` at startup; `--label` overrides
- Warning printed when label is `main` or `master`

**`run_flush_bot.py`** — `--label` argparse arg passed through to runner

**`balatrobot/analytics/analyse_runs.py`**
- `--label` flag: filters analysis to that label (default: git branch when `--doc` is set)
- `--doc PATH` flag: appends `format_best_run_markdown(...)` to the file

**`tests/test_run_history.py`** — 7 unit tests (no game required)

---

## What Was Built

### 4a. Run labelling & best-run capture

All sub-tasks above implemented as planned. Key implementation details:

- `format_best_run_markdown` globs `replays/{seed}_*.replay.json` for the replay path — robust to timestamp format drift between run_history and replay filenames.
- `analyse_runs.py` auto-derives the label from git branch only when `--doc` is passed (not on plain `analyse` calls, to avoid breaking the no-arg usage pattern).
- `RecordingFlushBot.__init__` accepts `label` kwarg and stores it for use in `_on_run_complete`.

### Usage

```bash
# On branch 'phase-4-analytics': label auto-derived
python run_flush_bot.py --runs 100

# Override for a specific experiment
python run_flush_bot.py --runs 50 --label phase4_checkered_vs_blue

# Append best-run summary to this doc
python -m balatrobot.analytics.analyse_runs --doc docs/PLAN_PHASE4.md

# Explicit label
python -m balatrobot.analytics.analyse_runs --label phase4_checkered_vs_blue --doc docs/PLAN_PHASE4.md
```

---

## Current State Per Sub-Task

| Sub-task | Status | Notes |
|---|---|---|
| **4a. run_history label + helpers** | ✅ Done | `record_run`, `runs_for_label`, `best_run_for_label`, `format_best_run_markdown` |
| **4a. recording.py git-branch label** | ✅ Done | `get_git_branch()`, `--label` arg, main-branch warning |
| **4a. analyse_runs.py --label/--doc** | ✅ Done | Label filter + doc append |
| **4a. tests/test_run_history.py** | ✅ Done | 7 tests, all passing |
| **4b. Joker/outcome correlation** | ⏳ Planned | |
| **4b. Failure mode analysis** | ⏳ Planned | |
| **4b. `current_chips` Lua field** | ⏳ Carried from Phase 2 | `G.GAME.chips` is always 0 |
| **4b. `_should_play` re-enable** | ⏳ Carried from Phase 2 | Blocked on `current_chips` |
| **4b. Blind skipping** | ⏳ Carried from Phase 2 | Requires Lua `getBlindData()` change |
