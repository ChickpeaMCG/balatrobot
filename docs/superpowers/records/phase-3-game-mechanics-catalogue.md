# Phase 3: Game Mechanics Catalogue — Implementation Record

**Date:** 2026-04 (retrospective — predates superpowers adoption)
**Follows:** Phase 2 (smarter FlushBot, 20-run baseline)
**Precedes:** Phase 4 (run analytics, labelling, failure mode analysis)

---

## Overview

Phase 2 left FlushBot with a hardcoded list of 5 joker keys, two of which didn't exist in the game. Phase 3 delivers a typed, version-controlled catalogue of all Balatro game items and a feature encoder that converts live gamestates into a fixed-size `float32` array — the foundation required for Phase 5 reinforcement learning.

---

## Scope

| Item | Independent? |
|---|---|
| 3a. Static data catalogue (`balatrobot/data/`) | Yes |
| 3b. Feature encoder (`balatrobot/features/`) | Depends on 3a (needs `JokerData`) |
| 3c. FlushBot integration (catalogue-driven `FLUSH_JOKERS`) | Depends on 3a |

---

## What Was Planned

### 3a. Static Data Catalogue

**`scripts/extract_balatro_data.py`** — one-shot parser targeting Balatro's embedded Lua source (ZIP archive inside `Balatro.exe`). Outputs skeleton JSON for jokers, tarots, planets, spectrals, vouchers. Preserves existing manual annotations when re-run.

**`balatrobot/data/models.py`** — typed dataclasses: `JokerData`, `ConsumableData`, `EditionData`, `SealData`, `EnhancementData`; `EffectType` and `TriggerCondition` enums.

**`balatrobot/data/catalogue.py`** — registry with `@cache` loading (JSON parsed once per process). `get_joker(key)` logs a warning for unknown keys at runtime. `all_jokers()` returns the full list.

**Annotation strategy:** All keys extracted automatically. `effect_types`, `trigger`, and `flush_synergy` annotated manually starting with ~25 flush-relevant jokers. Remaining jokers get `effect_types: []` as placeholders — safe since bots only query `flush_synergy >= 0.7`.

**Design decisions:**
- **No database** — JSON files + Python dataclasses. ~300KB, version-controlled, no relational queries needed.
- **Exhaustiveness guaranteed by extraction** — re-run on any game patch to detect additions/removals by diffing committed JSON.

### 3b. Feature Encoder

Converts a live `G` dict into a fixed-size `float32` numpy array for SB3 compatibility.

**Observation space: `Box(300,) float32`**

| Segment | Dims | Content |
|---|---|---|
| Global scalars | 9 | ante, dollars, hands_left, discards_left, log(chips_needed), log(current_chips), deficit_fraction, deck_size/52, hands_played/100 |
| Hand cards | 152 | 8 slots × 19 dims (suit one-hot(4) + value(1) + enhancement one-hot(4) + edition(1) + seal one-hot(3) + is_stone(1) + ...) |
| Joker slots | 80 | 5 slots × 16 dims (effect_types one-hot(9) + base_chips(1) + base_mult(1) + is_scaling(1) + is_conditional(1) + flush_synergy(1) + edition_bonus(1) + is_eternal(1)) |
| Consumables | 12 | 2 slots × 6 dims (category one-hot(3) + simplified effect(3)) |
| Hand scores | 39 | 13 hand types × 3 dims (chips/200, mult/20, level/10) |
| Shop flags | 8 | Binary: is each top-8 flush-synergy joker present and affordable? |

Empty slots zero-padded. Unknown joker keys → zero joker vector (safe degradation).

### 3c. FlushBot Integration

Replace hardcoded `FLUSH_JOKERS` list with:
```python
from balatrobot.data.catalogue import all_jokers
FLUSH_JOKERS = [j.key for j in sorted(all_jokers(), key=lambda j: j.flush_synergy, reverse=True) if j.flush_synergy >= 0.7]
```

---

## What Was Built

### Extraction script (`scripts/extract_balatro_data.py`)

Reads `game.lua` from inside the Balatro executable (LÖVE2D ZIP-embedded archive). Handles both single- and double-quoted Lua strings. Merges new skeletons with existing manual annotations on re-run.

Extracted: **150 jokers**, 22 tarots, 12 planets, 18 spectrals, 32 vouchers.

### Data package (`balatrobot/data/`)

- `models.py` — all dataclasses and enums as planned
- `catalogue.py` — all `get_*` / `all_*` functions; `@cache` loaders; runtime unknown-key warning
- `jokers.json` — 150 jokers, 22 annotated with effect_types/trigger/flush_synergy
- `tarots.json`, `planets.json`, `spectrals.json`, `vouchers.json` — full skeletons
- `editions.json`, `seals.json`, `enhancements.json` — fully annotated (5, 4, 9 entries)

### Feature encoder (`balatrobot/features/`)

- `constants.py` — all dimension counts; `OBSERVATION_SHAPE = 300`
- `encoder.py` — `GamestateEncoder.encode(G) -> np.ndarray(float32, shape=(300,))`; handles missing/None fields and unknown joker keys gracefully

Game version confirmed: **1.0.1o** (self-reported in `globals.lua`).

### FlushBot integration

Replaced hardcoded list with catalogue-driven query. Correct keys: `['j_droll', 'j_four_fingers', 'j_tribe', 'j_smeared', 'j_crafty']`. Updated two unit tests that referenced the old incorrect keys.

---

## Bugs Found During Implementation

### Bug #1 — FlushBot's shop strategy never fired (incorrect joker keys)

**Symptom:** Extracting all 150 joker keys revealed that `j_flush` and `j_4_fingers` don't exist in Balatro. The Phase 2 priority list contained phantom keys.

**Root cause:** Keys were invented without consulting the game source. The correct keys are `j_droll` ("Droll Joker") and `j_four_fingers` ("Four Fingers").

**Fix:** Replaced hardcoded list with `all_jokers()` filtered by `flush_synergy >= 0.7`.

**Impact:** The bot was blind to its most important shop items for all Phase 2 runs. The baseline result (avg ante 1.5, 2% reaching ante 4) may improve significantly with correct joker purchasing.

---

### Bug #2 — Lua single-quoted strings not matched by extractor

**Symptom:** Initial extraction found only 135 jokers (not 150).

**Root cause:** Regex `set = "Joker"` didn't handle both quote styles. ~15 jokers in `game.lua` use single quotes.

**Fix:** Updated `_extract_field` and all set-detection regexes to use `["']...["']` pattern.

---

## Current State Per Sub-Task

| Sub-task | Status | Notes |
|---|---|---|
| **3a. Extraction script** | ✅ Done | 150 jokers, 22 tarots, 12 planets, 18 spectrals, 32 vouchers |
| **3a. models.py** | ✅ Done | All dataclasses and enums |
| **3a. catalogue.py** | ✅ Done | All `get_*` / `all_*`; `@cache` loaders; runtime warning |
| **3a. JSON data files** | ✅ Done | Editions/seals/enhancements complete; jokers 22/150 annotated |
| **3a. test_catalogue.py** | ✅ Done | 18 tests, all passing |
| **3b. constants.py** | ✅ Done | `OBSERVATION_SHAPE = 300` |
| **3b. encoder.py** | ✅ Done | Shape/dtype verified, values in [0, 1] |
| **3b. test_encoder.py** | ✅ Done | 10 tests against empty states and cached gamestates |
| **3c. FlushBot integration** | ✅ Done | Catalogue-driven `FLUSH_JOKERS`; unit tests updated |

---

## What Is Explicitly Out of Scope

- Full joker annotation (only top ~25 annotated; expand as analytics show what matters)
- Deferred Phase 2 items (`current_chips`, blind skipping) — carry forward unchanged
- Consumable use strategy
- RL training or SB3 integration (Phase 5)

---

## Deferred Items (carry into Phase 4)

Items carried from Phase 2:

1. **`current_chips` correct Lua field** — `G.GAME.chips` is always 0. Find the correct field, then wire `_should_play` back in.
2. **Blind skipping** — expose offered tag in `Utils.getBlindData()` (Lua), then re-enable skip logic in FlushBot.
3. **Full joker annotation** — only top ~25 annotated; expand lazily as Phase 4 analytics reveal which jokers matter most.
