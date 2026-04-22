"""Tests for Phase 6 FlushBot additions: booster pack purchase, pack open, consumable use."""

import pytest

from balatrobot.bots.flush_bot import FlushBot
from balatrobot.core.bot import Actions


@pytest.fixture(scope="module")
def bot():
    return FlushBot(deck="Checkered Deck", stake=1, seed=None, bot_port=12345)


def _shop_G(
    dollars: int = 10,
    cards: list[dict] | None = None,
    boosters: list[dict] | None = None,
    consumables: list[dict] | None = None,
):
    return {
        "dollars": dollars,
        "shop": {
            "cards": cards or [],
            "boosters": boosters or [],
        },
        "consumables": consumables or [],
    }


# -----------------------------------------------------------------------------
# Shop priority: flush joker > Celestial pack > Buffoon pack > END_SHOP
# -----------------------------------------------------------------------------

class TestShopPriority:
    def test_flush_joker_beats_celestial_pack(self, bot):
        # A flush joker in shop + a Celestial pack → bot buys the joker.
        flush_joker_key = bot.FLUSH_JOKERS[0]
        G = _shop_G(
            dollars=10,
            cards=[{"key": flush_joker_key, "cost": 5}],
            boosters=[{"key": "p_celestial_normal_1", "name": "Celestial Pack", "cost": 4}],
        )
        action = bot.select_shop_action(G)
        assert action[0] == Actions.BUY_CARD
        assert action[1] == [1]

    def test_celestial_pack_bought_when_no_joker_and_no_planet_held(self, bot):
        G = _shop_G(
            dollars=10,
            cards=[],
            boosters=[{"key": "p_celestial_normal_1", "name": "Celestial Pack", "cost": 4}],
            consumables=[],
        )
        action = bot.select_shop_action(G)
        assert action[0] == Actions.BUY_BOOSTER
        assert action[1] == [1]

    def test_celestial_pack_skipped_when_planet_already_held(self, bot):
        # Already have a planet in consumables → don't buy another Celestial.
        G = _shop_G(
            dollars=10,
            cards=[],
            boosters=[{"key": "p_celestial_normal_1", "name": "Celestial Pack", "cost": 4}],
            consumables=[{"key": "c_jupiter"}],
        )
        action = bot.select_shop_action(G)
        assert action[0] == Actions.END_SHOP

    def test_buffoon_pack_bought_when_celestial_blocked(self, bot):
        # Planet held → skip Celestial. Buffoon pack present → buy it.
        G = _shop_G(
            dollars=10,
            cards=[],
            boosters=[
                {"key": "p_celestial_normal_1", "name": "Celestial Pack", "cost": 4},
                {"key": "p_buffoon_normal_1",   "name": "Buffoon Pack",   "cost": 4},
            ],
            consumables=[{"key": "c_mercury"}],
        )
        action = bot.select_shop_action(G)
        assert action[0] == Actions.BUY_BOOSTER
        # Buffoon pack is at index 2 (1-based).
        assert action[1] == [2]

    def test_unaffordable_pack_not_bought(self, bot):
        G = _shop_G(
            dollars=2,
            cards=[],
            boosters=[{"key": "p_celestial_normal_1", "name": "Celestial Pack", "cost": 4}],
        )
        action = bot.select_shop_action(G)
        assert action[0] == Actions.END_SHOP

    def test_arcana_and_spectral_packs_ignored(self, bot):
        G = _shop_G(
            dollars=10,
            cards=[],
            boosters=[
                {"key": "p_arcana_normal_1",   "name": "Arcana Pack",   "cost": 4},
                {"key": "p_spectral_normal_1", "name": "Spectral Pack", "cost": 4},
                {"key": "p_standard_normal_1", "name": "Standard Pack", "cost": 4},
            ],
        )
        action = bot.select_shop_action(G)
        assert action[0] == Actions.END_SHOP
