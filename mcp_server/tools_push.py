"""tools_push.py — push_block. The one tool this task's own limits govern.

IMPROVEMENT_BACKLOG.md §6 states the non-negotiable line this file exists
to respect: "Do not let the engine start giving advice... A future feature
that crosses that line — an engine that prescribes rather than reports —
would undo the architecture even if each individual step seemed
reasonable." Uploading to Intervals.icu is the one action in this whole
system with real, hard-to-reverse consequences for the athlete's calendar,
so it gets more resistance than every other tool here, not less:

- `dry_run=True` is the default AND the only mode this function will ever
  run in unless the caller passes BOTH `dry_run=False` AND `confirm=True`
  explicitly, in the same call. One flag flipped by accident is not enough.
- Nothing in this repository calls this function automatically. It is not
  wired into `mcp_server/server.py`'s tool descriptions in any way that
  encourages an LLM to reach for it unprompted, and — per this task's own
  scope — the Claude Project prompt is untouched, so nothing there can
  invoke it either. It exists to be called deliberately, by a human, the
  same as every other manual step it could someday replace.
"""

from __future__ import annotations

import os
from datetime import date

from .common import ROOT, ensure_import_paths, safe_out_dir
from .guard import ToolError, guarded

# Confirmed against config/authors/*.yaml's own `sport:` field — never a
# flat [Discipline] -> Intervals.icu `type` table, per the exact bug fixed
# in archive/RESTORE_POINT_v6.5.md §2 ("[Discipline]: road is genuinely
# ambiguous, not a typo... push_block now resolves the Intervals.icu
# activity type by reading the author's own sport: field"). `road_bike` vs
# `road_run`, `trainer` vs `treadmill`, etc. are already sport-specific
# canonical names in decision_thresholds.yaml's disciplines.canonical, so
# the ambiguity that bug was about doesn't even reach this table — it's
# resolved before the CLI ever calls into this file. Kept anyway as an
# explicit, auditable mapping rather than a guess made once and forgotten.
_DISCIPLINE_TO_TYPE = {
    ("cycling", "road_bike"): "Ride",
    ("cycling", "mtb"): "MountainBikeRide",
    ("cycling", "gravel"): "GravelRide",
    ("cycling", "trainer"): "VirtualRide",
    ("running", "road_run"): "Run",
    ("running", "trail_run"): "TrailRun",
    ("running", "treadmill"): "VirtualRun",
    # No confirming fixture either way for track_run, same honest gap the
    # original restore point flagged for "track" generally — mapped to the
    # plain sport type as the least-wrong default, not verified evidence.
    ("running", "track_run"): "Run",
}


def _activity_type(sport: str, discipline: str) -> tuple[str, bool]:
    """(type, is_inferred). is_inferred marks the one mapping above that
    isn't backed by a confirming fixture, so a dry-run payload can say so
    plainly instead of presenting every entry with equal confidence."""
    key = (sport, str(discipline or "").lower())
    if key in _DISCIPLINE_TO_TYPE:
        return _DISCIPLINE_TO_TYPE[key], key == ("running", "track_run")
    fallback = "Ride" if sport == "cycling" else "Run"
    return fallback, True


@guarded
def push_block(
    athlete_id: str,
    file_path: str | None = None,
    dry_run: bool = True,
    confirm: bool = False,
    athlete_name: str | None = None,
) -> dict:
    """Build the Intervals.icu bulk-events payload for a saved block and,
    only when explicitly told twice (dry_run=False AND confirm=True), POST
    it to `/athlete/{id}/events/bulk?upsert=true` — the same endpoint and
    upsert semantics IMPROVEMENT_BACKLOG.md §5 describes. Every session's
    `external_id` is deterministic (athlete + date + week), so re-pushing a
    corrected block updates the same events instead of duplicating them.

    Every call not opening both gates returns the constructed payload and
    `sent: False` without making any network request at all — this is the
    default, and it is exercised by every automated test in this package;
    the live-send path is exercised only by a mocked `requests.Session.post`,
    the same way the original tool's live path was verified (and, per
    archive/RESTORE_POINT_v6.5.md §5, never actually exercised against a
    real account even once)."""
    ensure_import_paths()
    import validate_block as vb

    if not file_path:
        out_dir = safe_out_dir(athlete_id, athlete_name)
        file_path = os.path.join(out_dir, "blocks", f"{date.today().isoformat()}_bloque.md")
        if not os.path.exists(file_path):
            raise ToolError(
                f"No block saved today for '{athlete_id}' — call save_block "
                f"first, or pass file_path explicitly."
            )
    else:
        # Same class of bug fixed in tools_validate.py's validate_block:
        # a caller-supplied relative file_path must never be resolved
        # against the current process's working directory, which is not
        # reliable at server runtime (confirmed on Windows via Claude
        # Desktop — see tools_validate.py's comment for the full story).
        if not os.path.isabs(file_path):
            file_path = os.path.join(ROOT, file_path)
        if not os.path.exists(file_path):
            raise ToolError(f"File not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        raw_text = f.read()
    text, _fixes = vb.normalize_block(raw_text)
    sessions = vb.split_sessions(text)

    events, skipped = [], []
    for header, code in sessions:
        if not header:
            skipped.append({"reason": "no session header found", "header": header})
            continue
        category = header.get("Category", "Training")
        if category in ("Rest", "Travel") and not code.strip():
            continue
        methodology = header.get("Methodology")
        discipline = header.get("Discipline")
        date_str = header.get("Date")
        if not date_str:
            skipped.append({"reason": "missing [Date]", "header": header})
            continue
        if not methodology or not discipline:
            skipped.append({"reason": "missing [Methodology] or [Discipline]", "header": header})
            continue
        try:
            author, _th, _tssc = vb.load_config(methodology.strip().lower())
        except SystemExit as exc:
            skipped.append({"reason": f"unknown methodology: {exc}", "header": header})
            continue
        activity_type, inferred = _activity_type(author.get("sport"), discipline)
        events.append({
            "start_date_local": f"{date_str}T00:00:00",
            "category": "WORKOUT" if category == "Training" else category.upper(),
            "type": activity_type,
            "type_inferred": inferred,
            "name": header.get("Focus") or f"{author['name']} session",
            "description": code.strip(),
            "external_id": f"infame-{athlete_id}-{date_str}-w{header.get('Week', '')}",
        })

    if not events:
        raise ToolError(
            "No pushable sessions found in this block — nothing was "
            f"constructed. Skipped: {skipped}" if skipped else
            "No pushable sessions found in this block."
        )

    payload = {"events": events, "skipped": skipped, "count": len(events)}

    if not (dry_run is False and confirm is True):
        return {
            "ok": True,
            "dry_run": True,
            "sent": False,
            **payload,
            "note": (
                "dry_run (default, and the only mode this tool runs in unless "
                "both dry_run=False and confirm=True are passed explicitly in "
                "the same call). No request was sent to Intervals.icu."
            ),
        }

    import fetch_athlete_data as fad

    # `type_inferred` is annotation for a human reading the dry-run payload
    # — never part of the actual wire request. Intervals.icu's tolerance
    # for unrecognized fields is unverified (this path itself is
    # unexercised, per this module's own docstring), so it's stripped
    # rather than trusted to be ignored.
    wire_events = [{k: v for k, v in e.items() if k != "type_inferred"} for e in events]

    fad.SESSION = fad.make_session()
    url = f"{fad.BASE_URL}/athlete/{athlete_id}/events/bulk"
    resp = fad.SESSION.post(url, params={"upsert": "true"}, json=wire_events, timeout=45)
    resp.raise_for_status()
    return {
        "ok": True,
        "dry_run": False,
        "sent": True,
        "status_code": resp.status_code,
        **payload,
    }
