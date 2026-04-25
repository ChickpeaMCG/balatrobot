# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Balatro Game Source

The full Balatro Lua source (extracted from `Balatro.exe`) is at:
```
../balatro_game_src/
```
Use this when investigating game internals — no need to re-extract from the .exe.

Steamodded debug logs go to: `%AppData%\Roaming\Balatro\Mods\lovely\log\` (most recent file).

### Source navigation

All paths relative to `../balatro_game_src/`.

**Top-level files**

| File | Purpose |
|---|---|
| `globals.lua` | `G.STATES` enum (284–304), `G.STAGES`, screen constants, instance registries |
| `game.lua` | `Game` class — init, `init_item_prototypes` (all joker/consumable/voucher prototypes in `P_CENTERS` at line 364), `init_game_object` (full `G.GAME` schema at line 1862), main `update` dispatcher (2449) |
| `card.lua` | `Card` class — every joker/consumable/playing card behavior; `Card:use_consumeable` (1091), `Card:calculate_joker` scoring triggers (2291), `Card:open` booster pack (1681) |
| `cardarea.lua` | `CardArea` — hand/deck/jokers/shop containers; `can_highlight`, `add_to_highlighted`, `parse_highlighted` (113–201) |
| `blind.lua` | `Blind` class — `set_blind` (78), `defeat`/`disable` (276, 356), boss hooks `press_play`/`debuff_card`/`modify_hand` (464+) |

**`functions/` files**

| File | Key locations |
|---|---|
| `state_events.lua` | `end_round` (87), `new_round` (290), `draw_from_deck_to_hand` (355), `discard_cards_from_highlighted` (379), `play_cards_from_highlighted` (450), `get_poker_hand_info` priority order (540), `evaluate_play` scoring pipeline (571), `evaluate_round` (1135) |
| `button_callbacks.lua` | Gate predicates: `can_buy`/`can_buy_and_use`/`can_use_consumeable`/`can_skip_booster` (55–124, 2076–2155). Action handlers: **`G.FUNCS.use_card`** (2155), `sell_card` (2318), `buy_from_shop` (2404), `select_blind` (2513), `skip_booster` (2558), `skip_blind` (2740), `cash_out` ROUND_EVAL→SHOP (2912) |
| `common_events.lua` | `G.UIDEF.use_and_sell_buttons` (239), per-card button factory `card_focus_button` (299–382), `G.UIDEF.shop` layout (637), pack UIBox definitions `create_UIBox_*_pack` (1629–1813), `get_pack` opens booster contents (1944), `create_card` universal card spawner (2082), `calculate_reroll_cost` (2263) |
| `misc_functions.lua` | `evaluate_poker_hand` + helpers `get_flush`/`get_straight`/`get_X_same` (376–613), deterministic RNG `pseudoseed`/`pseudorandom` (279–315), `get_blind_amount(ante)` chip formula (919) |

**Key global state**

| Variable | Contains |
|---|---|
| `G.STATE` | Current state enum value (compare to `G.STATES.*`) |
| `G.GAME` | Full run state: `dollars`, `current_round`, `hands` (chips/mult/level per hand type), `shop`, `blind`, `round_resets` |
| `G.GAME.hands` | Per-hand-type table — `level`, `chips`, `mult` (initialized at `game.lua:2001`) |
| `G.hand` / `G.play` / `G.deck` / `G.discard` | Card areas (CardArea instances) |
| `G.jokers` / `G.consumeables` | Joker and consumable slots |
| `G.shop_jokers` / `G.shop_booster` / `G.shop_vouchers` | Shop card areas |
| `G.pack_cards` | Cards inside an open booster pack |
| `G.CONTROLLER.locks` | Non-nil entries block input during animations |

**`G.STATES` values** (from `globals.lua:284`)

```
SELECTING_HAND=1  HAND_PLAYED=2    DRAW_TO_HAND=3   GAME_OVER=4
SHOP=5            PLAY_TAROT=6     BLIND_SELECT=7   ROUND_EVAL=8
TAROT_PACK=9      PLANET_PACK=10   BUFFOON_PACK=18  STANDARD_PACK=17
NEW_ROUND=19      SMODS_BOOSTER_OPENED=999  (Steamodded — Jumbo/Mega packs)
```

**Bot action entry points:** every bot action maps to a `G.FUNCS.*` callback in `button_callbacks.lua` — the same function the UI button calls. Most are guarded by a sibling `can_*` predicate. When debugging a stuck action, check the predicate first.

**Planet → hand type mapping:** `game.lua:557–568`.

## Project Overview

Balatrobot is a two-part system: a **Lua mod** that runs inside Balatro (via Steamodded) and a **Python client** that drives bot logic externally. They communicate over UDP sockets.

The mod does **not** contain a finished bot — it exposes an API. Bot logic lives in `src/bot.lua` (Lua-native) or in Python clients that subclass `balatrobot/core/bot.py:Bot`.

## Running a Bot

**Python client (recommended for new bots):**
```bash
python run_flush_bot.py          # runs the recording flush bot (saves history + replays)
python replay_bot.py <file>      # replays a saved .replay.json file
```

**Lua-native bot:** Edit `src/bot.lua` directly with `Bot.SETTINGS.api = false` in `Bot.SETTINGS`.

**Multi-instance benchmarking:** `balatrobot/runners/benchmark.py` contains `benchmark_multi_instance()` for running multiple Balatro instances in parallel (ports start at 12348+i).

## Configuration

`config.lua` controls mod-level settings:
- `enabled` — set to `false` to disable entirely
- `port` — default UDP port (overridden by Balatro's `arg[1]`)
- `dt`, `uncap_fps`, `instant_move`, `disable_vsync`, `frame_ratio` — speedup settings for botting (frame_ratio=100 skips rendering most frames)

`Bot.SETTINGS` in `src/bot.lua` controls bot behavior including `api = true/false` to switch between Python-driven vs Lua-native mode.

## Architecture

### Communication Protocol
- Balatro mod listens on a UDP port; Python client connects to it
- Python sends `HELLO\n` each step → Lua responds with JSON gamestate
- Python sends action strings like `PLAY_HAND|1,3,4,5` → Lua executes them
- Action format: `ACTION_NAME|arg1|arg2` where list args are comma-separated integers

### Lua Mod (`main.lua` → `src/`)
- `src/utils.lua` — gamestate serialization (`Utils.getGamestate()`) and action parsing/validation
- `src/bot.lua` — bot action definitions, `Bot.ACTIONS` enum, `Bot.ACTIONPARAMS` validation rules, and default Lua bot implementations
- `src/middleware.lua` — hooks into Balatro's game loop via `Hook.*`; translates bot decisions into UI interactions (clicking buttons, selecting cards); implements the `firewhenready` pattern for async conditions
- `src/api.lua` — UDP socket server; receives commands, calls `BalatrobotAPI.queueaction()`; also sets up speedup hooks (dt override, fps uncap, instant moves)
- `src/botlogger.lua` — action queue logging

### Python Package (`balatrobot/`)
`balatrobot/core/bot.py:Bot` is an abstract base class. Subclass it and override these methods (all receive `self` and `G` gamestate dict):
- `skip_or_select_blind(G)` → `[Actions.SELECT_BLIND]` or `[Actions.SKIP_BLIND]`
- `select_cards_from_hand(G)` → `[Actions.PLAY_HAND, [card_indices]]` or `[Actions.DISCARD_HAND, [card_indices]]`
- `select_shop_action(G)` → `[Actions.END_SHOP]`, `[Actions.BUY_CARD, [idx]]`, etc.
- `select_booster_action(G)` → `[Actions.SKIP_BOOSTER_PACK]` or `[Actions.SELECT_BOOSTER_CARD, [hand_idxs], [pack_idx]]`
- `sell_jokers(G)`, `rearrange_jokers(G)`, `use_or_sell_consumables(G)`, `rearrange_consumables(G)`, `rearrange_hand(G)`

Card indices are **1-based**. The gamestate `G` dict includes: `hand`, `jokers`, `consumables`, `ante`, `shop`, `current_round`, `state`, `dollars`, `waitingFor`, `waitingForAction`.

### Package Layout
```
balatrobot/
├── core/bot.py          # Bot base class, State/Actions enums, socket loop
├── bots/
│   ├── flush_bot.py     # FlushBot strategy (hunt flushes, skip shop)
│   ├── replay_bot.py    # ReplayBot — replays a recorded .replay.json
│   └── example_bot.py   # Minimal example bot
├── runners/
│   ├── recording.py     # RecordingFlushBot runner — saves history + replays
│   └── benchmark.py     # Multi-instance parallel benchmarking
├── utils/
│   ├── gamestates.py    # Gamestate cache writer (opt-in, off by default)
│   └── run_history.py   # Run history persistence (record_run, load_history)
└── analytics/
    └── analyse_runs.py  # Run history analysis
```

### Gamestate Caching
`balatrobot/utils/gamestates.py:cache_state()` writes JSON snapshots to `gamestate_cache/<game_step>/<timestamp>.json`. Caching is **off by default** — pass `cache_states=True` to the `Bot` constructor to enable it for debugging.

## Coding Standards

### Testing convention
Every new feature or bug fix must include tests. No exceptions.

- **Bot decision logic** (methods that take `G` and return an action): test using cached gamestates from `gamestate_cache/`. Use `load_states("<phase>")` from the existing test helper. Run the bot once with `cache_states=True` to generate cache if the phase is new.
- **Infrastructure / pure Python logic** (constructors, serialization, subprocess args): test with `unittest.mock` — no game required. See `tests/test_bot.py` for the pattern.
- Tests live in `tests/`. One file per module being tested (`test_bot.py`, `test_flush_bot.py`).
- Run with `pytest tests/`.

### Linting and type checking
Ruff and Mypy are configured in `pyproject.toml`. Run before committing:
```bash
ruff check --fix balatrobot/ tests/
mypy balatrobot/
```

Both are enforced by `.pre-commit-config.yaml`. Install hooks once with:
```bash
pip install pre-commit && pre-commit install
```

### Style rules
- Use `isinstance(x, list)` not `type(x) is list`
- No bare `except:` — always `except Exception:` or a specific type
- New public methods should have type annotations on parameters and return type

## Superpowers Workflow

### Finishing a phase or feature branch

When using `superpowers:finishing-a-development-branch`, always create a phase implementation record before merging:

1. Create `docs/superpowers/records/phase-<N>-<slug>.md` using the standard structure:
   - Header metadata (Date, Branch, Follows, Precedes)
   - Overview (2–3 sentences)
   - Scope table (items + independence)
   - What Was Planned
   - What Was Built
   - Bugs Found During Implementation
   - Current State Per Sub-Task table
   - What Is Explicitly Out of Scope
   - Deferred Items
2. Update `docs/PLAN_DOCS_SITE.md` nav if a new phase page was added

The records serve as both internal archaeology and the source content for the public MkDocs documentation site — no separate phase pages are needed.

## Steamodded Installation

The mod folder must be symlinked or placed at `%AppData%\Roaming\Balatro\Mods\balatrobot`. Requires Steamodded v0.9.3+. The mod is loaded via `main.lua` SMODS header; all files are loaded manually via `NFS.read` + `load()`.

**Recommended setup:** Create a directory junction so edits in the repo are reflected immediately in the game:
```
mklink /J "%AppData%\Roaming\Balatro\Mods\balatrobot" "C:\path\to\repo"
```
