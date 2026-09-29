"""
engine/durability_watts.py — Infame Elite Endurance Coach v7
=============================================================
Durability in watts: how much of a rider's fresh power is still there after a
given amount of work. Best 5-minute and 20-minute power after X kJ, against
the same durations fresh, this window against the one before it.

It answers what HR decoupling can only hint at. Decoupling says the heart rate
drifted; this says what the legs could still produce.

Source. Intervals.icu keeps up to two "fatigued" power curves per athlete
(`kj0`, `kj1`). The fetcher asks for each activity's best power at 5 and 20
minutes, fresh and fatigued (`activity-power-curves`, its documented
`fatigue` parameter), and keeps the best of each window. The kJ each fatigued
curve was cut at is read from the answer itself (`after_kj`). An athlete with
no fatigued curve defined has nothing here: the section is absent, never
reported as zero and never a fault.

Two windows of the same length that do NOT overlap (the last 42 days and the 42
before them), so the comparison is fair, unlike the nested 42d/90d/1y curves in
longitudinal.py. A window with few activities is a small sample: every value
carries the number of activities behind it.

Reports only. Nothing here says the durability is good or bad, and nothing
blocks or prescribes.
"""

from __future__ import annotations

from datetime import datetime, timedelta

SECS = (300, 1200)          # 5 min, 20 min
WINDOW_DAYS = 42


def _d(s):
    return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()


def rows_from_payload(payload, secs=SECS):
    """(rows, after_kj) from an `activity-power-curves` answer. The endpoint
    returns {"after_kj", "secs", "curves": [{"start_date_local", "watts"}]},
    with `watts` aligned to the answer's own `secs`: they are re-aligned here
    to the durations asked for, whatever order the answer uses. `after_kj` is
    the kJ the fatigued curve was cut at (None for a fresh curve, or when
    Intervals.icu defines no such curve). A bare list of curves is accepted."""
    if isinstance(payload, dict):
        curves = payload.get("curves") or payload.get("list") or []
        psecs, kj = payload.get("secs"), payload.get("after_kj")
    elif isinstance(payload, list):
        curves, psecs, kj = payload, None, None
    else:
        return [], None
    idx = {s: i for i, s in enumerate(psecs)} if psecs else None
    rows = []
    for c in curves:
        w = c.get("watts") or []
        if idx is None:
            aligned = list(w)
        else:
            aligned = [w[idx[s]] if s in idx and idx[s] < len(w) else None for s in secs]
        rows.append({"start_date_local": c.get("start_date_local"), "watts": aligned})
    ok_kj = kj if isinstance(kj, int) and not isinstance(kj, bool) and kj > 0 else None
    return rows, ok_kj


def best_by_window(rows, today, secs=SECS, window_days=WINDOW_DAYS):
    """{"current": {sec: {"watts", "n"}}, "previous": {...}} from the rows
    `activity-power-curves` returns: one per activity, `watts` aligned to the
    requested durations. A duration an activity did not reach is null or 0 and
    is skipped, not counted. `n` is the number of activities that reached it."""
    cur_from = today - timedelta(days=window_days - 1)
    prev_from = today - timedelta(days=2 * window_days - 1)
    out = {"current": {}, "previous": {}}
    for row in rows or []:
        if not row.get("start_date_local"):
            continue
        d = _d(row["start_date_local"])
        if d > today or d < prev_from:
            continue
        window = "current" if d >= cur_from else "previous"
        watts = row.get("watts") or []
        for i, sec in enumerate(secs):
            w = watts[i] if i < len(watts) else None
            if not isinstance(w, (int, float)) or w <= 0:
                continue
            slot = out[window].setdefault(str(sec), {"watts": w, "n": 0})
            slot["n"] += 1
            slot["watts"] = max(slot["watts"], w)
    return out


def _pct(a, b):
    return round(100 * a / b, 1) if a and b else None


def analyze(data):
    """None when the athlete has no fatigued-curve data (not populated), so
    the section is simply absent. Otherwise one row per kJ level and duration."""
    fc = data.get("fatigue_curves")
    if not fc:
        return None
    best = fc.get("best") or {}
    fresh = best.get("fresh")
    levels = fc.get("after_kj") or {}
    secs = fc.get("secs") or list(SECS)

    result = {
        "available": False,
        "windows": fc.get("windows"),
        "levels": {},
        "source": "Intervals.icu activity power curves, fresh vs fatigued "
                  "(after_kj thresholds from the sport settings)",
        "note": "Best power per window; the two windows do not overlap. "
                "n is the number of activities behind each value.",
    }
    if not fresh:
        result["reason"] = "the fresh power curve could not be read"
        return result

    for name, kj in levels.items():
        fat = best.get(name)
        if not fat:
            continue
        rows = []
        for sec in secs:
            s = str(sec)
            f_cur = (fresh.get("current") or {}).get(s)
            f_prev = (fresh.get("previous") or {}).get(s)
            x_cur = (fat.get("current") or {}).get(s)
            x_prev = (fat.get("previous") or {}).get(s)
            if not x_cur and not x_prev:
                continue
            r_cur = _pct(x_cur["watts"], f_cur["watts"]) if x_cur and f_cur else None
            r_prev = _pct(x_prev["watts"], f_prev["watts"]) if x_prev and f_prev else None
            rows.append({
                "secs": sec,
                "fresh_current": f_cur, "fresh_previous": f_prev,
                "fatigued_current": x_cur, "fatigued_previous": x_prev,
                "retained_pct_current": r_cur,
                "retained_pct_previous": r_prev,
                "retained_change_pts": (round(r_cur - r_prev, 1)
                                        if r_cur is not None and r_prev is not None else None),
            })
        if rows:
            result["levels"][name] = {"after_kj": kj, "rows": rows}

    if result["levels"]:
        result["available"] = True
    else:
        result["reason"] = ("no efforts of 5 or 20 minutes after the configured "
                            "kJ in the last 84 days")
    return result


def _cell(slot):
    return f"{slot['watts']:g} W (n={slot['n']})" if slot else "—"


def render(section):
    """Markdown block for state.md; empty string when there is no section."""
    if not section:
        return ""
    L = ["## Durability in watts", ""]
    if not section["available"]:
        L.append(f"Not available — {section.get('reason')}.")
        L.append("")
        return "\n".join(L)
    w = section.get("windows") or {}
    cur, prev = w.get("current") or {}, w.get("previous") or {}
    L.append(f"Best power fresh vs after the configured kJ. Current window "
             f"{cur.get('from', '?')} to {cur.get('to', '?')}; previous "
             f"{prev.get('from', '?')} to {prev.get('to', '?')} (same length, no overlap). "
             f"Reports only; n is the number of activities behind each value.")
    L.append("")
    L.append("| After | Duration | Fresh now | Fatigued now | Retained now | "
             "Fresh before | Fatigued before | Retained before | Change |")
    L.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for name, lvl in section["levels"].items():
        for r in lvl["rows"]:
            def p(v, sfx="%"):
                return "—" if v is None else f"{v:g}{sfx}"
            chg = ("—" if r["retained_change_pts"] is None
                   else f"{r['retained_change_pts']:+g} pts")
            L.append(f"| {lvl['after_kj']:g} kJ | {r['secs'] // 60} min | "
                     f"{_cell(r['fresh_current'])} | {_cell(r['fatigued_current'])} | "
                     f"{p(r['retained_pct_current'])} | {_cell(r['fresh_previous'])} | "
                     f"{_cell(r['fatigued_previous'])} | "
                     f"{p(r['retained_pct_previous'])} | {chg} |")
    L.append("")
    return "\n".join(L)
