# Phase 1: Replay & Run History — Implementation Record

**Date:** 2026-04 (retrospective — predates superpowers adoption)
**Follows:** Initial prototype (bot plays end-to-end, no persistence)
**Precedes:** Phase 2 (smarter FlushBot decisions)

---

## Overview

The bot could play Balatro end-to-end but discarded all run data on exit. Phase 1 establishes the persistence layer needed for analytics and eventually training data: run history (every completed run appended to JSON), replay files (ordered gamestate/action pairs for deterministic replay), and a fixed Lua action logger.

---

## Scope

| Item | Independent? |
|---|---|
| 1. Fix `State.GAME_OVER` detection in `bot.py` | Yes |
| 2. Add `_on_run_complete` hook + `_action_log` to `Bot` | Yes |
| 3. Create `run_history.py` | Yes |
| 4. Add `RecordingFlushBot` to `run_flush_bot.py` | Depends on 2 + 3 |
| 5. Create `replay_bot.py` | Depends on 2 |
| 6. Fix `src/botlogger.lua` (path + seed bugs) | Yes |
| 7. Update `.gitignore` | Yes |

---

## What Was Planned

### 1a. Fix `State.GAME_OVER` detection

`chooseaction()` compared `G["state"] == State.GAME_OVER` — a regular `Enum` that never equals the integer value Lua sends. The fix moves the check to `run_step()` using `State.GAME_OVER.value` and calls `_on_run_complete(G)` before returning.

### 1b. Add `_on_run_complete` hook and `_action_log`

Add a no-op `_on_run_complete(G)` to `Bot` base class (subclasses override). Add `self._action_log: list[dict] = []` to `__init__`; each `run_step()` appends `{"state": self.G, "action": action_str}` before sending. Reset at the start of each new run.

### 1c. Create `run_history.py`

Standalone module with no game dependencies:
- `load_history()` — reads `run_history.json`, returns `{"best_run": None, "runs": []}` if absent
- `record_run(seed, deck, stake, ante_reached, result, hands_played, best_hand)` — appends entry, updates `best_run` index, writes file
- `print_run_summary(entry)` — one-line console summary

### 1d. Add `RecordingFlushBot` to `run_flush_bot.py`

Subclass of `FlushBot` that overrides `_on_run_complete` to write a `.replay.json` to `replays/` and call `record_run`. Accepts `--seed` CLI arg.

### 1e. Create `replay_bot.py`

`ReplayBot` reads a `.replay.json` and re-sends recorded actions in order, bypassing all decision logic. Requires `_recv_gamestate()` and `_send_action()` to be extracted as helpers in `bot.py`.

### 1f. Fix `src/botlogger.lua`

Two bugs:
- **Path bug:** `.run` files were saving to the game's CWD instead of the mod directory
- **Seed bug:** `start_run()` used a hardcoded seed `"1OGB5WO"` instead of `G.GAME.pseudorandom.seed`

### 1g. Update `.gitignore`

Add `run_history.json`, `replays/`, `gamestate_cache/`.

---

## What Was Built

All seven items implemented as planned. Key details:

- `RecordingFlushBot._on_run_complete` globs `replays/` for the path using a timestamp-robust pattern
- `replay_bot.py` accepts `--port` to target a specific Balatro instance
- `botlogger.lua` path and seed fixes landed together in a single Lua commit
- `_recv_gamestate()` and `_send_action()` successfully extracted to helpers in `bot.py`

---

## Bugs Found During Implementation

None documented during Phase 1. Downstream issues from this phase (incorrect `GAME_OVER` field, port conflicts) surfaced in Phase 2.

---

## Current State Per Sub-Task

| Sub-task | Status | Notes |
|---|---|---|
| **1a. GAME_OVER detection** | ✅ Done | Uses `State.GAME_OVER.value` in `run_step()` |
| **1b. `_on_run_complete` + `_action_log`** | ✅ Done | No-op default in `Bot`; reset each run |
| **1c. `run_history.py`** | ✅ Done | `record_run`, `load_history`, `print_run_summary` |
| **1d. `RecordingFlushBot`** | ✅ Done | Saves replay + history on GAME_OVER |
| **1e. `replay_bot.py`** | ✅ Done | Deterministic replay from `.replay.json` |
| **1f. `botlogger.lua` fixes** | ✅ Done | Path and seed bugs resolved |
| **1g. `.gitignore`** | ✅ Done | |

---

## What Is Explicitly Out of Scope

- Any bot decision improvements (deferred to Phase 2)
- Analytics or run labelling (deferred to Phase 4)
- Multi-instance benchmarking

---

## Deferred Items (carry into Phase 2)

None from Phase 1. Phase 2 scope was defined independently.
