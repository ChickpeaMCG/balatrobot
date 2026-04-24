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

## Phase 6 — Booster Pack & Planet Consumable Use 🔧

**Branch:** `phase-6-boosters`
**Goal:** Buy Celestial/Buffoon packs in the shop, open them intelligently (Jupiter-first for Celestial, flush-joker-first for Buffoon), and use planet consumables immediately to level Flush.

Spec: `docs/superpowers/specs/2026-04-22-phase-6-booster-pack-consumable-use-design.md`

- [x] **6a** — Planet catalogue: `planets.json` + `PlanetData` + `catalogue.py` (get_planet, planet_for_hand)
- [x] **6b** — Shop: buy Celestial & Buffoon packs (priority: flush joker > Celestial pack > Buffoon pack > END_SHOP)
- [x] **6.infra** — Middleware: pack→shop transition fixed (SHOP-wait `firewhenready`, SMODS_BOOSTER_OPENED=999 added to all `isvalid` checks, skip-path bypasses `pack_choices` loop)
- [x] **6.tools** — Debug tooling: `tail_log.py`, auto-timeout (30s stuck kills + restarts Balatro), `debug-balatro` skill
- [x] **6c** — `select_booster_action`: Jupiter-first for Celestial, flush-joker-first for Buffoon
- [x] **6d** — `use_or_sell_consumables`: use planet consumables immediately (Jupiter preferred)
- [ ] **6e** — A/B benchmark: 30 runs `phase-6-boosters` vs 30 runs `phase-5-baseline`, ≥30% improvement in ante-3 reach

---

## Phase 7 — RL Groundwork *(deferred)*

**Goal:** Replace hand-coded heuristics with a learned policy.

- [ ] `BalatroEnv(gym.Env)` wraps the bot loop; observation = `GamestateEncoder.encode(G)` (300-dim float32)
- [ ] Define action space: `Discrete` over (PLAY_HAND variants, DISCARD_HAND variants)
- [ ] Define reward: +1 ante cleared, -1 game over, shaped by chips scored vs chips needed
- [ ] Instrument `Bot` to record `(obs, action, reward)` tuples into a replay buffer
- [ ] Train a simple policy with Stable Baselines3 (MlpPolicy, PPO) against gamestate cache first, then live

---

## Deferred / Ideas

- Analytics page with Chart.js run charts (export_runs.py → docs/data/runs.json)
- Multi-instance parallel training (infrastructure already exists in `benchmark_multi_instance()`)
- Challenge mode runs (fixed seed + challenge for reproducible benchmarking)
- Joker synergy graph (map which joker combinations produce the highest scores)
