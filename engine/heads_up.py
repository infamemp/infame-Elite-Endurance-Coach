"""
engine/heads_up.py — Infame Elite Endurance Coach v7
=====================================================
The short "read this first" list at the top of #STATE. When the coach starts
work on an athlete, it reads these lines out before planning, so the head
coach sees what may need fixing without asking for it.

Two kinds of line, deliberately kept apart:

  Check items   Something the head coach may want to fix in Intervals.icu or
                in the declared profile before planning: a threshold that is
                missing or looks out of date, no activity for a week, no
                declared profile. Reported only -- nothing here ever blocks a
                state, a block or an upload.

  Optional data Wellness coverage (HRV, resting HR, sleep, subjective) and
                whether W' is set. Information only. Few athletes keep these
                accurate, so a gap is never a fault, never a Check item and
                never a requirement.

Nothing here diagnoses or advises. Every number comes from
data/<id>/athlete_data.json and every threshold from the `heads_up` section
of config/decision_thresholds.yaml.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta

import execution


def _d(s):
    return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()


def _family_of(activity_type, sport_types):
    for family, types in (sport_types or {}).items():
        if activity_type in (types or []):
            return family
    return None


def _settings_for(activity_type, sport_settings):
    for s in sport_settings or []:
        if activity_type in (s.get("types") or []):
            return s
    return None


def _pct(n, total):
    return round(100 * n / total) if total else 0


def wellness_coverage(data, lookback_days, as_of=None):
    """Share of days in the lookback window with each wellness signal.
    Days are counted over the whole window, not just days that have a
    wellness row, so a device that stopped syncing shows as low coverage."""
    as_of = as_of or date.today()
    start = as_of - timedelta(days=lookback_days - 1)
    rows = [w for w in data.get("wellness") or []
            if w.get("date") and start <= _d(w["date"]) <= as_of]

    def days_with(*keys):
        return sum(1 for w in rows if any(w.get(k) is not None for k in keys))

    cov = {
        "window_days": lookback_days,
        "hrv_pct": _pct(days_with("hrv"), lookback_days),
        "resting_hr_pct": _pct(days_with("resting_hr"), lookback_days),
        "sleep_pct": _pct(days_with("sleep_secs", "sleep_score"), lookback_days),
        "subjective_pct": _pct(days_with("soreness", "fatigue_subjective",
                                         "stress", "mood"), lookback_days),
    }
    # The HRV ratio in #STATE reads the rMSSD field ("hrv"). Some devices
    # write only SDNN ("hrvSDNN"); the two are not interchangeable.
    sdnn_only = days_with("hrv_sdnn") > 0 and cov["hrv_pct"] == 0
    cov["hrv_sdnn_only"] = sdnn_only
    return cov


def analyze(data, aid, cfg, declared_profile_exists, as_of=None):
    """Build the heads-up. `cfg` is the `heads_up` section of
    decision_thresholds.yaml."""
    as_of = as_of or date.today()
    lookback = cfg["lookback_days"]
    sport_types = cfg.get("sport_types") or {}
    start = as_of - timedelta(days=lookback - 1)
    profile = data.get("profile") or {}
    settings = profile.get("sport_settings") or []

    checks = []

    if not declared_profile_exists:
        checks.append({
            "kind": "no_declared_profile",
            "text": f"No declared profile (config/athletes/{aid}.yaml): goals, "
                    f"availability and metric choices are unknown.",
        })

    acts = [a for a in data.get("activities") or [] if a.get("date")]
    if acts:
        last = max(_d(a["date"]) for a in acts)
        idle = (as_of - last).days
        if idle >= cfg["inactivity_days"]:
            checks.append({
                "kind": "inactive",
                "text": f"No activity for {idle} days (last: {last.isoformat()}).",
            })
    else:
        checks.append({"kind": "inactive",
                       "text": "No activities in the fetched window."})

    # Planned sessions with no activity paired to them (engine/execution.py).
    # "Unpaired", not "missed": skipped, or done and never paired -- only the
    # head coach knows which. Silent when the cached data cannot say.
    ex = execution.analyze(data, days=cfg.get("unpaired_lookback_days", 7),
                           as_of=as_of)
    if ex.get("available"):
        unp = [r for r in ex["sessions"] if r["status"] == "unpaired"]
        if unp:
            shown = "; ".join(f"{r['date']} {r['name'] or 'session'}" for r in unp[:3])
            more = f" (+{len(unp) - 3} more)" if len(unp) > 3 else ""
            checks.append({
                "kind": "unpaired_sessions",
                "text": f"{len(unp)} planned session(s) in the last "
                        f"{ex['window']['days']} days have no activity paired in "
                        f"Intervals.icu: {shown}{more}. Skipped, or done without "
                        f"pairing — ask before assuming.",
            })
        diff = [r for r in ex["sessions"] if r.get("adherence") == "done_differently"]
        if diff:
            shown = "; ".join(f"{r['date']} {r['name'] or 'session'} ({', '.join(r['differences'])})"
                              for r in diff[:3])
            more = f" (+{len(diff) - 3} more)" if len(diff) > 3 else ""
            checks.append({
                "kind": "done_differently",
                "text": f"{len(diff)} session(s) in the last {ex['window']['days']} days "
                        f"were done differently from the plan: {shown}{more}. Design the "
                        f"next week from what was done.",
            })

    # Sports trained in the lookback window, by activity type.
    recent = [a for a in acts if start <= _d(a["date"]) <= as_of]
    trained = {}
    for a in recent:
        fam = _family_of(a.get("type"), sport_types)
        if fam:
            trained.setdefault(a["type"], []).append(a)

    seen_settings = set()
    for atype, rows in sorted(trained.items()):
        fam = _family_of(atype, sport_types)
        s = _settings_for(atype, settings)
        if s is None:
            checks.append({
                "kind": "no_sport_settings",
                "text": f"{atype}: no sport settings in Intervals.icu, so no "
                        f"zones or thresholds for it.",
            })
            continue
        key = id(s)
        if key in seen_settings:
            continue
        seen_settings.add(key)
        label = "/".join(s.get("types") or [atype])

        if fam == "cycling":
            has_power = any(r.get("average_watts")
                            for t in (s.get("types") or [atype])
                            for r in trained.get(t, []))
            ftp, eftp = s.get("ftp"), s.get("eftp")
            if has_power and not ftp:
                checks.append({"kind": "missing_threshold",
                               "text": f"{label}: rides with power but no FTP set."})
            elif ftp and eftp:
                diff = 100 * (eftp - ftp) / ftp
                if abs(diff) > cfg["eftp_divergence_pct"]:
                    word = "higher" if diff > 0 else "lower"
                    checks.append({
                        "kind": "ftp_vs_eftp",
                        "text": f"{label}: FTP {ftp:.0f} W set, eFTP {eftp:.0f} W is "
                                f"{abs(diff):.1f}% {word} — the FTP may be out of date.",
                    })
        if fam == "running" and not s.get("threshold_pace"):
            checks.append({"kind": "missing_threshold",
                           "text": f"{label}: no threshold pace set."})
        if not s.get("lthr"):
            checks.append({"kind": "missing_threshold",
                           "text": f"{label}: no LTHR set."})

    coverage = wellness_coverage(data, lookback, as_of)
    w_prime_set = any(s.get("w_prime") for s in settings
                      if _family_of((s.get("types") or [None])[0], sport_types)
                      == "cycling")

    return {
        "checks": checks,
        "optional_data": {**coverage, "w_prime_set": w_prime_set},
    }


def render(section):
    """Render the heads-up block for state.md. Kept short on purpose."""
    L = ["## Heads-up — read before planning", ""]
    if section["checks"]:
        L.append("Check (reported, never blocking):")
        for c in section["checks"]:
            L.append(f"- {c['text']}")
    else:
        L.append("Check: nothing.")
    o = section["optional_data"]
    line = (f"Optional data, last {o['window_days']} days (never required): "
            f"HRV {o['hrv_pct']}% of days · resting HR {o['resting_hr_pct']}% · "
            f"sleep {o['sleep_pct']}% · subjective {o['subjective_pct']}% · "
            f"W′ {'set' if o['w_prime_set'] else 'not set'}.")
    if o.get("hrv_sdnn_only"):
        line += " HRV arrives only as SDNN; the HRV ratio needs rMSSD."
    L.append("")
    L.append(line)
    L.append("")
    return "\n".join(L)


def declared_profile_exists(config_dir, aid):
    return os.path.exists(os.path.join(config_dir, "athletes", f"{aid}.yaml"))
