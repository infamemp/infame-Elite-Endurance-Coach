# RESTORE POINT — Infame Elite Endurance Coach v6.1

**Date frozen:** 2026-08-22
**Git tag:** `v6.1-stage6`
**Previous restore points:** `v6.0-stage5`, `v5.1-stable`
**Status:** Stages 0–6 complete and running. Stage 7 (golden tests) not started.

---

## 1. Purpose

Two jobs. It freezes the definition of "working" for v6.1, and it is the handoff
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
│  ├─ athletes/         ATHLETE_INTAKE.md + _template.yaml (real profiles gitignored)
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
├─ generated/          zone tables built from config — NEVER hand-edited
├─ tests/blocks/       five verification fixtures
├─ Prompt/             infame_elite_endurance_coach.md v6.0 + archive/
├─ Knowledge/          6 book-derived KBs
├─ Syntax/             Intervals.icu workout builder reference
├─ Athlete Template/   intervals_export.py (Excel report)
├─ Excel to MD Converter/
├─ build_zone_tables.py
├─ ARCHITECTURE_v6.md
├─ RESTORE_POINT_v5.1.md
├─ RESTORE_POINT_v6.0.md
└─ RESTORE_POINT_v6.1.md
```

**Not in git:** `data/` (athlete data), `config/athletes/*.yaml` except the
template, `*.xlsx`. The API key lives in the `ICU_API_KEY` environment variable.

---

## 4. Daily workflow

```
python engine/fetch_athlete_data.py --athlete <id>     # pull from Intervals.icu
python engine/build_state.py --athlete <id>            # resolve state → state.md
```
Paste `state.md` into the Claude Project alongside the `#SESSION` header. Design
the block in conversation. Then:
```
python verify/validate_block.py <file> --fill-tss      # gate + TSS
```
A block that fails is corrected and re-verified. It is never uploaded.

Config maintenance:
```
python build_zone_tables.py validate    # schema-check the 8 authors
python build_zone_tables.py build       # regenerate the zone tables
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
pass. Treadmill ramps blocked without the athlete-profile flag, permitted with it —
both paths tested.

**Engine.** Fetches 180 days of wellness, PMC series, activities, events, and
power/pace curves across 42d/90d/1y windows. State resolution validated against
real data and confirmed to match the coach's own judgement.

**Longitudinal analysis (Stage 6).** Separates trend (42d vs 90d) from level (42d
as a percent of the 1y best), because the windows are nested and the 1y comparison
is unfair by construction. Reports durability direction, anaerobic repeatability,
and an adaptation state assembled from all three with its evidence attached.
Refuses to read phenotype from values below the Coggan table floor, since for a
training athlete that means the effort was never made. Emits per-anchor testing
recommendations with duration-based protocols, plus data-quality flags for
underestimated W' and non-endurance sessions in the log.

**Prompt v6 in the Project.** Phase 0 gating returns a single-sentence prompt with
no data. With `#SESSION` but no `#STATE`, it names the rebuild command, refuses to
estimate, and stops.

---

## 6. Where the numbers come from

Nothing in the engine is invented. Every threshold traces to a source:

| Area | Source |
|:---|:---|
| Zone tables, 8 authors | The authors' own published zones, migrated verbatim |
| Cycling power cutpoints | Coach's own bands, verified against 14/14 zones of Coggan, Friel, Carmichael |
| Running power cutpoints | Palladino's zones, 9/9 agreement |
| Taper parameters | Bosquet et al. 2007 meta-analysis, 27 studies |
| Power profile and phenotype | Coggan power profile table |
| Running CP test protocol | Palladino, "Protocol for CP Testing" (2020) and his 2018 primer |
| Cycling testing week | Coach's own baseline protocol |
| Target TSB by event type | Coach heuristic — explicitly NOT from evidence, flagged as such in config |

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
`#SESSION` slimmed to carry no numbers.

---

## 8. Known open items

- **No golden tests** (Stage 7). Regression detection is still manual.
- **No athlete profiles exist yet.** `config/athletes/` holds only the template.
  Profile-dependent rules — treadmill ramps, trail metric overrides, cue language —
  do not apply to any athlete until one exists.
- **Bosquet and Ingham KBs** were discussed but not extracted into `Knowledge/`.
- **Target TSB ranges by event type** are coach heuristic, flagged in config.
- **`.gitignore` comments are in Spanish.** Project convention is English.
- **The 120-minute power anchor has no data.** Intervals.icu curve data stops at
  60 minutes. The anchor is declared for the day the API offers it.
- **The Coggan power profile is calibrated on road cyclists** and ranks in W/kg,
  so it reads heavier and multisport athletes as lower-category than their actual
  training state warrants. Read the category with that in mind.
- **Integration with the cycling workout engine** is designed but not started.
  See section 9.

---

## 9. Planned: workout engine integration

The `cycling-workout-engine-gemini` repository solves the same problem from the
automated side. Reviewed in full; the agreed direction is NOT to merge the
repositories but to share Layer 1 — the engine would read `config/authors/` instead
of its hardcoded single-author `zones.py`, and use `verify/validate_block.py` as its
output gate.

**Blocker to resolve first:** the two compute TSS incompatibly. The workout engine
uses `IF² × 100` with normalized power; Infame uses minutes × physiological class
multiplier. The likely resolution is that both are right in their domain — IF² where
power exists, class multipliers where it does not — but this must be settled before
anything is shared.

Also worth porting into Infame from that engine: `resolve_intensity.py`, which
solves work-segment intensity in closed form to hit a TSS target rather than
computing TSS after the fact; its budget-ceiling, zone-containment and post-build IF
checks; and its 77-test suite as the model for Stage 7.

---

## 10. Restoring

1. Download the `v6.1-stage6` release from GitHub.
2. Replace the Claude Project instructions with `Prompt/infame_elite_endurance_coach.md`.
3. Upload to the Project: both files from `generated/`, the 6 KBs from `Knowledge/`,
   the syntax reference, `config/athletes/ATHLETE_INTAKE.md`, and
   `config/tss_classes.yaml`.
4. Confirm `ICU_API_KEY` is set, then run `build_zone_tables.py validate` as a
   smoke test — it should report 8/8.

Earlier points: `v6.0-stage5` restores the system before longitudinal analysis;
`v5.1-stable` restores the pre-refactor system.
