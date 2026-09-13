# WORKFLOW_ACTUAL — what the code actually does

Written by reading `coach.py`, `engine/`, `verify/`, `tests/`,
`config/schema/author.schema.json`, `config/authors/coggan.yaml`,
`config/athletes/_template.yaml`, and `build_zone_tables.py`, then checking
every claim in `manual/OPERATIONS_MANUAL.md`, `manual/QUICK_GUIDE.md`,
`WORKFLOW_CHECKLIST.md`, `IMPROVEMENT_BACKLOG.md`, `ARCHITECTURE_v6.md`, and
`RESTORE_POINT_v7.0.md` against it. Where the chat-side behavior mattered to
a claim (phase numbering, staleness rules), `Prompt/infame_elite_endurance_coach.md`
was also read — it isn't Python code, but it's the only place that behavior
is actually specified, since nothing in `coach.py`/`engine/` implements it.

Not touched, per instructions: `config/athletes/*.yaml` (real athlete data,
gitignored) and `generated/` (build output).

---

## 1. The real process, step by step

### One-time setup
1. `pip install -r requirements.txt` — installs `requests`, `pyyaml`,
   `jsonschema`. The file's own header says it was written by reading actual
   imports, not copied from a manual — that check confirms it's current.
2. `ICU_API_KEY` environment variable set. `engine/fetch_athlete_data.py`
   calls `sys.exit()` at **import time** if it's missing — before argparse
   even runs. `coach.py` avoids importing that module until a command
   actually needs it, specifically so `coach.py check` still works with no
   key set.

### Onboarding an athlete
1. `python coach.py new <id>` → `cmd_new()`:
   - Connects to Intervals.icu, calls `fetch_athlete_data.list_athletes()`
     to confirm the id is real on the account.
   - Refuses if `config/athletes/<id>.yaml` already exists — never
     overwrites.
   - Copies `config/athletes/_template.yaml` to `config/athletes/<id>.yaml`
     verbatim, then prints where `config/athletes/ATHLETE_INTAKE.md` is so
     the head coach can run the intake as a conversation.
2. The intake conversation itself, and turning its output into filled YAML,
   happens **entirely inside the Claude Project chat** — there is no code
   in this repo that conducts, checks, or writes the intake answers. The
   head coach pastes the finished text over the templated file by hand.
3. The only code-level check on that file's content is
   `build_profile.py`'s `profile_warnings()` — and it only runs the next
   time `prep` renders `profile.md` for that athlete, not at onboarding
   time.

### Daily prep — `python coach.py prep <id>` (or `--all` / `--list`)
`cmd_prep()` → `prep_one()` runs four steps per athlete, and the first
failure that matters stops that athlete's run:

1. **`fetch_athlete_data.fetch_one()`** — pulls from the Intervals.icu API:
   profile + per-sport settings (`fetch_profile`), 180 days of wellness and
   the PMC series in the same call (`fetch_wellness`), 180 days of activity
   summaries (`fetch_activities`), power/pace curves across three named,
   *nested* windows — 42d/90d/1y — for Ride and Run (`fetch_curves`), and
   events for the next 365 days (`fetch_events`). Writes
   `data/<id>/athlete_data.json`. **A fetch failure aborts prep for that
   athlete outright** — `prep_one` prints `FETCH FAILED` and returns
   `False` without touching `data/` further, because resolving state on
   stale data is explicitly treated as worse than not resolving it at all.
2. **`capture_snapshot()`** — writes a small dated file to
   `data/<id>/history/<fetched_date>.json` containing only that day's
   curves. This is what later lets `review` reconstruct a past curve state,
   since Intervals.icu's curve endpoints only ever return today's best, never
   a historical one. Wrapped in `try/except` — a failure here is printed but
   never blocks `state.md` delivery.
3. **`build_state.build()`** — the deterministic core:
   - `latest_pmc()` reads the last row of the PMC series.
   - `hrv_signal()` — 7-day mean vs 60-day median baseline, needs ≥14 total
     HRV readings and ≥4 recent / ≥10 baseline to report anything.
   - `acwr_signal()` — 7-day acute load vs 28-day/4 chronic average.
   - `durability_signal()` — median decoupling over the last ≤6 qualifying
     sessions (≥45 min), needs ≥3 to report.
   - `resolve_state()` — **TSB is the primary governor** when present;
     falls back to the HRV band only when TSB is absent. A
     `maladaptation_risk` TSB reading is downgraded to
     `functional_overreach` only when ACWR is inside the configured safe
     range *and* durability is `stable` — both conditions, not either.
     HRV/TSB divergence is recorded as a flag explicitly marked
     "reference only, not actionable" — it never gates anything.
   - `project_pmc()` — a Banister exponential projection 42 days out. Any
     day with an explicit Intervals.icu event (including an explicit
     zero-load rest day) uses that event's load; every other day falls back
     to `weekday_load_pattern()` — the athlete's own trailing-8-week average
     load for that weekday — rather than assuming zero. That pattern
     requires ≥10 logged activities, ≥21 days of span, and every weekday
     represented ≥3 times; short of any of those, the projection reverts to
     zero-fill with a caveat sentence in the output.
   - `taper_check()` — finds the next A+/A/A- goal from
     **`config/athletes/<id>.yaml`'s `goals[]`, never from Intervals.icu's
     own event fields** (Intervals collapses A+/A/A- into one category and
     its `type` field is the sport, not the event format — neither is
     usable). Compares projected TSB at that date against
     `target_tsb_by_event_type` from `decision_thresholds.yaml`.
   - `longitudinal.analyze()` — curve progression (42d-vs-90d *trend*,
     42d-vs-1y *level*, kept strictly separate because the windows are
     nested, not comparable), durability trend, W' repeatability
     (depletion above 100% is clamped and counted as a data-quality flag,
     never reported as an impossible number), an `adaptation_state` summary,
     and `testing_recommendations` (which anchors are worth retesting, plus
     data-quality flags for underestimated W', non-endurance sessions in the
     log, and thin power coverage).
   - `power_profile.analyze()` — Coggan-table ranking and phenotype, only if
     `config/power_profile.yaml` exists and the athlete has 42d power-curve
     points. Refuses to assign a phenotype if any required column (5s or FT)
     scores at or below the table floor, since that reads as "never tested,"
     not "weak."
   - Writes `data/<id>/state.md` and `state.json`. **A failure here (unlike
     fetch) also aborts that athlete's `prep` run** — no `profile.md` step
     runs, nothing is copied to `out/`.
4. **`build_profile.build()`** — renders `profile.md`: the declared-profile
   section (verbatim YAML with comments stripped, flagged via
   `profile_warnings()` for unrecognized disciplines/priorities/event
   types/methodology-sport mismatches), personal info, a computed context
   snapshot (next A-race, average weekly TSS/hours, sport-count
   distribution), sport configuration, races, workouts, and 180 days of
   activity history. **This step is explicitly non-blocking** — a failure
   here is printed as `PROFILE BUILD FAILED (non-blocking)` and `state.md`
   is still delivered alone.
5. Both files (whichever exist) are copied to
   `out/<safe_athlete_name>/`. `check_continuity()` then only *reports* the
   presence and age (>10 days flagged) of `out/<name>/continuity.md` — it
   never writes or validates that file's contents.
6. `write_roster()` regenerates `out/roster.md` from every athlete's
   `fetched_at`, every time `prep` runs in any mode (single, `--all`, or
   `--list`).

### Working the block, inside the Claude Project chat
Everything from here through phase progression, gating, and the Metric Map
is specified in `Prompt/infame_elite_endurance_coach.md` and enforced only
by the chat model reading and following it — **none of it is implemented
or checked by any script in this repository.** The prompt currently defines
seven phases: **0** Gateway, **1** Intake and verification (the Metric Map
is decided inside this phase, not a phase of its own), **2** Strategy,
**3** Macrocycle blueprint, **4** Block execution, **5** Recalibration,
**6** Macrocycle close and race debrief. The head coach drags in
`state.md` + `profile.md` (+ `continuity.md` if a macrocycle is already in
progress); the coach proposes and the head coach approves before any
session code is generated (Phase 4).

### Validating and uploading a block
1. Head coach copies just the delivered block (from `[Week]` through the
   last session's `[Nutrition]` line) into a local file.
2. `python coach.py check <file>` → `cmd_check()` shells out to
   `verify/validate_block.py <file> --fill-tss` (plus `--methodology`/
   `--discipline` if passed) so the exit code matches exactly. This:
   - `normalize_block()` **auto-repairs the file on disk before validating
     it at all** — translates Spanish header labels, strips markdown bold
     from header lines, adds a missing ` ```text ` fence, cleans a
     `~`/parenthetical-decorated `[Duration]`, and treats a bare `—` as
     "not applicable" for a Rest/Travel session's Methodology/Discipline.
     Every fix is printed; the file is rewritten whether or not the block
     ultimately passes.
   - `split_sessions()` splits on `[Week]` headers; each session's
     `[Methodology]` resolves an author file from `config/authors/`, its
     `[Discipline]` is canonicalized against `decision_thresholds.yaml`'s
     alias table and checked against the methodology's sport.
   - A session's declared profile (equipment, ramp overrides, Metric Map)
     is loaded only from **`[Athlete ID]` in that session's own header** —
     `coach.py check` never exposes a `--athlete` flag of its own, even
     though `validate_block.py` itself accepts one directly. This only
     matters for a raw block with no header; the prompt's own session
     template always emits `[Athlete ID]`, so real deliveries are unaffected.
   - `parse_block()` + `check_constraints()` enforce hard constraints
     (`HC-*`): RPE present on every step and consistent with the author's
     table for that target, prescription floors, forbidden absolute units
     (raw watts/bpm/pace), the metric legality for the methodology/sport/
     declared Metric Map/declared equipment, ramp eligibility by discipline
     and profile override, and dual-layer completeness (engine metric +
     quoted cue). Any hard-constraint failure anywhere in the file **blocks
     the entire run** (exit 1) — `--fill-tss` is refused outright, not
     applied to the sessions that did pass.
   - Warnings (`FMT-*`, `CHK-*`) never block: formatting nits, non-canonical
     section language, a metric the author doesn't natively define
     (classified by generic cutpoints instead), a partial TSS (some steps
     — distance-based, freeride, RPE-only — can't be costed), and
     `CHK-MONO` — repeated Tempo-or-above architecture with no dose increase,
     compared only against earlier sessions **within the same validation
     run**, never against `continuity.md` or a prior file.
   - On a clean pass, `--fill-tss` rewrites each `[Estimated TSS]` (as a
     plain number, or `N (partial)` when some steps were excluded) and each
     fully-determined `[Duration]` in place, then prints
     `RESULT: PASS — verified against config. Upload-safe.`
3. **Uploading itself has no code path.** The passed block is pasted into
   Intervals.icu's own Workout Builder by hand — `IMPROVEMENT_BACKLOG.md`
   confirms the only automated-upload attempt (`push_block`, via an MCP
   server) was built and then removed after production instability, with
   nothing standing in for it today.
4. At block close or after a race, the coach emits a `#SESSION` or
   `#RACE_RESULT` block in the chat. The head coach pastes it by hand into
   `out/<name>/continuity.md` or appends it to `out/<name>/race_notes.md`.
   **`coach.py` only ever reads these two files (`check_continuity()`,
   `read_race_notes()`) — it never writes either one.**

### Measuring a block — `python coach.py review <id> --since <date>`
`cmd_review()` requires `data/<id>/athlete_data.json` to already exist — it
never fetches on its own. It reconstructs CTL/ATL/TSB (`pmc_at`) and ACWR
(`acwr_signal(..., as_of=since)`) at the given date from the same 180-day
history `prep` already pulled, computes durability at both dates
(`decoupling_at`), finds the curve snapshot nearest `since` via
`nearest_snapshot()` (only populated from the day `capture_snapshot()`
first ran for that athlete — this is a hard floor, not something that can
be reconstructed retroactively for older blocks), diffs shared 42d anchors
between then and now, and folds in any `#RACE_RESULT` block from
`race_notes.md` whose date falls in the window. Writes `out/<name>/review.md`.

### Maintenance
- `python tests/run_tests.py` — unit tests, block-fixture tests
  (`tests/blocks/*.md` run through the real validator as a subprocess), and
  golden comparisons: `make_fixtures.py` is re-run immediately before every
  comparison specifically so synthetic fixtures never age out of their own
  rolling windows, then each fixture's full `build_state.build()` output is
  diffed against a frozen `expected_state.json`. **Currently 193/193 pass**
  — see the doc-gap list below for why every written test count in the docs
  disagrees with this.
- `python build_zone_tables.py validate` / `build` — schema-validates every
  `config/authors/*.yaml` against `config/schema/author.schema.json`
  (`Draft7Validator`) and regenerates the two Markdown zone tables under
  `generated/`, which is what actually gets uploaded to the Claude Project
  as "Knowledge." Referenced constantly by `WORKFLOW_CHECKLIST.md` but not
  by `OPERATIONS_MANUAL.md`.

---

## 2. Manual vs. automated

**Automated (code in this repo):**
- Fetching Intervals.icu data; resolving state (PMC, HRV, ACWR, durability,
  taper, longitudinal analysis, power profile); rendering `profile.md`;
  writing `out/roster.md`; reporting `continuity.md` presence/age (report
  only, not a gate); reconstructing past signals and curve diffs for
  `review`; parsing, auto-repairing, and hard-gating a workout block;
  computing and filling TSS/Duration; schema-validating author files and
  regenerating zone tables; the full regression suite.

**Manual, or done only inside the Claude Project chat (i.e. not
implemented or enforced by any script here):**
- The intake conversation and transcribing its result into the athlete's
  YAML.
- Every phase gate, the Metric Map decision, and the 7-day `#STATE`
  staleness refusal — all exist purely as instructions in
  `Prompt/infame_elite_endurance_coach.md`; nothing in `coach.py` or
  `engine/` checks `state.md`'s age or a phase's progress.
- Copying the delivered block text into a file.
- Uploading a passed block to Intervals.icu (no code path exists).
- Writing `continuity.md` (`#SESSION`) and `race_notes.md`
  (`#RACE_RESULT`) — `coach.py` reads both, writes neither.
- Keeping two machines' repo copies in sync (commit/push/pull) — no
  tooling checks this; `IMPROVEMENT_BACKLOG.md` names this as a real,
  previously-realized failure mode with no fix built yet.
- Re-uploading `generated/*.md` and `Knowledge/` files to the Claude
  Project after any config or knowledge edit.

---

## 3. Where the docs are wrong, silent, or outdated

- **Every stated test count disagrees with the live suite, and with each
  other.** `manual/OPERATIONS_MANUAL.md` §11 and `WORKFLOW_CHECKLIST.md`
  §A3/§H both say "76 tests" / "76/76 passed." `RESTORE_POINT_v7.0.md`'s own
  restoring checklist says "192/192." Running `tests/run_tests.py` right now
  gives **193/193**. None of the three numbers currently on disk matches
  reality, and the two most recently written docs (the manual and the
  latest restore point) don't even agree with each other.

- **`coach.py check` silently drops a flag `validate_block.py` supports.**
  `validate_block.py --athlete <id>` loads that athlete's declared profile
  directly; `coach.py`'s `cmd_check()` never forwards such an option — only
  `--methodology`/`--discipline`. Neither manual mentions this gap. It's
  invisible for real deliveries (the prompt's template always emits
  `[Athlete ID]` in the header), but it means "`coach.py check` is a
  shortcut for `validate_block.py`" (as `WORKFLOW_CHECKLIST.md` §C Step 5
  states) is not quite true for a raw, headerless block.

- **The "7-day stale `#STATE`" rule is described as if the system enforces
  it.** `OPERATIONS_MANUAL.md` §12 ("the coach will refuse to advance on
  stale numbers") and `QUICK_GUIDE.md`'s golden rules ("it will refuse to
  guess with stale data") both describe this as something the tooling does.
  It is entirely a line in `Prompt/infame_elite_endurance_coach.md`'s
  "missing input" table — no code anywhere reads `state.md`'s `Resolved:`
  date. It only holds if the chat model notices and honors it in that one
  conversation; `coach.py` will happily let a head coach `check` a block or
  read a `review` off week-old data with no warning.

- **Neither manual's phase list matches the current prompt.**
  `WORKFLOW_CHECKLIST.md` §C Step 3 lists six phases numbered 1–6 named
  "Metric Map," "Macrocycle design," "Block proposal," "Session
  generation," "Recalibration," "Macrocycle close" — none of those names
  match `Prompt/infame_elite_endurance_coach.md`'s actual phases (0
  Gateway, 1 Intake and verification, 2 Strategy, 3 Macrocycle blueprint,
  4 Block execution, 5 Recalibration, 6 Close and debrief), and it omits
  Phase 0 entirely. `OPERATIONS_MANUAL.md` §5 references "Phase 1" and
  "Phase 4" by number correctly but never names or counts Phase 0, 2, or 3,
  and describes Phase 1 as "verification, and intake" without mentioning
  that the Metric Map is decided there too.

- **`profile.md`'s built-in profile-vocabulary check isn't mentioned
  anywhere in the operational docs.** `build_profile.py`'s
  `profile_warnings()` flags unrecognized disciplines, priorities, event
  types, and cross-sport methodology assignments written into an athlete's
  YAML, and surfaces them at the top of `profile.md` — a real, code-run
  check. Neither `OPERATIONS_MANUAL.md` nor `WORKFLOW_CHECKLIST.md` tells
  the head coach this exists, so there's no documented expectation that a
  typo in the YAML will be caught here (one `prep` cycle after it's
  written) rather than silently ignored.

- **`WORKFLOW_CHECKLIST.md` §B4's YAML sanity check is weaker than it
  reads.** The command shown (`python -c "import yaml;yaml.safe_load(...)"`)
  only confirms the file parses as YAML — it does not run
  `profile_warnings()`, so it will print "ok" for a file with an
  unrecognized discipline, priority, or methodology name. The real check
  only happens on the next `prep` run, once `profile.md` is rendered. The
  checklist presents B4 as if it were the validation step for a freshly
  filled profile.

- **No documented failure-mode row for `STATE RESOLUTION FAILED`.**
  `OPERATIONS_MANUAL.md` §12's troubleshooting table has a row for
  `PROFILE BUILD FAILED (non-blocking)` but none for a `build_state.build()`
  exception — which is the one failure mode in `prep_one()` that aborts
  delivery of *both* files for that athlete, not just `profile.md`. Someone
  hitting it sees `STATE RESOLUTION FAILED` printed with no corresponding
  guidance anywhere in either manual.

- **`OPERATIONS_MANUAL.md` §6's session-header field list is incomplete.**
  It lists a session's fields as `[Category]`, `[Methodology]`,
  `[Discipline]`, `[Focus]`, `[Duration]`/`[Estimated TSS]`, `[Execution]`,
  `[Nutrition]` — omitting `[Week]`, `[Date]`, and `[Athlete ID]`, all three
  of which the validator's own parser (`split_sessions`, `FIELD_RE`) and the
  prompt's template require or use. `WORKFLOW_CHECKLIST.md` §C Step 4 does
  correctly say the validator reads `[Methodology]`, `[Discipline]`, and
  `[Athlete ID]` — the two docs are inconsistent with each other here, not
  just individually incomplete.

- **`ARCHITECTURE_v6.md` is explicitly marked design-only and already
  self-corrects** (its own banner lists exactly where the built system
  diverged from it) — checked and confirmed accurate as a historical
  document, not as an operational reference. No new gap found there beyond
  what it already discloses about itself.

---

## 4. Friction points and error-prone spots

- **Two-machine sync is entirely trust-based.** No hash, diff, or
  sync-check tool exists (an unbuilt item in `IMPROVEMENT_BACKLOG.md`
  itself), and the backlog names a real prior incident — "a field silently
  showing blank" — caused by exactly this. The whole workflow depends on a
  human remembering to copy, commit, push, and pull correctly, every time.

- **The three hand-maintained files have no validation layer at all.**
  `continuity.md`, `race_notes.md`, and an athlete's `config/athletes/*.yaml`
  are pasted over by hand, with nothing checking the paste was complete or
  went into the right file — in sharp contrast to how rigorously
  `validate_block.py` treats the training block itself. A partial paste
  into `continuity.md` silently corrupts the macrocycle's resumed position
  with no code anywhere positioned to catch it.

- **`coach.py check` mutates the input file before you know whether it will
  pass.** `normalize_block()`'s auto-repairs are written to disk
  unconditionally, even on a run that ends up `BLOCKED`. A head coach who
  re-runs `check` after a failed attempt will find their local file already
  altered from what the coach originally delivered.

- **A "(partial)" TSS is easy to miss.** `--fill-tss` writes either a plain
  integer or the string `"37 (partial)"` into `[Estimated TSS]` depending on
  whether every step could be costed. Both look like a normal number at a
  glance in Intervals.icu's own interface once pasted in.

- **`taper_check`'s "not applicable" message can't distinguish two very
  different situations.** It returns the same reason string —
  "no upcoming A+/A/A- priority goal declared in `goals[]`" — whether the
  athlete's YAML doesn't exist at all (`load_declared_goals` returns `[]`
  for a missing file) or the file exists with no upcoming A-race declared.
  With most athletes currently missing a real declared profile (per
  `RESTORE_POINT_v7.0.md`'s own open-items list), this is the common case,
  and there's no way to tell from `state.md` alone which situation applies.

- **The weekday-load fallback silently reverts with only a caveat
  sentence.** `weekday_load_pattern` needs ≥10 activities, ≥21 days of span,
  and every weekday seen ≥3 times; short of any one of those,
  `project_pmc` reverts to zero-fill for every unplanned day. For an athlete
  with patchy recent history (e.g. returning from a break), this can quietly
  produce an artificially pessimistic taper verdict, flagged only by a
  caveat sentence buried in `state.md`'s prose, not by anything visually
  distinct.

- **A Rest/Travel day is only skipped from validation if its code block is
  literally empty.** If a Rest day carries any code at all — even an
  accidental leftover line — it's validated exactly like a Training session
  against methodology and discipline, which can produce a confusing
  hard-constraint failure on a day that was never meant to be checked.

- **A mismatched athlete `id` inside the YAML only warns, never blocks.**
  `build_profile.py`'s `render_declared()` compares the file's own `id:`
  field against the athlete id it was loaded for and, on a mismatch, only
  adds a warning banner inside `profile.md`'s markdown — `prep` still
  proceeds normally. A copy-pasted or misnamed athlete file can silently
  drive session design for the wrong person if that banner is scrolled past.

- **The monotony check (`CHK-MONO`) has no memory across separate `check`
  runs.** It only compares sessions within the single file being validated
  right now — a repeated architecture split across two files validated a
  week apart (a very plausible real workflow, since blocks are validated
  session-by-session or week-by-week) is invisible to it. Already an
  acknowledged open item in `RESTORE_POINT_v7.0.md`, not a new finding, but
  worth restating here as a live friction point in the actual workflow.

- **Curve-progression history has a hard floor that isn't retroactively
  fixable.** `review`'s curve-progression comparison is unavailable for any
  block that started before `capture_snapshot()` first ran for a given
  athlete — the docs frame this well as "resolves itself over time," but
  for any athlete already active before the feature shipped, that specific
  historical window is permanently unrecoverable, not merely pending.

---

## 5. Undocumented behavior — exists and works, mentioned nowhere in the manuals or architecture docs

Checked every `add_argument()` call in `coach.py`, `engine/*.py`,
`verify/validate_block.py`, `build_zone_tables.py`, and `tests/run_tests.py`,
plus a few code paths that are user-visible but never named, against
`manual/OPERATIONS_MANUAL.md`, `manual/QUICK_GUIDE.md`,
`WORKFLOW_CHECKLIST.md`, `ARCHITECTURE_v6.md`, and `IMPROVEMENT_BACKLOG.md`.
None of the items below appear in any of those five files.

**CLI flags:**

- **`coach.py prep --days`** (`coach.py:538`) — overrides the 180-day fetch
  window per-run. Every doc shows `prep <id>` bare; the option to fetch a
  shorter or longer history is never mentioned as available.
- **`fetch_athlete_data.py --outdir`** (`engine/fetch_athlete_data.py:474`)
  — redirects output away from `data/`. Relevant because
  `WORKFLOW_CHECKLIST.md` §C explicitly tells the reader each engine step
  "remains usable on its own," but never mentions this option exists on the
  fetch step.
- **`build_state.py --quiet`** (`engine/build_state.py:672`) and
  **`build_profile.py --quiet`** (`engine/build_profile.py:591`) — suppress
  console printing while still writing the files. `coach.py` uses both
  internally (`prep_one()` calls `bs.build(..., quiet=True)` and
  `bp.build(..., quiet=True)`), but a head coach running either script
  directly, as the checklist tells them they can, is never told the flag
  exists.
- **`validate_block.py --tss <value>`** (`verify/validate_block.py:908`) —
  supplies a declared TSS for a raw block with no `[Estimated TSS]` header
  field at all, so divergence can still be checked. Documented only in the
  script's own module docstring (`verify/validate_block.py:22`), never in
  any manual — and `coach.py check` has no way to pass it through at all,
  since `cmd_check()` only forwards `--methodology`/`--discipline`.
- **`validate_block.py --tolerance <pct>`** (`verify/validate_block.py:909`)
  — overrides the divergence tolerance normally read from
  `decision_thresholds.yaml`. Not mentioned anywhere outside the code.
- **`validate_block.py --athlete <id>`** (`verify/validate_block.py:910`) —
  loads `config/athletes/<id>.yaml` directly, as an alternative to the
  block header's `[Athlete ID]` field. Not documented, and (as noted in
  §3 above) not even reachable through `coach.py check`.
- **`validate_block.py --quiet`** (`verify/validate_block.py:911`) — omits
  the per-interval TSS breakdown, keeping only the pass/fail summary. Not
  mentioned in any manual, though `tests/run_tests.py` uses it internally
  when shelling out to the validator.
- **`build_zone_tables.py diff <reference-markdown-file>`**
  (`build_zone_tables.py:516`, implemented at `build_zone_tables.py:466`) —
  a whole third subcommand, diffing freshly generated zone tables against a
  reference file for migration checking. `WORKFLOW_CHECKLIST.md` §E and §F
  only ever show `validate` and `build`; `diff` is never named.
- **`tests/run_tests.py --unit` / `--golden` / `--blocks` / `--verbose`**
  (`tests/run_tests.py:775-780`) — every doc that mentions the test suite
  (`OPERATIONS_MANUAL.md` §11, `WORKFLOW_CHECKLIST.md` §A3/§E3/§H) shows
  only the bare command or `--update`; the ability to run just one category,
  or to print every passing test name with `--verbose`, is undocumented.

**Code paths (no flag needed — silent, automatic behavior):**

- **Spanish and bold-wrapped header-label translation**
  (`verify/validate_block.py:123` `HEADER_LABEL_TRANSLATIONS`, applied in
  `normalize_header_labels()` at `verify/validate_block.py:148`, called from
  `normalize_block()` at `verify/validate_block.py:176`) — `check`/
  `validate_block.py` silently rewrites `[Semana]`, `[Fecha]`,
  `[Categoría]`, `[Metodología]`, `[Disciplina]`, `[Enfoque]`,
  `[Duración]`, `[TSS Estimado]`, `[Ejecución]`, `[Nutrición]`, and
  `**[Week]**`-style bold wrapping into canonical English headers, **before
  validating**, and rewrites the file on disk whether or not the block
  ultimately passes. Given the whole system is bilingual by design (the
  prompt itself is explicit about producing Mexican Spanish athlete-facing
  text), this is exactly the kind of safety net a head coach would want to
  know exists — and no doc mentions it at all, not even the one line in
  `OPERATIONS_MANUAL.md` §6 that lists what `check` does.
- **Automatic repair of a missing ` ```text ` fence, a decorated
  `[Duration]` value (leading `~`, trailing parenthetical), and a bare `—`
  placeholder on a Rest/Travel session's Methodology/Discipline** — all in
  the same `normalize_block()` (`verify/validate_block.py:176-227`). Same
  observation: printed to the console as "Auto-corrected before
  validating," never mentioned in any manual.
- **`validate_block.py --fill-tss` also fills `[Duration]`, not only
  `[Estimated TSS]`.** `fill_tss()` (`verify/validate_block.py:860`) takes
  and writes both `computed_by_session` and `duration_by_session`, and
  `main()` prints "Wrote computed TSS into N header(s) **and Duration into
  N header(s)**" (`verify/validate_block.py:1140-1142`). Every description
  of `--fill-tss` — the script's own module docstring
  (`verify/validate_block.py:30-33`), `OPERATIONS_MANUAL.md` §6, and
  `WORKFLOW_CHECKLIST.md` §C Step 5 — describes it as writing TSS only.
  This is also a git-history-confirmed drift; see §6 below.

---

## 6. Stale docs — describing something the code has since changed, removed, or renamed

Checked the full commit history (51 commits) against every top-level doc
still presented as current (excluding `archive/RESTORE_POINT_v*.md`, which
are historical snapshots by design and are expected to describe a past
state).

- **`RESTORE_POINT_v7.0.md`'s own "Restoring" checklist is already stale,
  one commit after it was written.** Step 4 tells a fresh session to
  upload to the Project "both files from `generated/`, the 6 files in
  `Knowledge/Principles/` plus `Joe_Friel_...md` and
  `Steve_Palladino_...md`... the syntax reference,
  `config/athletes/ATHLETE_INTAKE.md`, and `config/tss_classes.yaml`" —
  and does not list `config/athletes/_template.yaml`. Commit `39f3687`
  ("Add config/athletes/_template.yaml to the Project's required
  Knowledge"), made *after* `e286548` (the commit that added
  `RESTORE_POINT_v7.0.md`), added that file to
  `Prompt/infame_elite_endurance_coach.md`'s Inputs table as required
  Knowledge — specifically because its absence was causing the model to
  invent nonexistent YAML field names during every real intake. `git log`
  confirms `RESTORE_POINT_v7.0.md` has never been touched since the commit
  that created it. This is the exact same failure mode the file's own §2c
  and this repo's history describe fixing for the MCP server: a restore
  point frozen at one moment, describing an upload/setup checklist that a
  later commit changed, with nobody updating the restore point afterward.
- **`--fill-tss` writing `[Duration]`, not just `[Estimated TSS]`, is
  undocumented everywhere it's described.** Commit `544cf2f`
  ("validate_block: auto-fill Duration from computed steps, accept pending
  like TSS") and the following `4a94e36` ("Prompt: declare Duration as
  pending, same as TSS — engine is sole source of truth for both") added
  this behavior. `verify/validate_block.py`'s own module docstring
  (lines 30-33) was never updated to match — it still describes
  `--fill-tss` as writing only `[Estimated TSS]`. `OPERATIONS_MANUAL.md` §6
  and `WORKFLOW_CHECKLIST.md` §C Step 5 have the same gap: both talk at
  length about the TSS half of `--fill-tss` and never say Duration is
  computed and written the same way. This is a real, working feature with
  a stale description in three places, including the source file itself.
- **The test count was correctly fixed once, then drifted again with no
  second fix.** Commit `7a08b06` ("Remove stale MCP server references;
  rewrite manuals for a first-time reader") explicitly corrected "the stale
  67-test count to 76." Since then the suite grew through `251e236`
  (Spanish/bold header handling), `19a10f5` (validator v2.5), `eb416d1` /
  `fca7669` (taper + PMC fixes, "+14 new unit tests" per
  `RESTORE_POINT_v7.0.md` §2b), and `66f1d52` (goals description
  stripping, "+13" per its diff) — none of these updated
  `OPERATIONS_MANUAL.md` or `WORKFLOW_CHECKLIST.md`'s "76 tests" claim.
  This confirms §3's finding above is not a one-off oversight but the same
  class of drift recurring: the docs were accurate exactly once, right
  after someone deliberately re-counted, and have been silently falling
  behind every commit since.
- **Spanish-language manuals are gone; the working assumption that they
  still exist is out of date.** `manual/manual_operativo_infame_coach.md`
  and `manual/guia_rapida.md` were deleted in the same `7a08b06` commit
  above ("documentation is English-only going forward"). `manual/` today
  holds only `OPERATIONS_MANUAL.md` and `QUICK_GUIDE.md`. Noted here
  because it's a clean example of the exact pattern this section looks
  for — a real, dated commit removing something — even though nothing
  currently in the repo's own live docs still claims the Spanish versions
  exist (the removal was done cleanly).
- **No other renames or removals found that a current, live doc still
  describes the old way.** The other file moves in history — the six split
  Knowledge books (`7fc0346`), the `RESTORE_POINT_v5.1–v6.6.md` files into
  `archive/` (`dcd3d46`), `Athlete Template/` and `Excel to MD Converter/`
  into `legacy/` — are all correctly reflected in `RESTORE_POINT_v7.0.md`
  and the current manuals; `ARCHITECTURE_v6.md` already carries its own
  banner (added 2026-09-06) listing exactly where the built system diverged
  from that original design doc, which is why it wasn't flagged again here.
