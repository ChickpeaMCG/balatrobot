# Phase 3: Game Mechanics Catalogue — Implementation Record

## Context

Phase 2 left `FlushBot` with a hardcoded list of 5 joker keys (`FLUSH_JOKERS`) and no knowledge of what any item in the game actually does. Two problems with this:

1. The priority list is so narrow it rarely fires — across 20 test runs, none of the 5 target jokers appeared in shop visits.
2. There is no path to ML (Phase 5) without a fixed-size numeric observation vector, which requires knowing item properties up front.

Phase 3 delivers a typed, version-controlled catalogue of all Balatro game items (jokers, tarots, planets, spectrals, editions, seals, enhancements, vouchers) and a feature encoder that converts live gamestates into a fixed-size `float32` array.

**Key design decisions:**
- **No database** — JSON files + Python dataclasses. The data is ~300KB, changes only on game patches, must be version-controlled, and needs no relational queries.
- **Exhaustiveness guaranteed by extraction script** — `scripts/extract_balatro_data.py` parses the game's own Lua source files to produce skeleton JSON covering every item the game can generate. Manual annotation fills in effect semantics.
- **Runtime validation** — `get_joker()` logs a warning for any unknown key encountered during play, acting as a safety net against missing catalogue entries or modded jokers.

---

## What Was Planned

### 3a. Static data catalogue (`balatrobot/data/`)

**`scripts/extract_balatro_data.py`** — one-shot parser targeting:
- `<BalatroInstall>/data/1/Jokers.lua` → `balatrobot/data/jokers.json`
- `<BalatroInstall>/data/1/Tarot.lua` → `balatrobot/data/tarots.json`
- `<BalatroInstall>/data/1/Planet.lua` → `balatrobot/data/planets.json`
- `<BalatroInstall>/data/1/Spectral.lua` → `balatrobot/data/spectrals.json`
- `<BalatroInstall>/data/1/Voucher.lua` → `balatrobot/data/vouchers.json`

Extracts `key`, `name`, `cost` for every item. Re-run on any game patch to detect additions/removals.

**`balatrobot/data/models.py`** — typed dataclasses:

```python
class EffectType(str, Enum):
    CHIPS = "chips"           # flat chip bonus
    MULT = "mult"             # flat mult bonus
    XMULT = "xmult"          # multiplicative mult
    SCALING = "scaling"       # grows over time
    HAND_MODIFIER = "hand_modifier"  # changes hand type rules
    ECONOMY = "economy"       # money/prices
    DECK_MODIFIER = "deck_modifier"  # adds/removes/transforms cards
    COPY_EFFECT = "copy_effect"      # mirrors another joker
    PASSIVE = "passive"       # always-on

class TriggerCondition(str, Enum):
    ALWAYS = "always"
    ON_FLUSH = "on_flush"
    ON_STRAIGHT = "on_straight"
    ON_SCORED_CARD = "on_scored_card"
    ON_HELD_CARD = "on_held_card"
    ON_FACE_CARD = "on_face_card"
    ON_DISCARD = "on_discard"
    END_OF_ROUND = "end_of_round"
    INDEPENDENT = "independent"

@dataclass
class JokerData:
    key: str
    name: str
    base_cost: int
    effect_types: list[EffectType]
    trigger: TriggerCondition
    base_chips: int = 0
    base_mult: int = 0
    base_xmult: float = 1.0
    is_scaling: bool = False
    is_conditional: bool = True
    flush_synergy: float = 0.0   # 0.0–1.0: how useful for a flush strategy
    description: str = ""
    balatro_version: str = "1.0.1n"
```

**`balatrobot/data/catalogue.py`** — registry with `lru_cache` loading (parse JSON once per process):

```python
@lru_cache(maxsize=None)
def _load_jokers() -> dict[str, JokerData]: ...

def get_joker(key: str) -> JokerData | None:
    result = _load_jokers().get(key)
    if result is None:
        logger.warning("Unknown joker key encountered at runtime: %s", key)
    return result

def all_jokers() -> list[JokerData]: ...
```

**Annotation strategy:** All keys extracted automatically; `effect_types`, `trigger`, and `flush_synergy` annotated manually starting with the ~25 flush-relevant jokers. Remaining jokers get `effect_types: []` as placeholders — safe since bots only query `flush_synergy >= 0.7`. Annotate further lazily as Phase 4 analytics reveal what else matters.

**Small catalogues** (`editions.json`, `seals.json`, `enhancements.json`) completed fully in a single session — 5, 4, and 8 entries respectively.

### 3b. Feature encoder (`balatrobot/features/`)

Converts a live `G` dict into a fixed-size `float32` numpy array for SB3 compatibility.

**Observation space: `Box(249,) float32`**

| Segment | Dims | Content |
|---|---|---|
| Global scalars | 9 | ante, dollars, hands_left, discards_left, log(chips_needed), log(current_chips), deficit_fraction, deck_size/52, hands_played/100 |
| Hand cards | 104 | 8 slots × 13 dims (suit one-hot(4) + value scaled(1) + enhancement one-hot(4) + edition(1) + seal one-hot(3)) |
| Joker slots | 80 | 5 slots × 16 dims (effect_types one-hot(9) + base_chips(1) + base_mult(1) + is_scaling(1) + is_conditional(1) + flush_synergy(1) + edition_bonus(1) + is_eternal(1)) |
| Consumables | 12 | 2 slots × 6 dims (category one-hot(3) + simplified effect(3)) |
| Hand scores | 36 | 12 hand types × 3 dims (chips/200, mult/20, level/10) |
| Shop flags | 8 | Binary: is each top-8 flush-synergy joker present and affordable? |

Empty slots zero-padded. Unknown joker keys → zero joker vector (safe degradation).

### 3c. Bot integration

Replace `FlushBot.FLUSH_JOKERS = ["j_4_fingers", ...]` with:

```python
from balatrobot.data.catalogue import all_jokers
FLUSH_JOKERS = [j.key for j in sorted(all_jokers(), key=lambda j: j.flush_synergy, reverse=True) if j.flush_synergy >= 0.7]
```

No behaviour change for current bots; the list is now derived from data rather than hardcoded.

---

## What Was Built

### Extraction script (`scripts/extract_balatro_data.py`)

Reads `game.lua` from the Balatro executable (a LÖVE2D ZIP-embedded archive) and outputs skeleton JSON for all item categories. Key details:
- Balatro embeds all Lua source in `Balatro.exe` as a ZIP — accessible via `zipfile.ZipFile`
- All joker, tarot, planet, spectral, voucher definitions are in `game.lua` as Lua table literals
- Some entries use single-quoted strings, others double-quoted — regex handles both
- The script preserves existing annotations when re-run (merges new skeletons with annotated entries)
- Re-run to detect patch additions/removals by diffing committed JSON

Extracted: **150 jokers**, 22 tarots, 12 planets, 18 spectrals, 32 vouchers.

### Data package (`balatrobot/data/`)

- `models.py` — `JokerData`, `ConsumableData`, `EditionData`, `SealData`, `EnhancementData` dataclasses; `EffectType` and `TriggerCondition` enums
- `catalogue.py` — `get_joker()`, `all_jokers()`, etc.; `@cache` loaders (JSON parsed once per process); runtime `logger.warning` for unknown keys
- `jokers.json` — 150 jokers, 22 annotated with effect_types/trigger/flush_synergy
- `tarots.json`, `planets.json`, `spectrals.json`, `vouchers.json` — full skeletons from extraction
- `editions.json`, `seals.json`, `enhancements.json` — complete (5, 4, 9 entries respectively)

### Feature encoder (`balatrobot/features/`)

- `constants.py` — all dimension counts; `OBSERVATION_SHAPE = 300` (actual dim count: 9 + 8×19 + 5×16 + 2×6 + 13×3 + 8 = 300)
- `encoder.py` — `GamestateEncoder.encode(G) -> np.ndarray(float32, shape=(300,))` — handles missing/None fields and unknown joker keys gracefully

### Bot integration

Replaced hardcoded `FLUSH_JOKERS` list in `flush_bot.py` with catalogue-driven query. Updated two unit tests that referenced the old incorrect keys.

### Version

Game version detected: **1.0.1o** (self-reported in `globals.lua`)

---

## Bugs Found During Implementation

### Bug #1 — FlushBot's shop strategy never fired (incorrect joker keys)

**Symptom:** Extracting all 150 joker keys from the game files revealed that `j_flush` and `j_4_fingers` do not exist in Balatro. The FlushBot `FLUSH_JOKERS` priority list contained two phantom keys, meaning the shop strategy silently skipped every shop visit for these items.

**Root cause:** The keys were invented without consulting the game source. The correct keys are:
- `j_droll` ("Droll Joker") — +4 Mult if hand contains a Flush
- `j_four_fingers` ("Four Fingers") — 4-card Flushes/Straights

**Fix:** Replaced the hardcoded list with `all_jokers()` filtered by `flush_synergy >= 0.7`. The new list is `['j_droll', 'j_four_fingers', 'j_tribe', 'j_smeared', 'j_crafty']`. Updated the two unit tests that referenced the old keys.

**Impact:** The bot was functionally blind to its most important shop items for all Phase 2 runs. The 20-run baseline result (avg ante 1.5, 2% reaching ante 4) may improve significantly once the correct jokers are purchased.

---

### Bug #2 — Lua single-quoted strings not matched by extractor

**Symptom:** Initial extraction found only 135 jokers (not 150). Running with `set = "Joker"` string match missed jokers whose Lua table used single-quoted strings (`set = 'Joker'`).

**Root cause:** Regex `set = "Joker"` didn't handle both quote styles. Approximately 15 jokers in `game.lua` use single quotes.

**Fix:** Updated `_extract_field` and all set-detection regexes to use `["']..["']` pattern.

---

## Current State Per Sub-Task

| Sub-task | Status | Notes |
|---|---|---|
| **3a. Extraction script** | ✅ Done | `scripts/extract_balatro_data.py`; 150 jokers, 22 tarots, 12 planets, 18 spectrals, 32 vouchers |
| **3a. models.py** | ✅ Done | `JokerData`, `ConsumableData`, `EditionData`, `SealData`, `EnhancementData`; `EffectType`/`TriggerCondition` enums |
| **3a. catalogue.py** | ✅ Done | All `get_*` / `all_*` functions; `@cache` loaders; runtime unknown-key warning |
| **3a. JSON data files** | ✅ Done | Editions/seals/enhancements complete; jokers 22/150 annotated; others are stubs |
| **3a. test_catalogue.py** | ✅ Done | 18 tests, all passing |
| **3b. constants.py** | ✅ Done | `OBSERVATION_SHAPE = 300` |
| **3b. encoder.py** | ✅ Done | `GamestateEncoder.encode(G)` — shape/dtype verified, values in [0, 1] |
| **3b. test_encoder.py** | ✅ Done | 10 tests against empty states and cached gamestates |
| **3c. FlushBot integration** | ✅ Done | Catalogue-driven `FLUSH_JOKERS`; old unit tests updated to use real keys |

---

## Deferred Items (carry into Phase 4)

Items carried from Phase 2 — not in scope for Phase 3:

1. **`current_chips` correct field** — find the Balatro Lua field for chips scored toward the current blind mid-round. Then wire `_should_play` back in.
2. **Blind skipping** — expose offered tag in `Utils.getBlindData()` (Lua), then re-enable skip logic.
3. **Full joker annotation** — only top ~25 annotated in Phase 3; expand as analytics show which jokers matter.
