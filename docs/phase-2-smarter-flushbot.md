# Phase 2: Smarter FlushBot — Implementation Record

**Date:** 2026-04 (retrospective — predates superpowers adoption)
**Follows:** Phase 1 (run persistence layer)
**Precedes:** Phase 3 (game mechanics catalogue)

---

## Overview

Phase 1 established run persistence. Phase 2 makes FlushBot decisions informed by actual game state rather than blind heuristics. The scope was deliberately narrow: play/discard logic, shop strategy, and blind skipping. Complex mechanics (economy, rerolling, comprehensive joker tiers) were deferred.

---

## Scope

| Item | Independent? |
|---|---|
| 2a. Play/discard decisions | Yes |
| 2b. Shop strategy | Yes |
| 2c. Blind skipping | Yes |

All three items are independent. 2c was partially reverted due to a Lua crash (see Bugs).

---

## What Was Planned

### 2a. Play/Discard Decisions

- Calculate expected chips for the best available hand using `handscores` + card values
- Compare against `chips_needed - current_chips` to decide whether to play or fish for a better hand
- Respect `hands_left`: if on last hand, always play
- Only discard when `discards_left > 0` AND expected best hand is below chip target with hands remaining

### 2b. Shop Strategy

- Priority list of flush-synergy joker keys: `j_4_fingers`, `j_flush`, `j_runner`, `j_shortcut`, `j_fibonacci`
- Buy highest-priority joker that is affordable and in stock
- Skip shop if no priority jokers available — no rerolling

### 2c. Blind Skipping

- Skip Small/Big blinds when a useful tag is on offer (`tag_double`, `tag_economy`, `tag_voucher`, `tag_coupon`)
- Always select Boss blind (can't skip)

---

## What Was Built

### Lua: `src/utils.lua`

Added `current_chips` to `Utils.getGameData()`:
```lua
_game.current_chips = G.GAME.chips or 0
```
`G.GAME.chips` turned out to be the wrong field — always 0 during `SELECTING_HAND`. The correct field is unknown without deeper Balatro source inspection. Deferred.

### Python: `balatrobot/bots/flush_bot.py`

**New constants:**
```python
FLUSH_JOKERS = ["j_4_fingers", "j_flush", "j_runner", "j_shortcut", "j_fibonacci"]
SKIP_TAGS = {"tag_double", "tag_economy", "tag_voucher", "tag_coupon"}
CARD_CHIPS = {"2": 2, ..., "Jack": 10, "Queen": 10, "King": 10, "Ace": 11}
```

**2b — `select_shop_action`:** Fully implemented. Scans shop cards in priority order, buys the first affordable match, ends shop otherwise. No rerolling.

**2a — `select_cards_from_hand`:** Implemented with a key simplification discovered during testing (see Bug #1). Final logic:
1. If 5+ cards of same suit → **always play the flush**
2. Else if discards remain and not last hand → **discard off-suit cards**
3. Else → **play forced hand** (best cards of most common suit)

`_should_play()` is retained as a utility but is no longer called by `select_cards_from_hand` (see Bug #1).

**2c — `skip_or_select_blind`:** Partially implemented, then reverted (see Bug #2). Always returns `SELECT_BLIND`.

### Deck Change

Switched from `"Blue Deck"` (standard 52-card) to `"Checkered Deck"` (26 Hearts + 26 Spades). Every card contributes to one of exactly two suits, maximising flush frequency.

**File changed:** `balatrobot/runners/recording.py`

---

## Bugs Found During Implementation

### Bug #1 — `_should_play` caused flush discards

**Symptom:** Bot discarding good flushes. Debug showed `should_play=False` for a flush scoring 272 chips against a 300 chip target.

**Root cause:** The score-vs-deficit check was applied to the flush play decision. The bot interpreted "my flush scores 272, I need 300, I should discard and try again." Wrong because chips accumulate across hands, `current_chips` was always 0 making deficit always equal to `chips_needed`, and discarding burns precious discards.

**Fix:** Remove `_should_play` from the flush play path. If we have a flush, always play it.

**Lesson:** The score check makes sense for deciding *whether to discard and fish*, not *whether to play our best available hand*.

---

### Bug #2 — `skip_or_select_blind` used wrong tag field (Lua crash)

**Symptom:** Game crashed mid-run with `WinError 10054` (UDP port unreachable — Balatro process died).

**Root cause:** `G["tags"]` holds tags the bot has **already collected**, not the tag **on offer** for skipping. When a collected tag matched `SKIP_TAGS`, the bot sent `SKIP_BLIND`. Lua middleware tried to click a UI element that was nil, crashing the game.

**Fix:** Reverted to always `SELECT_BLIND`. The correct fix requires exposing the offered tag in `Utils.getBlindData()`.

---

### Bug #3 — Duplicate card indices with Checkered Deck

**Symptom:** `Error: Action invalid for action 3` (PLAY_HAND) looping indefinitely.

**Root cause:** The Checkered Deck has two copies of each rank per suit. `hand.index(card)` uses dict value equality, producing duplicate indices for identical cards. Lua's `Utils.isTableUnique` rejects duplicate indices.

**Fix:** Replaced `hand.index()` with `enumerate(hand)` throughout — build `(index, card)` pairs from the start, never search by value.

---

### Bug #4 — Reconnect loop spins at full speed

**Symptom:** Hundreds of socket error messages per second when Balatro crashes.

**Root cause:** `_recv_gamestate` caught `OSError`, immediately reconnected with no delay, returned `None`. No exit condition when the Balatro process had died.

**Fix:** Added `time.sleep(1)` in the error handler and a `_balatro_alive()` check via `subprocess.Popen.poll()`.

---

### Bug #5 — Port conflict between simultaneous Balatro instances

**Symptom:** Background 20-run job failed immediately with `WinError 10054`.

**Root cause:** Previous interactive run left a Balatro instance on port 12345. New instance could not bind the same port.

**Fix (operational):** Always ensure no Balatro instance is running before starting a new bot session.

---

## Performance Results (20-run baseline, Checkered Deck, Stake 1)

| Ante reached | Count | % |
|---|---|---|
| 1 | ~50% | Dies on first blind |
| 2 | ~48% | Reaches Ante 2, fails Big/Boss |
| 4 | ~2% | Outlier (lucky joker purchase) |

Chip requirement jumps at Ante 2 and naked flushes can't reliably hit it. Joker acquisition is the critical unlock.

---

## Current State Per Sub-Task

| Sub-task | Status | Notes |
|---|---|---|
| **2a. Play/discard** | ✅ Done | Flush-first logic; `_should_play` scaffolded but not called |
| **2b. Shop strategy** | ✅ Done | Logic correct but priority list had wrong keys (fixed in Phase 3) |
| **2c. Blind skipping** | ❌ Deferred | Requires exposing offered tag in `getBlindData()` |
| **`current_chips`** | ❌ Deferred | `G.GAME.chips` is always 0; correct Lua field unknown |

---

## What Is Explicitly Out of Scope

- Economy management, rerolling, consumable use
- Comprehensive joker tier list (deferred to Phase 3 catalogue)
- Multi-instance benchmarking

---

## Deferred Items (carry into Phase 3)

1. **Offered skip tag in gamestate** — Add the tag on offer for skipping to `Utils.getBlindData()`. Then re-enable skip logic in `FlushBot.skip_or_select_blind`.
2. **`current_chips` correct Lua field** — Find the field tracking chips scored toward the current blind mid-round. Then wire `_should_play` back in.
3. **Joker priority list accuracy** — Phase 2 keys were invented without consulting the game source. Phase 3 extraction will replace them with correct keys.
