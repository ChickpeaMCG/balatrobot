Read `run_history.json` if it exists and print a summary of bot performance across all recorded runs.

Include:
- Total runs completed
- Win rate (runs that reached ante 8) if any, otherwise distribution of ante reached (e.g. "Ante 1: 50%, Ante 2: 45%, Ante 4: 5%")
- Average ante reached
- Best run (highest ante, with seed and deck)
- Most recent 5 runs (ante, result, seed)

If `run_history.json` doesn't exist, say so and suggest running `python run_flush_bot.py` to record some runs first.

Keep the output concise — this is a quick status check, not a full analysis.
