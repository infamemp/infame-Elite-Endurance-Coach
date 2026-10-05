# RESTORE POINT — Infame Elite Endurance Coach v7.29

**Date frozen:** 2026-10-05
**Previous:** v7.28 — every version is in `CHANGELOG.md`; older restore points are in the git history
**Prompt:** `Prompt/infame_elite_endurance_coach.md` v7.27 (unchanged in v7.28 and v7.29)
**Tests:** `python tests/run_tests.py` → 754/754 · `.venv-mcp\Scripts\python.exe tests/test_mcp_server.py` → 172/172

## What changed in v7.29

Batch 2 of the 2026-10-05 audit: the critical fixes. Each one has its own test.

- **HC-ATHLETE — no athlete, no PASS.** `verify/validate_block.py` 3.2 blocks a session
  whose card has no `[Athlete ID]`, an id with no `config/athletes/<id>.yaml`, or an id
  different from the athlete the run is for (`--athlete`). Before, a missing or mistyped
  id loaded an empty profile in silence: injury restrictions (HC-LIMIT), metric overrides
  and equipment were never checked and the block was reported upload-safe.
  `--skip-athlete-check` exists for the test fixtures only; the MCP tools never pass it.
- **`push_block` never uploads to the wrong athlete.** It refuses a file with a card for
  another athlete (the dry run too), and its pre-upload validation now runs for the
  athlete it uploads to.
- **Importing the engine no longer ends the process.** `fetch_athlete_data.py` checks
  `ICU_API_KEY` when it connects (`make_session`), not at import. The MCP tests run
  with no key set.
- **Stable `external_id`.** The week is always two digits (`[Week] 3` and `[Week] 03`
  both give `w03`), so a corrected re-push updates the same events.
- **The week just saved stays the latest.** The validator keeps a block file's
  modification time when it fills TSS or auto-corrects it, so `validate_block` and
  `push_block` without `file_path` never pick an older week that was re-validated.
- The test athlete `TESTRAMP` now declares a smart trainer and the `trainer`
  discipline, so the MCP tests can validate a cycling block for a real profile.
- **Deploy:** restart Claude Desktop (the MCP server and validator changed). Nothing to
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
