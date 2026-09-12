# RESTORE POINT — Infame Elite Endurance Coach v7.0

**Date frozen:** 2026-09-11
**Git tag:** `v7.0-taper-pmc-kb-split` (tag this commit once pushed)
**Previous restore points:** `v6.6-mcp-removed`, `v6.5-mcp`, `v6.4-results`,
`v6.3-workflow`, `v6.2-complete`, `v6.1-stage6`, `v6.0-stage5`, `v5.1-stable`
**Status:** Two long-standing engine bugs fixed, both with new regression
coverage that did not exist before this session. The Knowledge base is
now physically split into binding content and worked-example content,
closing the root cause behind repetitive session design that earlier
sessions could only patch at the prompt level.

---

## 1. Purpose

Same two jobs as every restore point: freezes the definition of "working"
for v7.0, and is the handoff brief for a new conversation to resume from.

v7.0 does not touch the four-layer architecture, the six-phase state
machine, or the MCP-free workflow `RESTORE_POINT_v6.6.md` established.
Everything true about the phases, the gates, and the STOP-AND-WAIT
discipline there still holds exactly. This restore point covers three
independent pieces of work done in the same session: two engine bugs
identified in the original v6.6 handoff, and the Knowledge base
restructure that had been sitting on the backlog since the monotony
diagnosis.

---

## 2. What changed

### 2a. `taper_check` now reads the declared profile, not Intervals.icu events

`engine/build_state.py`'s `taper_check` used to identify the next
A-priority race by filtering Intervals.icu events on `category == "RACE"`
and `priority in ("A", "RACE_A")`. Neither ever matched real data:
Intervals stores category as `RACE_A`/`RACE_B`/`RACE_C` directly, never
plain `"RACE"`, so the filter was silently empty for every real athlete
and the taper check never activated. `event_type` was also read from the
Intervals event's `type` field (the sport — Run/Ride/etc.), which never
matches the `target_tsb_by_event_type` keys (`marathon`, `ultra`,
`time_trial`, ...), so the target TSB range always fell back to default.

`taper_check` now takes the athlete's declared `goals[]`
(`config/athletes/<id>.yaml`) as its source for both priority and
`event_type` — the only place both are declared at the right granularity.
A new `load_declared_goals()` loads that file. Along the way, a second
bug surfaced and was fixed in the same function: YAML auto-parses an
unquoted `YYYY-MM-DD` scalar into a `date`/`datetime` object rather than
a string, which the original date-parsing helper did not expect.

New `taper_active` fixture (`tests/fixtures/taper_active/`) exercises the
`applicable: true` / verdict path for the first time — every existing
fixture had been hitting the "no races found" branch by accident, so this
part of `taper_check` had zero real coverage before now.

### 2b. PMC projection no longer assumes zero load on undeclared days

`project_pmc` filled every future day without an explicit Intervals.icu
event with zero training load. Most athletes do not log every future
session as a calendar event — they just keep training — so the projection
was reading as "no training at all between now and the race," decaying
ATL fast (7-day time constant) and producing misleadingly fresh projected
TSB.

New `weekday_load_pattern()` computes the athlete's historical average
load per weekday (trailing 8 weeks) and `project_pmc` falls back to it for
any day with no explicit event. An explicit event — including an explicit
zero, a declared rest day — always overrides the fallback. The pattern
itself requires real history (>=10 logged activities and >=3 weeks of
span) before it's trusted; short on either, the function falls back to
the old zero-fill behavior with an explicit caveat, which is what keeps
the `sparse` fixture refusing cleanly instead of extrapolating from noise.

14 new unit tests cover `weekday_load_pattern`'s two insufficient-history
gates and the explicit-vs-assumed override in `project_pmc` — previously
untested. All 8 existing golden fixtures updated (`projection.caveat` /
`days_with_assumed_load`, and `taper_active`'s `projected_tsb_at_race`,
which moves from a zero-fill 17.6 to a more realistic 12.3 while staying
in the same target range).

### 2c. Knowledge base split into `Principles/` and `Catalogs/`

Six of the eight book-derived KB files mixed two kinds of content in the
same file: binding content (zone definitions, work:rest ratios, ceilings,
progression rules — needed to construct any session) and the author's own
named worked examples (workout tables, weekly/seasonal plans). The coach
was treating the worked examples as a menu to select from rather than as
calibration references, which was the diagnosed root cause of repetitive
session design (see the "Diagnosed root cause of repetitive sessions" note
carried from the prior session).

Each of the six was split at the exact line ranges identified by content,
not by section title alone — several sections titled things like "Workout
Catalog" or "Individual Workouts Library" turned out to be binding
zone/type definitions on inspection, while some ordinary-looking chapters
turned out to contain full named weekly plans. Every split was verified
character-for-character against the source before and after: nothing was
reworded, summarized, or lost — only moved, with a short editorial note
left at each seam pointing to the sibling file.

- `Knowledge/Principles/<book>.md` — loaded in the Project. Physiological
  targets, ratios, ceilings, anchors, progression and recovery rules.
- `Knowledge/Catalogs/<book>.md` — not loaded by default. The author's own
  worked examples, kept for calibration only.

Split: Mujika, Jason Koop, Chris Carmichael, Wolfgang Olbrich, Allen &
Coggan, Jack Daniels. **Not split** — reviewed in full, no named worked
plan or session table found in either, only workout-type definitions:
Joe Friel, Steve Palladino. Originals of the six split books moved to
`archive/Knowledge_legacy/`.

`Prompt/infame_elite_endurance_coach.md`'s `<session_design>` section
("Knowledge files: binding constraints versus worked examples") and its
Inputs table were rewritten to reflect the physical split — the model no
longer has to infer binding-vs-catalog content by eye inside one mixed
file; only `Knowledge/Principles/` loads by default, and a `Catalogs/`
file supplied ad hoc is still never a menu.

---

## 3. Repository layout — changes since v6.6

```
engine/
└─ build_state.py            taper_check + project_pmc rewritten;
                              new weekday_load_pattern(), load_declared_goals()

tests/
├─ run_tests.py              +14 unit tests; build_for_fixture() now also
│                             copies a fixture's declared_profile.yaml
├─ make_fixtures.py          +case_taper_active, +declared_profile_taper_active
└─ fixtures/taper_active/    NEW — first fixture exercising taper_check's
                              applicable=true / verdict path

Knowledge/
├─ Principles/                NEW — 6 files, loaded in the Project
├─ Catalogs/                  NEW — 6 files, not loaded by default
├─ Joe_Friel_...md            unchanged, single file
└─ Steve_Palladino_...md      unchanged, single file

archive/
└─ Knowledge_legacy/          NEW — the 6 original combined KB files

Prompt/
└─ infame_elite_endurance_coach.md   <session_design> + Inputs table updated
                                     for the Principles/Catalogs split

README.md                     Knowledge/ description updated
```

Everything else matches `RESTORE_POINT_v6.6.md` §3 exactly.

---

## 4. Consequence: taper and PMC numbers will look different for real athletes

The first `coach.py prep` run for each athlete after pulling this update
will show a materially different PMC projection and taper verdict than
before — this is the fix working, not a regression. Athletes whose
calendars have no explicit future Intervals.icu events (most of them)
will see a projected TSB closer to their actual recent training load
instead of an artificial "no training at all" decay, and any athlete with
a declared A-priority goal in their `config/athletes/<id>.yaml` will get
a real taper verdict for the first time instead of "no races on the
calendar."

Separately, the six re-split KB files mean re-uploading the Project
knowledge: drag `Knowledge/Principles/` (all 6) plus `Joe_Friel_...md` and
`Steve_Palladino_...md` in place of the old flat 8-file `Knowledge/`.
`Knowledge/Catalogs/` is not uploaded by default.

---

## 5. Known open items

Carried over from v6.6, still open: 16 of 17 athletes have no real profile
in `config/athletes/`; Bosquet and Ingham KBs not yet extracted (Bosquet
resolved as not needed); Friel running shares the cycling KB; target TSB
ranges are coach heuristic; Coggan power profile under-ranks
heavier/multisport athletes; cycling workout engine integration not
started; `eW'`/`ePmax` rule confirmed against only one athlete;
`build_profile.py` has no dedicated test fixture; the `out/` PII exposure
is closed going forward but not scrubbed from git history; the
`continuity.md` staleness threshold (10 days) is hardcoded in `coach.py`
rather than living in `decision_thresholds.yaml`; `data/<id>/history/` has
no retention limit.

Also still open, unrelated to this session's work: the monotony detector
(`CHK-MONO`) has no unit tests in `tests/run_tests.py` yet, and only
compares sessions within the same file being validated — it does not yet
read `continuity.md`/`#SESSION` to compare against blocks already
uploaded in prior sessions. The prompt v7.0 has never been used to
generate a real block end-to-end inside the Claude Project — everything
built so far has been verified from the command line only.

Closed in v7.0:
- **`taper_check` never activating on real data** — resolved by reading
  the declared profile instead of Intervals.icu event fields. No longer
  an open item.
- **PMC projection understating future CTL on unplanned days** — resolved
  by the weekday historical fallback. No longer an open item.
- **KB files acting as a copy-paste menu** — resolved by the physical
  Principles/Catalogs split for the six books that had worked-example
  content. No longer an open item for those six; Friel and Palladino were
  confirmed to never have had it.

New in v7.0:
- **Project knowledge re-upload required.** The six re-split KB files
  mean the live Claude Project's uploaded knowledge is now stale until
  someone re-drags the new `Knowledge/Principles/` files in. See §4.

---

## 6. Restoring

1. Confirm `engine/build_state.py` has `weekday_load_pattern()` and
   `load_declared_goals()`, and that `taper_check`'s signature is
   `taper_check(projection, goals, thresholds)` — not `(projection,
   events, thresholds)`.
2. Confirm `Knowledge/` contains `Principles/` and `Catalogs/` (6 files
   each) plus the two unsplit files (Friel, Palladino), and that
   `archive/Knowledge_legacy/` holds the 6 originals.
3. Replace the Claude Project instructions with
   `Prompt/infame_elite_endurance_coach.md`.
4. Upload to the Project: both files from `generated/`, the 6 files in
   `Knowledge/Principles/` plus `Joe_Friel_...md` and
   `Steve_Palladino_...md` from `Knowledge/` directly, the syntax
   reference, `config/athletes/ATHLETE_INTAKE.md`, and
   `config/tss_classes.yaml`. **Do not upload `Knowledge/Catalogs/`.**
5. Confirm `ICU_API_KEY` is set, then run as a smoke test:
   - `python build_zone_tables.py validate` — expect 8/8
   - `python tests/run_tests.py` — expect 192/192
   - `python coach.py prep --list` — expect all 17 athletes

Earlier points: `v6.6-mcp-removed` before this session's fixes (kept at
the repo root until superseded again), `v6.5-mcp` before that (in
`archive/` as the full MCP incident history), `v6.4-results` before the
results module, `v6.3-workflow` before the daily-workflow unification,
`v6.2-complete` before that, `v6.1-stage6` before the regression suite,
`v6.0-stage5` before longitudinal analysis, `v5.1-stable` before the
refactor entirely.
