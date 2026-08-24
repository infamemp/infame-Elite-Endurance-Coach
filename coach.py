"""
coach.py — Infame Elite Endurance Coach v6
============================================
One command in place of two. Pulls fresh data from Intervals.icu and resolves
the athlete's state in a single step, for one athlete or every athlete on the
account.

This wraps fetch_athlete_data.py and build_state.py — it does not replace them.
Both remain usable directly if you ever need to run just one step (for example,
re-resolving state without a fresh pull).

Usage:
    python coach.py prep <athlete_id>       one athlete, fetch + resolve
    python coach.py prep --all              every athlete with data on the account
    python coach.py prep --list             list athletes and exit, nothing fetched

    python coach.py check <file>            validate a workout block and fill its TSS
                                             (shortcut for validate_block.py <file> --fill-tss)

Version: 1.0
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "engine"))
sys.path.insert(0, os.path.join(ROOT, "verify"))

# fetch_athlete_data checks ICU_API_KEY at import time, which "check" does not
# need. Import both modules lazily, inside the command that actually uses them,
# so `coach.py check` works with no key set.


def prep_one(fad, bs, aid, name, days, thresholds):
    """Fetch then resolve, for one athlete. Stops and reports plainly if the
    fetch fails — a stale state is worse than no state, so a failed fetch must
    not silently fall through to resolving on old data."""
    print(f"\n{'='*60}")
    print(f"{name} ({aid})")
    print(f"{'='*60}")
    try:
        fad.fetch_one(aid, name, days, os.path.join(ROOT, "data"))
    except Exception as e:
        print(f"   FETCH FAILED: {type(e).__name__}: {e}")
        print(f"   Skipping state resolution for {aid} — data was not refreshed.")
        return False

    try:
        bs.build(aid, thresholds, quiet=True)
    except Exception as e:
        print(f"   STATE RESOLUTION FAILED: {type(e).__name__}: {e}")
        return False

    state_path = os.path.join(ROOT, "data", str(aid), "state.md")
    print(f"   Ready — paste {os.path.relpath(state_path, ROOT)} into the Claude Project")
    return True


def cmd_prep(args):
    import fetch_athlete_data as fad
    import build_state as bs
    fad.SESSION = fad.make_session()
    print("Connecting to Intervals.icu...")
    try:
        athletes = fad.list_athletes()
    except Exception as e:
        sys.exit(f"Connection failed: {e}\nCheck that ICU_API_KEY is set correctly.")

    if not athletes:
        sys.exit("No athletes found on this account.")

    if args.list:
        print(f"   {len(athletes)} athletes on the account\n")
        for aid, name in athletes:
            print(f"   {aid}  {name}")
        return

    thresholds = bs.load_thresholds()

    if args.all:
        ok = 0
        for aid, name in athletes:
            if prep_one(fad, bs, aid, name, args.days, thresholds):
                ok += 1
        print(f"\n{'='*60}")
        print(f"Done. {ok}/{len(athletes)} athletes ready.")
        return

    if not args.athlete:
        sys.exit("Specify an athlete id, --all, or --list. "
                 "Run 'python coach.py prep --list' to see ids.")

    match = [(a, n) for a, n in athletes if str(a) == str(args.athlete)]
    if not match:
        sys.exit(f"Athlete '{args.athlete}' not found. "
                 f"Run 'python coach.py prep --list' to see ids.")
    aid, name = match[0]
    ok = prep_one(fad, bs, aid, name, args.days, thresholds)
    sys.exit(0 if ok else 1)


def cmd_check(args):
    """Delegate to validate_block.py --fill-tss. Kept as a subprocess call
    rather than an import so this command's exit code matches the validator's
    exactly — 0 pass, 1 blocked — with no risk of the two drifting apart."""
    import subprocess
    script = os.path.join(ROOT, "verify", "validate_block.py")
    cmd = [sys.executable, script, args.file, "--fill-tss"]
    if args.methodology:
        cmd += ["--methodology", args.methodology]
    if args.discipline:
        cmd += ["--discipline", args.discipline]
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def main():
    ap = argparse.ArgumentParser(
        description="Infame v6 — unified entry point for the daily workflow")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prep", help="fetch data and resolve state")
    p.add_argument("athlete", nargs="?", help="athlete id, e.g. i18969")
    p.add_argument("--all", action="store_true", help="every athlete on the account")
    p.add_argument("--list", action="store_true", help="list athletes and exit")
    p.add_argument("--days", type=int, default=180)
    p.set_defaults(func=cmd_prep)

    c = sub.add_parser("check", help="validate a workout block and fill its TSS")
    c.add_argument("file")
    c.add_argument("--methodology", help="override the [Methodology] header field")
    c.add_argument("--discipline", help="override the [Discipline] header field")
    c.set_defaults(func=cmd_check)

    args = ap.parse_args()
    if args.cmd == "prep":
        cmd_prep(args)
    elif args.cmd == "check":
        cmd_check(args)


if __name__ == "__main__":
    main()
