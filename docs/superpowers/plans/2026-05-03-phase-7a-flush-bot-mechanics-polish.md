# Phase 7a — Flush Bot Mechanics Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement four targeted mechanical improvements to FlushBot to raise the average ante reached before the RL training phase.

**Architecture:** All changes confined to `balatrobot/bots/flush_bot.py` and `tests/test_flush_bot.py`. No new files. The existing `flush_synergy` field on joker catalogue entries drives all joker-quality comparisons. Gamestate field names confirmed from `src/utils.lua`: reroll cost at `G["shop"]["reroll_cost"]`, max joker slots at `G["max_jokers"]`, offered blind tag at `G["ante"]["blinds"]["tag"]`.

**Tech Stack:** Python 3.11+, pytest, `balatrobot.data.catalogue` (get_joker, all_jokers, all_planets)

---

## Files

| Action | Path |
|---|---|
| Modify | `balatrobot/bots/flush_bot.py` |
| Modify | `tests/test_flush_bot.py` |

---

## Task 1: sell_jokers no-op

Current `sell_jokers` always sells joker slot 2 when there is more than one joker. Replace with a no-op — selling will only happen reactively in future tasks.

**Files:**
- Modify: `balatrobot/bots/flush_bot.py:162-165`
- Modify: `tests/test_flush_bot.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_flush_bot.py`:

```python
def test_sell_jokers_noop_with_multiple_jokers():
    bot = FlushBot()
    G = {
        "jokers": [
            {"key": "j_tribe", "sell_cost": 3},
            {"key": "j_crafty", "sell_cost": 2},
            {"key": "j_smeared", "sell_cost": 4},
        ]
    }
    action, *args = bot.sell_jokers(G)
    assert action == Actions.SELL_JOKER
    assert args[0] == []
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_flush_bot.py::test_sell_jokers_noop_with_multiple_jokers -v
```

Expected: FAIL — current code returns `[Actions.SELL_JOKER, [2]]` when len(jokers) > 1.

- [ ] **Step 3: Implement**

In `balatrobot/bots/flush_bot.py`, replace `sell_jokers`:

```python
def sell_jokers(self, G):
    return [Actions.SELL_JOKER, []]
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_flush_bot.py::test_sell_jokers_noop_with_multiple_jokers -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add balatrobot/bots/flush_bot.py tests/test_flush_bot.py
git commit -m "fix: sell_jokers is no-op — proactive selling removed"
```

---

## Task 2: Shop reroll

After exhausting all buy priorities, reroll if `dollars >= 25` and `dollars - reroll_cost >= 20`. Reroll cost is available at `G["shop"]["reroll_cost"]`.

**Files:**
- Modify: `balatrobot/bots/flush_bot.py:110-136`
- Modify: `tests/test_flush_bot.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_flush_bot.py`:

```python
def test_reroll_when_rich_and_cost_is_safe():
    bot = FlushBot()
    G = {
        "dollars": 25,
        "shop": {"cards": [], "boosters": [], "reroll_cost": 5},
        "consumables": [],
        "jokers": [],
    }
    assert bot.select_shop_action(G) == [Actions.REROLL_SHOP]


def test_no_reroll_when_would_drop_below_20():
    bot = FlushBot()
    G = {
        "dollars": 23,
        "shop": {"cards": [], "boosters": [], "reroll_cost": 5},
        "consumables": [],
        "jokers": [],
    }
    assert bot.select_shop_action(G) == [Actions.END_SHOP]


def test_no_reroll_when_below_dollar_threshold():
    bot = FlushBot()
    G = {
        "dollars": 20,
        "shop": {"cards": [], "boosters": [], "reroll_cost": 5},
        "consumables": [],
        "jokers": [],
    }
    assert bot.select_shop_action(G) == [Actions.END_SHOP]
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_flush_bot.py::test_reroll_when_rich_and_cost_is_safe tests/test_flush_bot.py::test_no_reroll_when_would_drop_below_20 tests/test_flush_bot.py::test_no_reroll_when_below_dollar_threshold -v
```

Expected: all FAIL — `select_shop_action` never returns `REROLL_SHOP`.

- [ ] **Step 3: Implement**

In `balatrobot/bots/flush_bot.py`, add before the final `return [Actions.END_SHOP]` in `select_shop_action`:

```python
        # Priority 4: reroll if safe to do so
        reroll_cost = (G.get("shop") or {}).get("reroll_cost", 5)
        if dollars >= 25 and dollars - reroll_cost >= 20:
            return [Actions.REROLL_SHOP]
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_flush_bot.py::test_reroll_when_rich_and_cost_is_safe tests/test_flush_bot.py::test_no_reroll_when_would_drop_below_20 tests/test_flush_bot.py::test_no_reroll_when_below_dollar_threshold -v
```

Expected: all PASS

- [ ] **Step 5: Run full test suite**

```
pytest tests/ -v
```

Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add balatrobot/bots/flush_bot.py tests/test_flush_bot.py
git commit -m "feat: reroll shop when dollars >= 25 and won't drop below 20"
```

---

## Task 3: Buffoon pack picks highest-synergy joker

Replace the current Buffoon pack logic (first joker from the `FLUSH_JOKERS` priority list) with: pick the highest `flush_synergy` joker in the pack, but only if a joker slot is free (`len(G["jokers"]) < G["max_jokers"]`).

**Files:**
- Modify: `balatrobot/bots/flush_bot.py:2-3, 138-160`
- Modify: `tests/test_flush_bot.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_flush_bot.py`:

```python
def test_buffoon_pack_picks_highest_synergy_joker():
    # j_smeared has flush_synergy 0.9, j_crafty has 0.7 — should pick j_smeared (index 1)
    bot = FlushBot()
    G = {
        "pack_cards": [
            {"key": "j_crafty"},   # index 0 → 1-based position 1
            {"key": "j_smeared"},  # index 1 → 1-based position 2
        ],
        "jokers": [],
        "max_jokers": 5,
    }
    assert bot.select_booster_action(G) == [Actions.SELECT_BOOSTER_CARD, [2], []]


def test_buffoon_pack_skips_when_joker_slots_full():
    bot = FlushBot()
    G = {
        "pack_cards": [{"key": "j_tribe"}],
        "jokers": [{"key": f"j_placeholder_{i}"} for i in range(5)],
        "max_jokers": 5,
    }
    assert bot.select_booster_action(G) == [Actions.SKIP_BOOSTER_PACK]


def test_buffoon_pack_skips_when_no_joker_has_synergy():
    # Unknown joker key → get_joker returns None → synergy 0.0 → skip
    bot = FlushBot()
    G = {
        "pack_cards": [{"key": "j_unknown_test_joker"}],
        "jokers": [],
        "max_jokers": 5,
    }
    assert bot.select_booster_action(G) == [Actions.SKIP_BOOSTER_PACK]
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_flush_bot.py::test_buffoon_pack_picks_highest_synergy_joker tests/test_flush_bot.py::test_buffoon_pack_skips_when_joker_slots_full tests/test_flush_bot.py::test_buffoon_pack_skips_when_no_joker_has_synergy -v
```

Expected: all FAIL.

- [ ] **Step 3: Add get_joker to the import**

In `balatrobot/bots/flush_bot.py`, change line 3 from:

```python
from balatrobot.data.catalogue import all_jokers, all_planets
```

to:

```python
from balatrobot.data.catalogue import all_jokers, all_planets, get_joker
```

- [ ] **Step 4: Replace the Buffoon pack branch in select_booster_action**

Replace the entire `if first_key and first_key.startswith("j_"):` block with:

```python
        if first_key and first_key.startswith("j_"):
            # Buffoon pack: pick highest flush-synergy joker if a slot is free
            jokers_held = G.get("jokers") or []
            max_jokers = G.get("max_jokers", 5)
            if len(jokers_held) >= max_jokers:
                return [Actions.SKIP_BOOSTER_PACK]
            best_idx: int | None = None
            best_synergy = 0.0
            for idx, card in enumerate(pack_cards):
                key = _card_key(card)
                if not key:
                    continue
                joker_data = get_joker(key)
                synergy = joker_data.flush_synergy if joker_data else 0.0
                if synergy > best_synergy:
                    best_synergy = synergy
                    best_idx = idx
            if best_idx is not None and best_synergy > 0:
                return [Actions.SELECT_BOOSTER_CARD, [best_idx + 1], []]
            return [Actions.SKIP_BOOSTER_PACK]
```

- [ ] **Step 5: Run tests to verify they pass**

```
pytest tests/test_flush_bot.py::test_buffoon_pack_picks_highest_synergy_joker tests/test_flush_bot.py::test_buffoon_pack_skips_when_joker_slots_full tests/test_flush_bot.py::test_buffoon_pack_skips_when_no_joker_has_synergy -v
```

Expected: all PASS

- [ ] **Step 6: Run full test suite**

```
pytest tests/ -v
```

Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add balatrobot/bots/flush_bot.py tests/test_flush_bot.py
git commit -m "feat: buffoon pack selects highest flush-synergy joker when slot available"
```

---

## Task 4: Blind tag skip

`skip_or_select_blind` currently always returns `SELECT_BLIND`. Implement tag evaluation using `SKIP_TAGS`. The offered tag key is at `G["ante"]["blinds"]["tag"]` (None when no tag is on offer).

**Files:**
- Modify: `balatrobot/bots/flush_bot.py:44-47`
- Modify: `tests/test_flush_bot.py`

- [ ] **Step 1: Write failing tests**

Note: `utils.lua` now serialises the tag as `false` (Python `False`) when no tag is on
offer, so `G["ante"]["blinds"]["tag"]` is always present. Test both `False` and absent
key to cover production and synthetic fixtures.

Add to `tests/test_flush_bot.py`:

```python
def test_skip_blind_for_every_skip_tag():
    bot = FlushBot()
    for tag in FlushBot.SKIP_TAGS:
        G = {"ante": {"blinds": {"tag": tag, "chips_needed": 300}}}
        result = bot.skip_or_select_blind(G)
        assert result == [Actions.SKIP_BLIND], f"Expected SKIP_BLIND for tag {tag!r}"


def test_select_blind_for_non_skip_tag():
    bot = FlushBot()
    G = {"ante": {"blinds": {"tag": "tag_uncommon", "chips_needed": 300}}}
    assert bot.skip_or_select_blind(G) == [Actions.SELECT_BLIND]


def test_select_blind_when_tag_is_false():
    # Production serialisation: utils.lua emits false (not nil) when no tag on offer
    bot = FlushBot()
    G = {"ante": {"blinds": {"tag": False, "chips_needed": 300}}}
    assert bot.skip_or_select_blind(G) == [Actions.SELECT_BLIND]


def test_select_blind_when_no_tag_key():
    # Synthetic fixture edge case: tag key absent entirely
    bot = FlushBot()
    G = {"ante": {"blinds": {"chips_needed": 300}}}
    assert bot.skip_or_select_blind(G) == [Actions.SELECT_BLIND]
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_flush_bot.py::test_skip_blind_for_every_skip_tag tests/test_flush_bot.py::test_select_blind_for_non_skip_tag tests/test_flush_bot.py::test_select_blind_when_tag_is_false tests/test_flush_bot.py::test_select_blind_when_no_tag_key -v
```

Expected: all FAIL — current code always returns `SELECT_BLIND`.

- [ ] **Step 3: Implement**

Replace `skip_or_select_blind` in `balatrobot/bots/flush_bot.py`:

```python
    def skip_or_select_blind(self, G):
        offered_tag = ((G.get("ante") or {}).get("blinds") or {}).get("tag")
        if offered_tag and offered_tag in self.SKIP_TAGS:
            return [Actions.SKIP_BLIND]
        return [Actions.SELECT_BLIND]
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_flush_bot.py::test_skip_blind_for_every_skip_tag tests/test_flush_bot.py::test_select_blind_for_non_skip_tag tests/test_flush_bot.py::test_select_blind_when_tag_is_false tests/test_flush_bot.py::test_select_blind_when_no_tag_key -v
```

Expected: all PASS

- [ ] **Step 5: Run full test suite and linters**

```
pytest tests/ -v
ruff check --fix balatrobot/ tests/
mypy balatrobot/
```

Expected: all tests pass, no ruff or mypy errors.

- [ ] **Step 6: Commit**

```bash
git add balatrobot/bots/flush_bot.py tests/test_flush_bot.py
git commit -m "feat: skip blind when offered tag is in SKIP_TAGS"
```

---

## Task 5: Live verification run

Confirm all four mechanics work correctly in a real Balatro game and that ante performance meets or exceeds the Phase 6 baseline (avg 2.1, Ante 3+ at 16.1%).

**Files:** none

- [ ] **Step 1: Run 10 games**

```
python run_flush_bot.py --runs 10
```

- [ ] **Step 2: Verify run_history.json**

Check that:
- 10 new entries were added with timestamps from this run
- All entries have a non-zero score
- No entries indicate a freeze or unhandled exception
- Average ante reached across the 10 runs is ≥ 2.5

The quickest way to check average ante:

```python
import json
history = json.load(open("run_history.json"))
recent = history[-10:]
avg = sum(r["ante_reached"] for r in recent) / len(recent)
print(f"Average ante: {avg:.2f}")
```

**PASS:** Average ante ≥ 2.5, no crashes  
**FAIL:** Any freeze, crash, missing entry, or average ante < 2.1 (worse than Phase 6 baseline)

- [ ] **Step 3: If passing — invoke finishing-a-development-branch skill**

The phase record and PR are handled by the `superpowers:finishing-a-development-branch` skill. Invoke it once the live run passes.
