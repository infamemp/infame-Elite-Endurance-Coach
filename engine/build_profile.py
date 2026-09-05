"""
build_profile.py — Infame Elite Endurance Coach v6, Stage 9
==============================================================
Renders the athlete's raw context — personal info, sport configuration,
race calendar, planned sessions, recent activity history, and a computed
context snapshot — from athlete_data.json into a Markdown file for the
Claude Project. This retires intervals_export.py + convert.py + the manual
Excel-sheet-splitting step from the daily workflow.

This file does NOT duplicate anything state.md already owns. CTL/ATL/TSB
and every interpreted signal live in state.md and are authoritative there;
showing them here too is exactly the kind of two-sources-of-truth drift
that caused a real desync between the old profile and state documents.
profile.md only ever shows what Intervals.icu reports about the athlete,
never a computed verdict.

Known gap, left out on purpose rather than guessed: eW' and ePmax are not
rendered. The old Excel's values traced back to one specific model
(FFT_CURVES) inside one specific window (90d) of curves.power.models, and
that rule has only been confirmed against a single athlete. It needs
checking against a few more athletes before it can be trusted as a general
rule — until then, showing a wrong number is worse than showing none.

Input:  data/<athlete_id>/athlete_data.json   (written by fetch_athlete_data.py)
Output: data/<athlete_id>/profile.md

Usage:
    python engine/build_profile.py --athlete i18969
    python engine/build_profile.py --all

Version: 1.0
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# Broad sport groupings for the context snapshot's distribution line.
SPORT_GROUP = {
    "Ride": "Cycling", "VirtualRide": "Cycling", "MountainBikeRide": "Cycling",
    "GravelRide": "Cycling", "TrackRide": "Cycling", "Cyclocross": "Cycling",
    "Run": "Running", "VirtualRun": "Running", "TrailRun": "Running",
    "Swim": "Swimming", "OpenWaterSwim": "Swimming",
}


def load_athlete(aid):
    path = os.path.join(DATA, str(aid), "athlete_data.json")
    if not os.path.exists(path):
        sys.exit(f"No data for '{aid}'. Run: python engine/fetch_athlete_data.py "
                 f"--athlete {aid}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def d(s):
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def fmt_sec(secs):
    """1933 -> '32m 13s'; 9480 -> '2h 38m' (seconds dropped once hours show,
    matching the display convention the old Excel export already used)."""
    if not secs:
        return "—"
    secs = int(secs)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


def fmt_pace(speed_ms, units):
    """threshold_pace is stored as speed in m/s regardless of the athlete's
    display units — confirmed against both a MINS_KM and a SECS_100M
    athlete: 2.739726 m/s + MINS_KM -> '6:05 / km'; 0.8333333 m/s +
    SECS_100M -> '2:00 / 100m'."""
    if not speed_ms:
        return None
    is_100m = "100m" in str(units or "").lower()
    secs = 100 / speed_ms if is_100m else 1000 / speed_ms
    m, s = divmod(round(secs), 60)
    return f"{m}:{s:02d} / " + ("100m" if is_100m else "km")


def is_race(ev):
    cat = str(ev.get("category") or "").upper()
    return "RACE" in cat or str(ev.get("priority") or "").upper() in ("A", "B", "C")


# ══════════════════════════════════════════════════════════════════
# SECTIONS
# ══════════════════════════════════════════════════════════════════

def render_personal(profile, wellness):
    p = profile
    L = ["## PERSONAL INFORMATION", ""]
    L.append(f"**Name:** {p.get('name') or '—'}")
    L.append(f"**Age:** {p.get('age') if p.get('age') is not None else '—'}")
    L.append(f"**Sex:** {p.get('sex') or '—'}")
    L.append(f"**Weight (kg):** {p.get('weight') or '—'}")
    L.append(f"**Height (m):** {p.get('height') or '—'}")
    if p.get("city") or p.get("country"):
        L.append(f"**Location:** {p.get('city') or '—'}, {p.get('country') or '—'}")

    # Two distinct meanings, shown separately rather than picking one:
    # the configured baseline vs. the most recent daily measurement.
    if p.get("resting_hr") is not None:
        L.append(f"**Resting HR (configured):** {p['resting_hr']} bpm")
    last_measured = next((w for w in reversed(wellness or [])
                          if w.get("resting_hr") is not None), None)
    if last_measured:
        L.append(f"**Resting HR (latest measured):** "
                 f"{last_measured['resting_hr']} bpm ({last_measured['date']})")
    L.append("")
    return L


def render_sport_config(sport_settings):
    L = ["## SPORT CONFIGURATION & SETTINGS", ""]
    for s in sport_settings or []:
        types = s.get("types") or []
        primary = types[0] if types else None
        if primary not in ("Ride", "Run", "Swim"):
            continue  # skip "Other" and any unrecognized group — nothing to show

        rows = []
        if s.get("ftp") is not None:
            rows.append(("FTP", f"{s['ftp']} W"))
        if s.get("indoor_ftp") is not None:
            rows.append(("Indoor FTP", f"{s['indoor_ftp']} W"))
        if s.get("eftp") is not None:
            rows.append(("eFTP", f"{s['eftp']:.1f} W"))
        if s.get("eftp_per_kg") is not None:
            rows.append(("eFTP/kg", f"{s['eftp_per_kg']:.2f} W/kg"))
        if s.get("lthr") is not None:
            rows.append(("Threshold HR", f"{s['lthr']} bpm"))
        if s.get("max_hr") is not None:
            rows.append(("Max HR", f"{s['max_hr']} bpm"))
        if s.get("w_prime") is not None:
            rows.append(("W'", f"{s['w_prime']} J"))
        pace = fmt_pace(s.get("threshold_pace"), s.get("pace_units"))
        if pace:
            rows.append(("Threshold Pace", pace))
        if s.get("power_zones"):
            rows.append(("Power Zones (% FTP)", "/".join(str(z) for z in s["power_zones"])))
        if s.get("hr_zones"):
            rows.append(("HR Zones (bpm)", "/".join(str(z) for z in s["hr_zones"])))
        if s.get("pace_zones"):
            rows.append(("Pace Zones (%)", "/".join(str(z) for z in s["pace_zones"])))

        if not rows:
            continue  # sport configured in Intervals but nothing populated

        L.append(f"### {primary}")
        L.append("")
        L.append("| Metric | Value |")
        L.append("| :--- | :--- |")
        for label, value in rows:
            L.append(f"| {label} | {value} |")
        L.append("")
    return L


def render_races(events):
    races = [e for e in events or [] if is_race(e)]
    L = ["## SCHEDULED RACES & COMPETITIONS (Next 365 days)", ""]
    if not races:
        L.append("No races or competitions scheduled.")
        L.append("")
        return L
    L.append("| Date | Event Name | Type | Category | Distance | Priority |")
    L.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for e in races:
        cat_raw = str(e.get("category") or "")
        priority = str(e.get("priority") or "")
        if not priority and cat_raw.upper().startswith("RACE_"):
            priority = cat_raw.split("_")[-1]
        display_cat = "Race" if cat_raw.upper().startswith("RACE") else (cat_raw.capitalize() or "—")
        dist = e.get("distance")
        dist_str = f"{dist / 1000:.1f} km" if dist else "—"
        L.append(f"| {e.get('date', '—')} | {e.get('name') or '—'} | "
                 f"{e.get('type') or '—'} | {display_cat} | {dist_str} | {priority or '—'} |")
    L.append("")
    return L


def render_workouts(events):
    workouts = [e for e in events or [] if not is_race(e)]
    L = ["## WORKOUTS, PLANS & REST DAYS SCHEDULE", ""]
    if not workouts:
        L.append("Nothing scheduled.")
        L.append("")
        return L
    L.append("| Date | Description / Session | Type | Est. Load | Est. Time |")
    L.append("| :--- | :--- | :--- | ---: | ---: |")
    for e in workouts:
        load = e.get("planned_load")
        L.append(f"| {e.get('date', '—')} | {e.get('name') or '—'} | "
                 f"{e.get('type') or 'Workout'} | {load if load is not None else '—'} | "
                 f"{fmt_sec(e.get('planned_time'))} |")
    L.append("")
    return L


def render_history(activities, days=28):
    cutoff = date.today() - timedelta(days=days)
    recent = [a for a in (activities or [])
              if a.get("date") and d(a["date"]) >= cutoff]
    recent.sort(key=lambda a: a["date"], reverse=True)

    L = [f"## HISTORY: LAST {days} DAYS ACTIVITIES", ""]
    if not recent:
        L.append("No activities in this window.")
        L.append("")
        return L, recent
    L.append("| Date | Name | Sport | Duration | Dist (km) | TSS | IF | "
             "Avg Power (W) | Avg HR | Elev (m) | Decoupling % | EF | VI |")
    L.append("| :--- | :--- | :--- | :--- | ---: | ---: | ---: | "
             "---: | ---: | ---: | ---: | ---: | ---: |")
    for a in recent:
        dist = a.get("distance")
        tss = a.get("training_load")
        intensity = a.get("intensity")
        dist_s = f"{dist/1000:.2f}" if dist else "—"
        tss_s = f"{tss:.0f}" if tss is not None else "—"
        if_s = f"{intensity/100:.2f}" if intensity is not None else "—"
        pw_s = f"{a['weighted_avg_watts']:.0f}" if a.get("weighted_avg_watts") is not None else "—"
        hr_s = f"{a['average_hr']:.0f}" if a.get("average_hr") is not None else "—"
        el_s = f"{a['elevation_gain']:.0f}" if a.get("elevation_gain") is not None else "—"
        dec_s = f"{a['decoupling']:.1f}" if a.get("decoupling") is not None else "—"
        ef_s = f"{a['efficiency_factor']:.2f}" if a.get("efficiency_factor") is not None else "—"
        vi_s = f"{a['variability_index']:.2f}" if a.get("variability_index") is not None else "—"
        L.append(f"| {a['date']} | {a.get('name') or '—'} | {a.get('type') or '—'} | "
                 f"{fmt_sec(a.get('moving_time'))} | {dist_s} | {tss_s} | {if_s} | "
                 f"{pw_s} | {hr_s} | {el_s} | {dec_s} | {ef_s} | {vi_s} |")
    L.append("")
    return L, recent


def render_context_snapshot(events, recent_activities, days=28):
    L = ["## CONTEXT SNAPSHOT", ""]

    a_races = sorted((e for e in events or []
                      if str(e.get("category") or "").upper() == "RACE_A"
                      or str(e.get("priority") or "").upper() == "A"),
                     key=lambda e: e["date"])
    if a_races:
        race = a_races[0]
        days_out = (d(race["date"]) - date.today()).days
        L.append(f"**Next A-race:** {race['name']} — {race['date']} ({days_out} days away)")
    else:
        L.append("**Next A-race:** none scheduled")

    total_load = sum(a.get("training_load") or 0 for a in recent_activities)
    total_secs = sum(a.get("moving_time") or 0 for a in recent_activities)
    weeks = days / 7
    L.append(f"**Avg weekly TSS ({days // 7}w):** {total_load / weeks:.0f}")
    L.append(f"**Avg weekly hours ({days // 7}w):** {total_secs / 3600 / weeks:.1f} h")

    # Distribution by activity count, not time or load — matches the metric
    # the old Excel export used (verified: 13 Cycling / 11 Running of 24
    # activities reproduces its exact 54%/46% for this same athlete/window).
    group_count = {}
    for a in recent_activities:
        grp = SPORT_GROUP.get(a.get("type"), a.get("type") or "Other")
        group_count[grp] = group_count.get(grp, 0) + 1
    total_count = sum(group_count.values())
    if total_count:
        parts = [f"{g} {n / total_count * 100:.0f}%"
                 for g, n in sorted(group_count.items(), key=lambda kv: -kv[1])]
        L.append(f"**Sport distribution ({days // 7}w):** " + " · ".join(parts))
    L.append("")
    return L


# ══════════════════════════════════════════════════════════════════
# BUILD
# ══════════════════════════════════════════════════════════════════

def build(aid, quiet=False):
    data = load_athlete(aid)
    profile = data.get("profile") or {}
    name = profile.get("name") or aid

    L = []
    L.append("---")
    L.append(f"athlete: {name}")
    L.append(f"generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    L.append(f"source: athlete_data.json (fetched {data.get('fetched_at')})")
    L.append("---")
    L.append("")
    L.append("> Raw context only. CTL/ATL/TSB and every interpreted signal are "
             "authoritative in state.md, not here — see that file, don't recompute.")
    L.append("")

    L += render_personal(profile, data.get("wellness"))
    L += render_sport_config(profile.get("sport_settings"))
    L += render_races(data.get("events"))
    L += render_workouts(data.get("events"))

    history_lines, recent = render_history(data.get("activities"), days=28)
    L += history_lines
    L += render_context_snapshot(data.get("events"), recent, days=28)

    md = "\n".join(L).rstrip() + "\n"

    dest = os.path.join(DATA, str(aid))
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, "profile.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)

    if not quiet:
        print(md)
    print(f"Wrote data/{aid}/profile.md")
    return path


def main():
    ap = argparse.ArgumentParser(description="Render profile.md from athlete_data.json")
    ap.add_argument("--athlete")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.all:
        if not os.path.isdir(DATA):
            sys.exit("No data directory. Run fetch_athlete_data.py first.")
        ids = sorted(x for x in os.listdir(DATA)
                     if os.path.exists(os.path.join(DATA, x, "athlete_data.json")))
        if not ids:
            sys.exit("No athlete data found. Run fetch_athlete_data.py first.")
        for aid in ids:
            build(aid, quiet=True)
        print(f"\nBuilt profiles for {len(ids)} athletes.")
        return

    if not args.athlete:
        sys.exit("Specify --athlete <id> or --all")
    build(args.athlete, quiet=args.quiet)


if __name__ == "__main__":
    main()
