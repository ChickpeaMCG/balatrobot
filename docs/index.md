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
| [Phase 5](superpowers/records/phase-5-docs-site.md) | Documentation site — MkDocs + Material theme, GitHub Pages auto-deploy |

## Source

[github.com/ChickpeaMCG/balatrobot](https://github.com/ChickpeaMCG/balatrobot)
