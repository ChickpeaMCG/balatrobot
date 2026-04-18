import argparse
import json
import time
from pathlib import Path

from balatrobot.bots.flush_bot import FlushBot
from balatrobot.utils.run_history import print_run_summary, record_run

REPLAYS_DIR = Path("replays")


class RecordingFlushBot(FlushBot):
    def _on_run_complete(self, G):
        ante = (G.get("ante") or {}).get("ante") or 0
        entry = record_run(
            seed=G.get("seed") or self._current_seed,
            deck=self.deck,
            stake=self.stake,
            ante_reached=ante,
            result="loss",
            hands_played=G.get("num_hands_played", 0),
            best_hand="Flush",
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
    args = parser.parse_args()

    bot = RecordingFlushBot(deck="Blue Deck", stake=1, seed=args.seed, bot_port=12345)
    bot.start_balatro_instance()
    print("Waiting for game to load...")
    time.sleep(15)

    completed = 0
    try:
        while args.runs == 0 or completed < args.runs:
            bot.run()
            completed += 1
            bot.running = True  # reset for next game
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        if bot.sock:
            bot.sock.close()
        bot.stop_balatro_instance()
