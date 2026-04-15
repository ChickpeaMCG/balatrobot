# Balatrobot — Fork History & Changes

## Upstream Origin

This project is forked from [giewev/balatrobot](https://github.com/giewev/balatrobot), a Balatro botting mod built on Steamodded. The upstream project provided:

- **Lua mod framework** — Steamodded mod entry point (`main.lua`), external libraries (`lib/`), and the core source modules (`src/api.lua`, `src/bot.lua`, `src/middleware.lua`, `src/botlogger.lua`, `src/utils.lua`)
- **UDP communication protocol** — the mod listens on a port; a Python client sends `HELLO` to receive gamestate JSON and sends action strings to drive the bot
- **Bot base class** (`bot.py`) — abstract `Bot` with `chooseaction()`, action enum, state enum, socket management, and Balatro process lifecycle
- **Example bots** — `FlushBot` (hunt flushes, never buy), `bot_example.py`
- **Lua-native replay system** — `botlogger.lua` records actions to `.run` files for Lua-side replay
- **Speedup hooks** — `config.lua` controls dt override, frame skipping, vsync disable for fast botting
- **Multi-instance benchmarking** — `benchmark_multi_instance()` in `flush_bot.py`

---

## Changes Made in This Fork

### Commit `8c07c8d` — Fork baseline (Steamodded 1.0.0 compat + bug fixes)

The upstream code did not run against Steamodded 1.0.0. This commit brought it to a working state:

- **`main.lua`** — replaced removed `SMODS.INIT` / `findModByID` API with `SMODS.current_mod.path`
- **`bot.py`** — fixed `Bot.run()` (never started due to `self.running=False` guard); fixed `chooseaction()` passing explicit `self` to already-bound methods
- **`flush_bot.py`** — renamed `play_flushes` → `select_cards_from_hand`; fixed missing module-level globals
- **`src/middleware.lua`** — added guard to prevent `c_start_run` firing hundreds of times per frame
- **`run_flush_bot.py`** — added one-command runner with automatic game launch and Ctrl+C shutdown
- **`CLAUDE.md`**, **`README.md`** — full project documentation added

### Commit `fe898be` — Development roadmap

- **`PLAN.md`** — phased roadmap: replay & run history (Phase 1), smarter FlushBot (Phase 2), analytics (Phase 3), RL groundwork (Phase 4)

### Commit `37d4730` — Full gamestate schema, caching, and test suite

- **`src/utils.lua`** — extended `Utils.getGamestate()` to include hand scores, tags, deck back, joker editions/state, card enhancements/seals/editions
- **`gamestates.py`** — `cache_state()` writes every decision-point gamestate to `gamestate_cache/<phase>/<timestamp>.json`
- **`tests/test_flush_bot.py`** — offline test suite: runs FlushBot against cached gamestates without needing the game running
- **`docs/PLAN_PHASE1.md`** — detailed implementation plan for Phase 1

### Commit `8b81e65` — Restructure Python code into `balatrobot/` package

Flat Python files reorganised into a proper package:

- **`balatrobot/core/bot.py`** — `Bot` base class (was `bot.py`)
- **`balatrobot/bots/flush_bot.py`** — `FlushBot` strategy (was `flush_bot.py`)
- **`balatrobot/bots/replay_bot.py`** — `ReplayBot` (was `replay_bot.py`)
- **`balatrobot/bots/example_bot.py`** — minimal example bot
- **`balatrobot/runners/recording.py`** — `RecordingFlushBot` runner with `--seed` flag
- **`balatrobot/runners/benchmark.py`** — multi-instance parallel benchmarking
- **`balatrobot/utils/gamestates.py`** — gamestate cache writer; caching now **opt-in** (`cache_states=False` by default on `Bot`) to prevent generating millions of files during long benchmark runs
- **`balatrobot/utils/run_history.py`** — run history persistence
- **`balatrobot/analytics/analyse_runs.py`** — run history analysis
- **`run_flush_bot.py`** / **`replay_bot.py`** — thin root-level entry points retained for convenience

### Commits `9fee92d` + `c033dc9` — Phase 1: Run history, replay recording, GAME_OVER detection

#### Problem solved

The bot played full games but threw away all run data on exit. There was no way to know how far a run got, what seed was used, or replay what happened.

#### What was built

**`bot.py` — core bot infrastructure fixes and hooks**
- Fixed `GAME_OVER` detection: was comparing `State` enum to an integer (never matched); moved check to `run_step()` using `State.GAME_OVER.value`
- Added `_action_log: list[dict]` — records every `(gamestate, action)` pair during a run
- Added `_current_seed: str` — stores the seed actually used (important when seed is auto-generated)
- Added `_on_run_complete(G)` — no-op hook; subclasses override to handle end-of-run
- Extracted `_recv_gamestate()` and `_send_action()` helpers from `run_step()` for use by `ReplayBot`
- `_action_log` resets automatically at the start of each new run (`waitingFor == "start_run"`)

**`run_history.py`** *(new)*
- `record_run()` — appends a structured entry to `run_history.json` and tracks `best_run` pointer
- `load_history()` — reads `run_history.json` (returns empty structure if missing)
- `print_run_summary()` — one-line console summary: `Run complete — Ante 3 | 42 hands | loss | seed=ABC1234`

**`run_flush_bot.py`** — replaced simple script with `RecordingFlushBot`
- Subclasses `FlushBot`, overrides `_on_run_complete` to write run history and save replay file
- Replay files written to `replays/<seed>_<timestamp>.replay.json`
- Adds `--seed` CLI argument for reproducible runs

**`replay_bot.py`** *(new)*
- `ReplayBot` reads a `.replay.json` and replays the recorded action sequence
- Waits for `waitingForAction=true` before consuming each action (stays in sync with game state)
- Stops when `GAME_OVER` is reached or replay is exhausted
- Usage: `python replay_bot.py replays/<file>.replay.json [--port 12345]`

**`src/botlogger.lua`** — path bug fixed
- Line 25 was commented out, causing `.run` files to save to the game's working directory instead of the mod directory. Uncommented.

**`.gitignore`** — updated
- Added `run_history.json`, `replays/`, `*.run`

---

## Repository Layout (current)

```
balatrobot/                      # repo root (also the Steamodded mod folder)
├── main.lua                     # Steamodded mod entry point
├── config.lua                   # Mod settings (port, speedup, frame skip)
├── run_flush_bot.py             # Entry point: RecordingFlushBot runner
├── replay_bot.py                # Entry point: replay a .replay.json file
├── src/
│   ├── api.lua                  # UDP server, action queue, speedup hooks
│   ├── bot.lua                  # Bot action definitions, ACTIONPARAMS validation
│   ├── middleware.lua            # Hooks into Balatro game loop, UI interaction
│   ├── botlogger.lua            # Lua-side action logging to .run files
│   └── utils.lua                # Gamestate serialisation, action parsing/validation
├── lib/                         # External Lua libraries (sock, json, hook, bitser, list)
├── balatrobot/                  # Python package
│   ├── core/bot.py              # Bot base class, State/Actions enums, socket loop
│   ├── bots/
│   │   ├── flush_bot.py         # FlushBot strategy (hunt flushes, skip shop)
│   │   ├── replay_bot.py        # ReplayBot — replays a recorded run
│   │   └── example_bot.py      # Minimal example bot
│   ├── runners/
│   │   ├── recording.py         # RecordingFlushBot — writes history + replays
│   │   └── benchmark.py         # Multi-instance parallel benchmarking
│   ├── utils/
│   │   ├── gamestates.py        # Gamestate cache writer (opt-in)
│   │   └── run_history.py       # Run history persistence
│   └── analytics/
│       └── analyse_runs.py      # Run history analysis
├── tests/
│   └── test_flush_bot.py        # Offline test suite against cached gamestates
├── docs/
│   ├── PLAN.md                  # Full development roadmap (Phases 1–4)
│   ├── PLAN_PHASE1.md           # Phase 1 detailed implementation plan
│   └── FORK_AND_CHANGES.md      # This file
├── CLAUDE.md                    # Claude Code project instructions
└── README.md                    # Project overview and usage guide
```

---

## Runtime Data (gitignored)

| Path | Contents |
|------|----------|
| `run_history.json` | Append-only log of completed runs with outcome metadata |
| `replays/*.replay.json` | Per-run ordered `(gamestate, action)` sequences for replay |
| `gamestate_cache/` | Per-decision-phase JSON snapshots (used by test suite) |
| `*.run` | Lua-side botlogger action files |
