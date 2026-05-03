# Phase 7a: Flush Bot Mechanics Polish — Implementation Record

**Date:** 2026-05-03
**Branch:** feature/phase-7a-flush-bot-mechanics
**Follows:** Phase 6 (Booster Pack & Planet Consumable Use)
**Precedes:** Phase 7b (Gym Environment)

---

## Overview

Phase 7a closes four mechanical gaps in FlushBot to raise the heuristic baseline before the RL training phase begins. The changes are all confined to `flush_bot.py`: selling was made a no-op, a shop reroll is triggered when the bot has sufficient funds, Buffoon pack selection now picks the highest flush-synergy joker instead of the first match on a static list, and blind skipping now uses the offered tag to skip economically-harmful blinds. Average ante reached improved from 2.1 (Phase 6) to 2.5 across 10 verification runs.

---

## Scope

| Item | Independent? |
|---|---|
| 7a-1. `sell_jokers` no-op | Yes |
| 7a-2. Shop reroll (dollars ≥ 25, won't drop below $20) | Yes |
| 7a-3. Buffoon pack — pick highest flush-synergy joker | Yes |
| 7a-4. Blind tag skip (skip when offered tag is in `SKIP_TAGS`) | Yes |

---

## What Was Planned

- Make `sell_jokers` return an empty list unconditionally — reactive selling deferred.
- Add a reroll priority to `select_shop_action`: after all buy priorities, reroll if `dollars >= 25` and `dollars - reroll_cost >= 20`.
- Replace Buffoon pack first-match logic with a synergy-ranked scan using `get_joker` from the catalogue; skip the pack if all joker slots are full or no joker in the pack has `flush_synergy > 0`.
- Implement `skip_or_select_blind`: read `G["ante"]["blinds"]["tag"]` and return `SKIP_BLIND` when the tag is in `SKIP_TAGS`.

A sell-to-upgrade mechanic (sell weakest held joker to make room for a better shop joker) was considered but deferred after confirming the `SELECT_BOOSTER_CARD` protocol has no sell-slot argument — reactive selling during pack-open is not supported by the Lua protocol.

---

## What Was Built

### 7a-1. `sell_jokers` no-op

Single-line replacement: `return [Actions.SELL_JOKER, []]`. The old conditional sold slot 2 whenever the bot held more than one joker, which was never intentional behaviour.

### 7a-2. Shop reroll

Added a Priority 4 block in `select_shop_action`, after Buffoon pack buying and before `END_SHOP`. Reads `reroll_cost` from `G["shop"]["reroll_cost"]` (default 5 if absent). Triggers `REROLL_SHOP` when `dollars >= 25 and dollars - reroll_cost >= 20`.

### 7a-3. Buffoon pack synergy selection

Replaced the static `FLUSH_JOKERS` list scan with an O(n) pass over pack cards that calls `get_joker(key)` for each and tracks the highest `flush_synergy` seen. Skips the pack if: joker slots are full (`len(jokers) >= max_jokers`), or no card has synergy > 0. `get_joker` was added to the catalogue import.

### 7a-4. Blind tag skip

`skip_or_select_blind` reads the offered tag via `((G.get("ante") or {}).get("blinds") or {}).get("tag")`. A falsy check (`if offered_tag`) handles the production-serialised `false` value (Python `False`) that `utils.lua` emits when no tag is on offer. Returns `SKIP_BLIND` only for tags in `SKIP_TAGS = {"tag_double", "tag_economy", "tag_voucher", "tag_coupon"}`.

---

## Bugs Found During Implementation

### 1. Stale test asserting old Celestial pack behaviour

`tests/test_flush_bot_boosters.py::test_celestial_pack_selects_first_when_no_jupiter` was left over from a mid-session fix commit that changed Celestial pack handling to return `SKIP_BOOSTER_PACK` when no Jupiter is present. The test asserted the old `SELECT_BOOSTER_CARD` behaviour. It was removed as a prerequisite before Phase 7a tasks began.

### 2. Tag serialised as `false`, not `nil`

The Phase 7a spec originally assumed the tag key would be absent from `G["ante"]["blinds"]` when no tag was on offer. A Lua fix commit (`6c92d42`) already changed `utils.lua` to serialise `false` instead of `nil`, meaning Python receives `False` (not a missing key). The test fixtures and implementation were updated to handle both `False` and absent key correctly.

---

## Current State Per Sub-Task

| Sub-task | Status | Notes |
|---|---|---|
| **7a-1. `sell_jokers` no-op** | ✅ Done | Single-line body; test verifies 3-joker case returns `[]` |
| **7a-2. Shop reroll** | ✅ Done | 3 tests: safe reroll, would-drop-below-20, below-threshold |
| **7a-3. Buffoon pack synergy** | ✅ Done | 3 tests: highest-synergy wins, full-slots skip, no-synergy skip |
| **7a-4. Blind tag skip** | ✅ Done | 4 tests: every SKIP_TAG, non-skip tag, `False`, absent key |
| **Live verification (10 runs)** | ✅ Done | Avg ante 2.5 — meets pass criteria |

---

## What Is Explicitly Out of Scope

- **Sell-to-upgrade (shop)**: sell weakest held joker to buy a better one from the shop. `SELL_JOKER` is valid during `SHOP` state but the interaction is deferred — selling and buying need to be sequenced correctly and tested in isolation.
- **Voucher evaluation**: no synergy data in catalogue yet.
- **Standard/Spectral/Arcana pack handling**: unchanged from Phase 6.
- **RL training layer**: Phase 7b (gym environment) and Phase 7c (simulator) are separate.

---

## Deferred Items

- **Sell-to-upgrade in shop** — evaluate held jokers vs shop joker by `flush_synergy`; sell weakest if shop joker is strictly better.
- **Phase 7b — Gym Environment** — `BalatroEnv(gym.Env)` wrapping `GamestateEncoder`, validated with a random agent. No training.
- **Phase 7c — Game Simulator** — lightweight simulator so RL training episodes do not require a live Balatro instance.

---

## Benchmark Results

### Phase 7a — 10 verification runs (Checkered Deck, Stake 1, random seeds)

| Metric | Value |
|--------|-------|
| Runs | 10 |
| Avg ante reached | 2.5 |
| Ante 2 exits | 5 (50%) |
| Ante 3 exits | 5 (50%) |

### Phase 6 Baseline

| Metric | Value |
|--------|-------|
| Avg ante reached | 2.1 |
| Ante 3+ rate | 16.1% |

### Summary

Average ante improved from 2.1 to 2.5 (+19%). Ante 3 reach rate improved from 16% to 50% across the 10 verification runs. The sample is small (10 vs 62 runs for Phase 6), but the direction is consistent with the mechanical improvements: the reroll mechanic finds better jokers, synergy-ranked Buffoon pack selection acquires stronger cards, and blind skipping avoids economically-harmful small blinds.
