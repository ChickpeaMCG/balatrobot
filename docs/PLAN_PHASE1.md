# Phase 1: Replay & Run History — Implementation Plan

## Context

The bot currently plays Balatro end-to-end but discards all run data when the process exits. Phase 1 establishes the persistence layer needed for analytics and eventually training data:

1. **Run history** — every completed run is appended to `run_history.json` with outcome, ante reached, hands played, and deck/stake metadata.
2. **Replay files** — every run is saved as an ordered sequence of `(gamestate, action)` pairs so it can be replayed deterministically from seed.
3. **Lua action logging** — the Lua-side `botlogger.lua` is fixed so `.run` files land in the mod directory (not the game CWD) and use the real seed rather than a hardcoded placeholder.

---

## Files to Modify / Create

| File | Change type |
|------|-------------|
| `bot.py` | Fix GAME_OVER detection; add `_on_run_complete` hook; add `_action_log` |
| `run_history.py` | **New** — `record_run()`, `load_history()`, `print_run_summary()` |
| `run_flush_bot.py` | Add `RecordingFlushBot` subclass; `--seed` CLI arg; wire up history + replay |
| `replay_bot.py` | **New** — `ReplayBot` that reads a `.replay.json` and replays it |
| `src/botlogger.lua` | Fix file-path bug (line 25); fix hardcoded seed bug |
| `.gitignore` | Add `run_history.json`, `replays/` |

---

## Step-by-Step Implementation

### Step 1 — Fix `State.GAME_OVER` detection in `bot.py`

**Problem:** `chooseaction()` compares `G["state"] == State.GAME_OVER`. `State` is a regular `Enum` so this equality never fires against the integer value from Lua's JSON.

**Fix location:** `bot.py` → `run_step()` (not `chooseaction()`), because GAME_OVER arrives with `waitingForAction=false` so `chooseaction()` is never called.

```python
# In run_step(), after receiving and decoding G:
if G.get("state") == State.GAME_OVER.value:
    self._on_run_complete(G)
    return   # don't try to choose an action
```

`State.GAME_OVER.value` yields the integer Lua sends.

---

### Step 2 — Add `_on_run_complete` hook to `Bot` base class (`bot.py`)

No-op default so existing bots are unaffected; subclasses override it.

```python
def _on_run_complete(self, G: dict) -> None:
    """Called once when the game reaches GAME_OVER. Override in subclasses."""
    pass
```

Also add `self._action_log: list[dict] = []` to `__init__`, and in `run_step()` append each `(state, action)` pair **before** sending:

```python
self._action_log.append({"state": self.G, "action": action_str})
```

Reset `_action_log` at the start of each new run (detect transition out of MENU state or on first `run_step()` call after `_on_run_complete` fired).

---

### Step 3 — Create `run_history.py`

Standalone module; no game dependencies.

```python
import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_FILE = Path("run_history.json")

def load_history() -> dict:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return {"best_run": None, "runs": []}

def record_run(seed, deck, stake, ante_reached, result, hands_played, best_hand) -> dict:
    history = load_history()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "deck": deck,
        "stake": stake,
        "ante_reached": ante_reached,
        "result": result,
        "hands_played": hands_played,
        "best_hand": best_hand,
    }
    history["runs"].append(entry)
    best = history.get("best_run")
    if best is None or ante_reached > history["runs"][best]["ante_reached"]:
        history["best_run"] = len(history["runs"]) - 1
    HISTORY_FILE.write_text(json.dumps(history, indent=2))
    return entry

def print_run_summary(entry: dict) -> None:
    print(
        f"Run complete — Ante {entry['ante_reached']} | "
        f"{entry['hands_played']} hands | {entry['result']} | "
        f"seed={entry['seed']}"
    )
```

---

### Step 4 — Update `run_flush_bot.py` with `RecordingFlushBot`

Override `_on_run_complete` to write the replay file and call `record_run`.

```python
import argparse
from pathlib import Path
import json, time
from flush_bot import FlushBot
from run_history import record_run, print_run_summary

REPLAYS_DIR = Path("replays")

class RecordingFlushBot(FlushBot):
    def _on_run_complete(self, G):
        ante = G.get("ante", {}).get("ante") or 0
        entry = record_run(
            seed=self.seed,
            deck=self.deck,
            stake=self.stake,
            ante_reached=ante,
            result="loss",
            hands_played=G.get("num_hands_played", 0),
            best_hand="Flush",
        )
        print_run_summary(entry)

        REPLAYS_DIR.mkdir(exist_ok=True)
        replay_path = REPLAYS_DIR / f"{self.seed or 'unseeded'}_{entry['timestamp'][:19].replace(':','-')}.replay.json"
        replay_path.write_text(json.dumps(self._action_log, indent=2))
        print(f"Replay saved → {replay_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default=None)
    args = parser.parse_args()

    bot = RecordingFlushBot(deck="Blue Deck", stake=1, seed=args.seed, bot_port=12345)
    bot.start_balatro_instance()
    print("Waiting for game to load...")
    time.sleep(15)
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        if bot.sock:
            bot.sock.close()
        bot.stop_balatro_instance()
```

---

### Step 5 — Create `replay_bot.py`

Reads a `.replay.json` and re-sends the recorded actions in order, skipping all decision logic.

> **Prerequisite:** Extract `_recv_gamestate()` and `_send_action()` helpers from `run_step()` in `bot.py` so `ReplayBot` can reuse them.

```python
import json, time, argparse
from pathlib import Path
from bot import Bot

class ReplayBot(Bot):
    def __init__(self, replay_path: str, **kwargs):
        super().__init__(**kwargs)
        entries = json.loads(Path(replay_path).read_text())
        self._replay_actions = [e["action"] for e in entries]
        self._replay_idx = 0

    def run_step(self):
        G = self._recv_gamestate()
        if G is None:
            return
        if self._replay_idx >= len(self._replay_actions):
            print("Replay complete.")
            self.running = False
            return
        action_str = self._replay_actions[self._replay_idx]
        self._replay_idx += 1
        self._send_action(action_str)

    # Stubs — not called during replay
    def skip_or_select_blind(self, G): pass
    def select_cards_from_hand(self, G): pass
    def select_shop_action(self, G): pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("replay", help="Path to .replay.json file")
    parser.add_argument("--port", type=int, default=12345)
    args = parser.parse_args()

    bot = ReplayBot(replay_path=args.replay, deck="Blue Deck", stake=1, seed=None, bot_port=args.port)
    bot.start_balatro_instance()
    time.sleep(15)
    try:
        bot.run()
    except KeyboardInterrupt:
        pass
    finally:
        if bot.sock:
            bot.sock.close()
        bot.stop_balatro_instance()
```

---

### Step 6 — Fix `src/botlogger.lua`

**Bug 1 — wrong save path (line 25):**
```lua
-- BEFORE (saves to game CWD):
-- _filename = Botlogger.path .. _filename

-- AFTER:
_filename = Botlogger.path .. _filename
```

**Bug 2 — hardcoded seed in `start_run()`:**
```lua
-- BEFORE:
Bot.SETTINGS.seed = "1OGB5WO"

-- AFTER:
local _seed = G.GAME.pseudorandom and G.GAME.pseudorandom.seed or "unknown"
-- use _seed when building _filename
```

---

### Step 7 — Update `.gitignore`

```
run_history.json
replays/
gamestate_cache/
```

---

## Verification

1. **Run the bot for one full game:**
   ```bash
   python run_flush_bot.py
   ```
   After GAME_OVER: `run_history.json` exists with one entry; `replays/` contains one `.replay.json`.

2. **Check the console summary:**
   ```
   Run complete — Ante 3 | 42 hands | loss | seed=ABC1234
   ```

3. **Test suite still passes (no schema changes):**
   ```bash
   pytest tests/
   ```

4. **Replay verification:**
   ```bash
   python replay_bot.py replays/<file>.replay.json
   ```

5. **Lua logger** — `.run` files now appear in the mod directory, not the game install directory.
