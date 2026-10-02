# RESTORE POINT — Infame Elite Endurance Coach v7.14

**Date frozen:** 2026-10-02
**Previous:** `archive/RESTORE_POINT_v7.13.md` (older ones in `archive/`)
**Tests:** `python tests/run_tests.py` → 651/651 · `python tests/test_mcp_server.py` → 156/156 (needs `mcp`)

## What changed in v7.14

- **Power-duration diagnosis in `#STATE`** (`engine/pd_diagnosis.py`, `config/pd_diagnosis.yaml`):
  TTE at FTP, Coggan Level 5 and 6 windows, best 20 min as % of FTP, Pmax, W′ setting and the
  CTL ramp band (Coggan Table 9.2) — measured curve values, no fitted model. Indoor and outdoor
  are separate tables, each against its own FTP (`indoor_ftp` for indoor rides).
- **Fetcher** stores ~85 dense curve points per window, plus indoor and outdoor power curves
  (`curves.power_indoor`, `curves.power_outdoor`) through the power page's `filters` parameter
  (not in the published API docs; verified 2026-10-02).
- **Declared profile:** `history.training_age_years` (template + intake 6.0) sets the ramp band.
- **Prompt:** Engine Contract row for the diagnosis.
- **New MCP tool `save_training_age(athlete_id, years)`:** the coach asks the training age once
  when the block says it is missing and saves it to `data/<id>/facts.json`; the engine reads it
  (a value in the declared profile still wins). No file editing by the head coach.

## Earlier: v7.13

- Cycling Doctrine (`config/doctrine/cycling.yaml` → `generated/Cycling_Doctrine.md`), prompt
  Doctrine section, time-crunched mode on request only, `friel_running` reference only, Coggan
  KB re-extracted in the tagged format. History rewritten 2026-10-02 to remove athlete data.

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

- **Instructions:** the full text of `Prompt/infame_elite_endurance_coach.md` (v7.14).
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

- **Privacy:** athlete files were removed from the whole git history on 2026-10-02
  (`git filter-repo`). Never commit `out/`, `data/` or `config/athletes/<id>.yaml`; they live
  in Google Drive through junctions. A local `coach_BACKUP.git` on the PC still holds the old
  history: delete it once it is no longer needed. The laptop copy must be re-synced
  (`git fetch` + `git reset --hard origin/main`) before its next commit.
- `push_block` does not delete workouts already planned on those dates;
  the coach names them and the head coach removes them.
- Writing `config/athletes/<id>.yaml` after an intake is still by hand (no tool).
- `coach.py review` has no tool yet.
- Knowledge layer plan (audit of 2026-10-02): running
  restructure (one Hansons, Palladino split and spine, trail rule); Running Doctrine after the
  Daniels and Koop re-extractions; Mujika and Training for the Uphill Athlete pending;
  `get_knowledge` MCP tool to move book KBs out of the Project.
