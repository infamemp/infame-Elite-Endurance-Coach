# Changelog — Infame Elite Endurance Coach

Newest first. One entry per version. The full handoff documents of each version
(`RESTORE_POINT_v*.md`) and every earlier prompt live in the git history:
`git log --all -- archive/` lists them, and `git show <commit>:<path>` prints one.

## v7.33 (2026-10-06)

Batch 6 of the 2026-10-05 audit: the base for the web interface. No training rule and no
number changed — the golden outputs are identical.

- **`engine/shared.py`:** one copy of the date parsers (there were eight), the sport of an
  activity type (three), the athlete folder rule (two) and the config reader (each file
  read once, again only when it changes on disk; every caller gets its own copy).
- **No `sys.exit` in the engine's functions.** Missing data, a missing config file or an
  unknown methodology raise `EngineError`. The command line prints the same message and
  exits 1; the MCP guard reports `error_type: EngineError` without a traceback.
- **`validate_block.parse_report()`:** the validator's result as data (`passed`, sessions
  with computed TSS and duration, findings with severity, code, line and message).
- **`services/`:** the engine as plain functions for scripts and the interface — the same
  functions the MCP tools run — plus `ledger` and `athlete_files`. `services.validate`
  adds the structured `summary`.
- **Athlete folders by id:** `out/<name>/` gets an `athlete_id.txt` marker; a renamed
  athlete keeps the folder, a same-name athlete gets `<name>_<id>`, and an unknown id
  writes nothing.
- **git out of the Google Drive folder:** `config/athletes/` is ignored as a whole.
  `_template.yaml` → `config/templates/profile_template.yaml`, `ATHLETE_INTAKE.md` →
  `config/templates/`, `TESTRAMP.yaml` → `tests/profiles/` (copied in for each test run,
  taken out after). The test runs also remove their `_test_*.yaml` profiles.
- **`config/decision_thresholds.yaml`:** section index at the top; not split, because the
  doctrines and the prompt cite it by name.
- **Documentation:** short `README.md`; `ROADMAP.md` replaces `IMPROVEMENT_BACKLOG.md`;
  `manual/GUIDE.md` (one page) replaces `OPERATIONS_MANUAL.md` and `QUICK_GUIDE.md`.

## v7.32 (2026-10-06)

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

## v7.31 (2026-10-05)

Batch 4 of the 2026-10-05 audit: fewer tokens per conversation, no rule removed.
`python tests/context_budget.py` measures what a conversation loads before any design
work: **~57,400 tokens in v7.30 → ~33,100 in v7.31 (−42%)**.

| Part | v7.30 | v7.31 |
| :--- | ---: | ---: |
| Project instructions (prompt) | ~19,300 | ~18,800 |
| Project knowledge files | ~31,400 (9 files) | ~8,700 (4 files) |
| MCP tool definitions | ~5,400 (19 tools) | ~4,400 (20 tools) |
| `get_athlete_state` (test athlete) | ~1,200 | ~1,200 |

- **New tool `get_reference`** (`engine/reference.py`): the zone tables, the architecture
  library, the intake script and the profile template leave the Project. The coach asks
  for one methodology's zone table (~1,500 tokens instead of ~13,000 for both tables),
  and for the architectures that fit a session's class and discipline.
- **Tool descriptions written for the model.** Each says what the tool does, when to use
  it and what it returns; the development history moved to code comments.
- **`get_knowledge` answers default to 6 KB** (`max_chars` up to 12 KB when needed).
- **Prompt:** the tools table is one line per tool (the details live in each tool's
  description); the validator section says once that `HC-`/`SYN-` codes block and
  `CHK-` codes warn, instead of listing every check; every reference to the files that
  left the Project points to `get_reference`, with a fallback for when the tools are down.
- **`tests/context_budget.py`** (new) for before/after measurements.

## v7.30 (2026-10-05)

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

## v7.29 (2026-10-05)

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

## v7.28 (2026-10-05)

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

## v7.27 (2026-10-05)

- **As planned / done differently.** `engine/execution.py` labels every paired session
  `as_planned` or `done_differently`, with the reasons: shorter or longer, lighter or heavier
  than planned (outside 80–120%), Intervals.icu compliance under 70%, or another sport. Limits
  in `heads_up.adherence` of `config/decision_thresholds.yaml` (coach judgement). `get_execution`
  shows the label in its table and totals; the Heads-up lists sessions done differently in the
  last 7 days, so the next week is designed from what was done. The roster already flags quiet
  athletes (days since the last activity). Idea taken from Prova Endurance (fulfilment per
  session).

## v7.26 (2026-10-05)

- **Ledger.** `engine/ledger.py` (new) appends one JSON line per event to
  `config/athletes/ledger/<athlete_id>.jsonl` — next to the declared profiles, so it travels
  between computers; never committed (`.gitignore`). Recorded automatically: every
  `validate_block` run (result, number of sessions, every FAIL/WARN code it printed),
  `update_threshold` (old → new), `push_block` (dates, sessions, whether validation was
  overridden), `remove_block`, `save_declared_profile` (sections changed), `save_continuity`
  (active phase, falsifier, review date), `save_race_result`, `save_training_age`. Best effort:
  a failed write never breaks a tool. `INFAME_NO_LEDGER=1` switches it off (the tests do).
- **Where it shows.** `get_athlete_state` returns `ledger` (last 30 days). `python coach.py ledger`
  prints every athlete: first-try pass rate per block file, runs to pass, most frequent
  failures — the evidence for deciding on schema-first sessions (row 9). Idea taken from Prova
  Endurance (decision history).

## v7.25 (2026-10-05)

- **Plan checks on the week as a whole.** `engine/plan_checks.py` (new) +
  `verify/validate_block.py` 3.0 print a "Plan checks" section after each run, beside the
  athlete's real activities: `CHK-SPACING` (two hard days with no easier day between —
  CTB-C05-035), `CHK-RAMP` (a sport's planned week vs its last 4 real weeks, above 1.3×),
  `CHK-RECOVERY` (more than 3 loading weeks in a row with no week ≥20% lighter — CTB-C08-026),
  `CHK-EASY` (under 70% of written time in recovery/endurance — HPC-C08-004), `CHK-TAPER`
  (volume cut outside 21–60%, frequency below 80%, or no hard day — TPOP-C09-022,
  TPOP-C04-044, TPOP-C09-006). All warn, never block. Values in `plan_checks` of
  `config/decision_thresholds.yaml` (new section).
- **Per-athlete exceptions.** `plan_checks` in `config/athletes/<id>.yaml` overrides any value or
  switches a check off (`off: [...]`), with a `reason` printed beside it.
- A future day the file does not cover is never counted as zero: the taper is only judged when
  the file reaches the race. Idea taken from Prova Endurance (JudgePlanDraft and its rules).

## v7.24 (2026-10-05)

- **Injury restrictions are checked.** `limitations.restrictions` in `config/athletes/<id>.yaml`
  (new field, in `_template.yaml`): one entry per restriction with `what`, `source`, `from`,
  `until`, `sport`, `disciplines` and the limits that were stated — `max_minutes`, `max_class`,
  `max_sessions_per_week`, `no_consecutive_days`, `avoid_architectures`.
- **What happens.** `engine/restrictions.py` (new). `verify/validate_block.py` 2.9 blocks a
  session that breaks a precise limit (`HC-LIMIT`: duration, class at the top of each step's range
  in the author's table, sessions per week and consecutive days in the file) and warns on a shape
  to avoid (`CHK-LIMIT`, the architecture is read by a heuristic). An active restriction is the
  first Heads-up line in `#STATE`. `build_profile.py` flags malformed or ended restrictions.
  `ATHLETE_INTAKE.md` 3.1 tells the coach to record the stated limits. Prova Endurance does not
  have this.
  `_template.yaml` in the Project knowledge; restart Claude Desktop.

## v7.23 (2026-10-05)

- **Core sessions per discipline.** `config/core_sessions.yaml` (new) lists, per race
  discipline, the few session types a race cannot be prepared without, each with its reason
  and KB source (road: sustained threshold, VO2max, sprint · MTB: repeated surges, VO2max,
  sustained climbing · gravel · road run · trail run · track). Checked only from 12 weeks before
  the next A goal (base work is general — CTB-C02-025, HPC-C08-005). Idea taken from Prova
  Endurance (archetypes tagged as core per discipline).
- **Where it shows.** `engine/core_sessions.py` (new). `#STATE` gets a "CORE SESSIONS" table
  (last date each was prescribed, from the last 3 weeks of saved sessions).
  `verify/validate_block.py` 2.8 prints a "Core sessions" section and `CHK-CORE` for each one
  missing from the block and the last 3 weeks. Warns only, never blocks; a deliberate omission
  is a valid answer.

## v7.22 (2026-10-04)

- **Every block states what would show it wrong.** Pass 1 now opens with three lines the head
  coach approves with the design table: Hypothesis, Would show wrong (one observable result
  `#STATE`, an activity or a race can show) and Review on (a date). `#SESSION` carries
  `Would Show Wrong`, `Review On` and `Last Review`. Idea taken from Prova Endurance
  (WouldShowWrong + ReviewOn per decision).
- **It comes back on its date.** `engine/block_review.py` (new): `get_athlete_state` returns
  `review_due` once the review date has passed with no review recorded; the coach puts it first
  in its reply and reviews before planning (Phase 5, "Review first"). `coach.py prep` prints the
  same line; `coach.py review` adds a "Block falsifier" section to review.md.
- **What a review is:** one question — did the stated result happen? It judges the design,
  never the athlete, attributes nothing, and one block is one observation, never a rule.

## v7.21 (2026-10-04)

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
  and `_template.yaml` in the Project knowledge; restart Claude Desktop.

## v7.20 (2026-10-04)

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
  and restart Claude Desktop so the MCP server loads the new `tools_push.py`.

## v7.19 (2026-10-02)

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

## v7.18 (2026-10-02)

- **New MCP tool `save_declared_profile(athlete_id, yaml_text, dry_run, confirm)`:** the coach
  writes `config/athletes/<id>.yaml` itself — after an intake or any approved change — behind
  the write gate (dry run with a diff, plain-words summary, approval, save). It checks the
  YAML, the template's sections and the names the system recognizes, and keeps the previous
  version in `data/<id>/profile_history/`. The head coach no longer saves a yaml by hand.
- **Prompt (same version):** a preference about degree ("not too much X") means rebalancing,
  never removing X; cadence work stays a legitimate modifier — variety comes from adding
  variables, not from dropping cadence.

## v7.17 (2026-10-02)

- **Prompt, from the first real use (2026-10-03):** three coaching-judgement principles —
  the head coach's input is a criterion applied with judgement, not a rule, and is recorded in
  `#SESSION` as a criterion with its reason; weekly TSS/hour targets are a guide that follows
  from well-designed sessions, never a quota (no trimmed warm-ups, odd durations or filler to
  hit a number); warm-up and cool-down proportionate to the session (brief in short sessions,
  longer as durations and intensities grow).

## v7.16 (2026-10-02)

- **Book knowledge on demand.** New MCP tool `get_knowledge(source, refs, query, max_entries)`
  (`engine/knowledge.py`): exact entries by ID (`TRPM-C06-019`) or section (`§7`), keyword
  search inside one source or all, or a source's table of contents. Principles only; answers
  capped. **The book KBs leave the Claude Project**: it now holds only the generated tables,
  doctrines, architectures, language guide, syntax and the intake files (~0.2 MB instead of
  ~3 MB).
- **Mujika** re-extracted (tagged) and now governs the taper in both doctrines (v1.1).
- **Prompt:** tools table, Inputs, "Project files and book knowledge", doctrine and fallback
  wording; zone-table headers and `profile.md` name `get_knowledge` instead of Project files.

## v7.15 (2026-10-02)

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

## v7.14 (2026-10-02)

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

## v7.13 (2026-10-02)

- Cycling Doctrine (`config/doctrine/cycling.yaml` → `generated/Cycling_Doctrine.md`), prompt
  Doctrine section, time-crunched mode on request only, `friel_running` reference only, Coggan
  KB re-extracted in the tagged format. History rewritten 2026-10-02 to remove athlete data.

## v7.12 — Tim Cusick's WKO webinars join Coggan and Friel cycling (2026-10-02)
New `Knowledge/Principles/Cusick_WKO_Coaching_Webinars.md` (+ Catalogs companion),
extracted with the book pipeline (254 entries, verified). Cusick is a different
author, so the YAML gets a new field, `companion_knowledge_files` (file + author):
`coggan.yaml` and `friel_cycling.yaml` list it, the zone-table header and
`profile.md` show a `Companion Knowledge` line, and the prompt says to attribute
its content to Cusick, never to Coggan or Friel, and that it never overrides a
zone table or the author's own books.

## v7.11 — Friel cycling reads two books (2026-09-30)
The 2018 *Cyclist's Training Bible* was re-extracted with the book pipeline
(411 entries, numbers checked against the source) and split into `Principles/` and
`Catalogs/` like the other authors; the old single file moved to
`archive/Knowledge_legacy/`. The 2025 *High-Performance Cyclist* joins it as a second
file by the same author: `friel_cycling.yaml` gets `supplementary_knowledge_files`,
the zone-table header and `profile.md` list both, and the prompt says that where
the two differ on a zone boundary the zone table governs.

## v7.10 — the language guide uses the head coach's own vocabulary (2026-09-27)
v7.9 imposed word choices nobody had asked for. Now: Tempo, strides, VO2max and
neuromuscular stay as written; the class is *resistencia aeróbica* (*fondo
aeróbico* on the long day, *trote aeróbico* on any other run), *umbral*,
*sub-umbral*; the cue bank is the head coach's own phrases and may repeat; prose
fields use `10 min` / `30 s` while the code block keeps `10m` / `30s`;
*zancada fluida*. Author codes (Friel Zona 3, Daniels E) never reach the athlete:
they live in a new coach-only header line, `[Zone]`, which `push_block` does not
upload. The validator only warns (`CHK-LANG`), and the repeated-cue check is gone.

## v7.9 — nutrition reaches Intervals.icu; Spanish text is controlled (2026-09-27)
- `push_block` sent only the code block, so `[Execution]` and `[Nutrition]` never
  left the session card. The Intervals.icu description is now the Execution and
  Nutrition notes (in the athlete's language, from the declared profile), a blank
  line, then the steps. `include_notes=false` restores the old behaviour.
- `config/language/es_mx.yaml` (glossary, cue bank, failure-condition sentences,
  patterns to avoid) builds `generated/Language_Guide_es-MX.md`, a Project file.
  The validator warns (never blocks) with `CHK-LANG` on calques, English class
  names, `10m` in prose, anglicisms and gender slips, and with `CHK-LANG-REPEAT`
  when one cue is pasted into three sessions.
- `[Execution]` is three short sentences and no longer re-lists the structure.
- `fill_tss` keeps a space before `|` after `[Duration]`.

## v7.8 — provisional thresholds, done properly (2026-09-26)
When `#STATE` contradicts a threshold, Endurance steps stay in the lower half of
the zone (they are a percentage of a threshold that is probably too high), at
most one test is scheduled per week (the sport the block needs first goes in
week 1), and the declared profile's notes never override the weekly pattern the
head coach saved.

## v7.7 — decisions survive the chat (2026-09-26)
Every new chat started from zero: the coach re-chose the methodologies
(Friel/Daniels one time, Coggan/Palladino the next), reverted the approved
weekly pattern (Tue/Thu treadmill instead of Tue/Thu trainer) and planned Tempo
before the FTP test, because `#SESSION` was only saved at block end. Now
`#SESSION` (methodologies, Metric Map, weekly pattern, strategy figures) is
saved at every phase gate and holds phases 1-6; the weekly pattern is stated by
the head coach, never inferred; and a threshold that `#STATE`'s own signals
contradict is provisional: Endurance only until the test result is in.

## v7.6 — the architecture library reaches the coach (2026-09-26)
The 16 session shapes distilled from ~1,700 MyWhoosh / Whatsonzwift workouts
and the running catalogs lived only in `config/architectures/*.yaml`, which
never reached the Project: the coach saw their names in `#STATE`, never what
each is for or how it progresses. And the engine only read the shape inside
one rep, so 6 of the 16 (pyramid, progressive_intervals, duration_ladder,
progression_run, climb_simulation, cadence_contrast) were never detected and
were reported "unused" forever.

- `build` now also writes `generated/Session_Architectures.md` (a Project file).
- The classifier reads shapes across reps; all 16 are detectable, and a test
  fails if the engine and the library ever disagree again.
- Hill repeats (`climb_simulation`) now apply to running and trail.
- Prompt: Pass 1 opens the library and names a slug per session; trail
  defaults to Koop or Olbrich.

## v7.5 — the coach stops asking for what it can read (2026-09-26)
Three failures seen in real sessions, fixed in the prompt and tested:
the coach asked the head coach to confirm that Project files were present
(it has the search); it left the Metric Map's anchor and dual-layer fields
"to be confirmed" for a later phase (they are in the zone-table header); and
it proposed its own daily time ceilings, lower than the ones the head coach
had stated. Availability is now only ever a stated number; the new
`save_availability` tool stores it once and `get_athlete_state` returns it,
so it is not asked or invented again. `friel_running` is zones-only (v7.4).

## v7.3 — MCP is the primary path (2026-09-26)
The server was rebuilt in v6.7, but the prompt never got its tool
instructions back after the v6.6 removal, so the coach kept asking for
dragged files. v7.3 closes that gap and fixes what the first real use
exposed:

- **Prompt:** new `<tools>` section. The coach opens every conversation
  with `get_athlete_state`/`get_athlete_profile`, and saves, validates and
  uploads each week itself. Uploads go through a gate: dry-run → the head
  coach approves → live push. The manual path is kept only as a fallback.
- **`push_block` date fix:** session headers carry `[Date]` as DD-MM-YYYY
  and were sent as-is; Intervals.icu answered HTTP 500 on the first real
  push (21-sep-2026). Dates are now converted to ISO. Race days are
  skipped with a stated reason (the race event already lives in
  Intervals.icu).
- **`get_athlete_state` returns `continuity` and `race_notes`**, so no
  file is pasted at the start of a conversation.
- **`save_block(week=N)`** writes `<date>_bloque_w<N>.md`, so two weeks
  saved the same day no longer overwrite each other; `validate_block` and
  `push_block` default to the most recently saved week.
- **Repo:** `snapshot_E.txt` removed (it listed athlete names and ids);
  superseded root docs moved to `archive/`.

## v6.7 — MCP server rebuilt
`mcp_server/` is back, with the root cause of the v6.6 removal fixed
structurally rather than patched around. The removal postmortem
(`archive/RESTORE_POINT_v6.5.md`) named a monkeypatch of a private SDK
class as the actual cause of the earlier instability; this rebuild
replaces that guesswork with a confirmed diagnosis and a version-pinned
fix:

- **Root cause, confirmed against upstream, not re-guessed.** The v6.5
  instability traced to `modelcontextprotocol/python-sdk#2610` — cancelling
  an in-flight request over stdio makes `RequestResponder.__exit__` let a
  `CancelledError` escape after the responder had already completed;
  because that task is a sibling of the stdio receive loop's own task
  group, one cancelled tool call took the whole server down. Confirmed
  still present in `mcp` 1.30.0 by reading its source directly, and
  confirmed a correct no-op against `mcp` 2.x, where `RequestResponder` no
  longer exists.
- **The fix:** a pinned SDK version plus `mcp_server/cancel_patch.py`, a
  self-detecting workaround — it constructs a real `RequestResponder` and
  empirically probes whether the installed SDK still exhibits the bug
  before patching anything, so it becomes a deliberate no-op the day the
  upstream fix (`python-sdk#2624`) ships in whatever version is installed,
  with nothing else to remember to change.
- **The 8 tools are back**, unchanged in shape from v6.5:
  `get_athlete_state`, `get_athlete_profile`, `list_roster` (reads),
  `save_continuity`, `save_race_result`, `save_block` (writes),
  `validate_block` (wraps the existing verifier as a subprocess), and
  `push_block` (uploads to Intervals.icu, dry-run by default).
- **Three real bugs found and fixed during manual end-to-end testing on
  Windows** — none caught by the test suite beforehand, since it runs on
  Linux:
  - `validate_block` crashed with an uncaught `UnicodeEncodeError` on
    Windows: `subprocess.run`'s `encoding="utf-8"` only controls how the
    *parent* decodes output, not what encoding the *child* uses to
    encode it, and a Windows child piped (not console) stdout defaults to
    cp1252, which can't encode the box-drawing characters
    `validate_block.py` prints on every run. The crash surfaced as
    `passed: False`, indistinguishable from a real hard-constraint
    failure. Fixed by forcing `PYTHONIOENCODING=utf-8`/`PYTHONUTF8=1` in
    the child's environment.
  - `validate_block` and `push_block` both resolved a relative
    `file_path` against the current process's working directory instead
    of the server's own `ROOT` — worked when called from a fresh
    interpreter launched at `ROOT`, failed with a spurious "File not
    found" through the live server process launched by Claude Desktop,
    whose actual working directory didn't match `ROOT` despite
    `claude_desktop_config.json`'s `cwd` field. Fixed by resolving a
    relative path against `ROOT` explicitly in both tools.
  - `validate_block` hung for several minutes over Desktop's live stdio
    connection while returning in 0.2s called directly: its
    `subprocess.run()` never redirected the child's stdin, so the child
    inherited the server's own stdin — the live JSON-RPC pipe Desktop
    uses under stdio transport, which a standalone CLI call never has.
    Fixed with an explicit `stdin=DEVNULL`.
- **One design gap closed, not a bug in the strict sense:** `push_block`
  never checked `validate_block`'s own result before sending. The
  original two-command CLI made "BLOCKED" and "upload" a full
  conversation turn apart, so a human seeing BLOCKED simply wouldn't run
  the next command; inside one MCP conversation they're a single tool
  call apart, and that protective friction doesn't exist by default.
  Confirmed directly during testing: a block with real HC-METRIC failures
  was assembled and would have been sent to Intervals.icu with both
  `dry_run=False` and `confirm=True`, rejected only because the test used
  invalid credentials, not because the tool stopped it. `push_block` now
  runs the same validation check internally before its live send and
  refuses a BLOCKED block unless `override_validation=True` is also
  passed explicitly.

## v6.6 — MCP server removed
`mcp_server/server.py` caused enough production instability that it was
removed entirely — code, prompt references, and the `mcp:` config block in
`decision_thresholds.yaml`. The daily workflow is back to dragging
`out/<athlete_name>/` into the Claude Project, as described in Daily Use
above. There is currently no automated upload path to Intervals.icu; a
verified block is pasted into its Workout Builder by hand. The full
incident history — what the server did, the two real bugs it surfaced, and
why it was reverted — is kept in `archive/RESTORE_POINT_v6.5.md` rather
than deleted, specifically so a future attempt does not start from zero.

## v6.5 — MCP server (built, then removed — see v6.6 above)
The daily workflow required dragging files into the Claude Project for
every new chat. What changed:

- **`mcp_server/server.py`** exposed the engine itself as 8 tools a local
  Claude Desktop connection could call mid-conversation — never a wrapper
  around the raw Intervals.icu API, so `#STATE`'s determinism guarantee
  carried over unchanged: `get_athlete_state`, `get_athlete_profile`,
  `list_roster` (reads), `save_continuity`, `save_race_result`,
  `save_block` (writes), `validate_block` (wrapped the existing verifier as
  a subprocess), and `push_block` (uploaded to Intervals.icu via
  `POST /events/bulk?upsert=true`, defaulting to a dry run).
- **The prompt called these tools itself** — `save_block`, `save_continuity`,
  `save_race_result`, and `validate_block` — when available, falling back
  to the manual copy-paste flow otherwise (e.g. the browser Project,
  where the server could never connect). `push_block` was deliberately
  never called automatically.
- **A real classification bug found and fixed in the process:**
  `[Discipline]: road` is ambiguous — confirmed real for both cycling
  (Coggan) and running (Daniels) methodologies in the repo's own test
  fixtures. The fix read the author's own `sport:` field from
  `config/authors/<methodology>.yaml` instead of a flat lookup table,
  which would have silently classified a marathon as a bike ride. This
  fix lived only inside the now-removed code — see `IMPROVEMENT_BACKLOG.md`
  §5 for why the underlying lesson still matters.

## v6.4 — results module
The system could generate and verify plans but never measured whether they
worked. What changed:

- **`coach.py review`** compares an athlete's signals between any past date
  and today: CTL/ATL/TSB and ACWR (both fully reconstructable from the
  180-day pull already fetched — no new data needed), durability, and curve
  progression (needs a dated snapshot — see next point).
- **Curve snapshots** are captured on every `coach.py prep`, since
  Intervals.icu's curves endpoint only ever returns the best value as of
  today, never a historical one. Progression tracking is only as old as the
  first snapshot captured after this shipped.
- **`#RACE_RESULT`** — Phase 6 of the prompt now emits a small saveable block
  after a race debrief, appended to `out/<athlete>/race_notes.md`, which
  `review` reads automatically for any race inside the requested window.
- **A dormant regression-suite bug was found and fixed:** the golden tests'
  synthetic fixtures are dated relative to whenever `make_fixtures.py` was
  last run, not to the calendar — so a fixture generated once and left on
  disk silently drifts out of its own rolling windows as real time passes,
  failing for reasons unrelated to any code change. `run_tests.py` now
  regenerates every fixture immediately before comparing, closing the gap
  for good.

## v6.3 — unified daily workflow
- **`coach.py`** gained `prep` (fetch + resolve + render in one call,
  delivered to a named `out/<athlete>/` folder instead of `data/<id>/`),
  `new` (athlete onboarding), and a live `continuity.md` staleness check.
  `out/roster.md` gives a name-to-id index across the whole account.
- **`build_profile.py`** replaced the Excel-based `intervals_export.py` +
  `convert.py` pipeline for the athlete-facing context document, recovering
  data the old pipeline silently dropped (Avg Power on every activity).
- **`#SESSION` can be requested on demand mid-block**, not only at
  block-end, so an off-calendar consult in a fresh chat has a continuity
  artifact to resume from.

## v6 — deterministic engine architecture
Rebuilt around four layers so that computation and judgement stop competing for
the same pass. What changed:

- **Configuration became data.** 13 methodologies as schema-validated YAML; zone
  tables generated from them and never hand-edited. Adding an author is a file,
  not a code change.
- **TSS left the prompt.** Computed by the verification engine from the zone
  tables, removing a class of silent arithmetic error.
- **A deterministic engine** resolves training state, projects the PMC, and reads
  curve progression, durability and anaerobic repeatability across rolling
  windows, emitting an authoritative `#STATE` block with the source of every
  figure.
- **A verification gate** checks every generated block against the hard
  constraints before it can reach an athlete.
- **A regression suite** of 409 tests over synthetic athletes with frozen expected
  outputs.
- **Non-threshold anchors** declared per author, keeping zones interchangeable
  across methodologies without altering any author's published numbers.

## v5.1 and earlier
- TSS assigned by the KB zone's physiological class instead of the raw % number.
- Special Output Rule generalized, replacing the hardcoded Olbrich exception.
- Two-class rule hierarchy: inviolable output-format constraints vs. overridable
  coaching defaults.
- Self-sufficient `#SESSION` continuation header; terminal Phase 6.

