"""
Offline tests for FlushBot decision logic.

These tests load cached game state snapshots from gamestate_cache/ and verify
bot decisions without needing the game running. To build the cache, run the bot
for at least one full game with FlushBot (it caches every decision point).

Run with:  pytest tests/
"""
import json
import glob
import pytest
from pathlib import Path

from balatrobot.bots.flush_bot import FlushBot
from balatrobot.core.bot import Actions

CACHE_DIR = Path(__file__).parent.parent / "gamestate_cache"


def load_states(phase: str) -> list[dict]:
    files = sorted((CACHE_DIR / phase).glob("*.json"))
    if not files:
        pytest.skip(f"No cached states for '{phase}' — run the bot first to generate them")
    return [json.loads(f.read_text()) for f in files]


@pytest.fixture(scope="module")
def bot():
    return FlushBot(deck="Blue Deck", stake=1, seed=None, bot_port=12345)


# ---------------------------------------------------------------------------
# skip_or_select_blind
# ---------------------------------------------------------------------------

def test_select_blind_always_returns_valid_action(bot):
    for G in load_states("skip_or_select_blind"):
        action = bot.skip_or_select_blind(G)
        assert action[0] in (Actions.SELECT_BLIND, Actions.SKIP_BLIND)


def test_flush_bot_always_selects_blind(bot):
    """FlushBot never skips — it wants to play every round."""
    for G in load_states("skip_or_select_blind"):
        action = bot.skip_or_select_blind(G)
        assert action[0] == Actions.SELECT_BLIND


# ---------------------------------------------------------------------------
# select_cards_from_hand
# ---------------------------------------------------------------------------

def test_play_or_discard_returns_valid_action(bot):
    for G in load_states("select_cards_from_hand"):
        action = bot.select_cards_from_hand(G)
        assert action[0] in (Actions.PLAY_HAND, Actions.DISCARD_HAND)


def test_card_indices_are_in_range(bot):
    for G in load_states("select_cards_from_hand"):
        action = bot.select_cards_from_hand(G)
        hand_size = len(G["hand"])
        for idx in action[1]:
            assert 1 <= idx <= hand_size, f"Card index {idx} out of range for hand size {hand_size}"


def test_no_duplicate_card_indices(bot):
    for G in load_states("select_cards_from_hand"):
        action = bot.select_cards_from_hand(G)
        indices = action[1]
        assert len(indices) == len(set(indices)), f"Duplicate indices: {indices}"


def test_flush_bot_plays_at_most_five_cards(bot):
    for G in load_states("select_cards_from_hand"):
        action = bot.select_cards_from_hand(G)
        if action[0] == Actions.PLAY_HAND:
            assert len(action[1]) <= 5


def test_flush_bot_respects_discard_limit(bot):
    for G in load_states("select_cards_from_hand"):
        action = bot.select_cards_from_hand(G)
        if action[0] == Actions.DISCARD_HAND:
            discards_left = G.get("current_round", {}).get("discards_left", 0)
            assert discards_left > 0, "Bot attempted discard with no discards remaining"


# ---------------------------------------------------------------------------
# select_shop_action
# ---------------------------------------------------------------------------

def test_shop_action_returns_valid_action(bot):
    valid = {Actions.END_SHOP, Actions.REROLL_SHOP, Actions.BUY_CARD,
             Actions.BUY_VOUCHER, Actions.BUY_BOOSTER}
    for G in load_states("select_shop_action"):
        action = bot.select_shop_action(G)
        assert action[0] in valid


def test_flush_bot_always_ends_shop(bot):
    for G in load_states("select_shop_action"):
        action = bot.select_shop_action(G)
        assert action[0] == Actions.END_SHOP


# ---------------------------------------------------------------------------
# Game state schema validation (verifies utils.lua is populating fields)
# ---------------------------------------------------------------------------

def test_hand_state_has_required_fields():
    for G in load_states("select_cards_from_hand"):
        assert "hand" in G
        assert len(G["hand"]) > 0
        card = G["hand"][0]
        for field in ("name", "suit", "value", "card_key"):
            assert field in card, f"Card missing field '{field}': {card}"


def test_round_state_has_hands_and_discards_left():
    for G in load_states("select_cards_from_hand"):
        cr = G.get("current_round", {})
        assert "hands_left" in cr, "current_round missing hands_left"
        assert "discards_left" in cr, "current_round missing discards_left"


def test_blind_has_chips_needed():
    for G in load_states("skip_or_select_blind"):
        blind = G.get("ante", {}).get("blinds", {})
        assert "chips_needed" in blind, "blind missing chips_needed"


def test_handscores_populated():
    for G in load_states("select_cards_from_hand"):
        assert "handscores" in G
        assert len(G["handscores"]) > 0, "handscores is empty — check getHandScoreData() in utils.lua"
        # Verify structure of at least one entry
        hand = next(iter(G["handscores"].values()))
        for field in ("level", "chips", "mult"):
            assert field in hand, f"handscore entry missing '{field}'"


def test_jokers_have_name_and_key():
    for G in load_states("sell_jokers"):
        for joker in G.get("jokers", []):
            assert "name" in joker, f"Joker missing 'name': {joker}"
            assert "key" in joker, f"Joker missing 'key': {joker}"
