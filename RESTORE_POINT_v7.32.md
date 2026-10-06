# RESTORE POINT — Infame Elite Endurance Coach v7.32

**Date frozen:** 2026-10-06
**Previous:** v7.31 — every version is in `CHANGELOG.md`; older restore points are in the git history
**Prompt:** `Prompt/infame_elite_endurance_coach.md` v7.32
**Tests:** `python tests/run_tests.py` → 765/765 · `.venv-mcp\Scripts\python.exe tests/test_mcp_server.py` → 179/179

## What changed in v7.32

Batch 5 of the 2026-10-05 audit: the data the coach plans on stays complete and true.

- **A failed download never replaces good data.** Intervals.icu answers that hit a rate
  limit (429), a server error (5xx) or a dropped connection are retried twice. The
  athlete's core data — profile, wellness and PMC, activities, planned and recent events —
  is no longer optional: if it cannot be read, the fetch fails and the previous
  `athlete_data.json` stays as it was (before, empty lists replaced it and the athlete
  looked untrained). The file is written whole or not at all.
- **`list_roster` reads the account live** (one call) and rewrites `out/roster.md`, so an
  athlete added on Intervals.icu is found without `coach.py prep`. If Intervals.icu cannot
  be read, it returns the last saved roster and says so.
- **The PMC projection after an upload.** A week this system uploaded is a written plan:
  its days without an event count as rest (zero), not as the weekday average. Before, the
  projected race-morning TSB came out too low once a week was uploaded.
- **Plan checks see the weeks already uploaded.** The validator reads the athlete's
  planned `infame-` events back from the cached data (their steps are classed with the
  sport's cutpoints; their planned load is Intervals.icu's) and gives them to the plan
  checks as context. The taper is judged across an uploaded week and the file in hand,
  and two hard days across a week boundary are caught. Warnings are still only about the
  days this file writes.
- **Hours per sport in `#STATE`** ("Recent volume": last 7 days and the weekly average of
  the last 4 weeks). The prompt reads them from there instead of adding them up by hand.
- **GitHub Actions** runs both test suites on every push (`.github/workflows/tests.yml`).
- Planned events now keep their `id`, `external_id` and `description` in
  `athlete_data.json`; the first `get_athlete_state` with `force_refresh=true` brings them.
- **Deploy:** paste the prompt into the Project instructions; restart Claude Desktop.

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

- **Instructions:** the full text of `Prompt/infame_elite_endurance_coach.md` (v7.32).
- **Knowledge files (flat, no folders):** `generated/Cycling_Doctrine.md`,
  `generated/Running_Doctrine.md`, `generated/Language_Guide_es-MX.md`,
  `Syntax/Intervals Workout Builder Syntax.md`.
- **Read with `get_reference`, not in the Project (v7.31):** the two zone tables
  (`generated/Simple_Table_*_Training_Zones.md`), `generated/Session_Architectures.md`,
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
