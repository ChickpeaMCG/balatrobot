# Balatrobot Development Roadmap

## Current State

The bot framework is functional end-to-end:
- Lua mod runs inside Balatro (Steamodded 1.0.0-beta compatible)
- Python connects over UDP, receives full game state JSON, sends actions
- Game state schema is complete: hand cards (with enhancement/edition/seal), jokers, shop, blind chip requirements, hand score table, round counters
- All decision phases are cached to `gamestate_cache/` as JSON snapshots
- Test suite runs offline against cached states (`pytest tests/`)

The `FlushBot` strategy is naive: always select blinds, hunt flushes, never buy anything.

---

## Phase 1 — Replay & Run History

**Goal:** Every run can be stored, replayed, and compared. Builds the foundation for analytics and eventually training data.

### 1a. Action logging (Lua)
- [x] `botlogger.lua` handles `.run` file naming for seeded and unseeded runs (`seed_deck_stake_challenge_port.run`)
- [x] API-driven action recording superseded by Python-side `_action_log` in `bot.py` — Lua `.run` files are no longer the primary record for Python-driven runs
- Note: `Botlogger.path` is still `''` (files land in CWD); intentionally left — Python recording is the canonical approach

### 1b. Run outcome tracking (Python)
- [x] Detect `G["state"] == State.GAME_OVER` in `bot.py:run_step()`, call `_on_run_complete` hook
- [x] `run_history.json` written via `balatrobot/utils/run_history.py:record_run()` — one entry per completed run with timestamp, seed, deck, stake, ante_reached, result, hands_played, best_hand
- [x] `best_run` pointer (index of highest ante reached) stored in `run_history.json` header
- [x] One-line summary printed via `print_run_summary()`: `Run complete — Ante N | N hands | result | seed=...`

### 1c. Replay runner
- [x] `ReplayBot` in `balatrobot/bots/replay_bot.py` replays runs from `.replay.json` files saved by `RecordingFlushBot`
- [x] `replay_bot.py` CLI entry point (`python replay_bot.py <file>`)
- [x] `.replay.json` files record full gamestate + action string at every step (richer than the original `.run` format)
- Note: approach is action-sequence replay (Python) rather than seed-determinism replay (Lua). Trade-off: action replay can desync on game version changes; seed replay would be immune but requires more Lua infrastructure. Current approach is sufficient for debugging and run comparison.

---

## Phase 2 — Smarter FlushBot ✅ Complete

**Goal:** Use the richer game state to make decisions that are actually informed by the game situation.

See `docs/PLAN_PHASE2.md` for full implementation record, bugs found, and deferred items.

### 2a. Play/discard decisions
- [x] Flush-first: if 5+ cards of same suit, always play — scores accumulate across hands
- [x] Discard off-suit cards to fish for flush when discards remain and not last hand
- [x] Play forced hand when no flush available and no discards (or last hand)
- [~] `current_chips` — `G.GAME.chips` is always 0 (wrong field); carried to Phase 4
- [~] Score-vs-deficit check (`_should_play`) — scaffolded, not wired in; carried to Phase 4

### 2b. Shop strategy
- [x] `FLUSH_JOKERS` priority list defined: `j_4_fingers`, `j_flush`, `j_runner`, `j_shortcut`, `j_fibonacci`
- [x] Buys highest-priority affordable joker, ends shop otherwise
- [x] No rerolling (out of scope)
- [~] Priority list too narrow to trigger reliably — joker selection to be data-driven in Phase 3

### 2c. Blind skipping
- [~] Deferred to Phase 4 — requires exposing offered tag in `Utils.getBlindData()` (Lua)

### Deck
- [x] Switched to Checkered Deck (26 Hearts + 26 Spades) — optimal for flush bot

### Baseline performance (20 runs, Checkered Deck, Stake 1)
- Avg ante: ~1.5 | Ante 1: 50% | Ante 2: 48% | Ante 4: 2% (outlier)
- Failure mode: chip wall at Ante 2 — naked flushes cannot reliably hit without jokers

---

## Phase 3 — Game Mechanics Catalogue

**Goal:** Give bots structured, typed knowledge of what every item in the game does — replacing hardcoded key lists with a query-able catalogue. Also lays the feature-vector foundation for RL (Phase 5).

See `docs/PLAN_PHASE3.md` for full implementation record.

### 3a. Static data catalogue (`balatrobot/data/`)
- [x] `scripts/extract_balatro_data.py` — parses Balatro Lua source files to output skeleton JSON for all item categories (jokers, tarots, planets, spectrals, vouchers)
- [x] `balatrobot/data/models.py` — `JokerData`, `TarotData`, etc. dataclasses; `EffectType` and `TriggerCondition` enums
- [x] `balatrobot/data/catalogue.py` — `get_joker()`, `all_jokers()`, `lru_cache` loaders; runtime warning on unknown keys
- [x] JSON data files: `jokers.json` (150 extracted, 22 annotated), `tarots.json`, `planets.json`, `spectrals.json`, `vouchers.json`, `editions.json`, `seals.json`, `enhancements.json`
- [x] `tests/test_catalogue.py` — 18 tests: load, parse, lookup, unknown-key warning

### 3b. Feature encoder (`balatrobot/features/`)
- [x] `balatrobot/features/constants.py` — `SUITS`, `VALUES`, `HAND_TYPES`, `OBSERVATION_SHAPE = 300`
- [x] `balatrobot/features/encoder.py` — `GamestateEncoder.encode(G) -> np.ndarray(float32, shape=(300,))`
- [x] Feature layout: 9 global scalars + 152 hand card dims + 80 joker dims + 12 consumable dims + 39 hand-score dims + 8 shop flags
- [x] `tests/test_encoder.py` — shape/dtype correct, values in [0, 1], handles unknown joker keys (zero vector)

### 3c. Bot integration
- [x] Replace `FlushBot.FLUSH_JOKERS` hardcoded list with catalogue query: `all_jokers()` filtered by `flush_synergy >= 0.7`

---

## Phase 4 — Run Analytics

**Goal:** Understand where runs fail so bot improvement is data-driven.

- [ ] `analyse_runs.py` script: reads `run_history.json`, outputs win rate, average ante, most common exit ante
- [ ] Correlate run outcomes with jokers held, deck used, stake
- [ ] Identify the most common failure mode: out of hands, chip deficit, or bad blind matchup
- [ ] Resolve `current_chips` — find the correct Balatro Lua field for chips scored toward the current blind
- [ ] Re-enable `_should_play` with correct `current_chips` for smarter play/discard decisions
- [ ] Blind skipping — expose offered tag in `Utils.getBlindData()` (Lua), then re-implement skip logic

---

## Phase 5 — RL Groundwork

**Goal:** Replace hand-coded heuristics with a learned policy.

- [ ] `BalatroEnv(gym.Env)` wraps the bot loop; observation = `GamestateEncoder.encode(G)` (300-dim float32, from Phase 3)
- [ ] Define action space: `Discrete` over (PLAY_HAND variants, DISCARD_HAND variants) for hand selection as a starting point
- [ ] Define reward: +1 per ante cleared, -1 on game over, shaped by chips scored vs chips needed
- [ ] Instrument `Bot` to optionally record `(obs, action, reward)` tuples per step into a replay buffer
- [ ] Train a simple policy with Stable Baselines3 (MlpPolicy, PPO) against the gamestate cache first, then live

---

## Deferred / Ideas

- Multi-instance parallel training (infrastructure already exists in `benchmark_multi_instance()`)
- Challenge mode runs (fixed seed + challenge for reproducible benchmarking)
- Web dashboard for run history (stretch goal)
- Joker synergy graph (map which joker combinations produce the highest scores)
