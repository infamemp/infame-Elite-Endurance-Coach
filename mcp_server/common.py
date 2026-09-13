"""common.py — shared plumbing for every tool: paths, caching, prep/deliver
==============================================================================
Every tool in this package calls into the exact same engine functions
`coach.py` does — nothing here recomputes or reinterprets a single number.
`resolve_and_prep()` is a thin orchestration layer over
`fetch_athlete_data`, `build_state`, `build_profile`, and `coach.py`'s own
`prep_one()`/`safe_filename()` — never a second implementation of what any
of them already do. That is the one property this module must never lose:
if it ever starts resolving state or validating a block itself instead of
calling the engine/verifier, the whole point of routing tools through it
is gone.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone

from .guard import ToolError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "out")

_PATHS_READY = False


def ensure_import_paths() -> None:
    """Mirror coach.py's own sys.path setup exactly, so `import
    fetch_athlete_data`, `import build_state`, `import build_profile`, and
    `import coach` all resolve the same modules the CLI runs — never a
    separate copy. Idempotent; safe to call from every tool."""
    global _PATHS_READY
    if _PATHS_READY:
        return
    for sub in ("engine", "verify"):
        p = os.path.join(ROOT, sub)
        if p not in sys.path:
            sys.path.insert(0, p)
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    _PATHS_READY = True


def _load_state_cache_minutes() -> float:
    """config/decision_thresholds.yaml's mcp.state_cache_minutes, defaulting
    to 60 if the section is missing — never a hard failure over an optional
    knob, and this module must not require build_state's own sys.exit-on-
    missing-config behavior just to answer 'how long is the cache good for'."""
    ensure_import_paths()
    try:
        import build_state as bs

        th = bs.load_thresholds()
        return float((th.get("mcp") or {}).get("state_cache_minutes", 60))
    except Exception:  # noqa: BLE001 — a bad/missing config here is not fatal
        return 60.0


def athlete_data_path(aid: str) -> str:
    return os.path.join(DATA, str(aid), "athlete_data.json")


def load_athlete_data(aid: str) -> dict | None:
    path = athlete_data_path(aid)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_cache_fresh(aid: str, max_age_minutes: float | None = None) -> bool:
    """Whether data/<aid>/athlete_data.json is recent enough to skip a
    fresh Intervals.icu fetch.

    Deliberately keyed on the file's own mtime, not the payload's
    `fetched_at` field: `fetched_at` is `date.today().isoformat()` —
    day-granularity only, by design, since that's all fetch_athlete_data.py
    ever records. Under a 60-minute cache window, treating a date-only
    timestamp as "fetched at midnight" would read as stale for all but the
    first hour of every day, which defeats the point of caching at all.
    The file's mtime is the actual moment this data was last written and
    has real time resolution — a straightforwardly better answer to
    "how old is this," not a workaround."""
    path = athlete_data_path(aid)
    if not os.path.exists(path):
        return False
    minutes = max_age_minutes if max_age_minutes is not None else _load_state_cache_minutes()
    age = (datetime.now(timezone.utc).timestamp() - os.path.getmtime(path)) / 60
    return age <= minutes


def lookup_on_account(aid: str, fad) -> tuple[object, str]:
    """One network call: (real_aid, name) for `aid` from
    fad.list_athletes(). Raises ToolError if the account has no such
    athlete — the same check coach.py's cmd_prep()/cmd_new() do before
    trusting an id."""
    try:
        athletes = fad.list_athletes()
    except Exception as exc:  # noqa: BLE001
        raise ToolError(f"Connection to Intervals.icu failed: {exc}") from exc
    match = [(a, n) for a, n in athletes if str(a) == str(aid)]
    if not match:
        raise ToolError(
            f"Athlete '{aid}' not found on the account. "
            f"Call list_roster to see valid ids."
        )
    return match[0]


def deliver_to_out(aid: str, name: str) -> str:
    """Copy state.md/profile.md to out/<safe_name>/ — the exact same
    delivery step coach.py's prep_one() performs, reusing its own
    safe_filename() rather than a second normalization rule that could
    drift from it."""
    ensure_import_paths()
    import coach

    dest_name = coach.safe_filename(name) or str(aid)
    out_dir = os.path.join(OUT, dest_name)
    os.makedirs(out_dir, exist_ok=True)
    for fname in ("state.md", "profile.md"):
        src = os.path.join(DATA, str(aid), fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out_dir, fname))
    return out_dir


def resolve_and_prep(aid: str, days: int = 180, force_refresh: bool = False) -> dict:
    """Fetch (only if the local cache is stale or a refresh was requested),
    then always resolve state and render the profile from whatever data is
    now on disk, then deliver to out/. Returns
    {"name", "cache_hit", "out_dir"}.

    The cache governs one thing only: whether Intervals.icu gets hit again.
    build_state.build()/build_profile.build() run unconditionally on every
    call, cache hit or not — cheap, deterministic, local computation with no
    reason to skip, and it's what guarantees a threshold or config edit is
    reflected immediately even when the underlying athlete_data.json wasn't
    refetched this time.
    """
    ensure_import_paths()
    import build_state as bs
    import build_profile as bp

    cache_hit = (not force_refresh) and is_cache_fresh(aid)

    if not cache_hit:
        import fetch_athlete_data as fad

        fad.SESSION = fad.make_session()
        # coach.py's own cmd_prep() uses the id it gets back from
        # list_athletes()'s match, not the raw string a caller typed —
        # mirrored here so data/<aid>/ is always named the same way the
        # CLI would name it, never a second, possibly differently-typed id.
        real_aid, name = lookup_on_account(aid, fad)
        aid = str(real_aid)
        try:
            fad.fetch_one(aid, name, days, DATA)
        except Exception as exc:  # noqa: BLE001
            raise ToolError(f"Fetch failed for {aid}: {exc}") from exc
        try:
            import coach

            coach.capture_snapshot(aid)
        except Exception:  # noqa: BLE001 — non-blocking, same as coach.py's own prep_one
            pass
    else:
        data = load_athlete_data(aid)
        name = (data or {}).get("profile", {}).get("name") or str(aid)

    thresholds = bs.load_thresholds()
    try:
        bs.build(aid, thresholds, quiet=True)
    except Exception as exc:  # noqa: BLE001
        raise ToolError(f"State resolution failed for {aid}: {exc}") from exc
    try:
        bp.build(aid, quiet=True)
    except Exception:  # noqa: BLE001 — non-blocking, same as coach.py's own prep_one
        pass

    out_dir = deliver_to_out(aid, name)
    return {"name": name, "cache_hit": cache_hit, "out_dir": out_dir}


def read_text(path: str, missing_message: str) -> str:
    if not os.path.exists(path):
        raise ToolError(missing_message)
    with open(path, encoding="utf-8") as f:
        return f.read()


def read_json_file(path: str, missing_message: str) -> dict:
    if not os.path.exists(path):
        raise ToolError(missing_message)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def safe_out_dir(aid: str, name: str | None = None) -> str:
    """out/<safe_name>/ for an athlete we already have local data for —
    used by the write tools, which never fetch and so never learn a name
    from the API themselves. Falls back to the raw id when no local
    profile name is on disk yet, matching coach.py's own fallback."""
    ensure_import_paths()
    import coach

    if name is None:
        data = load_athlete_data(aid)
        name = (data or {}).get("profile", {}).get("name")
    dest_name = coach.safe_filename(name) if name else None
    dest_name = dest_name or str(aid)
    out_dir = os.path.join(OUT, dest_name)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir
