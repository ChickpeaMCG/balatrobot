import argparse
import json
import time
from pathlib import Path

from bot import Bot


class ReplayBot(Bot):
    def __init__(self, replay_path: str, **kwargs):
        super().__init__(**kwargs)
        entries = json.loads(Path(replay_path).read_text())
        self._replay_actions = [e["action"] for e in entries]
        self._replay_idx = 0

    def run_step(self):
        if self.sock is None:
            import socket
            self.running = True
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(1)
            self.sock.connect(self.addr)

        if not self.running:
            return

        G = self._recv_gamestate()
        if G is None:
            return

        if self._replay_idx >= len(self._replay_actions):
            print("Replay complete.")
            self.running = False
            return

        action_str = self._replay_actions[self._replay_idx]
        self._replay_idx += 1
        self._send_action(action_str)

    # Stubs — not called during replay
    def skip_or_select_blind(self, G): pass
    def select_cards_from_hand(self, G): pass
    def select_shop_action(self, G): pass
    def select_booster_action(self, G): pass
    def sell_jokers(self, G): pass
    def rearrange_jokers(self, G): pass
    def use_or_sell_consumables(self, G): pass
    def rearrange_consumables(self, G): pass
    def rearrange_hand(self, G): pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("replay", help="Path to .replay.json file")
    parser.add_argument("--port", type=int, default=12345)
    args = parser.parse_args()

    bot = ReplayBot(
        replay_path=args.replay,
        deck="Blue Deck",
        stake=1,
        seed=None,
        bot_port=args.port,
    )
    bot.start_balatro_instance()
    print("Waiting for game to load...")
    time.sleep(15)

    try:
        bot.run()
    except KeyboardInterrupt:
        pass
    finally:
        if bot.sock:
            bot.sock.close()
        bot.stop_balatro_instance()
