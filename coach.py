"""
coach.py — Infame Elite Endurance Coach v6
============================================
One command in place of three. Pulls fresh data from Intervals.icu, resolves
the athlete's state, and renders the raw profile — for one athlete or every
athlete on the account — then delivers both files to a folder named after
the athlete, ready to drag into the Claude Project.

This wraps fetch_athlete_data.py, build_state.py and build_profile.py — it
does not replace them. All three remain usable directly if you ever need to
run just one step (for example, re-resolving state without a fresh pull).

Usage:
    python coach.py prep <athlete_id>       one athlete, fetch + resolve + profile
    python coach.py prep --all              every athlete with data on the account
    python coach.py prep --list             list athletes and exit, nothing fetched

    python coach.py new <athlete_id>        onboard a new athlete: create their
                                             config from the template

    python coach.py check <file>            validate a workout block and fill its TSS
                                             (shortcut for validate_block.py <file> --fill-tss)

Output:
    out/<athlete_name>/state.md and profile.md   — drag this folder into the Project
    out/roster.md                                — every athlete, id, and last fetch date

Version: 1.1 — adds build_profile.py to the daily run and delivers to a
named out/ folder instead of data/<id>/, so a folder full of athletes no
longer has to be identified by Intervals id alone.
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
import unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "engine"))
sys.path.insert(0, os.path.join(ROOT, "verify"))

# fetch_athlete_data checks ICU_API_KEY at import time, which "check" does not
# need. Import both modules lazily, inside the command that actually uses them,
# so `coach.py check` works with no key set.


def safe_filename(name):
    """Same normalization already fixed and verified in convert.py's
    safe_filename — copied rather than imported, since convert.py lives in a
    space-containing folder path and is being retired from the daily
    workflow this script drives."""
    normalized = unicodedata.normalize("NFKD", name or "")
    safe = normalized.encode("ascii", "ignore").decode("ascii")
    safe = re.sub(r"[^\w\s-]", " ", safe)
    safe = re.sub(r"\s+", "_", safe.strip())
    safe = re.sub(r"_+", "_", safe)
    safe = re.sub(r"-+", "-", safe)
    return safe.strip("-_")


def write_roster(athletes):
    """out/roster.md — every athlete on the account, by name, with the date
    their local data was last fetched. Regenerated from the full athlete
    list every time prep runs (single, --all, or --list), so an athlete not
    touched in this run still shows their real last-fetch date rather than
    going stale or missing."""
    rows = []
    for aid, name in athletes:
        data_path = os.path.join(ROOT, "data", str(aid), "athlete_data.json")
        fetched = "never fetched"
        if os.path.exists(data_path):
            try:
                with open(data_path, encoding="utf-8") as f:
                    fetched = json.load(f).get("fetched_at") or "—"
            except Exception:
                fetched = "—"
        rows.append((name or "—", aid, fetched))
    rows.sort(key=lambda r: r[0].lower())

    out_dir = os.path.join(ROOT, "out")
    os.makedirs(out_dir, exist_ok=True)
    lines = ["# ROSTER", "", "| Name | Athlete ID | Last fetched |",
             "| :--- | :--- | :--- |"]
    for name, aid, fetched in rows:
        lines.append(f"| {name} | {aid} | {fetched} |")
    path = os.path.join(out_dir, "roster.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def check_continuity(out_dir):
    """continuity.md is never written or touched by prep — it's the coach's
    own paste-once file, saved by hand from the block the Project outputs at
    the end of a week or block. This only reports presence and age, so a
    missing or stale block doesn't go unnoticed between sessions."""
    path = os.path.join(out_dir, "continuity.md")
    if not os.path.exists(path):
        print("   note: no continuity.md here yet — first prep for this "
              "athlete, or a continuity block was never saved")
        return
    age_days = (time.time() - os.path.getmtime(path)) / 86400
    flag = "  — check it's still current" if age_days > 10 else ""
    print(f"   continuity.md last updated {age_days:.0f} day(s) ago{flag}")


def prep_one(fad, bp, bs, aid, name, days, thresholds):
    """Fetch, resolve, and render — for one athlete. Stops and reports plainly
    if the fetch fails — a stale state is worse than no state, so a failed
    fetch must not silently fall through to resolving on old data. A failed
    profile render does NOT stop delivery: state.md is the authoritative
    piece, profile.md is supplementary raw context."""
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

    try:
        bp.build(aid, quiet=True)
    except Exception as e:
        print(f"   PROFILE BUILD FAILED (non-blocking): {type(e).__name__}: {e}")

    dest_name = safe_filename(name) or str(aid)
    out_dir = os.path.join(ROOT, "out", dest_name)
    os.makedirs(out_dir, exist_ok=True)
    delivered = []
    for fname in ("state.md", "profile.md"):
        src = os.path.join(ROOT, "data", str(aid), fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out_dir, fname))
            delivered.append(fname)

    print(f"   Ready — drag out/{dest_name}/ ({', '.join(delivered)}) "
          f"into the Claude Project")
    check_continuity(out_dir)
    return True


def cmd_prep(args):
    import fetch_athlete_data as fad
    import build_state as bs
    import build_profile as bp
    fad.SESSION = fad.make_session()
    print("Connecting to Intervals.icu...")
    try:
        athletes = fad.list_athletes()
    except Exception as e:
        sys.exit(f"Connection failed: {e}\nCheck that ICU_API_KEY is set correctly.")

    if not athletes:
        sys.exit("No athletes found on this account.")

    roster_path = write_roster(athletes)

    if args.list:
        print(f"   {len(athletes)} athletes on the account\n")
        for aid, name in athletes:
            print(f"   {aid}  {name}")
        print(f"\nRoster written to {os.path.relpath(roster_path, ROOT)}")
        return

    thresholds = bs.load_thresholds()

    if args.all:
        ok = 0
        for aid, name in athletes:
            if prep_one(fad, bp, bs, aid, name, args.days, thresholds):
                ok += 1
        write_roster(athletes)  # refresh fetch dates now that --all just ran
        print(f"\n{'='*60}")
        print(f"Done. {ok}/{len(athletes)} athletes ready in out/")
        return

    if not args.athlete:
        sys.exit("Specify an athlete id, --all, or --list. "
                 "Run 'python coach.py prep --list' to see ids.")

    match = [(a, n) for a, n in athletes if str(a) == str(args.athlete)]
    if not match:
        sys.exit(f"Athlete '{args.athlete}' not found. "
                 f"Run 'python coach.py prep --list' to see ids.")
    aid, name = match[0]
    ok = prep_one(fad, bp, bs, aid, name, args.days, thresholds)
    if ok:
        write_roster(athletes)
    sys.exit(0 if ok else 1)


def cmd_new(args):
    """Onboard a new athlete: confirm the id is real on the account, then
    create their config from the template. Never overwrites an existing
    profile — this is for new athletes only."""
    import fetch_athlete_data as fad
    fad.SESSION = fad.make_session()
    print("Connecting to Intervals.icu...")
    try:
        athletes = fad.list_athletes()
    except Exception as e:
        sys.exit(f"Connection failed: {e}\nCheck that ICU_API_KEY is set correctly.")

    match = [(a, n) for a, n in athletes if str(a) == str(args.athlete)]
    if not match:
        sys.exit(f"Athlete '{args.athlete}' not found on the account. "
                 f"Run 'python coach.py prep --list' to see ids.")
    aid, name = match[0]

    template = os.path.join(ROOT, "config", "athletes", "_template.yaml")
    dest = os.path.join(ROOT, "config", "athletes", f"{aid}.yaml")
    intake = os.path.join(ROOT, "config", "athletes", "ATHLETE_INTAKE.md")

    if not os.path.exists(template):
        sys.exit(f"Template not found: {os.path.relpath(template, ROOT)}")
    if os.path.exists(dest):
        sys.exit(f"{os.path.relpath(dest, ROOT)} already exists — this athlete "
                 f"already has a profile. Edit it directly instead of overwriting.")

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(template, dest)

    print(f"\n{name} ({aid}) confirmed on the account.")
    print(f"Created {os.path.relpath(dest, ROOT)} from the template.")
    if os.path.exists(intake):
        print(f"Run the intake conversation using "
              f"{os.path.relpath(intake, ROOT)} as the script, in the "
              f"athlete's language, then fill in the declared fields.")
    else:
        print(f"note: intake script not found at "
              f"{os.path.relpath(intake, ROOT)} — check it wasn't moved.")


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

    n = sub.add_parser("new", help="onboard a new athlete: create their config from the template")
    n.add_argument("athlete", help="athlete id, e.g. i18969")
    n.set_defaults(func=cmd_new)

    args = ap.parse_args()
    if args.cmd == "prep":
        cmd_prep(args)
    elif args.cmd == "check":
        cmd_check(args)
    elif args.cmd == "new":
        cmd_new(args)


if __name__ == "__main__":
    main()
