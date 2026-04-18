from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EffectType(str, Enum):
    CHIPS = "chips"
    MULT = "mult"
    XMULT = "xmult"
    SCALING = "scaling"
    HAND_MODIFIER = "hand_modifier"
    ECONOMY = "economy"
    DECK_MODIFIER = "deck_modifier"
    COPY_EFFECT = "copy_effect"
    PASSIVE = "passive"


class TriggerCondition(str, Enum):
    ALWAYS = "always"
    ON_FLUSH = "on_flush"
    ON_STRAIGHT = "on_straight"
    ON_PAIR = "on_pair"
    ON_TWO_PAIR = "on_two_pair"
    ON_THREE_OF_A_KIND = "on_three_of_a_kind"
    ON_FULL_HOUSE = "on_full_house"
    ON_FOUR_OF_A_KIND = "on_four_of_a_kind"
    ON_STRAIGHT_FLUSH = "on_straight_flush"
    ON_SCORED_CARD = "on_scored_card"
    ON_HELD_CARD = "on_held_card"
    ON_FACE_CARD = "on_face_card"
    ON_DISCARD = "on_discard"
    END_OF_ROUND = "end_of_round"
    INDEPENDENT = "independent"


@dataclass
class JokerData:
    key: str
    name: str
    base_cost: int
    rarity: str = "Common"
    effect_types: list[EffectType] = field(default_factory=list)
    trigger: TriggerCondition = TriggerCondition.ALWAYS
    base_chips: int = 0
    base_mult: int = 0
    base_xmult: float = 1.0
    is_scaling: bool = False
    is_conditional: bool = True
    flush_synergy: float = 0.0
    description: str = ""
    balatro_version: str = "1.0.1o"


@dataclass
class ConsumableData:
    key: str
    name: str
    base_cost: int
    effect_types: list[EffectType] = field(default_factory=list)
    description: str = ""
    balatro_version: str = "1.0.1o"


@dataclass
class EditionData:
    key: str
    name: str
    base_chips: int = 0
    base_mult: int = 0
    xmult: float = 1.0
    extra_joker_slot: bool = False


@dataclass
class SealData:
    key: str
    name: str
    description: str = ""


@dataclass
class EnhancementData:
    key: str
    name: str
    base_chips: int = 0
    description: str = ""
