# Phase 6: Booster Pack & Planet Consumable Use — Design Spec

**Date:** 2026-04-22
**Branch:** TBD (likely `phase-6-boosters`)
**Follows:** Phase 5 (documentation site)
**Precedes:** TBD (RL groundwork deferred pending evaluation of this phase's impact)

---

## Motivation

147 recorded runs show FlushBot dies at ante 1 (23%) or ante 2 (74%). At ante 2, most losses finish at 94–99% of the chip requirement with discards still on the table:

| scored / needed | discards left | hand |
|---|---|---|
| 1156 / 1200 | 3 | Flush |
| 1168 / 1200 | 3 | Flush |
| 1196 / 1200 | 2 | Flush |
| 1176 / 1200 | 2 | Flush |

These are not strategic failures — they are missing numerical boost. Meanwhile FlushBot's `select_booster_action` always returns `SKIP_BOOSTER_PACK` and its `use_or_sell_consumables` is a no-op. The bot walks past two free sources of that exact boost:

- **Celestial packs** contain Planet cards. Jupiter levels Flush by +15 chips, +2 mult per level. Levelling Flush L1 → L2 trivially turns a 1156-chip flush into a winning hand.
- **Buffoon packs** give a free joker selection and appear independently of the shop's joker row.

Phase 6 plugs this specific leak without broadening strategy elsewhere.

---

## Scope

| Item | Independent? |
|---|---|
| 6a. Planet catalogue annotation (`planets.json` + `PlanetData` + catalogue lookup) | Yes |
| 6b. Shop: buy Celestial & Buffoon packs when affordable | Depends on 6a |
| 6c. Pack open + Planet consumable use (`select_booster_action`, `use_or_sell_consumables`) | Depends on 6a, 6b |

Explicitly **out of scope**: Arcana / Spectral / Standard packs, shop rerolls, voucher purchasing, non-Planet consumable use, strategic selling of consumables, annotating the remaining 128 jokers.

---

## Success Criterion

A/B comparison using the existing `--label` mechanism:

1. 30 runs on current `main` FlushBot, label `phase-5-baseline`.
2. 30 runs on the Phase 6 FlushBot, label `phase-6-boosters`.
3. Same deck (Checkered Deck), same stake (1). Seeds are random per run — sample size of 30 absorbs variance.

**Target:** ≥30% relative improvement in ante-2 win rate (currently ~26% reach ante 3+). Recorded in the phase record and surfaced via `analyse_runs --doc`.

Secondary signal (non-blocking): reduction in the "scored 94–99% of chips needed, died" cluster.

---

## Item 6a — Planet Catalogue Annotation

**Problem:** `balatrobot/data/planets.json` lists all 12 planet keys but has no `hand_type` field. Without it, the bot can't tell which planet levels Flush.

**Authoritative mapping** (from `../balatro_game_src/game.lua:557-568`):

| Key | Name | Hand type | Softlocked? |
|---|---|---|---|
| `c_mercury` | Mercury | Pair | no |
| `c_venus` | Venus | Three of a Kind | no |
| `c_earth` | Earth | Full House | no |
| `c_mars` | Mars | Four of a Kind | no |
| `c_jupiter` | Jupiter | **Flush** | no |
| `c_saturn` | Saturn | Straight | no |
| `c_uranus` | Uranus | Two Pair | no |
| `c_neptune` | Neptune | Straight Flush | no |
| `c_pluto` | Pluto | High Card | no |
| `c_planet_x` | Planet X | Five of a Kind | yes |
| `c_ceres` | Ceres | Flush House | yes |
| `c_eris` | Eris | Flush Five | yes |

**Changes:**
- `balatrobot/data/planets.json` — add `"hand_type": "..."` and `"softlock": bool` to every entry.
- `balatrobot/data/models.py` — add `PlanetData` dataclass with fields `key: str`, `name: str`, `base_cost: int`, `hand_type: str`, `softlock: bool`.
- `balatrobot/data/catalogue.py` — add `get_planet(key) -> PlanetData | None`, `all_planets() -> list[PlanetData]`, `planet_for_hand(hand_type) -> PlanetData | None`. Follow the existing `@cache` pattern used by `get_joker`.

**Test (`tests/test_planets_catalogue.py`):**
- Load catalogue, assert all 12 planets have `hand_type` and `softlock`.
- `planet_for_hand("Flush")` returns the Jupiter entry.
- `planet_for_hand("Nonexistent")` returns `None`.
- `get_planet("c_jupiter").hand_type == "Flush"`.

---

## Item 6b — Shop Extension

**Depends on:** 6a (for `get_planet` lookup, though the trigger only needs pack-key matching).

**Problem:** `FlushBot.select_shop_action` considers only `G["shop"]["cards"]` (joker/consumable row) and `END_SHOP`. It never looks at `G["shop"]["boosters"]`.

**Gamestate fields (already exposed, verified in `src/utils.lua:175-189`):**
- `G["shop"]["boosters"]` — list of `{key, name, cost}` dicts for each pack in the shop.

**Pack type detection:** A pack's type is inferable from its key prefix or `name` (e.g., `"Celestial Pack"`, `"Jumbo Celestial Pack"`, `"Mega Celestial Pack"`, `"Buffoon Pack"`, etc.). Implementation will match on `"Celestial"` and `"Buffoon"` substrings in the pack name.

**New priority order in `select_shop_action`:**
1. Flush-synergy joker in `shop.cards` (existing — unchanged).
2. Celestial pack in `shop.boosters`, affordable, AND no Planet already in `G["consumables"]`.
3. Buffoon pack in `shop.boosters`, affordable.
4. `END_SHOP`.

The "no Planet already in consumables" guard on Celestial purchase prevents a second pack buy before the first planet has been used and slot is freed — avoids the slot-full edge case.

**Action to send:** `[Actions.BUY_BOOSTER, [idx+1]]` where `idx` is the 0-based index into `shop.boosters`.

**Lua/Python infrastructure check:**
- `Bot.ACTIONS.BUY_BOOSTER` exists in `src/bot.lua` (verify during implementation) and is wired by middleware.
- `Actions.BUY_BOOSTER` may or may not exist in the Python `Actions` enum in `balatrobot/core/bot.py`. If absent, add it (match the Lua enum integer value).

**Test (`tests/test_flush_bot_boosters.py`, shop portion):**
- Mocked `G` with a flush joker in `shop.cards` + Celestial pack in `shop.boosters` → returns flush joker purchase (priority).
- Mocked `G` with no flush joker + affordable Celestial pack + empty consumables → returns `BUY_BOOSTER` for the Celestial pack.
- Mocked `G` with Celestial pack but consumables already contain a Planet → skips Celestial, buys Buffoon if present, else `END_SHOP`.
- Mocked `G` with unaffordable Celestial pack (`cost > dollars`) → does not buy it.
- Mocked `G` with only Arcana/Spectral packs → returns `END_SHOP`.

---

## Item 6c — Pack Open + Consumable Use

**Depends on:** 6a, 6b.

**Problem:** `FlushBot.select_booster_action` always returns `SKIP_BOOSTER_PACK`. `use_or_sell_consumables` is a no-op.

**Pack-open flow:** After `BUY_BOOSTER`, the game opens the pack and the bot enters `waitingForAction == "select_booster_action"`. The gamestate exposes `G["pack_cards"]` — a list of card dicts representing the options inside the opened pack.

### `select_booster_action(G)` policy

1. Read `G["pack_cards"]` (list of card dicts; each has `key` and other metadata).
2. Determine pack type by inspecting the first card's `key`:
   - If it starts with `c_` and is a known planet key → Celestial pack.
   - If it matches a known joker key (`j_...`) → Buffoon pack.
   - Otherwise (Arcana, Spectral, Standard) → this code path should not fire in Phase 6 because we never buy those packs. Defensive: return `SKIP_BOOSTER_PACK`.
3. **Celestial branch:**
   - If any card has `key == "c_jupiter"` → select that card.
   - Else → select the first card in `pack_cards`.
   - Return `[Actions.SELECT_BOOSTER_CARD, [card_idx+1], []]`. Third argument (hand cards) is empty because planets don't target hand cards.
4. **Buffoon branch:**
   - `FlushBot.FLUSH_JOKERS` is already sorted by descending `flush_synergy`. Iterate that list in order; return the first match found in `pack_cards`.
   - If no card in `pack_cards` matches any key in `FLUSH_JOKERS` → return `[Actions.SKIP_BOOSTER_PACK]` (avoid taking an unknown joker into a limited slot).

**Gamestate shape verification needed in implementation:** The exact keys on `pack_cards[i]` (specifically whether `key` is top-level or nested under `config.center`) must be checked against a live cached gamestate. Phase 6 implementation begins with running a single Balatro session, buying a Celestial pack, and caching the `select_booster_action` gamestate for reference.

### `use_or_sell_consumables(G)` policy

1. Read `G["consumables"]` (list of consumable dicts, `key` identifies each).
2. If any entry has a `key` matching a known planet key (`c_*`) → return `[Actions.USE_CONSUMABLE, [idx+1]]` for the first match (prefer `c_jupiter` if multiple planets are present).
3. Otherwise → return `[Actions.USE_CONSUMABLE, []]` (existing no-op behaviour).

No selling. No prioritising; no hoarding.

### Consumable slot management (implicit)

The "use immediately" policy means the bot's consumable inventory drains back to empty before the next shop. Combined with the "don't buy a second Celestial if one is already in consumables" rule from 6b, the slot-full case (inventory at capacity blocking acquisition) does not require explicit handling.

### Tests (`tests/test_flush_bot_boosters.py`, pack + consumable portions)

Mocked `G` fixtures, no live game required:
- `pack_cards` contains `c_jupiter` + 2 others → selects Jupiter.
- `pack_cards` contains planets without Jupiter → selects first planet (no skip).
- `pack_cards` contains Buffoon-pack jokers with one flush-synergy match → selects that joker.
- `pack_cards` contains Buffoon-pack jokers with no known match → skips.
- `consumables` contains `c_jupiter` → uses slot 1.
- `consumables` contains `c_mercury` + `c_jupiter` → uses the Jupiter slot (prefer Jupiter).
- `consumables` contains a Tarot only → returns the no-op use form.
- Empty `consumables` → returns the no-op use form.

### Live verification (manual)

One Balatro session with `cache_states=True`:
- Confirm Celestial pack purchase → open → Jupiter selection fires.
- Confirm `G.GAME.hands["Flush"].level` increments from 1 to 2 after use.
- Cache the `select_booster_action` gamestate and commit one sample to `gamestate_cache/` for future regression tests.

---

## Risks & Unknowns

- **`Actions.BUY_BOOSTER` missing in Python enum:** 2-line addition if absent.
- **`pack_cards[i]` shape:** `key` may be nested. Resolved during live verification at the start of 6c.
- **`G["consumables"]` shape:** Key path for planet identification unverified. Same resolution — check cached gamestate early in 6c.
- **Multiple packs opened per round:** If the bot buys both a Celestial and a Buffoon pack in the same shop, `select_booster_action` fires once per pack. Each call inspects `G["pack_cards"]` fresh; the design handles this naturally.
- **Regression risk:** Spending money on packs could leave the bot worse off if pack contents are poor and joker opportunities are missed. The A/B benchmark is the detector. Rollback plan: revert the three sub-tasks behind a single commit if Phase 6 bot performs worse than baseline.
- **Consumable-use timing:** Assumes `use_or_sell_consumables` hook fires often enough after pack opens for the planet to be used before the next blind. If it fires only between rounds, a planet bought mid-round sits unused until the round-end transition. Acceptable — the planet still levels up before the next hand in the subsequent round.

---

## Out of Scope (deferred)

- Arcana, Spectral, Standard pack handling — each requires its own policy (which cards to enhance, which spectrals to use, which regular cards to add to deck).
- Shop rerolls — economy management is a separate concern.
- Voucher purchasing — same.
- Annotating the remaining 128 jokers — tackled lazily when analytics reveal which ones matter.
- Non-Flush hand strategies — if Phase 6 shows levelling Flush alone doesn't break the ante-3 cliff, a subsequent phase may broaden hand evaluation.
- Selling consumables or jokers strategically — current `sell_jokers` is simplistic; out of scope to touch it.
