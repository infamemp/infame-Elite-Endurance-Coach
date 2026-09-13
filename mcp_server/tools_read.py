"""tools_read.py — get_athlete_state, get_athlete_profile, list_roster
=========================================================================
Every value returned here is exactly what `state.md`/`profile.md`/
`roster.md` already carry — these tools read and, where a fetch is needed,
produce those same files via the same engine calls `coach.py prep` makes.
Nothing is computed here that isn't already computed there.
"""

from __future__ import annotations

import os

from .common import DATA, OUT, ensure_import_paths, read_json_file, read_text, resolve_and_prep
from .guard import ToolError, guarded


@guarded
def get_athlete_state(athlete_id: str, force_refresh: bool = False, days: int = 180) -> dict:
    """Fetch (if the local cache is stale or force_refresh is set), resolve,
    and return #STATE — the exact content of state.md, plus its structured
    state.json, plus whether this call hit the cache or refetched.

    A stale answer is never served silently: `cache_hit` and `resolved_at`
    are always present, so a caller (or the coach reading this response)
    can see for itself how current the numbers are, rather than trusting an
    internal cache blindly — the same "#STATE more than 7 days old" judgement
    the prompt already asks a human to make from a file's date, just made
    visible here as data instead of requiring a human to open the file.
    """
    info = resolve_and_prep(athlete_id, days=days, force_refresh=force_refresh)
    state_md = read_text(
        os.path.join(DATA, str(athlete_id), "state.md"),
        f"state.md was not produced for '{athlete_id}' — check the server log.",
    )
    state_json = read_json_file(
        os.path.join(DATA, str(athlete_id), "state.json"),
        f"state.json was not produced for '{athlete_id}' — check the server log.",
    )
    return {
        "ok": True,
        "athlete_id": athlete_id,
        "name": info["name"],
        "cache_hit": info["cache_hit"],
        "resolved_at": state_json.get("resolved_at"),
        "markdown": state_md,
        "state": state_json,
    }


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
