# RESTORE POINT — Infame Elite Endurance Coach v6.2

**Date frozen:** 2026-08-23
**Git tag:** `v6.2-complete`
**Previous restore points:** `v6.1-stage6`, `v6.0-stage5`, `v5.1-stable`
**Status:** All eight stages complete. The system is in production use.

---

## 1. Purpose

Two jobs. It freezes the definition of "working" for v6.2, and it is the handoff
brief: a new conversation can read this file plus `ARCHITECTURE_v6.md` and resume
without re-deriving anything.

---

## 2. What v6 is

A four-layer system that separates deterministic computation from coaching
judgement, so both can be good at once. v5.1 asked one language model to do
arithmetic, classification, and prescription in a single pass; v6 gives the first
two to code and leaves the third where it belongs.

| Layer | Location | Responsibility |
|:---|:---|:---|
| 1 — Configuration | `config/` | All coaching knowledge as schema-governed data |
| 2 — Engine | `engine/` | Fetch, resolve state, project PMC, longitudinal analysis |
| 3 — Reasoning | Claude Project | Methodology, session design, conversation |
| 4 — Verification | `verify/` | Hard-constraint gate before anything reaches an athlete |

**The governing rule (contract C3):** the `#STATE` block produced by Layer 2 is
authoritative. The model reads it, prescribes on top of it, and never recalculates
or contradicts it.

---

## 3. Repository layout

```
infame_elite_endurance_coach/
├─ config/
│  ├─ authors/          8 methodologies as YAML + _template.yaml
│  │                    (carmichael declares a non-threshold `anchor`)
│  ├─ athletes/         ATHLETE_INTAKE.md, _template.yaml, TESTRAMP.yaml
│  │                    (real athlete profiles are gitignored)
│  ├─ schema/           author.schema.json
│  ├─ decision_thresholds.yaml
│  ├─ tss_classes.yaml
│  └─ power_profile.yaml
├─ engine/
│  ├─ fetch_athlete_data.py    Intervals.icu → data/<id>/athlete_data.json
│  ├─ build_state.py           → data/<id>/state.md and state.json
│  ├─ longitudinal.py          curve progression, durability, repeatability
│  └─ power_profile.py         Coggan ranking and phenotype
├─ verify/
│  └─ validate_block.py        hard-constraint gate + TSS audit + --fill-tss
├─ tests/
│  ├─ make_fixtures.py         generates 7 synthetic athletes
│  ├─ run_tests.py             75 tests: unit, block, golden
│  ├─ fixtures/                datasets + frozen expected outputs
│  └─ blocks/                  workout-block verification fixtures
├─ generated/          zone tables built from config — NEVER hand-edited
├─ Prompt/             infame_elite_endurance_coach.md v6.1 + archive/
├─ Knowledge/          8 book-derived KBs
├─ Syntax/             Intervals.icu workout builder reference
├─ Athlete Template/   intervals_export.py (Excel report)
├─ Excel to MD Converter/
├─ build_zone_tables.py
├─ ARCHITECTURE_v6.md
├─ IMPROVEMENT_BACKLOG.md
├─ WORKFLOW_CHECKLIST.md
└─ RESTORE_POINT_*.md  (v5.1, v6.0, v6.1, v6.2)
```

**Not in git:** `data/`, `config/athletes/*.yaml` except the template and
TESTRAMP, `*.xlsx`, `athlete_docs/`, `__pycache__/`. The API key lives in the
`ICU_API_KEY` environment variable.

---

## 4. Daily workflow

Full step-by-step in `WORKFLOW_CHECKLIST.md`. In short:

```
python engine/fetch_athlete_data.py --athlete <id>
python engine/build_state.py --athlete <id>
# paste state.md into the Claude Project, design the block in conversation
python verify/validate_block.py <file> --fill-tss
```

After any change to `config/` or `engine/`:
```
python tests/run_tests.py
```

---

## 5. Confirmed working

**Config layer.** 8 authors schema-valid; zone tables regenerate from YAML with a
build date stamped in; cutpoint agreement reported at 66/78 with divergences
listed as author disagreements rather than errors.

**Verification gate.** Catches ramps in prohibited disciplines, format violations,
prescription-floor breaches, nested repeats, non-English section keywords, invalid
categories, incomplete Koop dual-layer, and Olbrich special-output-rule breaches.
Reads methodology and discipline from the session header. Recomputes TSS with the
source zone shown per interval. Fills `[Estimated TSS] pending` only on a clean
pass. Treadmill ramps blocked without the athlete-profile flag, permitted with it.

**Engine.** Fetches 180 days of wellness, PMC series, activities, events, and
power/pace curves across 42d/90d/1y windows. State resolution validated against
real athlete data and confirmed to match the coach's own judgement.

**Non-threshold anchors.** An author whose percentages are measured against
something other than functional threshold declares it in an `anchor` block. The
YAML keeps the author's own numbers; the generator emits an additional
threshold-equivalent column; the validator converts before matching a target, and
says so in the source it reports. Carmichael is the worked example, and the
mechanism is available to any future author who anchors differently.

**Longitudinal analysis.** Separates trend (42d vs 90d) from level (42d as a
percent of the 1y best), because the windows are nested and the 1y comparison is
unfair by construction. Reports durability direction, anaerobic repeatability, and
an adaptation state with its evidence attached. Refuses to read phenotype from
values below the Coggan table floor. Emits per-anchor testing recommendations with
duration-based protocols, plus data-quality flags.

**Regression suite.** 75 tests across three kinds. Verified to catch a real
regression: altering one config band failed both a unit test and a golden
comparison, each naming exactly what moved.

**Prompt v6.1 in the Project.** Phase 0 gating returns a single-sentence prompt with
no data. With `#SESSION` but no `#STATE`, it names the rebuild command, refuses to
estimate, and stops.

---

## 6. Where the numbers come from

Nothing in the engine is invented. Every threshold traces to a source:

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

## 7. Resolved since v5.1

| Defect | Resolution |
|:---|:---|
| D-1 ramps where prohibited | Moved into the Absolute Prescription Rules and enforced by the validator |
| D-2 vague TSS | Removed from the prompt entirely; computed by the engine from config |
| D-3 colloquial Execution/Nutrition | Three-line structure, positive rule requiring zone/class/target references |

Also: API key moved to an environment variable; duplicate `athlete-summary.json`
rows merged instead of discarded; `supra` split into VO2max, anaerobic and
neuromuscular; `sub_threshold` added; taper parameters replaced with Bosquet 2007;
`#SESSION` slimmed to carry no numbers; the intake split into a derived half and a
declared half.

---

## 8. Known open items

- **No real athlete profiles exist yet.** `config/athletes/` holds the template and
  the test fixture. Profile-dependent rules — treadmill ramps, trail metric
  overrides, cue language — apply to nobody until profiles are created.
- **Bosquet and Ingham KBs** were discussed but not extracted into `Knowledge/`.
- **Friel running has no KB of its own** — it currently shares the cycling
  Training Bible. Zones are correctly migrated; the methodology text is not his
  running material.
- **Target TSB ranges by event type** are coach heuristic, flagged in config.
- **`.gitignore` comments are in Spanish.** Project convention is English.
- **The 120-minute power anchor has no data.** Intervals.icu curve data stops at
  60 minutes. The anchor is declared for the day the API offers it.
- **The Coggan power profile is calibrated on road cyclists** and ranks in W/kg,
  so it reads heavier and multisport athletes as lower-category than their actual
  training state warrants.
- **Integration with the cycling workout engine** is designed but not started.

Full list with reasoning in `IMPROVEMENT_BACKLOG.md`.

---

## 9. Restoring

1. Download the `v6.2-complete` release from GitHub.
2. Replace the Claude Project instructions with `Prompt/infame_elite_endurance_coach.md`.
3. Upload to the Project: both files from `generated/`, the 6 KBs from `Knowledge/`,
   the syntax reference, `config/athletes/ATHLETE_INTAKE.md`, and
   `config/tss_classes.yaml`.
4. Confirm `ICU_API_KEY` is set, then run as a smoke test:
   - `python build_zone_tables.py validate` — expect 8/8
   - `python tests/run_tests.py` — expect 67/67

Earlier points: `v6.1-stage6` before the regression suite, `v6.0-stage5` before
longitudinal analysis, `v5.1-stable` before the refactor entirely.
