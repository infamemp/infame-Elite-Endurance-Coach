"""tools_write.py — save_continuity, save_race_result, save_block
=====================================================================
These three write exactly the files a head coach otherwise pastes by hand
— continuity.md, race_notes.md, and a block file under out/<athlete>/blocks/
— and are the first point anywhere in this system that puts even a light
structural check on them before they land on disk. `coach.py` itself only
ever *reads* these three files (`check_continuity()`, `read_race_notes()`);
none of its own code validates what a human pasted into them
(`WORKFLOW_ACTUAL.md` §4 names this as a real, pre-existing gap). The
checks here are deliberately shallow — the envelope a file must have to be
read back correctly by the code that already reads it — never a rule about
what a `#SESSION`'s phase or block name should say. That judgement stays
entirely in the prompt, per this task's own scope limit.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime

from .common import OUT, safe_out_dir
from .guard import ToolError, guarded

# Mirrors coach.py's read_race_notes() patterns exactly (those are inline in
# that function, not exported constants) — kept in sync deliberately, since
# a block this tool writes must parse back the same way that function reads
# it, or `coach.py review` silently never sees it.
_RACE_RESULT_SPLIT_RE = re.compile(r"(?=^#RACE_RESULT\s*$)", re.M)
_RACE_RESULT_DATE_RE = re.compile(r"^Date:\s*(\S+)", re.M)


@guarded
def save_continuity(athlete_id: str, text: str, athlete_name: str | None = None) -> dict:
    """Write out/<athlete>/continuity.md, always overwriting — the same
    file coach.py's check_continuity() only ever reports the presence/age
    of. Requires the boxed #SESSION ... #END envelope
    (manual/OPERATIONS_MANUAL.md §8 describes exactly this shape) so a
    partial or empty paste is refused instead of silently corrupting the
    macrocycle's resumed position. Never inspects what's inside that
    envelope — Active Phase, Current Block, the Metric Map — that's the
    prompt's structure to define and read, not this tool's to enforce."""
    body = (text or "").strip()
    if not body:
        raise ToolError("Refusing to write an empty continuity.md.")
    if not re.match(r"^#SESSION\b", body):
        raise ToolError(
            "This doesn't look like a #SESSION block — it must start with "
            "'#SESSION'. Nothing was written."
        )
    if "#END" not in body:
        raise ToolError(
            "No '#END' found — the #SESSION block looks incomplete. "
            "Nothing was written."
        )
    out_dir = safe_out_dir(athlete_id, athlete_name)
    path = os.path.join(out_dir, "continuity.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body.rstrip() + "\n")
    return {"ok": True, "path": os.path.relpath(path, os.path.dirname(OUT))}


@guarded
def save_race_result(
    athlete_id: str,
    date_str: str,
    text: str,
    athlete_name: str | None = None,
) -> dict:
    """Append a #RACE_RESULT block to out/<athlete>/race_notes.md — never
    overwriting or deleting what's already there, matching
    manual/OPERATIONS_MANUAL.md §9's "never delete or overwrite" rule.

    `date_str` is required and authoritative (YYYY-MM-DD) — it's what
    coach.py review's --since window actually filters on, so it's taken as
    its own argument rather than trusted to already be correctly embedded
    in free-form `text`. `text` is the rest of the block in whatever shape
    the coach wrote it; the '#RACE_RESULT' header line and 'Date:' field
    are added automatically if missing, exactly as save_race_result's
    original description promised ("normalizing the header if the caller
    omitted it") — but the result is always re-checked against the same
    patterns coach.py's read_race_notes() uses before it's written, so a
    block that would silently fail to be picked up later is refused now
    instead."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ToolError(f"date_str must be YYYY-MM-DD, got '{date_str}'.") from exc

    body = (text or "").strip()
    if not body:
        raise ToolError("Refusing to append an empty race result.")

    lines = body.splitlines()
    if lines and lines[0].strip() == "#RACE_RESULT":
        lines = lines[1:]
    body = "\n".join(lines).strip()

    if _RACE_RESULT_DATE_RE.search(body):
        raise ToolError(
            "`text` already contains its own 'Date:' line, which would "
            "conflict or duplicate with date_str. Pass the date only via "
            "date_str and remove the 'Date:' line from text."
        )

    block = f"#RACE_RESULT\nDate: {date_str}\n{body}\n"

    # Re-derive from the assembled block using coach.py's own patterns —
    # proves this block will actually be found and dated correctly the
    # next time `coach.py review` reads race_notes.md, rather than assuming
    # the assembly above got it right.
    parts = [p for p in _RACE_RESULT_SPLIT_RE.split(block) if p.strip().startswith("#RACE_RESULT")]
    if len(parts) != 1:
        raise ToolError("Internal error assembling the #RACE_RESULT block — nothing was written.")
    m = _RACE_RESULT_DATE_RE.search(parts[0])
    if not m or m.group(1) != date_str:
        raise ToolError(
            "The assembled block's Date field doesn't match date_str — "
            "nothing was written. This usually means `text` already "
            "contained its own conflicting 'Date:' line; remove it and "
            "pass the date only via date_str."
        )

    out_dir = safe_out_dir(athlete_id, athlete_name)
    path = os.path.join(out_dir, "race_notes.md")
    existing = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = f.read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(existing.rstrip("\n") + ("\n\n" if existing.strip() else "") + block)
    return {"ok": True, "path": os.path.relpath(path, os.path.dirname(OUT))}


@guarded
def save_block(athlete_id: str, text: str, athlete_name: str | None = None) -> dict:
    """Write out/<athlete>/blocks/<today>_bloque.md, overwriting a file
    already saved today — same convention as the original tool. This is
    deliberately dumb: it does not parse or validate the block at all
    (that's validate_block's job, as a separate, explicit next step, the
    same two-step shape as the manual copy-paste-then-check workflow it
    replaces)."""
    body = (text or "").strip()
    if not body:
        raise ToolError("Refusing to save an empty block.")
    out_dir = safe_out_dir(athlete_id, athlete_name)
    blocks_dir = os.path.join(out_dir, "blocks")
    os.makedirs(blocks_dir, exist_ok=True)
    fname = f"{date.today().isoformat()}_bloque.md"
    path = os.path.join(blocks_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body.rstrip() + "\n")
    return {"ok": True, "path": os.path.relpath(path, os.path.dirname(OUT))}
