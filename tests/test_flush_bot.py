"""
Offline tests for FlushBot decision logic.

These tests load cached game state snapshots from gamestate_cache/ and verify
bot decisions without needing the game running. To build the cache, run the bot
for at least one full game with FlushBot (it caches every decision point).

Run with:  pytest tests/
"""
import json
from pathlib import Path

import pytest

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


# --- unit tests with mock G dicts (no game required) ---

def _blind_G(boss=False, tags=None):
    return {
        "ante": {"blinds": {"boss": boss, "chips_needed": 300}},
        "tags": [{"key": k, "name": k} for k in (tags or [])],
        "current_chips": 0,
    }


def test_select_blind_boss_always_selects(bot):
    G = _blind_G(boss=True, tags=["tag_double"])
    assert bot.skip_or_select_blind(G)[0] == Actions.SELECT_BLIND


def test_skip_blind_on_good_tag(bot):
    # Skip logic deferred — G["tags"] = already-collected tags, not the offered skip tag.
    # Bot always selects until offered tags are exposed in gamestate.
    G = _blind_G(boss=False, tags=["tag_double"])
    assert bot.skip_or_select_blind(G)[0] == Actions.SELECT_BLIND


def test_select_blind_no_useful_tag(bot):
    G = _blind_G(boss=False, tags=["tag_unknown"])
    assert bot.skip_or_select_blind(G)[0] == Actions.SELECT_BLIND


def test_select_blind_no_tags(bot):
    G = _blind_G(boss=False, tags=[])
    assert bot.skip_or_select_blind(G)[0] == Actions.SELECT_BLIND


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


# --- unit tests with mock G dicts (no game required) ---

def _shop_G(cards, dollars=20):
    return {"shop": {"cards": cards}, "dollars": dollars}


def test_shop_buys_priority_joker(bot):
    G = _shop_G([{"key": "j_flush", "cost": 5, "name": "Flush"}])
    action = bot.select_shop_action(G)
    assert action[0] == Actions.BUY_CARD
    assert action[1] == [1]


def test_shop_respects_priority_order(bot):
    # j_4_fingers is higher priority than j_flush
    G = _shop_G([
        {"key": "j_flush", "cost": 5, "name": "Flush"},
        {"key": "j_4_fingers", "cost": 5, "name": "4 Fingers"},
    ])
    action = bot.select_shop_action(G)
    assert action[0] == Actions.BUY_CARD
    assert action[1] == [2]  # j_4_fingers is at index 2 (1-based)


def test_shop_skips_unaffordable_joker(bot):
    G = _shop_G([{"key": "j_flush", "cost": 50, "name": "Flush"}], dollars=5)
    assert bot.select_shop_action(G)[0] == Actions.END_SHOP


def test_shop_ends_no_priority_joker(bot):
    G = _shop_G([{"key": "j_some_other", "cost": 4, "name": "Other"}])
    assert bot.select_shop_action(G)[0] == Actions.END_SHOP


def test_shop_ends_empty(bot):
    G = _shop_G([])
    assert bot.select_shop_action(G)[0] == Actions.END_SHOP


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


def test_gamestate_includes_seed():
    for G in load_states("select_cards_from_hand"):
        assert "seed" in G, "seed missing from gamestate — check getGameData() in utils.lua"
        assert isinstance(G["seed"], str) and len(G["seed"]) > 0, f"seed is empty or wrong type: {G.get('seed')!r}"


def test_gamestate_includes_current_chips():
    for G in load_states("select_cards_from_hand"):
        assert "current_chips" in G, "current_chips missing — add it to getGameData() in utils.lua"
        assert isinstance(G["current_chips"], (int, float))


# ---------------------------------------------------------------------------
# select_cards_from_hand — play/discard logic (mock G dicts)
# ---------------------------------------------------------------------------

def _hand_G(suits, hands_left=3, discards_left=3, chips_needed=300, current_chips=0):
    hand = [
        {"suit": s, "value": v, "name": f"{v} of {s}", "card_key": f"{s[0]}{v}"}
        for s, v in suits
    ]
    return {
        "hand": hand,
        "current_round": {"hands_left": hands_left, "discards_left": discards_left},
        "ante": {"blinds": {"chips_needed": chips_needed, "boss": False}},
        "current_chips": current_chips,
        "handscores": {
            "Flush": {"chips": 35, "mult": 4, "level": 1, "order": 6},
            "High Card": {"chips": 5, "mult": 1, "level": 1, "order": 1},
        },
        "tags": [],
        "dollars": 10,
        "shop": {"cards": []},
    }


def test_plays_flush_when_score_meets_target(bot):
    # 5 hearts; expected flush score well above 300 deficit
    suits = [("Hearts", v) for v in [2, 4, 6, 8, 10]] + [("Spades", 3), ("Clubs", 5)]
    G = _hand_G(suits, chips_needed=50, current_chips=0)
    action = bot.select_cards_from_hand(G)
    assert action[0] == Actions.PLAY_HAND


def test_discards_when_below_target_and_discards_remain(bot):
    # 3 hearts, 4 spades — no flush, score will be low, discards available
    suits = [("Hearts", v) for v in [2, 3, 4]] + [("Spades", v) for v in [5, 6, 7, 8]]
    G = _hand_G(suits, chips_needed=9999, current_chips=0, discards_left=3)
    action = bot.select_cards_from_hand(G)
    assert action[0] == Actions.DISCARD_HAND


def test_plays_on_last_hand_regardless_of_score(bot):
    suits = [("Hearts", v) for v in [2, 3, 4]] + [("Spades", v) for v in [5, 6, 7, 8]]
    G = _hand_G(suits, hands_left=1, chips_needed=9999, current_chips=0)
    action = bot.select_cards_from_hand(G)
    assert action[0] == Actions.PLAY_HAND


def test_plays_when_no_discards_left(bot):
    suits = [("Hearts", v) for v in [2, 3, 4]] + [("Spades", v) for v in [5, 6, 7, 8]]
    G = _hand_G(suits, chips_needed=9999, current_chips=0, discards_left=0)
    action = bot.select_cards_from_hand(G)
    assert action[0] == Actions.PLAY_HAND
