import json
import logging
from functools import cache
from pathlib import Path

from balatrobot.data.models import (
    ConsumableData,
    EditionData,
    EffectType,
    EnhancementData,
    JokerData,
    SealData,
    TriggerCondition,
)

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent


def _parse_joker(entry: dict) -> JokerData:
    return JokerData(
        key=entry["key"],
        name=entry["name"],
        base_cost=entry["base_cost"],
        rarity=entry.get("rarity", "Common"),
        effect_types=[EffectType(e) for e in entry.get("effect_types", [])],
        trigger=TriggerCondition(entry.get("trigger", "always")),
        base_chips=entry.get("base_chips", 0),
        base_mult=entry.get("base_mult", 0),
        base_xmult=entry.get("base_xmult", 1.0),
        is_scaling=entry.get("is_scaling", False),
        is_conditional=entry.get("is_conditional", True),
        flush_synergy=entry.get("flush_synergy", 0.0),
        description=entry.get("description", ""),
    )


def _parse_consumable(entry: dict) -> ConsumableData:
    return ConsumableData(
        key=entry["key"],
        name=entry["name"],
        base_cost=entry["base_cost"],
        effect_types=[EffectType(e) for e in entry.get("effect_types", [])],
        description=entry.get("description", ""),
    )


@cache
def _load_jokers() -> dict[str, JokerData]:
    raw = json.loads((_DATA_DIR / "jokers.json").read_text(encoding="utf-8"))
    return {entry["key"]: _parse_joker(entry) for entry in raw["jokers"]}


@cache
def _load_tarots() -> dict[str, ConsumableData]:
    raw = json.loads((_DATA_DIR / "tarots.json").read_text(encoding="utf-8"))
    return {entry["key"]: _parse_consumable(entry) for entry in raw["tarots"]}


@cache
def _load_planets() -> dict[str, ConsumableData]:
    raw = json.loads((_DATA_DIR / "planets.json").read_text(encoding="utf-8"))
    return {entry["key"]: _parse_consumable(entry) for entry in raw["planets"]}


@cache
def _load_spectrals() -> dict[str, ConsumableData]:
    raw = json.loads((_DATA_DIR / "spectrals.json").read_text(encoding="utf-8"))
    return {entry["key"]: _parse_consumable(entry) for entry in raw["spectrals"]}


@cache
def _load_editions() -> dict[str, EditionData]:
    raw = json.loads((_DATA_DIR / "editions.json").read_text(encoding="utf-8"))
    return {
        e["key"]: EditionData(
            key=e["key"],
            name=e["name"],
            base_chips=e.get("base_chips", 0),
            base_mult=e.get("base_mult", 0),
            xmult=e.get("xmult", 1.0),
            extra_joker_slot=e.get("extra_joker_slot", False),
        )
        for e in raw["editions"]
    }


@cache
def _load_seals() -> dict[str, SealData]:
    raw = json.loads((_DATA_DIR / "seals.json").read_text(encoding="utf-8"))
    return {
        s["key"]: SealData(key=s["key"], name=s["name"], description=s.get("description", ""))
        for s in raw["seals"]
    }


@cache
def _load_enhancements() -> dict[str, EnhancementData]:
    raw = json.loads((_DATA_DIR / "enhancements.json").read_text(encoding="utf-8"))
    return {
        e["key"]: EnhancementData(
            key=e["key"],
            name=e["name"],
            base_chips=e.get("base_chips", 0),
            description=e.get("description", ""),
        )
        for e in raw["enhancements"]
    }


def get_joker(key: str) -> JokerData | None:
    result = _load_jokers().get(key)
    if result is None:
        logger.warning("Unknown joker key encountered: %s", key)
    return result


def all_jokers() -> list[JokerData]:
    return list(_load_jokers().values())


def get_tarot(key: str) -> ConsumableData | None:
    result = _load_tarots().get(key)
    if result is None:
        logger.warning("Unknown tarot key encountered: %s", key)
    return result


def get_planet(key: str) -> ConsumableData | None:
    result = _load_planets().get(key)
    if result is None:
        logger.warning("Unknown planet key encountered: %s", key)
    return result


def get_spectral(key: str) -> ConsumableData | None:
    result = _load_spectrals().get(key)
    if result is None:
        logger.warning("Unknown spectral key encountered: %s", key)
    return result


def get_edition(key: str) -> EditionData | None:
    return _load_editions().get(key)


def get_seal(key: str) -> SealData | None:
    return _load_seals().get(key)


def get_enhancement(key: str) -> EnhancementData | None:
    return _load_enhancements().get(key)
