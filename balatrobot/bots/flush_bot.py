
from balatrobot.core.bot import Actions, Bot


# Plays flushes if possible
# otherwise keeps the most common suit
# Discarding the rest, or playing the rest if there are no discards left
class FlushBot(Bot):

    def skip_or_select_blind(self, G):
        return [Actions.SELECT_BLIND]

    def select_cards_from_hand(self, G):
        suit_count = {
            "Hearts": 0,
            "Diamonds": 0,
            "Clubs": 0,
            "Spades": 0,
        }
        for card in G["hand"]:
            suit_count[card["suit"]] += 1

        most_common_suit = max(suit_count, key=suit_count.get)
        most_common_suit_count = suit_count[most_common_suit]
        if most_common_suit_count >= 5:
            flush_cards = []
            for card in G["hand"]:
                if card["suit"] == most_common_suit:
                    flush_cards.append(card)
            flush_cards.sort(key=lambda x: x["value"], reverse=True)
            return [
                Actions.PLAY_HAND,
                [G["hand"].index(card) + 1 for card in flush_cards[:5]],
            ]

        # We don't have a flush, so we discard up to 5 cards that are not of the most common suit
        discards = []
        for card in G["hand"]:
            if card["suit"] != most_common_suit:
                discards.append(card)
        discards.sort(key=lambda x: x["value"], reverse=True)
        discards = discards[:5]
        if len(discards) > 0:
            if G["current_round"]["discards_left"] > 0:
                action = Actions.DISCARD_HAND
            else:
                action = Actions.PLAY_HAND
            return [action, [G["hand"].index(card) + 1 for card in discards]]

        print(
            "Somehow don't have a flush, but also don't have any cards to discard. Playing the first card"
        )
        return [Actions.PLAY_HAND, [1]]

    def select_shop_action(self, G):
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
