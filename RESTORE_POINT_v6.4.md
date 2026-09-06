# RESTORE POINT — Infame Elite Endurance Coach v6.4

**Date frozen:** 2026-09-06
**Git tag:** `v6.4-results` (tag this commit once pushed)
**Previous restore points:** `v6.3-workflow`, `v6.2-complete`, `v6.1-stage6`,
`v6.0-stage5`, `v5.1-stable`
**Status:** The system can now measure whether a block worked, not just
generate and verify one. In production use across 17 athletes.

---

## 1. Purpose

Two jobs, as always: freezes the definition of "working" for v6.4, and is
the handoff brief for a new conversation to resume from without
re-deriving anything.

v6.4 does not change the four-layer architecture. It closes the gap
identified at the end of v6.3's session: the system could generate a plan
and verify it before upload, but nothing measured whether the plan
actually worked. It also fixes a dormant bug in the regression suite found
while building this.

---

## 2. What's new

### `coach.py review <id> --since <date>`

Compares an athlete's signals between a past date and today, writing
`out/<athlete_name>/review.md`:

- **CTL/ATL/TSB and ACWR** — fully reconstructable from the 180-day
  `pmc_series`/`activities` window `fetch_athlete_data.py` already pulls.
  Works immediately, for any athlete, no waiting required.
- **Durability** (median decoupling) — same 180-day window, same immediacy.
- **Curve progression** — needs a dated snapshot near the requested date
  (see below). Honestly reports "no history yet" rather than faking a
  comparison until one exists.
- **Race results** — folds in any `#RACE_RESULT` entry from
  `out/<athlete_name>/race_notes.md` whose date falls in the window.

### Dated curve snapshots

Intervals.icu's curve endpoint (`curves.power`/`curves.pace`) returns only
the best value in a window **as of today** — never a historical one. There
is no way to ask it "what were this athlete's curves on 2026-07-15."
`coach.py prep` now writes a lightweight snapshot
(`data/<id>/history/<date>.json`, just the curve data) on every run,
non-blocking, so curve progression becomes answerable starting from
whenever this shipped — never retroactively. All 17 athletes have their
first snapshot as of this restore point; the first genuinely useful
progression comparison is still weeks away by construction, not by defect.

### `#RACE_RESULT` in the prompt

Phase 6 (Macrocycle Close / Race Debrief) now emits a small structured
block after evaluating a completed race, mirroring how `#SESSION`
already solves the same problem for continuity:

```
#RACE_RESULT
Date:           [race date]
Race:           [race name]
Result:         [time/placement/outcome as reported]
Vs plan:        [met / exceeded / missed] target of [the stated goal]
Context:        [confounding factors, if any, or "none reported"]
Retest flagged: [yes/no, per the KB recommendation]
```

The athlete appends it (never overwrites) to `out/<id>/race_notes.md`, and
the phase now `STOP AND WAIT`s for confirmation it was saved before
offering to start a new macrocycle — the same discipline that protects
`continuity.md`.

### `acwr_signal(data, as_of=None)`

Generalized to accept an optional reference date, defaulting to
`date.today()` — the exact behavior every existing caller and the golden
suite already relied on. This is what lets `review` reconstruct a past
ACWR reading without any new data collection: activities are already
pulled 180 days back, so any window ending on a past date is already in
hand.

---

## 3. Bug found and fixed: golden tests rot with real time

**Symptom:** all 7 golden fixtures failed identically —
`acute_7d: 0, expected <real value>` — with no code change to explain it.

**Cause:** `tests/fixtures/<case>/athlete_data.json` dates are computed
relative to whenever `make_fixtures.py` was last run (deliberately, per its
own docstring, so a fixture never ages out of a rolling window). But
`run_tests.py` never re-ran the generator — it read whatever fixture
happened to be sitting on disk. A fixture generated once and left
uncommitted-to-again silently drifts out of its own 7/28-day windows as
real time passes, failing for a reason that has nothing to do with any
code change. This is the same class of bug fixtures were designed to avoid
against the *athlete's* data — it just wasn't applied to the *test
harness's own* freshness.

**Fix:** `golden_tests()` now calls `make_fixtures.main()` to regenerate
every fixture immediately before comparing. Verified in three scenarios:
a normal run (unaffected), a fixture deliberately corrupted with dates 6
months stale (self-heals, passes), and `--update` mode (still writes
identical values, confirming the relative-date design really is
deterministic regardless of which real day it runs on).

**Confirmed test count: 76.** Neither `README.md`'s prior "75" nor
`WORKFLOW_CHECKLIST.md`'s prior "67" was correct — both have been
corrected to match the real, verified count from `python tests/run_tests.py`.

---

## 4. Also resolved this session

| Item | Resolution |
|:---|:---|
| No `User-Agent` header on Intervals.icu requests | Cloudflare (which fronts the API) can silently challenge or block bare-Python clients per the official API guide; a browser-shaped `User-Agent` was added to `make_session()` |
| `render_review`'s race-notes path message used the unsanitized athlete name | Fixed to use the same `safe_filename()`-sanitized `dest_name` the file is actually written under |
| `pmc_at()` returned raw, unrounded CTL/ATL floats | Rounded to 1 decimal, matching the convention `latest_pmc()` already used |
| `ARCHITECTURE_v6.md`, `README.md` diverged from the built system's actual naming and structure | `ARCHITECTURE_v6.md` kept as-written (it's a dated design doc) with an implementation note added at the top; `README.md` — a living doc — updated directly: commands, repo tree, test count, changelog |
| Root-level clutter: 4 restore points, 2 folders of retired scripts and generated Excel files | `legacy/` and `archive/` introduced; generated `.xlsx`/`athlete_docs/` deleted (already gitignored) |
| `out/` was briefly committed to git with real athlete PII while the repo was public | Untracked with `git rm -r --cached`, added to `.gitignore`; a follow-up PowerShell `echo >>` corrupted that same `.gitignore` line with UTF-16 encoding and a missing newline — rewritten cleanly and confirmed with `git check-ignore` |
| `WORKFLOW_CHECKLIST.md` §C still described the pre-`coach.py` 3-step manual process | Rewritten to use `coach.py prep`/`out/`/`continuity.md`; cross-referenced against `manual/OPERATIONS_MANUAL.md` |

---

## 5. Repository layout — changes since v6.3

```
data/<id>/
├─ athlete_data.json
├─ state.md / state.json
├─ profile.md
└─ history/<date>.json      NEW — dated curve snapshots, written by prep

out/<athlete_name>/
├─ state.md
├─ profile.md
├─ continuity.md
├─ race_notes.md            NEW — #RACE_RESULT blocks, appended by hand
└─ review.md                NEW — written by coach.py review

Athlete Template/           REMOVED — intervals_export.py moved to legacy/
Excel to MD Converter/      REMOVED — convert.py moved to legacy/
legacy/                     NEW — the two retired scripts above
archive/                    NEW — RESTORE_POINT_v5.1/v6.0/v6.1/v6.2.md
```

Everything else matches `RESTORE_POINT_v6.3.md` §3 exactly.

---

## 6. Known open items

Carried over from v6.3, still open: 16 of 17 athletes have no real profile
in `config/athletes/`; Bosquet and Ingham KBs not yet extracted; Friel
running shares the cycling KB; target TSB ranges are coach heuristic;
Coggan power profile under-ranks heavier/multisport athletes; cycling
workout engine integration not started; `eW'`/`ePmax` rule confirmed
against only one athlete; `build_profile.py` has no dedicated test
fixture; the `out/` PII exposure is closed going forward but not scrubbed
from git history (`git filter-repo`/BFG, coach's call); the
`continuity.md` staleness threshold (10 days) is hardcoded in `coach.py`
rather than living in `decision_thresholds.yaml` with every other
threshold.

New in v6.4:

- **`data/<id>/history/` has no retention limit.** One snapshot per
  athlete per `prep` run, unbounded. Not a problem yet at 17 athletes;
  worth a cap before it is one.
- **A dedicated MCP server exposing this engine** (`get_athlete_state`,
  `validate_block`, `push_block`, `list_roster` — not a generic wrapper
  around the raw Intervals.icu API, which would hand the model unresolved
  data and reintroduce the interpretation risk v6's `#STATE` contract
  exists to prevent) was scoped and explicitly deferred this session in
  favor of the results module. Next priority when resumed.
- **Uploading a verified block via the Intervals.icu API directly**
  (`POST /api/v1/athlete/{id}/events/bulk?upsert=true` — confirmed to
  accept the coach's native workout-description syntax and to return its
  own computed TSS as a free cross-check against the verifier's) remains
  unimplemented; still the last manual step in the daily loop.

---

## 7. Restoring

1. Download the `v6.4-results` release from GitHub (tag it if not done yet).
2. Replace the Claude Project instructions with
   `Prompt/infame_elite_endurance_coach.md`.
3. Upload to the Project: both files from `generated/`, the 8 KBs from
   `Knowledge/`, the syntax reference, `config/athletes/ATHLETE_INTAKE.md`,
   and `config/tss_classes.yaml`.
4. Confirm `ICU_API_KEY` is set, then run as a smoke test:
   - `python build_zone_tables.py validate` — expect 8/8
   - `python tests/run_tests.py` — expect **76/76**
   - `python coach.py prep --list` — expect all 17 athletes, refreshes
     `out/roster.md`
   - `python coach.py review <any id> --since <a date within the last
     180 days>` — expect CTL/ATL/TSB, ACWR and durability populated; curve
     progression will say "no history yet" until enough real time has
     passed since this restore point

Earlier points: `v6.3-workflow` before the daily-workflow unification,
`v6.2-complete` before that, `v6.1-stage6` before the regression suite,
`v6.0-stage5` before longitudinal analysis, `v5.1-stable` before the
refactor entirely.
