"""
plan_checks.py — the week as a whole, not session by session.

Five checks on the sessions of one block file, beside the athlete's real
history (data/<id>/athlete_data.json activities):

  CHK-SPACING   two hard days in a row
  CHK-RAMP      one sport's planned weekly load against its last weeks
  CHK-RECOVERY  too many loading weeks in a row with no lighter week
  CHK-EASY      too little of the week's written time is easy
  CHK-TAPER     the taper cuts too little or too much volume, drops
                sessions, or drops intensity

Every check warns, never blocks: each is a question for the head coach, and
a deliberate choice is a valid answer. The values live in `plan_checks` and
`taper` of config/decision_thresholds.yaml, with their sources. An athlete
can override any value, or switch a check off, in config/athletes/<id>.yaml:

    plan_checks:
      reason: "returning from 3 weeks off; physio wants 4 easy weeks"
      easy_share: {min_pct: 85}
      off: [ramp]

Idea taken from Prova Endurance (JudgePlanDraft and its rules); Infame keeps
its own rule that advisories never block.

Version: 1.0 (v7.25)
"""

from datetime import date, datetime, timedelta

CHECKS = ("spacing", "ramp", "recovery", "easy_share", "taper")
_CYCLING = {"ride", "virtualride", "gravelride", "mtb", "mountainbikeride", "ebikeride"}
_RUNNING = {"run", "virtualrun", "trailrun"}


def sport_of(activity_type):
    t = (activity_type or "").strip().lower()
    return "cycling" if t in _CYCLING else "running" if t in _RUNNING else None


def _as_date(raw):
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw)[:10])
    except (TypeError, ValueError):
        return None


def _monday(d):
    return d - timedelta(days=d.weekday())


def _dmy(d):
    return d.strftime("%d-%m-%Y")


def settings(cfg, profile):
    """(values, off, reason): config values with the athlete's overrides."""
    base = {k: dict(v) if isinstance(v, dict) else v for k, v in (cfg or {}).items()}
    over = (profile or {}).get("plan_checks") or {}
    if not isinstance(over, dict):
        return base, set(), None
    for k, v in over.items():
        if k in base and isinstance(v, dict) and isinstance(base[k], dict):
            base[k].update(v)
    off = {str(x) for x in (over.get("off") or [])}
    return base, off, over.get("reason")


def real_days(activities):
    """{date: {"load": {sport|None: tss}, "minutes": m, "sessions": n}}."""
    out = {}
    for a in activities or []:
        d = _as_date(a.get("date"))
        if not d:
            continue
        day = out.setdefault(d, {"load": {}, "minutes": 0.0, "sessions": 0})
        sp = sport_of(a.get("type"))
        day["load"][sp] = day["load"].get(sp, 0.0) + (a.get("training_load") or 0)
        day["minutes"] += (a.get("moving_time") or 0) / 60
        day["sessions"] += 1
    return out


def _week_loads(real, sessions, today, sport=None):
    """{monday: load} — real history for days before today, the file's
    sessions for the days it writes (they replace real ones that day)."""
    file_days = {s["date"] for s in sessions if s.get("date")}
    weeks = {}
    for d, day in real.items():
        if d >= today or d in file_days:
            continue
        v = sum(day["load"].values()) if sport is None else day["load"].get(sport, 0.0)
        weeks[_monday(d)] = weeks.get(_monday(d), 0.0) + v
    for s in sessions:
        if not s.get("date") or (sport is not None and s.get("sport") != sport):
            continue
        weeks[_monday(s["date"])] = weeks.get(_monday(s["date"]), 0.0) + (s.get("load") or 0)
    return weeks


def run(cfg, taper_cfg, profile, sessions, activities, goal=None, race_date=None, today=None,
        uploaded=None):
    """Return (lines, warnings). warnings: [(code, message)].

    sessions: the file's Training/Race sessions for ONE athlete —
      {date, sport, category, load, minutes, easy_minutes, hard_minutes}
      (minutes = costed minutes; a session without a date is ignored).
    uploaded: the same rows for weeks already uploaded to Intervals.icu, on
      dates this file does not write (v7.32). They are context — loads, hard
      days, taper coverage — and never get a warning of their own: every
      warning is about a week or a day this file writes.
    goal/race_date: the next A goal, or None."""
    today = today or date.today()
    values, off, reason = settings(cfg, profile)
    note = f" (athlete exception: {reason})" if reason else ""
    cards = [s for s in sessions if s.get("date")]
    sessions = [s for s in cards if s.get("category") != "Rest"]
    file_dates = {s["date"] for s in cards}
    extra = [u for u in (uploaded or []) if u.get("date") and u["date"] not in file_dates]
    context = sessions + extra          # what the athlete will do: this file + uploaded weeks
    real = real_days(activities)
    lines, warns = [], []
    if not sessions:
        return ["no dated training session in this file — nothing to check"], []
    hs = values.get("hard_session") or {}
    hard_min = hs.get("min_minutes", 8)
    hard_dates = sorted({s["date"] for s in context if (s.get("hard_minutes") or 0) >= hard_min})

    # ── Spacing ──────────────────────────────────────────────────
    if "spacing" not in off:
        gap = (values.get("spacing") or {}).get("min_easy_days_between_hard", 1)
        pairs = [(a, b) for a, b in zip(hard_dates, hard_dates[1:]) if (b - a).days <= gap
                 and (a in file_dates or b in file_dates)]
        for a, b in pairs:
            between = "no easier day" if gap == 1 else f"fewer than {gap} easier days"
            warns.append(("CHK-SPACING", f"hard days {_dmy(a)} and {_dmy(b)} with {between} "
                          f"between them (CTB-C05-035){note} — deliberate before a stage "
                          f"race is a valid answer; say so"))
        lines.append(f"spacing: {len(hard_dates)} hard day(s), {len(pairs)} too close")

    # ── Ramp per sport ───────────────────────────────────────────
    if "ramp" not in off:
        rc = values.get("ramp") or {}
        n_base, mx, floor = rc.get("baseline_weeks", 4), rc.get("max_ratio", 1.3), \
            rc.get("min_baseline_load", 50)
        this_monday = _monday(today)
        for sport in sorted({s["sport"] for s in sessions if s.get("sport")}):
            base_weeks = [this_monday - timedelta(weeks=i) for i in range(1, n_base + 1)]
            real_only = _week_loads(real, [], today, sport)
            base = sum(real_only.get(m, 0.0) for m in base_weeks) / n_base
            planned = _week_loads(real, context, today, sport)
            file_weeks = sorted({_monday(s["date"]) for s in sessions if s.get("sport") == sport})
            if base < floor:
                lines.append(f"ramp {sport}: not checked — last {n_base} weeks average "
                             f"{base:.0f} TSS (no base to compare with)")
                continue
            for m in file_weeks:
                ratio = planned.get(m, 0.0) / base
                lines.append(f"ramp {sport}: week of {_dmy(m)} {planned.get(m, 0.0):.0f} TSS = "
                             f"{ratio:.2f}x the last {n_base} weeks ({base:.0f})")
                if ratio > mx:
                    warns.append(("CHK-RAMP", f"{sport}, week of {_dmy(m)}: {ratio:.2f}x the "
                                  f"average of the last {n_base} weeks, above {mx:g}x{note}"))

    # ── Loading weeks in a row ───────────────────────────────────
    if "recovery" not in off:
        rv = values.get("recovery") or {}
        mx_w, drop = rv.get("max_loading_weeks", 3), rv.get("drop_pct", 20)
        weeks = _week_loads(real, context, today)
        file_weeks = sorted({_monday(s["date"]) for s in sessions})
        first = min(weeks) if weeks else None
        for m in file_weeks:
            seq = [m - timedelta(weeks=i) for i in range(mx_w + 3, -1, -1)]
            if first is None or seq[0] < first:
                lines.append(f"recovery: week of {_dmy(m)} not checked — too little history")
                continue
            run_len = 0
            for i in range(3, len(seq)):
                prev = [weeks.get(seq[j], 0.0) for j in range(i - 3, i)]
                mean = sum(prev) / 3
                load = weeks.get(seq[i], 0.0)
                lighter = load == 0 or (mean > 0 and load <= mean * (1 - drop / 100))
                run_len = 0 if lighter else run_len + 1
            lines.append(f"recovery: week of {_dmy(m)} is loading week {run_len} in a row"
                         if run_len else f"recovery: week of {_dmy(m)} is a lighter week")
            if run_len > mx_w:
                warns.append(("CHK-RECOVERY", f"week of {_dmy(m)} would be loading week "
                              f"{run_len} in a row with no week at least {drop:g}% lighter; "
                              f"Friel places one every 3rd or 4th week (CTB-C08-026){note}"))

    # ── Easy share by time ───────────────────────────────────────
    if "easy_share" not in off:
        ec = values.get("easy_share") or {}
        mn, min_s = ec.get("min_pct", 70), ec.get("min_sessions", 3)
        by_week = {}
        for s in context:
            by_week.setdefault(_monday(s["date"]), []).append(s)
        own_weeks = {_monday(s["date"]) for s in sessions}
        for m, ss in sorted(by_week.items()):
            if m not in own_weeks:
                continue
            total = sum(s.get("minutes") or 0 for s in ss)
            if len(ss) < min_s or total <= 0:
                lines.append(f"easy share: week of {_dmy(m)} not checked — {len(ss)} session(s)")
                continue
            pct = sum(s.get("easy_minutes") or 0 for s in ss) / total * 100
            lines.append(f"easy share: week of {_dmy(m)} {pct:.0f}% of written time easy")
            if pct < mn:
                warns.append(("CHK-EASY", f"week of {_dmy(m)}: {pct:.0f}% of the written time "
                              f"is recovery or endurance, below {mn:g}%{note}"))

    # ── Taper ────────────────────────────────────────────────────
    if "taper" not in off and goal and race_date:
        t_days = (taper_cfg or {}).get("a_race_taper_days", 14)
        pre_days = (taper_cfg or {}).get("a_race_pre_taper_days", 21)
        band = (taper_cfg or {}).get("volume_reduction_pct") or {"min": 21, "max": 60}
        freq_min = (taper_cfg or {}).get("min_frequency_pct_of_pretaper", 80)
        min_hist = (values.get("taper") or {}).get("min_history_days", 14)
        start = race_date - timedelta(days=t_days)
        in_win = [s for s in context if start <= s["date"] < race_date
                  and s.get("category") != "Race"]
        if not any(start <= s["date"] < race_date for s in sessions):
            in_win = []          # this file writes no taper day: nothing to say
        card_dates = [c["date"] for c in cards] + [u["date"] for u in extra]
        f_first, f_last = min(card_dates), max(card_dates)
        days = [start + timedelta(days=i) for i in range((race_date - start).days)]
        gaps = [d for d in days if d >= today and not f_first <= d <= f_last]
        if in_win and gaps:
            lines.append(f"taper: not checked — the file does not cover "
                         f"{_dmy(gaps[0])} to {_dmy(gaps[-1])} before the race "
                         f"({_dmy(race_date)}); validate the taper weeks together")
        elif in_win:
            # Past days come from real activities, the rest from this file.
            file_dates = set(card_dates)
            span = len(days)
            minutes = sum(s.get("minutes") or 0 for s in in_win)
            count = len(in_win)
            for d in days:
                if d < today and d not in file_dates and d in real:
                    minutes += real[d]["minutes"]
                    count += real[d]["sessions"]
            hist = [start - timedelta(days=i) for i in range(1, pre_days + 1)]
            hist = [d for d in hist if d < today]
            if len(hist) < min_hist:
                lines.append(f"taper: not checked — {len(hist)} day(s) of real history "
                             f"before it (needs {min_hist})")
            else:
                pre_min = sum(real[d]["minutes"] for d in hist if d in real) / len(hist)
                pre_n = sum(real[d]["sessions"] for d in hist if d in real) / len(hist)
                if pre_min <= 0:
                    lines.append("taper: not checked — no real training before it")
                else:
                    cut = (1 - (minutes / span) / pre_min) * 100
                    freq = ((count / span) / pre_n * 100) if pre_n else None
                    side = "below" if cut >= 0 else "above"
                    lines.append(f"taper: {_dmy(start)} → race {_dmy(race_date)} · {span} day(s) "
                                 f"counted · volume {abs(cut):.0f}% {side} the {len(hist)} days "
                                 f"before" + (f" · frequency {freq:.0f}% of before"
                                              if freq is not None else ""))
                    if not band["min"] <= cut <= band["max"]:
                        warns.append(("CHK-TAPER", f"volume cut {cut:.0f}% (negative = more than before), outside "
                                      f"{band['min']}-{band['max']}% for cycling and running "
                                      f"(Bosquet 2007, TPOP-C09-022){note}"))
                    if freq is not None and freq < freq_min:
                        warns.append(("CHK-TAPER", f"sessions at {freq:.0f}% of the pre-taper "
                                      f"frequency, below {freq_min}% — cut duration, not "
                                      f"sessions (TPOP-C04-044){note}"))
            if not any((s.get("hard_minutes") or 0) >= hard_min for s in in_win):
                warns.append(("CHK-TAPER", f"no hard day in the taper sessions of this file — "
                              f"intensity is kept while volume drops (TPOP-C09-006){note}"))
    if reason:
        lines.append(f"athlete exception in force: {reason}" +
                     (f" · off: {', '.join(sorted(off))}" if off else ""))
    return lines, warns
