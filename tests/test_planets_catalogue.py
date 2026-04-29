"""Tests for planet catalogue annotations added in Phase 6."""

from balatrobot.data.catalogue import all_planets, get_planet, planet_for_hand
from balatrobot.data.models import PlanetData


class TestPlanetData:
    def test_all_twelve_planets_loaded(self):
        planets = all_planets()
        assert len(planets) == 12

    def test_every_planet_has_hand_type(self):
        for p in all_planets():
            assert isinstance(p, PlanetData)
            assert p.hand_type, f"{p.key} missing hand_type"

    def test_jupiter_levels_flush(self):
        jupiter = get_planet("c_jupiter")
        assert jupiter is not None
        assert jupiter.hand_type == "Flush"
        assert jupiter.softlock is False

    def test_neptune_levels_straight_flush(self):
        neptune = get_planet("c_neptune")
        assert neptune is not None
        assert neptune.hand_type == "Straight Flush"

    def test_softlocked_planets_marked(self):
        for key in ("c_planet_x", "c_ceres", "c_eris"):
            p = get_planet(key)
            assert p is not None
            assert p.softlock is True

    def test_planet_for_hand_flush_returns_jupiter(self):
        p = planet_for_hand("Flush")
        assert p is not None
        assert p.key == "c_jupiter"

    def test_planet_for_hand_unknown_returns_none(self):
        assert planet_for_hand("Not A Real Hand") is None
