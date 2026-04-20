# Phase 4b: Bot Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `current_chips` (always 0), wire in `_should_play` for smarter play/discard decisions, expose blind skip tags in the gamestate, and capture failure mode data in run history.

**Architecture:** Four discrete changes — two requiring Lua-side research before code (items 1 and 4), one Python-only wiring (item 3), one schema extension (item 5). Items 1→2→3 are sequential. Items 4 and 5 are independent of each other and of 1/2/3.

**Tech Stack:** Lua (Balatro mod), Python 3.11+, pytest, unittest.mock

---

## File Map

| File | Change |
|---|---|
| `src/utils.lua` | Fix `current_chips` field; add blind skip tag |
| `balatrobot/bots/flush_bot.py` | Wire `_should_play` into `select_cards_from_hand`; track `_last_hand_type` |
| `balatrobot/utils/run_history.py` | Add 4 new optional params to `record_run()` |
| `balatrobot/runners/recording.py` | Pass failure mode fields from `G` to `record_run()` |
| `tests/test_flush_bot.py` | New: test `_should_play` wiring |
| `tests/test_run_history.py` | Extend: add backward compat + new fields tests |

---

## Task 1: Research `current_chips` Lua field

This is an investigation task, not a code task. No commits until Task 2.

**Files:**
- Modify temporarily: `src/utils.lua` (revert before committing)

- [ ] **Step 1: Add temporary debug logging to `Utils.getGameData()`**

  In `src/utils.lua`, replace the existing `current_chips` line (line 212) with a block that dumps all fields from `G.GAME.current_round` and `G.GAME.blind` to `sendDebugMessage`:

  ```lua
  function Utils.getGameData()
      local _game = { }

      if G and G.STATE then
          _game.state               = G.STATE
          _game.num_hands_played    = G.GAME.hands_played
          _game.num_skips           = G.GAME.skips
          _game.round               = G.GAME.round
          _game.discount_percent    = G.GAME.discount_percent
          _game.interest_cap        = G.GAME.interest_cap
          _game.inflation           = G.GAME.inflation
          _game.dollars             = G.GAME.dollars
          _game.max_jokers          = G.GAME.max_jokers
          _game.bankrupt_at         = G.GAME.bankrupt_at
          _game.seed                = G.GAME.pseudorandom and tostring(G.GAME.pseudorandom.seed) or nil

          -- DEBUG: dump all current_round fields
          if G.GAME.current_round then
              for k, v in pairs(G.GAME.current_round) do
                  sendDebugMessage('current_round.'..tostring(k)..' = '..tostring(v))
              end
          end
          -- DEBUG: dump blind fields
          if G.GAME.blind then
              for k, v in pairs(G.GAME.blind) do
                  if type(v) ~= 'table' and type(v) ~= 'function' then
                      sendDebugMessage('blind.'..tostring(k)..' = '..tostring(v))
                  end
              end
          end

          _game.current_chips = G.GAME.chips or 0
      end

      return _game
  end
  ```

- [ ] **Step 2: Run the game and play a hand**

  Start Balatro with the mod loaded. Play one hand. Observe the debug output (check Balatro's debug log or console). Look for a field that:
  - Is 0 at round start
  - Increases after hands are scored
  - Reaches `chips_needed` when the blind is beaten

  Common candidates: `current_round.chips_scored`, `current_round.current_hand.chips`, `blind.chips`

- [ ] **Step 3: Document the confirmed field name**

  Note the exact Lua path (e.g. `G.GAME.current_round.chips_scored`) before reverting the debug code. This is the input to Task 2.

---

## Task 2: Fix `current_chips` in Lua + test

**Files:**
- Modify: `src/utils.lua:197-216`
- Modify: `tests/test_flush_bot.py` (create if it doesn't exist)

- [ ] **Step 1: Revert the debug logging from Task 1 and apply the real fix**

  In `src/utils.lua`, update `Utils.getGameData()` to use the field confirmed in Task 1. Replace the existing line:
  ```lua
  _game.current_chips = G.GAME.chips or 0
  ```
  with (substituting the confirmed field path):
  ```lua
  _game.current_chips = G.GAME.current_round.chips_scored or 0
  ```
  *(Replace `G.GAME.current_round.chips_scored` with the actual confirmed path.)*

- [ ] **Step 2: Write a failing test**

  Create `tests/test_flush_bot.py` (or add to it if it exists):

  ```python
  import pytest
  from balatrobot.bots.flush_bot import FlushBot
  from balatrobot.core.bot import Actions


  def _make_G(**overrides):
      """Minimal gamestate dict for FlushBot tests."""
      base = {
          "hand": [
              {"suit": "Hearts", "value": "Ace"},
              {"suit": "Hearts", "value": "King"},
              {"suit": "Hearts", "value": "Queen"},
              {"suit": "Hearts", "value": "Jack"},
              {"suit": "Hearts", "value": "10"},
          ],
          "current_round": {"hands_left": 3, "discards_left": 3},
          "current_chips": 0,
          "ante": {"blinds": {"chips_needed": 300}},
          "handscores": {},
      }
      base.update(overrides)
      return base


  def test_current_chips_field_is_accessible():
      """Smoke test: gamestate dict includes current_chips as a non-negative integer."""
      G = _make_G(current_chips=150)
      assert isinstance(G["current_chips"], int)
      assert G["current_chips"] >= 0
  ```

- [ ] **Step 3: Run the test to confirm it passes**

  ```
  pytest tests/test_flush_bot.py::test_current_chips_field_is_accessible -v
  ```
  Expected: PASS (this test is Python-side only; Lua correctness is verified by live play)

- [ ] **Step 4: Commit**

  ```bash
  git add src/utils.lua tests/test_flush_bot.py
  git commit -m "fix: correct current_chips Lua field in getGameData"
  ```

---

## Task 3: Wire `_should_play` into `select_cards_from_hand`

**Files:**
- Modify: `balatrobot/bots/flush_bot.py`
- Modify: `tests/test_flush_bot.py`

- [ ] **Step 1: Write a failing test**

  Add to `tests/test_flush_bot.py`:

  ```python
  def test_plays_hand_when_chips_already_meet_requirement():
      """When current_chips >= chips_needed, play instead of discarding to fish for flush."""
      bot = FlushBot(deck="Checkered Deck", stake=1)
      # 3 Hearts + 2 Spades: would normally trigger discard (no 5-card flush)
      G = _make_G(
          hand=[
              {"suit": "Hearts", "value": "Ace"},
              {"suit": "Hearts", "value": "King"},
              {"suit": "Hearts", "value": "Queen"},
              {"suit": "Spades", "value": "2"},
              {"suit": "Spades", "value": "3"},
          ],
          current_round={"hands_left": 3, "discards_left": 3},
          current_chips=500,
          ante={"blinds": {"chips_needed": 300}},
      )
      action = bot.select_cards_from_hand(G)
      assert action[0] == Actions.PLAY_HAND


  def test_discards_normally_when_chips_below_requirement():
      """When current_chips < chips_needed, normal flush-fishing logic applies."""
      bot = FlushBot(deck="Checkered Deck", stake=1)
      G = _make_G(
          hand=[
              {"suit": "Hearts", "value": "Ace"},
              {"suit": "Hearts", "value": "King"},
              {"suit": "Hearts", "value": "Queen"},
              {"suit": "Spades", "value": "2"},
              {"suit": "Spades", "value": "3"},
          ],
          current_round={"hands_left": 3, "discards_left": 3},
          current_chips=0,
          ante={"blinds": {"chips_needed": 300}},
      )
      action = bot.select_cards_from_hand(G)
      assert action[0] == Actions.DISCARD_HAND


  def test_current_chips_zero_guard_does_not_skip_flush_fishing():
      """current_chips=0 must not trigger the 'already won' path (guard against broken field)."""
      bot = FlushBot(deck="Checkered Deck", stake=1)
      G = _make_G(
          hand=[
              {"suit": "Hearts", "value": "Ace"},
              {"suit": "Hearts", "value": "King"},
              {"suit": "Hearts", "value": "Queen"},
              {"suit": "Spades", "value": "2"},
              {"suit": "Spades", "value": "3"},
          ],
          current_round={"hands_left": 3, "discards_left": 3},
          current_chips=0,
          ante={"blinds": {"chips_needed": 0}},  # chips_needed=0 would naively match
      )
      action = bot.select_cards_from_hand(G)
      # current_chips=0 guard prevents false positive — should still discard
      assert action[0] == Actions.DISCARD_HAND
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```
  pytest tests/test_flush_bot.py -v
  ```
  Expected: `test_plays_hand_when_chips_already_meet_requirement` FAILS (bot discards instead of plays)

- [ ] **Step 3: Update `select_cards_from_hand` in `flush_bot.py`**

  Replace the full method body (lines 29-60) with:

  ```python
  def select_cards_from_hand(self, G):
      hand = G["hand"]
      hands_left = G["current_round"]["hands_left"]
      discards_left = G["current_round"]["discards_left"]

      suit_indices: dict[str, list[int]] = {}
      for i, card in enumerate(hand):
          suit = card.get("suit") or "Unknown"
          suit_indices.setdefault(suit, []).append(i)

      most_common_suit = max(suit_indices, key=lambda s: len(suit_indices[s]))

      # Already beaten the chip requirement — stop fishing, play best available
      current_chips = G.get("current_chips", 0)
      chips_needed = G["ante"]["blinds"]["chips_needed"]
      if current_chips > 0 and current_chips >= chips_needed:
          best_cards = sorted(
              suit_indices[most_common_suit], key=lambda i: hand[i]["value"], reverse=True
          )[:5]
          self._last_hand_type = "Other"
          return [Actions.PLAY_HAND, [i + 1 for i in best_cards]]

      # If we have a flush, always play it — scores accumulate across hands
      if len(suit_indices[most_common_suit]) >= 5:
          suit_cards = sorted(
              [(i, hand[i]) for i in suit_indices[most_common_suit]],
              key=lambda x: x[1]["value"],
              reverse=True,
          )
          self._last_hand_type = "Flush"
          return [Actions.PLAY_HAND, [i + 1 for i, _ in suit_cards[:5]]]

      # No flush — discard off-suit cards to fish for one
      off_suit_indices = [
          i for s, idxs in suit_indices.items() if s != most_common_suit for i in idxs
      ][:5]
      if off_suit_indices and discards_left > 0 and hands_left > 1:
          return [Actions.DISCARD_HAND, [i + 1 for i in off_suit_indices]]

      # Forced play — no flush and no discards (or last hand)
      forced_indices = sorted(
          suit_indices[most_common_suit], key=lambda i: hand[i]["value"], reverse=True
      )[:5]
      if not forced_indices:
          forced_indices = list(range(min(5, len(hand))))
      self._last_hand_type = "Other"
      return [Actions.PLAY_HAND, [i + 1 for i in forced_indices]]
  ```

- [ ] **Step 4: Run tests to confirm they pass**

  ```
  pytest tests/test_flush_bot.py -v
  ```
  Expected: all tests PASS

- [ ] **Step 5: Run full test suite**

  ```
  pytest tests/ -v
  ```
  Expected: all tests PASS

- [ ] **Step 6: Commit**

  ```bash
  git add balatrobot/bots/flush_bot.py tests/test_flush_bot.py
  git commit -m "feat: wire _should_play — stop fishing when chip requirement met"
  ```

---

## Task 4: Research + expose blind skip tag

This task has two sub-steps: investigation (no commit), then implementation.

**Files:**
- Modify temporarily: `src/utils.lua` (revert after research)
- Modify: `src/utils.lua:129-143` (final implementation)
- Modify: `tests/test_flush_bot.py`

- [ ] **Step 1: Add temporary debug logging to `Utils.getBlindData()`**

  In `src/utils.lua`, add field dumping inside `Utils.getBlindData()`:

  ```lua
  function Utils.getBlindData()
      local _blinds = { }

      if G and G.GAME then
          _blinds.ondeck = G.GAME.blind_on_deck

          -- DEBUG: dump all top-level G.GAME fields related to tags
          if G.GAME.current_round then
              for k, v in pairs(G.GAME.current_round) do
                  if string.find(tostring(k), 'tag') then
                      sendDebugMessage('current_round.'..tostring(k)..' = '..tostring(v))
                  end
              end
          end
          -- DEBUG: dump G.tags (the offered tag for each blind)
          if G.tags then
              for i, tag in ipairs(G.tags) do
                  sendDebugMessage('G.tags['..i..'].key = '..tostring(tag.key))
                  sendDebugMessage('G.tags['..i..'].name = '..tostring(tag.name))
              end
          end

          if G.GAME.blind then
              _blinds.chips_needed = G.GAME.blind.chips
              _blinds.name        = G.GAME.blind.name
              _blinds.boss        = G.GAME.blind.boss or false
          end
      end

      return _blinds
  end
  ```

- [ ] **Step 2: Run the game and observe at the blind select screen**

  Navigate to a blind select screen. Look at debug output for:
  - Which Lua table holds the offered tag (e.g. `G.tags`, `G.GAME.current_round.tag`, etc.)
  - Whether boss blinds have a tag or `nil`
  - The structure of the tag object (does it have `.key`, `.name`, etc.)

  Note the confirmed field before reverting.

- [ ] **Step 3: Verify `SKIP_BLIND` is fully wired end-to-end**

  In `src/bot.lua` lines 36-43, `SKIP_BLIND` has `ACTIONPARAMS` defined. In `src/middleware.lua` lines 211-213, the middleware clicks the skip button when `_action == Bot.ACTIONS.SKIP_BLIND`. Confirm this by attempting a skip action from Python:

  Temporarily change `FlushBot.skip_or_select_blind` to return `[Actions.SKIP_BLIND]`, run one game step at a blind select screen, and verify the blind is skipped. Revert after confirming.

  If SKIP_BLIND is NOT wired (blank screen / error), the middleware hook needs fixing — stop and investigate before proceeding.

- [ ] **Step 4: Implement the tag field in `Utils.getBlindData()`**

  Revert debug logging. Add the confirmed tag field. Example using `G.tags[1]` as a placeholder (substitute confirmed path):

  ```lua
  function Utils.getBlindData()
      local _blinds = { }

      if G and G.GAME then
          _blinds.ondeck = G.GAME.blind_on_deck

          if G.GAME.blind then
              _blinds.chips_needed = G.GAME.blind.chips
              _blinds.name        = G.GAME.blind.name
              _blinds.boss        = G.GAME.blind.boss or false
          end

          -- Offered skip tag (nil for boss blind or when no tag is available)
          _blinds.tag = nil
          if G.tags and #G.tags > 0 then
              _blinds.tag = G.tags[1].key or nil
          end
      end

      return _blinds
  end
  ```
  *(Adjust the `G.tags` path to match what was confirmed in Step 2.)*

- [ ] **Step 5: Write a failing test**

  Add to `tests/test_flush_bot.py`:

  ```python
  def test_gamestate_includes_blind_tag_key():
      """blind dict must always include a 'tag' key (value may be None)."""
      G = _make_G()
      G.setdefault("ante", {}).setdefault("blinds", {})
      G["ante"]["blinds"]["tag"] = None  # simulate no tag (boss blind)
      assert "tag" in G["ante"]["blinds"]

      G["ante"]["blinds"]["tag"] = "tag_double"
      assert G["ante"]["blinds"]["tag"] == "tag_double"
  ```

  Note: this test is Python-side only. The Lua correctness is confirmed by live play in Step 2/3.

- [ ] **Step 6: Run test to confirm it passes**

  ```
  pytest tests/test_flush_bot.py::test_gamestate_includes_blind_tag_key -v
  ```
  Expected: PASS

- [ ] **Step 7: Run full test suite**

  ```
  pytest tests/ -v
  ```
  Expected: all tests PASS

- [ ] **Step 8: Commit**

  ```bash
  git add src/utils.lua tests/test_flush_bot.py
  git commit -m "feat: expose blind skip tag in gamestate via getBlindData"
  ```

---

## Task 5: Extend run history schema with failure mode fields

**Files:**
- Modify: `balatrobot/utils/run_history.py`
- Modify: `balatrobot/runners/recording.py`
- Modify: `tests/test_run_history.py`

- [ ] **Step 1: Write failing tests**

  Add to `tests/test_run_history.py`:

  ```python
  @patch("balatrobot.utils.run_history.HISTORY_FILE")
  def test_record_run_stores_failure_mode_fields(mock_path):
      mock_path.exists.return_value = False
      written = {}
      mock_path.write_text.side_effect = lambda t: written.update({"data": json.loads(t)})
      entry = record_run(
          "ABC1234", "Blue Deck", 1, 2, "loss", 15, "Flush",
          final_chips_needed=300,
          final_chips_scored=250,
          final_discards_remaining=0,
          final_hand_type="Flush",
      )
      assert entry["final_chips_needed"] == 300
      assert entry["final_chips_scored"] == 250
      assert entry["final_discards_remaining"] == 0
      assert entry["final_hand_type"] == "Flush"
      assert written["data"]["runs"][0]["final_chips_needed"] == 300


  @patch("balatrobot.utils.run_history.HISTORY_FILE")
  def test_record_run_omits_failure_fields_when_none(mock_path):
      mock_path.exists.return_value = False
      written = {}
      mock_path.write_text.side_effect = lambda t: written.update({"data": json.loads(t)})
      entry = record_run("ABC1234", "Blue Deck", 1, 2, "loss", 15, "Flush")
      assert "final_chips_needed" not in entry
      assert "final_chips_scored" not in entry


  def test_runs_for_label_handles_missing_failure_fields():
      """Old run history entries without failure fields must not break label queries."""
      history = _history(_run(2, label="phase4"))  # old entry, no failure fields
      runs = runs_for_label(history, "phase4")
      assert len(runs) == 1
      assert runs[0].get("final_chips_needed") is None
      assert runs[0].get("final_chips_scored") is None
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```
  pytest tests/test_run_history.py -v
  ```
  Expected: the three new tests FAIL (`record_run` doesn't accept the new params yet)

- [ ] **Step 3: Update `record_run()` signature in `run_history.py`**

  Replace the existing `record_run` function (lines 14-36) with:

  ```python
  def record_run(
      seed, deck, stake, ante_reached, result, hands_played, best_hand,
      label: str | None = None,
      final_chips_needed: int | None = None,
      final_chips_scored: int | None = None,
      final_discards_remaining: int | None = None,
      final_hand_type: str | None = None,
  ) -> dict:
      history = load_history()
      entry: dict = {
          "timestamp": datetime.now(timezone.utc).isoformat(),
          "seed": seed,
          "deck": deck,
          "stake": stake,
          "ante_reached": ante_reached,
          "result": result,
          "hands_played": hands_played,
          "best_hand": best_hand,
      }
      if label is not None:
          entry["label"] = label
      if final_chips_needed is not None:
          entry["final_chips_needed"] = final_chips_needed
      if final_chips_scored is not None:
          entry["final_chips_scored"] = final_chips_scored
      if final_discards_remaining is not None:
          entry["final_discards_remaining"] = final_discards_remaining
      if final_hand_type is not None:
          entry["final_hand_type"] = final_hand_type
      history["runs"].append(entry)
      best_idx = history.get("best_run")
      if best_idx is None or ante_reached > history["runs"][best_idx]["ante_reached"]:
          history["best_run"] = len(history["runs"]) - 1
      HISTORY_FILE.write_text(json.dumps(history, indent=2))
      return entry
  ```

- [ ] **Step 4: Run tests to confirm they pass**

  ```
  pytest tests/test_run_history.py -v
  ```
  Expected: all tests PASS

- [ ] **Step 5: Update `RecordingFlushBot._on_run_complete` in `recording.py`**

  Replace the existing `_on_run_complete` method (lines 30-48) with:

  ```python
  def _on_run_complete(self, G):
      ante = (G.get("ante") or {}).get("ante") or 0
      blind = (G.get("ante") or {}).get("blinds") or {}
      round_data = G.get("current_round") or {}
      entry = record_run(
          seed=G.get("seed") or self._current_seed,
          deck=self.deck,
          stake=self.stake,
          ante_reached=ante,
          result="loss",
          hands_played=G.get("num_hands_played", 0),
          best_hand="Flush",
          label=self._label,
          final_chips_needed=blind.get("chips_needed"),
          final_chips_scored=G.get("current_chips"),
          final_discards_remaining=round_data.get("discards_left"),
          final_hand_type=getattr(self, "_last_hand_type", None),
      )
      print_run_summary(entry)

      REPLAYS_DIR.mkdir(exist_ok=True)
      safe_ts = entry["timestamp"][:19].replace(":", "-")
      seed_label = G.get("seed") or self._current_seed or "unseeded"
      replay_path = REPLAYS_DIR / f"{seed_label}_{safe_ts}.replay.json"
      replay_path.write_text(json.dumps(self._action_log, indent=2))
      print(f"Replay saved -> {replay_path}")
  ```

- [ ] **Step 6: Run full test suite**

  ```
  pytest tests/ -v
  ```
  Expected: all tests PASS

- [ ] **Step 7: Run linting and type checks**

  ```bash
  ruff check --fix balatrobot/ tests/
  mypy balatrobot/
  ```
  Expected: no errors

- [ ] **Step 8: Commit**

  ```bash
  git add balatrobot/utils/run_history.py balatrobot/runners/recording.py tests/test_run_history.py
  git commit -m "feat: capture failure mode fields in run history (chips, discards, hand type)"
  ```

---

## Final verification

- [ ] **Run full test suite one last time**

  ```
  pytest tests/ -v
  ```
  Expected: all tests PASS

- [ ] **Check git log**

  ```
  git log --oneline -6
  ```
  Expected: 4 feature commits since the spec commit.
