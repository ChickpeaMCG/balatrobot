# Architecture

Balatrobot is a two-part system: a **Lua mod** that runs inside Balatro (via Steamodded) and a **Python client** that drives bot logic externally over UDP.

## Communication Protocol

```
Python bot          Balatro mod (Lua)
    |   HELLO\n         |
    | ───────────────>  |   mod responds with full game state JSON
    |   {"state":...}   |
    | <───────────────  |
    |   PLAY_HAND|1,3   |
    | ───────────────>  |   mod executes action via UI hooks
```

Each game tick the Python client sends `HELLO\n` and receives a JSON gamestate snapshot. It then sends one action string. The mod parses the action, validates it against `Bot.ACTIONPARAMS`, and queues it for execution via Balatro's UI hooks.

Action format: `ACTION_NAME|arg1|arg2` where list args are comma-separated integers. Card indices are 1-based.

## Lua Mod (`main.lua` → `src/`)

| File | Responsibility |
|---|---|
| `src/utils.lua` | Gamestate serialisation (`Utils.getGamestate()`) and action validation |
| `src/bot.lua` | `Bot.ACTIONS` enum, `Bot.ACTIONPARAMS` validation rules, default Lua bot |
| `src/middleware.lua` | Hooks into Balatro's game loop; translates actions into UI clicks |
| `src/api.lua` | UDP socket server; receives commands, queues actions; speedup hooks |
| `src/botlogger.lua` | Action queue logging |

## Python Package (`balatrobot/`)

`balatrobot/core/bot.py:Bot` is an abstract base class. Subclass it and override decision methods (all receive `self` and `G` — the gamestate dict):

| Method | Returns |
|---|---|
| `skip_or_select_blind(G)` | `[Actions.SELECT_BLIND]` or `[Actions.SKIP_BLIND]` |
| `select_cards_from_hand(G)` | `[Actions.PLAY_HAND, [indices]]` or `[Actions.DISCARD_HAND, [indices]]` |
| `select_shop_action(G)` | `[Actions.END_SHOP]`, `[Actions.BUY_CARD, [idx]]`, etc. |
| `select_booster_action(G)` | `[Actions.SKIP_BOOSTER_PACK]` or `[Actions.SELECT_BOOSTER_CARD, ...]` |
| `sell_jokers(G)` | `[Actions.SELL_JOKER, [idx]]` or `[Actions.SKIP]` |

```
balatrobot/
├── core/bot.py          # Bot base class, State/Actions enums, socket loop
├── bots/
│   ├── flush_bot.py     # FlushBot — hunt flushes, catalogue-driven joker selection
│   ├── replay_bot.py    # ReplayBot — replay a saved .replay.json
│   └── example_bot.py  # Minimal bot skeleton
├── runners/
│   ├── recording.py     # RecordingFlushBot — saves run history + replays
│   └── benchmark.py     # Multi-instance parallel benchmarking
├── data/                # Typed catalogue: jokers, tarots, planets, spectrals, etc.
├── features/            # GamestateEncoder → 300-dim float32 observation vector
├── utils/               # run_history.py, gamestates.py
└── analytics/           # analyse_runs.py
```

## Gamestate (`G`)

The JSON gamestate includes: `hand`, `jokers`, `consumables`, `ante`, `shop`, `current_round`, `state`, `dollars`, `seed`, `waitingFor`, `waitingForAction`.

`state` is a `State` enum value (`SELECTING_HAND`, `SHOP`, `BLIND_SELECT`, `GAME_OVER`, etc.). `waitingFor` names the decision method the bot should call next.

## Configuration

`config.lua` — mod-level settings (port, speedup flags, frame skip ratio).  
`Bot.SETTINGS` in `src/bot.lua` — bot behaviour (`api = true` for Python-driven, `false` for Lua-native).
