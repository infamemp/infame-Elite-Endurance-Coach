"""
shared.py — small helpers every part of the engine shares (v7.33).

Before v7.33 each module carried its own copy: eight date parsers, three sets
of Intervals.icu activity types, two folder-naming rules. A fix in one copy
never reached the others. These are the single versions; the modules import
them under their old local names, so nothing else changed.

  iso_day(s)            "YYYY-MM-DD..." -> date; raises ValueError (strict)
  as_date(raw)          date, datetime, ISO or DD-MM-YYYY -> date; None if not
  sport_of(type)        Intervals.icu activity type -> "cycling" | "running" | None
  safe_filename(name)   an athlete's name as a folder name
  athlete_out_dir(...)  the athlete's folder under out/, found by id
  read_config(name)     one file of config/, parsed once (re-read if it changes)
  thresholds()          decision_thresholds.yaml with the derived class cutpoints
  EngineError           what the engine raises instead of ending the process
"""

import copy
import os
import re
import sys
import unicodedata
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config")


class EngineError(Exception):
    """Something the caller has to fix before the engine can go on: no data
    for an athlete, a missing config file, an unknown methodology. Until
    v7.33 the engine called sys.exit() for these, which ends the whole
    process — fine for a one-shot command, wrong for the MCP server or a web
    interface. The command-line entry points turn it back into a message and
    exit code 1, so on the command line nothing changed."""


def cli(main):
    """Run a command-line main(): an EngineError becomes its message on
    stderr and exit code 1, exactly what sys.exit(message) used to do."""
    try:
        return main()
    except EngineError as exc:
        sys.exit(str(exc))


_CONFIG_CACHE = {}


def read_config(name, required=True):
    """config/<name> parsed. Each file is read once and read again only when
    it changes on disk (so an edit is picked up without restarting the MCP
    server). Every caller gets its own copy. A missing file raises
    EngineError, or gives {} when required=False."""
    path = name if os.path.isabs(name) else os.path.join(CONFIG, name)
    try:
        stamp = os.stat(path).st_mtime_ns
    except OSError:
        if required:
            raise EngineError(f"Config file not found: {path}") from None
        return {}
    hit = _CONFIG_CACHE.get(path)
    if hit is None or hit[0] != stamp:
        import yaml
        with open(path, encoding="utf-8") as f:
            hit = (stamp, yaml.safe_load(f) or {})
        _CONFIG_CACHE[path] = hit
    return copy.deepcopy(hit[1])


def thresholds():
    """config/decision_thresholds.yaml, with the class cutpoints derived
    from tss_classes.yaml + crosswalk.yaml (they are never stored)."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import zone_model
    return zone_model.with_derived_cutpoints(read_config("decision_thresholds.yaml"))

CYCLING_TYPES = frozenset({"ride", "virtualride", "gravelride", "mtb",
                           "mountainbikeride", "ebikeride"})
RUNNING_TYPES = frozenset({"run", "virtualrun", "trailrun"})

# The file that ties a folder under out/ to an athlete id (v7.33).
ID_MARKER = "athlete_id.txt"


def iso_day(s):
    """Strict: the first 10 characters must be YYYY-MM-DD."""
    return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()


def as_date(raw):
    """Lenient: a date, a datetime, an ISO date (with or without time) or a
    DD-MM-YYYY header date. None for anything else, never a guess."""
    if raw in (None, ""):
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    text = str(raw)[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def sport_of(activity_type):
    t = (activity_type or "").strip().lower()
    return "cycling" if t in CYCLING_TYPES else "running" if t in RUNNING_TYPES else None


def safe_filename(name):
    """An athlete's name as a folder name: accents removed, spaces to "_"."""
    normalized = unicodedata.normalize("NFKD", name or "")
    safe = normalized.encode("ascii", "ignore").decode("ascii")
    safe = re.sub(r"[^\w\s-]", " ", safe)
    safe = re.sub(r"\s+", "_", safe.strip())
    safe = re.sub(r"_+", "_", safe)
    safe = re.sub(r"-+", "-", safe)
    return safe.strip("-_")


def _marker_id(folder):
    try:
        with open(os.path.join(folder, ID_MARKER), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def find_out_dir(out_root, aid):
    """The folder under out/ whose athlete_id.txt names this athlete, or None."""
    aid = str(aid)
    try:
        names = sorted(os.listdir(out_root))
    except OSError:
        return None
    for name in names:
        folder = os.path.join(out_root, name)
        if os.path.isdir(folder) and _marker_id(folder) == aid:
            return folder
    return None


def athlete_out_dir(out_root, aid, name=None, create=True):
    """The athlete's folder under out/ (continuity, availability, race notes,
    blocks), found by id, not by name (v7.33).

    Until v7.32 the folder was only the athlete's name as Intervals.icu spells
    it, so a renamed athlete (an accent, a second surname) got a new, empty
    folder and the coach lost the saved #SESSION. Now each folder carries
    athlete_id.txt: the folder that names the id is used whatever its name.
    The first time, the folder is the name as before (so existing folders are
    adopted, not moved) and the marker is written into it; when that name is
    already another athlete's, "<name>_<id>" is used instead."""
    aid = str(aid)
    found = find_out_dir(out_root, aid)
    if found:
        return found
    base = safe_filename(name) if name else ""
    folder = os.path.join(out_root, base or aid)
    owner = _marker_id(folder) if os.path.isdir(folder) else None
    if owner and owner != aid:
        folder = os.path.join(out_root, f"{base}_{aid}" if base else aid)
    if create:
        os.makedirs(folder, exist_ok=True)
        if _marker_id(folder) is None:
            with open(os.path.join(folder, ID_MARKER), "w", encoding="utf-8") as f:
                f.write(aid + "\n")
    return folder
