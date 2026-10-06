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

Version: 1.2 — adds fetch_recent_sessions(): the same /events endpoint,
looked backward instead of forward, reading each event's own `description`
field (the exact code block the coach wrote and the head coach pasted into
Intervals.icu, or that push_block sent directly). This is the coach's own
record of what it already prescribed, so an architecture classifier can
read it without anyone pasting continuity.md by hand. schema_version -> 2.
"""

import argparse
import base64
import json
import os
import sys
import time
from datetime import date, timedelta

try:
    import requests
except ImportError:
    sys.exit("Missing dependency. Run: pip install requests")

BASE_URL = "https://intervals.icu/api/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The key is read when a session is made, not at import (v7.29): importing this
# module used to exit the whole process when ICU_API_KEY was unset, which also
# took down anything that only imported it (the MCP tests, a future interface).
API_KEY = os.getenv("ICU_API_KEY")

# Power curve anchors, in seconds.
# 5s neuromuscular · 1m anaerobic · 5m VO2max · 20m threshold · 60m durability
CURVE_SECONDS = [5, 60, 300, 1200, 3600]

# Dense power-duration points for the Cusick diagnosis (engine/pd_diagnosis.py):
# how long the athlete holds FTP (TTE) and where the curve crosses each level
# above threshold. Measured values only, read straight off the curve -- no
# fitted model. Kept apart from CURVE_SECONDS so the longitudinal anchors,
# their config and their golden tests stay exactly as they are.
PD_CURVE_SECONDS = (
    [1, 5, 10, 15, 20, 30, 45]
    + list(range(60, 600, 30))        # 1:00 - 9:30 every 30 s
    + list(range(600, 3600, 60))      # 10:00 - 59:00 every minute
    + list(range(3600, 7201, 300))    # 60:00 - 120:00 every 5 min
)

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
    key = os.getenv("ICU_API_KEY") or API_KEY
    if not key:
        sys.exit('Missing environment variable ICU_API_KEY '
                 '(run: setx ICU_API_KEY "your_key")')
    s = requests.Session()
    token = base64.b64encode(f"API_KEY:{key}".encode()).decode()
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


RETRY_STATUS = (429, 500, 502, 503, 504)
RETRY_WAITS = (2, 5)          # seconds before the 2nd and 3rd attempt
_sleep = time.sleep           # replaced by the tests


def get(endpoint, params=None, optional=False):
    """GET one endpoint. A rate limit (429), a server error (5xx) or a dropped
    connection is retried twice, waiting a few seconds (or what Retry-After
    asks, up to 30 s) — v7.32. With optional=True, a failure that survives
    the retries returns None instead of raising: only for data that may not
    exist for every athlete (curves). The athlete's core data — profile,
    wellness and PMC, activities, planned and recent events — is never
    optional: if it cannot be read, the fetch fails and the previous
    athlete_data.json stays as it was, instead of being replaced by empty
    lists that would make the athlete look untrained."""
    attempts = len(RETRY_WAITS) + 1
    for attempt in range(attempts):
        try:
            r = SESSION.get(f"{BASE_URL}{endpoint}", params=params, timeout=45)
            status = getattr(r, "status_code", 200)
            if status in RETRY_STATUS and attempt < attempts - 1:
                wait = RETRY_WAITS[attempt]
                try:
                    wait = min(30, max(wait, int((r.headers or {}).get("Retry-After", wait))))
                except (TypeError, ValueError, AttributeError):
                    pass
                _sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < attempts - 1:
                _sleep(RETRY_WAITS[attempt])
                continue
            err = e
        except Exception as e:  # noqa: BLE001
            err = e
        if optional:
            print(f"      note: {endpoint} unavailable ({type(err).__name__})")
            return None
        raise err


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
               params={"oldest": oldest, "newest": newest}) or []

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
    # {seconds: watts}, only where the curve has a value within 2% of the
    # wanted duration (tighter than the anchors: these feed exact crossings).
    pd_points = {}
    for want in PD_CURVE_SECONDS:
        i = nearest(secs, vals, want, max(1, want * 0.02))
        if i is not None:
            pd_points[str(want)] = vals[i]
    return {
        "points": points,
        "pd_points": pd_points,
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

    # Indoor and outdoor power curves, apart. Intervals.icu keeps a separate
    # indoor FTP (sport settings `indoor_ftp`) and applies it to indoor rides,
    # so a curve has to be judged against the FTP of the same environment
    # (engine/pd_diagnosis.py). The combined curve above stays as it is: the
    # longitudinal analysis and its golden tests read it unchanged.
    # `filters` is the same filter the Intervals.icu power page uses; it is not
    # in the published API docs. Verified 2026-10-02: "indoor" returns the
    # indoor rides only, "outdoor" returns nothing for an athlete with none.
    for env in ("indoor", "outdoor"):
        got = {}
        flt = json.dumps([{"field_id": "indoor", "value": env, "id": 1}])
        for window in CURVE_WINDOWS:
            data = get(f"/athlete/{aid}/power-curves",
                       params={"curves": window, "type": "Ride", "filters": flt},
                       optional=True)
            for entry in unwrap(data):
                parsed = extract_power_curve(entry)
                if parsed:
                    parsed["window"] = {
                        "id": entry.get("id", window),
                        "from": (entry.get("start_date_local") or "")[:10],
                        "to": (entry.get("end_date_local") or "")[:10],
                        "days": entry.get("days"),
                    }
                    got[entry.get("id", window)] = parsed
        if got:
            out[f"power_{env}"] = got
    return out


def fetch_fatigue_curves(aid, profile):
    """Best 5- and 20-minute power per window, fresh and after the kJ of the
    athlete's fatigued curves (durability in watts, engine/durability_watts.py).

    Uses the documented `fatigue` parameter of activity-power-curves. The
    answer carries `after_kj`, the kJ each fatigued curve was cut at, so the
    level comes from Intervals.icu itself and not from a setting read here.
    Returns (curves, probe). `curves` is None -- silently, this is optional
    data -- when the athlete has no Ride settings, no power curve in the last
    84 days, or no fatigued curve defined; a fatigued curve that fails is left
    out, not guessed. `probe` says what each request came back with, kept in
    athlete_data.json so an absent section can be explained."""
    import durability_watts as dw

    ride = next((s for s in (profile or {}).get("sport_settings") or []
                 if "Ride" in (s.get("types") or [])), None)
    if not ride:
        return None, {"reason": "no Ride sport settings"}

    today = date.today()
    oldest = today - timedelta(days=2 * dw.WINDOW_DAYS - 1)
    base = {"oldest": oldest.isoformat(), "newest": today.isoformat(),
            "type": "Ride", "secs": ",".join(str(x) for x in dw.SECS)}
    endpoint = f"/athlete/{aid}/activity-power-curves"
    probe = {}

    fresh = get(endpoint, params=dict(base), optional=True)
    if fresh is None:
        probe["fresh"] = "request failed"
        return None, probe
    rows, _ = dw.rows_from_payload(fresh)
    probe["fresh"] = {"curves": len(rows)}
    if not rows:
        return None, probe

    best = {"fresh": dw.best_by_window(rows, today)}
    levels = {}
    for name in ("kj0", "kj1"):
        data = get(endpoint, params=dict(base, fatigue=name), optional=True)
        if data is None:
            probe[name] = "request failed"
            continue
        rws, kj = dw.rows_from_payload(data)
        probe[name] = {"after_kj": kj, "curves": len(rws),
                       "settings_after_kj": ride.get(f"after_{name}")}
        if not kj:
            continue                      # no such fatigued curve for this athlete
        levels[name] = kj
        best[name] = dw.best_by_window(rws, today)
    if not levels:
        return None, probe

    cur_from = today - timedelta(days=dw.WINDOW_DAYS - 1)
    prev_to = cur_from - timedelta(days=1)
    return {
        "secs": list(dw.SECS),
        "after_kj": levels,
        "window_days": dw.WINDOW_DAYS,
        "windows": {
            "current": {"from": cur_from.isoformat(), "to": today.isoformat()},
            "previous": {"from": oldest.isoformat(), "to": prev_to.isoformat()},
        },
        "best": best,
    }, probe


def fetch_activities(aid, days):
    """Activity summaries carrying the fields the durability and repeatability
    contracts need. Full streams are not downloaded — only what Intervals.icu
    has already computed."""
    oldest = (date.today() - timedelta(days=days)).isoformat()
    newest = date.today().isoformat()
    acts = get(f"/athlete/{aid}/activities",
               params={"oldest": oldest, "newest": newest}) or []

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
        # High-intensity / neuromuscular load density (M3, engine/load_metrics.py).
        # Not populated for a workout prescribed by %FTP rather than absolute
        # watts, or for a non-power sport -- reported as unavailable there,
        # never guessed.
        ("icu_joules_above_ftp", "joules_above_ftp"),
        # Planned-vs-done (engine/execution.py). paired_event_id is
        # Intervals.icu's own pairing of this activity to a planned event;
        # compliance, rpe and feel are what the athlete/Intervals.icu recorded.
        # Left out of the row when not recorded -- never defaulted to 0.
        ("id", "id"), ("paired_event_id", "paired_event_id"),
        ("compliance", "compliance"), ("icu_rpe", "rpe"), ("feel", "feel"),
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
              params={"oldest": today, "newest": future}) or []

    out = []
    for e in evs:
        out.append({
            "id": e.get("id"),
            # external_id says which events this system uploaded (push_block's
            # "infame-<athlete>-..."); description holds their steps. Both feed
            # the PMC projection and the plan checks of later weeks (v7.32).
            "external_id": e.get("external_id"),
            "description": e.get("description") or "",
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


RECENT_SESSIONS_DAYS = 56  # 8 weeks — enough for the monotony check to have
                           # real history without pulling the whole macrocycle.


def fetch_recent_sessions(aid, days=RECENT_SESSIONS_DAYS):
    """The last `days` days of events, looked backward instead of forward.

    Same endpoint as fetch_events(), same row shape, plus the one field that
    function does not need: `description` — the event's own saved text. For
    a session the coach designed, this is the exact code block (Warmup /
    Main Set / Cooldown, one line per step) that was pasted into
    Intervals.icu or sent by push_block. For anything else on the calendar
    (an imported ride, a race with no code block, a rest day), it is empty.

    Returns every event in the window regardless of content — deciding what
    counts as a real, classifiable session is the classifier's job, not the
    fetcher's.
    """
    oldest = (date.today() - timedelta(days=days)).isoformat()
    newest = date.today().isoformat()
    evs = get(f"/athlete/{aid}/events",
              params={"oldest": oldest, "newest": newest}) or []

    out = []
    for e in evs:
        out.append({
            "id": e.get("id"),
            "date": (e.get("start_date_local") or "")[:10],
            "name": e.get("name"),
            "category": e.get("category"),
            "type": e.get("type"),
            "description": e.get("description") or "",
            "planned_load": e.get("icu_training_load") or e.get("training_load"),
            "planned_time": e.get("moving_time"),
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
    a = get(f"/athlete/{aid}") or {}
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
            "after_kj0": s.get("after_kj0"),
            "after_kj1": s.get("after_kj1"),
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

    print("   fatigued power curves (only if the athlete has them defined)...")
    fatigue_curves, fatigue_probe = fetch_fatigue_curves(aid, profile)
    print("      " + ("fetched" if fatigue_curves else "none defined for this athlete, skipped"))

    print("   power and pace curves...")
    curves = fetch_curves(aid)
    for kind, windows in curves.items():
        print(f"      {kind}: {', '.join(sorted(windows))}")
    if not curves:
        print("      none available")

    print("   planned events...")
    events = fetch_events(aid)
    print(f"      {len(events)} events")

    print("   recent sessions (past 8 weeks, for the architecture record)...")
    recent_sessions = fetch_recent_sessions(aid)
    with_text = sum(1 for s in recent_sessions if s["description"].strip())
    print(f"      {len(recent_sessions)} events, {with_text} with a code block")

    payload = {
        "schema_version": 2,
        "fetched_at": date.today().isoformat(),
        "window_days": days,
        "profile": profile,
        "wellness": wellness,
        "pmc_series": pmc,
        "activities": activities,
        "curves": curves,
        "events": events,
        "recent_sessions": recent_sessions,
    }
    if fatigue_curves:
        payload["fatigue_curves"] = fatigue_curves
    if fatigue_probe:
        payload["fatigue_probe"] = fatigue_probe

    dest = os.path.join(outdir, str(aid))
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, "athlete_data.json")
    # Written to a temporary file first and swapped in whole (v7.32): an
    # interrupted write never leaves a half file where the good one was.
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
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
