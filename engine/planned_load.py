"""
engine/planned_load.py — Infame Elite Endurance Coach v7.38
============================================================
The load (TSS) of a planned session, computed the way Intervals.icu computes
the planned load it stores on the athlete's calendar, so the number in the
session header, the week totals and the plan checks are the same numbers
the calendar and the PMC will show.

Which method applies is set per target in config/decision_thresholds.yaml
(tss_rules.method_by_target). Measured on 2026-10-08 against the loads
Intervals.icu stored for the head coach's real planned workouts:

  target                 method                         sessions  largest gap
  cycling power          np_30s (below)                 74        1.4 TSS
  running pace           if_squared (per step)          44        1.0 TSS
  running power          if_squared (per step)          11        0.6 TSS
  heart rate (LTHR/HR)   hrss (below)                    6        see note

Before v7.38 every target used if_squared. On cycling power it under-read
interval sessions by up to 11 TSS (13-21% on the hardest), because a
per-step IF^2 ignores the 4th-power weighting of Normalized Power. On heart
rate it read up to twice the stored load (130 vs 62).

np_30s — Normalized Power: the session as a 1 Hz stream (a ramp changes
    linearly second by second), a 30 s rolling average (over the seconds
    available at the very start), 4th power, mean, 4th root.
    IF = NP / FTP, TSS = hours x IF^2 x 100. Order matters: repeat blocks
    are expanded in the order they are ridden.

hrss — normalised TRIMP, the method the Intervals.icu workout builder uses
    for heart-rate workouts. Each second's target in whole bpm (% LTHR x
    LTHR, or % HR x max HR); HRr = (HR - resting) / (max - resting);
    TRIMP per minute = HRr x 0.64 x e^(1.92 x HRr); HRSS = 100 x
    TRIMP(session) / TRIMP(60 min at LTHR). It needs the athlete's LTHR,
    max HR and resting HR (read from data/<id>/athlete_data.json, the same
    values Intervals.icu holds). Intervals.icu keeps the values of the day
    a workout was planned; when they change later its stored load and this
    one drift apart, which the upload check (push_block) reports. Without
    the athlete's values a typical profile stands in and the result says so.

The gap that remains is rounding (Intervals.icu stores whole numbers) and
the thresholds of the day. It is checked, not assumed: push_block compares
every uploaded session's load with the one Intervals.icu computed.
"""

from __future__ import annotations

import json
import math
import os
import statistics

TRIMP_A = 0.64
TRIMP_B = 1.92
TYPICAL_MAX_HR_RATIO = 1.09      # max HR / LTHR, used only without real values
TYPICAL_REST_HR_RATIO = 0.37     # resting HR / LTHR
# Intervals.icu's own resting HR when the athlete has none: with 60 bpm the
# formula reproduced both planned HR workouts of an athlete with no resting
# HR on record (17 vs 18, 124 vs 125), against 13 and 115 with the athlete
# values otherwise used.
DEFAULT_RESTING_HR = 60

# Intervals.icu activity types that carry each sport's settings.
_SPORT_TYPES = {"cycling": ("Ride", "VirtualRide"), "running": ("Run", "VirtualRun")}


# ── the ordered stream ────────────────────────────────────────────

def ordered_segments(steps, fraction_of):
    """Expand parsed steps (verify/validate_block.parse_block) into ordered
    segments (seconds, start_fraction, end_fraction), repeat blocks ridden
    in order: A B A B, never A A B B. `fraction_of(step)` returns the step's
    (start, end) fraction of threshold, or None to leave the step out (the
    caller reports it as not costed)."""
    out, block, block_id, block_mult = [], [], None, 1

    def flush():
        nonlocal block, block_id, block_mult
        for _ in range(block_mult):
            out.extend(block)
        block, block_id, block_mult = [], None, 1

    for s in steps:
        frac = fraction_of(s)
        if frac is None or not s.get("secs"):
            continue
        seg = (int(s["secs"]), frac[0], frac[1])
        bid = s.get("block")
        if s.get("mult", 1) > 1 and bid is not None:
            if bid != block_id:
                flush()
                block_id, block_mult = bid, s["mult"]
            block.append(seg)
        else:
            flush()
            out.append(seg)
    flush()
    return out


def stream(segments):
    """One value per second; a ramp is sampled at the middle of each second."""
    p = []
    for secs, a, b in segments:
        if secs <= 0:
            continue
        if a == b:
            p.extend([a] * secs)
        else:
            p.extend(a + (b - a) * (i + 0.5) / secs for i in range(secs))
    return p


# ── power: Normalized Power ───────────────────────────────────────

def np_fraction(segments, window=30):
    p = stream(segments)
    if not p:
        return 0.0
    acc = fourth = 0.0
    for i, v in enumerate(p):
        acc += v
        if i >= window:
            acc -= p[i - window]
        fourth += (acc / min(window, i + 1)) ** 4
    return (fourth / len(p)) ** 0.25


def np_tss(segments, window=30):
    seconds = sum(s for s, _, _ in segments if s > 0)
    if not seconds:
        return 0.0
    return seconds / 3600 * np_fraction(segments, window) ** 2 * 100


# ── heart rate: HRSS ──────────────────────────────────────────────

def _trimp_per_minute(hrr):
    return hrr * TRIMP_A * math.exp(TRIMP_B * hrr)


def hrss(bpm_segments, lthr, max_hr, resting):
    """HRSS of segments given in bpm (seconds, start_bpm, end_bpm)."""
    span = max_hr - resting
    ref = 60.0 * _trimp_per_minute((lthr - resting) / span)
    trimp = 0.0
    for v in stream(bpm_segments):
        hrr = max(0.0, min(1.0, (round(v) - resting) / span))
        trimp += _trimp_per_minute(hrr) / 60.0
    return 100.0 * trimp / ref


def typical_profile(lthr=None):
    lt = float(lthr or 160)
    return {"lthr": lt, "max_hr": round(lt * TYPICAL_MAX_HR_RATIO),
            "resting_hr": round(lt * TYPICAL_REST_HR_RATIO), "source": "typical"}


_PROFILE_CACHE = {}


def hr_profile(athlete_id, sport, root):
    """{"lthr", "max_hr", "resting_hr", "source"} for the athlete and sport,
    from data/<id>/athlete_data.json: LTHR and max HR from the sport's
    Intervals.icu settings, resting HR from the athlete record (the value
    Intervals.icu holds), else the median of the last 14 days of wellness,
    else Intervals.icu's default of 60 bpm. None when LTHR or max HR is
    missing or the three are out of order."""
    key = (str(athlete_id), sport)
    if key in _PROFILE_CACHE:
        return _PROFILE_CACHE[key]
    result = None
    path = os.path.join(root, "data", str(athlete_id), "athlete_data.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = None
    if data:
        prof = data.get("profile") or {}
        wanted = _SPORT_TYPES.get(sport, ())
        settings = next((s for s in prof.get("sport_settings") or []
                         if set(s.get("types") or []) & set(wanted)), {})
        lthr, max_hr = settings.get("lthr"), settings.get("max_hr")
        rest = prof.get("resting_hr")
        if not rest:
            recent = [w.get("resting_hr") for w in (data.get("wellness") or [])
                      if w.get("resting_hr")][-14:]
            rest = statistics.median(recent) if recent else None
        source = "athlete_data.json"
        if not rest:
            rest, source = DEFAULT_RESTING_HR, "athlete_data.json, resting HR 60 (Intervals.icu default)"
        if lthr and max_hr and rest < lthr < max_hr:
            result = {"lthr": float(lthr), "max_hr": float(max_hr),
                      "resting_hr": float(rest), "source": source}
    _PROFILE_CACHE[key] = result
    return result


def clear_cache():
    _PROFILE_CACHE.clear()
