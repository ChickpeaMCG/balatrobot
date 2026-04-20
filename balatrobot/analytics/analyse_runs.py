"""Analyse run_history.json and print a summary to stdout."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from balatrobot.runners.recording import get_git_branch
from balatrobot.utils.run_history import (
    best_run_for_label,
    format_best_run_markdown,
    runs_for_label,
)

HISTORY_FILE = Path("run_history.json")


def analyse(history_path: Path = HISTORY_FILE, label: str | None = None, doc: str | None = None) -> None:
    if not history_path.exists():
        print("No run_history.json found — run the bot first.")
        return

    data = json.loads(history_path.read_text())
    all_runs = data.get("runs", [])
    if not all_runs:
        print("No runs recorded yet.")
        return

    runs = runs_for_label(data, label) if label else all_runs

    if label and not runs:
        print(f"No runs found for label '{label}'.", file=sys.stderr)
        sys.exit(1)

    total = len(runs)
    wins = sum(1 for r in runs if r.get("result") == "win")
    antes = [r.get("ante_reached", 0) for r in runs]
    avg_ante = sum(antes) / total
    exit_counter = Counter(antes)

    if label:
        best = best_run_for_label(data, label)
    else:
        best_idx = data.get("best_run")
        best = all_runs[best_idx] if best_idx is not None else max(all_runs, key=lambda r: r.get("ante_reached", 0))
    assert best is not None  # guaranteed: runs is non-empty and best_run_for_label only returns None on empty

    label_display = f" [{label}]" if label else ""
    print(f"Runs: {total}{label_display}  |  Wins: {wins} ({wins/total*100:.0f}%)  |  Avg ante: {avg_ante:.1f}")
    print(f"Exit ante distribution: {dict(sorted(exit_counter.items()))}")
    print(f"Best run: Ante {best['ante_reached']} | {best['hands_played']} hands | seed={best['seed']}")

    # Per-ante breakdown
    print("\nAnte | Count | %")
    for ante in sorted(exit_counter):
        count = exit_counter[ante]
        print(f"  {ante}  |  {count:4d}  | {count/total*100:5.1f}%")

    if doc and best and label:
        md = format_best_run_markdown(label, best, total)
        doc_path = Path(doc)
        with doc_path.open("a", encoding="utf-8") as f:
            f.write(f"\n\n{md}\n")
        print(f"\nBest-run summary appended to {doc_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyse balatrobot run history.")
    parser.add_argument("--label", default=None,
                        help="Filter to runs with this label (default: current git branch)")
    parser.add_argument("--doc", default=None, metavar="PATH",
                        help="Append best-run markdown block to this file; uses current git branch as label if --label is omitted")
    args = parser.parse_args()

    label = args.label or (get_git_branch() if args.doc else None)
    analyse(label=label, doc=args.doc)
