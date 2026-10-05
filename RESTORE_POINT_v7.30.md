# RESTORE POINT — Infame Elite Endurance Coach v7.30

**Date frozen:** 2026-10-05
**Previous:** v7.29 — every version is in `CHANGELOG.md`; older restore points are in the git history
**Prompt:** `Prompt/infame_elite_endurance_coach.md` v7.30
**Tests:** `python tests/run_tests.py` → 758/758 · `.venv-mcp\Scripts\python.exe tests/test_mcp_server.py` → 172/172

## What changed in v7.30

Batch 3 of the 2026-10-05 audit: the prompt no longer contradicts the engine or itself.
Prompt and its tests only; no engine code, number or check changed.

- **One source for the opening state.** Phase 2 no longer carries its own TSB bands
  (they said TSB −12 is "fatigued, open with a recovery week" while the engine reads it
  as `load_pressure` / `load_accepting`). The coach starts from `#STATE`'s Resolved state:
  `load_accepting` → progressive loading, `recovery_priority` → a recovery week.
- **Catalogs are allowed everywhere.** The Inputs table said "principles only, never
  catalogs" while Session Design asks for `get_knowledge(catalog=true)`.
- **`friel_running` is out of the `[Methodology]` list.** It stays a zone reference only,
  as the declared-profile rules already said.
- **No version-history notes** inside the prompt (the Supra-threshold line).
- **Deploy:** paste the whole prompt into the Project instructions. No file changes in the
  Project knowledge; no restart needed.

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

- **Instructions:** the full text of `Prompt/infame_elite_endurance_coach.md` (v7.30).
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
