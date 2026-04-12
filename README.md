# Balatrobot

A botting framework for [Balatro](https://store.steampowered.com/app/2379780/Balatro/) built on top of [Steamodded](https://github.com/Steamodded/smods). Write bots in Python that play Balatro autonomously.

> **This repo does not contain a finished bot — it provides the API and infrastructure to build one.**

---

## How It Works

The system has two halves that communicate over a local UDP socket:

```
┌─────────────────────────────┐         UDP          ┌──────────────────────┐
│  Balatro + Steamodded mod   │  ◄──── HELLO ──────  │   Python bot         │
│  (Lua, runs inside game)    │  ──── gamestate ───►  │   (your logic here)  │
│                             │  ◄──── ACTION ──────  │                      │
└─────────────────────────────┘                       └──────────────────────┘
```

1. **Lua mod** hooks into the game's update loop and intercepts game state transitions (selecting blinds, playing hands, shopping, etc.). At each decision point it pauses and waits for an action from the Python side.
2. **Python bot** sends `HELLO` each step, receives the full game state as JSON, decides on an action, and sends it back as a pipe-delimited string (e.g. `PLAY_HAND|1,3,5`).
3. The Lua mod validates and executes the action by simulating UI interactions (clicking buttons, selecting cards).

---

## Requirements

- [Balatro](https://store.steampowered.com/app/2379780/Balatro/) (Steam)
- [Lovely Injector](https://github.com/ethangreen-dev/lovely-injector) — drop `version.dll` into the Balatro game folder
- [Steamodded](https://github.com/Steamodded/smods) `1.0.0-beta` — place in `%AppData%\Roaming\Balatro\Mods\smods-1.0.0-beta\`
- Python 3.10+

---

## Installation

1. Clone this repo into your Balatro mods directory:
   ```
   cd %AppData%\Roaming\Balatro\Mods
   git clone <your-repo-url> balatrobot
   ```

2. Verify your mod folder structure:
   ```
   %AppData%\Roaming\Balatro\Mods\
   ├── lovely\              ← Lovely Injector logs (auto-created)
   ├── smods-1.0.0-beta\    ← Steamodded
   └── balatrobot\          ← this repo
       └── version.dll      ← NOT here — this goes in the game folder

   C:\Program Files (x86)\Steam\steamapps\common\Balatro\
   └── version.dll          ← Lovely Injector goes here
   ```

3. Launch Balatro via Steam. You should see the Steamodded mod list on startup with **Balatrobot** listed.

---

## Running the Example Bot

```bash
cd %AppData%\Roaming\Balatro\Mods\balatrobot
python run_flush_bot.py
```

This launches Balatro automatically, waits for it to load, then connects and starts playing. Press **Ctrl+C** to stop cleanly.

The included `FlushBot` always selects every blind, tries to build and play flushes, skips boosters, and ends the shop immediately.

---

## Writing Your Own Bot

Subclass `Bot` from `bot.py` and implement these methods. Each receives the current game state `G` (a dict) and returns an action list:

```python
from bot import Bot, Actions

class MyBot(Bot):
    def skip_or_select_blind(self, G):
        return [Actions.SELECT_BLIND]

    def select_cards_from_hand(self, G):
        # G["hand"] is a list of card dicts: {label, name, suit, value, card_key}
        # Card indices are 1-based
        return [Actions.PLAY_HAND, [1, 2, 3, 4, 5]]

    def select_shop_action(self, G):
        return [Actions.END_SHOP]

    def select_booster_action(self, G):
        return [Actions.SKIP_BOOSTER_PACK]

    def sell_jokers(self, G):
        return [Actions.SELL_JOKER, []]      # empty list = sell nothing

    def rearrange_jokers(self, G):
        return [Actions.REARRANGE_JOKERS, []]

    def use_or_sell_consumables(self, G):
        return [Actions.USE_CONSUMABLE, []]

    def rearrange_consumables(self, G):
        return [Actions.REARRANGE_CONSUMABLES, []]

    def rearrange_hand(self, G):
        return [Actions.REARRANGE_HAND, []]
```

Then run it:
```python
bot = MyBot(deck="Red Deck", stake=1, seed=None, bot_port=12345)
bot.start_balatro_instance()
time.sleep(15)
bot.run()
```

### Available Actions

| Action | Args | Description |
|--------|------|-------------|
| `SELECT_BLIND` | — | Select the current blind |
| `SKIP_BLIND` | — | Skip the current blind |
| `PLAY_HAND` | `[card_indices]` | Play selected cards (1-based) |
| `DISCARD_HAND` | `[card_indices]` | Discard selected cards (1-based) |
| `END_SHOP` | — | Leave the shop |
| `REROLL_SHOP` | — | Reroll shop (costs money) |
| `BUY_CARD` | `[idx]` | Buy joker at shop index (1-based) |
| `BUY_VOUCHER` | `[idx]` | Buy voucher at shop index |
| `BUY_BOOSTER` | `[idx]` | Buy booster pack at shop index |
| `SELECT_BOOSTER_CARD` | `[hand_idxs], [pack_idx]` | Pick a card from a booster pack |
| `SKIP_BOOSTER_PACK` | — | Skip the booster pack |
| `SELL_JOKER` | `[idx]` | Sell joker(s) by index |
| `REARRANGE_JOKERS` | `[new_order]` | Reorder jokers (full permutation) |
| `REARRANGE_HAND` | `[new_order]` | Reorder hand cards |
| `USE_CONSUMABLE` | `[idx]` | Use a consumable |
| `SELL_CONSUMABLE` | `[idx]` | Sell a consumable |

### Game State Schema

Each decision method receives `G`, a dict with (among others):

```python
G["state"]          # int — current game state (maps to bot.py State enum)
G["waitingFor"]     # str — which decision is being requested
G["dollars"]        # int — current money
G["round"]          # int — current round number
G["hand"]           # list of card dicts (see below)
G["jokers"]         # list of joker card dicts
G["consumables"]    # list of consumable card dicts
G["shop"]           # dict with keys: cards, boosters, vouchers, reroll_cost
G["ante"]           # dict with blinds.ondeck: "Small" | "Big" | "Boss"
G["current_round"]  # dict with discards_left, etc.

# Card dict shape:
# { "label": "base_card", "name": "3 of Hearts",
#   "suit": "Hearts", "value": 3, "card_key": "H_3" }
```

> **Note:** Several game state fields (`deck`, `handscores`, `tags`, `deckback`) are currently stubs returning empty data. See `src/utils.lua` to extend them.

---

## Configuration

`config.lua` controls mod-level behaviour:

```lua
BALATRO_BOT_CONFIG = {
    enabled = true,          -- set false to disable the mod entirely
    port = '12345',          -- UDP port (overridden by Balatro's arg[1])
    dt = 8.0/60.0,           -- simulated time per frame (speeds up game logic)
    uncap_fps = true,
    instant_move = true,     -- cards snap to position instead of sliding
    disable_vsync = true,
    frame_ratio = 100,       -- only render every Nth frame (100 = fast botting)
    disable_card_eval_status_text = true,
}
```

For **watching the bot play** at normal speed, use:
```lua
dt = false,
frame_ratio = 1,
```

For **fast headless botting**, restore the defaults above.

---

## Game State Logging

All game states are cached to disk automatically during a run:

```
gamestate_cache/
├── skip_or_select_blind/
│   └── 20260412123456789.json
├── select_cards_from_hand/
│   └── ...
└── ...
```

This is useful for understanding the state schema and building training datasets for ML/RL bots.

---

## Project Structure

```
balatrobot/
├── main.lua                  # Steamodded entry point — loads all Lua modules
├── config.lua                # Speed and port configuration
├── bot.py                    # Python Bot base class, Actions/State enums, protocol
├── flush_bot.py              # Example bot: plays flushes greedily
├── bot_example.py            # Minimal functional-style bot example
├── run_flush_bot.py          # Runner: launches game + starts FlushBot
├── gamestates.py             # Game state cache (writes JSON snapshots to disk)
├── src/
│   ├── api.lua               # UDP socket server + game speedup hooks
│   ├── middleware.lua        # Hooks Balatro UI; translates actions into button clicks
│   ├── bot.lua               # Lua bot: action definitions, validation rules, default logic
│   ├── botlogger.lua         # Action queue (feeds API commands into bot decision points)
│   └── utils.lua             # Game state serialisation, action parsing/validation
└── lib/
    ├── sock.lua              # LuaSocket UDP wrapper
    ├── json.lua              # JSON encode/decode
    ├── hook.lua              # Function hooking (callbacks, breakpoints, onwrite)
    ├── list.lua              # Doubly-linked list
    └── bitser.lua            # Binary serialisation (unused by API path)
```

---

## Architecture Notes

- **Action flow (API mode):** Python → UDP → `api.lua` receives action → pushed to `Botlogger` queue → `middleware.lua` `firewhenready` pops queue → UI interaction queued as Love2D Event → game progresses → next decision point → breakpoint fires → Python notified.
- **`Hook` library** (`lib/hook.lua`) wraps functions and tables with callbacks, breakpoints (pre-call interceptors), and onwrite listeners. Used pervasively to intercept Balatro's internal game loop without modifying game source files.
- **Saving is disabled** while the bot runs — the game's save manager is stubbed out in `middleware.lua`.

---

## Known Limitations

- `use_or_sell_consumables` action execution is not yet implemented in `middleware.lua`
- Several game state fields are stubs: `deck`, `handscores`, `tags`, `deckback`
- Tested against Steamodded `1.0.0-beta-1606b`; earlier versions used a different mod loading API
