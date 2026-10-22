"""tools_push.py — push_block. The one tool this task's own limits govern.

ROADMAP.md ("Lines not to cross") states the line this file exists to
respect, in the words of the original backlog: "Do not let the engine start giving advice... A future feature
that crosses that line — an engine that prescribes rather than reports —
would undo the architecture even if each individual step seemed
reasonable." Uploading to Intervals.icu is the one action in this whole
system with real, hard-to-reverse consequences for the athlete's calendar,
so it gets more resistance than every other tool here, not less:

- `dry_run=True` is the default AND the only mode this function will ever
  run in unless the caller passes BOTH `dry_run=False` AND `confirm=True`
  explicitly, in the same call. One flag flipped by accident is not enough.
- Nothing in this repository calls this function automatically. The coach
  calls it only through the prompt's upload gate: a dry run, the head
  coach's explicit approval, then the live call with both flags.
- Before actually sending (both gates open), this function runs the exact
  same check `validate_block` runs and refuses to send a block that check
  reports as BLOCKED. This was NOT true of the original two-command CLI
  workflow's "separateness," and that gap was found and closed here: when
  validating and uploading were two separate manual commands, a human
  seeing "BLOCKED" simply wouldn't go on to run the next one. Once both
  live one tool call apart in the same conversation, that protective
  friction is gone — nothing before this fix stopped `push_block` from
  being called on a block `validate_block` had just reported BLOCKED, in
  the same turn. This is a deterministic-fact check (the same category as
  validate_block's own HC-METRIC-style rules), not the engine giving
  advice, so it does not cross the line above. `override_validation=True`
  exists for the rare legitimate case of pushing anyway — always a
  conscious, visible choice in the call, never an accident.
"""

from __future__ import annotations

import os
import re
from datetime import date

from .common import (ROOT, ensure_import_paths, ledger_record, safe_out_dir, latest_block_path,
                     mark_cache_stale)
from .guard import ToolError, guarded
from .tools_validate import _run_validation

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
# Indoor rule (Oct 2026): an indoor session is NEVER uploaded as VirtualRide /
# VirtualRun, because Intervals.icu then applies the outdoor FTP. It goes up as
# Ride / Run with the indoor box checked (`indoor: true` in the payload), which
# makes Intervals.icu use the Indoor FTP. Which disciplines are indoor is read
# from config/decision_thresholds.yaml (`disciplines.canonical.<name>.indoor`).
_DISCIPLINE_TO_TYPE = {
    ("cycling", "road_bike"): "Ride",
    ("cycling", "mtb"): "MountainBikeRide",
    ("cycling", "gravel"): "GravelRide",
    ("cycling", "trainer"): "Ride",         # indoor: sent with indoor=true
    ("running", "road_run"): "Run",
    ("running", "trail_run"): "TrailRun",
    ("running", "treadmill"): "Run",        # indoor: sent with indoor=true
    # No confirming fixture either way for track_run, same honest gap the
    # original restore point flagged for "track" generally — mapped to the
    # plain sport type as the least-wrong default, not verified evidence.
    ("running", "track_run"): "Run",
}



def _iso_date(date_str: str) -> str | None:
    """Session headers carry [Date] as DD-MM-YYYY (the prompt's output
    contract); Intervals.icu's start_date_local needs YYYY-MM-DD. Sending
    the header string as-is is what made the first real push (21-sep-2026,
    a real athlete) fail with HTTP 500. Accepts either form; returns None
    for anything else so the session is skipped with a reason, never sent
    with a date Intervals.icu would reject or misread."""
    from datetime import datetime as _dt

    raw = str(date_str or "").strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return _dt.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None

def _week_tag(week) -> str:
    """The week as it goes into external_id: two digits for a number ("3" and
    "03" both give "03", the template's own form), so re-pushing a corrected
    week updates the same events instead of creating a second copy (v7.29)."""
    raw = str(week or "").strip()
    return f"{int(raw):02d}" if raw.isdigit() else raw


_NOTE_LABELS = {
    "es": ("Por qué", "Ejecución", "Nutrición e hidratación"),
    "en": ("Why", "Execution", "Nutrition & hydration"),
}
_EMPTY_NOTE = {"", "pending", "-", "—", "n/a", "none", "ninguno", "ninguna"}


def _athlete_language(athlete_id: str) -> str:
    """The athlete's `language` from the declared profile (es | en); Spanish
    when the profile cannot be read, since the head coach's athletes are
    Mexican. Reads the same file `profile.md` is built from."""
    try:
        import yaml
        path = os.path.join(ROOT, "config", "athletes", f"{athlete_id}.yaml")
        with open(path, encoding="utf-8") as f:
            lang = str((yaml.safe_load(f) or {}).get("language") or "es").lower()
    except Exception:  # noqa: BLE001 — missing or unreadable profile: default
        return "es"
    return "en" if lang.startswith("en") else "es"


def _note_line(text: str) -> str:
    """One plain paragraph the workout builder cannot mistake for syntax:
    never starts with '-', never ends in a repeat marker like `6x`."""
    t = " ".join(str(text or "").split())
    t = t.lstrip("-–—• ").strip()
    if re.search(r"\d+\s*[xX]$", t):
        t += "."
    return t


def _description(header: dict, code: str, language: str, include_notes: bool) -> str:
    """What the athlete sees in Intervals.icu: the Why, Execution and
    Nutrition notes from the session card, a blank line, then the workout
    steps. Until v7.9 only the steps were sent, so the nutrition and hydration
    guidance (and the how-to-execute text) never left the card. [Why] joined
    in v7.20. [Zone] and [Source] are for the head coach and never uploaded."""
    steps = code.strip()
    if not include_notes:
        return steps
    why_label, ex_label, nu_label = _NOTE_LABELS.get(language, _NOTE_LABELS["es"])
    lines = []
    for label, key in ((why_label, "Why"), (ex_label, "Execution"), (nu_label, "Nutrition")):
        val = _note_line(header.get(key, ""))
        if val.lower() not in _EMPTY_NOTE:
            lines.append(f"{label}: {val}")
    return ("\n".join(lines) + "\n\n" + steps) if lines else steps


def _activity_type(sport: str, discipline: str, th: dict | None = None) -> tuple[str, bool, bool]:
    """(type, is_inferred, indoor). is_inferred marks a mapping that isn't
    backed by a confirming fixture, so a dry-run payload can say so plainly.
    The discipline is resolved through the same aliases the validator uses
    ('rodillo' -> trainer, 'caminadora' -> treadmill), so an informal name
    still gets the right type AND the indoor box. `indoor` comes from the
    discipline's `indoor` flag in config/decision_thresholds.yaml."""
    raw = str(discipline or "").strip().lower()
    canonical = raw
    flags: dict = {}
    if th:
        try:
            import validate_block as vb
            name, _alias, err = vb.resolve_discipline(raw, sport, th)
            if name and not err:
                canonical = name
            flags = (((th.get("disciplines") or {}).get("canonical") or {}).get(canonical)) or {}
        except Exception:  # noqa: BLE001 — fall back to the raw name
            flags = {}
    indoor = bool(flags.get("indoor"))
    key = (sport, canonical)
    if key in _DISCIPLINE_TO_TYPE:
        return _DISCIPLINE_TO_TYPE[key], key == ("running", "track_run"), indoor
    fallback = "Ride" if sport == "cycling" else "Run"
    return fallback, True, indoor


# Fields that annotate an event for the head coach and are never sent.
_LOCAL_ONLY = {"type_inferred", "infame_load", "load_method"}


# ══════════════════════════════════════════════════════════════════
# TAGS (v7.46, declared values since v7.47)
# Every uploaded session carries tags: infame, method:<author>,
# class:<class>, arch:<architecture>, week:<NN>. The class is the purpose
# declared in [Zone] and the architecture the one declared in [Architecture]:
# what the coach decided, never a reading of the steps. They are read back by
# engine/architecture.py, so RECENT ARCHITECTURES, the core-session check and
# the cross-week monotony check work from what was decided. A value the card
# does not declare is left out, never guessed; tagging never stops an upload.
# Idea taken from Montis.icu (v5.4.121, Oct 2026: template tags on workouts).
# ══════════════════════════════════════════════════════════════════


def _tag_value(text) -> str:
    """One tag value: lowercase, no accents, no spaces."""
    import shared as _shared
    t = _shared.strip_accents(str(text or "").strip().lower())
    return re.sub(r"\s+", "_", t)


def _session_tags(header: dict) -> list:
    """The tags of one session, from its card: infame, method:, class: (from
    [Zone]), arch: (from [Architecture]), week:."""
    import architecture
    import validate_block as vb
    tags = [architecture.OWN_TAG]
    method = _tag_value(header.get("Methodology"))
    if method:
        tags.append(f"method:{method}")
    cls = vb.declared_class(header)
    if cls:
        tags.append(f"class:{cls}")
    arch = architecture.parse_declared(header.get("Architecture"))
    if arch:
        tags.append(f"arch:{arch}")
    week = _week_tag(header.get("Week"))
    if week:
        tags.append(f"week:{_tag_value(week)}")
    return tags


def _is_own_tag(tag) -> bool:
    import architecture
    t = str(tag or "").strip().lower()
    return t == architecture.OWN_TAG or t.startswith(architecture.OWN_TAG_PREFIXES)


def _keep_coach_tags(athlete_id: str, events: list, fad) -> dict:
    """Before a live send, read the events already on the calendar for those
    dates and keep, on each event being re-pushed, the tags the head coach
    added by hand. This system's own tags are replaced (a corrected session
    may have changed class or architecture). Never raises: if the calendar
    cannot be read, the events go up with this system's tags only, and the
    result says so."""
    result = {"events_with_kept_tags": 0}
    try:
        dates = sorted(e["start_date_local"][:10] for e in events)
        url = f"{fad.BASE_URL}/athlete/{athlete_id}/events"
        got = fad.SESSION.get(url, params={"oldest": dates[0], "newest": dates[-1]},
                              timeout=45)
        got.raise_for_status()
        existing = {e.get("external_id"): e.get("tags") or []
                    for e in got.json() or []
                    if isinstance(e, dict) and e.get("external_id")}
        for e in events:
            kept = [t for t in existing.get(e["external_id"], [])
                    if isinstance(t, str) and t.strip() and not _is_own_tag(t)]
            if kept:
                e["tags"] = e.get("tags", []) + [t for t in kept if t not in e.get("tags", [])]
                result["events_with_kept_tags"] += 1
    except Exception as exc:  # noqa: BLE001 — upload with our tags only
        result["error"] = f"existing tags could not be read; sent this system's tags only: {exc}"
    return result


def _intervals_load(event: dict):
    """The planned load Intervals.icu computed for an event, or None."""
    for key in ("icu_training_load", "training_load"):
        v = event.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return None


def _check_uploaded_loads(athlete_id: str, events: list, resp, fad) -> dict:
    """After a live send, compare the load this system computed for each
    session with the load Intervals.icu computed for the event it created
    (v7.38). The bulk response is read first; when it does not carry the
    loads, the events of those dates are read back once. Reports only —
    never undoes the upload — and never raises: a check that cannot run says
    why. Differences beyond tss_rules.upload_check_tolerance_tss are listed
    and written to the athlete's ledger."""
    try:
        import validate_block as vb
        th = vb.load_thresholds_only()
        tol = float((th.get("tss_rules") or {}).get("upload_check_tolerance_tss", 2))
    except Exception:  # noqa: BLE001
        tol = 2.0
    result = {"tolerance_tss": tol, "checked": 0, "within_tolerance": 0,
              "mismatches": [], "not_available": []}
    try:
        by_id = {}
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001 — no JSON body
            body = None
        for e in body if isinstance(body, list) else []:
            if isinstance(e, dict) and e.get("external_id"):
                by_id[e["external_id"]] = _intervals_load(e)
        missing = [e for e in events if by_id.get(e["external_id"]) is None]
        if missing:
            dates = sorted(e["start_date_local"][:10] for e in missing)
            url = f"{fad.BASE_URL}/athlete/{athlete_id}/events"
            got = fad.SESSION.get(url, params={"oldest": dates[0], "newest": dates[-1]},
                                  timeout=45)
            got.raise_for_status()
            for e in got.json() or []:
                if isinstance(e, dict) and e.get("external_id") in {m["external_id"] for m in missing}:
                    by_id[e["external_id"]] = _intervals_load(e)
        for e in events:
            ours, theirs = e.get("infame_load"), by_id.get(e["external_id"])
            if ours is None or theirs is None:
                result["not_available"].append(e["external_id"])
                continue
            result["checked"] += 1
            diff = round(theirs - float(ours), 1)
            if abs(diff) > tol:
                result["mismatches"].append({
                    "date": e["start_date_local"][:10], "name": e.get("name"),
                    "external_id": e["external_id"], "infame_load": ours,
                    "intervals_load": theirs, "difference": diff,
                    "method": e.get("load_method")})
            else:
                result["within_tolerance"] += 1
    except Exception as exc:  # noqa: BLE001 — the upload already happened
        result["error"] = f"load check could not run: {exc}"
    if result["mismatches"]:
        ledger_record(athlete_id, "upload_load_mismatch",
                      sessions=[{k: m[k] for k in ("date", "infame_load",
                                                   "intervals_load", "method")}
                                for m in result["mismatches"]])
    return result


def _check_uploaded_indoor(athlete_id: str, events: list, resp, fad) -> dict:
    """After a live send, confirm Intervals.icu kept the `indoor` box of each
    event as sent (v7.44). Without it Intervals.icu applies the outdoor FTP to
    an indoor session. The bulk response is read first; when it does not carry
    the field, the events of those dates are read back once. Reports only —
    never undoes the upload — and never raises: a check that cannot run says
    why. Events that did not keep the box are listed and written to the ledger."""
    result = {"checked": 0, "confirmed": 0, "not_confirmed": [], "not_available": []}
    try:
        want = {e["external_id"]: bool(e.get("indoor")) for e in events}
        got: dict = {}
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001 — no JSON body
            body = None
        for e in body if isinstance(body, list) else []:
            if isinstance(e, dict) and e.get("external_id") in want and "indoor" in e:
                got[e["external_id"]] = bool(e.get("indoor"))
        missing = [x for x in want if x not in got]
        if missing:
            dates = sorted(e["start_date_local"][:10] for e in events
                           if e["external_id"] in missing)
            url = f"{fad.BASE_URL}/athlete/{athlete_id}/events"
            back = fad.SESSION.get(url, params={"oldest": dates[0], "newest": dates[-1]},
                                   timeout=45)
            back.raise_for_status()
            for e in back.json() or []:
                if isinstance(e, dict) and e.get("external_id") in missing:
                    got[e["external_id"]] = bool(e.get("indoor"))
        for e in events:
            sent, kept = want[e["external_id"]], got.get(e["external_id"])
            if kept is None:
                result["not_available"].append(e["external_id"])
                continue
            result["checked"] += 1
            if kept == sent:
                result["confirmed"] += 1
            else:
                result["not_confirmed"].append({
                    "date": e["start_date_local"][:10], "name": e.get("name"),
                    "external_id": e["external_id"], "sent_indoor": sent,
                    "intervals_indoor": kept, "type": e.get("type")})
    except Exception as exc:  # noqa: BLE001 — the upload already happened
        result["error"] = f"indoor check could not run: {exc}"
    if result["not_confirmed"]:
        ledger_record(athlete_id, "upload_indoor_mismatch",
                      sessions=[{k: m[k] for k in ("date", "sent_indoor", "intervals_indoor")}
                                for m in result["not_confirmed"]])
    return result


# Maintainer notes (the docstring below is the description the model reads):
# Build the Intervals.icu bulk-events payload for a saved block and,
# only when explicitly told twice (dry_run=False AND confirm=True), POST
# it to `/athlete/{id}/events/bulk?upsert=true` — the same endpoint and
# upsert semantics the original backlog (git history) described. Every session's
# `external_id` is deterministic (athlete + date + week, plus -2, -3 for a
# second or third session on the same date), so re-pushing a corrected
# block updates the same events instead of duplicating them — and two
# sessions on one day never overwrite each other.
#
# Every call not opening both gates returns the constructed payload and
# `sent: False` without making any network request at all — this is the
# default. The test suite exercises the live-send path only against a
# mocked `requests.Session`; it has run against the real Intervals.icu
# account since 21 September 2026.
#
# Before that live send, this tool runs the same check `validate_block`
# runs against `file_path` and raises `ToolError` — sending nothing — if
# the block is BLOCKED (a real hard-constraint failure, not a warning).
# Pass `override_validation=True` to skip that check and push anyway; the
# dry-run path never validates, since it never sends anything either
# way.
@guarded
def push_block(
    athlete_id: str,
    file_path: str | None = None,
    dry_run: bool = True,
    confirm: bool = False,
    athlete_name: str | None = None,
    override_validation: bool = False,
    include_notes: bool = True,
) -> dict:
    """Upload a validated week to the athlete's Intervals.icu calendar. The default is
    a dry run: it returns the events it would create and anything skipped, and sends
    nothing. It sends only with dry_run=false AND confirm=true, after the head coach
    approved; it validates again first and refuses a BLOCKED file
    (override_validation=true only when the head coach explicitly asks). It refuses
    a file with cards for another athlete. Re-pushing a corrected week updates the
    same events. Race days are skipped; workouts already planned on those dates are
    not removed. include_notes=false sends only the steps. Each session carries tags
    (infame, method:, class:, arch:, week:) so it can be grouped in Intervals.icu;
    tags the head coach added there by hand are kept. After a live send,
    `load_check` compares each session's load with the one Intervals.icu computed
    and lists any difference beyond the tolerance: tell the head coach. A live send
    marks the local data stale, so the next get_athlete_state re-reads the calendar,
    and records each session's load in the ledger."""
    ensure_import_paths()
    import validate_block as vb
    import shared as _shared

    if not file_path:
        file_path = latest_block_path(athlete_id, athlete_name)
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

    # A card written for another athlete is never uploaded here (v7.29). The
    # validator checks the same thing (HC-ATHLETE); this refusal also covers the
    # dry run, which does not validate.
    wanted = str(athlete_id).strip()
    others = sorted({str(h.get("Athlete ID")).strip() for h, _ in sessions
                     if h and str(h.get("Athlete ID") or "").strip()
                     and str(h.get("Athlete ID")).strip() != wanted})
    if others:
        raise ToolError(
            f"Refusing: this file has sessions for athlete(s) {', '.join(others)}, "
            f"not '{wanted}'. Nothing was built or sent. Check the [Athlete ID] of each "
            f"card, or the file path.")

    language = _athlete_language(athlete_id)
    events, skipped = [], []
    same_day: dict[str, int] = {}
    for header, code in sessions:
        if not header:
            skipped.append({"reason": "no session header found", "header": header})
            continue
        category = header.get("Category", "Training")
        if category in ("Rest", "Travel") and not code.strip():
            continue
        if category == "Race":
            # The race itself already lives in Intervals.icu as a RACE_A/B/C
            # event (it is how the goal reached #STATE in the first place);
            # "RACE" is not a valid Intervals.icu category, and pushing the
            # race-day card as a WORKOUT would put a second event on the
            # race date. Reported, never silently dropped.
            skipped.append({"reason": "race day: the race event is managed in Intervals.icu",
                            "header": header})
            continue
        methodology = header.get("Methodology")
        discipline = header.get("Discipline")
        date_str = header.get("Date")
        if not date_str:
            skipped.append({"reason": "missing [Date]", "header": header})
            continue
        iso = _iso_date(date_str)
        if not iso:
            skipped.append({"reason": f"unreadable [Date] '{date_str}' (expected DD-MM-YYYY)",
                            "header": header})
            continue
        if not methodology or not discipline:
            skipped.append({"reason": "missing [Methodology] or [Discipline]", "header": header})
            continue
        try:
            author, th, tssc = vb.load_config(methodology.strip().lower())
        except Exception as exc:  # noqa: BLE001 — EngineError: unknown methodology
            skipped.append({"reason": f"unknown methodology: {exc}", "header": header})
            continue
        activity_type, inferred, indoor = _activity_type(author.get("sport"), discipline, th)
        # One external_id per SESSION, not per date: a double day (AM run +
        # PM bike, or a strength session) used to get the same id twice, and
        # upsert=true silently kept only the last one. The first session of
        # a date keeps the original id (so events already pushed still match
        # on re-push); later sessions on that date get -2, -3, ...
        base_id = f"infame-{athlete_id}-{iso}-w{_week_tag(header.get('Week'))}"
        same_day[base_id] = same_day.get(base_id, 0) + 1
        external_id = base_id if same_day[base_id] == 1 else f"{base_id}-{same_day[base_id]}"
        # The load this system computed for the session (v7.38), kept beside
        # the event so the live send can compare it with the load
        # Intervals.icu computes. Never part of the wire payload.
        steps, _ = vb.parse_block(code)
        try:
            infame_load, _d, _s = vb.compute_tss(steps, author, th, tssc, athlete_id)
            load_method = vb.compute_tss.last_method
        except Exception:  # noqa: BLE001 — a load we cannot compute is not checked
            infame_load, load_method = None, None
        events.append({
            "start_date_local": f"{iso}T00:00:00",
            "category": "WORKOUT",
            "type": activity_type,
            # Always sent, true or false, so a corrected re-push also fixes an
            # event that was uploaded the other way (v7.44).
            "indoor": indoor,
            "type_inferred": inferred,
            # v7.35: no accents in anything the athlete's calendar receives.
            "name": _shared.strip_accents(header.get("Focus") or f"{author['name']} session"),
            "description": _shared.strip_accents(
                _description(header, code, language, include_notes)),
            "external_id": external_id,
            "tags": _session_tags(header),
            "infame_load": infame_load,
            "load_method": load_method,
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

    if not override_validation:
        validation = _run_validation(athlete_id=athlete_id, file_path=file_path, quiet=True)
        if not validation.get("passed", False):
            raise ToolError(
                "Refusing to push — validate_block reports this file is "
                f"BLOCKED (exit_code={validation.get('exit_code')}). Fix the "
                "hard-constraint failure(s) first, or pass "
                "override_validation=True to push anyway (not recommended; "
                "always a deliberate, visible choice, never a default).\n\n"
                + validation.get("report", "")
            )

    import fetch_athlete_data as fad

    fad.SESSION = fad.make_session()
    tag_merge = _keep_coach_tags(athlete_id, events, fad)
    # Annotations for the head coach (_LOCAL_ONLY: type_inferred, our load and
    # its method) never travel in the request.
    wire_events = [{k: v for k, v in e.items() if k not in _LOCAL_ONLY} for e in events]
    url = f"{fad.BASE_URL}/athlete/{athlete_id}/events/bulk"
    resp = fad.SESSION.post(url, params={"upsert": "true"}, json=wire_events, timeout=45)
    resp.raise_for_status()
    load_check = _check_uploaded_loads(athlete_id, events, resp, fad)
    indoor_check = _check_uploaded_indoor(athlete_id, events, resp, fad)
    # The load of what was uploaded lives here, so #SESSION never has to
    # carry it (v7.42): a figure written by hand in Notes went stale on
    # 2026-10-11 when the week was corrected and re-uploaded.
    per_session = [(str(e.get("start_date_local") or "")[:10], e.get("infame_load")) for e in events]
    known = [v for _d, v in per_session if isinstance(v, (int, float))]
    ledger_record(athlete_id, "block_uploaded", file=os.path.basename(str(file_path or "")) or None,
                  sessions=len(events), override_validation=bool(override_validation),
                  dates=sorted({d for d, _v in per_session}),
                  load_tss=round(sum(known)) if known else None,
                  loads=[f"{d} {round(v) if isinstance(v, (int, float)) else '?'}"
                         for d, v in sorted(per_session, key=lambda x: x[0])])
    stale = mark_cache_stale(athlete_id)
    return {
        "ok": True,
        "dry_run": False,
        "sent": True,
        "status_code": resp.status_code,
        **payload,
        "load_check": load_check,
        "indoor_check": indoor_check,
        "tag_merge": tag_merge,
        "cache_marked_stale": stale,
    }
