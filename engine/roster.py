"""
engine/roster.py — Infame Elite Endurance Coach v7
===================================================
One table for the whole roster, read from what is already on disk. Makes no
network call and computes no new figure: every value is copied from
data/<id>/state.json (the resolved #STATE) or data/<id>/athlete_data.json,
plus one subtraction against today's date.

Reports only. Rows are ordered by how many things the engine already flagged
for that athlete (its own state flags plus its heads-up Check items), then by
name. No score, no ranking of who is "worse": the count is only there so an
athlete with something to read is not buried in a list of seventeen.

An athlete is only as current as the last time the engine prepared them.
Every row says how old its numbers are, and an athlete on the account that
was never prepared is listed as such instead of being left out.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timezone


def _d(s):
    return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _roster_names(out_dir):
    """{id: name} from out/roster.md (the account's full list, as written by
    the last prep run). Empty if the file does not exist."""
    path = os.path.join(out_dir, "roster.md") if out_dir else None
    if not path or not os.path.exists(path):
        return {}
    names = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\|\s*(.+?)\s*\|\s*(\S+)\s*\|\s*(.+?)\s*\|\s*$", line)
            if m and m.group(1) not in ("Name", ":---") and m.group(2) != ":---":
                names[m.group(2)] = m.group(1)
    return names


def _row(aid, state, adata, as_of, now_ts, data_path):
    heads = state.get("heads_up") or {}
    checks = [c.get("text") for c in heads.get("checks") or []]
    flags = list((state.get("state") or {}).get("flags") or [])
    pmc = (state.get("signals") or {}).get("pmc") or {}
    taper = state.get("taper") or {}
    profile = (adata or {}).get("profile") or {}

    acts = [a for a in (adata or {}).get("activities") or [] if a.get("date")]
    idle = (as_of - max(_d(a["date"]) for a in acts)).days if acts else None

    race = None
    if taper.get("applicable") and taper.get("date"):
        race = {"name": taper.get("race"), "date": taper["date"],
                "days_out": (_d(taper["date"]) - as_of).days}

    resolved = state.get("resolved_at")
    age_days = (as_of - _d(resolved)).days if resolved else None
    fetched_hours = None
    if data_path and os.path.exists(data_path):
        fetched_hours = round((now_ts - os.path.getmtime(data_path)) / 3600, 1)

    return {
        "athlete_id": str(aid),
        "name": profile.get("name") or str(aid),
        "prepared": True,
        "load_recovery_state": (state.get("state") or {}).get("load_recovery_state"),
        "operational_state": (state.get("state") or {}).get("operational_state"),
        "tsb": pmc.get("tsb"),
        "ctl": pmc.get("ctl"),
        "days_since_last_activity": idle,
        "next_a_race": race,
        "flags": flags,
        "checks": checks,
        "attention_items": len(flags) + len(checks),
        "state_resolved_at": resolved,
        "state_age_days": age_days,
        "data_age_hours": fetched_hours,
    }


def build(data_dir, out_dir=None, as_of=None, now_ts=None):
    """Rows for every athlete under data_dir with a state.json, plus every
    athlete in out/roster.md that has none (prepared=False)."""
    as_of = as_of or date.today()
    now_ts = now_ts or datetime.now(timezone.utc).timestamp()
    rows, seen = [], set()

    if os.path.isdir(data_dir):
        for aid in sorted(os.listdir(data_dir)):
            base = os.path.join(data_dir, aid)
            state = _read_json(os.path.join(base, "state.json"))
            if not state:
                continue
            adata_path = os.path.join(base, "athlete_data.json")
            rows.append(_row(aid, state, _read_json(adata_path), as_of, now_ts, adata_path))
            seen.add(str(aid))

    for aid, name in _roster_names(out_dir).items():
        if aid not in seen:
            rows.append({"athlete_id": aid, "name": name, "prepared": False})

    rows.sort(key=lambda r: (not r["prepared"], -r.get("attention_items", 0),
                             r["name"].lower()))
    return rows


def _v(x, spec=""):
    return "—" if x is None else format(x, spec)


def render(rows, as_of=None):
    as_of = as_of or date.today()
    prepared = [r for r in rows if r["prepared"]]
    L = [f"## Roster — {as_of.isoformat()}", ""]
    L.append(f"{len(prepared)} prepared, {len(rows) - len(prepared)} not prepared. "
             f"Numbers are as of each athlete's last prep (see *State age*); "
             f"nothing here was fetched just now. Ordered by items already "
             f"flagged, most first.")
    L.append("")
    L.append("| Athlete | ID | State | TSB | CTL | Idle days | Next A race | "
             "Flags | Checks | State age |")
    L.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for r in rows:
        if not r["prepared"]:
            L.append(f"| {r['name']} | {r['athlete_id']} | not prepared | — | — | — | — | — | — | — |")
            continue
        race = r["next_a_race"]
        race_txt = f"{race['name']} · {race['date']} ({race['days_out']}d)" if race else "—"
        age = f"{r['state_age_days']}d" if r["state_age_days"] is not None else "—"
        L.append(f"| {r['name']} | {r['athlete_id']} | {_v(r['load_recovery_state'])} | "
                 f"{_v(r['tsb'], 'g')} | {_v(r['ctl'], 'g')} | "
                 f"{_v(r['days_since_last_activity'])} | {race_txt} | "
                 f"{len(r['flags'])} | {len(r['checks'])} | {age} |")
    with_items = [r for r in prepared if r["attention_items"]]
    if with_items:
        L.append("")
        L.append("### What was flagged")
        for r in with_items:
            L.append(f"**{r['name']}**")
            for t in r["flags"] + r["checks"]:
                L.append(f"- {t}")
    L.append("")
    return "\n".join(L)
