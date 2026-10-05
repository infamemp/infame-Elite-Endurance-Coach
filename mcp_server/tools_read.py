"""tools_read.py — get_athlete_state, get_athlete_profile, list_roster,
roster_overview, get_execution, load_targets, what_if_targets
=========================================================================
Every value returned here is exactly what `state.md`/`profile.md`/
`roster.md` already carry — these tools read and, where a fetch is needed,
produce those same files via the same engine calls `coach.py prep` makes.
Nothing is computed here that isn't already computed there.
"""

from __future__ import annotations

import os

from .common import (DATA, OUT, ensure_import_paths, load_athlete_data, read_json_file,
                     read_text, resolve_and_prep)
from .guard import ToolError, guarded


@guarded
def get_athlete_state(athlete_id: str, force_refresh: bool = False, days: int = 180,
                      include_json: bool = False) -> dict:
    """Fetch (if the local cache is stale or force_refresh is set), resolve,
    and return #STATE — the exact content of state.md, plus whether this
    call hit the cache or refetched, plus the
    athlete's saved #SESSION (continuity.md) and race notes when they exist.
    include_json=true also returns the structured state.json (`state`); the
    markdown carries the same figures, so it is off by default.

    A stale answer is never served silently: `cache_hit` and `resolved_at`
    are always present, so a caller (or the coach reading this response)
    can see for itself how current the numbers are, rather than trusting an
    internal cache blindly — the same "#STATE more than 7 days old" judgement
    the prompt already asks a human to make from a file's date, just made
    visible here as data instead of requiring a human to open the file.
    """
    info = resolve_and_prep(athlete_id, days=days, force_refresh=force_refresh)
    continuity = _optional_text(os.path.join(info["out_dir"], "continuity.md"))
    ensure_import_paths()
    import block_review
    due = block_review.review_due(continuity) if continuity else None
    import ledger
    led = ledger.summary(athlete_id, days=30)
    state_md = read_text(
        os.path.join(DATA, str(athlete_id), "state.md"),
        f"state.md was not produced for '{athlete_id}' — check the server log.",
    )
    state_json = read_json_file(
        os.path.join(DATA, str(athlete_id), "state.json"),
        f"state.json was not produced for '{athlete_id}' — check the server log.",
    )
    result = {
        "ok": True,
        "athlete_id": athlete_id,
        "name": info["name"],
        "cache_hit": info["cache_hit"],
        "resolved_at": state_json.get("resolved_at"),
        "markdown": state_md,
        # #SESSION and race history travel with #STATE, so one call gives
        # the coach everything a conversation starts from. None = no file
        # yet (new macrocycle / no race logged), never an error.
        "continuity": continuity,
        # The block's own falsifier, handed back once its Review On date has
        # passed and no review was recorded (engine/block_review.py, v7.22).
        "review_due": due["text"] if due else None,
        "race_notes": _optional_text(os.path.join(info["out_dir"], "race_notes.md")),
        "availability": _optional_text(os.path.join(info["out_dir"], "availability.md")),
        # What was changed and what the validator said, last 30 days
        # (engine/ledger.py, v7.26). None when nothing is recorded yet.
        "ledger": ledger.render(athlete_id, led) if led["events"] else None,
    }
    # The structured state.json repeats what the markdown already says and
    # roughly doubles the size of every call, so it is sent only on request.
    if include_json:
        result["state"] = state_json
    return result


def _optional_text(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return text if text.strip() else None


@guarded
def get_athlete_profile(athlete_id: str, force_refresh: bool = False, days: int = 180) -> dict:
    """Same fetch/cache pattern as get_athlete_state, sharing the same
    underlying data — asking for both back to back never double-fetches,
    since resolve_and_prep's cache check is keyed on the same
    athlete_data.json both tools read from."""
    info = resolve_and_prep(athlete_id, days=days, force_refresh=force_refresh)
    profile_md = read_text(
        os.path.join(DATA, str(athlete_id), "profile.md"),
        f"profile.md was not produced for '{athlete_id}' (PROFILE BUILD FAILED — "
        f"non-blocking, but nothing to return here; state.md may still be usable "
        f"via get_athlete_state).",
    )
    return {
        "ok": True,
        "athlete_id": athlete_id,
        "name": info["name"],
        "cache_hit": info["cache_hit"],
        "markdown": profile_md,
    }


@guarded
def list_roster() -> dict:
    """Reads out/roster.md — no network call of its own. Matches
    coach.py's own write_roster() output exactly; this tool never
    regenerates it, only reports what the last prep run wrote."""
    ensure_import_paths()
    path = os.path.join(OUT, "roster.md")
    if not os.path.exists(path):
        raise ToolError(
            "out/roster.md doesn't exist yet — run get_athlete_state or "
            "get_athlete_profile at least once (or `python coach.py prep`) "
            "before asking for the roster."
        )
    with open(path, encoding="utf-8") as f:
        return {"ok": True, "markdown": f.read()}


@guarded
def roster_overview() -> dict:
    """Every athlete in one table, from what is already on disk: each
    athlete's saved #STATE (data/<id>/state.json) plus out/roster.md for the
    athletes on the account that were never prepared. No network call, and no
    figure computed here that state.json does not already carry — the only
    arithmetic is days-to-race against today and idle days counted to the
    date of the last prep. Each row says how old its
    numbers are (`state_age_days`, `data_age_hours`); an athlete's row is only
    as current as the last time get_athlete_state ran for them."""
    ensure_import_paths()
    import roster

    rows = roster.build(DATA, OUT)
    if not rows:
        raise ToolError(
            "No athlete has been prepared yet and out/roster.md doesn't exist — "
            "call get_athlete_state for an athlete first."
        )
    return {
        "ok": True,
        "markdown": roster.render(rows),
        "athletes": rows,
    }


@guarded
def get_execution(athlete_id: str, days: int = 28, force_refresh: bool = False) -> dict:
    """Planned versus done for the last `days` days (at most 56, the history
    the engine fetches): which planned sessions have an activity paired to
    them in Intervals.icu, planned vs actual load and minutes, and the
    compliance, RPE and feel Intervals.icu recorded. Reports only.

    Pairing is Intervals.icu's own (`paired_event_id`); nothing is matched by
    guessing. A planned session with no paired activity is "unpaired", not
    "missed" — the athlete may have skipped it or done it without pairing.

    Uses the same cache as get_athlete_state. If the cached data was fetched
    before pairing was recorded, it is refreshed once, automatically."""
    ensure_import_paths()
    import execution

    info = resolve_and_prep(athlete_id, force_refresh=force_refresh)
    result = execution.analyze(load_athlete_data(athlete_id) or {}, days=days)
    refreshed = False
    if not result.get("available") and result.get("needs_refresh") and not force_refresh:
        info = resolve_and_prep(athlete_id, force_refresh=True)
        result = execution.analyze(load_athlete_data(athlete_id) or {}, days=days)
        refreshed = True
    return {
        "ok": True,
        "athlete_id": athlete_id,
        "name": info["name"],
        "cache_hit": info["cache_hit"] and not refreshed,
        "refreshed_for_pairing": refreshed,
        "markdown": execution.render(result),
        "execution": result,
    }


@guarded
def load_targets(start_weekly_tss: float, weeks: int, cycle: str = "3:1",
                 growth_pct: float | list[float] = 5, recovery_pct: float = 30,
                 tss_per_hour: float | None = None,
                 start_date: str | None = None) -> dict:
    """Weekly TSS (and hours) targets for a block, from the coach's own
    choices: the cycle ("3:1" = three build weeks then one recovery week),
    the TSS of the first week, the growth from one build week to the next, and
    how far a recovery week drops. Pure arithmetic: no athlete data is read
    and nothing is sent anywhere. Compare the result with #STATE (CTL, ramp
    rate, ACWR) before using it; the engine does not say a target is right.
    Each week also carries its tolerance, max(5, 3% of the target): how far
    the summed TSS of the written sessions may sit from the target."""
    ensure_import_paths()
    import load_targets as lt

    try:
        result = lt.plan(start_weekly_tss, weeks, cycle=cycle, growth_pct=growth_pct,
                         recovery_pct=recovery_pct, tss_per_hour=tss_per_hour,
                         start_date=start_date)
    except ValueError as e:
        raise ToolError(str(e))
    return {"ok": True, "markdown": lt.render(result), **result}


@guarded
def what_if_targets(athlete_id: str, week_targets: dict[str, float],
                    race_date: str | None = None, event_type: str | None = None,
                    force_refresh: bool = False) -> dict:
    """What if these weekly TSS targets are followed? Feeds them into the same
    projection #STATE uses and returns CTL and TSB on race morning with and
    without the targets, before any session is written. week_targets maps the
    Monday of each whole future week (YYYY-MM-DD) to its TSS target, normally
    the numbers load_targets gave. A target is spread over the week by the
    athlete's own weekday pattern; that week's planned Intervals.icu events
    are set aside. The race is the athlete's next declared A goal unless
    race_date (and event_type, for the target TSB range) are given.
    Reports only: the verdict shown is taper_check's own, and the head coach
    decides."""
    ensure_import_paths()
    import build_state as bs
    import what_if

    resolve_and_prep(athlete_id, force_refresh=force_refresh)
    data = load_athlete_data(athlete_id)
    if not data:
        raise ToolError(f"No data for '{athlete_id}' — call get_athlete_state first.")
    try:
        result = what_if.analyze(
            bs.latest_pmc(data), data.get("events", []), data.get("activities", []),
            week_targets, bs.load_declared_goals(athlete_id), bs.load_thresholds(),
            race_date=race_date, event_type=event_type)
    except ValueError as e:
        raise ToolError(str(e))
    return {"ok": True, "athlete_id": athlete_id, "markdown": what_if.render(result), **result}


@guarded
def get_knowledge(source: str | None = None, refs: list[str] | None = None,
                  query: str | None = None, max_entries: int = 6,
                  catalog: bool = False) -> dict:
    """Read the book knowledge bases, which are not in the Claude Project.

    - source: who to read — an author or doctrine source id (coggan, friel_cycling,
      friel_tb, friel_hpc, cusick, carmichael, daniels, palladino, koop, uphill,
      hansons_marathon, hansons_half, hudson, rosario, olbrich, run_less_run_faster
      / rlrf, mujika).
    - refs: exact references, as the doctrines and zone tables cite them —
      entry IDs ("TRPM-C06-019") or sections ("§7"). Needs a source.
    - query: keywords, searched inside the source (or across every source when
      source is omitted); returns the best `max_entries` entries (max 15).
    - catalog: true reads the author's catalog — the sessions, workouts and plans
      the author actually prescribes (IDs like TRPM-L2-014) — instead of the
      principles. The source of session ideas: take the idea, rebuild the numbers.
    - neither: the source's table of contents; with no source either, the list of
      sources.
    Answers are capped in size and say when they were cut."""
    ensure_import_paths()
    import knowledge

    try:
        return {"ok": True, **knowledge.get(source=source, refs=refs, query=query,
                                            max_entries=max_entries, catalog=catalog)}
    except ValueError as e:
        raise ToolError(str(e))
