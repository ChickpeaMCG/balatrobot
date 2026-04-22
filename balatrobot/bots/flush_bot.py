
from balatrobot.core.bot import Actions, Bot
from balatrobot.data.catalogue import all_jokers, get_planet

CARD_CHIPS = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "Jack": 10, "Queen": 10, "King": 10, "Ace": 11,
}

# Derived from catalogue: jokers with flush_synergy >= 0.7, ordered by synergy descending.
# Previously this list was hardcoded with two incorrect keys (j_flush, j_4_fingers) that
# don't exist in the game — the shop strategy never triggered as a result.
_FLUSH_JOKERS = [
    j.key
    for j in sorted(all_jokers(), key=lambda j: j.flush_synergy, reverse=True)
    if j.flush_synergy >= 0.7
]


def _card_key(card: dict) -> str | None:
    """Extract the catalogue key from a card dict.

    Cards from shop/pack/consumables use either a top-level `key` field or
    nest it under `config.center.key` (per utils.lua:186). Handle both.
    """
    if not isinstance(card, dict):
        return None
    if "key" in card and card["key"]:
        return card["key"]
    center = (card.get("config") or {}).get("center") or {}
    return center.get("key")


def _is_planet_key(key: str | None) -> bool:
    """True if the key matches a known planet in the catalogue."""
    if not key:
        return False
    return get_planet(key) is not None


class FlushBot(Bot):
    FLUSH_JOKERS = _FLUSH_JOKERS
    SKIP_TAGS = {"tag_double", "tag_economy", "tag_voucher", "tag_coupon"}

    def skip_or_select_blind(self, G):
        # Always select — skip logic deferred until offered tags are exposed in gamestate.
        # G["tags"] = already-collected tags, not the tag currently on offer for skipping.
        return [Actions.SELECT_BLIND]

    def select_cards_from_hand(self, G):
        hand = G["hand"]
        hands_left = G["current_round"]["hands_left"]
        discards_left = G["current_round"]["discards_left"]

        suit_indices: dict[str, list[int]] = {}
        for i, card in enumerate(hand):
            suit = card.get("suit") or "Unknown"
            suit_indices.setdefault(suit, []).append(i)

        most_common_suit = max(suit_indices, key=lambda s: len(suit_indices[s]))

        # Already beaten the chip requirement — stop fishing, play best available
        current_chips = G.get("current_chips", 0)
        chips_needed = G["ante"]["blinds"]["chips_needed"]
        if current_chips > 0 and current_chips >= chips_needed:
            best_cards = sorted(
                suit_indices[most_common_suit], key=lambda i: hand[i]["value"], reverse=True
            )[:5]
            self._last_hand_type = "Other"
            return [Actions.PLAY_HAND, [i + 1 for i in best_cards]]

        # If we have a flush, always play it — scores accumulate across hands
        if len(suit_indices[most_common_suit]) >= 5:
            suit_cards = sorted(
                [(i, hand[i]) for i in suit_indices[most_common_suit]],
                key=lambda x: x[1]["value"],
                reverse=True,
            )
            self._last_hand_type = "Flush"
            return [Actions.PLAY_HAND, [i + 1 for i, _ in suit_cards[:5]]]

        # No flush — discard off-suit cards to fish for one
        off_suit_indices = [
            i for s, idxs in suit_indices.items() if s != most_common_suit for i in idxs
        ][:5]
        if off_suit_indices and discards_left > 0 and hands_left > 1:
            return [Actions.DISCARD_HAND, [i + 1 for i in off_suit_indices]]

        # Forced play — no flush and no discards (or last hand)
        forced_indices = sorted(
            suit_indices[most_common_suit], key=lambda i: hand[i]["value"], reverse=True
        )[:5]
        if not forced_indices:
            forced_indices = list(range(min(5, len(hand))))
        self._last_hand_type = "Other"
        return [Actions.PLAY_HAND, [i + 1 for i in forced_indices]]

    def _should_play(self, cards: list[dict], hand_name: str, G: dict) -> bool:
        """Estimate whether expected score meets the remaining chip deficit. Reserved for future use."""
        if G["current_round"]["hands_left"] == 1:
            return True
        score_data = G.get("handscores", {}).get(hand_name, {})
        hand_chips = score_data.get("chips", 0)
        mult = score_data.get("mult", 1)
        card_chips = sum(CARD_CHIPS.get(str(c["value"]), 0) for c in cards)
        expected = (hand_chips + card_chips) * mult
        chips_needed = G["ante"]["blinds"]["chips_needed"]
        deficit = chips_needed - G.get("current_chips", 0)
        return expected >= deficit

    def select_shop_action(self, G):
        dollars = G["dollars"]
        shop_cards = G.get("shop", {}).get("cards", [])
        shop_boosters = G.get("shop", {}).get("boosters", [])

        # Priority 1: flush-synergy joker
        for priority_key in self.FLUSH_JOKERS:
            for idx, card in enumerate(shop_cards):
                if card.get("key") == priority_key and card.get("cost", 999) <= dollars:
                    return [Actions.BUY_CARD, [idx + 1]]

        # Priority 2: Celestial pack (only if no planet already waiting in consumables)
        consumables = G.get("consumables", []) or []
        has_planet = any(_is_planet_key(_card_key(c)) for c in consumables)
        if not has_planet:
            for idx, pack in enumerate(shop_boosters):
                name = pack.get("name", "")
                if "Celestial" in name and pack.get("cost", 999) <= dollars:
                    return [Actions.BUY_BOOSTER, [idx + 1]]

        # Priority 3: Buffoon pack
        for idx, pack in enumerate(shop_boosters):
            name = pack.get("name", "")
            if "Buffoon" in name and pack.get("cost", 999) <= dollars:
                return [Actions.BUY_BOOSTER, [idx + 1]]

        return [Actions.END_SHOP]

    def select_booster_action(self, G):
        return [Actions.SKIP_BOOSTER_PACK]

    def sell_jokers(self, G):
        if len(G["jokers"]) > 1:
            return [Actions.SELL_JOKER, [2]]
        return [Actions.SELL_JOKER, []]

    def rearrange_jokers(self, G):
        return [Actions.REARRANGE_JOKERS, []]

    def use_or_sell_consumables(self, G):
        return [Actions.USE_CONSUMABLE, []]

    def rearrange_consumables(self, G):
        return [Actions.REARRANGE_CONSUMABLES, []]

    def rearrange_hand(self, G):
        return [Actions.REARRANGE_HAND, []]
