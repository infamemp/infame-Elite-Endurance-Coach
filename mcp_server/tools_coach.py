"""tools_coach.py — post_activity_comment, update_threshold, remove_block
=========================================================================
The three tools that change the athlete's real Intervals.icu data, apart
from `push_block`. They follow the same gate `push_block` has always had
(see tools_push.py's own docstring for why):

- `dry_run=True` is the default. Nothing is written unless the caller passes
  BOTH `dry_run=False` AND `confirm=True` in the same call.
- Every dry run reads what it needs from Intervals.icu (a read, never a
  write) so it can show exactly what a live call would change: the activity a
  comment would land on, the old value of a threshold next to the new one,
  the sessions a removal would delete.
- A live call re-reads afterwards and reports what Intervals.icu now holds,
  instead of trusting that the write did what was asked.

Nothing here decides anything. The coach writes the comment, the head coach
chooses the threshold and approves each call; these tools only carry it out.
Endpoints and field names are from Intervals.icu's own OpenAPI spec.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta

from .common import DATA, ensure_import_paths
from .guard import ToolError, guarded

MAX_COMMENT_CHARS = 2000

# Thresholds this tool can set, with the range a real value falls in. A value
# outside it is almost certainly a typo or a wrong unit, and is refused.
_INT_FIELDS = {"ftp": (50, 700), "lthr": (80, 230), "max_hr": (100, 230)}
_PACE_MS_RANGE = (1.0, 8.0)          # threshold_pace is stored in m/s
_HR_FIELDS = ("lthr", "max_hr")      # changing these recalculates HR zones


def _gates_open(dry_run: bool, confirm: bool) -> bool:
    return dry_run is False and confirm is True


def _http():
    ensure_import_paths()
    import fetch_athlete_data as fad

    fad.SESSION = fad.make_session()
    return fad


def _check(resp, what: str):
    if resp.status_code >= 400:
        raise ToolError(
            f"Intervals.icu refused {what}: HTTP {resp.status_code} "
            f"{str(getattr(resp, 'text', ''))[:300]}"
        )
    return resp


def _iso(s: str, label: str) -> date:
    try:
        return datetime.strptime(str(s).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        raise ToolError(f"{label} must be YYYY-MM-DD, got '{s}'.") from None


# ══════════════════════════════════════════════════════════════════
# post_activity_comment
# ══════════════════════════════════════════════════════════════════

@guarded
def post_activity_comment(
    athlete_id: str,
    activity_id: str,
    text: str,
    dry_run: bool = True,
    confirm: bool = False,
) -> dict:
    """Post the coach's feedback as a comment on one of the athlete's
    activities (POST /activity/{id}/messages). `activity_id` comes from
    `get_execution` (`activity_id` on each session and extra activity).

    The activity is read first and refused unless it belongs to
    `athlete_id`, so a comment can never land on another athlete's ride. The
    text is posted exactly as given: write it in the athlete's language
    (`language` in the declared profile) before calling."""
    body = str(text or "").strip()
    if not body:
        raise ToolError("The comment is empty — nothing to post.")
    if len(body) > MAX_COMMENT_CHARS:
        raise ToolError(f"The comment is {len(body)} characters; the limit here is "
                        f"{MAX_COMMENT_CHARS}. Shorten it.")
    aid_txt = str(activity_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", aid_txt):
        raise ToolError(f"'{activity_id}' is not an activity id.")

    fad = _http()
    act = _check(fad.SESSION.get(f"{fad.BASE_URL}/activity/{aid_txt}", timeout=45),
                 "reading the activity").json()
    owner = str(act.get("icu_athlete_id") or "")
    if owner != str(athlete_id):
        raise ToolError(
            f"Activity {aid_txt} belongs to athlete '{owner or 'unknown'}', not "
            f"'{athlete_id}'. Nothing was posted."
        )
    target = {"activity_id": aid_txt, "name": act.get("name"),
              "date": str(act.get("start_date_local") or "")[:10],
              "type": act.get("type")}

    if not _gates_open(dry_run, confirm):
        return {"ok": True, "dry_run": True, "sent": False, "activity": target,
                "comment": body,
                "note": "dry_run (default). Nothing was posted; both dry_run=False "
                        "and confirm=True are needed in the same call."}

    resp = _check(fad.SESSION.post(f"{fad.BASE_URL}/activity/{aid_txt}/messages",
                                   json={"content": body}, timeout=45),
                  "posting the comment")
    return {"ok": True, "dry_run": False, "sent": True, "activity": target,
            "comment": body, "status_code": resp.status_code}


# ══════════════════════════════════════════════════════════════════
# update_threshold
# ══════════════════════════════════════════════════════════════════

def _pace_to_ms(value, pace_units: str | None) -> float:
    """A pace string 'M:SS' in the athlete's own pace unit -> m/s, the unit
    Intervals.icu stores threshold_pace in. A plain number is taken as m/s."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    txt = str(value).strip()
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", txt)
    if not m:
        try:
            return float(txt)
        except ValueError:
            raise ToolError(f"Cannot read '{value}' as a pace: use M:SS "
                            f"(in the athlete's pace unit) or a speed in m/s.") from None
    secs = int(m.group(1)) * 60 + int(m.group(2))
    if secs <= 0:
        raise ToolError("A pace of 0:00 is not valid.")
    per_metre = {"MINS_KM": 1000.0, "MINS_MILE": 1609.344}.get(str(pace_units))
    if per_metre is None:
        raise ToolError(
            f"This athlete's pace unit is {pace_units}: give the threshold pace "
            f"as a speed in m/s instead of M:SS."
        )
    return per_metre / secs


def _fmt_pace(ms, pace_units) -> str | None:
    if not ms:
        return None
    per_metre = {"MINS_KM": 1000.0, "MINS_MILE": 1609.344}.get(str(pace_units))
    if not per_metre:
        return f"{ms:.3f} m/s"
    secs = round(per_metre / ms)
    return f"{secs // 60}:{secs % 60:02d}" + (" /km" if pace_units == "MINS_KM" else " /mi")


@guarded
def update_threshold(
    athlete_id: str,
    sport_type: str,
    field: str,
    value,
    dry_run: bool = True,
    confirm: bool = False,
) -> dict:
    """Set one threshold in the athlete's Intervals.icu sport settings after
    a test: `field` is ftp, lthr, max_hr or threshold_pace; `sport_type` is an
    Intervals.icu activity type (Ride, Run, VirtualRide...). Always shows old
    -> new. A threshold pace may be given as 'M:SS' in the athlete's own pace
    unit (min/km or min/mile) or as a speed in m/s.

    The head coach's decision, never the engine's: call it only with a value
    the head coach has confirmed. Changing lthr or max_hr recalculates the HR
    zones, as editing them in Intervals.icu does. After a live change the
    local cache is marked stale, so the next get_athlete_state re-fetches and
    #STATE carries the new threshold."""
    field = str(field or "").strip().lower()
    if field not in (*_INT_FIELDS, "threshold_pace"):
        raise ToolError(f"'{field}' cannot be set here. Allowed: "
                        f"{', '.join((*_INT_FIELDS, 'threshold_pace'))}.")
    sport = str(sport_type or "").strip()
    if not re.fullmatch(r"[A-Za-z]+", sport):
        raise ToolError(f"'{sport_type}' is not an Intervals.icu activity type "
                        f"(e.g. Ride, Run, VirtualRide).")

    fad = _http()
    base = f"{fad.BASE_URL}/athlete/{athlete_id}/sport-settings"
    settings = _check(fad.SESSION.get(f"{base}/{sport}", timeout=45),
                      f"reading the {sport} sport settings").json()
    sid = settings.get("id")
    if sid is None:
        raise ToolError(f"No {sport} sport settings found for '{athlete_id}'.")
    units = settings.get("pace_units")
    old = settings.get(field)

    if field == "threshold_pace":
        new = round(_pace_to_ms(value, units), 4)
        lo, hi = _PACE_MS_RANGE
    else:
        try:
            new = int(round(float(value)))
        except (TypeError, ValueError):
            raise ToolError(f"'{value}' is not a number.") from None
        lo, hi = _INT_FIELDS[field]
    if not lo <= new <= hi:
        raise ToolError(f"{field} = {new} is outside the plausible range "
                        f"{lo}-{hi}. Check the value and its unit. Nothing was changed.")

    def human(v):
        return _fmt_pace(v, units) if field == "threshold_pace" else v

    change = {"sport_type": sport, "settings_id": sid, "types": settings.get("types"),
              "field": field, "old": old, "new": new,
              "old_display": human(old), "new_display": human(new)}
    if field in _HR_FIELDS:
        change["note"] = "HR zones are recalculated from the new value."

    if old is not None and abs(float(old) - float(new)) < 1e-6:
        return {"ok": True, "dry_run": not _gates_open(dry_run, confirm), "sent": False,
                "changed": False, **change,
                "note": "Already set to this value; nothing to change."}

    if not _gates_open(dry_run, confirm):
        return {"ok": True, "dry_run": True, "sent": False, "changed": False, **change,
                "note": "dry_run (default). Nothing was changed; both dry_run=False "
                        "and confirm=True are needed in the same call."}

    resp = _check(
        fad.SESSION.put(f"{base}/{sid}",
                        params={"recalcHrZones": "true" if field in _HR_FIELDS else "false"},
                        json={field: new}, timeout=45),
        f"updating {field}")
    after = _check(fad.SESSION.get(f"{base}/{sport}", timeout=45),
                   "re-reading the sport settings").json().get(field)
    confirmed = after is not None and abs(float(after) - float(new)) < 1e-3

    # The cached athlete_data.json still has the old threshold: mark it stale
    # so the next get_athlete_state re-fetches by itself.
    invalidated = False
    cache = os.path.join(DATA, str(athlete_id), "athlete_data.json")
    if os.path.exists(cache):
        os.utime(cache, (0, 0))
        invalidated = True
    return {"ok": True, "dry_run": False, "sent": True, "changed": confirmed,
            "status_code": resp.status_code, **change,
            "now_in_intervals": after, "now_in_intervals_display": human(after),
            "verified": confirmed, "cache_marked_stale": invalidated,
            "note": None if confirmed else
            "Intervals.icu answered but the re-read does not show the new value — "
            "check the sport settings in Intervals.icu before relying on it."}


# ══════════════════════════════════════════════════════════════════
# remove_block
# ══════════════════════════════════════════════════════════════════

@guarded
def remove_block(
    athlete_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
    dry_run: bool = True,
    confirm: bool = False,
) -> dict:
    """Delete sessions this system uploaded, so a week can be redone.

    Only events whose `external_id` starts with `infame-<athlete_id>-` (the
    id `push_block` gives every session) and whose category is WORKOUT are
    ever touched, and only from tomorrow onward: today and the past are never
    removed, and anything else on the calendar — the athlete's own workouts,
    races, notes — is left alone and only counted. Narrow the range with
    `from_date` / `to_date` (YYYY-MM-DD); by default it covers every uploaded
    session from tomorrow on. After a live delete the calendar is re-read and
    anything that survived is reported."""
    tomorrow = date.today() + timedelta(days=1)
    start = _iso(from_date, "from_date") if from_date else tomorrow
    if start < tomorrow:
        raise ToolError(f"remove_block never removes today or past sessions: "
                        f"from_date must be {tomorrow.isoformat()} or later.")
    end = _iso(to_date, "to_date") if to_date else start + timedelta(days=365)
    if end < start:
        raise ToolError("to_date is before from_date.")

    fad = _http()
    url = f"{fad.BASE_URL}/athlete/{athlete_id}/events"
    prefix = f"infame-{athlete_id}-"

    def _mine():
        evs = _check(fad.SESSION.get(url, params={"oldest": start.isoformat(),
                                                  "newest": end.isoformat()}, timeout=45),
                     "reading the calendar").json() or []
        ours = [e for e in evs
                if str(e.get("external_id") or "").startswith(prefix)
                and e.get("category") == "WORKOUT"
                and str(e.get("start_date_local") or "")[:10] >= tomorrow.isoformat()]
        return evs, ours

    events, ours = _mine()
    rows = [{"id": e.get("id"), "date": str(e.get("start_date_local") or "")[:10],
             "name": e.get("name"), "external_id": e.get("external_id")}
            for e in sorted(ours, key=lambda x: str(x.get("start_date_local")))]
    summary = {"range": {"from": start.isoformat(), "to": end.isoformat()},
               "to_remove": rows, "count": len(rows),
               "left_alone": len(events) - len(ours)}

    if not rows:
        return {"ok": True, "dry_run": not _gates_open(dry_run, confirm), "sent": False,
                **summary, "note": "No sessions uploaded by this system in that range."}
    if not _gates_open(dry_run, confirm):
        return {"ok": True, "dry_run": True, "sent": False, **summary,
                "note": "dry_run (default). Nothing was deleted; both dry_run=False "
                        "and confirm=True are needed in the same call."}

    resp = _check(fad.SESSION.put(f"{url}/bulk-delete",
                                  json=[{"id": r["id"]} for r in rows], timeout=45),
                  "deleting the sessions")
    _, still = _mine()
    left = [e.get("id") for e in still if e.get("id") in {r["id"] for r in rows}]
    return {"ok": True, "dry_run": False, "sent": True, "status_code": resp.status_code,
            **summary, "still_on_calendar": left, "verified": not left,
            "note": None if not left else
            "Some sessions are still on the calendar after the delete — check Intervals.icu."}
