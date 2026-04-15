import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_FILE = Path("run_history.json")


def load_history() -> dict:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return {"best_run": None, "runs": []}


def record_run(seed, deck, stake, ante_reached, result, hands_played, best_hand) -> dict:
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
    history["runs"].append(entry)
    best = history.get("best_run")
    if best is None or ante_reached > history["runs"][best]["ante_reached"]:
        history["best_run"] = len(history["runs"]) - 1
    HISTORY_FILE.write_text(json.dumps(history, indent=2))
    return entry


def print_run_summary(entry: dict) -> None:
    print(
        f"Run complete — Ante {entry['ante_reached']} | "
        f"{entry['hands_played']} hands | {entry['result']} | "
        f"seed={entry['seed']}"
    )
