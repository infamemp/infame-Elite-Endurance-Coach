"""
make_fixtures.py — Infame Elite Endurance Coach v6, Stage 7
============================================================
Generates the synthetic athlete datasets the golden tests run against.

Why synthetic rather than real athlete data:
  - Real data is gitignored for privacy and cannot live in the repository
  - Real data changes every time the fetcher runs, so a frozen expectation rots
  - Edge cases have to be constructed; they cannot be waited for

Why dates are relative:
  The engine reads today's date. A fixture with fixed calendar dates would drift
  out of every rolling window within weeks and the tests would fail for reasons
  that have nothing to do with the code. Every date here is computed backward
  from today, so the fixtures stay in-window forever.

Usage:
    python tests/make_fixtures.py

Writes tests/fixtures/<case>/athlete_data.json for each case.
"""

import json
import os
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "tests", "fixtures")


def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()


def pmc_series(days, ctl_start, ctl_end, atl_offset):
    """A linear CTL ramp with ATL trailing it by a fixed offset."""
    out = []
    for i in range(days, 0, -1):
        frac = (days - i) / max(days - 1, 1)
        ctl = round(ctl_start + (ctl_end - ctl_start) * frac, 1)
        atl = round(ctl + atl_offset, 1)
        out.append({"date": days_ago(i), "ctl": ctl, "atl": atl,
                    "tsb": round(ctl - atl, 1), "ramp_rate": 1.5})
    return out


def wellness(days, hrv_base, hrv_recent=None):
    """Daily HRV. hrv_recent, when given, applies to the last 7 days."""
    out = []
    for i in range(days, 0, -1):
        h = hrv_recent if (hrv_recent and i <= 7) else hrv_base
        out.append({"date": days_ago(i), "hrv": h, "resting_hr": 48,
                    "sleep_secs": 27000})
    return out


def activities(count, spacing, load, *, decoupling=None, duration=3600,
               w_prime=None, depletion=None, atype="Ride", watts=200):
    out = []
    for i in range(count):
        a = {"date": days_ago(i * spacing + 1), "type": atype,
             "moving_time": duration, "training_load": load}
        if watts:
            a["average_watts"] = watts
            a["weighted_avg_watts"] = watts + 10
        if decoupling is not None:
            a["decoupling"] = decoupling[i % len(decoupling)] \
                if isinstance(decoupling, list) else decoupling
        if w_prime:
            a["w_prime"] = w_prime
            a["max_wbal_depletion"] = depletion[i % len(depletion)] \
                if isinstance(depletion, list) else depletion
        out.append(a)
    out.reverse()
    return out


def power_curves(w42, w90, w1y):
    def pts(d):
        return {"points": {k: {"secs": int(k), "watts": v} for k, v in d.items()},
                "window": {"id": "", "from": days_ago(42), "to": days_ago(0)}}
    return {"power": {"42d": pts(w42), "90d": pts(w90), "1y": pts(w1y)}}


def pace_curves(p42, p90, p1y):
    def pts(d):
        return {"points": {k: {"metres": int(k), "seconds": v,
                               "speed_ms": round(int(k) / v, 3)}
                           for k, v in d.items()},
                "window": {"id": "", "from": days_ago(42), "to": days_ago(0)}}
    return {"pace": {"42d": pts(p42), "90d": pts(p90), "1y": pts(p1y)}}


def profile(name, weight=72.0, sex="M", ftp=250):
    return {"id": "TEST", "name": name, "sex": sex, "weight": weight,
            "height": 178, "resting_hr": 48, "timezone": "America/Mexico_City",
            "sport_settings": [{"types": ["Ride", "VirtualRide"], "ftp": ftp,
                                "lthr": 165, "max_hr": 188, "w_prime": 20000}]}


def wrap(prof, wells, pmc, acts, curves, events=None):
    return {"schema_version": 1, "fetched_at": date.today().isoformat(),
            "window_days": 180, "profile": prof, "wellness": wells,
            "pmc_series": pmc, "activities": acts, "curves": curves,
            "events": events or []}


# ══════════════════════════════════════════════════════════════════
# CASES
# ══════════════════════════════════════════════════════════════════

def case_cyclist_building():
    """Consistent cyclist gaining across every anchor. Expect broad_progression,
    stable durability, and no testing recommendations — every anchor is at or
    near its yearly best."""
    return wrap(
        profile("Building Cyclist", weight=70.0, ftp=280),
        wellness(120, 55),
        pmc_series(120, 40, 68, 12),
        activities(40, 3, 85, decoupling=[2.0, 2.5, 1.8, 2.2],
                   w_prime=22000, depletion=[14000, 15500, 13000]),
        power_curves(
            {"5": 1150, "60": 610, "300": 360, "1200": 300, "3600": 272},
            {"5": 1120, "60": 590, "300": 348, "1200": 290, "3600": 262},
            {"5": 1150, "60": 610, "300": 360, "1200": 300, "3600": 272}),
    )


def case_cyclist_plateau():
    """Flat trend with the aerobic end near the yearly best and the short end
    well below it. Expect plateau.

    The 1200s anchor is set deliberately at -2.0% against the 90-day window: that
    sits inside the band between the old stable floor (-1.0) and the widened one
    (-2.5), so any future change to the cycling delta bands moves this fixture's
    output and the golden comparison catches it."""
    return wrap(
        profile("Plateau Cyclist", weight=73.5, ftp=205),
        wellness(120, 36),
        pmc_series(120, 60, 66, 17),
        activities(40, 3, 95, decoupling=[6.8, 7.2, 6.5, 7.0],
                   w_prime=20000, depletion=[16000, 17000, 15500]),
        power_curves(
            {"5": 431, "60": 343, "300": 236, "1200": 198, "3600": 185},
            {"5": 523, "60": 343, "300": 236, "1200": 202, "3600": 185},
            {"5": 748, "60": 374, "300": 280, "1200": 233, "3600": 191}),
    )


def case_cyclist_regression():
    """A majority of anchors down against the 90-day window. Expect regression —
    the one state that requires a majority, not just any decline."""
    return wrap(
        profile("Regressing Cyclist", weight=75.0, ftp=230),
        wellness(120, 42, hrv_recent=33),
        pmc_series(120, 75, 52, 6),
        activities(30, 4, 60, decoupling=[11.5, 12.0, 10.8, 11.2]),
        power_curves(
            {"5": 800, "60": 420, "300": 250, "1200": 215, "3600": 196},
            {"5": 900, "60": 470, "300": 275, "1200": 235, "3600": 210},
            {"5": 980, "60": 510, "300": 300, "1200": 255, "3600": 228}),
    )


def case_runner():
    """Running athlete with pace curves and no power. Exercises the pace branch
    of curve analysis and the running delta bands."""
    return wrap(
        profile("Runner", weight=64.0, ftp=None),
        wellness(120, 62),
        pmc_series(120, 45, 58, 14),
        activities(36, 3, 70, decoupling=[3.5, 4.0, 3.2, 3.8], atype="Run",
                   watts=None),
        pace_curves(
            {"400": 62, "1000": 172, "3000": 570, "5000": 990, "10000": 2100,
             "21097": 4740},
            {"400": 63, "1000": 175, "3000": 578, "5000": 1005, "10000": 2130,
             "21097": 4800},
            {"400": 58, "1000": 163, "3000": 540, "5000": 940, "10000": 2010,
             "21097": 4560}),
    )


def case_sparse():
    """Barely any data. Every analysis must refuse cleanly with a stated reason
    rather than producing a confident answer from nothing."""
    return wrap(
        profile("Sparse Athlete", weight=80.0, ftp=180),
        wellness(10, 40),
        pmc_series(10, 8, 9, 3),
        activities(4, 7, 30),
        {},
    )


def case_overreached():
    """Deep negative TSB with workload inside the safe ACWR range and durability
    holding — the validation gate must downgrade maladaptation_risk to
    functional_overreach."""
    return wrap(
        profile("Overreached Cyclist", weight=68.0, ftp=300),
        wellness(120, 50),
        pmc_series(120, 70, 95, 35),
        activities(45, 2, 130, decoupling=[2.5, 3.0, 2.2, 2.8]),
        power_curves(
            {"5": 1000, "60": 560, "300": 340, "1200": 300, "3600": 278},
            {"5": 1000, "60": 560, "300": 340, "1200": 300, "3600": 278},
            {"5": 1020, "60": 570, "300": 345, "1200": 305, "3600": 282}),
    )


def case_w_prime_overflow():
    """Depletion recorded above 100% of the configured W'. The engine must clamp
    it, count it, and raise the data-quality flag rather than reporting an
    impossible value."""
    return wrap(
        profile("Bad W-prime", weight=71.0, ftp=245),
        wellness(120, 48),
        pmc_series(120, 50, 58, 10),
        activities(30, 4, 80, decoupling=[4.0, 4.5],
                   w_prime=12000, depletion=[15000, 14000, 9000]),
        power_curves(
            {"5": 900, "60": 480, "300": 300, "1200": 258, "3600": 238},
            {"5": 900, "60": 480, "300": 300, "1200": 258, "3600": 238},
            {"5": 950, "60": 500, "300": 315, "1200": 268, "3600": 245}),
    )


CASES = {
    "cyclist_building": case_cyclist_building,
    "cyclist_plateau": case_cyclist_plateau,
    "cyclist_regression": case_cyclist_regression,
    "runner": case_runner,
    "sparse": case_sparse,
    "overreached": case_overreached,
    "w_prime_overflow": case_w_prime_overflow,
}


def main():
    os.makedirs(FIXTURES, exist_ok=True)
    for name, fn in CASES.items():
        dest = os.path.join(FIXTURES, name)
        os.makedirs(dest, exist_ok=True)
        data = fn()
        with open(os.path.join(dest, "athlete_data.json"), "w",
                  encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  {name}: {len(data['activities'])} activities, "
              f"{len(data['pmc_series'])} PMC days")
    print(f"\nWrote {len(CASES)} fixtures to tests/fixtures/")


if __name__ == "__main__":
    main()
