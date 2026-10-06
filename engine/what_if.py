"""
engine/what_if.py — Infame Elite Endurance Coach v7
====================================================
What if the weekly load targets are followed? Feeds the coach's weekly TSS
targets (load_targets) into the same Banister projection #STATE already uses
and reports where CTL and TSB land on race morning, next to the projection
without those targets, before a single session is written.

How a target becomes days. A weekly TSS target is spread over the seven days
in proportion to the athlete's own average load per weekday over the trailing
8 weeks (build_state.weekday_load_pattern), so a habitual rest day stays near
zero and a habitual long day keeps its weight. When there is too little
history for that pattern, the week is spread evenly and the result says so.

What it replaces. In a week with a target, that week's planned events in
Intervals.icu are set aside: the target stands in for them. Weeks without a
target keep exactly what #STATE assumes (planned events, else weekday
history). Only whole future weeks are accepted: a week that has already
started is already partly in the athlete's real CTL and ATL.

Race morning is the same definition taper_check uses: the end of the day
before the race, race-day load excluded. The race comes from the athlete's
declared goals unless the coach passes one.

Reports only. Nothing here says the projected form is right or wrong for the
athlete; taper_check's own verdict against the target range is shown as it
stands, and the coach decides.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

MAX_HORIZON = 200


from shared import iso_day as _d  # noqa: E402 — shared parser (v7.33)


def _weights(pattern):
    """Share of a week's load that falls on each weekday (Mon=0), and whether
    they came from the athlete's own history."""
    if pattern and sum(max(v, 0) for v in pattern.values()) > 0:
        total = sum(max(v, 0) for v in pattern.values())
        return {wd: max(pattern[wd], 0) / total for wd in range(7)}, True
    return {wd: 1 / 7 for wd in range(7)}, False


def _at(series, iso):
    return next((s for s in series if s["date"] == iso), None)


def _summary(projection, taper):
    if not taper.get("applicable") or "projected_tsb_at_race" not in taper:
        return None
    race = _d(taper["date"])
    row = _at(projection["series"], (race - timedelta(days=1)).isoformat())
    out = {"tsb_at_race": taper["projected_tsb_at_race"],
           "target_tsb_range": taper["target_tsb_range"],
           "verdict": taper["verdict"]}
    if row:
        out["ctl_at_race"] = row["ctl"]
        out["atl_at_race"] = row["atl"]
    return out


def analyze(pmc, events, activities, week_targets, goals, thresholds,
            race_date=None, event_type=None):
    """week_targets: {"YYYY-MM-DD of a Monday": weekly TSS}. Returns a dict
    with "available" False and a reason when the question cannot be answered."""
    import build_state as bs

    if not pmc or pmc.get("ctl") is None or not pmc.get("date"):
        return {"available": False, "reason": "no PMC reading in the athlete's data"}
    if not week_targets:
        return {"available": False, "reason": "no week targets given"}

    start = bs.d(pmc["date"])
    targets, skipped = {}, []
    for key, tss in week_targets.items():
        try:
            monday = _d(key)
        except ValueError:
            raise ValueError(f"'{key}' is not a date (YYYY-MM-DD)")
        if isinstance(tss, bool) or not isinstance(tss, (int, float)) or not 0 < tss <= 2000:
            raise ValueError(f"target for {key} must be a number from 1 to 2000")
        if monday.weekday() != 0:
            raise ValueError(f"{key} is not a Monday")
        if monday <= start:
            skipped.append({"week_start": monday.isoformat(),
                            "reason": "the week has already started, so it is already "
                                      "partly in the real CTL and ATL"})
            continue
        targets[monday] = float(tss)
    if not targets:
        return {"available": False, "reason": "no whole future week among the targets",
                "skipped": skipped}

    if race_date:
        try:
            rd = _d(race_date)
        except ValueError:
            raise ValueError(f"race_date '{race_date}' is not a date (YYYY-MM-DD)")
        goals_used = [{"priority": "A", "date": rd.isoformat(),
                       "event_type": event_type, "description": "Race given by the coach"}]
    else:
        goals_used = goals

    long_base = bs.project_pmc(pmc, events, activities, horizon_days=MAX_HORIZON)
    probe = bs.taper_check(long_base, goals_used, thresholds, pmc)
    if not probe.get("applicable"):
        return {"available": False, "reason": probe.get("reason"), "skipped": skipped}
    race = _d(probe["date"])
    horizon = max(1, min(MAX_HORIZON, (race - start).days))

    weights, from_history = _weights(bs.weekday_load_pattern(activities or []))
    week_dates, weeks_out = set(), []
    new_events = []
    for monday, tss in sorted(targets.items()):
        daily = []
        for i in range(7):
            day = monday + timedelta(days=i)
            week_dates.add(day.isoformat())
            load = round(tss * weights[i], 1)
            daily.append(load)
            new_events.append({"date": day.isoformat(), "planned_load": load})
        weeks_out.append({"week_start": monday.isoformat(), "target_tss": tss,
                          "daily_load": daily,
                          "ends_after_race": (monday + timedelta(days=6)) >= race})
    kept = [e for e in (events or []) if str(e.get("date"))[:10] not in week_dates]

    base = bs.project_pmc(pmc, events, activities, horizon_days=horizon)
    what = bs.project_pmc(pmc, kept + new_events, activities, horizon_days=horizon)
    b_taper = bs.taper_check(base, goals_used, thresholds, pmc)
    w_taper = bs.taper_check(what, goals_used, thresholds, pmc)

    notes = ["each target is spread over the week by the athlete's own weekday "
             "pattern" if from_history else
             "too little history for a weekday pattern: each target is spread evenly "
             "over the seven days",
             "planned Intervals.icu events in a week with a target are set aside; "
             "weeks without a target keep what #STATE assumes",
             "race morning = end of the day before the race, race-day load excluded"]
    if any(w["ends_after_race"] for w in weeks_out):
        notes.append("a targeted week reaches the race date: its days from the race "
                     "on do not affect race-morning form")
    return {
        "available": True,
        "race": {"name": probe["race"], "date": probe["date"], "days_out": probe["days_out"]},
        "baseline": _summary(base, b_taper),
        "what_if": _summary(what, w_taper),
        "weeks": weeks_out,
        "weekday_pattern_from_history": from_history,
        "skipped": skipped,
        "notes": notes,
    }


def render(result):
    if not result.get("available"):
        return f"What-if: not available — {result.get('reason')}"
    r = result["race"]
    L = ["## What-if: weekly load targets", "",
         f"Race: **{r['name']}** on {r['date']} ({r['days_out']} days out). "
         "Race morning form with and without the targets:", ""]
    b, w = result["baseline"], result["what_if"]
    if not b or not w:
        L.append("The race is beyond the projection horizon.")
    else:
        L += ["| | TSB race morning | CTL | ATL | Target range | Verdict |",
              "| :--- | ---: | ---: | ---: | :--- | :--- |"]
        for name, x in (("Without the targets", b), ("With the targets", w)):
            lo, hi = x["target_tsb_range"]
            L.append(f"| {name} | {x['tsb_at_race']:g} | {x.get('ctl_at_race', '—')} | "
                     f"{x.get('atl_at_race', '—')} | [{lo:g}, {hi:g}] | {x['verdict']} |")
    L += ["", "| Week starts | TSS target | Mon | Tue | Wed | Thu | Fri | Sat | Sun |",
          "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for wk in result["weeks"]:
        L.append(f"| {wk['week_start']} | {wk['target_tss']:g} | "
                 + " | ".join(f"{v:g}" for v in wk["daily_load"]) + " |")
    for s in result["skipped"]:
        L.append(f"\nSkipped {s['week_start']}: {s['reason']}.")
    L += [""] + [f"- {n}" for n in result["notes"]] + [""]
    return "\n".join(L)
