"""
engine/execution.py — Infame Elite Endurance Coach v7
======================================================
Planned versus done. Answers one question from data Intervals.icu already
holds: of the sessions that were planned, which did the athlete actually do,
and how did they go?

Pairing is Intervals.icu's own. An activity carries `paired_event_id` when
Intervals.icu matched it to a planned event; this module never guesses a
match by date or sport. A planned session with no paired activity is reported
as "unpaired", not "missed": the athlete may have skipped it, or may have
done it and never paired it. Only the head coach knows which.

Reports only. Nothing here judges, scores or advises, and nothing blocks
anything. Every number is read from data/<id>/athlete_data.json:

  recent_sessions  planned events, 8 weeks back  (needs `id`)
  activities       what was done                  (needs `paired_event_id`,
                                                   `compliance`, `rpe`, `feel`)

Fields Intervals.icu did not record stay None. A missing RPE is never a zero.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

# Planned events that are sessions. Notes, holidays, injury/sick markers and
# calendar targets are events too, but they are not something to be paired.
SESSION_CATEGORIES = ("WORKOUT", "RACE_A", "RACE_B", "RACE_C")

# The fetcher looks 56 days back (fetch_athlete_data.RECENT_SESSIONS_DAYS).
MAX_WINDOW_DAYS = 56


def _d(s):
    return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _mean(values, digits=1):
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), digits) if vals else None


def _minutes(seconds):
    s = _num(seconds)
    return round(s / 60) if s is not None else None


def _week_start(d):
    return d - timedelta(days=d.weekday())


def analyze(data, days=28, as_of=None):
    """Planned versus done over the last `days` days (ending today).

    Returns {"available": False, "reason": ..., "needs_refresh": bool} when
    the cached data cannot answer, so a caller can tell "nothing to report"
    from "cannot tell"."""
    as_of = as_of or date.today()
    capped = days > MAX_WINDOW_DAYS
    days = min(max(int(days), 1), MAX_WINDOW_DAYS)
    start = as_of - timedelta(days=days - 1)

    events = data.get("recent_sessions")
    if events is None:
        return {"available": False, "needs_refresh": True,
                "reason": "no planned-event history in the cached data "
                          "(recent_sessions is absent)"}

    planned = [e for e in events
               if e.get("date") and e.get("category") in SESSION_CATEGORIES
               and start <= _d(e["date"]) <= as_of]
    if planned and not any(e.get("id") is not None for e in planned):
        return {"available": False, "needs_refresh": True,
                "reason": "the cached planned events carry no event id, so "
                          "activities cannot be paired to them — the data was "
                          "fetched before pairing was recorded"}

    acts = [a for a in data.get("activities") or []
            if a.get("date") and start <= _d(a["date"]) <= as_of]

    by_event = {}
    for a in acts:
        if a.get("paired_event_id") is not None:
            by_event.setdefault(a["paired_event_id"], []).append(a)
    unpaired_by_day = {}
    for a in acts:
        if a.get("paired_event_id") is None:
            unpaired_by_day.setdefault(a["date"], []).append(a)

    rows = []
    for e in sorted(planned, key=lambda x: (x["date"], str(x.get("name")))):
        paired = by_event.get(e.get("id")) or []
        d = _d(e["date"])
        if paired:
            status = "paired"
        elif d < as_of:
            status = "unpaired"
        else:
            status = "pending"          # today, not done yet
        loads = [_num(a.get("training_load")) for a in paired]
        times = [_num(a.get("moving_time")) for a in paired]
        row = {
            "date": e["date"],
            "name": e.get("name"),
            "category": e.get("category"),
            "event_id": e.get("id"),
            "status": status,
            "planned_load": _num(e.get("planned_load")),
            "planned_min": _minutes(e.get("planned_time")),
            "actual_load": (sum(v for v in loads if v is not None)
                            if any(v is not None for v in loads) else None),
            "actual_min": (_minutes(sum(v for v in times if v is not None))
                           if any(v is not None for v in times) else None),
            "compliance": _mean([_num(a.get("compliance")) for a in paired]),
            "rpe": _mean([_num(a.get("rpe")) for a in paired]),
            "feel": _mean([_num(a.get("feel")) for a in paired]),
        }
        if status == "unpaired" and unpaired_by_day.get(e["date"]):
            row["note"] = ("an activity on the same day is not paired to any "
                           "planned event — it may be this session")
        rows.append(row)

    extras = [{
        "date": a["date"], "name": a.get("name"), "type": a.get("type"),
        "load": _num(a.get("training_load")),
        "minutes": _minutes(a.get("moving_time")),
    } for a in sorted(acts, key=lambda x: x["date"])
        if a.get("paired_event_id") is None]

    paired_rows = [r for r in rows if r["status"] == "paired"]
    n_due = sum(1 for r in rows if r["status"] in ("paired", "unpaired"))
    both = [r for r in paired_rows
            if r["planned_load"] is not None and r["actual_load"] is not None]
    planned_load_both = sum(r["planned_load"] for r in both)
    both_ids = {id(r) for r in both}

    weeks = {}
    for r in rows:
        w = _week_start(_d(r["date"])).isoformat()
        wk = weeks.setdefault(w, {"week_start": w, "planned": 0, "paired": 0,
                                  "unpaired": 0, "pending": 0,
                                  "planned_load": 0.0, "actual_load": 0.0})
        wk["planned"] += 1
        wk[r["status"]] += 1
        if id(r) in both_ids:
            wk["planned_load"] += r["planned_load"]
            wk["actual_load"] += r["actual_load"]
    for wk in weeks.values():
        wk["planned_load"] = round(wk["planned_load"], 1)
        wk["actual_load"] = round(wk["actual_load"], 1)

    feels = [r["feel"] for r in paired_rows if r["feel"] is not None]
    return {
        "available": True,
        "window": {"from": start.isoformat(), "to": as_of.isoformat(),
                   "days": days, "capped_at_fetched_history": capped},
        "totals": {
            "planned_sessions": len(rows),
            "due": n_due,
            "paired": len(paired_rows),
            "unpaired": sum(1 for r in rows if r["status"] == "unpaired"),
            "pending_today": sum(1 for r in rows if r["status"] == "pending"),
            "paired_pct_of_due": round(100 * len(paired_rows) / n_due) if n_due else None,
            "planned_load_of_paired": round(planned_load_both, 1) if both else None,
            "actual_load_of_paired": (round(sum(r["actual_load"] for r in both), 1)
                                      if both else None),
            "load_pct_of_planned": (round(100 * sum(r["actual_load"] for r in both)
                                          / planned_load_both) if planned_load_both else None),
            "mean_compliance": _mean([r["compliance"] for r in paired_rows]),
            "mean_rpe": _mean([r["rpe"] for r in paired_rows]),
            "mean_feel": _mean(feels),
            "sessions_with_rpe": sum(1 for r in paired_rows if r["rpe"] is not None),
            "sessions_with_feel": len(feels),
            "extra_activities": len(extras),
            "extra_load": round(sum(x["load"] for x in extras if x["load"] is not None), 1),
        },
        "weeks": [weeks[k] for k in sorted(weeks)],
        "sessions": rows,
        "extra_activities": extras,
        "source": "Intervals.icu paired_event_id (its own pairing); recent_sessions "
                  "for the plan, activities for what was done",
        "notes": ["unpaired = no activity paired to the planned event in "
                  "Intervals.icu; skipped or done-but-not-paired cannot be "
                  "told apart from here",
                  "feel is Intervals.icu's 1-5 scale, reported raw; RPE is 1-10"],
    }


def _v(x, suffix=""):
    return "—" if x is None else f"{x:g}{suffix}"


def render(result):
    """Compact Markdown for the coach to read. Reports only."""
    if not result.get("available"):
        return f"Execution: not available — {result.get('reason')}"
    t, w = result["totals"], result["window"]
    L = [f"## Planned vs done — {w['from']} to {w['to']}", ""]
    if t["planned_sessions"] == 0:
        L.append("No planned sessions in this window.")
    else:
        L.append(f"- Sessions due: {t['due']} · paired: {t['paired']} · "
                 f"unpaired: {t['unpaired']}"
                 + (f" · pending today: {t['pending_today']}" if t["pending_today"] else "")
                 + (f" · {t['paired_pct_of_due']}% of due sessions paired"
                    if t["paired_pct_of_due"] is not None else ""))
        L.append(f"- Load, paired sessions: {_v(t['actual_load_of_paired'])} done of "
                 f"{_v(t['planned_load_of_paired'])} planned"
                 + (f" ({t['load_pct_of_planned']}%)" if t["load_pct_of_planned"] is not None else ""))
        L.append(f"- Mean compliance {_v(t['mean_compliance'], '%')} · mean RPE "
                 f"{_v(t['mean_rpe'])} ({t['sessions_with_rpe']} sessions rated) · "
                 f"mean feel {_v(t['mean_feel'])} ({t['sessions_with_feel']} rated)")
        L.append("")
        L.append("| Date | Session | Status | Load plan→done | Min plan→done | Compl. | RPE | Feel |")
        L.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in result["sessions"]:
            L.append(f"| {r['date']} | {r['name'] or '—'} | {r['status']} | "
                     f"{_v(r['planned_load'])}→{_v(r['actual_load'])} | "
                     f"{_v(r['planned_min'])}→{_v(r['actual_min'])} | "
                     f"{_v(r['compliance'], '%')} | {_v(r['rpe'])} | {_v(r['feel'])} |")
    if result["extra_activities"]:
        L.append("")
        L.append(f"Activities not paired to any plan: {t['extra_activities']} "
                 f"(load {t['extra_load']:g}).")
    L.append("")
    L.append("_Unpaired = no activity paired in Intervals.icu; skipped or "
             "done-but-not-paired cannot be told apart from here._")
    return "\n".join(L) + "\n"
