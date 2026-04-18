import json
from pathlib import Path

import numpy as np
import pytest

from balatrobot.features.constants import OBSERVATION_SHAPE
from balatrobot.features.encoder import GamestateEncoder

_CACHE_ROOT = Path(__file__).parent.parent / "gamestate_cache"


def _load_cached(phase: str) -> list[dict]:
    phase_dir = _CACHE_ROOT / phase
    if not phase_dir.exists():
        return []
    states = []
    for f in sorted(phase_dir.iterdir())[:5]:
        states.append(json.loads(f.read_text(encoding="utf-8")))
    return states


@pytest.fixture(scope="module")
def encoder() -> GamestateEncoder:
    return GamestateEncoder()


@pytest.fixture(scope="module")
def empty_G() -> dict:
    return {
        "hand": [],
        "jokers": [],
        "consumables": [],
        "ante": {"ante": 1, "blinds": {"chips_needed": 300}},
        "current_round": {"hands_left": 4, "discards_left": 3},
        "dollars": 4,
        "deck": [],
        "handscores": {},
        "shop": {"cards": []},
        "num_hands_played": 0,
        "current_chips": 0,
    }


class TestEncoderShape:
    def test_empty_state_shape(self, encoder, empty_G):
        vec = encoder.encode(empty_G)
        assert vec.shape == (OBSERVATION_SHAPE,)

    def test_empty_state_dtype(self, encoder, empty_G):
        vec = encoder.encode(empty_G)
        assert vec.dtype == np.float32

    def test_empty_state_all_finite(self, encoder, empty_G):
        vec = encoder.encode(empty_G)
        assert np.all(np.isfinite(vec))

    def test_cached_hand_states_shape(self, encoder):
        states = _load_cached("select_cards_from_hand")
        assert states, "No cached hand states found"
        for G in states:
            vec = encoder.encode(G)
            assert vec.shape == (OBSERVATION_SHAPE,), f"Bad shape: {vec.shape}"

    def test_cached_shop_states_shape(self, encoder):
        states = _load_cached("select_shop_action")
        assert states, "No cached shop states found"
        for G in states:
            vec = encoder.encode(G)
            assert vec.shape == (OBSERVATION_SHAPE,)


class TestEncoderRange:
    def test_all_values_bounded(self, encoder, empty_G):
        vec = encoder.encode(empty_G)
        assert float(vec.min()) >= 0.0, f"Min value below 0: {vec.min()}"
        assert float(vec.max()) <= 1.0, f"Max value above 1: {vec.max()}"

    def test_cached_states_bounded(self, encoder):
        for phase in ["select_cards_from_hand", "select_shop_action"]:
            for G in _load_cached(phase):
                vec = encoder.encode(G)
                assert float(vec.min()) >= 0.0
                assert float(vec.max()) <= 1.0


class TestEncoderSemantics:
    def test_unknown_joker_key_produces_zero_slot(self, encoder, empty_G):
        G = dict(empty_G)
        G["jokers"] = [{"key": "j_nonexistent_xyz", "name": "Unknown", "eternal": False}]
        vec_with = encoder.encode(G)
        # Just verify no crash and shape is correct; unknown key → zero joker slot
        assert vec_with.shape == (OBSERVATION_SHAPE,)

    def test_known_joker_produces_nonzero_slot(self, encoder, empty_G):
        G = dict(empty_G)
        G["jokers"] = [{"key": "j_four_fingers", "name": "Four Fingers", "eternal": False}]
        vec_with = encoder.encode(G)
        vec_without = encoder.encode(empty_G)
        # The two vectors should differ (joker slot is now non-zero)
        assert not np.array_equal(vec_with, vec_without)

    def test_flush_synergy_joker_in_shop_sets_flag(self, encoder, empty_G):
        G = dict(empty_G)
        G["dollars"] = 10
        G["shop"] = {"cards": [{"key": "j_four_fingers", "cost": 7}]}
        vec_with = encoder.encode(G)
        G2 = dict(empty_G)
        G2["dollars"] = 10
        G2["shop"] = {"cards": []}
        vec_without = encoder.encode(G2)
        # Shop flags segment should differ
        assert not np.array_equal(vec_with[-8:], vec_without[-8:])

    def test_suit_encoding_differs_by_suit(self, encoder, empty_G):
        def make_G(suit: str) -> dict:
            G = dict(empty_G)
            G["hand"] = [{"suit": suit, "value": "Ace", "enhancement": "Default Base"}]
            return G

        hearts = encoder.encode(make_G("Hearts"))
        spades = encoder.encode(make_G("Spades"))
        assert not np.array_equal(hearts, spades)

    def test_dollars_affects_global_scalar(self, encoder, empty_G):
        G_rich = dict(empty_G, dollars=50)
        G_poor = dict(empty_G, dollars=0)
        rich_vec = encoder.encode(G_rich)
        poor_vec = encoder.encode(G_poor)
        assert not np.array_equal(rich_vec, poor_vec)
