# Phase 7a — Flush Bot Mechanics Polish

**Date:** 2026-05-03  
**Follows:** Phase 6 (Booster Pack & Planet Consumable Use)  
**Precedes:** Phase 7b (Gym Environment)

## Context

The flush bot (Phase 6) reaches Ante 2–3 on average and occasionally Ante 4. The next
step toward a machine learning layer is to raise the heuristic baseline and close the
most impactful mechanical gaps before training begins. This phase implements four
targeted improvements to `flush_bot.py`, all of which feed into a higher average ante
and a stronger benchmark for future RL comparison.

Two follow-on phases have been scoped and deferred:
- **Phase 7b — Gym Environment**: Build `BalatroEnv(gym.Env)` wrapping the existing
  `GamestateEncoder`, validated with a random agent. No training yet.
- **Phase 7c — Game Simulator**: Lightweight simulator so training episodes do not
  require a live Balatro instance. Significantly faster RL iteration.

The eventual ML target is a **flush-specialist RL agent** (PPO via Stable Baselines3)
that can generalise to other hand types over time. The 300-dim observation space in
`balatrobot/features/` was designed with this in mind.

---

## Scope

| Mechanic | File | Change |
|---|---|---|
| Shop reroll | `flush_bot.py:select_shop_action` | Reroll when dollars ≥ 25 and cost won't drop below $20 |
| Buffoon pack upgrade | `flush_bot.py:select_booster_action` | Pick highest flush-synergy joker; only take if free slot |
| Joker selling | `flush_bot.py:sell_jokers` | Remove proactive sell — becomes no-op |
| Blind tag skip | `flush_bot.py:skip_or_select_blind` | Skip blind when offered tag is in SKIP_TAGS |

Vouchers are out of scope for this phase (no synergy data in catalogue yet).

---

## Architecture

All changes are confined to `balatrobot/bots/flush_bot.py`. No new files required.
Catalogue data (`flush_synergy`) is already present on all jokers.

### 1. `select_shop_action` — reroll

After all buy priorities are exhausted and before returning `END_SHOP`:

```python
reroll_cost = G.get("reroll_cost", 5)   # verify field name in gamestate
if dollars >= 25 and dollars - reroll_cost >= 20:
    return [Actions.REROLL_SHOP]
return [Actions.END_SHOP]
```

**First implementation step:** confirm the reroll cost field name in `G` (check
`Utils.getGamestate()` in `src/utils.lua` or run with `cache_states=True`).

### 2. `select_shop_action` — sell-to-upgrade (shop jokers)

When a flush joker is found in the shop but joker slots are full:
- Look up the shop joker's `flush_synergy` from the catalogue
- Look up the weakest held joker's `flush_synergy`
- If the shop joker is strictly better, sell the weakest held joker first, then buy

**First implementation step:** confirm `SELL_JOKER` is valid during `SHOP` state
(check `ACTIONPARAMS` in `src/bot.lua`). If not valid in SHOP state, this
sub-feature is deferred to Phase 7b.

### 3. `select_booster_action` — Buffoon pack

Replace current logic (first joker in `FLUSH_JOKERS` priority list) with: pick the
highest flush-synergy joker in the pack, but only take it if a joker slot is free.
Skip the pack if slots are full or no joker in the pack has synergy > 0.

Max joker slots: confirm from `G` (likely `G["joker_slots"]` — verify field name).

### 4. `sell_jokers` — no-op

```python
def sell_jokers(self, G):
    return [Actions.SELL_JOKER, []]
```

### 5. `skip_or_select_blind` — tag skip

Read the offered tag key from `G` (verify field name) and compare against
`self.SKIP_TAGS`. Return `SKIP_BLIND` on a match, `SELECT_BLIND` otherwise.

**First implementation step:** confirm how the offered tag key is exposed in `G`
(check `Utils.getGamestate()` in `src/utils.lua`).

---

## Protocol Verification Steps (do first)

Before writing any implementation code, confirm four things from the Lua source:

1. **Reroll cost field**: What key holds the current reroll cost in `G`?
2. **Joker slot count**: What key holds max joker slots in `G`?
3. **Offered blind tag**: How is the tag currently on offer for skipping exposed in `G`?
4. **SELL_JOKER in SHOP**: Is `SELL_JOKER` valid during `G.STATE == SHOP`?

Check `src/utils.lua` (`Utils.getGamestate()`) and `src/bot.lua` (`ACTIONPARAMS`).

---

## Testing

All tests in `tests/test_flush_bot.py` using cached or synthetic gamestates.

| Test | Gamestate | Assertion |
|---|---|---|
| Reroll when dollars ≥ 25 and cost safe | SHOP, dollars=25, reroll_cost=5, no flush joker | Returns `REROLL_SHOP` |
| No reroll when would drop below $20 | SHOP, dollars=23, reroll_cost=5 | Returns `END_SHOP` |
| No reroll when dollars < 25 | SHOP, dollars=20 | Returns `END_SHOP` |
| Buffoon pack picks highest synergy | BUFFOON_PACK, 2 jokers with different synergy, free slot | Returns higher-synergy joker index |
| Buffoon pack skips when full | BUFFOON_PACK, joker slots full | Returns `SKIP_BOOSTER_PACK` |
| sell_jokers is no-op | Any, 3 jokers held | Returns `[]` |
| Blind skip on matching tag | BLIND_SELECT, offered tag in SKIP_TAGS | Returns `SKIP_BLIND` |
| Blind select on non-matching tag | BLIND_SELECT, offered tag not in SKIP_TAGS | Returns `SELECT_BLIND` |

Gamestates for SHOP and BUFFOON_PACK states must be captured with a fresh
`cache_states=True` run if not already present in `gamestate_cache/`.
Blind tag gamestates may need synthetic fixtures depending on what `G` exposes.

---

## Verification

1. Run `pytest tests/test_flush_bot.py` — all new tests pass
2. Run `python run_flush_bot.py --runs 10`
3. Confirm `run_history.json` has 10 new entries with non-zero scores and no freezes
4. Compare average ante to Phase 6 baseline (avg 2.1, Ante 3+ at 16.1%)
5. Run `ruff check --fix balatrobot/ tests/` and `mypy balatrobot/`

**PASS criteria:** Tests green, average ante ≥ 2.5 across 10 runs, no freeze/crash  
**FAIL criteria:** Any freeze, test failure, or average ante below Phase 6 baseline
