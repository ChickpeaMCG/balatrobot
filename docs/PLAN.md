# Balatrobot Development Roadmap

## Current State

Phases 1–4 complete. The bot framework runs end-to-end: Lua mod + Python client over UDP, FlushBot strategy with catalogue-driven joker selection, full run history with labelling and best-run capture.

Completed phase records: `docs/superpowers/records/`

---

## Phase 5 — Documentation Site ✅

**Goal:** Public MkDocs site chronicling Balatrobot's development, auto-deployed to GitHub Pages on push to `main`.

- [x] `mkdocs.yml` at repo root — Material theme, dark/red/amber, phase records wired into nav
- [x] `docs/index.md` — project overview
- [x] `docs/architecture.md` — system overview
- [x] `pyproject.toml` `[docs]` optional dependency (`mkdocs-material>=9.5`)
- [x] `.github/workflows/docs.yml` — auto-deploy on push to `main`
- [x] `site/` added to `.gitignore`

Spec: `docs/superpowers/specs/2026-04-20-phase-5-docs-site-design.md`

---

## Phase 6 — RL Groundwork

**Goal:** Replace hand-coded heuristics with a learned policy.

- [ ] `BalatroEnv(gym.Env)` wraps the bot loop; observation = `GamestateEncoder.encode(G)` (300-dim float32)
- [ ] Define action space: `Discrete` over (PLAY_HAND variants, DISCARD_HAND variants)
- [ ] Define reward: +1 per ante cleared, -1 on game over, shaped by chips scored vs chips needed
- [ ] Instrument `Bot` to optionally record `(obs, action, reward)` tuples per step into a replay buffer
- [ ] Train a simple policy with Stable Baselines3 (MlpPolicy, PPO) against the gamestate cache first, then live

---

## Deferred / Ideas

- Analytics page with Chart.js run charts (export_runs.py → docs/data/runs.json)
- Multi-instance parallel training (infrastructure already exists in `benchmark_multi_instance()`)
- Challenge mode runs (fixed seed + challenge for reproducible benchmarking)
- Joker synergy graph (map which joker combinations produce the highest scores)
