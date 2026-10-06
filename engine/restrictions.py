"""
restrictions.py — the limits an injury puts on prescription, checked.

`limitations.restrictions` in config/athletes/<id>.yaml turns what the
athlete, the physio or the doctor said ("no running over 30 minutes",
"nothing above endurance", "no hills", "not two days in a row") into rules
the validator can check. Each entry:

    - what: Achilles tendinopathy     # what it is, in a few words
      source: physio, 01-10-2026      # who said it, and when
      from: 2026-10-01                # YYYY-MM-DD, or null = already active
      until: 2026-11-15               # YYYY-MM-DD, or null = until removed
      sport: running                  # cycling | running | null = every sport
      disciplines: []                 # narrower, e.g. [trail_run]; [] = all of the sport
      max_minutes: 30                 # longest session
      max_class: endurance            # highest class any step may reach
      max_sessions_per_week: 3        # in that sport (or those disciplines)
      no_consecutive_days: true       # never two days in a row
      avoid_architectures: [climb_simulation, sprints]

Precise limits block (HC-LIMIT): duration, class (the author's own zone
table, at the top of each step's range), sessions per week and consecutive
days, all counted in the file being validated. `avoid_architectures` only
warns (CHK-LIMIT), because the architecture is read from the text by a
heuristic (engine/architecture.py) and can misread.

A restriction is the head coach's decision. When the head coach approves an
exception, the restriction is changed in the profile — the validator never
argues with it.

Prova Endurance does not have this.

Version: 1.0 (v7.24)
"""

from datetime import date, datetime, timedelta

FIELDS = ("what", "source", "from", "until", "sport", "disciplines", "max_minutes",
          "max_class", "max_sessions_per_week", "no_consecutive_days", "avoid_architectures")
SPORTS = ("cycling", "running")


from shared import as_date as _as_date  # noqa: E402 — shared parser (v7.33)

def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def declared(profile):
    """The restriction entries of a profile ([] when none)."""
    r = ((profile or {}).get("limitations") or {}).get("restrictions") or []
    return [x for x in r if isinstance(x, dict)] if isinstance(r, list) else []


def applies(r, on_date, sport, discipline):
    """True when restriction `r` covers a session on that date, sport and
    discipline. A session with no date is covered by every restriction that
    is not limited to a future start (the safe reading)."""
    if r.get("sport") and r["sport"] != sport:
        return False
    discs = r.get("disciplines") or []
    if discs and discipline not in discs:
        return False
    start, end = _as_date(r.get("from")), _as_date(r.get("until"))
    if on_date is None:
        return not (start and start > date.today())
    if start and on_date < start:
        return False
    if end and on_date > end:
        return False
    return True


def _label(r):
    what = r.get("what") or "declared restriction"
    end = _as_date(r.get("until"))
    return f"{what}" + (f" (until {end.strftime('%d-%m-%Y')})" if end else "")


def check_session(restrictions, on_date, sport, discipline, total_secs, undetermined,
                  step_classes, architectures, class_order):
    """(errors, warnings) for one session, as (code, line, message).

    step_classes:  [(line, class)] — each step's class at the top of its range.
    architectures: the session's architecture sequence, [] when unknown."""
    errors, warns = [], []
    rank = {c: i for i, c in enumerate(class_order)}
    for r in restrictions:
        if not applies(r, on_date, sport, discipline):
            continue
        lab = _label(r)
        mx = _num(r.get("max_minutes"))
        if mx is not None:
            if undetermined:
                warns.append(("CHK-LIMIT", "-", f"{lab}: max {mx:g} min — cannot check, the "
                              f"session has distance steps with no fixed duration"))
            elif total_secs is not None and total_secs > mx * 60 + 30:
                errors.append(("HC-LIMIT", "-", f"{lab}: session lasts {total_secs / 60:.0f} min, "
                               f"the restriction allows {mx:g} min"))
        top = r.get("max_class")
        if top in rank:
            for line, cls in step_classes:
                if cls in rank and rank[cls] > rank[top]:
                    errors.append(("HC-LIMIT", line, f"{lab}: step reaches {cls}, the "
                                   f"restriction allows up to {top}"))
        avoid = set(r.get("avoid_architectures") or [])
        hit = [a for a in architectures or [] if a in avoid]
        if hit:
            warns.append(("CHK-LIMIT", "-", f"{lab}: the session reads as {', '.join(hit)}, "
                          f"which the restriction says to avoid"))
    return errors, warns


def check_file(restrictions, sessions):
    """Errors across the sessions of one file for one athlete: sessions per
    week and consecutive days. sessions: [{date, sport, discipline}]."""
    errors = []
    for r in restrictions:
        covered = sorted({s["date"] for s in sessions if s.get("date")
                          and applies(r, s["date"], s.get("sport"), s.get("discipline"))})
        if not covered:
            continue
        lab = _label(r)
        mx = _num(r.get("max_sessions_per_week"))
        if mx is not None:
            weeks = {}
            for d in covered:
                monday = d - timedelta(days=d.weekday())
                weeks[monday] = weeks.get(monday, 0) + 1
            for monday, n in sorted(weeks.items()):
                if n > mx:
                    errors.append(("HC-LIMIT", "-", f"{lab}: {n} sessions in the week of "
                                   f"{monday.strftime('%d-%m-%Y')}, the restriction allows {mx:g}"))
        if r.get("no_consecutive_days") is True:
            for a, b in zip(covered, covered[1:]):
                if b - a == timedelta(days=1):
                    errors.append(("HC-LIMIT", "-", f"{lab}: sessions on consecutive days "
                                   f"{a.strftime('%d-%m-%Y')} and {b.strftime('%d-%m-%Y')}"))
    return errors


def profile_warnings(profile, disciplines, class_order, architectures, today=None):
    """Problems in the restriction entries, for build_profile's warnings."""
    today = today or date.today()
    raw = ((profile or {}).get("limitations") or {}).get("restrictions")
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        return ["`limitations.restrictions` must be a list, one entry per restriction"]
    W = []
    for i, r in enumerate(raw, 1):
        w = f"limitations.restrictions[{i}]"
        if not isinstance(r, dict):
            W.append(f"`{w}` must be a mapping like {{what: ..., max_minutes: 30}}")
            continue
        for k in r:
            if k not in FIELDS:
                W.append(f"`{w}.{k}` is not a known field ({', '.join(FIELDS)})")
        if not r.get("what"):
            W.append(f"`{w}.what` is empty — say what the restriction is for")
        if not r.get("source"):
            W.append(f"`{w}.source` is empty — who said it, and when")
        if r.get("sport") not in (None,) + SPORTS:
            W.append(f"`{w}.sport`: '{r['sport']}' is not one of {', '.join(SPORTS)}")
        for d in r.get("disciplines") or []:
            if disciplines and d not in disciplines:
                W.append(f"`{w}.disciplines`: '{d}' is not a canonical discipline")
        for k in ("from", "until"):
            if r.get(k) not in (None, "") and _as_date(r.get(k)) is None:
                W.append(f"`{w}.{k}`: '{r[k]}' is not YYYY-MM-DD")
        for k in ("max_minutes", "max_sessions_per_week"):
            if r.get(k) is not None and _num(r.get(k)) is None:
                W.append(f"`{w}.{k}`: '{r[k]}' is not a number")
        if r.get("max_class") is not None and r["max_class"] not in class_order:
            W.append(f"`{w}.max_class`: '{r['max_class']}' is not one of {', '.join(class_order)}")
        for a in r.get("avoid_architectures") or []:
            if architectures and a not in architectures:
                W.append(f"`{w}.avoid_architectures`: '{a}' is not an architecture")
        end = _as_date(r.get("until"))
        if end and end < today:
            W.append(f"`{w}` ({r.get('what') or '?'}) ended on {end.strftime('%d-%m-%Y')} — "
                     f"remove it, or extend `until` if it still applies")
        checks = [k for k in ("max_minutes", "max_class", "max_sessions_per_week",
                              "no_consecutive_days", "avoid_architectures") if r.get(k)]
        if not checks:
            W.append(f"`{w}` has no limit the validator can check (max_minutes, max_class, "
                     f"max_sessions_per_week, no_consecutive_days, avoid_architectures)")
    return W


def active_on(profile, on_date=None):
    """Restrictions in force on a date (today by default)."""
    on_date = on_date or date.today()
    out = []
    for r in declared(profile):
        start, end = _as_date(r.get("from")), _as_date(r.get("until"))
        if (start is None or start <= on_date) and (end is None or end >= on_date):
            out.append(r)
    return out


def summary(r):
    """One line for the Heads-up: what, where and the limits."""
    where = ", ".join(r.get("disciplines") or []) or r.get("sport") or "every sport"
    limits = []
    if _num(r.get("max_minutes")) is not None:
        limits.append(f"max {r['max_minutes']:g} min")
    if r.get("max_class"):
        limits.append(f"up to {r['max_class']}")
    if _num(r.get("max_sessions_per_week")) is not None:
        limits.append(f"max {r['max_sessions_per_week']:g}/week")
    if r.get("no_consecutive_days") is True:
        limits.append("never two days in a row")
    if r.get("avoid_architectures"):
        limits.append("avoid " + ", ".join(r["avoid_architectures"]))
    return (f"Active restriction — {_label(r)} · {where}: "
            f"{'; '.join(limits) or 'no checkable limit'}. Source: {r.get('source') or 'not stated'}.")
