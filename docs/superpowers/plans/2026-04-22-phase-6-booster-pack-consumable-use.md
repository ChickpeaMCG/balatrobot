# Phase 6: Booster Pack & Planet Consumable Use — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make FlushBot buy Celestial and Buffoon booster packs, pick Jupiter from Celestial (to level Flush) and flush-synergy jokers from Buffoon, and use Planet consumables immediately. Target: ≥30% relative improvement in ante-2 win rate.

**Architecture:** Three independent TDD-driven code changes plus one live-data capture step plus one benchmark step. Dependency chain 6a → 6b → 6c mirrors the spec. No new files outside `balatrobot/data/`, `balatrobot/bots/`, and `tests/`.

**Tech Stack:** Python 3 (dataclasses, pytest, numpy), JSON catalogue files, existing UDP-based Lua mod (no Lua changes needed — `Actions.BUY_BOOSTER`, `SELECT_BOOSTER_CARD`, `USE_CONSUMABLE`, `SKIP_BOOSTER_PACK` all exist in `balatrobot/core/bot.py:36-56`).

**Spec:** `docs/superpowers/specs/2026-04-22-phase-6-booster-pack-consumable-use-design.md`

---

## Task 1: Planet Catalogue Annotation

**Files:**
- Modify: `balatrobot/data/planets.json`
- Modify: `balatrobot/data/models.py` — add `PlanetData` dataclass
- Modify: `balatrobot/data/catalogue.py:39-46,62-64,130-134` — add `_parse_planet`, retarget `_load_planets`, add `all_planets` + `planet_for_hand`
- Test: `tests/test_planets_catalogue.py` (new)

Note: `tests/test_catalogue.py:100-103` already checks `get_planet("c_mars").name == "Mars"`. After this task the return type changes from `ConsumableData` to `PlanetData`, but `.name` is preserved so the existing test stays green.

- [ ] **Step 1.1: Write the failing test**

Create `tests/test_planets_catalogue.py`:

```python
"""Tests for planet catalogue annotations added in Phase 6."""

from balatrobot.data.catalogue import all_planets, get_planet, planet_for_hand
from balatrobot.data.models import PlanetData


class TestPlanetData:
    def test_all_twelve_planets_loaded(self):
        planets = all_planets()
        assert len(planets) == 12

    def test_every_planet_has_hand_type(self):
        for p in all_planets():
            assert isinstance(p, PlanetData)
            assert p.hand_type, f"{p.key} missing hand_type"

    def test_jupiter_levels_flush(self):
        jupiter = get_planet("c_jupiter")
        assert jupiter is not None
        assert jupiter.hand_type == "Flush"
        assert jupiter.softlock is False

    def test_neptune_levels_straight_flush(self):
        neptune = get_planet("c_neptune")
        assert neptune is not None
        assert neptune.hand_type == "Straight Flush"

    def test_softlocked_planets_marked(self):
        for key in ("c_planet_x", "c_ceres", "c_eris"):
            p = get_planet(key)
            assert p is not None
            assert p.softlock is True

    def test_planet_for_hand_flush_returns_jupiter(self):
        p = planet_for_hand("Flush")
        assert p is not None
        assert p.key == "c_jupiter"

    def test_planet_for_hand_unknown_returns_none(self):
        assert planet_for_hand("Not A Real Hand") is None
```

- [ ] **Step 1.2: Run test to verify it fails**

Run: `pytest tests/test_planets_catalogue.py -v`
Expected: FAIL with `ImportError: cannot import name 'PlanetData'`.

- [ ] **Step 1.3: Add PlanetData dataclass**

Append to `balatrobot/data/models.py` (after `EnhancementData` class at line 87):

```python
@dataclass
class PlanetData:
    key: str
    name: str
    base_cost: int
    hand_type: str
    softlock: bool = False
    description: str = ""
    balatro_version: str = "1.0.1o"
```

- [ ] **Step 1.4: Update planets.json with hand_type and softlock**

Replace the entire contents of `balatrobot/data/planets.json` with:

```json
{
  "balatro_version": "1.0.1o",
  "planets": [
    { "key": "c_mercury",  "name": "Mercury",  "base_cost": 3, "hand_type": "Pair",             "softlock": false, "description": "" },
    { "key": "c_venus",    "name": "Venus",    "base_cost": 3, "hand_type": "Three of a Kind",  "softlock": false, "description": "" },
    { "key": "c_earth",    "name": "Earth",    "base_cost": 3, "hand_type": "Full House",       "softlock": false, "description": "" },
    { "key": "c_mars",     "name": "Mars",     "base_cost": 3, "hand_type": "Four of a Kind",   "softlock": false, "description": "" },
    { "key": "c_jupiter",  "name": "Jupiter",  "base_cost": 3, "hand_type": "Flush",            "softlock": false, "description": "" },
    { "key": "c_saturn",   "name": "Saturn",   "base_cost": 3, "hand_type": "Straight",         "softlock": false, "description": "" },
    { "key": "c_uranus",   "name": "Uranus",   "base_cost": 3, "hand_type": "Two Pair",         "softlock": false, "description": "" },
    { "key": "c_neptune",  "name": "Neptune",  "base_cost": 3, "hand_type": "Straight Flush",   "softlock": false, "description": "" },
    { "key": "c_pluto",    "name": "Pluto",    "base_cost": 3, "hand_type": "High Card",        "softlock": false, "description": "" },
    { "key": "c_planet_x", "name": "Planet X", "base_cost": 3, "hand_type": "Five of a Kind",   "softlock": true,  "description": "" },
    { "key": "c_ceres",    "name": "Ceres",    "base_cost": 3, "hand_type": "Flush House",      "softlock": true,  "description": "" },
    { "key": "c_eris",     "name": "Eris",     "base_cost": 3, "hand_type": "Flush Five",       "softlock": true,  "description": "" }
  ]
}
```

- [ ] **Step 1.5: Update catalogue.py — parse, load, expose planets**

In `balatrobot/data/catalogue.py`, update the imports at line 6-14 to include `PlanetData`:

```python
from balatrobot.data.models import (
    ConsumableData,
    EditionData,
    EffectType,
    EnhancementData,
    JokerData,
    PlanetData,
    SealData,
    TriggerCondition,
)
```

Insert a new `_parse_planet` function after `_parse_consumable` (after line 46):

```python
def _parse_planet(entry: dict) -> PlanetData:
    return PlanetData(
        key=entry["key"],
        name=entry["name"],
        base_cost=entry["base_cost"],
        hand_type=entry["hand_type"],
        softlock=entry.get("softlock", False),
        description=entry.get("description", ""),
    )
```

Replace the existing `_load_planets` (currently at lines 61-64):

```python
@cache
def _load_planets() -> dict[str, PlanetData]:
    raw = json.loads((_DATA_DIR / "planets.json").read_text(encoding="utf-8"))
    return {entry["key"]: _parse_planet(entry) for entry in raw["planets"]}
```

Replace the existing `get_planet` (currently at lines 130-134):

```python
def get_planet(key: str) -> PlanetData | None:
    result = _load_planets().get(key)
    if result is None:
        logger.warning("Unknown planet key encountered: %s", key)
    return result


def all_planets() -> list[PlanetData]:
    return list(_load_planets().values())


def planet_for_hand(hand_type: str) -> PlanetData | None:
    for p in _load_planets().values():
        if p.hand_type == hand_type:
            return p
    return None
```

- [ ] **Step 1.6: Run all catalogue tests**

Run: `pytest tests/test_planets_catalogue.py tests/test_catalogue.py -v`
Expected: all tests PASS (including the pre-existing `test_planets_load` which still accesses `.name`).

- [ ] **Step 1.7: Run type and lint checks**

Run: `ruff check --fix balatrobot/ tests/ && mypy balatrobot/`
Expected: no errors.

- [ ] **Step 1.8: Commit**

```bash
git add balatrobot/data/planets.json balatrobot/data/models.py balatrobot/data/catalogue.py tests/test_planets_catalogue.py
git commit -m "feat(data): annotate planets.json with hand_type and add PlanetData

Adds hand_type and softlock fields to all 12 planets plus a PlanetData
dataclass, catalogue helpers (all_planets, planet_for_hand), and tests.
Mapping sourced from game.lua:557-568."
```

---

## Task 2: Shop Booster Pack Purchase

**Files:**
- Modify: `balatrobot/bots/flush_bot.py:90-97` — extend `select_shop_action`
- Test: `tests/test_flush_bot_boosters.py` (new)

The spec requires: priority = (1) flush joker, (2) Celestial pack if no planet already in consumables, (3) Buffoon pack, (4) `END_SHOP`. Pack type detection uses substring match on the pack's `name` field from `G["shop"]["boosters"]`.

- [ ] **Step 2.1: Write the failing test**

Create `tests/test_flush_bot_boosters.py`:

```python
"""Tests for Phase 6 FlushBot additions: booster pack purchase, pack open, consumable use."""

import pytest

from balatrobot.bots.flush_bot import FlushBot
from balatrobot.core.bot import Actions


@pytest.fixture(scope="module")
def bot():
    return FlushBot(deck="Checkered Deck", stake=1, seed=None, bot_port=12345)


def _shop_G(
    dollars: int = 10,
    cards: list[dict] | None = None,
    boosters: list[dict] | None = None,
    consumables: list[dict] | None = None,
):
    return {
        "dollars": dollars,
        "shop": {
            "cards": cards or [],
            "boosters": boosters or [],
        },
        "consumables": consumables or [],
    }


# -----------------------------------------------------------------------------
# Shop priority: flush joker > Celestial pack > Buffoon pack > END_SHOP
# -----------------------------------------------------------------------------

class TestShopPriority:
    def test_flush_joker_beats_celestial_pack(self, bot):
        # A flush joker in shop + a Celestial pack → bot buys the joker.
        flush_joker_key = bot.FLUSH_JOKERS[0]
        G = _shop_G(
            dollars=10,
            cards=[{"key": flush_joker_key, "cost": 5}],
            boosters=[{"key": "p_celestial_normal_1", "name": "Celestial Pack", "cost": 4}],
        )
        action = bot.select_shop_action(G)
        assert action[0] == Actions.BUY_CARD
        assert action[1] == [1]

    def test_celestial_pack_bought_when_no_joker_and_no_planet_held(self, bot):
        G = _shop_G(
            dollars=10,
            cards=[],
            boosters=[{"key": "p_celestial_normal_1", "name": "Celestial Pack", "cost": 4}],
            consumables=[],
        )
        action = bot.select_shop_action(G)
        assert action[0] == Actions.BUY_BOOSTER
        assert action[1] == [1]

    def test_celestial_pack_skipped_when_planet_already_held(self, bot):
        # Already have a planet in consumables → don't buy another Celestial.
        G = _shop_G(
            dollars=10,
            cards=[],
            boosters=[{"key": "p_celestial_normal_1", "name": "Celestial Pack", "cost": 4}],
            consumables=[{"key": "c_jupiter"}],
        )
        action = bot.select_shop_action(G)
        assert action[0] == Actions.END_SHOP

    def test_buffoon_pack_bought_when_celestial_blocked(self, bot):
        # Planet held → skip Celestial. Buffoon pack present → buy it.
        G = _shop_G(
            dollars=10,
            cards=[],
            boosters=[
                {"key": "p_celestial_normal_1", "name": "Celestial Pack", "cost": 4},
                {"key": "p_buffoon_normal_1",   "name": "Buffoon Pack",   "cost": 4},
            ],
            consumables=[{"key": "c_mercury"}],
        )
        action = bot.select_shop_action(G)
        assert action[0] == Actions.BUY_BOOSTER
        # Buffoon pack is at index 2 (1-based).
        assert action[1] == [2]

    def test_unaffordable_pack_not_bought(self, bot):
        G = _shop_G(
            dollars=2,
            cards=[],
            boosters=[{"key": "p_celestial_normal_1", "name": "Celestial Pack", "cost": 4}],
        )
        action = bot.select_shop_action(G)
        assert action[0] == Actions.END_SHOP

    def test_arcana_and_spectral_packs_ignored(self, bot):
        G = _shop_G(
            dollars=10,
            cards=[],
            boosters=[
                {"key": "p_arcana_normal_1",   "name": "Arcana Pack",   "cost": 4},
                {"key": "p_spectral_normal_1", "name": "Spectral Pack", "cost": 4},
                {"key": "p_standard_normal_1", "name": "Standard Pack", "cost": 4},
            ],
        )
        action = bot.select_shop_action(G)
        assert action[0] == Actions.END_SHOP
```

- [ ] **Step 2.2: Run test to verify it fails**

Run: `pytest tests/test_flush_bot_boosters.py -v`
Expected: FAIL. Six failures — all Celestial/Buffoon tests return `END_SHOP` because current `select_shop_action` ignores `shop.boosters`.

- [ ] **Step 2.3: Extend select_shop_action**

Replace `balatrobot/bots/flush_bot.py:90-97` (the full `select_shop_action` method) with:

```python
    def select_shop_action(self, G):
        dollars = G["dollars"]
        shop_cards = G.get("shop", {}).get("cards", [])
        shop_boosters = G.get("shop", {}).get("boosters", [])

        # Priority 1: flush-synergy joker
        for priority_key in self.FLUSH_JOKERS:
            for idx, card in enumerate(shop_cards):
                if card.get("key") == priority_key and card.get("cost", 999) <= dollars:
                    return [Actions.BUY_CARD, [idx + 1]]

        # Priority 2: Celestial pack (only if no planet already waiting in consumables)
        consumables = G.get("consumables", []) or []
        has_planet = any(_is_planet_key(_card_key(c)) for c in consumables)
        if not has_planet:
            for idx, pack in enumerate(shop_boosters):
                name = pack.get("name", "")
                if "Celestial" in name and pack.get("cost", 999) <= dollars:
                    return [Actions.BUY_BOOSTER, [idx + 1]]

        # Priority 3: Buffoon pack
        for idx, pack in enumerate(shop_boosters):
            name = pack.get("name", "")
            if "Buffoon" in name and pack.get("cost", 999) <= dollars:
                return [Actions.BUY_BOOSTER, [idx + 1]]

        return [Actions.END_SHOP]
```

Add two helpers at module scope near the top of `flush_bot.py` (after `_FLUSH_JOKERS` definition, around line 18). Both are reused by Tasks 4 and 5, so they live at module scope:

```python
from balatrobot.data.catalogue import get_planet


def _card_key(card: dict) -> str | None:
    """Extract the catalogue key from a card dict.

    Cards from shop/pack/consumables use either a top-level `key` field or
    nest it under `config.center.key` (per utils.lua:186). Handle both.
    """
    if not isinstance(card, dict):
        return None
    if "key" in card and card["key"]:
        return card["key"]
    center = (card.get("config") or {}).get("center") or {}
    return center.get("key")


def _is_planet_key(key: str | None) -> bool:
    """True if the key matches a known planet in the catalogue."""
    if not key:
        return False
    return get_planet(key) is not None
```

Note: `get_planet` logs a warning on unknown keys. That's fine here — the warning fires only when we see an unknown `c_*` key, which is worth knowing about.

- [ ] **Step 2.4: Run new tests**

Run: `pytest tests/test_flush_bot_boosters.py -v`
Expected: all 6 shop-priority tests PASS.

- [ ] **Step 2.5: Run existing flush_bot tests to check for regression**

Run: `pytest tests/test_flush_bot.py -v`
Expected: all pre-existing tests PASS (no behavior change when `shop.boosters` is empty).

- [ ] **Step 2.6: Run type and lint checks**

Run: `ruff check --fix balatrobot/ tests/ && mypy balatrobot/`
Expected: no errors.

- [ ] **Step 2.7: Commit**

```bash
git add balatrobot/bots/flush_bot.py tests/test_flush_bot_boosters.py
git commit -m "feat(flush_bot): buy Celestial and Buffoon packs in shop

Extends select_shop_action priority: flush joker > Celestial (if no
planet already held) > Buffoon > END_SHOP. Pack detection via name
substring. Unit tests cover all priority paths."
```

---

## Task 3: Live Gamestate Capture (Pack Open + Consumables Shape)

**Files:**
- Modify (manually, via live game run): `gamestate_cache/select_booster_action/*.json`
- Modify (manually): `gamestate_cache/use_or_sell_consumables/*.json` (after buying pack)

**Why this is a separate task:** the exact shape of `G["pack_cards"]` (how `key` is nested on card dicts) is unverified — this task resolves that before Tasks 4 & 5 write tests against the wrong assumption.

**Prerequisite:** Balatro installed, mod symlinked, Steam path at `C:\Program Files (x86)\Steam\steamapps\common\Balatro\Balatro.exe`. Only Task 1 + Task 2 code needs to be live for this (Task 2's shop changes are what triggers the pack purchase).

- [ ] **Step 3.1: Clear the existing stale caches**

These caches were written before the bot bought packs; re-generating with Task 2's code active ensures the new shop decisions are reflected. Safety: only delete subdirectories matching the ones that will be regenerated.

```bash
rm -rf gamestate_cache/select_booster_action gamestate_cache/use_or_sell_consumables gamestate_cache/select_shop_action
```

- [ ] **Step 3.2: Run a single cache-generating session**

Edit `run_flush_bot.py` to pass `cache_states=True` to the `RecordingFlushBot` constructor if it does not already (check the file first — if already wired via a flag, use it).

Run: `python run_flush_bot.py --runs 1 --label phase-6-cache-capture`

Expected: Balatro launches, plays one run. `gamestate_cache/` regenerates. The session must include at least one Celestial pack purchase for the `select_booster_action` cache to populate.

If no Celestial pack appeared in the first run's shops, run again with a different seed: `python run_flush_bot.py --runs 3 --label phase-6-cache-capture`. Continue until at least one `gamestate_cache/select_booster_action/*.json` exists.

- [ ] **Step 3.3: Inspect the cached pack_cards shape**

Run: `python -c "import json, glob; f = sorted(glob.glob('gamestate_cache/select_booster_action/*.json'))[0]; g = json.load(open(f)); print('keys:', list(g.keys())); print('pack_cards type:', type(g.get('pack_cards'))); print('sample card:', json.dumps(g.get('pack_cards', [{}])[0], indent=2)[:500])"`

Expected: prints the gamestate keys (including `pack_cards`) and the shape of the first card in the pack. Record the path to `key` — it is either top-level (`card["key"]`) or nested (`card["config"]["center"]["key"]`). **This is the critical verification — Task 4 depends on it.**

- [ ] **Step 3.4: Inspect the cached consumables shape**

Run: `python -c "import json, glob; f = sorted(glob.glob('gamestate_cache/use_or_sell_consumables/*.json'))[-1]; g = json.load(open(f)); print('consumables:', json.dumps(g.get('consumables', []), indent=2)[:800])"`

Expected: prints the consumables list with at least one planet entry (the one bought via Celestial pack). Record the path to `key` on a consumable card.

- [ ] **Step 3.5: Commit a representative sample as fixtures**

Copy one sample of each new cache type into a permanent fixture directory so Tasks 4 & 5 can test against frozen data that won't drift:

```bash
mkdir -p tests/fixtures/phase6
cp "$(ls gamestate_cache/select_booster_action/*.json | head -1)" tests/fixtures/phase6/pack_celestial_sample.json
cp "$(ls gamestate_cache/use_or_sell_consumables/*.json | tail -1)" tests/fixtures/phase6/consumables_with_planet_sample.json
```

Inspect both files quickly — the consumables fixture must contain a planet (one of the `c_*` keys from Task 1). If it doesn't, pick a different file with `ls gamestate_cache/use_or_sell_consumables/` until you find one that does, or re-run step 3.2 to capture a better moment.

- [ ] **Step 3.6: Commit**

```bash
git add tests/fixtures/phase6/
git commit -m "test(phase6): capture live gamestate fixtures for pack_cards and consumables"
```

---

## Task 4: Pack Open Handler (`select_booster_action`)

**Files:**
- Modify: `balatrobot/bots/flush_bot.py:99-100` — replace the `select_booster_action` method
- Modify: `tests/test_flush_bot_boosters.py` — add pack-open tests

**Prerequisite:** Task 3 complete. The `CARD_KEY_PATH` constant below must be set to match the actual nesting observed in `tests/fixtures/phase6/pack_celestial_sample.json`.

- [ ] **Step 4.1: Determine CARD_KEY_PATH from fixture**

Open `tests/fixtures/phase6/pack_celestial_sample.json`. Find a `pack_cards` entry. The card's key can be at one of two paths:
- `card["key"]` (top-level)
- `card["config"]["center"]["key"]` (nested, matches the shop representation in `utils.lua:186`)

Record which is correct. In the test and implementation below, a helper `_card_key(card)` hides the difference. Adjust the helper if neither path matches (unlikely — `utils.lua:186` is the only known pattern).

- [ ] **Step 4.2: Write the failing tests**

Append to `tests/test_flush_bot_boosters.py`:

```python
# -----------------------------------------------------------------------------
# Pack open (select_booster_action)
# -----------------------------------------------------------------------------

def _pack_G(pack_cards: list[dict], hand: list[dict] | None = None):
    return {
        "pack_cards": pack_cards,
        "hand": hand or [],
    }


def _planet_card(key: str) -> dict:
    # Matches the shape utils.lua:186 produces (card.config.center.key).
    return {"config": {"center": {"key": key}}, "key": key}


def _joker_card(key: str) -> dict:
    return {"config": {"center": {"key": key}}, "key": key}


class TestPackOpen:
    def test_celestial_picks_jupiter_when_present(self, bot):
        G = _pack_G([_planet_card("c_mercury"), _planet_card("c_jupiter"), _planet_card("c_saturn")])
        action = bot.select_booster_action(G)
        assert action[0] == Actions.SELECT_BOOSTER_CARD
        assert action[1] == [2]  # Jupiter at index 2 (1-based)
        assert action[2] == []

    def test_celestial_picks_first_planet_when_no_jupiter(self, bot):
        G = _pack_G([_planet_card("c_mercury"), _planet_card("c_saturn")])
        action = bot.select_booster_action(G)
        assert action[0] == Actions.SELECT_BOOSTER_CARD
        assert action[1] == [1]
        assert action[2] == []

    def test_buffoon_picks_highest_priority_flush_joker(self, bot):
        top_priority = bot.FLUSH_JOKERS[0]
        second_priority = bot.FLUSH_JOKERS[1] if len(bot.FLUSH_JOKERS) > 1 else bot.FLUSH_JOKERS[0]
        # Put the second-priority card first to prove the bot picks by priority, not by order.
        G = _pack_G([_joker_card(second_priority), _joker_card(top_priority)])
        action = bot.select_booster_action(G)
        assert action[0] == Actions.SELECT_BOOSTER_CARD
        assert action[1] == [2]

    def test_buffoon_skips_when_no_known_joker(self, bot):
        G = _pack_G([_joker_card("j_some_unknown_joker"), _joker_card("j_another_unknown")])
        action = bot.select_booster_action(G)
        assert action[0] == Actions.SKIP_BOOSTER_PACK

    def test_empty_pack_cards_skips(self, bot):
        G = _pack_G([])
        action = bot.select_booster_action(G)
        assert action[0] == Actions.SKIP_BOOSTER_PACK
```

- [ ] **Step 4.3: Run tests to verify they fail**

Run: `pytest tests/test_flush_bot_boosters.py::TestPackOpen -v`
Expected: all 5 FAIL — current `select_booster_action` returns `SKIP_BOOSTER_PACK` for every case including Celestial, so the Jupiter/first-planet tests fail on the action type or selected index.

- [ ] **Step 4.4: Implement select_booster_action**

Replace `balatrobot/bots/flush_bot.py:99-100`:

```python
    def select_booster_action(self, G):
        pack_cards = G.get("pack_cards") or []
        if not pack_cards:
            return [Actions.SKIP_BOOSTER_PACK]

        # Identify pack type from the first card's key.
        first_key = _card_key(pack_cards[0])
        is_celestial = first_key is not None and _is_planet_key(first_key)
        is_buffoon = first_key is not None and first_key.startswith("j_")

        if is_celestial:
            # Prefer Jupiter. Otherwise take the first planet — don't skip, money's already spent.
            for i, card in enumerate(pack_cards):
                if _card_key(card) == "c_jupiter":
                    return [Actions.SELECT_BOOSTER_CARD, [i + 1], []]
            return [Actions.SELECT_BOOSTER_CARD, [1], []]

        if is_buffoon:
            # FLUSH_JOKERS is sorted by descending flush_synergy. Take the highest-priority match.
            keys_in_pack = {_card_key(c): i for i, c in enumerate(pack_cards) if _card_key(c)}
            for priority_key in self.FLUSH_JOKERS:
                if priority_key in keys_in_pack:
                    return [Actions.SELECT_BOOSTER_CARD, [keys_in_pack[priority_key] + 1], []]
            return [Actions.SKIP_BOOSTER_PACK]

        # Defensive: Arcana/Spectral/Standard shouldn't reach here (we don't buy those packs).
        return [Actions.SKIP_BOOSTER_PACK]
```

`_card_key` already exists at module scope from Task 2. If Task 3 step 4.1 revealed a nesting path neither `card["key"]` nor `card["config"]["center"]["key"]` covers, adjust `_card_key` now.

- [ ] **Step 4.5: Run new tests**

Run: `pytest tests/test_flush_bot_boosters.py::TestPackOpen -v`
Expected: all 5 PASS.

- [ ] **Step 4.6: Smoke-test against the live fixture**

Run:
```bash
python -c "
import json
from balatrobot.bots.flush_bot import FlushBot
from balatrobot.core.bot import Actions

G = json.load(open('tests/fixtures/phase6/pack_celestial_sample.json'))
bot = FlushBot(deck='Checkered Deck', stake=1, seed=None, bot_port=12345)
action = bot.select_booster_action(G)
print('action:', action[0].name, action[1:])
assert action[0] == Actions.SELECT_BOOSTER_CARD, 'Celestial fixture should not skip'
print('OK — live fixture accepted, picked card', action[1])
"
```

Expected: `action: SELECT_BOOSTER_CARD [<idx>] []`, no assertion errors.

If this fails with `SKIP_BOOSTER_PACK`, the `_card_key` helper is not finding the key — re-check the fixture's card shape and fix the helper.

- [ ] **Step 4.7: Run type and lint checks**

Run: `ruff check --fix balatrobot/ tests/ && mypy balatrobot/`
Expected: no errors.

- [ ] **Step 4.8: Commit**

```bash
git add balatrobot/bots/flush_bot.py tests/test_flush_bot_boosters.py
git commit -m "feat(flush_bot): select Jupiter from Celestial, flush jokers from Buffoon

Implements select_booster_action: Celestial → Jupiter (or first planet
fallback), Buffoon → highest-priority flush joker (skip if none match).
Verified against live fixture."
```

---

## Task 5: Consumable Use (`use_or_sell_consumables`)

**Files:**
- Modify: `balatrobot/bots/flush_bot.py:110-111` — replace `use_or_sell_consumables`
- Modify: `tests/test_flush_bot_boosters.py` — add consumable-use tests

- [ ] **Step 5.1: Write the failing tests**

Append to `tests/test_flush_bot_boosters.py`:

```python
# -----------------------------------------------------------------------------
# Consumable use
# -----------------------------------------------------------------------------

def _consumable_card(key: str) -> dict:
    return {"config": {"center": {"key": key}}, "key": key}


def _consumables_G(consumables: list[dict]):
    return {"consumables": consumables}


class TestConsumableUse:
    def test_uses_jupiter_when_present(self, bot):
        G = _consumables_G([_consumable_card("c_jupiter")])
        action = bot.use_or_sell_consumables(G)
        assert action[0] == Actions.USE_CONSUMABLE
        assert action[1] == [1]

    def test_prefers_jupiter_over_other_planet(self, bot):
        # Jupiter at index 2 should win over Mercury at index 1.
        G = _consumables_G([_consumable_card("c_mercury"), _consumable_card("c_jupiter")])
        action = bot.use_or_sell_consumables(G)
        assert action[0] == Actions.USE_CONSUMABLE
        assert action[1] == [2]

    def test_uses_any_planet_if_no_jupiter(self, bot):
        G = _consumables_G([_consumable_card("c_mercury")])
        action = bot.use_or_sell_consumables(G)
        assert action[0] == Actions.USE_CONSUMABLE
        assert action[1] == [1]

    def test_does_nothing_for_non_planet_consumables(self, bot):
        # A tarot, not a planet — return the no-op form.
        G = _consumables_G([_consumable_card("c_fool")])
        action = bot.use_or_sell_consumables(G)
        assert action[0] == Actions.USE_CONSUMABLE
        assert action[1] == []

    def test_does_nothing_when_empty(self, bot):
        G = _consumables_G([])
        action = bot.use_or_sell_consumables(G)
        assert action[0] == Actions.USE_CONSUMABLE
        assert action[1] == []
```

- [ ] **Step 5.2: Run tests to verify they fail**

Run: `pytest tests/test_flush_bot_boosters.py::TestConsumableUse -v`
Expected: 3 FAIL (the "uses" tests) and 2 PASS (the empty/tarot cases, which currently match the no-op behaviour). Confirm before proceeding.

- [ ] **Step 5.3: Implement use_or_sell_consumables**

Replace `balatrobot/bots/flush_bot.py:110-111`:

```python
    def use_or_sell_consumables(self, G):
        consumables = G.get("consumables") or []
        jupiter_idx = None
        first_planet_idx = None
        for i, card in enumerate(consumables):
            key = _card_key(card)
            if key == "c_jupiter":
                jupiter_idx = i
                break
            if first_planet_idx is None and _is_planet_key(key):
                first_planet_idx = i
        chosen = jupiter_idx if jupiter_idx is not None else first_planet_idx
        if chosen is not None:
            return [Actions.USE_CONSUMABLE, [chosen + 1]]
        return [Actions.USE_CONSUMABLE, []]
```

- [ ] **Step 5.4: Run all phase-6 tests**

Run: `pytest tests/test_flush_bot_boosters.py -v`
Expected: all tests PASS (shop + pack open + consumable use).

- [ ] **Step 5.5: Run the full test suite for regression**

Run: `pytest tests/ -v`
Expected: all tests PASS.

- [ ] **Step 5.6: Run type and lint checks**

Run: `ruff check --fix balatrobot/ tests/ && mypy balatrobot/`
Expected: no errors.

- [ ] **Step 5.7: Commit**

```bash
git add balatrobot/bots/flush_bot.py tests/test_flush_bot_boosters.py
git commit -m "feat(flush_bot): use Planet consumables immediately, Jupiter first

Replaces the no-op use_or_sell_consumables with: scan consumables for
a planet (Jupiter preferred), return USE_CONSUMABLE for its 1-based
index. Falls back to no-op for non-planet consumables."
```

---

## Task 6: Live Verification + A/B Benchmark + Phase Record

**Files:**
- Create: `docs/superpowers/records/phase-6-booster-packs.md` (new)
- Modify: `docs/PLAN.md` — mark Phase 6 complete, trim "Phase 6 — RL Groundwork" (this phase replaces the old Phase 6)

**Prerequisite:** Tasks 1–5 complete and all tests green.

- [ ] **Step 6.1: Single live verification run**

Run: `python run_flush_bot.py --runs 1 --label phase-6-smoke`

Observe the Balatro window. Confirm (visually or via log inspection):
- Bot buys at least one Celestial pack.
- After pack opens, Jupiter is selected if present.
- After pack closes, the Flush hand in the hand-info panel displays Level 2 (was Level 1 at run start).

If Jupiter never appears in any Celestial pack across 2-3 runs, use one of the other planets and verify its corresponding hand level incremented — confirms the mechanism works even when Jupiter is absent.

- [ ] **Step 6.2: Run 30-run baseline on main**

On a clean checkout of `main` (without Phase 6 code):

```bash
git stash  # if any uncommitted changes
git checkout main
python run_flush_bot.py --runs 30 --label phase-5-baseline
git checkout -  # return to Phase 6 branch
git stash pop  # if stashed
```

Alternative: run this on the Phase 6 branch but explicitly disable the new paths by temporarily reverting `select_shop_action`, `select_booster_action`, `use_or_sell_consumables`. **Prefer the branch-switch approach** — simpler and can't accidentally benchmark against the wrong code.

- [ ] **Step 6.3: Run 30-run Phase 6 benchmark**

```bash
python run_flush_bot.py --runs 30 --label phase-6-boosters
```

- [ ] **Step 6.4: Analyse and compare**

Run:
```bash
python -c "
from balatrobot.utils.run_history import load_history, runs_for_label
h = load_history()
for label in ('phase-5-baseline', 'phase-6-boosters'):
    runs = runs_for_label(h, label)
    n = len(runs)
    ante_3_plus = sum(1 for r in runs if r.get('ante_reached', 0) >= 3)
    ante_2_plus = sum(1 for r in runs if r.get('ante_reached', 0) >= 2)
    avg_ante = sum(r.get('ante_reached', 0) for r in runs) / n if n else 0
    print(f'{label}: n={n}  ante>=3: {ante_3_plus}/{n} ({100*ante_3_plus/n:.0f}%)  ante>=2: {ante_2_plus}/{n} ({100*ante_2_plus/n:.0f}%)  avg ante: {avg_ante:.2f}')
"
```

Expected: two lines comparing the two labels. Target: `phase-6-boosters` ante>=3 rate ≥ 30% relative improvement over `phase-5-baseline` (e.g., if baseline is 10%, Phase 6 should be ≥ 13%).

- [ ] **Step 6.5: Write the phase record**

Create `docs/superpowers/records/phase-6-booster-packs.md` with the standard structure (matching `docs/superpowers/records/phase-4-run-analytics.md`):

```markdown
# Phase 6: Booster Pack & Planet Consumable Use — Implementation Record

**Date:** 2026-04-22 / <completion date>
**Branch:** <branch name>
**Follows:** Phase 5 (documentation site)
**Precedes:** TBD

---

## Overview

Phase 4 analytics showed 74% of runs died at ante 2, with most losses
scoring 94-99% of the chip requirement and discards unused. FlushBot
was skipping every booster pack and never using consumables — leaving
the specific numerical boost needed (Jupiter → Flush level) on the table.

Phase 6 plugs this leak: buy Celestial and Buffoon packs, pick Jupiter
from Celestial, flush-synergy jokers from Buffoon, use Planet consumables
immediately.

---

## Scope

| Item | Independent? |
|---|---|
| 6a. Planet catalogue annotation | Yes |
| 6b. Shop: buy Celestial & Buffoon packs | Depends on 6a |
| 6c. Pack open + Planet consumable use | Depends on 6a, 6b |

---

## What Was Planned

<paste design summary from spec>

---

## What Was Built

<brief notes on each sub-task and any deviations from the spec>

---

## Bugs Found During Implementation

<any bugs encountered; if none, write "None documented.">

---

## Performance Results (30-run A/B)

<paste the output from step 6.4>

| Metric | Baseline (phase-5) | Phase 6 | Delta |
|---|---|---|---|
| ante >= 2 | XX% | XX% | +XX pp |
| ante >= 3 | XX% | XX% | +XX pp |
| avg ante | X.XX | X.XX | +X.XX |

<Commentary — was the ≥30% relative improvement target hit?>

---

## Current State Per Sub-Task

| Sub-task | Status | Notes |
|---|---|---|
| 6a. Planet catalogue | ✅ Done | 12 planets annotated, PlanetData, planet_for_hand |
| 6b. Shop pack buying | ✅ Done | Celestial + Buffoon; priority unchanged for jokers |
| 6c. Pack open + consumable use | ✅ Done | Jupiter-first, use-immediately policy |

---

## What Is Explicitly Out of Scope

- Arcana / Spectral / Standard pack handling
- Shop rerolls
- Voucher purchasing
- Non-Planet consumable use
- Annotating the remaining 128 jokers
- Non-Flush hand strategies

---

## Deferred Items

**Stuck-loop self-termination (Python `Bot.run_step`)**
The bot can spin indefinitely on `Action invalid` responses without ever firing the `stuck_timeout` abort. In `_recv_gamestate`, an error response returns `G is None` and `run_step` exits early, **before** the `stuck_timeout` check runs. So when Lua reports `waitingFor='select_booster_action'` in a state where SKIP_BOOSTER_PACK is invalid (e.g. inter-run transition), Python sends → Lua errors → Python reads error → repeats forever. Observed during 6e: bot spammed thousands of "Error: Action invalid for action 11" until Balatro crashed.

Fix sketch: in `run_step`, treat consecutive `G is None` responses as no-progress for stuck-detection purposes — increment a counter and abort once it crosses the same threshold. Two-line change in `bot.py`. Worth its own phase or sub-task because it's defence-in-depth (the underlying state-leak should also be fixed) and changes failure semantics for any future stuck condition, not just boosters.

<anything else discovered during implementation that should be a future phase>
```

Fill in the placeholder sections with actual data from the run.

- [ ] **Step 6.6: Update PLAN.md**

Open `docs/PLAN.md`. Replace the "Phase 6 — RL Groundwork" section with a completed Phase 6 block mirroring the Phase 5 format:

```markdown
## Phase 6 — Booster Pack & Planet Consumable Use ✅

**Goal:** Make FlushBot buy Celestial and Buffoon packs, pick Jupiter from Celestial to level Flush, use Planets immediately. Targets the 94-99% chip near-misses at ante 2.

- [x] Planet catalogue annotation (hand_type, softlock)
- [x] Shop: buy Celestial & Buffoon packs when affordable
- [x] Pack open handler: Jupiter-first, flush-joker-only Buffoon
- [x] Consumable use: Planets immediately, Jupiter preferred
- [x] A/B benchmark: 30-vs-30 runs, target ≥30% relative ante-2+ lift

Spec: `docs/superpowers/specs/2026-04-22-phase-6-booster-pack-consumable-use-design.md`
Record: `docs/superpowers/records/phase-6-booster-packs.md`

---

## Phase 7 — RL Groundwork (deferred)

<paste the existing Phase 6 RL content here, renumbered as Phase 7>
```

- [ ] **Step 6.7: Commit**

```bash
git add docs/superpowers/records/phase-6-booster-packs.md docs/PLAN.md
git commit -m "docs: add Phase 6 record, update roadmap

30-run A/B shows <result>. Phase 6 complete; RL groundwork pushed to Phase 7."
```

---

## Self-Review Checklist (for plan author)

- [x] Spec coverage: 6a (Task 1), 6b (Task 2), 6c (Tasks 3+4+5), success criterion (Task 6).
- [x] No placeholders. All code is inline. All commands are exact.
- [x] Type consistency: `PlanetData` in Task 1 is referenced consistently in Task 2 (via `_is_planet_key`), Task 4, and Task 5. `_card_key` and `_is_planet_key` helpers both defined once (Task 2, step 2.3), reused in Tasks 4 and 5. `Actions.BUY_BOOSTER` exists in `balatrobot/core/bot.py:45` (verified during plan writing — no enum change needed).
- [x] Dependencies are explicit: Task 2 depends on Task 1; Task 3 depends on Task 2 live; Task 4 depends on Task 3; Task 5 depends on Task 4 (for the `_card_key` helper); Task 6 depends on all.
