"""
load_metrics.py — Infame Elite Endurance Coach v7
===================================================
Foster monotony & strain (M2), and high-intensity / neuromuscular load
density (M3). Both are informational: they never gate anything and are
never a requirement for anyone.

Monotony/strain is read from two vantage points, and they must agree on
the same number for the same week, so the arithmetic lives in exactly one
place -- week_monotony_strain() -- and both callers use it:

  Past days     monotony_signal() -- the trailing real 7 days. Consumed by
                build_state.py as a #STATE signal, alongside PMC/HRV/ACWR/
                durability.
  Planned week  verify/validate_block.py calls week_monotony_strain()
                directly, after filling in the days a block does not cover
                with the athlete's real recent history (or a future day's
                implicit zero) -- "catch monotony before upload," not just
                after.

Nothing here blocks anything, and nothing here is required. A flagged week
is a prompt for coaching judgement, not a defect.

All thresholds come from config/decision_thresholds.yaml (`load_monotony`,
`neuromuscular_density`). This file contains no numbers of its own besides
the Foster formula itself.
"""

from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta


from shared import iso_day as _d  # noqa: E402 — shared parser (v7.33)


# ══════════════════════════════════════════════════════════════════
# M2 — FOSTER MONOTONY & STRAIN
# ══════════════════════════════════════════════════════════════════

def week_monotony_strain(daily_loads):
    """Foster monotony & strain over exactly 7 daily loads (any order).

    monotony = mean / population-stdev; strain = weekly total * monotony.
    Population standard deviation, not sample: these 7 values ARE the week
    being judged, not a sample drawn from something larger.

    Zero variance is handled explicitly rather than left to raise:
      - all zero (mean 0): no training to be monotonous about. verdict
        "no_load", monotony/strain reported as None.
      - identical nonzero load every day: the ratio is mathematically
        undefined, but by construction this IS the most monotonous week
        possible, so it is reported as "at_risk" directly rather than as a
        division error. monotony/strain stay None -- there is no number to
        give, only the verdict.

    The caller applies the configured risk_threshold to the ordinary case
    via verdict_for(); the two zero-variance verdicts above are already
    final.
    """
    loads = list(daily_loads)
    mean = statistics.mean(loads)
    sd = statistics.pstdev(loads)
    weekly_load = round(sum(loads), 1)

    if sd == 0:
        if mean == 0:
            return {"monotony": None, "strain": None, "weekly_load": weekly_load,
                    "verdict": "no_load",
                    "note": "no training load across the week"}
        return {"monotony": None, "strain": None, "weekly_load": weekly_load,
                "verdict": "at_risk",
                "note": "identical load every day — the ratio is undefined, "
                        "but a flat week is the most monotonous week possible"}

    monotony = round(mean / sd, 2)
    return {"monotony": monotony, "strain": round(weekly_load * monotony, 1),
            "weekly_load": weekly_load, "verdict": None, "note": None}


def verdict_for(result, risk_threshold):
    """Apply the configured risk threshold to a week_monotony_strain()
    result. The zero-variance cases already carry a final verdict; only the
    ordinary numeric case needs the threshold applied here."""
    if result["verdict"] is not None:
        return result["verdict"]
    return "at_risk" if result["monotony"] > risk_threshold else "normal"


def monotony_signal(data, thresholds, as_of=None):
    """Foster monotony & strain over the trailing real 7 days. Every day in
    the window counts, including one with nothing logged -- that is a real
    zero, not missing data, so unlike ACWR this signal needs no minimum
    history and is always available once there is a today to look back
    from."""
    as_of = as_of or date.today()
    start = as_of - timedelta(days=6)
    acts = data.get("activities") or []

    daily = {start + timedelta(days=i): 0.0 for i in range(7)}
    for a in acts:
        if not a.get("date"):
            continue
        try:
            ad = _d(a["date"])
        except (ValueError, TypeError):
            continue
        if ad in daily:
            daily[ad] += a.get("training_load") or 0

    loads = [daily[start + timedelta(days=i)] for i in range(7)]
    cfg = thresholds["load_monotony"]
    result = week_monotony_strain(loads)
    result["verdict"] = verdict_for(result, cfg["risk_threshold"])
    result.update({
        "available": True,
        "risk_threshold": cfg["risk_threshold"],
        "window": {"from": start.isoformat(), "to": as_of.isoformat()},
        "source": "activity training_load, trailing 7 days, padded with 0",
    })
    return result


# ══════════════════════════════════════════════════════════════════
# M3 — NEUROMUSCULAR / HIGH-INTENSITY DENSITY
# ══════════════════════════════════════════════════════════════════

def neuromuscular_density_signal(data, thresholds, as_of=None):
    """High-intensity / neuromuscular load density: total kJ above FTP over
    the trailing 7 days, and how many of those days crossed the per-day
    threshold. TSS is built from an averaged intensity factor and
    undercounts short supra-threshold efforts (sprints, attacks) -- this
    reads the neuromuscular class's own field instead of inferring it from
    TSS.

    Only days with a logged icu_joules_above_ftp count -- a workout
    prescribed by %FTP rather than absolute watts, or a non-power sport,
    does not populate it, and a missing field is not the same as a
    confirmed zero. Not available when nothing in the window carries it."""
    as_of = as_of or date.today()
    start = as_of - timedelta(days=6)
    acts = data.get("activities") or []
    cfg = thresholds["neuromuscular_density"]

    daily = {}
    for a in acts:
        if not a.get("date") or a.get("joules_above_ftp") is None:
            continue
        try:
            ad = _d(a["date"])
        except (ValueError, TypeError):
            continue
        if start <= ad <= as_of:
            daily[ad] = daily.get(ad, 0) + a["joules_above_ftp"]

    if not daily:
        return {"available": False,
                "reason": "no icu_joules_above_ftp on any activity in the "
                          "last 7 days — workouts prescribed by %FTP rather "
                          "than absolute watts, or a non-power sport, do "
                          "not populate it"}

    kj_by_day = {dt: j / 1000 for dt, j in daily.items()}
    total_kj = round(sum(kj_by_day.values()), 1)
    days_over = sum(1 for kj in kj_by_day.values() if kj > cfg["day_kj_threshold"])

    return {
        "available": True,
        "total_kj_7d": total_kj,
        "days_over_threshold": days_over,
        "day_kj_threshold": cfg["day_kj_threshold"],
        "days_with_data": len(kj_by_day),
        "window": {"from": start.isoformat(), "to": as_of.isoformat()},
        "source": "activity icu_joules_above_ftp, trailing 7 days",
    }
