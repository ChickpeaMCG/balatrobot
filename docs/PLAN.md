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
- [~] `current_chips` — `G.GAME.chips` is always 0 (wrong field); carried to Phase 3
- [~] Score-vs-deficit check (`_should_play`) — scaffolded, not wired in; carried to Phase 3

### 2b. Shop strategy
- [x] `FLUSH_JOKERS` priority list defined: `j_4_fingers`, `j_flush`, `j_runner`, `j_shortcut`, `j_fibonacci`
- [x] Buys highest-priority affordable joker, ends shop otherwise
- [x] No rerolling (out of scope)
- [~] Priority list too narrow to trigger reliably — joker selection to be data-driven in Phase 3

### 2c. Blind skipping
- [~] Deferred to Phase 3 — requires exposing offered tag in `Utils.getBlindData()` (Lua)

### Deck
- [x] Switched to Checkered Deck (26 Hearts + 26 Spades) — optimal for flush bot

### Baseline performance (20 runs, Checkered Deck, Stake 1)
- Avg ante: ~1.5 | Ante 1: 50% | Ante 2: 48% | Ante 4: 2% (outlier)
- Failure mode: chip wall at Ante 2 — naked flushes cannot reliably hit without jokers

---

## Phase 3 — Run Analytics

**Goal:** Understand where runs fail so bot improvement is data-driven.

- [ ] `analyse_runs.py` script: reads `run_history.json`, outputs win rate, average ante, most common exit ante
- [ ] Correlate run outcomes with jokers held, deck used, stake
- [ ] Identify the most common failure mode: out of hands, chip deficit, or bad blind matchup

---

## Phase 4 — RL Groundwork

**Goal:** Replace hand-coded heuristics with a learned policy.

- [ ] Define observation vector: flattened hand cards (suit/value/enhancement one-hot), chips_needed, hands_left, discards_left, joker keys (encoded), ante, dollars
- [ ] Define action space: discrete over (PLAY_HAND variants, DISCARD_HAND variants) for the hand selection phase as a starting point
- [ ] Define reward: +1 per ante cleared, -1 on game over, shaped by chips scored vs chips needed
- [ ] Instrument `Bot` to optionally record `(obs, action, reward)` tuples per step into a replay buffer
- [ ] Train a simple policy with Stable Baselines3 (MlpPolicy, PPO) against the gamestate cache first, then live

---

## Deferred / Ideas

- Multi-instance parallel training (infrastructure already exists in `benchmark_multi_instance()`)
- Challenge mode runs (fixed seed + challenge for reproducible benchmarking)
- Web dashboard for run history (stretch goal)
- Joker synergy graph (map which joker combinations produce the highest scores)
