# Phase 5: Documentation Site — Implementation Record

**Date:** 2026-04-20
**Branch:** phase-5-docs-site
**Follows:** Phase 4 (run analytics, run labelling, best-run capture)
**Precedes:** Phase 6 (RL groundwork)

---

## Overview

Phase 4 delivered run analytics and a labelling system. Phase 5 ships a public MkDocs site at `https://ChickpeaMCG.github.io/balatrobot/` that chronicles the project's development across phases. The site auto-deploys on every push to `main` via GitHub Actions. Phase implementation records become the phase history pages — no duplicate content.

---

## Scope

| Item | Independent? |
|---|---|
| MkDocs + Material theme (`mkdocs.yml`) | Yes |
| `docs/index.md` — project overview | Yes |
| `docs/architecture.md` — system overview | Yes |
| Phase records wired into nav | Yes |
| `pyproject.toml` `[docs]` optional dependency | Yes |
| GitHub Actions auto-deploy on push to `main` | Yes |
| Analytics page / Chart.js / `export_runs.py` | ❌ deferred |
| `docs/data/runs.json` data pipeline | ❌ deferred |

---

## What Was Planned

- `mkdocs.yml` at repo root with Material theme (dark/slate default, red primary, amber accent)
- `docs/index.md` — project overview, protocol summary, phase table with links
- `docs/architecture.md` — system overview covering protocol, Lua mod files, Python package layout, gamestate structure, and configuration
- `pyproject.toml` `[project.optional-dependencies]` docs group (`mkdocs>=1.6`, `mkdocs-material>=9.5`)
- `.github/workflows/docs.yml` — builds and deploys via `mkdocs gh-deploy --force` on push to `main`
- `site/` added to `.gitignore`
- Planning files (`PLAN.md`, `PLAN_DOCS_SITE.md`, `FORK_AND_CHANGES.md`, `superpowers/specs/`, `superpowers/plans/`) excluded from the built site via `exclude_docs`

---

## What Was Built

All in-scope items implemented as planned. Key details:

- `exclude_docs` block in `mkdocs.yml` keeps planning artifacts out of the public site without moving files
- Phase records required no changes — their existing structure (Overview, Scope, Bugs, Deferred Items) maps directly to what a public audience needs
- GitHub Pages serves from the `gh-pages` branch; the branch is created by the first Actions run

---

## Bugs Found During Implementation

None.

---

## Current State Per Sub-Task

| Sub-task | Status | Notes |
|---|---|---|
| `.gitignore` — add `site/` | ✅ Done | |
| `pyproject.toml` — `[docs]` optional dependency | ✅ Done | |
| `mkdocs.yml` — Material theme, nav, exclude_docs | ✅ Done | |
| `docs/index.md` | ✅ Done | |
| `docs/architecture.md` | ✅ Done | |
| `.github/workflows/docs.yml` | ✅ Done | Triggers on push to `main` |
| Analytics page / Chart.js | ⬜ Deferred indefinitely | See deferred items |

---

## What Is Explicitly Out of Scope

- Analytics page, Chart.js visualisations, `export_runs.py`, `docs/data/runs.json`
- Auto-generated run history table
- API reference (`mkdocstrings`)
- Video embeds, GIFs, comments

---

## Deferred Items

- **Analytics page with Chart.js run charts** — requires `export_runs.py` → `docs/data/runs.json` pipeline. Deferred indefinitely; the static JSON approach is sufficient when this becomes useful, and `PLAN_DOCS_SITE.md` has the full design.
