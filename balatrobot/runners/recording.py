import argparse
import json
import subprocess
import time
from pathlib import Path

from balatrobot.bots.flush_bot import FlushBot
from balatrobot.utils.run_history import print_run_summary, record_run

REPLAYS_DIR = Path("replays")


def get_git_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        branch = result.stdout.strip()
        return branch if branch else "unlabelled"
    except Exception:
        return "unlabelled"


class RecordingFlushBot(FlushBot):
    def __init__(self, *args, label: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._label = label

    def _on_run_complete(self, G):
        ante = (G.get("ante") or {}).get("ante") or 0
        blind = (G.get("ante") or {}).get("blinds") or {}
        round_data = G.get("current_round") or {}
        entry = record_run(
            seed=G.get("seed") or self._current_seed,
            deck=self.deck,
            stake=self.stake,
            ante_reached=ante,
            result="loss",
            hands_played=G.get("num_hands_played", 0),
            best_hand="Flush",
            label=self._label,
            final_chips_needed=blind.get("chips_needed"),
            final_chips_scored=G.get("current_chips"),
            final_discards_remaining=round_data.get("discards_left"),
            final_hand_type=getattr(self, "_last_hand_type", None),
        )
        print_run_summary(entry)

        REPLAYS_DIR.mkdir(exist_ok=True)
        safe_ts = entry["timestamp"][:19].replace(":", "-")
        seed_label = G.get("seed") or self._current_seed or "unseeded"
        replay_path = REPLAYS_DIR / f"{seed_label}_{safe_ts}.replay.json"
        replay_path.write_text(json.dumps(self._action_log, indent=2))
        print(f"Replay saved -> {replay_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default=None)
    parser.add_argument("--runs", type=int, default=0,
                        help="Number of runs before exiting (0 = unlimited)")
    parser.add_argument("--label", default=None,
                        help="Label for this batch of runs (default: current git branch)")
    parser.add_argument("--restart", action="store_true",
                        help="Restart Balatro automatically when it exits (default: exit instead)")
    args = parser.parse_args()

    label = args.label or get_git_branch()
    if label in ("main", "master"):
        print(
            f"Warning: running on '{label}' — runs will be labelled '{label}'.\n"
            "  Use --label <name> or switch to a feature branch to group runs by phase."
        )

    bot = RecordingFlushBot(deck="Checkered Deck", stake=1, seed=args.seed, bot_port=12345, label=label, cache_states=True)
    bot.start_balatro_instance()
    print(f"Waiting for game to load... (label: {label})")
    time.sleep(15)

    completed = 0
    try:
        while args.runs == 0 or completed < args.runs:
            bot.run()
            completed += 1

            if not bot._balatro_alive():
                if args.restart and (args.runs == 0 or completed < args.runs):
                    print("Restarting Balatro...")
                    if bot.sock:
                        bot.sock.close()
                    bot.sock = None
                    bot.start_balatro_instance()
                    time.sleep(15)
                else:
                    break

            bot.running = True
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        if bot.sock:
            bot.sock.close()
        bot.stop_balatro_instance()
