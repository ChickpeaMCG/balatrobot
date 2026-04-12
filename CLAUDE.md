# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Balatrobot is a two-part system: a **Lua mod** that runs inside Balatro (via Steamodded) and a **Python client** that drives bot logic externally. They communicate over UDP sockets.

The mod does **not** contain a finished bot — it exposes an API. Bot logic lives in `src/bot.lua` (Lua-native) or in Python clients that subclass `bot.py:Bot`.

## Running a Bot

**Python client (recommended for new bots):**
```bash
python bot_example.py        # runs the example bot
python flush_bot.py          # runs the flush-focused benchmark bot
```

**Lua-native bot:** Edit `src/bot.lua` directly with `Bot.SETTINGS.api = false` in `Bot.SETTINGS`.

**Multi-instance benchmarking:** `flush_bot.py` contains `benchmark_multi_instance()` for running multiple Balatro instances in parallel (ports start at 12348+i).

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

### Python Client (`bot.py`)
`Bot` is an abstract base class. Subclass it and override these methods (all receive `self` and `G` gamestate dict):
- `skip_or_select_blind(G)` → `[Actions.SELECT_BLIND]` or `[Actions.SKIP_BLIND]`
- `select_cards_from_hand(G)` → `[Actions.PLAY_HAND, [card_indices]]` or `[Actions.DISCARD_HAND, [card_indices]]`
- `select_shop_action(G)` → `[Actions.END_SHOP]`, `[Actions.BUY_CARD, [idx]]`, etc.
- `select_booster_action(G)` → `[Actions.SKIP_BOOSTER_PACK]` or `[Actions.SELECT_BOOSTER_CARD, [hand_idxs], [pack_idx]]`
- `sell_jokers(G)`, `rearrange_jokers(G)`, `use_or_sell_consumables(G)`, `rearrange_consumables(G)`, `rearrange_hand(G)`

Card indices are **1-based**. The gamestate `G` dict includes: `hand`, `jokers`, `consumables`, `ante`, `shop`, `current_round`, `state`, `dollars`, `waitingFor`, `waitingForAction`.

### Gamestate Caching
`gamestates.py:cache_state()` writes JSON snapshots to `gamestate_cache/<game_step>/<timestamp>.json` for debugging/replay.

## Steamodded Installation

The mod folder must be placed at `%AppData%\Roaming\Balatro\Mods\balatrobot`. Requires Steamodded v0.9.3+. The mod is loaded via `main.lua` SMODS header; all files are loaded manually via `NFS.read` + `load()`.
