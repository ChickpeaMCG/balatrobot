from balatrobot.data.models import EffectType

SUITS = ["Spades", "Hearts", "Diamonds", "Clubs"]

VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King", "Ace"]

HAND_TYPES = [
    "High Card",
    "Pair",
    "Two Pair",
    "Three of a Kind",
    "Straight",
    "Flush",
    "Full House",
    "Four of a Kind",
    "Straight Flush",
    "Royal Flush",
    "Five of a Kind",
    "Flush House",
    "Flush Five",
]

ENHANCEMENT_KEYS = [
    "Default Base",
    "Bonus",
    "Mult",
    "Wild",
    "Glass",
    "Steel",
    "Stone",
    "Gold",
    "Lucky",
]

EFFECT_TYPES = [e.value for e in EffectType]

EDITION_ENCODING = {
    "foil": 0.25,
    "holographic": 0.5,
    "polychrome": 0.75,
    "negative": 1.0,
}

SEAL_KEYS = ["Gold", "Red", "Blue", "Purple"]

MAX_HAND = 8
MAX_JOKERS = 5
MAX_CONSUMABLES = 2

# Dims per slot
_CARD_DIMS = len(SUITS) + 1 + len(ENHANCEMENT_KEYS) + 1 + len(SEAL_KEYS)  # 4+1+9+1+4 = 19
_JOKER_DIMS = len(EFFECT_TYPES) + 1 + 1 + 1 + 1 + 1 + 1 + 1  # 9+7 = 16
_CONSUMABLE_DIMS = 3 + 3  # category one-hot + effect type simplified = 6
_GLOBAL_DIMS = 9
_HANDSCORE_DIMS = len(HAND_TYPES) * 3
_SHOP_FLAG_DIMS = 8

OBSERVATION_SHAPE = (
    _GLOBAL_DIMS
    + MAX_HAND * _CARD_DIMS
    + MAX_JOKERS * _JOKER_DIMS
    + MAX_CONSUMABLES * _CONSUMABLE_DIMS
    + _HANDSCORE_DIMS
    + _SHOP_FLAG_DIMS
)
# 9 + 152 + 80 + 12 + 39 + 8 = 300
