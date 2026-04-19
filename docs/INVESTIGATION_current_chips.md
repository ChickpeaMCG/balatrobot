# Investigation: `current_chips` Lua Field

## What We're Trying To Do

In `src/utils.lua:Utils.getGameData()`, the line:
```lua
_game.current_chips = G.GAME.chips or 0
```
always returns 0. We need the field that reflects chips accumulated toward the current blind during a round.

## What We Found

### The correct field IS `G.GAME.chips`

From `balatro_game_src/game.lua:1917`, `G.GAME.chips` is initialized to `0` at game start.

From `balatro_game_src/functions/state_events.lua:1049`, after each hand is scored:
```lua
G.E_MANAGER:add_event(Event({
    trigger = 'ease',
    blocking = false,
    ref_table = G.GAME,
    ref_value = 'chips',
    ease_to = G.GAME.chips + math.floor(hand_chips*mult),
    delay = 0.5,
    func = (function(t) return math.floor(t) end)
}))
```

From `balatro_game_src/functions/button_callbacks.lua:2948`, at round end:
```lua
ease_chips(0)  -- resets G.GAME.chips to 0
```

The game's own blind-defeat check at `state_events.lua:96` and `:1139`:
```lua
if G.GAME.chips - G.GAME.blind.chips >= 0 then
    -- blind beaten
end
```

So `G.GAME.chips` is the right field. The game itself uses it.

### Why It's Always 0

The update is an **ease event with `blocking = false` and delay `0.5`**. With our bot speed settings (`dt = 8/60`, uncapped FPS, `frame_ratio = 100`), the game runs extremely fast. The `SELECTING_HAND` state is re-entered before the 0.5s ease completes, so we always read the mid-animation value (which starts at the previous value, typically 0 after the round reset).

Confirmed via live debug logging — `G.GAME.chips`, `current_hand.chip_total`, and `current_hand.chips` are all `0` throughout an entire run (13 hands played, Ante 2 reached).

### Other Fields Ruled Out

From the live debug log, `G.GAME.current_round` only contains these scalar fields:
- `reroll_cost_increase`, `jokers_purchased`, `reroll_cost`, `discards_left`, `discards_used`
- `hands_played`, `dollars`, `round_dollars`, `cards_flipped`, `most_played_poker_hand`
- `dollars_to_be_earned`, `round_text`, `free_rerolls`, `hands_left`

None of these track accumulated chips.

`G.GAME.current_round.current_hand` contains `chips`, `mult`, `chip_total` — but these are the display values for the CURRENT hand being scored, not the accumulated total. They're also always 0 at `SELECTING_HAND` time.

## Proposed Fix

**Option A (Recommended): Track chips synchronously in the mod**

Add a variable `BalatrobotAPI.chips_total = 0` in the mod and hook into the hand scoring event to update it synchronously (before the ease). Reset at blind start.

In `src/utils.lua`, read this tracked value instead of `G.GAME.chips`.

**Option B: Read `G.GAME.chips` after the ease with a Lua hook**

Hook into a late event in the hand-scoring sequence (after the 0.5s ease completes) and cache the value. Read the cached value in `getGameData()`.

**Option C: Defer entirely**

Since the bot currently has no jokers (never buys any), blind chip requirements are never going to be met mid-round — the bot always uses all hands. `_should_play` would only ever fire when `current_chips >= chips_needed`, which in practice means "the blind is about to be won." For the current bot this is rare enough that deferring this feature has minimal impact.

## Balatro Source Files

The full Balatro Lua source is extracted to:
```
C:\Users\Vince\Desktop\sandbox\balatro_game_src\
```

Key files:
- `game.lua` — game state initialization
- `functions/state_events.lua` — hand scoring, chip accumulation, state transitions
- `functions/button_callbacks.lua` — `ease_chips()` definition, round-end chip reset
- `functions/common_events.lua` — `update_hand_text`, scoring display logic
- `functions/misc_functions.lua` — ambient audio, score intensity tracking

## Next Steps for New Session

1. Decide between Option A, B, or C above
2. If Option A: implement a synchronous chip tracker in `src/api.lua` or `src/middleware.lua`
3. If Option C: skip `current_chips` fix for now and implement Tasks 3, 4, 5 from the plan independently (they don't depend on it)
4. Revert the debug logging in `src/utils.lua` (currently has `sendDebugMessage` calls in `Utils.getGameData()`)

## Debug Logging to Revert

`src/utils.lua` currently has temporary debug logging in `Utils.getGameData()` (around lines 212-218). It must be reverted before committing. Replace with:
```lua
_game.current_chips = G.GAME.chips or 0
```
