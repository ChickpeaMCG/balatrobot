"""One-time script to annotate known jokers in jokers.json with effect metadata."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "balatrobot" / "data"

ANNOTATIONS: dict[str, dict] = {
    # ── Flush-direct (flush_synergy = 1.0) ──────────────────────────────────
    "j_droll": {
        "effect_types": ["mult"],
        "trigger": "on_flush",
        "base_mult": 4,
        "is_conditional": True,
        "flush_synergy": 1.0,
        "description": "+4 Mult if played hand contains a Flush",
    },
    "j_four_fingers": {
        "effect_types": ["hand_modifier"],
        "trigger": "always",
        "is_conditional": False,
        "flush_synergy": 1.0,
        "description": "All Flushes and Straights can be made with 4 cards",
    },
    "j_tribe": {
        "effect_types": ["xmult"],
        "trigger": "on_flush",
        "base_xmult": 2.0,
        "is_conditional": True,
        "flush_synergy": 1.0,
        "description": "X2 Mult if played hand contains a Flush",
    },
    # ── High flush synergy ──────────────────────────────────────────────────
    "j_smeared": {
        "effect_types": ["hand_modifier"],
        "trigger": "always",
        "is_conditional": False,
        "flush_synergy": 0.9,
        "description": "Hearts and Diamonds count as same suit; Spades and Clubs count as same suit",
    },
    "j_crafty": {
        "effect_types": ["chips"],
        "trigger": "on_flush",
        "base_chips": 4,
        "is_conditional": True,
        "flush_synergy": 0.7,
        "description": "+4 Chips if played hand contains a Flush",
    },
    # ── Medium flush synergy ────────────────────────────────────────────────
    "j_fibonacci": {
        "effect_types": ["mult"],
        "trigger": "on_scored_card",
        "base_mult": 8,
        "is_conditional": True,
        "flush_synergy": 0.4,
        "description": "+8 Mult when an Ace, 2, 3, 5, or 8 is scored",
    },
    "j_supernova": {
        "effect_types": ["mult"],
        "trigger": "always",
        "is_scaling": True,
        "is_conditional": False,
        "flush_synergy": 0.5,
        "description": "Adds the number of times the played poker hand has been played to Mult",
    },
    "j_blackboard": {
        "effect_types": ["xmult"],
        "trigger": "always",
        "base_xmult": 3.0,
        "is_conditional": True,
        "flush_synergy": 0.5,
        "description": "X3 Mult if all cards held in hand are Spades or Clubs",
    },
    "j_steel_joker": {
        "effect_types": ["xmult"],
        "trigger": "on_held_card",
        "is_scaling": True,
        "is_conditional": True,
        "flush_synergy": 0.3,
        "description": "Gives X0.2 Mult for each Steel Card in your full deck",
    },
    # ── Useful staples (any strategy) ──────────────────────────────────────
    "j_joker": {
        "effect_types": ["mult"],
        "trigger": "always",
        "base_mult": 4,
        "is_conditional": False,
        "flush_synergy": 0.4,
        "description": "+4 Mult",
    },
    "j_abstract": {
        "effect_types": ["mult"],
        "trigger": "always",
        "is_scaling": True,
        "is_conditional": False,
        "flush_synergy": 0.3,
        "description": "+3 Mult for each Joker card",
    },
    "j_space": {
        "effect_types": ["passive"],
        "trigger": "on_scored_card",
        "is_conditional": True,
        "flush_synergy": 0.3,
        "description": "1-in-4 chance to upgrade the level of the played poker hand",
    },
    # ── Straight synergy (low flush synergy) ────────────────────────────────
    "j_shortcut": {
        "effect_types": ["hand_modifier"],
        "trigger": "always",
        "is_conditional": False,
        "flush_synergy": 0.3,
        "description": "Allows Straights to be made with gaps of 1 rank",
    },
    "j_runner": {
        "effect_types": ["chips", "scaling"],
        "trigger": "on_straight",
        "base_chips": 15,
        "is_scaling": True,
        "is_conditional": True,
        "flush_synergy": 0.0,
        "description": "Gains +15 Chips if played hand contains a Straight",
    },
    # ── Suit-mult jokers ────────────────────────────────────────────────────
    "j_greedy_joker": {
        "effect_types": ["mult"],
        "trigger": "on_scored_card",
        "base_mult": 3,
        "is_conditional": True,
        "flush_synergy": 0.2,
        "description": "+3 Mult when a Diamond card is scored",
    },
    "j_lusty_joker": {
        "effect_types": ["mult"],
        "trigger": "on_scored_card",
        "base_mult": 3,
        "is_conditional": True,
        "flush_synergy": 0.2,
        "description": "+3 Mult when a Heart card is scored",
    },
    "j_wrathful_joker": {
        "effect_types": ["mult"],
        "trigger": "on_scored_card",
        "base_mult": 3,
        "is_conditional": True,
        "flush_synergy": 0.2,
        "description": "+3 Mult when a Spade card is scored",
    },
    "j_gluttenous_joker": {
        "effect_types": ["mult"],
        "trigger": "on_scored_card",
        "base_mult": 3,
        "is_conditional": True,
        "flush_synergy": 0.2,
        "description": "+3 Mult when a Club card is scored",
    },
    # ── Pair/trio hand jokers (low flush synergy) ───────────────────────────
    "j_jolly": {
        "effect_types": ["mult"],
        "trigger": "on_pair",
        "base_mult": 8,
        "is_conditional": True,
        "flush_synergy": 0.0,
        "description": "+8 Mult if played hand contains a Pair",
    },
    "j_zany": {
        "effect_types": ["mult"],
        "trigger": "on_three_of_a_kind",
        "base_mult": 12,
        "is_conditional": True,
        "flush_synergy": 0.0,
        "description": "+12 Mult if played hand contains a Three of a Kind",
    },
    "j_sly": {
        "effect_types": ["chips"],
        "trigger": "on_pair",
        "base_chips": 50,
        "is_conditional": True,
        "flush_synergy": 0.0,
        "description": "+50 Chips if played hand contains a Pair",
    },
    "j_scary_face": {
        "effect_types": ["chips"],
        "trigger": "on_scored_card",
        "base_chips": 30,
        "is_conditional": True,
        "flush_synergy": 0.2,
        "description": "+30 Chips when a face card is scored",
    },
}


def main() -> None:
    path = DATA_DIR / "jokers.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    key_map = {j["key"]: j for j in data["jokers"]}

    updated = 0
    missing = []
    for key, patch in ANNOTATIONS.items():
        if key in key_map:
            key_map[key].update(patch)
            updated += 1
        else:
            missing.append(key)

    if missing:
        print(f"WARNING: keys not found in jokers.json: {missing}")

    data["jokers"] = sorted(key_map.values(), key=lambda j: j["key"])
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    annotated = sum(1 for j in data["jokers"] if j.get("effect_types") or j.get("flush_synergy", 0) > 0)
    print(f"Annotated {updated} jokers. Total with annotations: {annotated}/{len(data['jokers'])}")


if __name__ == "__main__":
    main()
