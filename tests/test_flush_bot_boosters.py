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


# -----------------------------------------------------------------------------
# Booster pack card selection
# -----------------------------------------------------------------------------

def _booster_G(pack_cards: list[dict]) -> dict:
    return {"pack_cards": pack_cards}


class TestSelectBoosterAction:
    def test_celestial_pack_selects_jupiter_when_present(self, bot):
        # Jupiter is at index 1 (0-based) → should return 1-based index 2
        G = _booster_G([
            {"key": "c_saturn", "name": "Saturn"},
            {"key": "c_jupiter", "name": "Jupiter"},
            {"key": "c_mars", "name": "Mars"},
        ])
        action = bot.select_booster_action(G)
        assert action[0] == Actions.SELECT_BOOSTER_CARD
        assert action[1] == [2]
        assert action[2] == []

    def test_celestial_pack_selects_first_when_no_jupiter(self, bot):
        G = _booster_G([
            {"key": "c_saturn", "name": "Saturn"},
            {"key": "c_mars", "name": "Mars"},
            {"key": "c_neptune", "name": "Neptune"},
        ])
        action = bot.select_booster_action(G)
        assert action[0] == Actions.SELECT_BOOSTER_CARD
        assert action[1] == [1]
        assert action[2] == []

    def test_buffoon_pack_selects_flush_joker(self, bot):
        flush_key = bot.FLUSH_JOKERS[0]
        G = _booster_G([
            {"key": "j_some_other_joker", "name": "Other Joker"},
            {"key": flush_key, "name": "Flush Joker"},
            {"key": "j_another_joker", "name": "Another Joker"},
        ])
        action = bot.select_booster_action(G)
        assert action[0] == Actions.SELECT_BOOSTER_CARD
        assert action[1] == [2]
        assert action[2] == []

    def test_buffoon_pack_skips_when_no_flush_joker(self, bot):
        G = _booster_G([
            {"key": "j_some_joker", "name": "Some Joker"},
            {"key": "j_another_joker", "name": "Another Joker"},
        ])
        action = bot.select_booster_action(G)
        assert action[0] == Actions.SKIP_BOOSTER_PACK

    def test_empty_pack_cards_skips(self, bot):
        G = _booster_G([])
        action = bot.select_booster_action(G)
        assert action[0] == Actions.SKIP_BOOSTER_PACK

    def test_arcana_pack_card_skips(self, bot):
        # c_fool is an Arcana card — neither planet nor joker key
        G = _booster_G([
            {"key": "c_fool", "name": "The Fool"},
            {"key": "c_magician", "name": "The Magician"},
        ])
        action = bot.select_booster_action(G)
        assert action[0] == Actions.SKIP_BOOSTER_PACK


# -----------------------------------------------------------------------------
# Consumable use: prefer Jupiter, otherwise first planet, else no-op
# -----------------------------------------------------------------------------

def _consumable_G(consumables: list[dict]) -> dict:
    return {"consumables": consumables}


class TestUseOrSellConsumables:
    def test_single_jupiter_uses_slot_1(self, bot):
        G = _consumable_G([{"key": "c_jupiter"}])
        action = bot.use_or_sell_consumables(G)
        assert action == [Actions.USE_CONSUMABLE, [1]]

    def test_jupiter_at_index_1_returns_slot_2(self, bot):
        G = _consumable_G([{"key": "c_mercury"}, {"key": "c_jupiter"}])
        action = bot.use_or_sell_consumables(G)
        assert action == [Actions.USE_CONSUMABLE, [2]]

    def test_planet_no_jupiter_uses_first_planet(self, bot):
        G = _consumable_G([{"key": "c_mercury"}])
        action = bot.use_or_sell_consumables(G)
        assert action == [Actions.USE_CONSUMABLE, [1]]

    def test_tarot_only_is_noop(self, bot):
        G = _consumable_G([{"key": "c_fool"}])
        action = bot.use_or_sell_consumables(G)
        assert action == [Actions.USE_CONSUMABLE, []]

    def test_empty_consumables_is_noop(self, bot):
        G = _consumable_G([])
        action = bot.use_or_sell_consumables(G)
        assert action == [Actions.USE_CONSUMABLE, []]

    def test_interleaved_non_planet_and_jupiter_uses_jupiter(self, bot):
        # Non-planet at index 0, planet at index 1, Jupiter at index 2 → 1-based slot 3
        G = _consumable_G([{"key": "c_fool"}, {"key": "c_mercury"}, {"key": "c_jupiter"}])
        action = bot.use_or_sell_consumables(G)
        assert action == [Actions.USE_CONSUMABLE, [3]]
