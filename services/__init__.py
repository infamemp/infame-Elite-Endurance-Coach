"""
services — the one interface to the engine for every client (v7.33).

The coach reaches the engine through the MCP tools (mcp_server/); the web
interface (batch 7) and any script reach it through this package. Both call
the same functions, so a rule fixed once is fixed for every client:

    import services
    services.athlete_state("i18969")["markdown"]
    services.validate(file_path="out/.../2026-10-06_bloque_w1.md",
                      athlete_id="i18969")["summary"]["findings"]

Every function returns a plain dict with "ok": True, or "ok": False with
"error" and "error_type" — it never raises and never prints (the MCP tools'
guard does that work: mcp_server/guard.py). Writes to Intervals.icu keep the
same two gates as the tools: nothing is sent without dry_run=False AND
confirm=True. The `mcp` package is not needed to import this one.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from mcp_server.common import OUT, ensure_import_paths  # noqa: E402
from mcp_server.guard import guarded  # noqa: E402
from mcp_server import tools_coach, tools_push, tools_read, tools_validate, tools_write  # noqa: E402

__all__ = [
    "athlete_state", "athlete_profile", "roster", "roster_overview", "execution",
    "load_targets", "what_if_targets", "knowledge", "reference",
    "save_block", "validate", "push_block", "remove_block",
    "save_continuity", "save_availability", "save_race_result", "save_training_age",
    "save_declared_profile", "post_activity_comment", "update_threshold",
    "ledger", "athlete_files",
]

# ── Reading ──────────────────────────────────────────────────────
athlete_state = tools_read.get_athlete_state          # #STATE, #SESSION, review, ledger
athlete_profile = tools_read.get_athlete_profile      # profile.md
roster = tools_read.list_roster                       # every athlete on the account
roster_overview = tools_read.roster_overview          # all athletes in one table
execution = tools_read.get_execution                  # planned versus done
load_targets = tools_read.load_targets                # weekly TSS arithmetic
what_if_targets = tools_read.what_if_targets          # race-morning CTL/TSB with targets
knowledge = tools_read.get_knowledge                  # book knowledge bases
reference = tools_read.get_reference                  # zone tables, architectures, intake

# ── Writing local files ──────────────────────────────────────────
save_block = tools_write.save_block
save_continuity = tools_write.save_continuity
save_availability = tools_write.save_availability
save_race_result = tools_write.save_race_result
save_training_age = tools_write.save_training_age
save_declared_profile = tools_write.save_declared_profile   # dry run by default

# ── Intervals.icu (dry run by default; dry_run=False AND confirm=True to act) ──
push_block = tools_push.push_block
remove_block = tools_coach.remove_block
post_activity_comment = tools_coach.post_activity_comment
update_threshold = tools_coach.update_threshold


def validate(file_path=None, athlete_id=None, fill_tss=False, week_targets=None):
    """The verification gate, with its report also as data: `summary` holds
    the sessions and every finding (severity, code, line, message)."""
    r = tools_validate.validate_block(athlete_id=athlete_id, file_path=file_path,
                                      fill_tss=fill_tss, week_targets=week_targets)
    if r.get("ok") and r.get("report") is not None:
        ensure_import_paths()
        import validate_block as vb
        r["summary"] = vb.parse_report(r["report"])
    return r


@guarded
def ledger(athlete_id, days=30):
    """What was changed and what the gate said: the summary and every event
    of the last `days` days (None = all), oldest first."""
    ensure_import_paths()
    import ledger as lg
    summary = lg.summary(athlete_id, days=days)
    events = lg.read(athlete_id)
    if days is not None:
        events = lg._since(events, days)  # noqa: SLF001 — same filter the summary uses
    return {"ok": True, "athlete_id": athlete_id, "summary": summary, "events": events,
            "markdown": lg.render(athlete_id, summary)}


@guarded
def athlete_files(athlete_id):
    """The athlete's saved files under out/: #SESSION, availability, race
    notes and every saved week (name, size, last change), newest first."""
    ensure_import_paths()
    import shared
    folder = shared.find_out_dir(OUT, athlete_id)
    if not folder:
        return {"ok": True, "athlete_id": athlete_id, "folder": None, "files": {}, "blocks": []}

    def _text(name):
        p = os.path.join(folder, name)
        return open(p, encoding="utf-8").read() if os.path.exists(p) else None

    blocks_dir = os.path.join(folder, "blocks")
    blocks = []
    if os.path.isdir(blocks_dir):
        for fn in os.listdir(blocks_dir):
            if fn.endswith(".md"):
                p = os.path.join(blocks_dir, fn)
                blocks.append({"name": fn, "path": os.path.relpath(p, ROOT),
                               "bytes": os.path.getsize(p), "modified": os.path.getmtime(p)})
    blocks.sort(key=lambda b: -b["modified"])
    return {"ok": True, "athlete_id": athlete_id,
            "folder": os.path.relpath(folder, ROOT),
            "files": {"continuity": _text("continuity.md"),
                      "availability": _text("availability.md"),
                      "race_notes": _text("race_notes.md")},
            "blocks": blocks}
