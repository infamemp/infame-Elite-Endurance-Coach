"""
fetch_athlete_data.py — Infame Elite Endurance Coach v6, Stage 3
=================================================================
Fetches the athlete data the deterministic engine needs and that the Excel
report does not carry: daily wellness (HRV, resting HR, sleep), the PMC time
series (CTL/ATL per day), and power/pace curves across rolling windows.

This script does NOT replace intervals_export.py. That script still produces
the human-readable Excel report and is untouched. This one writes structured
JSON for the engine to consume in Stage 4.

Output: data/<athlete_id>/athlete_data.json  (one file per athlete)

Usage:
    python engine/fetch_athlete_data.py
    python engine/fetch_athlete_data.py --athlete 123456
    python engine/fetch_athlete_data.py --days 180 --list

Options:
    --athlete   Fetch one athlete by id. Default: every athlete on the account.
    --days      History window in days. Default 180.
    --list      List athletes and exit without fetching.
    --outdir    Output directory. Default: data/

Requires the ICU_API_KEY environment variable.

Version: 1.1 — profile now also carries age, city, country, per-sport pace
units and eFTP (from the cached athlete-summary.json row); events now carry
distance. Added to retire intervals_export.py + convert.py from the daily
workflow, so athlete_data.json alone can supply everything the old Excel did.
"""

import argparse
import base64
import json
import os
import sys
from datetime import date, timedelta

try:
    import requests
except ImportError:
    sys.exit("Missing dependency. Run: pip install requests")

BASE_URL = "https://intervals.icu/api/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

API_KEY = os.getenv("ICU_API_KEY")
if not API_KEY:
    sys.exit('Missing environment variable ICU_API_KEY '
             '(run: setx ICU_API_KEY "your_key")')

# Power curve anchors, in seconds.
# 5s neuromuscular · 1m anaerobic · 5m VO2max · 20m threshold · 60m durability
CURVE_SECONDS = [5, 60, 300, 1200, 3600]

# Pace curve anchors, in metres. The pace endpoint is indexed by distance and
# returns elapsed time, not speed — a different shape from the power curve.
CURVE_METRES = [400, 1000, 5000, 10000, 21097]

# Rolling windows requested in one call. Intervals.icu only accepts named
# windows relative to today; date ranges are rejected, and oldest/newest are
# silently ignored on this endpoint (it returns the 1y curve instead), so they
# must never be used here.
CURVE_WINDOWS = ["42d", "90d", "1y"]

SESSION = None

# Populated by list_athletes() — the merged athlete-summary.json row per id,
# so fetch_profile() can read eFTP-by-category without a second API call.
_SUMMARY_CACHE = {}


def make_session():
    s = requests.Session()
    token = base64.b64encode(f"API_KEY:{API_KEY}".encode()).decode()
    s.headers.update({
        "Authorization": f"Basic {token}",
        "Accept": "application/json",
        # Cloudflare (which fronts Intervals.icu) can challenge or block
        # requests from bare Python clients. A browser-shaped User-Agent
        # avoids that — see forum.intervals.icu/t/api-access-to-intervals-icu/609
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/128.0.0.0 Safari/537.36"),
    })
    return s


def get(endpoint, params=None, optional=False):
    """GET one endpoint. With optional=True, a failure returns None instead of
    raising — used for endpoints that may not exist for every athlete."""
    try:
        r = SESSION.get(f"{BASE_URL}{endpoint}", params=params, timeout=45)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        if optional:
            print(f"      note: {endpoint} unavailable ({type(e).__name__})")
            return None
        raise


# ══════════════════════════════════════════════════════════════════
# FETCHERS
# ══════════════════════════════════════════════════════════════════

def fetch_wellness(aid, days):
    """Daily wellness records. In Intervals.icu these carry both the recovery
    signals (HRV, resting HR, sleep, weight) and the PMC series (ctl, atl),
    so one call covers two of the three gaps."""
    oldest = (date.today() - timedelta(days=days)).isoformat()
    newest = date.today().isoformat()
    rows = get(f"/athlete/{aid}/wellness",
               params={"oldest": oldest, "newest": newest}, optional=True) or []

    wellness, pmc = [], []
    for r in rows:
        d = r.get("id") or r.get("date")
        if not d:
            continue
        w = {"date": d}
        for src, dst in (("hrv", "hrv"), ("hrvSDNN", "hrv_sdnn"),
                         ("restingHR", "resting_hr"), ("sleepSecs", "sleep_secs"),
                         ("sleepScore", "sleep_score"), ("weight", "weight"),
                         ("soreness", "soreness"), ("fatigue", "fatigue_subjective"),
                         ("stress", "stress"), ("mood", "mood")):
            if r.get(src) is not None:
                w[dst] = r[src]
        if len(w) > 1:
            wellness.append(w)

        if r.get("ctl") is not None or r.get("atl") is not None:
            ctl, atl = r.get("ctl"), r.get("atl")
            pmc.append({
                "date": d,
                "ctl": ctl,
                "atl": atl,
                "tsb": (round(ctl - atl, 1)
                        if ctl is not None and atl is not None else None),
                "ramp_rate": r.get("rampRate"),
            })

    wellness.sort(key=lambda x: x["date"])
    pmc.sort(key=lambda x: x["date"])
    return wellness, pmc


def unwrap(data):
    """The curve endpoints return {"list": [ ... ]}. Normalize to a list."""
    if not data:
        return []
    if isinstance(data, dict):
        return data.get("list") or []
    if isinstance(data, list):
        return data
    return []


def nearest(axis, values, want, tolerance):
    """Closest index on an axis within tolerance, skipping null values."""
    best = None
    for i, x in enumerate(axis):
        if i >= len(values) or values[i] is None:
            continue
        if best is None or abs(x - want) < abs(axis[best] - want):
            best = i
    if best is None or abs(axis[best] - want) > tolerance:
        return None
    return best


def extract_power_curve(entry):
    """Anchor points plus the fitted power models (CP, W', FTP per model)."""
    secs = entry.get("secs")
    vals = entry.get("values") or entry.get("watts")
    if not secs or not vals:
        return None
    points = {}
    for want in CURVE_SECONDS:
        i = nearest(secs, vals, want, max(2, want * 0.05))
        if i is not None:
            points[str(want)] = {
                "secs": secs[i],
                "watts": vals[i],
                "activity_id": (entry.get("activity_id") or [None] * (i + 1))[i]
                if entry.get("activity_id") and i < len(entry["activity_id"]) else None,
            }
    if not points:
        return None
    return {
        "points": points,
        "models": entry.get("powerModels"),
        "vo2max_5m": entry.get("vo2max_5m"),
        "compound_score_5m": entry.get("compound_score_5m"),
        "weight": entry.get("weight"),
    }


def extract_pace_curve(entry):
    """The pace curve is indexed by distance in metres and returns elapsed
    seconds, so anchors are distances and the derived figure is speed."""
    dist = entry.get("distance")
    vals = entry.get("values")
    if not dist or not vals:
        return None
    points = {}
    for want in CURVE_METRES:
        i = nearest(dist, vals, want, max(50, want * 0.02))
        if i is not None and vals[i]:
            points[str(want)] = {
                "metres": round(dist[i]),
                "seconds": vals[i],
                "speed_ms": round(dist[i] / vals[i], 3),
                "activity_id": entry["activity_id"][i]
                if entry.get("activity_id") and i < len(entry["activity_id"]) else None,
            }
    if not points:
        return None
    return {"points": points, "models": entry.get("paceModels")}


def fetch_curves(aid):
    """Power and pace curves across nested rolling windows.

    Only named windows are accepted (see CURVE_WINDOWS). Comparing 42d against
    90d against 1y shows whether an athlete's best efforts are recent or stale:
    when the 42d value matches the 1y value, that peak was set recently."""
    out = {}
    for label, sport, extractor, kind in (
            ("power", "Ride", extract_power_curve, "power-curves"),
            ("pace", "Run", extract_pace_curve, "pace-curves")):
        got = {}
        for window in CURVE_WINDOWS:
            data = get(f"/athlete/{aid}/{kind}",
                       params={"curves": window, "type": sport}, optional=True)
            for entry in unwrap(data):
                parsed = extractor(entry)
                if parsed:
                    parsed["window"] = {
                        "id": entry.get("id", window),
                        "label": entry.get("label"),
                        "from": (entry.get("start_date_local") or "")[:10],
                        "to": (entry.get("end_date_local") or "")[:10],
                        "days": entry.get("days"),
                    }
                    got[entry.get("id", window)] = parsed
        if got:
            out[label] = got
    return out


def fetch_activities(aid, days):
    """Activity summaries carrying the fields the durability and repeatability
    contracts need. Full streams are not downloaded — only what Intervals.icu
    has already computed."""
    oldest = (date.today() - timedelta(days=days)).isoformat()
    newest = date.today().isoformat()
    acts = get(f"/athlete/{aid}/activities",
               params={"oldest": oldest, "newest": newest}, optional=True) or []

    fields = [
        ("start_date_local", "date"), ("type", "type"), ("name", "name"),
        ("moving_time", "moving_time"), ("distance", "distance"),
        ("icu_training_load", "training_load"), ("icu_intensity", "intensity"),
        ("icu_efficiency_factor", "efficiency_factor"),
        ("icu_variability_index", "variability_index"),
        ("decoupling", "decoupling"), ("icu_hr_zone_times", "hr_zone_times"),
        ("icu_power_zone_times", "power_zone_times"),
        ("icu_weighted_avg_watts", "weighted_avg_watts"),
        ("average_watts", "average_watts"), ("average_heartrate", "average_hr"),
        ("icu_w_prime", "w_prime"),
        ("icu_max_wbal_depletion", "max_wbal_depletion"),
        ("icu_ftp", "ftp_at_time"), ("average_speed", "average_speed"),
        ("total_elevation_gain", "elevation_gain"),
        ("average_temp", "average_temp"),
    ]

    out = []
    for a in acts:
        row = {}
        for src, dst in fields:
            if a.get(src) is not None:
                row[dst] = a[src]
        if row.get("date"):
            row["date"] = row["date"][:10]
        if row:
            out.append(row)
    out.sort(key=lambda x: x.get("date", ""))
    return out


def fetch_events(aid):
    """Planned workouts and races for the next 365 days — the input to PMC
    projection and taper governance in Stage 4."""
    today = date.today().isoformat()
    future = (date.today() + timedelta(days=365)).isoformat()
    evs = get(f"/athlete/{aid}/events",
              params={"oldest": today, "newest": future}, optional=True) or []

    out = []
    for e in evs:
        out.append({
            "date": (e.get("start_date_local") or "")[:10],
            "name": e.get("name"),
            "category": e.get("category"),
            "type": e.get("type"),
            "distance": e.get("distance"),
            "planned_load": e.get("icu_training_load") or e.get("training_load"),
            "planned_time": e.get("moving_time"),
            "priority": e.get("race_category") or e.get("priority"),
        })
    out.sort(key=lambda x: x["date"])
    return out


def calc_age(dob_str):
    """Age in years from an ISO date string (icu_date_of_birth). None if
    missing or unparseable — this is optional context, never blocking."""
    if not dob_str:
        return None
    try:
        dob = date.fromisoformat(dob_str[:10])
    except (ValueError, TypeError):
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def eftp_by_category(summary_row):
    """eFTP per sport category (Ride/Run/Swim) from athlete-summary.json's
    byCategory block. Same source and shape intervals_export.py already
    reads — kept identical so the two scripts never disagree."""
    out = {}
    for bc in (summary_row or {}).get("byCategory") or []:
        cat = bc.get("category", "")
        if cat:
            out[cat] = {"eftp": bc.get("eftp"), "eftp_per_kg": bc.get("eftpPerKg")}
    return out


def fetch_profile(aid, summary_row=None):
    """Static profile and per-sport settings: FTP, LTHR, threshold pace,
    pace units, zones, eFTP. summary_row (from list_athletes()'s cache)
    supplies eFTP-by-category — falls back to _SUMMARY_CACHE if not passed
    explicitly, so existing callers get it with no change on their side."""
    a = get(f"/athlete/{aid}", optional=True) or {}
    summary_row = summary_row or _SUMMARY_CACHE.get(aid) or {}
    eftp_map = eftp_by_category(summary_row)

    sports = []
    for s in a.get("sportSettings", []) or []:
        types = s.get("types") or []
        eftp_entry = next((eftp_map[c] for c in types if c in eftp_map), None)
        sports.append({
            "types": types,
            "ftp": s.get("ftp"),
            "indoor_ftp": s.get("indoor_ftp"),
            "lthr": s.get("lthr"),
            "max_hr": s.get("max_hr"),
            "threshold_pace": s.get("threshold_pace"),
            "pace_units": s.get("pace_units"),
            "w_prime": s.get("w_prime"),
            "power_zones": s.get("power_zones"),
            "hr_zones": s.get("hr_zones"),
            "pace_zones": s.get("pace_zones"),
            "eftp": eftp_entry.get("eftp") if eftp_entry else None,
            "eftp_per_kg": eftp_entry.get("eftp_per_kg") if eftp_entry else None,
        })
    return {
        "id": aid,
        "name": a.get("name"),
        "sex": a.get("sex"),
        "dob": a.get("icu_date_of_birth"),
        "age": calc_age(a.get("icu_date_of_birth")),
        "weight": a.get("icu_weight") or a.get("weight"),
        "height": a.get("height"),
        "city": a.get("city"),
        "country": a.get("country"),
        "resting_hr": a.get("icu_resting_hr") or a.get("resting_hr"),
        "timezone": a.get("timezone"),
        "sport_settings": sports,
    }


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def list_athletes():
    """Every athlete on the account, as (id, name) pairs.

    athlete-summary.json can return up to two rows per athlete_id with
    different fields populated — the same quirk already fixed in
    intervals_export.py. Rows are merged the same way: the row with the
    higher fitness value is primary, the other fills only what the primary
    is missing. The merged row is cached per id so fetch_profile() can read
    eFTP-by-category from it without a second API call."""
    summary = get("/athlete/0/athlete-summary.json") or []
    merged = {}
    for s in summary:
        aid = s.get("athlete_id")
        if not aid:
            continue
        if aid not in merged:
            merged[aid] = dict(s)
        else:
            existing = merged[aid]
            f_new = s.get("fitness") or 0
            f_existing = existing.get("fitness") or 0
            primary, secondary = (s, existing) if f_new > f_existing else (existing, s)
            row = dict(secondary)
            row.update({k: v for k, v in primary.items() if v is not None})
            merged[aid] = row

    _SUMMARY_CACHE.clear()
    _SUMMARY_CACHE.update(merged)
    return [(aid, row.get("athlete_name", "—")) for aid, row in merged.items()]


def fetch_one(aid, name, days, outdir):
    print(f"\n{name} ({aid})")

    print("   profile...")
    profile = fetch_profile(aid)

    print("   wellness and PMC series...")
    wellness, pmc = fetch_wellness(aid, days)
    print(f"      {len(wellness)} wellness days, {len(pmc)} PMC days")

    print("   activities...")
    activities = fetch_activities(aid, days)
    print(f"      {len(activities)} activities")

    print("   power and pace curves...")
    curves = fetch_curves(aid)
    for kind, windows in curves.items():
        print(f"      {kind}: {', '.join(sorted(windows))}")
    if not curves:
        print("      none available")

    print("   planned events...")
    events = fetch_events(aid)
    print(f"      {len(events)} events")

    payload = {
        "schema_version": 1,
        "fetched_at": date.today().isoformat(),
        "window_days": days,
        "profile": profile,
        "wellness": wellness,
        "pmc_series": pmc,
        "activities": activities,
        "curves": curves,
        "events": events,
    }

    dest = os.path.join(outdir, str(aid))
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, "athlete_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    size = os.path.getsize(path) / 1024
    print(f"   wrote {os.path.relpath(path, ROOT)} ({size:.0f} KB)")
    return path


def main():
    global SESSION
    ap = argparse.ArgumentParser(description="Fetch engine data from Intervals.icu")
    ap.add_argument("--athlete", help="Athlete id. Default: all athletes.")
    ap.add_argument("--days", type=int, default=180, help="History window (default 180)")
    ap.add_argument("--list", action="store_true", help="List athletes and exit")
    ap.add_argument("--outdir", default=os.path.join(ROOT, "data"))
    args = ap.parse_args()

    SESSION = make_session()
    print("Connecting to Intervals.icu...")

    try:
        athletes = list_athletes()
    except Exception as e:
        sys.exit(f"Connection failed: {e}\n"
                 f"Check that ICU_API_KEY is set correctly in this terminal.")

    if not athletes:
        sys.exit("No athletes found on this account.")
    print(f"   {len(athletes)} athletes on the account")

    if args.list:
        for aid, name in athletes:
            print(f"   {aid}  {name}")
        return

    if args.athlete:
        athletes = [(a, n) for a, n in athletes if str(a) == str(args.athlete)]
        if not athletes:
            sys.exit(f"Athlete '{args.athlete}' not found. Run with --list to see ids.")

    ok = 0
    for aid, name in athletes:
        try:
            fetch_one(aid, name, args.days, args.outdir)
            ok += 1
        except Exception as e:
            print(f"   FAILED: {type(e).__name__}: {e}")

    print(f"\nDone. {ok}/{len(athletes)} athletes written to "
          f"{os.path.relpath(args.outdir, ROOT)}/")


if __name__ == "__main__":
    main()
