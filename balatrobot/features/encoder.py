from __future__ import annotations

import math

import numpy as np

from balatrobot.data.catalogue import all_jokers, get_joker
from balatrobot.features.constants import (
    EDITION_ENCODING,
    EFFECT_TYPES,
    ENHANCEMENT_KEYS,
    HAND_TYPES,
    MAX_CONSUMABLES,
    MAX_HAND,
    MAX_JOKERS,
    OBSERVATION_SHAPE,
    SEAL_KEYS,
    SUITS,
    VALUES,
)

# Top flush-synergy jokers for shop-flag encoding (stable order, computed once)
_FLUSH_SHOP_JOKERS = sorted(
    [j for j in all_jokers() if j.flush_synergy >= 0.7],
    key=lambda j: j.flush_synergy,
    reverse=True,
)[:8]


def _safe_log(x: float) -> float:
    return math.log1p(max(x, 0)) / math.log1p(1_000_000)


class GamestateEncoder:
    """Converts a live G dict into a fixed-size float32 numpy array.

    The output shape is stable (OBSERVATION_SHAPE,) regardless of how many
    cards/jokers/consumables are present — empty slots are zero-padded.
    Compatible with Stable Baselines3 Box observation spaces.
    """

    def encode(self, G: dict) -> np.ndarray:
        parts = [
            self._encode_globals(G),
            self._encode_hand(G.get("hand", [])),
            self._encode_jokers(G.get("jokers", [])),
            self._encode_consumables(G.get("consumables", [])),
            self._encode_handscores(G.get("handscores", {})),
            self._encode_shop_flags(G),
        ]
        vec = np.concatenate(parts).astype(np.float32)
        assert vec.shape == (OBSERVATION_SHAPE,), f"Shape mismatch: {vec.shape} != {OBSERVATION_SHAPE}"
        return vec

    def _encode_globals(self, G: dict) -> np.ndarray:
        blind = G.get("ante", {}).get("blinds", {})
        chips_needed = max(float(blind.get("chips_needed", 1)), 1.0)
        current_chips = max(float(G.get("current_chips", 0)), 0.0)
        ante = float(G.get("ante", {}).get("ante", 1))
        cr = G.get("current_round", {})
        return np.array(
            [
                min(ante / 8.0, 1.0),
                min(float(G.get("dollars", 0)) / 50.0, 1.0),
                min(float(cr.get("hands_left", 0)) / 5.0, 1.0),
                min(float(cr.get("discards_left", 0)) / 5.0, 1.0),
                _safe_log(chips_needed),
                _safe_log(current_chips),
                min(max((chips_needed - current_chips) / chips_needed, 0.0), 1.0),
                min(len(G.get("deck", [])) / 52.0, 1.0),
                min(float(G.get("num_hands_played", 0)) / 100.0, 1.0),
            ],
            dtype=np.float32,
        )

    def _encode_card_slot(self, card: dict | None) -> np.ndarray:
        """19-dim encoding for a single playing card slot."""
        vec = np.zeros(len(SUITS) + 1 + len(ENHANCEMENT_KEYS) + 1 + len(SEAL_KEYS), dtype=np.float32)
        if card is None:
            return vec
        suit = card.get("suit", "")
        if suit in SUITS:
            vec[SUITS.index(suit)] = 1.0
        val = card.get("value", "")
        if val in VALUES:
            vec[4] = VALUES.index(val) / (len(VALUES) - 1)
        enh = card.get("enhancement", "Default Base")
        if enh in ENHANCEMENT_KEYS:
            vec[5 + ENHANCEMENT_KEYS.index(enh)] = 1.0
        ed = card.get("edition", "")
        vec[14] = EDITION_ENCODING.get(str(ed), 0.0)
        seal = card.get("seal", "")
        if seal in SEAL_KEYS:
            vec[15 + SEAL_KEYS.index(seal)] = 1.0
        return vec

    def _encode_hand(self, hand: list[dict]) -> np.ndarray:
        slots = [self._encode_card_slot(hand[i] if i < len(hand) else None) for i in range(MAX_HAND)]
        return np.concatenate(slots)

    def _encode_joker_slot(self, joker_runtime: dict | None) -> np.ndarray:
        """16-dim encoding for a single joker slot."""
        vec = np.zeros(len(EFFECT_TYPES) + 7, dtype=np.float32)
        if joker_runtime is None:
            return vec
        key = joker_runtime.get("key", "")
        data = get_joker(key)
        if data:
            for et in data.effect_types:
                if et.value in EFFECT_TYPES:
                    vec[EFFECT_TYPES.index(et.value)] = 1.0
            vec[9] = min(data.base_chips / 100.0, 1.0)
            vec[10] = min(data.base_mult / 20.0, 1.0)
            vec[11] = float(data.is_scaling)
            vec[12] = float(data.is_conditional)
            vec[13] = data.flush_synergy
        vec[14] = EDITION_ENCODING.get(str(joker_runtime.get("edition", "")), 0.0)
        vec[15] = float(joker_runtime.get("eternal", False))
        return vec

    def _encode_jokers(self, jokers: list[dict]) -> np.ndarray:
        slots = [self._encode_joker_slot(jokers[i] if i < len(jokers) else None) for i in range(MAX_JOKERS)]
        return np.concatenate(slots)

    def _encode_consumable_slot(self, consumable: dict | None) -> np.ndarray:
        """6-dim encoding: category one-hot(3) + simplified effect(3)."""
        vec = np.zeros(6, dtype=np.float32)
        if consumable is None:
            return vec
        cat = consumable.get("set", consumable.get("label", ""))
        if cat == "Tarot":
            vec[0] = 1.0
        elif cat == "Planet":
            vec[1] = 1.0
        elif cat == "Spectral":
            vec[2] = 1.0
        return vec

    def _encode_consumables(self, consumables: list[dict]) -> np.ndarray:
        slots = [
            self._encode_consumable_slot(consumables[i] if i < len(consumables) else None)
            for i in range(MAX_CONSUMABLES)
        ]
        return np.concatenate(slots)

    def _encode_handscores(self, handscores: dict) -> np.ndarray:
        vec = np.zeros(len(HAND_TYPES) * 3, dtype=np.float32)
        for i, hand_type in enumerate(HAND_TYPES):
            entry = handscores.get(hand_type, {})
            base = i * 3
            vec[base] = min(float(entry.get("chips", 0)) / 200.0, 1.0)
            vec[base + 1] = min(float(entry.get("mult", 0)) / 20.0, 1.0)
            vec[base + 2] = min(float(entry.get("level", 1)) / 10.0, 1.0)
        return vec

    def _encode_shop_flags(self, G: dict) -> np.ndarray:
        """8 binary flags: top flush-synergy jokers present and affordable in shop."""
        vec = np.zeros(8, dtype=np.float32)
        dollars = float(G.get("dollars", 0))
        shop = G.get("shop", {})
        shop_cards = shop.get("cards", []) if isinstance(shop, dict) else []
        shop_keys = {card.get("key"): card.get("cost", 999) for card in shop_cards}
        for i, joker_data in enumerate(_FLUSH_SHOP_JOKERS):
            cost = shop_keys.get(joker_data.key, 999)
            vec[i] = float(cost <= dollars)
        return vec
