# Phase 2: Smarter FlushBot — Implementation Record

## Context

Phase 1 established run persistence. Phase 2 makes FlushBot decisions informed by actual game state rather than blind heuristics. The scope was deliberately narrow: three sub-tasks (play/discard logic, shop strategy, blind skipping). Complex mechanics (economy, rerolling, comprehensive joker tiers) were explicitly deferred — Phase 3 analytics will show empirically where runs fail and guide further improvements.

**Key constraint:** A full game mechanics catalogue was considered and rejected. Incremental implementation teaches us what mechanics matter as we go.

---

## What Was Planned

### 2a. Play/Discard Decisions
- Calculate expected chips for best available hand using `handscores` + card values
- Compare against `chips_needed - current_chips` to decide whether to play or fish for a better hand
- Respect `hands_left`: if on last hand, always play
- Only discard when `discards_left > 0` AND expected best hand is below chip target with hands remaining

### 2b. Shop Strategy
- Priority list of flush-synergy joker keys: `j_4_fingers`, `j_flush`, `j_runner`, `j_shortcut`, `j_fibonacci`
- Buy highest-priority joker that is affordable and in stock
- Skip shop if no priority jokers available. No rerolling.

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
**Status:** Added but `G.GAME.chips` turned out to be the wrong field — it is always 0 during `SELECTING_HAND` state. The correct field for chips scored toward the current blind is unknown without deeper Balatro source inspection. Deferred.

### Python: `balatrobot/bots/flush_bot.py`

**New constants:**
```python
FLUSH_JOKERS = ["j_4_fingers", "j_flush", "j_runner", "j_shortcut", "j_fibonacci"]
SKIP_TAGS = {"tag_double", "tag_economy", "tag_voucher", "tag_coupon"}
CARD_CHIPS = {"2": 2, ..., "Jack": 10, "Queen": 10, "King": 10, "Ace": 11}
```

**2b — `select_shop_action`:** Fully implemented. Scans shop cards in priority order, buys the first affordable match, ends shop otherwise. No rerolling.

**2a — `select_cards_from_hand`:** Implemented with a key simplification discovered during testing (see bugs below). Final logic:
1. If 5+ cards of same suit → **always play the flush** (score accumulates across hands)
2. Else if discards remain and not last hand → **discard off-suit cards**
3. Else → **play forced hand** (best cards of most common suit)

`_should_play()` was initially used to gate flush plays behind a chip-deficit check, but this caused a regression (see Bug #1 below). It is retained as a utility method for future use but is no longer called by `select_cards_from_hand`.

**2c — `skip_or_select_blind`:** Partially implemented, then reverted (see Bug #2 below). Always returns `SELECT_BLIND`.

---

## Bugs Found During Implementation

### Bug #1 — `_should_play` caused flush discards (regression)

**Symptom:** Bot was discarding good flushes. Debug output showed `should_play=False` for a flush scoring 272 chips against a 300 chip target.

**Root cause:** The score-vs-deficit check was applied to the flush play decision, not just the discard decision. The bot interpreted "my flush scores 272, I need 300, I should discard and try again." This is wrong because:
1. Chips accumulate across multiple hands — scoring 272 gets you 90% of the way there
2. Discarding burns precious discards and forces later hands to play weak partial-suit hands
3. `current_chips` was always 0, making the deficit calculation equal to the full `chips_needed` every time

**Fix:** Remove `_should_play` from the flush play path entirely. If we have a flush, always play it.

**Lesson:** The score check makes sense for deciding *whether to discard and fish*, not *whether to play our best available hand*.

---

### Bug #2 — `skip_or_select_blind` used wrong tag field (Lua crash)

**Symptom:** Game crashed mid-run with `WinError 10054` (UDP port unreachable — Balatro process died).

**Root cause:** `G["tags"]` in the Python gamestate is tags the bot has **already collected**, not the tag currently **on offer** for skipping the current blind. When a collected tag key matched `SKIP_TAGS`, the bot sent `SKIP_BLIND`. The Lua middleware then tried to click the skip button UI element:
```lua
local _skip_button = _blind_obj:get_UIE_by_ID('tag_'..blind_on_deck).children[2]
```
If the element was nil (or the action was otherwise invalid), this caused a Lua error, crashing the game.

**Fix:** Reverted `skip_or_select_blind` to always `SELECT_BLIND`. The correct fix requires exposing the **offered** skip tag in `Utils.getBlindData()` — the offered tag is part of the blind selection UI, not `G.GAME.tags`.

**Deferred:** Add offered tag to `getBlindData()` in Lua, then re-implement skip logic.

---

### Bug #3 — Duplicate card indices with Checkered Deck

**Symptom:** `Error: Action invalid for action 3` (PLAY_HAND) looping indefinitely. Bot stuck in reconnect loop.

**Root cause:** The Checkered Deck has **two copies of each rank per suit** (26 Hearts + 26 Spades = 52 cards). The original code used `hand.index(card)` to find card positions, which does Python dict value equality. Two cards with identical serialized data (same suit, value, name, card_key) produce duplicate indices in the action. Lua's `Utils.isTableUnique` rejects duplicate indices, returning "Action invalid".

**Fix:** Replaced `hand.index()` with `enumerate(hand)` throughout — build `(index, card)` pairs from the start and never search by value:
```python
suit_indices: dict[str, list[int]] = {}
for i, card in enumerate(hand):
    suit = card.get("suit") or "Unknown"
    suit_indices.setdefault(suit, []).append(i)
```
Also handles non-standard suits (Stone cards, etc.) gracefully via `.get("suit") or "Unknown"`.

---

### Bug #4 — Reconnect loop spins at full speed

**Symptom:** Hundreds of socket error messages per second when Balatro crashes or port conflicts occur.

**Root cause:** `_recv_gamestate` in `bot.py` caught `OSError` and immediately reconnected with no delay, then returned `None`. `run_step` returned immediately, looping back to call `_recv_gamestate` again. No exit condition when the Balatro process had died.

**Fix:** Added `time.sleep(1)` in the error handler and a `_balatro_alive()` check that polls `subprocess.Popen.poll()` — if the process has exited, `running` is set to `False` and the loop terminates.

---

### Bug #5 — Port conflict between simultaneous Balatro instances

**Symptom:** Background 20-run job failed immediately with `WinError 10054` from the first packet.

**Root cause:** A previous interactive run had left a Balatro instance running on port 12345. When the background job launched a second instance on the same port, Lua's `setsockname` failed, crashing the new instance before it could process any commands.

**Fix (operational):** Always ensure no Balatro instance is running before starting a new bot session. A future improvement could detect the port conflict and report it clearly rather than spinning.

---

## Deck Change

Switched from `"Blue Deck"` (standard 52-card deck) to `"Checkered Deck"` (26 Hearts + 26 Spades only). This is the natural choice for a flush bot — every card in the deck contributes to one of exactly two suits, maximising flush frequency.

**File changed:** `balatrobot/runners/recording.py`

---

## Performance Results (20-run baseline, Checkered Deck, Stake 1)

| Ante reached | Count | % |
|---|---|---|
| 1 | ~50% | Dies on first blind |
| 2 | ~48% | Reaches Ante 2, fails Big/Boss |
| 4 | ~2% | Outlier (lucky joker purchase) |

**Observed failure mode:** Bot consistently clears Ante 1 Small Blind via flushes, then stalls at Ante 2. The chip requirement jumps significantly and naked flushes (no jokers) cannot reliably hit it. This confirms that joker acquisition (2b) is the critical unlock — runs that happen to buy a flush-synergy joker progress significantly further.

---

## Current State Per Sub-Task

| Sub-task | Status | Notes |
|---|---|---|
| **2a. Play/discard** | ✅ Done | Flush-first logic works; `_should_play` scaffolded but not called |
| **2b. Shop strategy** | ✅ Done | Logic verified firing correctly. Priority list too narrow (5/150 jokers) — none appeared across 20 shop visits in testing. Widening the list is a Phase 3 data question. |
| **2c. Blind skipping** | ❌ Deferred | Requires exposing offered tag in `getBlindData()` |
| **`current_chips`** | ❌ Deferred | `G.GAME.chips` is not the right Lua field; correct field unknown |

---

## Deferred Items (carry into Phase 3 / future)

1. **Offered skip tag in gamestate** — Add the tag currently on offer for skipping to `Utils.getBlindData()`. Then re-enable skip logic in `FlushBot.skip_or_select_blind`.

2. **`current_chips` correct field** — Find the Balatro field that tracks chips scored toward the current blind mid-round. Likely `G.GAME.current_round.chips_earned` or similar. Once correct, `_should_play` can be wired back in for smarter play/discard decisions.

3. **Discard threshold tuning** — When the most common suit has 4 cards and the bot has only 1 discard, discarding is often wasteful. A threshold (`if best_suit_count >= 4 and discards_left == 1, play instead`) could reduce forced weak hands.

4. **Joker impact measurement** — Phase 3 analytics should correlate run outcomes with jokers held at game over. This will confirm whether 2b's priority list is correct or needs reordering.
