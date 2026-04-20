# Phase 5: Documentation Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a public MkDocs site at `https://ChickpeaMCG.github.io/balatrobot/` that auto-deploys on push to `main` and surfaces the four existing phase records as the development chronicle.

**Architecture:** Static site built from Markdown in `docs/`, served via GitHub Pages from the `gh-pages` branch. GitHub Actions handles the build-and-deploy step on every push to `main`. No analytics, no data pipeline — docs content only.

**Tech Stack:** MkDocs 1.6+, mkdocs-material 9.5+, GitHub Actions, GitHub Pages

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `.gitignore` | Modify | Add `site/` |
| `pyproject.toml` | Modify | Add `[project]` + `[project.optional-dependencies]` docs group |
| `mkdocs.yml` | Create | MkDocs config: theme, nav, site URL |
| `docs/index.md` | Create | Project overview page |
| `docs/architecture.md` | Create | System architecture overview |
| `.github/workflows/docs.yml` | Create | Auto-deploy on push to `main` |

---

### Task 1: Add `site/` to `.gitignore`

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add site/ to .gitignore**

Append to `.gitignore`:

```
site/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore mkdocs site/ build output"
```

---

### Task 2: Add docs dependencies to `pyproject.toml`

**Files:**
- Modify: `pyproject.toml`

`pyproject.toml` currently has no `[project]` section. Add one with the docs optional dependency group so `pip install -e ".[docs]"` works.

- [ ] **Step 1: Add project section and docs dependency**

Add at the top of `pyproject.toml` (before existing `[tool.*]` sections):

```toml
[project]
name = "balatrobot"
version = "0.1.0"
requires-python = ">=3.10"

[project.optional-dependencies]
docs = [
    "mkdocs>=1.6",
    "mkdocs-material>=9.5",
]
```

- [ ] **Step 2: Verify install works**

```bash
pip install -e ".[docs]"
```

Expected: installs without error, `mkdocs --version` prints a version string.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add docs optional dependency group to pyproject.toml"
```

---

### Task 3: Create `mkdocs.yml`

**Files:**
- Create: `mkdocs.yml` (repo root)

- [ ] **Step 1: Create mkdocs.yml**

```yaml
site_name: Balatrobot
site_description: An AI bot for Balatro — development chronicle
site_url: https://ChickpeaMCG.github.io/balatrobot/
repo_url: https://github.com/ChickpeaMCG/balatrobot
repo_name: balatrobot

theme:
  name: material
  palette:
    - scheme: slate
      primary: red
      accent: amber
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
    - scheme: default
      primary: red
      accent: amber
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
  features:
    - navigation.tabs
    - navigation.sections
    - content.code.copy

nav:
  - Home: index.md
  - Phases:
      - Phase 1 — Replay & History: superpowers/records/phase-1-replay-run-history.md
      - Phase 2 — Smarter FlushBot: superpowers/records/phase-2-smarter-flushbot.md
      - Phase 3 — Mechanics Catalogue: superpowers/records/phase-3-game-mechanics-catalogue.md
      - Phase 4 — Run Analytics: superpowers/records/phase-4-run-analytics.md
  - Architecture: architecture.md
```

- [ ] **Step 2: Verify site builds locally**

```bash
mkdocs serve
```

Expected: server starts at `http://127.0.0.1:8000`, no errors in terminal. The site will be missing `index.md` and `architecture.md` — that's fine at this step, MkDocs will warn but still serve.

- [ ] **Step 3: Commit**

```bash
git add mkdocs.yml
git commit -m "feat: add mkdocs.yml with Material theme and phase nav"
```

---

### Task 4: Write `docs/index.md`

**Files:**
- Create: `docs/index.md`

- [ ] **Step 1: Create docs/index.md**

```markdown
# Balatrobot

An AI bot for [Balatro](https://store.steampowered.com/app/2379780/Balatro/), built in two parts: a Lua mod that runs inside the game and exposes a UDP API, and a Python client that drives bot logic externally.

## How It Works

Balatro runs with the Steamodded mod loader. The Balatrobot mod listens on a UDP port. Each game tick the Python bot sends `HELLO\n` and receives the full game state as JSON, then sends back an action string (`PLAY_HAND|1,3,4,5`, `BUY_CARD|2`, etc.) which the mod translates into UI interactions.

Bot logic is entirely in Python — subclass `balatrobot.core.bot.Bot`, override the decision methods, and run it against a live game or a cached gamestate snapshot.

## Development Chronicle

This site documents each phase of development: what was built, what was deferred, and what bugs were found along the way.

| Phase | Description |
|---|---|
| [Phase 1](superpowers/records/phase-1-replay-run-history.md) | Replay & run history — action logging, run outcome tracking, replay runner |
| [Phase 2](superpowers/records/phase-2-smarter-flushbot.md) | Smarter FlushBot — flush-first play/discard logic, shop strategy, Checkered Deck |
| [Phase 3](superpowers/records/phase-3-game-mechanics-catalogue.md) | Game mechanics catalogue — typed item data, feature encoder (300-dim float32) |
| [Phase 4](superpowers/records/phase-4-run-analytics.md) | Run analytics — run labelling, best-run capture, failure mode analysis |

## Source

[github.com/ChickpeaMCG/balatrobot](https://github.com/ChickpeaMCG/balatrobot)
```

- [ ] **Step 2: Verify page renders**

```bash
mkdocs serve
```

Open `http://127.0.0.1:8000` — home page should render with the table and intro text. No warnings about missing `index.md`.

- [ ] **Step 3: Commit**

```bash
git add docs/index.md
git commit -m "docs: add index.md project overview page"
```

---

### Task 5: Write `docs/architecture.md`

**Files:**
- Create: `docs/architecture.md`

- [ ] **Step 1: Create docs/architecture.md**

Write the following to `docs/architecture.md`:

````markdown
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
````

- [ ] **Step 2: Verify page renders**

```bash
mkdocs serve
```

Open `http://127.0.0.1:8000/architecture/` — tables and code blocks should render cleanly. Check the nav tab shows "Architecture".

- [ ] **Step 3: Commit**

```bash
git add docs/architecture.md
git commit -m "docs: add architecture.md system overview"
```

---

### Task 6: Create GitHub Actions deploy workflow

**Files:**
- Create: `.github/workflows/docs.yml`

- [ ] **Step 1: Create .github/workflows/ directory and docs.yml**

```yaml
name: Deploy Docs

on:
  push:
    branches: [main]

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -e ".[docs]"

      - name: Build and deploy
        run: mkdocs gh-deploy --force
```

- [ ] **Step 2: Commit and push to main**

```bash
git add .github/workflows/docs.yml
git commit -m "ci: add GitHub Actions workflow to deploy MkDocs on push to main"
git push origin main
```

- [ ] **Step 3: Verify GitHub Actions run**

Go to `https://github.com/ChickpeaMCG/balatrobot/actions` — the "Deploy Docs" workflow should trigger and complete successfully. The `gh-pages` branch will be created by this run.

- [ ] **Step 4: Enable GitHub Pages (one-time manual step)**

Go to: **GitHub repo → Settings → Pages → Source → Deploy from a branch → `gh-pages` / `/ (root)` → Save**

Wait ~1 minute, then open `https://ChickpeaMCG.github.io/balatrobot/` — the site should be live.
