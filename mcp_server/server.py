"""
mcp_server/server.py — Infame Elite Endurance Coach v6.4+, MCP Phase 1
=========================================================================
A local MCP server exposing this project's own engine to Claude Desktop —
not a wrapper around the raw Intervals.icu API. What a tool returns here is
always something the engine already computes deterministically (a resolved
#STATE, a roster), never unresolved data the model would have to interpret
itself. That is the same contract state.md already enforces for the
drag-and-drop workflow; this server gives the same content a conversational
path instead of a file path, without weakening the contract.

Phase 1 — read-only tools, proven working against real data (2026-09-06):
    get_athlete_state(athlete_id, force_refresh=False)
    get_athlete_profile(athlete_id, force_refresh=False)
    list_roster()

Phase 2 remaining (not built yet): validate_block, and the four tools that
write to disk (save_block, save_continuity, save_race_result, push_block).

Transport: stdio only. This process is launched and owned by Claude
Desktop as a local subprocess — it is not a network service, and nothing
here listens on a port. See claude_desktop_config.json for how Desktop
starts it.

Setup:
    pip install "mcp[cli]" pyyaml requests

Run manually, for testing outside Desktop:
    python mcp_server/server.py
"""

import json
import os
import sys
from datetime import date, datetime

import yaml

from mcp.server.fastmcp import FastMCP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, ROOT)                       # for `import coach`
sys.path.insert(0, os.path.join(ROOT, "engine"))  # for fetch_athlete_data, build_state

mcp = FastMCP("infame-coach")


def _cache_minutes():
    """Reads config/decision_thresholds.yaml — mcp.state_cache_minutes.
    Falls back to 60 only if the key is somehow missing, so a config typo
    degrades gracefully instead of crashing every tool call."""
    path = os.path.join(ROOT, "config", "decision_thresholds.yaml")
    try:
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cfg.get("mcp", {}).get("state_cache_minutes", 60)
    except Exception:
        return 60


def _data_age_minutes(athlete_id):
    """Minutes since data/<id>/athlete_data.json was last written, from the
    file's own modification time — not from the fetched_at field inside it,
    which only stores a date with no time-of-day and can't tell 9am from
    11pm. Returns None if the file doesn't exist yet."""
    path = os.path.join(DATA, str(athlete_id), "athlete_data.json")
    if not os.path.exists(path):
        return None
    age_seconds = datetime.now().timestamp() - os.path.getmtime(path)
    return age_seconds / 60


def _guarded(fn, *args):
    """Runs fn inside a redirected stdout (see _ensure_fresh_data's docstring
    for why) and converts any failure — including SystemExit, which a bare
    except Exception does NOT catch and which would otherwise kill this
    entire server process — into a returned error string instead of letting
    it propagate. Returns None on success."""
    import contextlib
    import io

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            fn(*args)
        return None
    except (Exception, SystemExit) as e:
        return str(e) if isinstance(e, SystemExit) else f"{type(e).__name__}: {e}"


def _ensure_fresh_data(athlete_id, force_refresh=False):
    """Pulls fresh data from Intervals.icu when needed, shared by every tool
    that reads from data/<id>/ — get_athlete_state and get_athlete_profile
    both need this, but each renders a different file from the same pull,
    so the fetch itself lives here once rather than twice.

    Returns (freshness_note, error). error is None on success; on failure,
    freshness_note is None and error is a plain string to return to the
    caller instead of raising.

    Critical: fetch_one() prints progress messages unconditionally (the
    same "profile...", "wellness and PMC series..." lines coach.py prep
    shows by hand) — normal for a CLI, fatal here. Over stdio, this
    process's stdout IS the MCP protocol channel back to Desktop; any
    stray print() corrupts that stream and Desktop hangs, then
    disconnects. _guarded() redirects stdout for the duration of the call."""
    age = _data_age_minutes(athlete_id)
    limit = _cache_minutes()

    if not (force_refresh or age is None or age > limit):
        return f"Using data fetched {age:.0f} minute(s) ago.", None

    def _fetch(aid):
        import fetch_athlete_data as fad
        import coach
        fad.SESSION = fad.make_session()
        # fetch_one's `name` argument is only used for its own print
        # statements (captured by _guarded) — the athlete's real name comes
        # from the API response and lands in athlete_data.json regardless.
        fad.fetch_one(aid, aid, 180, DATA)
        try:
            coach.capture_snapshot(aid)
        except Exception:
            pass  # non-blocking here too — see coach.py's own capture_snapshot

    err = _guarded(_fetch, athlete_id)
    if err:
        return None, f"Could not fetch data for '{athlete_id}': {err}"
    return "Just fetched.", None


@mcp.tool()
def get_athlete_state(athlete_id: str, force_refresh: bool = False) -> str:
    """Get an athlete's authoritative #STATE — CTL/ATL/TSB, ACWR, durability,
    longitudinal progression, and any flags — exactly what state.md contains
    today. Reuses data already fetched within the last hour instead of
    re-querying Intervals.icu on every question; pass force_refresh=true
    when the athlete is known to have just synced and a stale reading would
    matter (e.g. right after they mention finishing a session).

    athlete_id: the Intervals.icu id, e.g. "i347129".
    """
    freshness, error = _ensure_fresh_data(athlete_id, force_refresh)
    if error:
        return error

    def _resolve(aid):
        import build_state as bs
        bs.build(aid, bs.load_thresholds(), quiet=True)

    err = _guarded(_resolve, athlete_id)
    if err:
        return f"Could not resolve state for '{athlete_id}': {err}"

    state_path = os.path.join(DATA, str(athlete_id), "state.md")
    if not os.path.exists(state_path):
        return (f"No state.md for '{athlete_id}' after fetching — check the "
                f"id is correct.")
    with open(state_path, encoding="utf-8") as f:
        content = f.read()
    return f"{freshness}\n\n{content}"


@mcp.tool()
def get_athlete_profile(athlete_id: str, force_refresh: bool = False) -> str:
    """Get an athlete's raw context — personal info, sport configuration,
    race calendar, planned sessions, recent activity history — exactly what
    profile.md contains today. Carries no interpreted signal (CTL/ATL/TSB
    etc. live only in get_athlete_state); shares the same hour-long cache
    and force_refresh escape hatch.

    athlete_id: the Intervals.icu id, e.g. "i347129".
    """
    freshness, error = _ensure_fresh_data(athlete_id, force_refresh)
    if error:
        return error

    def _render(aid):
        import build_profile as bp
        bp.build(aid, quiet=True)

    err = _guarded(_render, athlete_id)
    if err:
        return f"Could not render profile for '{athlete_id}': {err}"

    profile_path = os.path.join(DATA, str(athlete_id), "profile.md")
    if not os.path.exists(profile_path):
        return (f"No profile.md for '{athlete_id}' after fetching — check "
                f"the id is correct.")
    with open(profile_path, encoding="utf-8") as f:
        content = f.read()
    return f"{freshness}\n\n{content}"


@mcp.tool()
def list_roster() -> str:
    """List every athlete on the account with their Intervals.icu id and the
    date they were last fetched — the same table coach.py prep --list
    writes to out/roster.md. Read-only: does not contact Intervals.icu or
    refresh anything itself."""
    roster_path = os.path.join(ROOT, "out", "roster.md")
    if not os.path.exists(roster_path):
        return ("No roster found. Run 'python coach.py prep --list' at "
                "least once first.")
    with open(roster_path, encoding="utf-8") as f:
        return f.read()


def _dest_name(athlete_id):
    """out/<name>/ folder for this athlete — the same sanitized name
    coach.py prep already writes to (José → Jose_Martinez, spaces to
    underscores), read from whatever athlete_data.json already exists.
    Falls back to the bare id if there's no data yet, matching prep_one's
    own fallback, so a write tool never fails just because get_athlete_*
    hasn't been called for this athlete in this conversation."""
    import coach
    path = os.path.join(DATA, str(athlete_id), "athlete_data.json")
    name = None
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            name = (data.get("profile") or {}).get("name")
        except Exception:
            pass
    return coach.safe_filename(name) if name else str(athlete_id)


@mcp.tool()
def save_continuity(athlete_id: str, session_text: str) -> str:
    """Save a #SESSION continuity block to out/<athlete_name>/continuity.md,
    replacing whatever was there. This is the same file the coach's
    end-of-block header (Phase 5/6) or an on-demand mid-block header is
    meant to be pasted into by hand today — call this instead of asking the
    athlete's coach to copy anything. Always overwrites: continuity.md is a
    snapshot of where the macrocycle stands right now, not a history.

    athlete_id: the Intervals.icu id, e.g. "i347129".
    session_text: the #SESSION block exactly as generated, header included.
    """
    dest_name = _dest_name(athlete_id)
    out_dir = os.path.join(ROOT, "out", dest_name)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "continuity.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(session_text.strip() + "\n")
    return f"Saved to out/{dest_name}/continuity.md"


@mcp.tool()
def save_race_result(athlete_id: str, race_result_text: str) -> str:
    """Append a #RACE_RESULT block to out/<athlete_name>/race_notes.md —
    never overwrites, since a season can have several races. A future
    review command reads entries here by date, matched against the `Date:`
    field inside the block, so the block's own formatting (Date/Race/
    Result/Vs plan/Context/Retest flagged) must stay intact.

    athlete_id: the Intervals.icu id, e.g. "i347129".
    race_result_text: the #RACE_RESULT block exactly as generated.
    """
    text = race_result_text.strip()
    if not text.startswith("#RACE_RESULT"):
        # Defensive normalization, not a judgment call on content — a block
        # missing its own header would silently fail to parse later, so
        # this just makes sure the header is there rather than rejecting it.
        text = "#RACE_RESULT\n" + text
    dest_name = _dest_name(athlete_id)
    out_dir = os.path.join(ROOT, "out", dest_name)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "race_notes.md")
    with open(path, "a", encoding="utf-8") as f:
        f.write(text + "\n\n")
    return f"Appended to out/{dest_name}/race_notes.md"


@mcp.tool()
def save_block(athlete_id: str, block_text: str) -> str:
    """Save a generated training block to
    out/<athlete_name>/blocks/<date>_bloque.md — the file coach.py check
    validates before anything goes to Intervals.icu. Overwrites the same
    day's file if called again (e.g. after a correction the coach makes
    on request), so the file on disk always matches the latest version
    shown on screen. Never uploads or validates anything itself — those
    stay separate, explicit steps the coach doesn't skip on your behalf.

    athlete_id: the Intervals.icu id, e.g. "i347129".
    block_text: the full block text, Intervals.icu syntax, headers included.
    """
    dest_name = _dest_name(athlete_id)
    blocks_dir = os.path.join(ROOT, "out", dest_name, "blocks")
    os.makedirs(blocks_dir, exist_ok=True)
    fname = f"{date.today().isoformat()}_bloque.md"
    path = os.path.join(blocks_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(block_text.strip() + "\n")
    return f"Saved to out/{dest_name}/blocks/{fname}"


@mcp.tool()
def validate_block(athlete_id: str, fill_tss: bool = True,
                    methodology: str = None, discipline: str = None) -> str:
    """Run the hard-constraint verification gate against the block most
    recently saved for this athlete via save_block — syntax, ramp
    eligibility, prescription floors, dual-layer completeness, and a TSS
    recomputation against the same config the engine uses. Nothing reaches
    Intervals.icu unverified; always call this before push_block.

    Equivalent to coach.py check <file> --fill-tss, run against
    out/<athlete_name>/blocks/<today>_bloque.md — the file save_block just
    wrote. Runs the real validator as a subprocess, exactly like coach.py
    check already does, so none of its logic is duplicated or reinterpreted
    here — and because it's a subprocess, its own print() output is
    naturally isolated from this server's stdout with no extra handling
    needed (unlike the fetch/build calls elsewhere in this file).

    athlete_id: the Intervals.icu id, e.g. "i347129".
    fill_tss: write the computed TSS into the block's headers on PASS
        (default true — matches coach.py check --fill-tss).
    methodology / discipline: override the block header's own fields; only
        needed when the block doesn't declare them.
    """
    dest_name = _dest_name(athlete_id)
    fname = f"{date.today().isoformat()}_bloque.md"
    path = os.path.join(ROOT, "out", dest_name, "blocks", fname)
    if not os.path.exists(path):
        return (f"No block saved for '{athlete_id}' today — call save_block "
                f"first, then validate_block.")

    script = os.path.join(ROOT, "verify", "validate_block.py")
    cmd = [sys.executable, script, path, "--athlete", str(athlete_id)]
    if fill_tss:
        cmd.append("--fill-tss")
    if methodology:
        cmd += ["--methodology", methodology]
    if discipline:
        cmd += ["--discipline", discipline]

    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True)
    verdict = "PASS" if result.returncode == 0 else "BLOCKED"
    return f"{verdict}\n\n{result.stdout}{result.stderr}"


CYCLING_DISCIPLINE_TO_TYPE = {
    "trainer": "VirtualRide",
    "road": "Ride",
    "mtb": "MountainBikeRide",
    "gravel": "GravelRide",
    "track": "TrackRide",
}
RUNNING_DISCIPLINE_TO_TYPE = {
    "run": "Run",
    "road": "Run",
    "trail": "TrailRun",
    "treadmill": "VirtualRun",
    # No distinct "track run" type exists in Intervals.icu's activity list —
    # a track running session is logged as a plain Run. Unlike every other
    # entry in this table, this one has no confirming fixture (no
    # tests/blocks/*.md uses a running methodology with [Discipline]: track)
    # — it follows the same road/trail/treadmill pattern by inference, not
    # by direct evidence the way road -> Run is now confirmed twice over
    # (vianey_bloque1.md, vianey_raw_unfixed.md, both daniels + road).
    "track": "Run",
}


def _author_sport(methodology):
    """cycling vs running, read from config/authors/<methodology>.yaml's own
    `sport:` field. Never hardcoded as a separate list here — building a
    second, disconnected list of "which methodologies are cycling" is
    exactly what produced the road/track ambiguity bug in the first place:
    [Discipline] alone doesn't disambiguate a shared token like "road"
    (confirmed real in both cycling and running fixtures) — the athlete's
    active methodology does, and only the author's own file is the source
    of truth for that."""
    path = os.path.join(ROOT, "config", "authors", f"{methodology.strip().lower()}.yaml")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return (cfg or {}).get("sport")


def _resolve_activity_type(methodology, discipline):
    """Returns (intervals_type, error). error is None on success."""
    if not methodology:
        return None, "no [Methodology] on this session — cannot resolve sport"
    sport = _author_sport(methodology)
    table = {"running": RUNNING_DISCIPLINE_TO_TYPE,
             "cycling": CYCLING_DISCIPLINE_TO_TYPE}.get(sport)
    if table is None:
        return None, (f"methodology '{methodology}' has no "
                      f"config/authors/{methodology.lower()}.yaml, or its "
                      f"sport field is neither cycling nor running")
    itype = table.get(discipline)
    if not itype:
        return None, f"[Discipline] '{discipline}' has no mapping for sport '{sport}'"
    return itype, None


def _strip_narrative_notes(code):
    """Removes "quoted narrative notes" from a session's step lines before
    it goes to Intervals.icu — per Michel's decision, only at the point of
    upload, never from the source the coach generates or save_block keeps.
    Not a judgment that the notes are wrong; the syntax reference has no
    documented behavior for them, and pushing something unconfirmed to a
    real athlete's calendar is not a risk worth taking to save a question."""
    import re
    cleaned = re.sub(r'"[^"]*"', "", code)
    # Collapse the trailing whitespace the removal leaves on each line,
    # without collapsing the blank lines the syntax itself requires around
    # repeat blocks (section 6 of the syntax reference).
    return "\n".join(line.rstrip() for line in cleaned.splitlines())


def _parse_header_date(date_str):
    """Session headers use DD-MM-YYYY (see good_trainer_coggan.md,
    vianey_bloque1.md) — not ISO. Returns a date object."""
    from datetime import datetime as dt
    return dt.strptime(date_str.strip(), "%d-%m-%Y").date()


def _parse_duration_seconds(duration_str):
    """[Duration] is HH:MM:SS. Returns None if missing/unparseable rather
    than guessing — moving_time is optional on the API side."""
    if not duration_str:
        return None
    try:
        h, m, s = (int(x) for x in duration_str.strip().split(":"))
        return h * 3600 + m * 60 + s
    except (ValueError, AttributeError):
        return None


def _parse_tss(tss_str):
    """[Estimated TSS] is either a number or "pending"/"tbd" — matches the
    same convention validate_block.py already reads. None means don't send
    icu_training_load at all, not zero."""
    if not tss_str:
        return None
    s = tss_str.strip().lower()
    if s in ("pending", "tbd", "", "—", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


@mcp.tool()
def push_block(athlete_id: str, dry_run: bool = True) -> str:
    """Upload the block most recently saved for this athlete (via
    save_block, and only after it has passed validate_block) to
    Intervals.icu's calendar, via POST /events/bulk?upsert=true. Each
    session gets a deterministic external_id
    (infame-<athlete_id>-<date>[-<n>]), so pushing a corrected block later
    updates the same calendar entries instead of duplicating them.

    Narrative notes in quotes ("Trote suave...") are stripped from the
    description sent to Intervals.icu — the syntax reference has no
    documented behavior for them, so they're removed only at this last
    step, never from the saved file itself. Rest/Travel days are skipped;
    nothing is created for them.

    dry_run (default true): builds and returns exactly what would be sent,
    without calling the API. Nothing reaches Intervals.icu until this is
    explicitly set to false — this is the only tool in this server that
    writes to Intervals.icu rather than to a local file, and it has never
    been exercised against the real API from this side, so the first real
    use should be a look, not a leap.

    athlete_id: the Intervals.icu id, e.g. "i347129".
    """
    import re

    dest_name = _dest_name(athlete_id)
    fname = f"{date.today().isoformat()}_bloque.md"
    path = os.path.join(ROOT, "out", dest_name, "blocks", fname)
    if not os.path.exists(path):
        return (f"No block saved for '{athlete_id}' today — call save_block "
                f"and validate_block first.")

    with open(path, encoding="utf-8") as f:
        text = f.read()

    import validate_block as vb  # reuses the real parser, never reimplemented
    sessions = vb.split_sessions(text)

    events = []
    skipped = []
    date_counts = {}
    for header, code in sessions:
        category = header.get("Category", "Training")
        if category in ("Rest", "Travel"):
            skipped.append(f"{header.get('Date', '?')}: {category} day, nothing to push")
            continue

        discipline = (header.get("Discipline") or "").strip().lower()
        itype, err = _resolve_activity_type(header.get("Methodology"), discipline)
        if err:
            skipped.append(f"{header.get('Date', '?')}: {err} — skipped")
            continue

        try:
            d = _parse_header_date(header.get("Date", ""))
        except ValueError:
            skipped.append(f"(unparseable date) {header.get('Date', '?')}: skipped")
            continue

        iso = d.isoformat()
        date_counts[iso] = date_counts.get(iso, 0) + 1
        ext_id = f"infame-{athlete_id}-{iso}"
        if date_counts[iso] > 1:
            ext_id += f"-{date_counts[iso]}"

        event = {
            "category": "WORKOUT",
            "external_id": ext_id,
            "start_date_local": f"{iso}T05:00:00",
            "type": itype,
            "name": header.get("Focus") or f"{discipline.title()} session",
            "description": _strip_narrative_notes(code).strip(),
        }
        moving_time = _parse_duration_seconds(header.get("Duration"))
        if moving_time:
            event["moving_time"] = moving_time
        tss = _parse_tss(header.get("Estimated TSS"))
        if tss is not None:
            event["icu_training_load"] = tss

        events.append(event)

    if not events:
        msg = ["Nothing to push — every session was skipped:", ""]
        msg += [f"- {s}" for s in skipped] if skipped else ["(no sessions found in the file)"]
        return "\n".join(msg)

    if dry_run:
        L = [f"DRY RUN — nothing was sent to Intervals.icu. "
             f"{len(events)} session(s) would be pushed:", ""]
        for e in events:
            L.append(f"- {e['start_date_local']}  {e['type']}  \"{e['name']}\"  "
                     f"external_id={e['external_id']}"
                     + (f"  TSS={e['icu_training_load']}" if 'icu_training_load' in e else ""))
        if skipped:
            L.append("")
            L.append("Skipped:")
            L += [f"- {s}" for s in skipped]
        L.append("")
        L.append("Call push_block again with dry_run=false to actually upload.")
        return "\n".join(L)

    import fetch_athlete_data as fad
    session = fad.make_session()
    url = f"{fad.BASE_URL}/athlete/{athlete_id}/events/bulk?upsert=true"
    try:
        resp = session.post(url, json=events, timeout=45)
    except Exception as e:
        return f"Upload failed — could not reach Intervals.icu: {type(e).__name__}: {e}"

    result = [f"HTTP {resp.status_code}"]
    try:
        result.append(json.dumps(resp.json(), indent=2, ensure_ascii=False)[:2000])
    except Exception:
        result.append(resp.text[:2000])
    if skipped:
        result.append("")
        result.append("Skipped (not sent):")
        result += [f"- {s}" for s in skipped]
    return "\n".join(result)


if __name__ == "__main__":
    mcp.run(transport="stdio")
