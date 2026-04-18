"""Analyse run_history.json and print a summary to stdout."""
import json
from collections import Counter
from pathlib import Path

HISTORY_FILE = Path("run_history.json")


def analyse(history_path: Path = HISTORY_FILE) -> None:
    if not history_path.exists():
        print("No run_history.json found — run the bot first.")
        return

    data = json.loads(history_path.read_text())
    runs = data.get("runs", [])
    if not runs:
        print("No runs recorded yet.")
        return

    total = len(runs)
    wins = sum(1 for r in runs if r.get("result") == "win")
    antes = [r.get("ante_reached", 0) for r in runs]
    avg_ante = sum(antes) / total
    exit_counter = Counter(antes)

    best_idx = data.get("best_run")
    best = runs[best_idx] if best_idx is not None else max(runs, key=lambda r: r.get("ante_reached", 0))

    print(f"Runs: {total}  |  Wins: {wins} ({wins/total*100:.0f}%)  |  Avg ante: {avg_ante:.1f}")
    print(f"Exit ante distribution: {dict(sorted(exit_counter.items()))}")
    print(f"Best run: Ante {best['ante_reached']} | {best['hands_played']} hands | seed={best['seed']}")

    # Per-ante breakdown
    print("\nAnte | Count | %")
    for ante in sorted(exit_counter):
        count = exit_counter[ante]
        print(f"  {ante}  |  {count:4d}  | {count/total*100:5.1f}%")


if __name__ == "__main__":
    analyse()
