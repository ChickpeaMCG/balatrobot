# Phase 4: Run Analytics — Implementation Record

**Date:** 2026-04-18 / 2026-04-19
**Branch:** phase-4-analytics
**Follows:** Phase 3 (game mechanics catalogue, feature encoder)
**Precedes:** Phase 5 (documentation site)

> **Note:** Phase 4 is the first phase using the superpowers workflow. Design specs for sub-phases live in `docs/superpowers/specs/`.

---

## Overview

Phase 3 delivered a typed game mechanics catalogue and feature encoder. Phase 4 turns run data into actionable insight — starting with infrastructure to group results by experiment (4a), then fixing known bot defects before accumulating analytics data (4b), then running correlation and failure mode analysis across 200+ runs (4c).

This split is intentional: analytics on a broken bot produces noise, not signal.

---

## Scope

| Item | Independent? | Design Spec |
|---|---|---|
| 4a. Run labelling & best-run capture | Yes | Inline below |
| 4b. Bot fixes (current_chips, blind skipping, schema extension) | Yes | `docs/superpowers/specs/2026-04-19-phase-4b-bot-fixes-design.md` |
| 4c. Joker/outcome correlation + failure mode analysis | Depends on 4b | TBD |

---

## What Was Planned

### 4a. Run Labelling & Best-Run Capture

**`balatrobot/utils/run_history.py`**
- `record_run()` gains optional `label` param — stored in entry when set, omitted when `None`
- `runs_for_label(history, label)` — filters runs by label
- `best_run_for_label(history, label)` — highest `ante_reached`, tiebreak `hands_played`
- `format_best_run_markdown(label, entry, total_runs)` — markdown table for doc insertion

**`balatrobot/runners/recording.py`**
- `get_git_branch()` helper — `git rev-parse --abbrev-ref HEAD`, falls back to `"unlabelled"`
- Default label = `get_git_branch()` at startup; `--label` overrides
- Warning printed when label is `main` or `master`

**Design decisions:**
- **Git branch as default label** — no flag needed in normal usage; switching to a feature branch automatically groups runs. Works naturally with worktrees: each worktree has its own branch, so two agents benchmarking in parallel are isolated by default.
- **`--doc` appends, never overwrites** — safe to run multiple times; each call adds a new block.
- **No schema migration** — old entries without `label` are simply excluded from label-filtered queries.

### 4b. Bot Fixes

See `docs/superpowers/specs/2026-04-19-phase-4b-bot-fixes-design.md` for full spec. Summary:
1. Research + fix `current_chips` Lua field
2. Re-enable `_should_play` in FlushBot (depends on 1)
3. Blind skipping infrastructure (Lua + Python)
4. Extend run history schema with failure mode fields

### 4b. Bot fixes

- **`current_chips` fix** — `G.GAME.chips` is updated via a 0.5s async ease event; the bot re-enters `SELECTING_HAND` before it resolves, so it always read 0. Fix: wrap `G.E_MANAGER.add_event` in `c_initgamehooks()` to intercept ease events targeting `G.GAME.chips` and cache the `ease_to` value synchronously in `BalatrobotAPI.chips_total`. `Utils.getGameData()` reads `chips_total` instead. Verified via live run: `final_chips_scored: 980` (was always 0).
- **`_should_play` wiring** — `select_cards_from_hand` now short-circuits to PLAY when `current_chips > 0 && current_chips >= chips_needed`, stopping flush-fishing when the blind requirement is already met. `_last_hand_type` tracked on all play paths for run history recording.
- **Blind skip tag** — `Utils.getBlindData()` now returns `tag: G.tags[1].key` (or nil). This exposes the offered skip reward so `skip_or_select_blind` can make informed decisions. SKIP_BLIND middleware wiring was already in place.
- **Run history schema** — `record_run()` gains 4 optional keyword params: `final_chips_needed`, `final_chips_scored`, `final_discards_remaining`, `final_hand_type`. Fields are omitted from JSON when None (backward compatible). `RecordingFlushBot._on_run_complete` passes all four from the final gamestate. Verified in live run.

### 4c. Joker/Outcome Correlation & Failure Mode Analysis

After 4b lands on a clean branch: accumulate 200+ runs, then build:
- Joker/outcome correlation: which jokers correlate with higher ante reached
- Failure mode classifier: label each loss using `final_chips_needed` vs `final_chips_scored` and `final_discards_remaining`
- Summary report appended to this doc via `--doc` mechanism

---

## What Was Built

### 4a. Run labelling & best-run capture

All 4a sub-tasks implemented as planned. Key details:

- `format_best_run_markdown` globs `replays/{seed}_*.replay.json` for the replay path — robust to timestamp format drift
- `analyse_runs.py` auto-derives label from git branch only when `--doc` is passed (not on plain `analyse` calls)
- `RecordingFlushBot.__init__` accepts `label` kwarg and stores it for use in `_on_run_complete`

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

## Bugs Found During Implementation

None documented for 4a.

---

## Current State Per Sub-Task

| Sub-task | Status | Notes |
|---|---|---|
| **4a. run_history label + helpers** | ✅ Done | `record_run`, `runs_for_label`, `best_run_for_label`, `format_best_run_markdown` |
| **4a. recording.py git-branch label** | ✅ Done | `get_git_branch()`, `--label` arg, main-branch warning |
| **4a. analyse_runs.py --label/--doc** | ✅ Done | Label filter + doc append |
| **4a. tests/test_run_history.py** | ✅ Done | 7 tests, all passing |
| **4b. `current_chips` Lua field** | ✅ Done | Option A: sync tracker via `G.E_MANAGER.add_event` wrap in `middleware.lua`; verified non-zero in live run |
| **4b. `_should_play` re-enable** | ✅ Done | Early-exit in `select_cards_from_hand` when `current_chips >= chips_needed`; `_last_hand_type` tracked |
| **4b. Blind skipping infrastructure** | ✅ Done | `Utils.getBlindData()` exposes `tag` field via `G.tags[1].key`; SKIP_BLIND wiring pre-existing |
| **4b. Run history schema extension** | ✅ Done | `record_run()` gains 4 optional failure-mode fields; `_on_run_complete` passes them; verified in live run |
| **4c. Joker/outcome correlation** | ⬜ Deferred indefinitely | Needs 200+ run corpus; backlog |
| **4c. Failure mode analysis** | ⬜ Deferred indefinitely | Needs 200+ run corpus; backlog |

---

## What Is Explicitly Out of Scope

- Any strategy changes beyond re-enabling `_should_play` (shop rerolling, consumable use, economy management)
- RL training or SB3 integration (Phase 5)
- Multi-instance benchmarking changes
- Docs site or GitHub Pages (future phase)

---

## Deferred Items

- **4c. Joker/outcome correlation** — deferred indefinitely; needs a 200+ run corpus accumulated on a stable bot. Can be revisited once Phase 6 (RL) generates sufficient data.
- **4c. Failure mode analysis** — deferred indefinitely; same prerequisite as correlation analysis.

---

## Best Run — phase-4-analytics (20 runs)

| Metric | Value |
|--------|-------|
| Ante reached | 2 |
| Hands played | 18 |
| Seed | `4XD6AY3` |
| Deck | Checkered Deck |
| Stake | 1 |
| Replay | `replays\4XD6AY3_2026-04-18T15-07-10.replay.json` |
