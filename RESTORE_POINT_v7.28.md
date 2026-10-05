# RESTORE POINT — Infame Elite Endurance Coach v7.28

**Date frozen:** 2026-10-05
**Previous:** v7.27 — every version is in `CHANGELOG.md`; older restore points are in the git history
**Prompt:** `Prompt/infame_elite_endurance_coach.md` v7.27 (unchanged in v7.28)
**Tests:** `python tests/run_tests.py` → 748/748 · `.venv-mcp\Scripts\python.exe tests/test_mcp_server.py` → 169/169

## What changed in v7.28

Maintenance only (batch 1 of the 2026-10-05 audit). No training rule, number or
check changed; the prompt and the Project files stay as they are.

- **Removed** what git already keeps: the two duplicated prompt copies at the root,
  `legacy/` (retired Excel pipeline), `archive/Knowledge_legacy/`, every
  `Prompt/archive/` copy except the last two, and every archived restore point
  except `archive/RESTORE_POINT_v6.5.md` (the MCP incident record the code cites).
- **`CHANGELOG.md`** (new): every version, newest first, in one place. The README
  points to it instead of carrying its own changelog.
- **Real names out of the repo:** test blocks renamed (`road_taper_block.md`,
  `road_taper_raw_unfixed.md`), an unused one deleted, a real athlete id and
  folder name replaced by placeholders in the docs.
- **MCP server:** the temporary diagnostics are gone (they logged every tool's full
  arguments); the log records only the tool name and rotates at 5 MB (3 files kept).
- **`get_athlete_state`** returns the `#STATE` markdown without the duplicated
  `state.json` (about half the size); `include_json=true` still returns it.
- **`get_knowledge`** search skips the "Contents of the library file" index entry,
  which matched almost every query and filled most of the answer.
- **`post_activity_comment`** is recorded in the ledger like the other changes.
- **`python engine/build_state.py --athlete <id>`** runs on its own again.
- Small text fixes: the validator prints its real version (3.1), `server.py` counts
  19 tools, two config headers no longer say "not yet consumed".
- **Deploy:** restart Claude Desktop (the MCP server code changed). Nothing to
  change in the Project.

## How the system is used

1. **Primary path — Claude Desktop + `infame-coach` MCP server.** Open a chat
   in the Claude Project and name the athlete. The coach calls the tools
   itself: `get_athlete_state` (brings `#STATE`, `continuity`, `race_notes`),
   `get_athlete_profile`, then per week `save_block` → `validate_block` →
   `push_block` dry-run → head coach approves → live `push_block`.
   `save_continuity` / `save_race_result` whenever it emits those blocks.
2. **Fallback — only if the server is down:** `python coach.py prep <id>`,
   attach the files, `python coach.py check <file>`, upload by hand.

## What the Project must contain

- **Instructions:** the full text of `Prompt/infame_elite_endurance_coach.md` (v7.27).
- **Knowledge files (flat, no folders):** `generated/Simple_Table_Cycling_Training_Zones.md`,
  `generated/Simple_Table_Running_Training_Zones.md`, `generated/Session_Architectures.md`,
  `generated/Language_Guide_es-MX.md`, `generated/Cycling_Doctrine.md`,
  `generated/Running_Doctrine.md`, `Syntax/Intervals Workout Builder Syntax.md`,
  `config/athletes/ATHLETE_INTAKE.md`, `config/athletes/_template.yaml`.
- **Not in the Project:** every book KB (`Knowledge/Principles/*.md`, the Palladino file) —
  the coach reads them with `get_knowledge`. Nothing from `Knowledge/Catalogs/`, `tests/` or
  other `config/` files either.

## Machines

- Laptop: `C:\Dev\Github\infame_elite_endurance_coach` · PC: `E:\Dev\github\infame_elite_endurance_coach`.
- `config/athletes/`, `data/`, `out/` are junctions to Google Drive (never in git).
- The MCP server runs from `.venv-mcp/` on each machine (Claude Desktop config per machine).

## Open items

- **Privacy:** athlete files were removed from the whole git history on 2026-10-02
  (`git filter-repo`). Never commit `out/`, `data/` or `config/athletes/<id>.yaml`; they live
  in Google Drive through junctions. A local `coach_BACKUP.git` on the PC still holds the old
  history: delete it once it is no longer needed.
- `push_block` does not delete workouts already planned on those dates;
  the coach names them and the head coach removes them.
- `coach.py review` has no tool yet.
- Knowledge layer plan (audit of 2026-10-02): complete. Every new book goes to
  `Knowledge/Principles/` and is reached with `get_knowledge`; never upload books to the Project.
