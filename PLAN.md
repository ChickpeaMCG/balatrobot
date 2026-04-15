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
- [ ] Fix `botlogger.lua`: uncomment and correct the `.run` file save path so files land in the mod directory
- [ ] When `api=true`, hook incoming API actions through `logbotdecision` so Python-driven runs are recorded, not just Lua-native runs
- [ ] `.run` files are keyed by `seed_deck_stake_challenge_port.run` — verify this works for seeded and unseeded runs

### 1b. Run outcome tracking (Python)
- [ ] Detect `G["state"] == State.GAME_OVER` in `Bot.chooseaction()` and emit a structured run record
- [ ] Write `run_history.json` — append one entry per completed run:
  ```json
  {
    "timestamp": "2026-04-12T21:00:00",
    "seed": "ABC1234",
    "deck": "Blue Deck",
    "stake": 1,
    "ante_reached": 3,
    "result": "loss",
    "hands_played": 42,
    "best_hand": "Flush"
  }
  ```
- [ ] Track `best_run` pointer (highest ante reached) in a summary header in `run_history.json`
- [ ] Print a one-line summary on exit: `Run complete — Ante 3 | 42 hands | loss`

### 1c. Replay runner
- [ ] Add `--replay <seed>` flag to `run_flush_bot.py` that sets `Bot.SETTINGS.replay=true` and the correct seed, replaying a stored `.run` file without Python decision logic
- [ ] Validate that a replayed run produces the same game progression as the original (same seed = deterministic)

---

## Phase 2 — Smarter FlushBot

**Goal:** Use the richer game state to make decisions that are actually informed by the game situation.

### 2a. Play/discard decisions
- [ ] Calculate expected chips for best available hand using `handscores` + card values
- [ ] Compare against `chips_needed - current_chips` to decide whether to play or fish for a better hand
- [ ] Respect `hands_left`: if on last hand, always play regardless of hand quality
- [ ] Only discard when `discards_left > 0` AND expected best hand is below chip target with hands remaining

### 2b. Shop strategy
- [ ] Define a priority list of flush-synergy joker keys (e.g. `j_runner`, `j_shortcut`, `j_fibonacci`, `j_flush`, `j_4_fingers`)
- [ ] Buy highest-priority joker that is affordable and in stock
- [ ] Skip shop if no priority jokers are available

### 2c. Blind skipping
- [ ] Track tags awarded for skipping — if a useful tag is on offer (e.g. `tag_double`), factor into skip decision
- [ ] Always select Boss blind (can't skip), skip Small/Big if a good tag is offered and ante allows it

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
