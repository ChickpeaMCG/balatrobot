from balatrobot.features.constants import (
    EFFECT_TYPES,
    ENHANCEMENT_KEYS,
    HAND_TYPES,
    MAX_CONSUMABLES,
    MAX_HAND,
    MAX_JOKERS,
    OBSERVATION_SHAPE,
    SEAL_KEYS,
    SUITS,
)

card_dims = len(SUITS) + 1 + len(ENHANCEMENT_KEYS) + 1 + len(SEAL_KEYS)
joker_dims = len(EFFECT_TYPES) + 7
total = 9 + MAX_HAND*card_dims + MAX_JOKERS*joker_dims + MAX_CONSUMABLES*6 + len(HAND_TYPES)*3 + 8
print(f"card_dims={card_dims}, joker_dims={joker_dims}")
print(f"Computed total: {total}")
print(f"OBSERVATION_SHAPE constant: {OBSERVATION_SHAPE}")
print(f"Match: {total == OBSERVATION_SHAPE}")
