"""
longitudinal.py — Infame Elite Endurance Coach v6, Stage 6
===========================================================
Longitudinal performance intelligence: how the athlete's capability is moving
over months, not how they feel today.

Three analyses:
  1. Curve progression — power and pace bests across nested rolling windows
  2. Durability trend — whether aerobic decoupling is improving or degrading
  3. Anaerobic repeatability — whether the athlete can still reach depth

Consumed by build_state.py and rendered into the #STATE block. All thresholds
come from the `longitudinal` section of config/decision_thresholds.yaml.

Nothing here diagnoses. Each function reports what the data shows, with the
window and sample size attached, and says plainly when there is not enough to
conclude anything.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta


def _d(s):
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def _band(delta_pct, bands):
    """Classify a percent change against the configured gain/decline bands."""
    if delta_pct >= bands["strong_gain"]:
        return "strong_gain"
    if delta_pct >= bands["moderate_gain"]:
        return "moderate_gain"
    if delta_pct >= bands["mild_gain"]:
        return "mild_gain"
    if delta_pct >= bands["stable"]:
        return "stable"
    return "decline"


# ══════════════════════════════════════════════════════════════════
# CURVE PROGRESSION
# ══════════════════════════════════════════════════════════════════

def _power_points(curves, window):
    entry = (curves.get("power") or {}).get(window)
    if not entry:
        return None, None
    pts = {k: v.get("watts") for k, v in (entry.get("points") or {}).items()
           if v.get("watts")}
    return (pts or None), entry.get("window")


def _pace_points(curves, window):
    """Pace curve points as speed in m/s, keyed by distance in metres."""
    entry = (curves.get("pace") or {}).get(window)
    if not entry:
        return None, None
    pts = {k: v.get("speed_ms") for k, v in (entry.get("points") or {}).items()
           if v.get("speed_ms")}
    return (pts or None), entry.get("window")


def _pace_by_duration(curves, window, anchors_secs, tolerance_pct):
    """Invert the pace curve: for each duration anchor, find how far the athlete
    covered in about that time. The curve is indexed by distance and returns
    elapsed seconds, so this answers 'how far in 60 minutes'."""
    entry = (curves.get("pace") or {}).get(window)
    if not entry:
        return None
    points = entry.get("points") or {}
    out = {}
    for want in anchors_secs:
        best_key, best_gap = None, None
        for k, v in points.items():
            secs = v.get("seconds")
            if not secs:
                continue
            gap = abs(secs - want)
            if best_gap is None or gap < best_gap:
                best_key, best_gap = k, gap
        if best_key is None:
            continue
        got = points[best_key]
        if best_gap > want * (tolerance_pct / 100.0):
            continue
        out[str(want)] = {
            "metres": got.get("metres"),
            "seconds": got.get("seconds"),
            "speed_ms": got.get("speed_ms"),
        }
    return out or None


def curve_progression(curves, sport, cfg):
    """Curve movement across rolling windows.

    CRITICAL — the windows are NESTED, not disjoint: the 1y curve contains the
    90d curve, which contains the 42d curve. A longer window therefore has
    proportionally more opportunities to record a maximum, so a 42d value below
    the 1y maximum is the EXPECTED result even for an athlete who is improving.
    The 1y window is roughly 8.7x longer than 42d; treating that gap as decline
    is a sampling artifact, not a finding.

    So two different questions are answered separately:

      TREND — 42d against 90d. Comparable windows (90d is about 2.1x, a mild
      and stated bias), so a real difference here means recent form actually
      moved. This is what drives the adaptation state.

      LEVEL — 42d as a percent of the 1y best. Where the athlete stands against
      their own yearly peak. Reported as context only; never banded as gain or
      decline, because the nesting makes that comparison unfair by construction.
    """
    lc = cfg["longitudinal"]
    bands = lc["delta_bands"]["cycling" if sport == "cycling" else "running"]

    getter = _power_points if sport == "cycling" else _pace_points
    unit = "watts" if sport == "cycling" else "m/s"

    recent, recent_win = getter(curves, "42d")
    mid, mid_win = getter(curves, "90d")
    long, long_win = getter(curves, "1y")

    if not recent:
        return {"available": False, "reason": "no 42d curve data"}
    if not mid:
        return {"available": False,
                "reason": "no 90d curve data — trend needs a comparable window"}

    anchors = [str(a) for a in (lc["power_anchors_secs"] if sport == "cycling"
                                else lc["pace_anchors_metres"])]

    rows, missing = [], []
    for a in anchors:
        r, m, l = recent.get(a), mid.get(a), (long or {}).get(a)
        if r is None or m is None:
            missing.append(a)
            continue
        trend = (r / m - 1) * 100
        row = {
            "anchor": a,
            "recent_42d": round(r, 1),
            "window_90d": round(m, 1),
            "trend_vs_90d_pct": round(trend, 1),
            "band": _band(trend, bands),
            "set_in_last_42d": abs(r - m) < 1e-9,
        }
        if l:
            row["best_1y"] = round(l, 1)
            row["level_pct_of_1y"] = round(r / l * 100, 1)
        rows.append(row)

    if not rows:
        return {"available": False,
                "reason": "no anchor durations present in both the 42d and 90d windows"}

    return {
        "available": True,
        "unit": unit,
        "windows": {"recent": recent_win, "comparison": mid_win, "reference": long_win},
        "anchors": rows,
        "anchors_set_recently": f"{sum(1 for r in rows if r['set_in_last_42d'])}/{len(rows)}",
        "composites": _composites(recent, long or {}, lc, sport),
        "method": ("Trend is 42d against 90d. Level is 42d as a percent of the 1y "
                   "best. The windows are nested, so the 1y comparison is a level "
                   "reading only and is never scored as gain or decline."),
        "anchors_unavailable": missing or None,
    }


def _composites(recent, long, lc, sport):
    """Ratios between anchors. These describe the SHAPE of the curve — whether
    it leans anaerobic or aerobic — independently of absolute fitness, so they
    stay meaningful when the athlete gains or loses form overall."""
    out = {}
    for name, spec in (lc.get("composites") or {}).items():
        num, den = str(spec["numerator"]), str(spec["denominator"])
        if num not in recent or den not in recent or not recent[den]:
            continue
        now = recent[num] / recent[den]
        row = {"ratio_42d": round(now, 3),
               "from": f"{num} over {den}"}
        if num in long and den in long and long[den]:
            then = long[num] / long[den]
            row["ratio_1y"] = round(then, 3)
            row["shift_pct"] = round((now / then - 1) * 100, 1)
        out[name] = row
    return out or None


# ══════════════════════════════════════════════════════════════════
# DURABILITY TREND
# ══════════════════════════════════════════════════════════════════

def durability_trend(activities, cfg):
    """Aerobic decoupling over time. Reports direction, not just current state:
    a stable-but-worsening athlete and a stable-but-improving one need
    different prescriptions."""
    d = cfg["longitudinal"]["durability"]
    rows = [a for a in activities
            if a.get("decoupling") is not None
            and (a.get("moving_time") or 0) >= d["min_session_seconds"]]

    if len(rows) < d["trend_split"]:
        return {"available": False,
                "reason": f"only {len(rows)} qualifying sessions "
                          f"(need {d['trend_split']})"}

    window = rows[-d["trend_window_sessions"]:]
    half = max(d["trend_split"] // 2, len(window) // 2)
    older, newer = window[:half], window[half:]
    if not older or not newer:
        return {"available": False, "reason": "cannot split the window"}

    med_old = statistics.median(a["decoupling"] for a in older)
    med_new = statistics.median(a["decoupling"] for a in newer)
    change = med_new - med_old

    if change <= -1.0:
        direction = "improving"
    elif change >= 1.0:
        direction = "degrading"
    else:
        direction = "flat"

    vals = [a["decoupling"] for a in newer]
    severe = sum(1 for v in vals if v > d["severe_drift_pct"])
    moderate = sum(1 for v in vals if d["moderate_drift_pct"] <= v <= d["severe_drift_pct"])

    if severe:
        status = "degraded"
    elif moderate >= d["moderate_requires_repeats"]:
        status = "drifting"
    else:
        status = "stable"

    return {
        "available": True,
        "status": status,
        "direction": direction,
        "median_recent_pct": round(med_new, 1),
        "median_previous_pct": round(med_old, 1),
        "change_pct_points": round(change, 1),
        "sessions": {"recent": len(newer), "previous": len(older)},
        "date_range": {"from": window[0].get("date"), "to": window[-1].get("date")},
        "source": f"activity decoupling, sessions of "
                  f"{d['min_session_seconds'] // 60}min or more",
    }


# ══════════════════════════════════════════════════════════════════
# ANAEROBIC REPEATABILITY
# ══════════════════════════════════════════════════════════════════

def repeatability(activities, cfg):
    """How deeply the athlete is reaching into W', and whether that depth is
    holding. A falling peak depletion in an athlete still doing the work means
    they can no longer access the same anaerobic capacity."""
    r = cfg["longitudinal"]["repeatability"]
    rows, over_full = [], 0
    for a in activities:
        wp, dep = a.get("w_prime"), a.get("max_wbal_depletion")
        if not wp or dep is None:
            continue
        pct = abs(dep) / wp * 100
        # Depletion above 100% is not physically possible: it means the W'
        # estimate at the time of that session was lower than the one recorded
        # against it. Clamp and count, rather than reporting an impossible value.
        if pct > 100:
            over_full += 1
            pct = 100.0
        rows.append({"date": a.get("date"), "pct": pct,
                     "load": a.get("training_load")})

    if len(rows) < r["min_sessions"]:
        return {"available": False,
                "reason": f"only {len(rows)} sessions with W' data "
                          f"(need {r['min_sessions']})"}

    anaerobic = [x for x in rows if x["pct"] >= r["high_depletion_pct"]]
    half = len(rows) // 2
    older, newer = rows[:half], rows[half:]
    peak_old = max((x["pct"] for x in older), default=0)
    peak_new = max((x["pct"] for x in newer), default=0)
    drop = peak_old - peak_new

    if not anaerobic:
        status = "untested"
    elif drop >= r["declining_threshold_pct"]:
        status = "declining"
    else:
        status = "maintained"

    return {
        "available": True,
        "status": status,
        "sessions_with_w_prime": len(rows),
        "sessions_above_threshold": len(anaerobic),
        "threshold_pct": r["high_depletion_pct"],
        "peak_depletion_recent_pct": round(peak_new, 1),
        "peak_depletion_previous_pct": round(peak_old, 1),
        "change_pct_points": round(-drop, 1),
        "source": "activity max W' balance depletion as a percent of W'",
        "clamped_sessions": over_full,
        "note": ("'untested' means no session reached the anaerobic depth "
                 "threshold — it says nothing about capacity, only that "
                 "capacity was not probed."),
    }


# ══════════════════════════════════════════════════════════════════
# ADAPTATION STATE
# ══════════════════════════════════════════════════════════════════

def adaptation_state(progression, durability, repeat_):
    """Where adaptation is heading. Driven by the 42d-vs-90d TREND, never by the
    level against the 1y best — see the nesting note in curve_progression.

    Level does inform the shape description: an athlete flat in trend but at 96%
    of their yearly best at 60min and 77% at 60s is not stagnant, they are
    aerobically near peak with the top end untrained. That is a different
    prescription from someone flat at 80% across the board."""
    if not progression.get("available"):
        return {"available": False, "reason": "no curve progression to summarize"}

    rows = progression["anchors"]
    gains = [r for r in rows if r["band"] in ("strong_gain", "moderate_gain")]
    declines = [r for r in rows if r["band"] == "decline"]
    flat = [r for r in rows if r["band"] in ("stable", "mild_gain")]

    def is_short(a):
        return a.isdigit() and int(a) <= 300

    short_gains = [r for r in gains if is_short(r["anchor"])]
    long_gains = [r for r in gains if not is_short(r["anchor"])]

    evidence = []
    # Regression requires a MAJORITY of anchors moving down. Two soft declines
    # among three flat anchors is a plateau with noise, not a losing athlete.
    if len(declines) > len(rows) / 2 and len(declines) > len(gains):
        state = "regression"
        evidence.append(f"{len(declines)} of {len(rows)} anchors down against the "
                        f"90d window")
    elif long_gains and not short_gains:
        state = "aerobic_consolidation"
        evidence.append("gains at the longer durations only")
    elif short_gains and not long_gains:
        state = "anaerobic_build"
        evidence.append("gains at the shorter durations only")
    elif gains:
        state = "broad_progression"
        evidence.append(f"{len(gains)} of {len(rows)} anchors gaining")
    else:
        state = "plateau"
        detail = f"{len(flat)} of {len(rows)} anchors flat against 90d"
        if declines:
            detail += (f", {len(declines)} down "
                       f"({', '.join(r['anchor'] for r in declines)})")
        evidence.append(detail)

    # Level context — where the flat/declining athlete actually stands.
    levels = [r for r in rows if "level_pct_of_1y" in r]
    if levels:
        long_lv = [r for r in levels if not is_short(r["anchor"])]
        short_lv = [r for r in levels if is_short(r["anchor"])]
        if long_lv and short_lv:
            hi = max(r["level_pct_of_1y"] for r in long_lv)
            lo = min(r["level_pct_of_1y"] for r in short_lv)
            if hi - lo >= 10:
                evidence.append(f"aerobic end at {hi:.0f}% of the yearly best "
                                f"while the short end sits at {lo:.0f}% — top-end "
                                f"capacity is the gap, not aerobic fitness")
        best = max(levels, key=lambda r: r["level_pct_of_1y"])
        evidence.append(f"closest to yearly best at {best['anchor']} "
                        f"({best['level_pct_of_1y']:.0f}%)")

    if durability.get("available"):
        evidence.append(f"durability {durability['status']} and "
                        f"{durability['direction']}")
    if repeat_.get("available") and repeat_["status"] != "untested":
        evidence.append(f"anaerobic depth {repeat_['status']}")

    return {"available": True, "state": state, "evidence": evidence,
            "anchors_set_recently": progression["anchors_set_recently"]}


# ══════════════════════════════════════════════════════════════════
# TESTING RECOMMENDATIONS AND DATA QUALITY
# ══════════════════════════════════════════════════════════════════

def testing_recommendations(progression, repeat_, activities, cfg):
    """What to test, and why.

    The engine cannot distinguish lost capacity from untested capacity — both
    look identical in a curve. It does not need to: in either case the correct
    action is to test, then re-plan on fresh numbers. So instead of guessing,
    this reports which anchors are far enough below the athlete's yearly best
    to be worth probing, and names a protocol for each.

    It also flags data problems that silently distort everything downstream."""
    lc = cfg["longitudinal"]
    tc = lc.get("testing") or {}
    trigger = tc.get("level_trigger_pct", 85)
    protocols = tc.get("protocols") or {}

    tests, data_flags = [], []

    if progression.get("available"):
        for r in progression["anchors"]:
            lvl = r.get("level_pct_of_1y")
            if lvl is None or lvl >= trigger:
                continue
            tests.append({
                "anchor": r["anchor"],
                "level_pct_of_1y": lvl,
                "trend_vs_90d_pct": r["trend_vs_90d_pct"],
                "protocol": protocols.get(r["anchor"], "Maximal effort at this duration"),
                "reason": (f"sitting at {lvl:.0f}% of the yearly best — either the "
                           f"capacity dropped or it has not been probed lately, and "
                           f"the data cannot tell which"),
            })

    # W' underestimated: depletion cannot exceed 100%.
    clamped = repeat_.get("clamped_sessions", 0) if repeat_.get("available") else 0
    if clamped >= lc.get("w_prime_review_trigger_sessions", 1):
        data_flags.append({
            "issue": "W' appears underestimated",
            "detail": (f"{clamped} session(s) recorded depletion above 100% of the "
                       f"configured W'. Every anaerobic reading derived from it is "
                       f"compressed."),
            "action": ("Refresh W' with a ramp or CP test, then update the athlete's "
                       "sport settings in Intervals.icu."),
        })

    # Non-endurance activities in the log.
    non_endurance = set(lc.get("non_endurance_types") or [])
    counts = {}
    for a in activities:
        ty = a.get("type")
        if ty in non_endurance:
            counts[ty] = counts.get(ty, 0) + 1
    if counts:
        total_non = sum(counts.values())
        data_flags.append({
            "issue": "Non-endurance sessions in the log",
            "detail": (f"{total_non} of {len(activities)} activities are "
                       + ", ".join(f"{v} {k}" for k, v in
                                   sorted(counts.items(), key=lambda x: -x[1]))
                       + ". These carry no endurance load and are excluded from "
                         "the curve, durability and repeatability analyses."),
            "action": "No action needed — noted so the session counts read correctly.",
        })

    # Power coverage.
    with_power = sum(1 for a in activities
                     if a.get("average_watts") or a.get("weighted_avg_watts"))
    endurance = [a for a in activities if a.get("type") not in non_endurance]
    if endurance and with_power / len(endurance) < 0.5:
        data_flags.append({
            "issue": "Limited power coverage",
            "detail": (f"only {with_power} of {len(endurance)} endurance sessions "
                       f"carry power data"),
            "action": ("Curve and repeatability analysis will stay thin until more "
                       "sessions are recorded with a power meter."),
        })

    return {"tests": tests, "data_flags": data_flags,
            "frame": tc.get("common_frame")}


# ══════════════════════════════════════════════════════════════════
# RENDERING
# ══════════════════════════════════════════════════════════════════

def render(section):
    """Render the longitudinal block for state.md."""
    L = ["## Longitudinal performance", ""]

    prog = section["progression"]
    if not prog.get("available"):
        L.append(f"Curve progression: not available — {prog.get('reason')}")
        L.append("")
    else:
        L.append(f"Curve anchors in {prog['unit']}. **Trend** compares the last 42 "
                 f"days against the last 90; **level** is where that sits against "
                 f"the best of the past year.")
        L.append("")
        L.append(f"The windows are nested, so the yearly figure is a level "
                 f"reading only — a 42-day window has far fewer chances to record "
                 f"a maximum than a 12-month one, and the gap between them is not "
                 f"decline.")
        L.append("")
        L.append("| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |")
        L.append("| :--- | ---: | ---: | ---: | ---: | ---: | :--- |")
        for r in prog["anchors"]:
            mark = " ·set in last 42d" if r["set_in_last_42d"] else ""
            b1y = r.get("best_1y")
            lvl = r.get("level_pct_of_1y")
            L.append(f"| {r['anchor']} | {r['recent_42d']} | {r['window_90d']} | "
                     f"{r['trend_vs_90d_pct']:+.1f}% | "
                     f"{b1y if b1y else '—'} | "
                     f"{f'{lvl:.0f}%' if lvl else '—'} | "
                     f"{r['band']}{mark} |")
        L.append("")
        L.append(f"{prog['anchors_set_recently']} anchors were set within the "
                 f"last 42 days.")
        if prog.get("anchors_unavailable"):
            L.append(f"No data at: {', '.join(prog['anchors_unavailable'])}")
        if prog.get("composites"):
            L.append("")
            L.append("Curve shape:")
            for name, c in prog["composites"].items():
                shift = (f", shifted {c['shift_pct']:+.1f}% vs 1y"
                         if "shift_pct" in c else "")
                L.append(f"- **{name}** ({c['from']}): {c['ratio_42d']}{shift}")
        if prog.get("by_duration_42d"):
            L.append("")
            L.append("Distance covered by duration (42d):")
            for secs, v in sorted(prog["by_duration_42d"].items(),
                                  key=lambda x: int(x[0])):
                L.append(f"- {int(secs)//60} min: {v['metres']/1000:.2f} km "
                         f"({v['speed_ms']} m/s)")
        L.append("")

    dur = section["durability_trend"]
    if dur.get("available"):
        L.append(f"**Durability:** {dur['status']}, {dur['direction']} — median "
                 f"decoupling {dur['median_recent_pct']}% recently vs "
                 f"{dur['median_previous_pct']}% before "
                 f"({dur['change_pct_points']:+.1f} points, "
                 f"{dur['sessions']['recent']} vs {dur['sessions']['previous']} "
                 f"sessions).")
    else:
        L.append(f"**Durability:** not available — {dur.get('reason')}")

    rep = section["repeatability"]
    if rep.get("available"):
        L.append(f"**Anaerobic depth:** {rep['status']} — peak W' depletion "
                 f"{rep['peak_depletion_recent_pct']}% recently vs "
                 f"{rep['peak_depletion_previous_pct']}% before; "
                 f"{rep['sessions_above_threshold']} of "
                 f"{rep['sessions_with_w_prime']} sessions reached "
                 f"{rep['threshold_pct']}%.")
        if rep["status"] == "untested":
            L.append(f"  {rep['note']}")
        if rep.get("clamped_sessions"):
            L.append(f"  Note: {rep['clamped_sessions']} session(s) recorded "
                     f"depletion above 100% of W', which is not physically "
                     f"possible — the W' estimate has changed since. Clamped "
                     f"to 100%; the trend is directional, not exact.")
    else:
        L.append(f"**Anaerobic depth:** not available — {rep.get('reason')}")

    ad = section["adaptation_state"]
    if ad.get("available"):
        L.append("")
        L.append(f"**Adaptation state: {ad['state']}** — "
                 f"{'; '.join(ad['evidence'])}.")

    tst = section.get("testing") or {}
    if tst.get("tests"):
        L.append("")
        L.append("### Suggested testing")
        L.append("")
        L.append("These anchors sit far enough below the yearly best that the data "
                 "cannot say whether the capacity dropped or simply was not probed. "
                 "Prescribe only the test that refreshes the anchor in question — "
                 "not a full battery.")
        L.append("")
        for x in tst["tests"]:
            L.append(f"- **{x['anchor']}** — at {x['level_pct_of_1y']:.0f}% of the "
                     f"yearly best ({x['trend_vs_90d_pct']:+.1f}% vs 90d). "
                     f"{x['protocol'].strip()}")
        frame = tst.get("frame") or {}
        if frame:
            L.append("")
            for k in ("warmup", "after", "spacing"):
                if frame.get(k):
                    L.append(f"- {frame[k].strip()}")
    if tst.get("data_flags"):
        L.append("")
        L.append("### Data quality")
        L.append("")
        for f in tst["data_flags"]:
            L.append(f"- **{f['issue']}** — {f['detail']} {f['action']}")
    L.append("")
    return "\n".join(L)


def analyze(data, cfg):
    """Run every longitudinal analysis over one athlete's fetched data."""
    curves = data.get("curves") or {}
    activities = data.get("activities") or []
    sport = "cycling" if (curves.get("power")) else "running"

    prog = curve_progression(curves, sport, cfg)
    dur = durability_trend(activities, cfg)
    rep = repeatability(activities, cfg)
    return {
        "sport_basis": sport,
        "progression": prog,
        "durability_trend": dur,
        "repeatability": rep,
        "adaptation_state": adaptation_state(prog, dur, rep),
        "testing": testing_recommendations(prog, rep, activities, cfg),
    }
