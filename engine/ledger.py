"""
ledger.py — what was decided and what the gate said, one line per event.

Every tool that changes something, and every run of the validator, appends
one JSON line to config/athletes/ledger/<athlete_id>.jsonl. That folder sits
with the declared profiles, so it travels with them between computers. It
is never committed (.gitignore) and never edited by hand.

Two uses:
  * A settled decision is not decided again: the head coach and the coach
    can see when a threshold changed, which weeks were uploaded or removed,
    when the profile or the continuity record changed and what the falsifier
    was at the time.
  * Evidence for later design choices. Each validator run records its
    result and the codes it printed, so `summary()` can say how often a
    block passes on the first try and which hard constraints fail most.
    That answers whether writing sessions from a schema (row 9 of the
    Prova comparison) is worth building.

Recording is best effort: a failure to write is swallowed, never raised —
the ledger must never break a tool or a validation. Set INFAME_NO_LEDGER=1
to switch it off (the test suite does); INFAME_LEDGER_DIR moves it.

Idea taken from Prova Endurance (decision history).

Version: 1.0 (v7.26)
"""

import json
import os
from collections import Counter
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_DIR = os.path.join(ROOT, "config", "athletes", "ledger")


def _dir(ledger_dir=None):
    return ledger_dir or os.environ.get("INFAME_LEDGER_DIR") or LEDGER_DIR


def _path(athlete_id, ledger_dir=None):
    safe = "".join(c for c in str(athlete_id) if c.isalnum() or c in "-_")
    return os.path.join(_dir(ledger_dir), f"{safe}.jsonl")


def enabled():
    return os.environ.get("INFAME_NO_LEDGER", "") not in ("1", "true", "yes")


def record(athlete_id, event, ledger_dir=None, **fields):
    """Append one event. Returns True when written, False otherwise."""
    if not athlete_id or not enabled():
        return False
    entry = {"at": datetime.now().isoformat(timespec="seconds"), "event": event, **fields}
    try:
        path = _path(athlete_id, ledger_dir)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        return True
    except Exception:  # noqa: BLE001 — never break the caller
        return False


def read(athlete_id, ledger_dir=None):
    """Every event for one athlete, oldest first ([] when none)."""
    path = _path(athlete_id, ledger_dir)
    if not os.path.exists(path):
        return []
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return out


def athletes(ledger_dir=None):
    d = _dir(ledger_dir)
    if not os.path.isdir(d):
        return []
    return sorted(fn[:-6] for fn in os.listdir(d) if fn.endswith(".jsonl"))


def _since(events, days, today=None):
    if days is None:
        return events
    cut = (today or date.today()) - timedelta(days=days)
    keep = []
    for e in events:
        try:
            if datetime.fromisoformat(str(e.get("at"))).date() >= cut:
                keep.append(e)
        except ValueError:
            continue
    return keep


def validation_stats(events):
    """First-try pass rate per block file and the most frequent codes."""
    runs = [e for e in events if e.get("event") == "validation"]
    by_file = {}
    for e in runs:
        by_file.setdefault(e.get("file") or "?", []).append(e)
    first_pass = sum(1 for rs in by_file.values() if rs[0].get("result") == "pass")
    attempts = [next((i + 1 for i, r in enumerate(rs) if r.get("result") == "pass"), None)
                for rs in by_file.values()]
    fails, warns = Counter(), Counter()
    for e in runs:
        fails.update(e.get("fail_codes") or {})
        warns.update(e.get("warn_codes") or {})
    passed = [a for a in attempts if a]
    return {"runs": len(runs), "files": len(by_file),
            "first_try_pass": first_pass,
            "first_try_pass_pct": round(first_pass / len(by_file) * 100) if by_file else None,
            "never_passed": sum(1 for a in attempts if a is None),
            "mean_runs_to_pass": round(sum(passed) / len(passed), 1) if passed else None,
            "fail_codes": dict(fails.most_common(8)),
            "warn_codes": dict(warns.most_common(8))}


def summary(athlete_id, days=30, last=8, ledger_dir=None, today=None):
    """What get_athlete_state and `coach.py ledger` show."""
    events = _since(read(athlete_id, ledger_dir), days, today)
    changes = [e for e in events if e.get("event") != "validation"]
    return {"days": days, "events": len(events),
            "by_event": dict(Counter(e.get("event") for e in events)),
            "validation": validation_stats(events),
            "recent_changes": changes[-last:]}


def _change_line(e):
    ev = e.get("event")
    at = str(e.get("at", ""))[:16].replace("T", " ")
    rest = {k: v for k, v in e.items() if k not in ("at", "event")}
    detail = " · ".join(f"{k}={v}" for k, v in rest.items() if v not in (None, "", [], {}))
    return f"{at}  {ev}" + (f"  {detail}" if detail else "")


def render(athlete_id, s):
    v = s["validation"]
    L = [f"## Ledger — {athlete_id} (last {s['days']} days, {s['events']} events)", ""]
    if v["runs"]:
        L.append(f"Validation: {v['runs']} run(s) on {v['files']} block file(s) · passed on the "
                 f"first try {v['first_try_pass']}/{v['files']} ({v['first_try_pass_pct']}%) · "
                 f"runs to pass {v['mean_runs_to_pass'] or '-'} · never passed {v['never_passed']}")
        if v["fail_codes"]:
            L.append("Most frequent failures: " +
                     ", ".join(f"{k} {n}" for k, n in v["fail_codes"].items()))
        if v["warn_codes"]:
            L.append("Most frequent warnings: " +
                     ", ".join(f"{k} {n}" for k, n in v["warn_codes"].items()))
    else:
        L.append("Validation: no run recorded.")
    L.append("")
    if s["recent_changes"]:
        L.append("Recent changes:")
        L += [f"- {_change_line(e)}" for e in s["recent_changes"]]
    else:
        L.append("Recent changes: none recorded.")
    return "\n".join(L)
