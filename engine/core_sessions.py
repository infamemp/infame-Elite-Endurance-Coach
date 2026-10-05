"""
core_sessions.py — the session types a race in each discipline cannot be
prepared without, looked for in the plan.

config/core_sessions.yaml lists, per race discipline, a few core sessions
(sustained threshold for a road race, repeated surges for MTB, uphill work
for trail...). Inside `applies_within_weeks` of the next A goal, this module
looks for each one in two places: the block being validated, and the
sessions prescribed over the last `look_back_weeks` (the planned events
Intervals.icu already holds, classified by engine/architecture.py).

A core session found in neither is a question for the head coach, never an
error: an injury or a deliberate phase choice is a valid answer. The
validator prints it as CHK-CORE, which never blocks; #STATE lists the last
date each one was prescribed.

The matching works on what architecture.py can read from the text — an
architecture name and an approximate class from generic cutpoints — so a
miss can also mean the session was written in a shape the classifier does
not name. The line says where it looked, so the coach can judge.

Idea taken from Prova Endurance (archetypes tagged as core per discipline).

Version: 1.0 (v7.23)
"""

import os
from datetime import date, datetime, timedelta

try:
    import yaml
except ImportError:  # pragma: no cover — every entry point already requires it
    yaml = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config", "core_sessions.yaml")
A_PRIORITIES = ("A+", "A", "A-")


def load_config(path=CONFIG_PATH):
    """The parsed core_sessions.yaml, or {} when it is missing or unreadable."""
    if yaml is None or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, ValueError):
        return {}


def _as_date(raw):
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    text = str(raw or "")[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def goal_discipline(goal):
    """The goal's discipline: `discipline`, else the first race day's."""
    disc = (goal or {}).get("discipline")
    if disc:
        return str(disc)
    for day in (goal or {}).get("demand") or []:
        if isinstance(day, dict) and day.get("discipline"):
            return str(day["discipline"])
    return None


def next_a_goal(goals, today=None):
    """(goal, race_date) for the nearest upcoming A+/A/A- goal; (None, None)."""
    today = today or date.today()
    found = []
    for g in goals or []:
        if not isinstance(g, dict):
            continue
        if str(g.get("priority") or "").upper() not in A_PRIORITIES:
            continue
        d = _as_date(g.get("date"))
        if d and d >= today:
            found.append((d, g))
    if not found:
        return None, None
    found.sort(key=lambda x: x[0])
    return found[0][1], found[0][0]


def matches(row, item):
    """True when a classified session (architecture.summarize_recent row, or
    the same keys from classify_session) is this core item."""
    seq = set(row.get("sequence") or ([row["architecture"]] if row.get("architecture") else []))
    cls = row.get("class")
    for alt in item.get("match") or []:
        archs = set(alt.get("architectures") or [])
        classes = set(alt.get("classes") or [])
        if not archs and not classes:
            continue
        if archs and not (seq & archs):
            continue
        if classes and cls not in classes:
            continue
        return True
    return False


def check(cfg, goals, block_rows, recent_rows, today=None):
    """Look for each core session of the next A goal's discipline.

    block_rows:  classified sessions of the block being checked
                 ({date, architecture, class, sequence}); date may be None.
    recent_rows: classified sessions already prescribed (summarize_recent).

    Returns a dict with `status`:
      no_goal      no upcoming A goal
      no_list      the goal's discipline has no core list (or none declared)
      too_far      the goal is further away than applies_within_weeks
      checked      `items` holds one entry per core session
    """
    today = today or date.today()
    defaults = (cfg or {}).get("defaults") or {}
    within = defaults.get("applies_within_weeks", 12)
    back = defaults.get("look_back_weeks", 3)

    goal, race_date = next_a_goal(goals, today)
    if not goal:
        return {"status": "no_goal"}
    disc = goal_discipline(goal)
    base = {"goal": (goal.get("description") or "Unnamed goal").strip(),
            "race_date": race_date.isoformat(), "days_to_race": (race_date - today).days,
            "discipline": disc, "applies_within_weeks": within, "look_back_weeks": back}
    items = ((cfg or {}).get("disciplines") or {}).get(disc or "") or []
    if not items:
        return {**base, "status": "no_list"}
    if (race_date - today).days > within * 7:
        return {**base, "status": "too_far"}

    since = today - timedelta(weeks=back)
    # Already-uploaded future sessions count too: they are in the plan.
    recent = [r for r in recent_rows or []
              if (_as_date(r.get("date")) or date.min) >= since]
    out = []
    for item in items:
        in_block = [r for r in block_rows or [] if matches(r, item)]
        in_recent = [r for r in recent if matches(r, item)]
        entry = {"id": item.get("id"), "label": item.get("label") or item.get("id"),
                 "why": item.get("why"), "source": item.get("source") or "coach judgement",
                 "found_in": None, "date": None}
        if in_block:
            dates = [_as_date(r.get("date")) for r in in_block if _as_date(r.get("date"))]
            entry.update(found_in="block", date=min(dates).isoformat() if dates else None)
        elif in_recent:
            entry.update(found_in="recent",
                         date=max(_as_date(r.get("date")) for r in in_recent).isoformat())
        out.append(entry)
    return {**base, "status": "checked", "items": out}


def _dmy(iso):
    d = _as_date(iso)
    return d.strftime("%d-%m-%Y") if d else "?"


def _source_text(src):
    return ", ".join(src) if isinstance(src, list) else str(src)


def validator_lines(result):
    """(info_lines, warnings) for validate_block. Warnings are message text;
    the caller prints them as CHK-CORE."""
    status = (result or {}).get("status")
    if status in (None, "no_goal"):
        return [], []
    head = (f"{result['goal']} · {result['discipline'] or 'discipline not declared'} · "
            f"{_dmy(result['race_date'])} (in {result['days_to_race']} days)")
    if status == "no_list":
        why = ("no discipline declared on the goal" if not result["discipline"]
               else f"no core list for '{result['discipline']}' in config/core_sessions.yaml")
        return [head, f"   not checked: {why}"], []
    if status == "too_far":
        return [head, f"   not checked yet: the list applies from "
                      f"{result['applies_within_weeks']} weeks out (base work is general)"], []
    lines, warns = [head], []
    for it in result["items"]:
        if it["found_in"] == "block":
            lines.append(f"   ok  {it['label']}: in this block"
                         + (f" ({_dmy(it['date'])})" if it["date"] else ""))
        elif it["found_in"] == "recent":
            lines.append(f"   ok  {it['label']}: prescribed {_dmy(it['date'])}")
        else:
            warns.append(f"{it['label']}: not in this block nor in the sessions prescribed "
                         f"over the last {result['look_back_weeks']} weeks — {it['why']} "
                         f"(source: {_source_text(it['source'])}). A deliberate omission "
                         f"is a valid answer; say why.")
    return lines, warns


def render_state(result):
    """The #STATE section."""
    lines = ["## CORE SESSIONS (next A goal, computed)", ""]
    status = (result or {}).get("status")
    if status in (None, "no_goal"):
        lines.append("No upcoming A goal declared — nothing to check.")
        return "\n".join(lines)
    lines.append(f"{result['goal']} · {result['discipline'] or 'discipline not declared'} · "
                 f"{_dmy(result['race_date'])} (in {result['days_to_race']} days).")
    if status == "no_list":
        lines.append("No core list for this discipline in config/core_sessions.yaml.")
        return "\n".join(lines)
    if status == "too_far":
        lines.append(f"Checked from {result['applies_within_weeks']} weeks out; until then "
                     f"base work is general (CTB-C02-025, HPC-C08-005).")
        return "\n".join(lines)
    lines += [f"Looked for in the sessions prescribed over the last "
              f"{result['look_back_weeks']} weeks. A missing one is a question for the "
              f"head coach, never an error.", "",
              "| Core session | Last prescribed | Why | Source |", "|:---|:---|:---|:---|"]
    for it in result["items"]:
        when = _dmy(it["date"]) if it["date"] else "**none**"
        lines.append(f"| {it['label']} | {when} | {it['why']} | {_source_text(it['source'])} |")
    return "\n".join(lines)
