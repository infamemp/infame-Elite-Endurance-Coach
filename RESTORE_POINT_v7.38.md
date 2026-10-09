# RESTORE POINT — Infame Elite Endurance Coach v7.38

**Date frozen:** 2026-10-08
**Previous:** v7.37 — every version is in `CHANGELOG.md`; older restore points are in the git history
**Prompt:** `Prompt/infame_elite_endurance_coach.md` v7.37 (unchanged in v7.38)
**Tests:** `python tests/run_tests.py` → 858/858 · `.venv-mcp\Scripts\python.exe tests/test_mcp_server.py` → 196/196

## What changed in v7.38 — load as Intervals.icu computes it

Session TSS now follows the method Intervals.icu uses for each target, measured against
the loads it stored for real planned workouts: Normalized Power for cycling power (largest
gap 1.0 TSS on 74 sessions, was 11 and always low on intervals), HRSS for heart rate (was
up to twice the stored load), and the per-step IF² unchanged for running pace and power
(already within 1 TSS). `push_block` checks every uploaded session against the load
Intervals.icu computed and reports differences beyond 2 TSS (`load_check`, also in the
ledger). Details in `CHANGELOG.md` and `engine/planned_load.py`.

- **Deploy:** restart Claude Desktop. The Project does not change.

## What changed in v7.35–v7.37 — aerobic variety

Aerobic sessions were caged in their zone: the hardest step named a session's class, so any
touch of tempo turned an aerobic ride into a "tempo session", and the coach kept them flat.

- **v7.35/v7.36 — engine.** A session's class is the purpose declared first in `[Zone]`
  (English or Spanish); without it, where the load sits. Harder minutes are **touches**, in
  every class; the validator lists them and warns with `CHK-PURPOSE` when most of the load
  sits in a harder class than the one declared.
- **v7.36 — library.** Aerobic shapes (`steady_aerobic`, was `endurance_cadence`;
  `aerobic_touches`; `rolling_aerobic`; progressions on the bike), `technique_drills` as its
  own category on request, `surges_on_base` and `hard_start_fading` for tempo and sweet
  spot. Built from a re-analysis of the 1,694 library workouts and the KB authors; every
  shape cites its sources. No limits on touches anywhere.
- **v7.37 — prompt and doctrine.** The prompt's "A session's purpose and its touches"
  (criteria, not rules), a `session_purpose_and_touches` row in both doctrines (cycling
  governed by Allen & Coggan, running by Palladino), Spanish terms (toques, arranques,
  cambios de ritmo, técnica de pedaleo / de carrera).
- **Deploy:** paste the prompt into the Project's Instructions; replace the three knowledge
  files `Cycling_Doctrine.md`, `Running_Doctrine.md`, `Language_Guide_es-MX.md`; restart
  Claude Desktop.

## What changed in v7.34

`HC-ATHLETE` now tells you to check the `config/athletes` link to Drive when a profile is
missing; `manual/GUIDE.md` has the link check and the repair. Nothing else changed.
Deploy: restart Claude Desktop. The Project does not change.

## What changed in v7.33

Batch 6 of the 2026-10-05 audit: the base for the web interface. No training rule and no
number changed — the golden outputs are identical.

- **`engine/shared.py`** — one copy of what every module repeated: date parsing, the
  sport of an activity type, folder names, and the config reader (each file read once,
  read again only when it changes on disk).
- **The engine no longer ends the process.** Missing data, a missing config file or an
  unknown methodology raise `EngineError`; the command line still prints the same message
  and exits 1, and the MCP tools report it as `error_type: EngineError`.
- **The validator's result as data:** `validate_block.parse_report()` gives `passed`, the
  sessions and every finding (severity, code, line, message).
- **`services/`** — the engine as plain functions for scripts and the coming interface (the
  same functions the MCP tools run), plus `ledger` and `athlete_files`.
- **Athlete folders found by id.** `out/<name>/` keeps its name and gets an
  `athlete_id.txt` marker the first time it is used; a renamed athlete keeps the same
  folder, and two athletes with the same name get `<name>_<id>`. A typo in an id writes
  nothing (before, it created an empty folder).
- **git and Google Drive separated.** `config/athletes/` is no longer in git at all. The
  template and the intake script moved to `config/templates/`; the test athlete to
  `tests/profiles/`, copied in for each test run and taken out after. The test runs no
  longer leave `_test_*.yaml` files in the synced folder.
- `config/decision_thresholds.yaml` has a section index at the top (which section, what
  it governs, which code reads it). It was not split: the doctrines and the prompt cite it
  by name.
- **Documentation:** a short `README.md`, `ROADMAP.md` (replaces `IMPROVEMENT_BACKLOG.md`)
  and `manual/GUIDE.md`, one page (replaces `OPERATIONS_MANUAL.md` and `QUICK_GUIDE.md`).
- **Deploy:** restart Claude Desktop. The Project does not change (same prompt, same files).

## How the system is used

1. **Primary path — Claude Desktop + `infame-coach` MCP server.** Open a chat
   in the Claude Project and name the athlete. The coach calls the tools
   itself: `get_athlete_state` (brings `#STATE`, `continuity`, `race_notes`),
   `get_athlete_profile`, then per week `save_block` → `validate_block` →
   `push_block` dry-run → head coach approves → live `push_block`.
   `save_continuity` / `save_race_result` whenever it emits those blocks.
2. **Fallback — only if the server is down:** `manual/GUIDE.md` §3.

## What the Project must contain

- **Instructions:** the full text of `Prompt/infame_elite_endurance_coach.md` (v7.37).
- **Knowledge files (flat, no folders):** `generated/Cycling_Doctrine.md`,
  `generated/Running_Doctrine.md`, `generated/Language_Guide_es-MX.md`,
  `Syntax/Intervals Workout Builder Syntax.md`.
- **Read with `get_reference`, not in the Project (v7.31):** the two zone tables
  (`generated/Simple_Table_*_Training_Zones.md`), `generated/Session_Architectures.md`,
  `config/templates/ATHLETE_INTAKE.md`, `config/templates/profile_template.yaml`.
- **Not in the Project:** every book KB (`Knowledge/Principles/*.md`, the Palladino file) —
  the coach reads them with `get_knowledge`. Nothing from `Knowledge/Catalogs/`, `tests/` or
  other `config/` files either.

## Machines

- Laptop: `C:\Dev\Github\infame_elite_endurance_coach` · PC: `E:\Dev\github\infame_elite_endurance_coach`.
- `config/athletes/`, `data/`, `out/` are junctions to Google Drive (never in git).
- The MCP server runs from `.venv-mcp/` on each machine (Claude Desktop config per machine).

## Open items

- **Privacy:** athlete files were removed from the whole git history on 2026-10-02
  (`git filter-repo`). Never commit `out/`, `data/` or `config/athletes/`; they live
  in Google Drive through junctions. A local `coach_BACKUP.git` on the PC still holds the old
  history: delete it once it is no longer needed.
- The rest, and what comes next (the web interface), is in `ROADMAP.md`.
