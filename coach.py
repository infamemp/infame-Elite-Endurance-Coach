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

    python coach.py review <athlete_id> --since <YYYY-MM-DD>
                                             compare CTL/ATL/TSB, ACWR, durability
                                             and (once history accumulates) curve
                                             progression against today; folds in
                                             race_notes.md if present

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
import statistics
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta

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


def capture_snapshot(aid):
    """Save a lightweight, dated snapshot of curve data after every prep.

    Why: CTL/ATL/TSB, ACWR and decoupling can all be recomputed for any past
    date from the 180-day window fetch_athlete_data.py already pulls — no
    snapshot needed there. Power/pace curves are different: Intervals.icu's
    curves endpoint returns only the best value in the window as of TODAY,
    never a historical one. Without a dated snapshot, "did this athlete's
    curve anchors move during this block" can never be answered for any
    block that started before this function first ran — that gap cannot be
    closed retroactively, so capture starts now rather than when a review
    command first needs it.

    Non-blocking by design: like build_profile, a failure here must never
    stop state.md from being delivered."""
    src = os.path.join(ROOT, "data", str(aid), "athlete_data.json")
    if not os.path.exists(src):
        return None
    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    snap_date = (data.get("fetched_at") or "")[:10]
    if not snap_date:
        return None

    hist_dir = os.path.join(ROOT, "data", str(aid), "history")
    os.makedirs(hist_dir, exist_ok=True)
    path = os.path.join(hist_dir, f"{snap_date}.json")
    snapshot = {
        "date": snap_date,
        "curves": data.get("curves") or {},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    return path


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
        capture_snapshot(aid)
    except Exception as e:
        print(f"   SNAPSHOT FAILED (non-blocking): {type(e).__name__}: {e}")

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


def d(s):
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def pmc_at(data, target):
    """The pmc_series entry on or nearest before target — same series
    build_state.py's latest_pmc() reads, just anchored at a past date
    instead of always taking the last entry."""
    series = [p for p in (data.get("pmc_series") or [])
              if p.get("date") and d(p["date"]) <= target]
    if not series:
        return None
    row = series[-1]
    return {"date": row["date"],
            "ctl": round(row["ctl"], 1) if row.get("ctl") is not None else None,
            "atl": round(row["atl"], 1) if row.get("atl") is not None else None,
            "tsb": row.get("tsb")}


def decoupling_at(data, target, window_days=28, min_minutes=45):
    """Median decoupling of qualifying sessions in the 28 days ending at
    target — the same window and session-length floor as the durability
    signal elsewhere, just anchored at a past date on request."""
    start = target - timedelta(days=window_days - 1)
    vals = [a["decoupling"] for a in (data.get("activities") or [])
            if a.get("date") and a.get("decoupling") is not None
            and (a.get("moving_time") or 0) >= min_minutes * 60
            and start <= d(a["date"]) <= target]
    if not vals:
        return {"available": False, "reason": "no qualifying sessions in window"}
    return {"available": True, "median": round(statistics.median(vals), 1),
            "sessions": len(vals)}


def nearest_snapshot(aid, target):
    """The curve snapshot closest to (on or before, else nearest after)
    target, from data/<id>/history/. Returns (snapshot_dict, days_off) or
    (None, None) if no snapshot exists at all — expected for any athlete
    until capture_snapshot() has had time to accumulate history."""
    hist_dir = os.path.join(ROOT, "data", str(aid), "history")
    if not os.path.isdir(hist_dir):
        return None, None
    candidates = []
    for fname in os.listdir(hist_dir):
        if fname.endswith(".json"):
            try:
                fdate = d(fname[:-5])
            except ValueError:
                continue
            candidates.append(fdate)
    if not candidates:
        return None, None
    on_or_before = [c for c in candidates if c <= target]
    best = max(on_or_before) if on_or_before else min(candidates)
    with open(os.path.join(hist_dir, f"{best.isoformat()}.json"),
              encoding="utf-8") as f:
        snap = json.load(f)
    return snap, (target - best).days


def curve_progression(snap, data):
    """Compare each anchor's 42d-window value between a past snapshot and
    today's curves. Only anchors present in both are compared — a duration
    the athlete hadn't tested at snapshot time is not a regression."""
    then = ((snap or {}).get("curves") or {})
    now = data.get("curves") or {}
    rows = []
    for kind in ("power", "pace"):
        t42 = ((then.get(kind) or {}).get("42d") or {}).get("points") or {}
        n42 = ((now.get(kind) or {}).get("42d") or {}).get("points") or {}
        for anchor in sorted(set(t42) & set(n42), key=lambda x: int(x)):
            val_key = "watts" if kind == "power" else "seconds"
            before = t42[anchor].get(val_key)
            after = n42[anchor].get(val_key)
            if before is None or after is None:
                continue
            rows.append({"kind": kind, "anchor": anchor, "before": before,
                        "after": after})
    return rows


def read_race_notes(name, since, today):
    """#RACE_RESULT blocks from out/<name>/race_notes.md whose Date falls in
    [since, today]. The athlete pastes these by hand after Phase 6 — this
    only reads what's already there, never writes to the file."""
    path = os.path.join(ROOT, "out", name, "race_notes.md")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    blocks = re.split(r"(?=^#RACE_RESULT\s*$)", text, flags=re.M)
    in_window = []
    for b in blocks:
        if not b.strip().startswith("#RACE_RESULT"):
            continue
        m = re.search(r"^Date:\s*(\S+)", b, flags=re.M)
        if not m:
            continue
        try:
            race_date = d(m.group(1))
        except ValueError:
            continue
        if since <= race_date <= today:
            in_window.append(b.strip())
    return in_window


def render_review(aid, name, dest_name, since, data, snap, snap_age, curves, races, bs):
    today = date.today()
    pmc_then, pmc_now = pmc_at(data, since), pmc_at(data, today)
    acwr_then = bs.acwr_signal(data, as_of=since)
    acwr_now = bs.acwr_signal(data)
    dec_then = decoupling_at(data, since)
    dec_now = decoupling_at(data, today)

    L = [f"# REVIEW — {name} ({aid})", "",
         f"Window: {since.isoformat()} \u2192 {today.isoformat()}", ""]

    L += ["## Load (CTL / ATL / TSB)", ""]
    if pmc_then and pmc_now:
        L.append(f"- **{since.isoformat()}:** CTL {pmc_then['ctl']} / "
                 f"ATL {pmc_then['atl']} / TSB {pmc_then['tsb']}")
        L.append(f"- **{today.isoformat()}:** CTL {pmc_now['ctl']} / "
                 f"ATL {pmc_now['atl']} / TSB {pmc_now['tsb']}")
        L.append(f"- **\u0394 CTL:** {round(pmc_now['ctl'] - pmc_then['ctl'], 1):+}")
    else:
        L.append("Not available \u2014 no PMC data covering this window.")
    L.append("")

    L += ["## ACWR", ""]
    for label, sig in ((since.isoformat(), acwr_then), (today.isoformat(), acwr_now)):
        if sig.get("available"):
            L.append(f"- **{label}:** ratio {sig['ratio']} "
                     f"(acute {sig['acute_7d']} vs chronic {sig['chronic_weekly_avg']}/wk)")
        else:
            L.append(f"- **{label}:** not available \u2014 {sig.get('reason')}")
    L.append("")

    L += ["## Durability (median decoupling)", ""]
    for label, sig in ((since.isoformat(), dec_then), (today.isoformat(), dec_now)):
        if sig.get("available"):
            L.append(f"- **{label}:** {sig['median']}% over {sig['sessions']} sessions")
        else:
            L.append(f"- **{label}:** not available \u2014 {sig.get('reason')}")
    L.append("")

    L += ["## Curve progression", ""]
    if snap is None:
        L.append("No curve history yet for this athlete \u2014 snapshot capture "
                 "started with the first `coach.py prep` run after this feature "
                 "shipped. Progression tracking will be available for any block "
                 "starting after that date.")
    elif not curves:
        L.append(f"Nearest snapshot found is {snap['date']} "
                 f"({snap_age:+d} days from {since.isoformat()}), but it shares "
                 f"no anchor durations with today's curves \u2014 nothing to compare.")
    else:
        if snap_age != 0:
            L.append(f"_Nearest available snapshot: {snap['date']} "
                     f"({abs(snap_age)} days {'before' if snap_age >= 0 else 'after'} "
                     f"the requested date \u2014 no snapshot fell exactly on it)._")
            L.append("")
        L.append("| Kind | Anchor (s) | Before | After | \u0394 |")
        L.append("| :--- | ---: | ---: | ---: | ---: |")
        for r in curves:
            delta = r["after"] - r["before"]
            L.append(f"| {r['kind']} | {r['anchor']} | {r['before']} | "
                     f"{r['after']} | {delta:+} |")
    L.append("")

    L += ["## Race results in this window", ""]
    if races is None:
        L.append(f"No `race_notes.md` found for this athlete "
                 f"(out/{dest_name}/race_notes.md).")
    elif not races:
        L.append("No race results recorded in this window.")
    else:
        for b in races:
            L.append(b)
            L.append("")

    return "\n".join(L).rstrip() + "\n"


def cmd_review(args):
    import build_state as bs

    data_path = os.path.join(ROOT, "data", str(args.athlete), "athlete_data.json")
    if not os.path.exists(data_path):
        sys.exit(f"No data for '{args.athlete}'. Run: python coach.py prep {args.athlete}")
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    try:
        since = d(args.since)
    except ValueError:
        sys.exit(f"--since must be YYYY-MM-DD, got '{args.since}'")

    name = (data.get("profile") or {}).get("name") or str(args.athlete)
    dest_name = safe_filename(name) or str(args.athlete)

    snap, snap_age = nearest_snapshot(args.athlete, since)
    curves = curve_progression(snap, data) if snap else []
    races = read_race_notes(dest_name, since, date.today())

    md = render_review(args.athlete, name, dest_name, since, data, snap, snap_age,
                       curves, races, bs)

    out_dir = os.path.join(ROOT, "out", dest_name)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "review.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)

    print(md)
    print(f"Wrote out/{dest_name}/review.md")


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

    r = sub.add_parser("review", help="compare an athlete's signals since a past date against today")
    r.add_argument("athlete", help="athlete id, e.g. i18969")
    r.add_argument("--since", required=True, help="YYYY-MM-DD — the block/period start date")
    r.set_defaults(func=cmd_review)

    args = ap.parse_args()
    if args.cmd == "prep":
        cmd_prep(args)
    elif args.cmd == "check":
        cmd_check(args)
    elif args.cmd == "new":
        cmd_new(args)
    elif args.cmd == "review":
        cmd_review(args)


if __name__ == "__main__":
    main()
