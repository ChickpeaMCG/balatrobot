# Phase 5: Documentation Site — Design Spec

**Date:** 2026-04-20
**Branch:** phase-5-docs-site
**Follows:** Phase 4 (run analytics, run labelling, best-run capture)
**Precedes:** Phase 6 (RL groundwork)

---

## Overview

Build a public MkDocs site that chronicles Balatrobot's development across phases. The site auto-deploys to GitHub Pages on every push to `main`. Phase implementation records (`docs/superpowers/records/`) become the phase history pages — no duplicate content. Analytics are explicitly out of scope for this phase.

---

## Scope

| Item | In scope |
|---|---|
| MkDocs + Material theme setup (`mkdocs.yml`) | ✅ |
| `docs/index.md` — project overview page | ✅ |
| `docs/architecture.md` — system overview | ✅ |
| Phase records wired into nav (4 existing records) | ✅ |
| `pyproject.toml` `[docs]` optional dependency | ✅ |
| GitHub Actions auto-deploy on push to `main` | ✅ |
| Analytics page / Chart.js / `export_runs.py` | ❌ deferred |
| `docs/data/runs.json` data pipeline | ❌ deferred |

---

## Site Structure

```
docs/
├── index.md                          ← new
├── architecture.md                   ← new
└── superpowers/
    └── records/
        ├── phase-1-replay-run-history.md     ← existing
        ├── phase-2-smarter-flushbot.md       ← existing
        ├── phase-3-game-mechanics-catalogue.md  ← existing
        └── phase-4-run-analytics.md          ← existing
mkdocs.yml                            ← new (repo root)
site/                                 ← built output, git-ignored
```

Phase records require no changes — they are already docs-ready.

---

## MkDocs Configuration

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

---

## Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
docs = [
    "mkdocs>=1.6",
    "mkdocs-material>=9.5",
]
```

---

## GitHub Actions

`.github/workflows/docs.yml`:

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

GitHub Pages must be configured in repo Settings → Pages → Source: `gh-pages` branch, `/ (root)`. The `gh-pages` branch is created by the first deploy run.

---

## Local Development

```bash
pip install -e ".[docs]"
mkdocs serve        # live reload at localhost:8000
mkdocs build        # build to ./site/
```

---

## Out of Scope

- Analytics page, Chart.js, `export_runs.py`, `docs/data/runs.json` — deferred to a future phase
- Auto-generated run history table — deferred
- API reference (`mkdocstrings`) — not needed
- Video embeds, GIFs, comments — not needed
