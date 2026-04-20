# Phase 4b: Bot Fixes — Design Spec

**Date:** 2026-04-19
**Branch:** phase-4-analytics (continues from 4a)
**Follows:** Phase 4a (run labelling, best-run capture)
**Precedes:** Phase 4c (run accumulation + analytics)

---

## Overview

Phase 4b contains four discrete code changes that fix known broken behaviour and extend the data captured per run. Phase 4c (separate branch) will accumulate 200+ runs against the improved bot and then run analytics.

This split is intentional: analytics on a broken bot produces noise, not signal.

---

## Scope

| Item | Independent? |
|---|---|
| 1. Research + fix `current_chips` Lua field | Yes |
| 2. Re-enable `_should_play` in FlushBot | Blocked on item 1 |
| 3. Blind skipping infrastructure (Lua + Python) | Yes |
| 4. Extend run history schema with failure mode fields | Yes |

Items 1 and 2 are sequential. Items 3 and 4 are independent of each other and of 1/2.

---

## Item 1 — Research + Fix `current_chips`

**Problem:** `G.GAME.chips` is always 0. The correct field for chips scored toward the current blind is unknown.

**Research step (before any code):** During a live run, print-log candidates from `G.GAME.current_round` and `G.GAME.blind` to identify the field that reflects chips accumulated in the current hand/round. This must be confirmed before writing any code.

**If the field is stored:** Add it directly to `Utils.getGamestate()` in `src/utils.lua`.

**If the field is computed:** Compute it in Lua before serializing (e.g. sum scored chips from round state).

**Python side:** No schema changes needed — the new field arrives automatically via JSON gamestate as `G["current_chips"]`.

**Test:** Load a cached gamestate, assert `G["current_chips"]` is a non-negative integer and present in the dict.

---

## Item 2 — Re-enable `_should_play`

**Depends on:** Item 1 (`current_chips` must be correct before this logic fires).

**Logic:** If `current_chips >= blind_chip_requirement`, play the best available hand rather than continuing to fish for a flush.

**Guard:** If `current_chips` is 0 (pre-hand or field still missing), `_should_play` must be a no-op — return `False` rather than short-circuiting flush logic incorrectly.

**Prerequisites to confirm before coding:**
- `blind_chip_requirement` is confirmed in the gamestate at `G["blind"]["chips_needed"]` (maps to `G.GAME.blind.chips` in Lua).
- The scaffold in `flush_bot.py` is confirmed wired to `select_cards_from_hand`.

**No new tests required** beyond confirming existing FlushBot tests still pass — the behaviour change is live-game only.

---

## Item 3 — Blind Skipping Infrastructure

**Goal:** Expose the offered skip tag in the gamestate. No strategy logic — `skip_or_select_blind` continues to always return `SELECT_BLIND`.

**Lua (`src/utils.lua` — `getBlindData()`):**
- Research step (same approach as item 1): confirm the Lua field that holds the offered tag when a blind can be skipped. Candidate: `G.GAME.blind_on_deck` or the tag queue. If no tag is offered (boss blind, or blind already selected), serialize as `null`.
- Add `tag` (or `tag_key`, depending on what the field contains) to the blind data table.

**Verification:** Confirm `SKIP_BLIND` is fully wired end-to-end in `src/bot.lua` Lua middleware before treating this as data-only. If it isn't, wire it up as part of this item.

**Python:** No changes to decision logic. The gamestate dict gains a `tag` key readable by future phases.

**Test:** Assert the gamestate includes a `blind.tag` key (value may be `None`).

---

## Item 4 — Extend Run History Schema

**Goal:** Capture enough data at `GAME_OVER` to classify failure mode in Phase 4c without replaying the run.

**New fields added to each run history entry:**

| Field | Source in `G` | Meaning |
|---|---|---|
| `final_chips_needed` | `G["blind"]["chips_needed"]` (confirmed — `G.GAME.blind.chips`) | Blind chip requirement when the run ended |
| `final_chips_scored` | `G["current_chips"]` (item 1 — field TBC) | Chips accumulated toward that blind |
| `final_discards_remaining` | `G["current_round"]["discards_left"]` (confirmed) | Whether we had options left |
| `final_hand_type` | Last played hand type (already in `G`) | What hand we were playing when we died |

**Where to capture:** `_on_run_complete` in `bot.py` already receives `G` — pass the new fields through to `record_run()`.

**Backward compatibility:** Old entries without these fields must not break anything. All analytics code must treat missing fields as `None`. Add one test: load a run history entry without the new fields, assert it parses without error.

---

## What Is Explicitly Out of Scope

- Tag priority logic for blind skipping (Phase 5+)
- Joker correlation or failure mode analysis (Phase 4c)
- Any changes to shop strategy, rerolling, or consumable use
- Multi-instance benchmarking changes

---

## Phase 4c Preview (not designed here)

After 4b lands: create a new branch, accumulate 200+ runs, then build:
- Joker/outcome correlation: which jokers correlate with higher ante reached
- Failure mode classifier: use `final_chips_needed` vs `final_chips_scored` and `final_discards_remaining` to label each loss as chip deficit, out of hands, or bad blind matchup
- Summary report appended to `docs/PLAN_PHASE4.md` via existing `--doc` mechanism
