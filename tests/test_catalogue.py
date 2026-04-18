from balatrobot.data.catalogue import (
    all_jokers,
    get_edition,
    get_enhancement,
    get_joker,
    get_planet,
    get_seal,
    get_spectral,
    get_tarot,
)
from balatrobot.data.models import EffectType, TriggerCondition


class TestJokerLoading:
    def test_all_jokers_loads(self):
        jokers = all_jokers()
        assert len(jokers) == 150

    def test_get_joker_known_key(self):
        j = get_joker("j_joker")
        assert j is not None
        assert j.name == "Joker"
        assert j.base_cost == 2

    def test_get_joker_unknown_key_returns_none(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="balatrobot.data.catalogue"):
            result = get_joker("j_does_not_exist")
        assert result is None
        assert "j_does_not_exist" in caplog.text

    def test_get_joker_unknown_key_does_not_raise(self):
        # Should never raise — bots call this with unknown keys at runtime
        assert get_joker("j_nonexistent_key_xyz") is None


class TestFlushSynergy:
    def test_four_fingers_flush_synergy(self):
        j = get_joker("j_four_fingers")
        assert j is not None
        assert j.flush_synergy == 1.0
        assert EffectType.HAND_MODIFIER in j.effect_types

    def test_droll_is_flush_mult_joker(self):
        j = get_joker("j_droll")
        assert j is not None
        assert j.flush_synergy == 1.0
        assert EffectType.MULT in j.effect_types
        assert j.trigger == TriggerCondition.ON_FLUSH
        assert j.base_mult == 4

    def test_smeared_high_flush_synergy(self):
        j = get_joker("j_smeared")
        assert j is not None
        assert j.flush_synergy >= 0.8

    def test_runner_zero_flush_synergy(self):
        j = get_joker("j_runner")
        assert j is not None
        assert j.flush_synergy == 0.0
        assert j.trigger == TriggerCondition.ON_STRAIGHT

    def test_flush_joker_priority_list(self):
        """Jokers with flush_synergy >= 0.7 form the bot priority list."""
        flush_jokers = [j for j in all_jokers() if j.flush_synergy >= 0.7]
        keys = {j.key for j in flush_jokers}
        assert "j_four_fingers" in keys
        assert "j_droll" in keys
        assert "j_smeared" in keys
        # Old incorrect keys must NOT be present
        assert "j_flush" not in {j.key for j in all_jokers()}
        assert "j_4_fingers" not in {j.key for j in all_jokers()}


class TestDataIntegrity:
    def test_all_jokers_have_required_fields(self):
        for j in all_jokers():
            assert isinstance(j.key, str) and j.key
            assert isinstance(j.name, str) and j.name
            assert isinstance(j.base_cost, int) and j.base_cost >= 0
            assert 0.0 <= j.flush_synergy <= 1.0

    def test_no_duplicate_joker_keys(self):
        keys = [j.key for j in all_jokers()]
        assert len(keys) == len(set(keys))

    def test_effect_types_are_valid_enum_values(self):
        valid = {e.value for e in EffectType}
        for j in all_jokers():
            for et in j.effect_types:
                assert et.value in valid, f"{j.key}: invalid effect_type {et}"


class TestConsumables:
    def test_tarots_load(self):
        t = get_tarot("c_fool")
        assert t is not None
        assert t.name == "The Fool"

    def test_planets_load(self):
        p = get_planet("c_mars")
        assert p is not None
        assert p.name == "Mars"

    def test_spectrals_load(self):
        s = get_spectral("c_familiar")
        assert s is not None
        assert s.name == "Familiar"


class TestSmallCatalogues:
    def test_editions_load(self):
        foil = get_edition("foil")
        assert foil is not None
        assert foil.base_chips == 50
        poly = get_edition("polychrome")
        assert poly is not None
        assert poly.xmult == 1.5
        neg = get_edition("negative")
        assert neg is not None
        assert neg.extra_joker_slot is True

    def test_seals_load(self):
        for key in ["Gold", "Red", "Blue", "Purple"]:
            s = get_seal(key)
            assert s is not None, f"Seal {key} not found"
            assert isinstance(s.description, str)

    def test_enhancements_load(self):
        bonus = get_enhancement("Bonus")
        assert bonus is not None
        assert bonus.base_chips == 30
        stone = get_enhancement("Stone")
        assert stone is not None
        assert stone.base_chips == 50
