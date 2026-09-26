# RESTORE POINT — Infame Elite Endurance Coach v7.6

**Date frozen:** 2026-09-26
**Previous:** `archive/RESTORE_POINT_v7.0.md` (older ones in `archive/`)
**Tests:** `python tests/run_tests.py` → 409/409 · `python tests/test_mcp_server.py` → 76/76 (needs `mcp`)

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

- **Instructions:** the full text of `Prompt/infame_elite_endurance_coach.md` (v7.6).
- **Knowledge files:** `generated/Simple_Table_Cycling_Training_Zones.md`,
  `generated/Simple_Table_Running_Training_Zones.md`, `generated/Session_Architectures.md`, every
  `Knowledge/Principles/*.md`, `Knowledge/Joe_Friel_cyclists_training_bible_knowledge_base.md`,
  `Knowledge/Steve_Palladino_Running_with_Power.md`,
  `Syntax/Intervals Workout Builder Syntax.md`,
  `config/athletes/ATHLETE_INTAKE.md`, `config/athletes/_template.yaml`.
  Nothing from `Knowledge/Catalogs/`, `tests/` or other `config/` files.

## Machines

- Laptop: `C:\Dev\Github\infame_elite_endurance_coach` · PC: `E:\Dev\github\infame_elite_endurance_coach`.
- `config/athletes/`, `data/`, `out/` are junctions to Google Drive (never in git).
- The MCP server runs from `.venv-mcp/` on each machine (Claude Desktop config per machine).

## Open items

- First real upload with the v7.3 date fix: confirm in Intervals.icu that
  the sessions land on the right dates.
- `push_block` does not delete workouts already planned on those dates;
  the coach names them and the head coach removes them.
- Writing `config/athletes/<id>.yaml` after an intake is still by hand
  (no tool).
- `coach.py review` has no tool yet.
- Knowledge gaps: Friel running has no KB of its own (uses the cycling
  one); Koop Catalog is nearly empty; Seiler / polarized distribution not
  modeled; Bosquet and Ingham KBs pending.
- Real athlete data (`out/…/state.md`, `profile.md`) exists in git history
  before 2026-09-04: the repo must stay **private**.
