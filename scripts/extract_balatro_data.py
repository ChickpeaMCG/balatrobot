"""
Extract game item skeletons from Balatro's embedded game.lua.

All item definitions live in Balatro.exe as a ZIP-embedded LÖVE2D archive.
This script reads them directly — no installation path configuration needed,
just pass the path to Balatro.exe.

Usage:
    python scripts/extract_balatro_data.py [--exe PATH] [--out DIR] [--version VER]

Defaults:
    --exe  "C:/Program Files (x86)/Steam/steamapps/common/Balatro/Balatro.exe"
    --out  balatrobot/data/
    --version  auto-detected from globals.lua

Outputs one JSON file per category with key/name/cost/rarity. Effect fields
(effect_types, trigger, flush_synergy) are left as empty placeholders for
manual annotation.

Re-run on any patch to detect additions/removals by diffing the output.
"""

import argparse
import json
import re
import zipfile
from pathlib import Path

DEFAULT_EXE = "C:/Program Files (x86)/Steam/steamapps/common/Balatro/Balatro.exe"
DEFAULT_OUT = Path(__file__).parent.parent / "balatrobot" / "data"

RARITY_NAMES = {1: "Common", 2: "Uncommon", 3: "Rare", 4: "Legendary"}


def _read_zip_file(exe_path: str, filename: str) -> str:
    with zipfile.ZipFile(exe_path) as z:
        return z.read(filename).decode("utf-8", errors="replace")


def _detect_version(exe_path: str) -> str:
    content = _read_zip_file(exe_path, "globals.lua")
    m = re.search(r"VERSION\s*=\s*'([^']+)'", content)
    return m.group(1) if m else "unknown"


def _extract_field(line: str, field: str) -> str | None:
    """Extract a simple field value from a Lua table line (handles single and double quotes)."""
    m = re.search(rf"{field}\s*=\s*[\"']([^\"']*)[\"']", line)
    if m:
        return m.group(1)
    m = re.search(rf'{field}\s*=\s*(\d+(?:\.\d+)?)', line)
    if m:
        return m.group(1)
    return None


def extract_jokers(content: str, version: str) -> dict:
    jokers = []
    for line in content.split("\n"):
        s = line.strip()
        if not s.startswith("j_") or not re.search(r'''set\s*=\s*["']Joker["']''', line):
            continue
        key_m = re.match(r'(j_\w+)\s*=', s)
        if not key_m:
            continue
        key = key_m.group(1)
        name = _extract_field(line, "name") or key
        cost_raw = _extract_field(line, "cost")
        rarity_raw = _extract_field(line, "rarity")
        cost = int(cost_raw) if cost_raw else 0
        rarity_int = int(rarity_raw) if rarity_raw else 1
        rarity = RARITY_NAMES.get(rarity_int, "Common")
        jokers.append({
            "key": key,
            "name": name,
            "base_cost": cost,
            "rarity": rarity,
            "effect_types": [],
            "trigger": "always",
            "base_chips": 0,
            "base_mult": 0,
            "base_xmult": 1.0,
            "is_scaling": False,
            "is_conditional": True,
            "flush_synergy": 0.0,
            "description": "",
        })
    jokers.sort(key=lambda j: j["key"])
    return {"balatro_version": version, "jokers": jokers}


def extract_consumables(content: str, version: str, set_name: str, out_key: str) -> dict:
    items = []
    for line in content.split("\n"):
        s = line.strip()
        if not s.startswith("c_") or not re.search(rf'''set\s*=\s*["']{set_name}["']''', line):
            continue
        key_m = re.match(r'(c_\w+)\s*=', s)
        if not key_m:
            continue
        key = key_m.group(1)
        name = _extract_field(line, "name") or key
        cost_raw = _extract_field(line, "cost")
        cost = int(cost_raw) if cost_raw else 3
        items.append({
            "key": key,
            "name": name,
            "base_cost": cost,
            "effect_types": [],
            "description": "",
        })
    items.sort(key=lambda x: x["key"])
    return {"balatro_version": version, out_key: items}


def extract_vouchers(content: str, version: str) -> dict:
    items = []
    seen = set()
    for line in content.split("\n"):
        s = line.strip()
        if not s.startswith("v_") or not re.search(r'''set\s*=\s*["']Voucher["']''', line):
            continue
        key_m = re.match(r'(v_\w+)\s*=', s)
        if not key_m:
            continue
        raw_key = key_m.group(1)
        # Deduplicate _norm/_mega variants — keep base key without suffix
        base_key = re.sub(r"_(norm|mega)$", "", raw_key)
        if base_key in seen:
            continue
        seen.add(base_key)
        name = _extract_field(line, "name") or base_key
        cost_raw = _extract_field(line, "cost")
        cost = int(cost_raw) if cost_raw else 10
        items.append({
            "key": base_key,
            "name": name,
            "base_cost": cost,
            "effect_types": [],
            "description": "",
        })
    items.sort(key=lambda x: x["key"])
    return {"balatro_version": version, "vouchers": items}


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Balatro item data to JSON skeletons")
    parser.add_argument("--exe", default=DEFAULT_EXE, help="Path to Balatro.exe")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory")
    parser.add_argument("--version", default=None, help="Override version tag")
    args = parser.parse_args()

    exe = args.exe
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading from: {exe}")
    try:
        content = _read_zip_file(exe, "game.lua")
    except (FileNotFoundError, KeyError) as e:
        print(f"Error reading game.lua from {exe}: {e}")
        raise SystemExit(1) from e

    version = args.version or _detect_version(exe)
    print(f"Detected version: {version}")

    outputs = [
        ("jokers.json", extract_jokers(content, version)),
        ("tarots.json", extract_consumables(content, version, "Tarot", "tarots")),
        ("planets.json", extract_consumables(content, version, "Planet", "planets")),
        ("spectrals.json", extract_consumables(content, version, "Spectral", "spectrals")),
        ("vouchers.json", extract_vouchers(content, version)),
    ]

    for filename, data in outputs:
        path = out_dir / filename
        # Count items
        list_key = next(k for k in data if k != "balatro_version")
        count = len(data[list_key])

        # If file exists, check for additions/removals vs current
        if path.exists():
            existing = json.loads(path.read_text())
            existing_keys = {item["key"] for item in existing.get(list_key, [])}
            new_keys = {item["key"] for item in data[list_key]}
            added = new_keys - existing_keys
            removed = existing_keys - new_keys
            if added:
                print(f"  {filename}: +{len(added)} new keys: {sorted(added)}")
            if removed:
                print(f"  {filename}: -{len(removed)} removed keys: {sorted(removed)}")
            if not added and not removed:
                print(f"  {filename}: {count} items (no changes vs existing)")
            # Preserve existing annotations — only add new skeleton entries
            existing_map = {item["key"]: item for item in existing.get(list_key, [])}
            merged = []
            for item in data[list_key]:
                if item["key"] in existing_map:
                    merged.append(existing_map[item["key"]])  # keep annotated version
                else:
                    merged.append(item)  # new skeleton entry
            data[list_key] = sorted(merged, key=lambda x: x["key"])
        else:
            print(f"  {filename}: {count} items (new file)")

        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        print(f"  -> wrote {path}")


if __name__ == "__main__":
    main()
