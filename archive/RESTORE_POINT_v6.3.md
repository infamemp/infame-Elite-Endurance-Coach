# RESTORE POINT — Infame Elite Endurance Coach v6.3

**Date frozen:** 2026-09-04
**Git tag:** `v6.3-workflow` (tag this commit once pushed)
**Previous restore points:** `v6.2-complete`, `v6.1-stage6`, `v6.0-stage5`, `v5.1-stable`
**Status:** Daily workflow unified under a single entry point. The system is in
production use across 17 athletes.

---

## 1. Purpose

Two jobs. It freezes the definition of "working" for v6.3, and it is the handoff
brief: a new conversation can read this file plus `ARCHITECTURE_v6.md` and resume
without re-deriving anything.

v6.3 does not change the four-layer architecture or any coaching logic. It closes
the daily-workflow gap identified in production use: three separate manual steps
(Excel export, sheet-splitting, markdown conversion) that had drifted out of sync
with the engine, cost real Avg Power data for weeks, and left every athlete folder
identified only by Intervals id.

---

## 2. What v6 is

Unchanged from v6.2. A four-layer system that separates deterministic computation
from coaching judgement, so both can be good at once.

| Layer | Location | Responsibility |
|:---|:---|:---|
| 1 — Configuration | `config/` | All coaching knowledge as schema-governed data |
| 2 — Engine | `engine/` | Fetch, resolve state, render profile, project PMC, longitudinal analysis |
| 3 — Reasoning | Claude Project | Methodology, session design, conversation |
| 4 — Verification | `verify/` | Hard-constraint gate before anything reaches an athlete |

**The governing rule (contract C3):** the `#STATE` block produced by Layer 2 is
authoritative. The model reads it, prescribes on top of it, and never recalculates
or contradicts it. `profile.md` (new in v6.3) carries no interpreted signal — it
is raw context only, precisely to avoid a second source of truth for any number
`#STATE` already owns.

---

## 3. Repository layout

```
infame_elite_endurance_coach/
├─ coach.py             single entry point: prep / new / check
├─ config/
│  ├─ authors/          8 methodologies as YAML + _template.yaml
│  │                    (carmichael declares a non-threshold `anchor`)
│  ├─ athletes/         ATHLETE_INTAKE.md, _template.yaml, TESTRAMP.yaml,
│  │                    1 real profile (i18969.yaml) — 16 more athletes are
│  │                    engine-only, never onboarded through intake
│  ├─ schema/           author.schema.json
│  ├─ decision_thresholds.yaml
│  ├─ tss_classes.yaml
│  └─ power_profile.yaml
├─ engine/
│  ├─ fetch_athlete_data.py    Intervals.icu → data/<id>/athlete_data.json
│  │                            (v1.1 — now also carries age, city, country,
│  │                            per-sport pace units and eFTP; events carry
│  │                            distance)
│  ├─ build_state.py           → data/<id>/state.md and state.json
│  ├─ build_profile.py         → data/<id>/profile.md (new in v6.3 — retires
│  │                            intervals_export.py + convert.py from the
│  │                            daily path)
│  ├─ longitudinal.py          curve progression, durability, repeatability
│  └─ power_profile.py         Coggan ranking and phenotype
├─ verify/
│  └─ validate_block.py        hard-constraint gate + TSS audit + --fill-tss
├─ tests/
│  ├─ make_fixtures.py         generates 7 synthetic athletes
│  ├─ run_tests.py             67 tests: unit, block, golden
│  ├─ fixtures/                datasets + frozen expected outputs
│  └─ blocks/                  workout-block verification fixtures
├─ generated/          zone tables built from config — NEVER hand-edited
├─ out/<athlete_name>/ what gets dragged into the Claude Project (new in v6.3)
│  ├─ state.md, profile.md     copied here by `coach.py prep`
│  ├─ continuity.md            the coach's own paste-once file — never
│  │                           written or overwritten by any script
│  └─ roster.md                name ↔ id ↔ last-fetch date, at out/ root
├─ manual/             OPERATIONS_MANUAL.md + QUICK_GUIDE.md (English, repo)
│                       and their Spanish counterparts (new in v6.3)
├─ Prompt/             infame_elite_endurance_coach.md v6.1 + archive/
├─ Knowledge/          8 book-derived KBs
├─ Syntax/             Intervals.icu workout builder reference
├─ legacy/             intervals_export.py, convert.py — retired from the
│                       daily path in v6.3, kept for reference (new)
├─ build_zone_tables.py
├─ ARCHITECTURE_v6.md
├─ IMPROVEMENT_BACKLOG.md
├─ WORKFLOW_CHECKLIST.md      cross-references manual/OPERATIONS_MANUAL.md
├─ RESTORE_POINT_v6.3.md      current
└─ archive/            RESTORE_POINT_v5.1/v6.0/v6.1.md (new — moved out of
                        the repo root to cut root-level clutter)
```

**Not in git:** `data/`, `out/` (added to `.gitignore` in v6.3 — see §7),
`config/athletes/*.yaml` except the template and TESTRAMP, `*.xlsx`,
`athlete_docs/`, `__pycache__/`. The API key lives in the `ICU_API_KEY`
environment variable.

`Athlete Template/` and `Excel to MD Converter/` no longer exist — their
scripts moved to `legacy/`, their generated `.xlsx`/`athlete_docs/` outputs
were deleted (they were already gitignored, so this is a local-only cleanup).

---

## 4. Daily workflow

Full step-by-step in `WORKFLOW_CHECKLIST.md` (system setup and maintenance) and
`manual/OPERATIONS_MANUAL.md` (day-to-day athlete routine). In short:

```
python coach.py prep <id>
# drag out/<athlete_name>/ (state.md, profile.md, continuity.md if present)
# into the Claude Project, design the block in conversation
python coach.py check <file>
```

Onboarding a new athlete:
```
python coach.py new <id>
```

After any change to `config/` or `engine/`:
```
python tests/run_tests.py
```

---

## 5. Confirmed working

Everything from v6.2's §5 still holds — the engine, verification gate,
non-threshold anchors, and longitudinal analysis are unchanged in v6.3. New
in this restore point:

**`fetch_athlete_data.py` v1.1.** Extended profile (age, city, country,
per-sport pace units, eFTP-by-category) confirmed against a real athlete's
data end to end. Reuses the same duplicate-row merge already fixed in
`intervals_export.py` — the account's `athlete-summary.json` can return two
rows per athlete, and the merge is now shared logic, not fixed twice.

**`build_profile.py`.** Renders `profile.md` from `athlete_data.json` —
personal info, sport configuration with eFTP and formatted threshold pace,
race calendar with distance, planned sessions, 28-day activity history
(including Avg Power, decoupling, efficiency factor, VI), and a computed
context snapshot. Verified field-by-field against the athlete's previous
Excel-based document, including two real discrepancies caught and fixed:
sport distribution is by activity count (not time or load — matches the old
export exactly), and generic calendar entries with no `type` default to
"Workout" rather than a blank. A separate bug (crash on an athlete with zero
activities in the trailing window) was caught in production against three
real inactive/test athletes and fixed. Deliberately does not render `eW'` or
`ePmax` — the rule for which curve model/window to use was only confirmed
against one athlete.

**`coach.py` v1.1.** Adds `prep` (now runs fetch → state → profile in one
call and delivers to a named `out/` folder instead of `data/<id>/`, which
was previously identifiable only by Intervals id), `new` (onboarding,
confirms the id is real before creating a config, never overwrites an
existing profile), and a `continuity.md` presence/age check on every `prep`
run. `out/roster.md` is regenerated on every `prep` call from the full
athlete list, not just the one(s) touched in that run.

**Prompt v6.1 → 6.1 (2026-09-04 revision).** `#SESSION` can now be requested
on demand mid-block, not only at block-end — closes the gap where an
off-calendar mid-week consult in a fresh chat had no continuity artifact to
resume from.

---

## 6. Where the numbers come from

Unchanged from v6.2 — no new coaching-science source was introduced in v6.3.
This restore point is infrastructure work, not methodology work.

| Area | Source |
|:---|:---|
| Zone tables, 8 authors | The authors' own published zones, migrated verbatim |
| Carmichael anchor factor 1.10 | The Time-Crunched Cyclist 3rd ed., Ch. 4 — field test power is ~10% above LT power |
| Cycling power cutpoints | Coach's own bands, verified against 14/14 zones of Coggan, Friel, Carmichael |
| Running power cutpoints | Palladino's zones, 9/9 agreement |
| Taper parameters | Bosquet et al. 2007 meta-analysis, 27 studies |
| Power profile and phenotype | Coggan power profile table |
| Running CP test protocol | Palladino, "Protocol for CP Testing" (2020), his 2018 primer, and his analysis video |
| Cycling testing week | Coach's own baseline protocol |
| Delta bands, durability and repeatability thresholds | Coach heuristic, tuned against real athlete data |
| Target TSB by event type | Coach heuristic — explicitly NOT evidence, flagged as such in config |

---

## 7. Resolved since v6.2

| Defect | Resolution |
|:---|:---|
| Local `intervals_export.py` never received the Aug fixes | Confirmed line-by-line against the GitHub copy (which was already correct); the discrepancy was an uncommitted local file, not a repo bug |
| `build_profile.py` crashed on an athlete with zero recent activities | `render_history` returned a bare list instead of the `(lines, activities)` tuple `build()` expected; fixed and verified against both an empty and a populated case |
| `out/` was committed to git with real athlete PII, repo was public | Untracked with `git rm -r --cached`, added to `.gitignore`, repo set back to private |
| `.gitignore`'s new `out/` line was corrupted | `echo >> .gitignore` in PowerShell writes UTF-16 and doesn't add a trailing newline, fusing the new rule onto the previous line as unreadable bytes; rewritten cleanly and confirmed with `git check-ignore` |
| `WORKFLOW_CHECKLIST.md` §C described the pre-`coach.py` 3-step manual process | Rewritten to use `coach.py prep`, `out/<name>/`, and `continuity.md`; cross-referenced against `manual/OPERATIONS_MANUAL.md` so the two no longer risk drifting apart silently |
| Root-level clutter — 4 restore points, 2 folders of retired scripts and generated Excel files | `legacy/` and `archive/` introduced; generated `.xlsx`/`athlete_docs/` deleted (already gitignored) |

Also: sport-distribution metric in `build_profile.py` corrected to match the
legacy export (activity count, not time); generic calendar entries default
to "Workout" instead of a blank `Type`.

---

## 8. Known open items

Carried over from v6.2, still open:

- **16 of 17 athletes have no real profile in `config/athletes/`.** They
  were coached before this system existed and never went through intake.
  `coach.py new <id>` now makes this a five-minute task per athlete when
  there's time to do it — not done as part of v6.3.
- **Bosquet and Ingham KBs** were discussed but not extracted into `Knowledge/`.
- **Friel running has no KB of its own** — it currently shares the cycling
  Training Bible.
- **Target TSB ranges by event type** are coach heuristic, flagged in config.
- **The Coggan power profile is calibrated on road cyclists** and ranks in
  W/kg, so it reads heavier and multisport athletes as lower-category than
  their actual training state warrants.
- **Integration with the cycling workout engine** is designed but not started.

New in v6.3:

- **`eW'`/`ePmax` are not rendered in `profile.md`.** The rule (model
  `FFT_CURVES`, 90d window) was confirmed against one athlete only. Needs
  checking against 3–4 more before it can be trusted generally.
- **`build_profile.py` has no fixture of its own in `tests/`.** The other
  two engine scripts are covered by the 67-test suite; this one was
  verified by hand this session. The crash fixed in §7 would have been
  caught earlier with a fixture carrying zero activities.
- **The `out/` PII exposure window is closed going forward, not scrubbed
  from git history.** `git rm --cached` stops future commits from carrying
  it; the already-pushed commits still contain it until a history rewrite
  (`git filter-repo` or BFG) is run. Left as the coach's call — low
  realistic risk given the short public window and that this is a
  single-maintainer repo, but not automatically safe.
- **`config/decision_thresholds.yaml` does not yet hold the `continuity.md`
  staleness threshold** (10 days, hardcoded in `coach.py`). Minor — flagged
  for consistency with how every other threshold in the system is stored.

Full list with reasoning in `IMPROVEMENT_BACKLOG.md` (not yet updated with
v6.3's items as of this restore point).

---

## 9. Restoring

1. Download the `v6.3-workflow` release from GitHub (tag it if not done yet).
2. Replace the Claude Project instructions with `Prompt/infame_elite_endurance_coach.md`.
3. Upload to the Project: both files from `generated/`, the 8 KBs from `Knowledge/`,
   the syntax reference, `config/athletes/ATHLETE_INTAKE.md`, and
   `config/tss_classes.yaml`.
4. Confirm `ICU_API_KEY` is set, then run as a smoke test:
   - `python build_zone_tables.py validate` — expect 8/8
   - `python tests/run_tests.py` — expect 67/67
   - `python coach.py prep --list` — expect all 17 athletes, refreshes `out/roster.md`

Earlier points: `v6.2-complete` before the daily-workflow unification,
`v6.1-stage6` before the regression suite, `v6.0-stage5` before longitudinal
analysis, `v5.1-stable` before the refactor entirely.
