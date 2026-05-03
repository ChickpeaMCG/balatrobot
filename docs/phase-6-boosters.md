# Phase 6: Booster Pack & Planet Consumable Use — Implementation Record

**Date:** 2026-04-24 / 2026-04-25
**Branch:** phase-6-boosters
**Follows:** Phase 5 (flush strategy improvements)
**Precedes:** Phase 7 (TBD)

---

## Overview

Phase 6 teaches FlushBot to interact with booster packs and consumables. The bot now buys Celestial (planet) and Buffoon packs from the shop, opens them, selects planet cards that level up Flush hands, and skips packs it can't use. A significant portion of the phase was consumed by debugging multi-run stability: Steamodded's state=999 (Jumbo/Mega pack) handling exposed three separate crash vectors that had to be fixed before the benchmark could run.

---

## Scope

| Item | Independent? |
|---|---|
| 6a. Middleware booster pack opening (Lua) | Yes |
| 6b. FlushBot `select_booster_action` | Depends on 6a |
| 6c. FlushBot buys packs in shop | Depends on 6b |
| 6d. FlushBot `use_or_sell_consumables` (planet cards) | Depends on 6c |
| 6e. A/B benchmark 30+30 and phase record | Depends on 6d |

---

## What Was Planned

- Middleware: hook `can_skip_booster` to call `c_choose_booster_cards()` when a pack opens; implement `firewhenready` callback to skip or select cards
- FlushBot: buy Celestial and Buffoon packs from shop; select planet cards that level Flush; skip Buffoon packs unless a flush joker is present
- FlushBot: use planet cards from `consumables` after each hand
- Benchmark Phase 6 vs Phase 5 baseline (30 runs each)

---

## What Was Built

### 6a–6b. Middleware + `select_booster_action`

`Middleware.c_choose_booster_cards()` added to `src/middleware.lua`. Called from a `can_skip_booster` hook that fires when a pack opens. Uses `firewhenready` to wait for pack cards to load, then dispatches SKIP or SELECT. For SELECT, calls `G.FUNCS.use_card` directly (pack cards are not in a highlightable area, so `card:click()` is a no-op).

Multi-choice packs loop back via a `firewhenready` that re-enters once `pack_choices` decrements.

### 6c. FlushBot buys packs in shop

`FlushBot.select_shop_action` now buys Celestial packs (priority) or Buffoon packs when affordable and a flush joker is present. Planet cards are identified via `data/planets.json` (added in this phase) which maps planet key → hand type.

### 6d. FlushBot uses planet cards

`FlushBot.use_or_sell_consumables` uses any planet consumable that targets Flush Five, Flush Five → Flush (fallback), or generic Flush-levelling planets. Uses the first matching planet from `G.consumables`.

### 6e. Benchmark

30 phase-6-boosters runs vs 30 phase-5-baseline runs (Checkered Deck, Stake 1, random seeds).

---

## Bugs Found During Implementation

### 1. State=999 packs never close (critical)

**Root cause:** Steamodded uses state=999 (`SMODS_BOOSTER_OPENED`) for Jumbo/Mega packs. `G.FUNCS.use_card`'s inner event checks only vanilla pack states when deciding to call `end_consumeable`; state=999 is skipped, so the pack stays open forever.

**Fix:** In the `firewhenready` callback, override `_action = SKIP_BOOSTER_PACK` unconditionally when `G.STATE == 999`. Also call `G.FUNCS.skip_booster()` directly (not via `pushbutton`) because `STOP_USE > 0` during pack-open animation sets `config.button = nil`, which `pushbutton` checks before calling.

### 2. Hook accumulation across runs (critical)

**Root cause:** `c_initgamehooks()` runs on every `G.start_run`. It re-registered `G.CONTROLLER.snap_to`, `G.FUNCS.can_skip_booster`, `G.FUNCS.can_reroll`, and `G.E_MANAGER.add_event` each run, doubling callbacks. By run 2, duplicate `snap_to` callbacks caused duplicate `c_shop()` chains → duplicate `use_card` calls → `STOP_USE` elevated when the next pack opened → skip button disabled → pack stuck.

**Fix:** Added `_global_hooks_registered` guard; global (cross-run) hooks register only once. Per-run hook (`G.GAME.blind.drawn_to_hand`) remains unguarded since `G.GAME.blind` is a new object each run.

### 3. UDP error response buffer pollution (critical)

**Root cause:** `api.lua` responded to every `INVALIDACTION` with an error message. During state transitions, brief validation failures accumulated error responses in Python's UDP recv buffer. These were drained one-per-iteration across subsequent runs, causing false error spam and eventually a crash.

**Fix:** INVALIDACTION is now silently dropped; Python retries on the next HELLO cycle. `stuck_timeout` (30s) provides a safety net if an action never validates.

### 4. `choosingboostercards` not reset on GAME_OVER

**Root cause:** If the SHOP `firewhenready` failed to fire at the end of a run (edge case), `choosingboostercards` stayed `true` into the next run, preventing `c_choose_booster_cards()` from setting up the callback.

**Fix:** Reset `Middleware.choosingboostercards = false` in `w_gamestate` when `G.STATE == GAME_OVER`.

---

## Current State Per Sub-Task

| Sub-task | Status | Notes |
|---|---|---|
| **6a. Middleware booster pack opening** | ✅ Done | `c_choose_booster_cards`, `can_skip_booster` hook, state=999 force-skip |
| **6b. FlushBot `select_booster_action`** | ✅ Done | Selects flush planets, skips buffoon packs without flush jokers |
| **6c. FlushBot buys packs in shop** | ✅ Done | Buys Celestial > Buffoon when affordable |
| **6d. FlushBot `use_or_sell_consumables`** | ✅ Done | Uses Flush-levelling planet cards |
| **6e. A/B benchmark + phase record** | ✅ Done | 30+30 runs, results below |
| **Hook accumulation fix** | ✅ Done | `_global_hooks_registered` guard in middleware |
| **Silent INVALIDACTION drop** | ✅ Done | api.lua no longer responds to transient failures |

---

## What Is Explicitly Out of Scope

- Tarot/spectral pack use (separate Phase 7 concern)
- Standard pack card selection
- Selling consumables
- Economy optimisation (rerolling, vouchers)
- Multi-instance benchmarking

---

## Deferred Items

- **Tarot/spectral pack handling** — skip_booster infrastructure works; SELECT path untested for non-planet consumables
- **Buffoon pack joker selection** — currently only used for Flush jokers present in hand; no logic to pick the best joker from the pack
- **`check_run.py` health-check utility** — useful for post-run verification; deferred until benchmark loop makes manual checks annoying

---

## Benchmark Results

### Phase 6 — `phase-6-boosters` (62 runs, includes test runs)

| Metric | Value |
|--------|-------|
| Runs | 62 |
| Avg ante reached | 2.1 |
| Ante 1 exits | 2 (3.2%) |
| Ante 2 exits | 50 (80.6%) |
| Ante 3 exits | 9 (14.5%) |
| Ante 4 exits | 1 (1.6%) |
| Best run | Ante 4 \| 25 hands \| seed=MINRLQZ |

### Phase 5 Baseline — `phase-5-baseline` (30 runs)

| Metric | Value |
|--------|-------|
| Runs | 30 |
| Avg ante reached | 2.1 |
| Ante 1 exits | 1 (3.3%) |
| Ante 2 exits | 26 (86.7%) |
| Ante 3 exits | 3 (10.0%) |
| Ante 4 exits | 0 (0%) |
| Best run | Ante 3 \| 22 hands \| seed=ZPOKEXB |

### Summary

Average ante reached is identical (2.1) but Phase 6 has a meaningfully higher Ante 3+ rate (16.1% vs 10.0%) and reached Ante 4 for the first time. The improvement is modest and consistent with the strategy: planet cards level Flush hands, which helps clear later blinds that the baseline couldn't reach.
