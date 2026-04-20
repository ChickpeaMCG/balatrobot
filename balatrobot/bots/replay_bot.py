import json
import socket
from pathlib import Path

from balatrobot.core.bot import Bot, State


class ReplayBot(Bot):
    def __init__(self, replay_path: str, **kwargs):
        super().__init__(**kwargs)
        entries = json.loads(Path(replay_path).read_text())
        self._replay_actions = [e["action"] for e in entries]
        self._replay_idx = 0

    def run_step(self):
        if self.sock is None:
            self.running = True
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(1)
            self.sock.connect(self.addr)

        if not self.running:
            return

        G = self._recv_gamestate()
        if G is None:
            return

        if G.get("state") == State.GAME_OVER.value:
            print("Replay complete.")
            self.running = False
            return

        if not G.get("waitingForAction"):
            return

        if self._replay_idx >= len(self._replay_actions):
            print("Replay complete.")
            self.running = False
            return

        action_str = self._replay_actions[self._replay_idx]
        self._replay_idx += 1
        self.sendcmd(action_str)

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
