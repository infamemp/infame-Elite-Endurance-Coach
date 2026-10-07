"""tools_write.py — save_continuity, save_race_result, save_block
=====================================================================
These three write exactly the files a head coach otherwise pastes by hand
— continuity.md, race_notes.md, and a block file under out/<athlete>/blocks/
— and are the first point anywhere in this system that puts even a light
structural check on them before they land on disk. `coach.py` itself only
ever *reads* these three files (`check_continuity()`, `read_race_notes()`);
none of its own code validates what a human pasted into them
(`archive/WORKFLOW_ACTUAL.md` §4 names this as a real, pre-existing gap). The
checks here are deliberately shallow — the envelope a file must have to be
read back correctly by the code that already reads it — never a rule about
what a `#SESSION`'s phase or block name should say. That judgement stays
entirely in the prompt, per this task's own scope limit.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime

from .common import DATA, OUT, ledger_record, safe_out_dir, block_file_name
import json
from .guard import ToolError, guarded

# Mirrors coach.py's read_race_notes() patterns exactly (those are inline in
# that function, not exported constants) — kept in sync deliberately, since
# a block this tool writes must parse back the same way that function reads
# it, or `coach.py review` silently never sees it.
_RACE_RESULT_SPLIT_RE = re.compile(r"(?=^#RACE_RESULT\s*$)", re.M)
_RACE_RESULT_DATE_RE = re.compile(r"^Date:\s*(\S+)", re.M)


# Maintainer notes (the docstring below is the description the model reads):
# Write out/<athlete>/availability.md, always overwriting: the head
# coach's stated daily maximums, so they are asked for once and read back
# by get_athlete_state instead of being re-asked (or invented) in every
# conversation. Requires an #AVAILABILITY ... #END envelope. It never
# judges the numbers — that stays with the head coach.
@guarded
def save_availability(athlete_id: str, text: str, athlete_name: str | None = None) -> dict:
    """Save the head coach's stated daily maximums as an #AVAILABILITY … #END block (it
    replaces the previous one), so they are never asked again. get_athlete_state
    returns it as `availability`."""
    body = (text or "").strip()
    if not body:
        raise ToolError("Refusing to write an empty availability.md.")
    if not re.match(r"^#AVAILABILITY\b", body):
        raise ToolError("This must start with '#AVAILABILITY'. Nothing was written.")
    if "#END" not in body:
        raise ToolError("No '#END' found — the block looks incomplete. Nothing was written.")
    out_dir = safe_out_dir(athlete_id, athlete_name)
    path = os.path.join(out_dir, "availability.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body.rstrip() + "\n")
    return {"ok": True, "path": os.path.relpath(path, os.path.dirname(OUT))}


# Maintainer notes (the docstring below is the description the model reads):
# Record the athlete's training age — years of consistent endurance
# training, as the head coach stated it — in data/<athlete_id>/facts.json.
# It sets the CTL ramp band in #STATE (Coggan Table 9.2). Asked once and
# never again: the next get_athlete_state(force_refresh=true) shows the band.
# A value in the declared profile (history.training_age_years) wins over
# this one. It never judges the number.
@guarded
def save_training_age(athlete_id: str, years: float) -> dict:
    """Save the athlete's training age — years of consistent endurance training as the
    head coach stated it, 0 for a beginner. It sets the CTL ramp band in #STATE:
    call get_athlete_state with force_refresh=true afterwards. A value in the
    declared profile wins over this one."""
    try:
        value = float(years)
    except (TypeError, ValueError):
        raise ToolError("years must be a number (0 for a beginner). Nothing was written.")
    if not 0 <= value <= 80:
        raise ToolError("years must be between 0 and 80. Nothing was written.")
    value = int(value) if value == int(value) else round(value, 1)
    dest = os.path.join(DATA, str(athlete_id))
    if not os.path.isdir(dest):
        raise ToolError(f"No local data for {athlete_id}: call get_athlete_state first. "
                        "Nothing was written.")
    path = os.path.join(dest, "facts.json")
    facts = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                facts = json.load(f) or {}
        except (OSError, ValueError):
            facts = {}
    facts["training_age_years"] = value
    facts["training_age_stated_on"] = date.today().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(facts, f, indent=2, ensure_ascii=False)
    ledger_record(athlete_id, "training_age_saved", years=value)
    return {"ok": True, "training_age_years": value,
            "path": os.path.relpath(path, os.path.dirname(DATA))}


# Maintainer notes (the docstring below is the description the model reads):
# Write out/<athlete>/continuity.md, always overwriting — the same
# file coach.py's check_continuity() only ever reports the presence/age
# of. Requires the boxed #SESSION ... #END envelope
# (the shape the prompt's #SESSION block has) so a
# partial or empty paste is refused instead of silently corrupting the
# macrocycle's resumed position. Never inspects what's inside that
# envelope — Active Phase, Current Block, the Metric Map — that's the
# prompt's structure to define and read, not this tool's to enforce.
@guarded
def save_continuity(athlete_id: str, text: str, athlete_name: str | None = None) -> dict:
    """Save a #SESSION … #END block as the athlete's continuity record (it replaces the
    previous one). Call it every time you emit #SESSION. Refused when the text does
    not start with #SESSION or has no #END; the content itself is never judged."""
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
    phase = re.search(r"^\s*Active Phase\s*:\s*(.+?)\s*$", body, re.M)
    falsifier = re.search(r"^\s*Would Show Wrong\s*:\s*(.+?)\s*$", body, re.M | re.I)
    review = re.search(r"^\s*Review On\s*:\s*(.+?)\s*$", body, re.M | re.I)
    ledger_record(athlete_id, "continuity_saved",
                  active_phase=phase.group(1) if phase else None,
                  would_show_wrong=falsifier.group(1) if falsifier else None,
                  review_on=review.group(1) if review else None)
    return {"ok": True, "path": os.path.relpath(path, os.path.dirname(OUT))}


# Maintainer notes (the docstring below is the description the model reads):
# Append a #RACE_RESULT block to out/<athlete>/race_notes.md — never
# overwriting or deleting what's already there, matching
# manual/GUIDE.md's "never delete or overwrite" rule.
#
# `date_str` is required and authoritative (YYYY-MM-DD) — it's what
# coach.py review's --since window actually filters on, so it's taken as
# its own argument rather than trusted to already be correctly embedded
# in free-form `text`. `text` is the rest of the block in whatever shape
# the coach wrote it; the '#RACE_RESULT' header line and 'Date:' field
# are added automatically if missing, exactly as save_race_result's
# original description promised ("normalizing the header if the caller
# omitted it") — but the result is always re-checked against the same
# patterns coach.py's read_race_notes() uses before it's written, so a
# block that would silently fail to be picked up later is refused now
# instead.
@guarded
def save_race_result(
    athlete_id: str,
    date_str: str,
    text: str,
    athlete_name: str | None = None,
) -> dict:
    """Append a #RACE_RESULT block to the athlete's race notes (it never overwrites).
    date_str: the race date, YYYY-MM-DD. text: the rest of the block, without a
    Date: line."""
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
    ledger_record(athlete_id, "race_result_saved", date=date_str)
    return {"ok": True, "path": os.path.relpath(path, os.path.dirname(OUT))}


# Maintainer notes (the docstring below is the description the model reads):
# Write out/<athlete>/blocks/<today>_bloque_w<week>.md (or
# <today>_bloque.md when no week is given), overwriting a file of the same
# name — so re-saving a corrected week replaces it, while a different
# week saved the same day gets its own file. This is
# deliberately dumb: it does not parse or validate the block at all
# (that's validate_block's job, as a separate, explicit next step, the
# same two-step shape as the manual copy-paste-then-check workflow it
# replaces).
@guarded
def save_block(athlete_id: str, text: str, athlete_name: str | None = None,
               week: int | None = None) -> dict:
    """Save one week the moment it is written, as
    out/<athlete>/blocks/<today>_bloque_w<week>.md (saving the same week again
    replaces it). Returns the path to pass to validate_block and push_block. It does
    not validate."""
    body = (text or "").strip()
    if not body:
        raise ToolError("Refusing to save an empty block.")
    out_dir = safe_out_dir(athlete_id, athlete_name)
    blocks_dir = os.path.join(out_dir, "blocks")
    os.makedirs(blocks_dir, exist_ok=True)
    fname = block_file_name(week)
    path = os.path.join(blocks_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body.rstrip() + "\n")
    return {"ok": True, "path": os.path.relpath(path, os.path.dirname(OUT))}


# Maintainer notes (the docstring below is the description the model reads):
# Write the athlete's declared profile, config/athletes/<athlete_id>.yaml —
# after an intake, or to change goals, equipment, limitations, methodology or
# any other declared field. Same gate as an upload:
#
# 1. Call with the defaults (a dry run): the text is checked — valid YAML,
#    every top-level section of config/templates/profile_template.yaml present, names
#    the system recognizes — and the answer shows what would change (a diff
#    against the current file, or "new profile").
# 2. Show the head coach the changes in plain words and wait for approval.
# 3. Call again with dry_run=False, confirm=True. The previous file is kept in
#    data/<athlete_id>/profile_history/ before it is replaced.
# Then call get_athlete_profile with force_refresh=true.
@guarded
def save_declared_profile(athlete_id: str, yaml_text: str, dry_run: bool = True,
                          confirm: bool = False) -> dict:
    """Write the athlete's declared profile (config/athletes/<id>.yaml) after an intake
    or any approved change. Pass the whole profile, structured like
    get_reference(topic='profile_template'). The default is a dry run: it checks the
    YAML, the template's sections and the names the system knows, and returns what
    would change. Show the head coach the changes in plain words, wait for approval,
    then call again with dry_run=false, confirm=true. The previous version is kept.
    Then call get_athlete_profile with force_refresh=true."""
    import difflib
    import shutil
    import yaml as _yaml

    from .common import ROOT, ensure_import_paths

    aid = str(athlete_id).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", aid) or aid.startswith("_") or aid == "TESTRAMP":
        raise ToolError(f"'{athlete_id}' is not a valid athlete id. Nothing was written.")
    body = (yaml_text or "").strip()
    if body.startswith("```"):
        body = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", body).strip()
    try:
        data = _yaml.safe_load(body)
    except _yaml.YAMLError as e:
        raise ToolError(f"The text is not valid YAML ({str(e).splitlines()[0]}). Nothing was written.")
    if not isinstance(data, dict):
        raise ToolError("The profile must be a YAML mapping like the profile template. Nothing was written.")

    cfg_dir = os.path.join(ROOT, "config", "athletes")
    with open(os.path.join(ROOT, "config", "templates", "profile_template.yaml"),
              encoding="utf-8") as f:
        template = _yaml.safe_load(f) or {}
    missing = [k for k in template if k not in data]
    if missing:
        raise ToolError("Missing sections compared with the profile template: " + ", ".join(missing)
                        + ". Nothing was written.")

    ensure_import_paths()
    import build_profile
    warnings = build_profile.profile_warnings(data)

    path = os.path.join(cfg_dir, f"{aid}.yaml")
    exists = os.path.exists(path)
    old = open(path, encoding="utf-8").read() if exists else ""
    new = body.rstrip() + "\n"
    diff = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                        f"{aid}.yaml (current)", f"{aid}.yaml (new)", n=1))
    if exists and not diff:
        return {"ok": True, "dry_run": dry_run, "changed": False,
                "message": "The new text is identical to the current profile. Nothing to do."}
    report = {"ok": True, "exists": exists, "warnings": warnings,
              "changes": (diff[:6000] + "\n[…diff cut]") if len(diff) > 6000 else diff}
    if dry_run or not confirm:
        return {**report, "dry_run": True,
                "message": "Dry run: nothing was written. Show the head coach what changes, wait "
                           "for approval, then call again with dry_run=False, confirm=True."}

    if exists:
        hist = os.path.join(DATA, aid, "profile_history")
        os.makedirs(hist, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, os.path.join(hist, f"{aid}_{stamp}.yaml"))
    # config/athletes/ is gitignored, so a fresh clone has no such folder:
    # the first profile saved on a machine must create it.
    os.makedirs(cfg_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    try:
        before = _yaml.safe_load(old) or {} if old else {}
    except _yaml.YAMLError:
        before = {}
    ledger_record(aid, "profile_saved", new=not exists,
                  sections_changed=sorted(k for k in set(before) | set(data)
                                          if before.get(k) != data.get(k)))
    return {**report, "dry_run": False, "path": os.path.relpath(path, ROOT),
            "message": "Saved. Now call get_athlete_profile with force_refresh=true."}
