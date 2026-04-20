import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_FILE = Path("run_history.json")


def load_history() -> dict:
    try:
        return json.loads(HISTORY_FILE.read_text())
    except FileNotFoundError:
        return {"best_run": None, "runs": []}


def record_run(
    seed, deck, stake, ante_reached, result, hands_played, best_hand,
    label: str | None = None,
    final_chips_needed: int | None = None,
    final_chips_scored: int | None = None,
    final_discards_remaining: int | None = None,
    final_hand_type: str | None = None,
) -> dict:
    history = load_history()
    entry = {
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


def runs_for_label(history: dict, label: str) -> list[dict]:
    return [r for r in history.get("runs", []) if r.get("label") == label]


def best_run_for_label(history: dict, label: str) -> dict | None:
    candidates = runs_for_label(history, label)
    if not candidates:
        return None
    return max(candidates, key=lambda r: (r.get("ante_reached", 0), r.get("hands_played", 0)))


def format_best_run_markdown(label: str, entry: dict, total_runs: int) -> str:
    seed = entry.get("seed", "unknown")
    replay_path = next(
        (str(m) for m in Path("replays").glob(f"{seed}_*.replay.json")),
        None,
    )
    replay_row = f"| Replay | `{replay_path}` |" if replay_path else "| Replay | *(not saved)* |"
    return (
        f"## Best Run — {label} ({total_runs} runs)\n\n"
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| Ante reached | {entry.get('ante_reached', 0)} |\n"
        f"| Hands played | {entry.get('hands_played', 0)} |\n"
        f"| Seed | `{seed}` |\n"
        f"| Deck | {entry.get('deck', 'unknown')} |\n"
        f"| Stake | {entry.get('stake', 1)} |\n"
        f"{replay_row}"
    )


def print_run_summary(entry: dict) -> None:
    print(
        f"Run complete — Ante {entry['ante_reached']} | "
        f"{entry['hands_played']} hands | {entry['result']} | "
        f"seed={entry['seed']}"
    )
