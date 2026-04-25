#!/usr/bin/env python3
"""
Show the tail of the latest Balatro/Steamodded debug log.

Usage:
  python tail_log.py                       # last 30 debug lines
  python tail_log.py respond               # last 30 lines matching 'respond'
  python tail_log.py pack 50               # last 50 lines matching 'pack'
  python tail_log.py "" 0                  # entire log (no filter, no limit)
  python tail_log.py --transitions         # state transitions + key markers only
  python tail_log.py --transitions 100     # last 100 transition lines
"""
import argparse
import glob
import os
import re
import sys

LOG_DIR = r"C:\Users\Vince\AppData\Roaming\Balatro\Mods\lovely\log"
KEY_PATTERNS = ["DEBUG", "ERROR", "WARN"]

# Lines we always keep when in --transitions mode (signal markers)
TRANSITION_MARKERS = ("BOOSTER CB", "SELECT SHOP ACTION")
# Pattern that emits a value we want to dedupe consecutive duplicates of
WAITING_FOR_RE = re.compile(r"WaitingFor (\S+)")
# Pull the timestamp out of the standard Steamodded log line prefix
TIMESTAMP_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\b")


def latest_log_path() -> str | None:
    logs = sorted(glob.glob(os.path.join(LOG_DIR, "*.log")), key=os.path.getmtime, reverse=True)
    return logs[0] if logs else None


def tail_log(pattern: str = "", n: int = 30) -> None:
    latest = latest_log_path()
    if not latest:
        print(f"No logs found in {LOG_DIR}")
        return

    print(f"==> {latest}\n")
    with open(latest, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    filtered = [l for l in lines if any(p in l for p in KEY_PATTERNS)]
    if pattern:
        filtered = [l for l in filtered if pattern.lower() in l.lower()]

    tail = filtered[-n:] if n > 0 else filtered
    for line in tail:
        print(line, end="")
    print(f"\n({len(filtered)} matching lines total, showing last {len(tail)})")


def transitions(n: int = 0) -> None:
    """Emit only state transitions + key markers, with timestamps."""
    latest = latest_log_path()
    if not latest:
        print(f"No logs found in {LOG_DIR}")
        return

    print(f"==> {latest}\n")
    with open(latest, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    out: list[str] = []
    last_waiting_for = None
    for line in lines:
        ts_match = TIMESTAMP_RE.search(line)
        ts = ts_match.group(1) if ts_match else ""

        wf_match = WAITING_FOR_RE.search(line)
        if wf_match:
            value = wf_match.group(1)
            if value != last_waiting_for:
                out.append(f"{ts}  WaitingFor -> {value}")
                last_waiting_for = value
            continue

        for marker in TRANSITION_MARKERS:
            if marker in line:
                # Strip the noisy log prefix; keep the message body
                body = line.split("DefaultLogger ::", 1)[-1].strip()
                if not body:
                    body = line.strip()
                out.append(f"{ts}  {body}")
                break

    if n > 0:
        out = out[-n:]
    for entry in out:
        print(entry)
    print(f"\n({len(out)} transition events shown)")


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--transitions", action="store_true",
                        help="show only state changes + key markers")
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("rest", nargs="*")
    args = parser.parse_args()

    if args.help:
        print(__doc__)
        sys.exit(0)

    if args.transitions:
        n = int(args.rest[0]) if args.rest else 0
        transitions(n)
        return

    pat = args.rest[0] if len(args.rest) > 0 else ""
    lim = int(args.rest[1]) if len(args.rest) > 1 else 30
    tail_log(pat, lim)


if __name__ == "__main__":
    main()
