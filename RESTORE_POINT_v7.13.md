# RESTORE POINT — Infame Elite Endurance Coach v7.13

**Date frozen:** 2026-10-02
**Previous:** `archive/RESTORE_POINT_v7.12.md` (older ones in `archive/`)
**Tests:** `python tests/run_tests.py` → 626/626 · `python tests/test_mcp_server.py` (needs `mcp`)

## What changed in v7.13

- **Cycling Doctrine.** `config/doctrine/cycling.yaml` (schema `config/schema/doctrine.schema.json`)
  names, for 13 cycling decisions, the one source that governs and the sources that refine it,
  with KB entry IDs. `python build_zone_tables.py validate` checks every ID exists;
  `build` writes `generated/Cycling_Doctrine.md`.
- **Prompt.** New `Doctrine` section: doctrine statements are attributed to "Infame doctrine"
  and are the only exception to the one-author rule. New `Time-crunched mode (cycling)`: on
  request only, Coggan/Friel zones, Carmichael structure. `friel_running` is reference only:
  never declared, chosen or prescribed.
- **Coggan KB** re-extracted in the C01-C18 tagged format (`TRPM-…` IDs).

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

- **Instructions:** the full text of `Prompt/infame_elite_endurance_coach.md` (v7.13).
- **Knowledge files:** `generated/Simple_Table_Cycling_Training_Zones.md`,
  `generated/Simple_Table_Running_Training_Zones.md`, `generated/Session_Architectures.md`,
  `generated/Language_Guide_es-MX.md`, `generated/Cycling_Doctrine.md`, every
  `Knowledge/Principles/*.md` (includes both Friel books: `Friel_Cyclists_Training_Bible.md` and `Friel_High_Performance_Cyclist.md`, and Tim Cusick's `Cusick_WKO_Coaching_Webinars.md`, a different-author companion of Coggan and Friel cycling),
  `Knowledge/Steve_Palladino_Running_with_Power.md`,
  `Syntax/Intervals Workout Builder Syntax.md`,
  `config/athletes/ATHLETE_INTAKE.md`, `config/athletes/_template.yaml`.
  Nothing from `Knowledge/Catalogs/`, `tests/` or other `config/` files.
  All files flat at the root of the Project, no folders.

## Machines

- Laptop: `C:\Dev\Github\infame_elite_endurance_coach` · PC: `E:\Dev\github\infame_elite_endurance_coach`.
- `config/athletes/`, `data/`, `out/` are junctions to Google Drive (never in git).
- The MCP server runs from `.venv-mcp/` on each machine (Claude Desktop config per machine).

## Open items

- **Privacy:** real athlete files (`out/…/state.md`, `profile.md`) remain in git history
  before 2026-09-04. While that history exists the repo must be **private**; making it public
  again requires rewriting history first.
- `push_block` does not delete workouts already planned on those dates;
  the coach names them and the head coach removes them.
- Writing `config/athletes/<id>.yaml` after an intake is still by hand (no tool).
- `coach.py review` has no tool yet.
- Knowledge layer plan (audit of 2026-10-02): power-duration block in `#STATE`; running
  restructure (one Hansons, Palladino split and spine, trail rule); Running Doctrine after the
  Daniels and Koop re-extractions; Mujika and Training for the Uphill Athlete pending;
  `get_knowledge` MCP tool to move book KBs out of the Project.
