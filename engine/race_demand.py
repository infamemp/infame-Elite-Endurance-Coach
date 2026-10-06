"""
race_demand.py — what the next race asks for, next to what the plan gives.

Each goal in config/athletes/<id>.yaml may carry a `demand` list: one entry
per race day (one per stage in a stage race), with the discipline, distance,
climbing, the athlete's realistic hours for that day and the terrain, plus a
`demand_source` saying where the figures came from. The validator puts the
block it is checking beside that record: longest session per discipline
against the longest race day, and consecutive training days against the
number of race days.

These are facts side by side, never a verdict. Nothing here warns or blocks:
whether a 3-hour long ride is enough eight weeks out from a 6-hour stage is a
coaching judgement, and passing these lines does not mean the plan fits the
race. Climbing is not compared, because a session card carries no elevation;
the line says so rather than pretending.

Idea taken from Prova Endurance (SetRaceDemand + race-demand hints).

Version: 1.0 (v7.21)
"""

from datetime import date, datetime, timedelta

A_PRIORITIES = ("A+", "A", "A-")
NUMERIC_FIELDS = ("day", "distance_km", "climb_m", "expected_hours")


from shared import as_date as _as_date  # noqa: E402 — shared parser (v7.33)

def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def next_demand_goal(goals, today=None):
    """(goal, race_date) for the nearest upcoming goal that declares a demand,
    preferring A+/A/A- goals over the rest. (None, None) when there is none."""
    today = today or date.today()
    found = []
    for g in goals or []:
        if not isinstance(g, dict) or not g.get("demand"):
            continue
        d = _as_date(g.get("date"))
        if d is None or d < today:
            continue
        is_a = str(g.get("priority") or "").upper() in A_PRIORITIES
        found.append((0 if is_a else 1, d, g))
    if not found:
        return None, None
    found.sort(key=lambda x: (x[0], x[1]))
    return found[0][2], found[0][1]


def demand_warnings(goal, where, disciplines):
    """Problems in one goal's demand record, for build_profile's warnings."""
    out = []
    demand = goal.get("demand")
    if demand in (None, []):
        return out
    if not isinstance(demand, list):
        return [f"`{where}.demand` must be a list, one entry per race day"]
    for i, day in enumerate(demand, 1):
        w = f"{where}.demand[{i}]"
        if not isinstance(day, dict):
            out.append(f"`{w}` must be a mapping like "
                       f"{{day: 1, discipline: mtb, distance_km: 110, ...}}")
            continue
        disc = day.get("discipline")
        if disc is None:
            out.append(f"`{w}.discipline` is missing")
        elif disciplines and disc not in disciplines:
            out.append(f"`{w}.discipline`: '{disc}' is not a canonical discipline")
        for key in NUMERIC_FIELDS:
            if day.get(key) is not None and _num(day.get(key)) is None:
                out.append(f"`{w}.{key}`: '{day.get(key)}' is not a number")
    if not goal.get("demand_source"):
        out.append(f"`{where}.demand_source` is empty — say where the figures come from "
                   f"(official course, GPX, last year's results)")
    return out


def _hm(hours):
    total = int(round(hours * 60))
    return f"{total // 60}h{total % 60:02d}"


def _longest_run(dates):
    """Longest run of consecutive calendar days in a set of dates."""
    best, run, prev = 0, 0, None
    for d in sorted(set(dates)):
        run = run + 1 if prev is not None and d - prev == timedelta(days=1) else 1
        best, prev = max(best, run), d
    return best


def compare(goal, race_date, sessions, disc_sport, today=None):
    """Lines that put the race demand beside the sessions in one file.

    sessions: dicts with date (date or None), discipline, sport, hours
              (float or None when not computable) and category.
    disc_sport: {canonical discipline: sport}."""
    today = today or date.today()
    days = [d for d in (goal.get("demand") or []) if isinstance(d, dict)]
    name = (goal.get("description") or "Unnamed goal").strip()
    lines = [f"{name} · {goal.get('priority') or '?'} · {race_date.isoformat()} "
             f"(in {(race_date - today).days} days) · source: "
             f"{goal.get('demand_source') or 'not stated'}"]
    for i, d in enumerate(days, 1):
        parts = [f"Day {d.get('day') or i}", str(d.get("discipline") or "?")]
        if _num(d.get("distance_km")) is not None:
            parts.append(f"{d['distance_km']:g} km")
        if _num(d.get("climb_m")) is not None:
            parts.append(f"+{d['climb_m']:,.0f} m")
        if _num(d.get("expected_hours")) is not None:
            parts.append(f"~{_hm(d['expected_hours'])}")
        if d.get("terrain"):
            parts.append(str(d["terrain"]))
        lines.append("   race: " + " · ".join(parts))

    training = [s for s in sessions if s.get("category") in ("Training", "Race", "", None)]
    run_shown = set()
    for disc in dict.fromkeys(str(d.get("discipline")) for d in days if d.get("discipline")):
        sport = disc_sport.get(disc)
        race_hours = [d["expected_hours"] for d in days
                      if d.get("discipline") == disc and _num(d.get("expected_hours")) is not None]
        same = [s for s in training if s.get("discipline") == disc and s.get("hours")]
        if not race_hours:
            lines.append(f"   {disc}: expected_hours not declared — duration not compared")
        elif same:
            longest = max(s["hours"] for s in same)
            lines.append(f"   {disc}: longest session in this file {_hm(longest)} · longest "
                         f"race day ~{_hm(max(race_hours))} "
                         f"({longest / max(race_hours) * 100:.0f}%)")
        else:
            other = [s for s in training if s.get("sport") == sport and s.get("hours")]
            tail = (f"; longest {sport} session {_hm(max(s['hours'] for s in other))} "
                    f"(other disciplines)" if other else "")
            lines.append(f"   {disc}: no {disc} session in this file{tail}")
        if len(days) > 1 and sport not in run_shown:
            run_shown.add(sport)
            run = _longest_run(s["date"] for s in training
                               if s.get("sport") == sport and s.get("date"))
            lines.append(f"   {sport}: longest run of consecutive training days in this "
                         f"file {run} · race days {len(days)}")
    if any(_num(d.get("climb_m")) for d in days):
        lines.append("   climbing: not compared — session cards carry no elevation")
    return lines
