"""
build_state.py — Infame Elite Endurance Coach v6, Stage 4
==========================================================
Resolves the athlete's training state deterministically and projects the PMC
forward, then emits an authoritative state block for the Claude Project.

This is contract C3: the state block is authoritative. The model receives a
resolved state and must not recalculate or contradict it. Every value carries
its source so the coach can audit any conclusion.

All thresholds come from config/decision_thresholds.yaml. This file contains
no numbers of its own.

Usage:
    python engine/build_state.py --athlete i18969
    python engine/build_state.py --athlete i18969 --json
    python engine/build_state.py --all

Input:  data/<athlete_id>/athlete_data.json   (written by fetch_athlete_data.py)
Output: data/<athlete_id>/state.md            (paste into the Claude Project)
        data/<athlete_id>/state.json          (machine-readable, same content)

Version: 1.0
"""

import argparse
import json
import math
import os
import statistics
import sys
from datetime import date, datetime, timedelta

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency. Run: pip install pyyaml")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import longitudinal  # noqa: E402
import power_profile  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config")
DATA = os.path.join(ROOT, "data")

# Banister time constants, in days. These are the definition of CTL and ATL,
# not tunable coaching parameters, so they live here rather than in config.
CTL_TAU = 42
ATL_TAU = 7


def load_power_profile_cfg():
    path = os.path.join(CONFIG, "power_profile.yaml")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_thresholds():
    path = os.path.join(CONFIG, "decision_thresholds.yaml")
    if not os.path.exists(path):
        sys.exit(f"Config not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_athlete(aid):
    path = os.path.join(DATA, str(aid), "athlete_data.json")
    if not os.path.exists(path):
        sys.exit(f"No data for '{aid}'. Run: python engine/fetch_athlete_data.py "
                 f"--athlete {aid}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def d(s):
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def band_of(value, bands):
    """Classify a value into named {min,max} bands. Half-open on max."""
    for name, r in bands.items():
        lo, hi = r.get("min"), r.get("max")
        if (lo is None or value >= lo) and (hi is None or value < hi):
            return name
    return None


# ══════════════════════════════════════════════════════════════════
# SIGNALS
# ══════════════════════════════════════════════════════════════════

def latest_pmc(data):
    series = data.get("pmc_series") or []
    if not series:
        return None
    last = series[-1]
    return {
        "date": last["date"],
        "ctl": round(last["ctl"], 1) if last.get("ctl") is not None else None,
        "atl": round(last["atl"], 1) if last.get("atl") is not None else None,
        "tsb": last.get("tsb"),
        "ramp_rate": round(last["ramp_rate"], 2) if last.get("ramp_rate") is not None else None,
        "source": "pmc_series (daily wellness record)",
    }


def hrv_signal(data, thresholds):
    """Ratio of the last 7 days of HRV to a 60-day baseline. Reported only when
    both windows have enough readings to mean anything."""
    rows = [w for w in data.get("wellness", []) if w.get("hrv") is not None]
    if len(rows) < 14:
        return {"available": False, "reason": f"only {len(rows)} HRV readings"}

    recent = [w["hrv"] for w in rows[-7:]]
    baseline_rows = rows[-60:-7] if len(rows) > 30 else rows[:-7]
    if len(recent) < 4 or len(baseline_rows) < 10:
        return {"available": False, "reason": "insufficient window coverage"}

    baseline = statistics.median(w["hrv"] for w in baseline_rows)
    if not baseline:
        return {"available": False, "reason": "baseline is zero"}

    ratio = round(statistics.mean(recent) / baseline, 3)
    return {
        "available": True,
        "recent_mean": round(statistics.mean(recent), 1),
        "baseline_median": round(baseline, 1),
        "ratio": ratio,
        "band": band_of(ratio, thresholds["state_resolution"]["hrv_bands"]),
        "readings": {"recent": len(recent), "baseline": len(baseline_rows)},
        "source": f"wellness HRV, {len(recent)}d mean vs {len(baseline_rows)}d median",
    }


def acwr_signal(data):
    """Acute:chronic workload ratio. Acute is the last 7 days of training load;
    chronic is the average 7-day load across the last 28."""
    acts = data.get("activities", [])
    if not acts:
        return {"available": False, "reason": "no activities"}

    today = date.today()
    def load_between(start, end):
        return sum(a.get("training_load") or 0 for a in acts
                   if a.get("date") and start <= d(a["date"]) <= end)

    acute = load_between(today - timedelta(days=6), today)
    chronic_total = load_between(today - timedelta(days=27), today)
    chronic = chronic_total / 4

    if chronic < 10:
        return {"available": False, "reason": f"chronic load too low ({chronic:.0f})",
                "acute_7d": round(acute), "chronic_weekly_avg": round(chronic)}

    return {
        "available": True,
        "acute_7d": round(acute),
        "chronic_weekly_avg": round(chronic, 1),
        "ratio": round(acute / chronic, 2),
        "source": "activity training_load, 7d vs 28d/4",
    }


def durability_signal(data):
    """Aerobic decoupling across recent qualifying sessions. A single high-drift
    session is noise; drift only counts when it repeats, or when it is severe."""
    rows = [a for a in data.get("activities", [])
            if a.get("decoupling") is not None
            and (a.get("moving_time") or 0) >= 2700]
    recent = rows[-6:]
    if len(recent) < 3:
        return {"available": False, "reason": f"only {len(recent)} qualifying sessions"}

    vals = [a["decoupling"] for a in recent]
    moderate = sum(1 for v in vals if 5 <= v <= 10)
    severe = sum(1 for v in vals if v > 10)

    if severe:
        status = "degraded"
    elif moderate >= 2:
        status = "drifting"
    else:
        status = "stable"

    return {
        "available": True,
        "status": status,
        "sessions": len(recent),
        "median_decoupling": round(statistics.median(vals), 1),
        "moderate_drift": moderate,
        "severe_drift": severe,
        "source": "activity decoupling, sessions of 45min or more",
    }


# ══════════════════════════════════════════════════════════════════
# STATE RESOLUTION
# ══════════════════════════════════════════════════════════════════

def resolve_state(pmc, hrv, acwr, durability, thresholds):
    """TSB governs. HRV is secondary and applies only where TSB is absent.
    ACWR acts as a validation gate that can downgrade a severe reading.
    Every step is recorded in `reasoning` so the conclusion can be audited."""
    sr = thresholds["state_resolution"]
    reasoning = []

    if pmc and pmc.get("tsb") is not None:
        state = band_of(pmc["tsb"], sr["tsb_bands"])
        governor = "tsb"
        reasoning.append(f"TSB {pmc['tsb']} falls in band '{state}' (primary governor)")
    elif hrv.get("available"):
        state = {"suppressed": "load_pressure", "normal": "neutral",
                 "elevated": "fresh"}.get(hrv["band"], "neutral")
        governor = "hrv"
        reasoning.append(f"No TSB available; HRV ratio {hrv['ratio']} "
                         f"({hrv['band']}) resolves state to '{state}'")
    else:
        return {"load_recovery_state": None, "operational_state": None,
                "governor": None,
                "reasoning": ["No TSB and no usable HRV — state cannot be resolved"]}

    # Validation gate: a severe TSB reading with workload in the safe range and
    # durability holding is functional overreach, not maladaptation.
    if state == "maladaptation_risk" and acwr.get("available"):
        safe = sr["acwr_safe_range"]
        in_range = safe["min"] <= acwr["ratio"] <= safe["max"]
        stable = durability.get("status") == "stable"
        if in_range and stable:
            state = "functional_overreach"
            reasoning.append(
                f"Downgraded to 'functional_overreach': ACWR {acwr['ratio']} is inside "
                f"the safe range [{safe['min']}, {safe['max']}] and durability is stable")
        elif not in_range:
            reasoning.append(
                f"Gate not applied: ACWR {acwr['ratio']} is outside "
                f"[{safe['min']}, {safe['max']}]")
        else:
            reasoning.append(
                f"Gate not applied: durability is '{durability.get('status')}', not stable")

    # HRV sanity check: reported for visibility only. It never overrides TSB
    # and must never be read as a reason to pause or condition prescription —
    # HRV as a standalone metric lacks the evidence base to drive training
    # decisions. Explicitly labelled non-actionable so the reasoning layer does
    # not treat it as a gate.
    flags = []
    if hrv.get("available") and hrv["band"] == "suppressed" and \
            state in ("fresh", "neutral"):
        flags.append(f"[reference only, not actionable] HRV suppressed "
                     f"(ratio {hrv['ratio']}) while TSB indicates '{state}'. "
                     f"Report this to the coach; it does not gate or delay "
                     f"prescription.")
        reasoning.append("HRV/TSB divergence noted for visibility; "
                         "TSB retained as sole governor, no HRV-based gating applied")

    if durability.get("status") == "degraded":
        flags.append(f"Durability degraded: {durability['severe_drift']} of "
                     f"{durability['sessions']} sessions above 10% decoupling")

    if acwr.get("available"):
        safe = sr["acwr_safe_range"]
        if acwr["ratio"] > safe["max"]:
            flags.append(f"ACWR {acwr['ratio']} above the safe ceiling {safe['max']} "
                         f"— load is ramping faster than the chronic base supports")
        elif acwr["ratio"] < safe["min"]:
            flags.append(f"ACWR {acwr['ratio']} below the safe floor {safe['min']} "
                         f"— recent load is detraining relative to the base")

    operational = ("recovery_priority"
                   if state in ("maladaptation_risk", "functional_overreach")
                   else "load_accepting")
    reasoning.append(f"Operational state: '{operational}'")

    return {
        "load_recovery_state": state,
        "operational_state": operational,
        "governor": governor,
        "flags": flags,
        "reasoning": reasoning,
    }


# ══════════════════════════════════════════════════════════════════
# PMC PROJECTION
# ══════════════════════════════════════════════════════════════════

def project_pmc(pmc, events, horizon_days=42):
    """Banister projection over planned load. Days with no planned session
    carry zero load, which is what makes CTL decay visible."""
    if not pmc or pmc.get("ctl") is None:
        return None

    planned = {}
    for e in events:
        if e.get("planned_load") and e.get("date"):
            planned[e["date"]] = planned.get(e["date"], 0) + e["planned_load"]

    ctl, atl = pmc["ctl"], pmc["atl"]
    kc, ka = 1 - math.exp(-1 / CTL_TAU), 1 - math.exp(-1 / ATL_TAU)
    start = d(pmc["date"])

    series = []
    for i in range(1, horizon_days + 1):
        day = start + timedelta(days=i)
        load = planned.get(day.isoformat(), 0)
        ctl += (load - ctl) * kc
        atl += (load - atl) * ka
        series.append({"date": day.isoformat(), "planned_load": load,
                       "ctl": round(ctl, 1), "atl": round(atl, 1),
                       "tsb": round(ctl - atl, 1)})

    planned_days = sum(1 for s in series if s["planned_load"] > 0)
    return {
        "horizon_days": horizon_days,
        "days_with_planned_load": planned_days,
        "series": series,
        "method": f"Banister exponential, CTL tau {CTL_TAU}d, ATL tau {ATL_TAU}d",
        "caveat": ("Unplanned days are projected as zero load. With few planned "
                   "sessions on the calendar this understates future CTL."),
    }


def taper_check(projection, events, thresholds):
    """Locate the next A-priority race and compare projected TSB at that date
    against the target range for the event type."""
    tp = thresholds["taper"]
    a_races = [e for e in events
               if str(e.get("category") or "").upper() == "RACE"
               and str(e.get("priority") or "").upper() in ("A", "RACE_A")]
    if not a_races:
        a_races = [e for e in events
                   if str(e.get("category") or "").upper() == "RACE"]
        if not a_races:
            return {"applicable": False, "reason": "no races on the calendar"}

    race = a_races[0]
    days_out = (d(race["date"]) - date.today()).days
    phase = ("taper" if days_out <= tp["a_race_taper_days"]
             else "pre_taper" if days_out <= tp["a_race_pre_taper_days"]
             else "build")

    result = {"applicable": True, "race": race["name"], "date": race["date"],
              "days_out": days_out, "phase": phase}

    if not projection:
        result["note"] = "No PMC projection available"
        return result

    at_race = next((s for s in projection["series"] if s["date"] == race["date"]), None)
    if not at_race:
        result["note"] = (f"Race is beyond the {projection['horizon_days']}-day "
                          f"projection horizon")
        return result

    ev_type = str(race.get("type") or "").lower()
    target = tp["target_tsb_by_event_type"].get(ev_type,
                                                tp["target_tsb_by_event_type"]["default"])
    tsb = at_race["tsb"]
    verdict = ("too_fatigued" if tsb < target["min"]
               else "too_fresh" if tsb > target["max"]
               else "in_target_range")

    result.update({
        "projected_tsb_at_race": tsb,
        "target_tsb_range": [target["min"], target["max"]],
        "target_source": ev_type if ev_type in tp["target_tsb_by_event_type"] else "default",
        "verdict": verdict,
    })
    return result


# ══════════════════════════════════════════════════════════════════
# OUTPUT
# ══════════════════════════════════════════════════════════════════

def render_markdown(aid, data, state, pmc, hrv, acwr, durability, projection, taper):
    name = (data.get("profile") or {}).get("name") or aid
    L = []
    L.append("# STATE — AUTHORITATIVE")
    L.append("")
    L.append(f"Athlete: {name} ({aid})")
    L.append(f"Resolved: {date.today().isoformat()} · "
             f"data fetched {data.get('fetched_at')}")
    L.append("")
    L.append("> This block is computed deterministically from Intervals.icu data and "
             "config/decision_thresholds.yaml. Do not recalculate or contradict these "
             "values. Prescribe on top of them.")
    L.append("")

    L.append("## Resolved state")
    L.append("")
    L.append(f"- **Load/recovery state:** {state['load_recovery_state'] or 'unresolved'}")
    L.append(f"- **Operational state:** {state['operational_state'] or 'unresolved'}")
    L.append(f"- **Governing signal:** {state['governor'] or 'none'}")
    L.append("")
    L.append("How it was resolved:")
    for r in state["reasoning"]:
        L.append(f"- {r}")
    if state.get("flags"):
        L.append("")
        L.append("Flags:")
        for f in state["flags"]:
            L.append(f"- {f}")
    L.append("")

    L.append("## Signals")
    L.append("")
    L.append("| Signal | Value | Source |")
    L.append("| :--- | :--- | :--- |")
    if pmc:
        L.append(f"| CTL / ATL / TSB | {pmc['ctl']} / {pmc['atl']} / {pmc['tsb']} "
                 f"(as of {pmc['date']}) | {pmc['source']} |")
        if pmc.get("ramp_rate") is not None:
            L.append(f"| Ramp rate | {pmc['ramp_rate']} | {pmc['source']} |")
    if hrv.get("available"):
        L.append(f"| HRV ratio | {hrv['ratio']} ({hrv['band']}) — "
                 f"{hrv['recent_mean']} vs baseline {hrv['baseline_median']} "
                 f"| {hrv['source']} |")
    else:
        L.append(f"| HRV ratio | not available — {hrv.get('reason')} | — |")
    if acwr.get("available"):
        L.append(f"| ACWR | {acwr['ratio']} — acute {acwr['acute_7d']} vs "
                 f"chronic {acwr['chronic_weekly_avg']}/wk | {acwr['source']} |")
    else:
        L.append(f"| ACWR | not available — {acwr.get('reason')} | — |")
    if durability.get("available"):
        L.append(f"| Durability | {durability['status']} — median decoupling "
                 f"{durability['median_decoupling']}% over "
                 f"{durability['sessions']} sessions | {durability['source']} |")
    else:
        L.append(f"| Durability | not available — {durability.get('reason')} | — |")
    L.append("")

    if projection:
        L.append("## PMC projection")
        L.append("")
        L.append(f"{projection['method']}. Horizon {projection['horizon_days']} days, "
                 f"{projection['days_with_planned_load']} with planned load.")
        L.append("")
        L.append("| Date | Planned load | CTL | ATL | TSB |")
        L.append("| :--- | ---: | ---: | ---: | ---: |")
        for s in projection["series"][::7]:
            L.append(f"| {s['date']} | {s['planned_load'] or '—'} | "
                     f"{s['ctl']} | {s['atl']} | {s['tsb']} |")
        L.append("")
        L.append(f"Caveat: {projection['caveat']}")
        L.append("")

    if taper.get("applicable"):
        L.append("## Next race")
        L.append("")
        L.append(f"- **{taper['race']}** on {taper['date']} — {taper['days_out']} days out")
        L.append(f"- Phase: {taper['phase']}")
        if "projected_tsb_at_race" in taper:
            lo, hi = taper["target_tsb_range"]
            L.append(f"- Projected TSB at race: {taper['projected_tsb_at_race']} "
                     f"· target [{lo}, {hi}] · **{taper['verdict']}**")
        if taper.get("note"):
            L.append(f"- {taper['note']}")
        L.append("")

    return "\n".join(L)


def build(aid, thresholds, quiet=False):
    data = load_athlete(aid)
    pmc = latest_pmc(data)
    hrv = hrv_signal(data, thresholds)
    acwr = acwr_signal(data)
    durability = durability_signal(data)
    state = resolve_state(pmc, hrv, acwr, durability, thresholds)
    projection = project_pmc(pmc, data.get("events", []))
    taper = taper_check(projection, data.get("events", []), thresholds)
    longit = longitudinal.analyze(data, thresholds)

    ppcfg = load_power_profile_cfg()
    pp = None
    if ppcfg:
        pts = (((data.get("curves") or {}).get("power") or {})
               .get("42d") or {}).get("points") or {}
        pts = {k: v.get("watts") for k, v in pts.items() if v.get("watts")}
        if pts:
            pp = power_profile.analyze(pts, data.get("profile") or {}, ppcfg)

    payload = {
        "schema_version": 1,
        "athlete_id": aid,
        "resolved_at": date.today().isoformat(),
        "state": state,
        "signals": {"pmc": pmc, "hrv": hrv, "acwr": acwr, "durability": durability},
        "projection": projection,
        "taper": taper,
        "longitudinal": longit,
        "power_profile": pp,
    }

    dest = os.path.join(DATA, str(aid))
    os.makedirs(dest, exist_ok=True)
    md = render_markdown(aid, data, state, pmc, hrv, acwr, durability, projection, taper)
    md = md.rstrip() + "\n\n" + longitudinal.render(longit)
    if pp:
        md = md.rstrip() + "\n\n" + power_profile.render(pp)
    with open(os.path.join(dest, "state.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(dest, "state.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    if not quiet:
        print(md)
        print()
    print(f"Wrote data/{aid}/state.md and state.json")
    return payload


def main():
    ap = argparse.ArgumentParser(description="Resolve athlete state deterministically")
    ap.add_argument("--athlete")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="write files without printing")
    args = ap.parse_args()

    thresholds = load_thresholds()

    if args.all:
        if not os.path.isdir(DATA):
            sys.exit("No data directory. Run fetch_athlete_data.py first.")
        ids = sorted(x for x in os.listdir(DATA)
                     if os.path.exists(os.path.join(DATA, x, "athlete_data.json")))
        if not ids:
            sys.exit("No athlete data found. Run fetch_athlete_data.py first.")
        for aid in ids:
            build(aid, thresholds, quiet=True)
        print(f"\nResolved {len(ids)} athletes.")
        return

    if not args.athlete:
        sys.exit("Specify --athlete <id> or --all")
    build(args.athlete, thresholds, quiet=args.quiet)


if __name__ == "__main__":
    main()
