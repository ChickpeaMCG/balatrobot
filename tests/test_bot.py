"""
Unit tests for Bot base class constructor and start_balatro_instance.
No game or socket required — subprocess.Popen is mocked.
"""
import argparse
from unittest.mock import MagicMock, patch

from balatrobot.core.bot import Actions, Bot


class DummyBot(Bot):
    def skip_or_select_blind(self, G): return [Actions.SELECT_BLIND]
    def select_cards_from_hand(self, G): return [Actions.PLAY_HAND, [1]]
    def select_shop_action(self, G): return [Actions.END_SHOP]
    def select_booster_action(self, G): return [Actions.SKIP_BOOSTER_PACK]
    def sell_jokers(self, G): return [Actions.SELL_JOKER, []]
    def rearrange_jokers(self, G): return [Actions.REARRANGE_JOKERS, []]
    def use_or_sell_consumables(self, G): return [Actions.USE_CONSUMABLE, []]
    def rearrange_consumables(self, G): return [Actions.REARRANGE_CONSUMABLES, []]
    def rearrange_hand(self, G): return [Actions.REARRANGE_HAND, []]


def test_default_speed_is_fast():
    bot = DummyBot(deck="Blue Deck")
    assert bot.speed == "fast"


def test_speed_stored_from_constructor():
    bot = DummyBot(deck="Blue Deck", speed="watch")
    assert bot.speed == "watch"


def test_default_balatro_path():
    bot = DummyBot(deck="Blue Deck")
    assert "Balatro.exe" in bot.balatro_path


def test_custom_balatro_path_stored():
    custom = r"D:\Games\Balatro\Balatro.exe"
    bot = DummyBot(deck="Blue Deck", balatro_path=custom)
    assert bot.balatro_path == custom


def test_start_balatro_passes_port_and_speed():
    bot = DummyBot(deck="Blue Deck", bot_port=12345, speed="watch")
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock()
        bot.start_balatro_instance()
        cmd = mock_popen.call_args[0][0]
        assert cmd[1] == "12345"
        assert cmd[2] == "watch"


def test_start_balatro_fast_speed():
    bot = DummyBot(deck="Blue Deck", bot_port=12346, speed="fast")
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock()
        bot.start_balatro_instance()
        cmd = mock_popen.call_args[0][0]
        assert cmd[2] == "fast"


def test_start_balatro_uses_custom_path():
    custom = r"D:\Games\Balatro\Balatro.exe"
    bot = DummyBot(deck="Blue Deck", balatro_path=custom)
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock()
        bot.start_balatro_instance()
        cmd = mock_popen.call_args[0][0]
        assert cmd[0] == custom


def test_replay_bot_argparse_defaults_speed_to_watch():
    parser = argparse.ArgumentParser()
    parser.add_argument("replay")
    parser.add_argument("--port", type=int, default=12345)
    parser.add_argument("--speed", default="watch", choices=["fast", "watch"])
    args = parser.parse_args(["some.replay.json"])
    assert args.speed == "watch"


def test_replay_bot_argparse_accepts_fast():
    parser = argparse.ArgumentParser()
    parser.add_argument("replay")
    parser.add_argument("--port", type=int, default=12345)
    parser.add_argument("--speed", default="watch", choices=["fast", "watch"])
    args = parser.parse_args(["some.replay.json", "--speed", "fast"])
    assert args.speed == "fast"
