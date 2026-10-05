# RESTORE POINT — Infame Elite Endurance Coach v7.21

**Date frozen:** 2026-10-04
**Previous:** `archive/RESTORE_POINT_v7.20.md` (older ones in `archive/`)
**Tests:** `python tests/run_tests.py` → 687/687 · `python tests/test_mcp_server.py` → 163/163 (needs `mcp`)

## What changed in v7.21

- **Race demand record.** Each goal in `config/athletes/<id>.yaml` can carry `demand`, one
  entry per race day (`day`, `discipline`, `distance_km`, `climb_m`, `expected_hours`,
  `terrain`), and `demand_source`. The coach fills it for every A-level goal and stage race
  (asking the head coach or reading the official route, never estimating), in Phase 1 and
  before Pass 1 of a continuing macrocycle. Idea taken from Prova Endurance (SetRaceDemand).
- **The validator shows the plan beside the race.** `engine/race_demand.py` (new) +
  `verify/validate_block.py` 2.7: a "Race demand" section after each run — longest session
  per discipline vs the longest race day, consecutive training days vs race days, and a note
  that climbing is not compared (cards carry no elevation). Information only: never warns,
  never blocks. `build_profile.py` flags a malformed demand record or a missing source.
- **Deploy:** re-paste the prompt into the Project instructions; replace `ATHLETE_INTAKE.md`
  and `_template.yaml` in the Project knowledge; restart Claude Desktop.

## Earlier: v7.20

- **Every session says why, and what that rests on.** Two new card fields. `[Why]` is one
  sentence in the athlete's language (why this session, for this athlete, now); it is uploaded
  to Intervals.icu above `[Execution]` as "Por qué:" / "Why:". `[Source]` is coach-only and
  never uploaded: KB entry IDs (Principles `DRF-C06-004`, Catalogs `TRPM-L2-014`), `§N` of the
  active methodology's file, and/or `coach judgement`. The Pass 1 design table gains a Source
  column; Pass 2 transcribes it. Idea taken from Prova Endurance (every session cites a source
  or says it is judgement).
- **The validator checks citations exist.** `verify/validate_block.py` 2.6: CHK-SRC warnings
  (never blocks) for a missing `[Why]` or `[Source]`, a source with no ID / §N / judgement, an
  entry ID not found anywhere in `Knowledge/`, or a §N not in the methodology's file. Spanish
  labels `[Por qué]` and `[Fuente]` are translated. `[Why]` joins the Spanish language check.
- **Deploy:** re-paste `Prompt/infame_elite_endurance_coach.md` into the Project instructions,
  and restart Claude Desktop so the MCP server loads the new `tools_push.py`.

## Earlier: v7.19

- **Provisional threshold limits load, never variety.** The rule from v7.10 (no work above
  Endurance, Endurance steps in the lower half) had become the cause of flat sessions once the
  power-duration block (v7.14) started flagging thresholds as provisional. Now it limits only
  sustained work above Endurance and long continuous steps; sessions keep their variety from
  stimuli that do not depend on an exact threshold (Endurance blocks at different points,
  progressive builds, 1–2 min touches, strides and sprints ≤ 30 s by RPE, cadence, terrain).
- **Catalogs are the source of session ideas.** `get_knowledge(…, catalog=true)` reads each
  author's catalog (worked sessions, workouts, plans; IDs like `TRPM-L2-014`). Before Pass 1
  the coach gathers worked sessions from the catalogs and the architecture library, takes the
  idea and the structure, and rebuilds every number for the athlete. Until v7.18 the catalogs
  were unreachable ("never loaded, never a menu").
- **A correction is checked before it is announced.**
- **Stored designs are a record, not a lock:** session designs saved in `#SESSION` Notes are
  re-read against current criteria before each week is written, and redesigned when they no
  longer fit.

## Earlier: v7.18

- **New MCP tool `save_declared_profile(athlete_id, yaml_text, dry_run, confirm)`:** the coach
  writes `config/athletes/<id>.yaml` itself — after an intake or any approved change — behind
  the write gate (dry run with a diff, plain-words summary, approval, save). It checks the
  YAML, the template's sections and the names the system recognizes, and keeps the previous
  version in `data/<id>/profile_history/`. The head coach no longer saves a yaml by hand.
- **Prompt (same version):** a preference about degree ("not too much X") means rebalancing,
  never removing X; cadence work stays a legitimate modifier — variety comes from adding
  variables, not from dropping cadence.

## Earlier: v7.17

- **Prompt, from the first real use (2026-10-03):** three coaching-judgement principles —
  the head coach's input is a criterion applied with judgement, not a rule, and is recorded in
  `#SESSION` as a criterion with its reason; weekly TSS/hour targets are a guide that follows
  from well-designed sessions, never a quota (no trimmed warm-ups, odd durations or filler to
  hit a number); warm-up and cool-down proportionate to the session (brief in short sessions,
  longer as durations and intensities grow).

## Earlier: v7.16

- **Book knowledge on demand.** New MCP tool `get_knowledge(source, refs, query, max_entries)`
  (`engine/knowledge.py`): exact entries by ID (`TRPM-C06-019`) or section (`§7`), keyword
  search inside one source or all, or a source's table of contents. Principles only; answers
  capped. **The book KBs leave the Claude Project**: it now holds only the generated tables,
  doctrines, architectures, language guide, syntax and the intake files (~0.2 MB instead of
  ~3 MB).
- **Mujika** re-extracted (tagged) and now governs the taper in both doctrines (v1.1).
- **Prompt:** tools table, Inputs, "Project files and book knowledge", doctrine and fallback
  wording; zone-table headers and `profile.md` name `get_knowledge` instead of Project files.

## Earlier: v7.15

- **Running Doctrine** (`config/doctrine/running.yaml` → `generated/Running_Doctrine.md`): 12
  decisions, Palladino as spine, Daniels road, Koop trail/ultra, Uphill Athlete vertical and
  strength; Hansons (the goal event picks the book), Hudson, Rosario, Olbrich refine; Run Less,
  Run Faster as the time-crunched runner mode, on request only.
- **Doctrine schema v1.1:** sources in the older numbered format are cited by section (`§N`);
  the build checks each `## N.` heading exists.
- **KBs:** Daniels (4th ed.) and Koop (2nd ed.) re-extracted in the tagged format; Training for
  the Uphill Athlete added as Koop's companion.
- **Prompt:** running methodology choice rules (Daniels default, Hansons by goal event,
  Palladino with a run power meter, Koop default on trail, Olbrich for flat road ultras only).

## Earlier: v7.14

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

- **Instructions:** the full text of `Prompt/infame_elite_endurance_coach.md` (v7.19).
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
  history: delete it once it is no longer needed. The laptop copy must be re-synced
  (`git fetch` + `git reset --hard origin/main`) before its next commit.
- `push_block` does not delete workouts already planned on those dates;
  the coach names them and the head coach removes them.
- `coach.py review` has no tool yet.
- Knowledge layer plan (audit of 2026-10-02): complete. Every new book goes to
  `Knowledge/Principles/` and is reached with `get_knowledge`; never upload books to the Project.
