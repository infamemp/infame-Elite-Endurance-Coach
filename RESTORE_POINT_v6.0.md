# RESTORE POINT — Infame Elite Endurance Coach v6.0

**Date frozen:** 2026-08-20
**Git tag:** `v6.0-stage5`
**Previous restore point:** `v5.1-stable` (see `RESTORE_POINT_v5.1.md`)
**Status:** Stages 0–5 complete and running. Stages 6–7 not started.

---

## 1. Purpose

This document does two jobs. It freezes the definition of "working" for v6.0, and
it is the handoff brief: a new conversation can read this file plus
`ARCHITECTURE_v6.md` and resume without re-deriving anything.

---

## 2. What v6 is

A four-layer system that separates deterministic computation from coaching
judgement, so that both can be good at once. v5.1 asked one language model to do
arithmetic, classification, and prescription in a single pass; v6 gives the first
two to code and leaves the third where it belongs.

| Layer | Location | Responsibility |
|:---|:---|:---|
| 1 — Configuration | `config/` | All coaching knowledge as schema-governed data |
| 2 — Engine | `engine/` | Fetch, resolve state, project PMC — deterministic |
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
│  └─ tss_classes.yaml
├─ engine/
│  ├─ fetch_athlete_data.py    Intervals.icu → data/<id>/athlete_data.json
│  └─ build_state.py           → data/<id>/state.md and state.json
├─ verify/
│  └─ validate_block.py        hard-constraint gate + TSS audit + --fill-tss
├─ generated/          zone tables built from config — NEVER hand-edited
├─ tests/blocks/       five verification fixtures
├─ Prompt/             infame_elite_endurance_coach.md v6.0 + archive/
├─ Knowledge/          6 book-derived KBs
├─ Syntax/             Intervals.icu workout builder reference
├─ Athlete Template/   intervals_export.py (Excel report, unchanged role)
├─ Excel to MD Converter/
├─ build_zone_tables.py
├─ ARCHITECTURE_v6.md
├─ RESTORE_POINT_v5.1.md
└─ RESTORE_POINT_v6.0.md
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

- **Config layer.** 8 authors schema-valid; zone tables regenerate from YAML;
  cutpoint agreement reported at 66/78 with divergences listed as author
  disagreements rather than errors.
- **Verification gate.** Catches ramps in prohibited disciplines, `% FTP`/`% HR`
  format violations, raw watts/bpm/pace, prescription-floor breaches, nested
  repeats, non-English section keywords, invalid categories, incomplete Koop
  dual-layer, and Olbrich special-output-rule violations. Recomputes TSS with the
  source zone shown per interval. Fills `[Estimated TSS] pending` only on a clean
  pass.
- **Treadmill ramps.** Blocked without `ramp_overrides.treadmill_ramps_requested`
  in the athlete profile; permitted with it. Both paths tested.
- **Engine.** Fetches 180 days of wellness, PMC series, activities, events, and
  power/pace curves across 42d/90d/1y windows. State resolution validated against
  real data and confirmed to match the coach's own judgement.
- **Prompt v6 in the Project.** Phase 0 gating returns a single-sentence prompt
  with no data. With `#SESSION` but no `#STATE`, it names the rebuild command,
  refuses to estimate, and stops — and independently flagged a phase/block-position
  inconsistency in the test header.

---

## 6. Resolved since v5.1

| Defect | Resolution |
|:---|:---|
| D-1 ramps where prohibited | Moved into the Absolute Prescription Rules and enforced by the validator |
| D-2 vague TSS | Removed from the prompt entirely; computed by the engine from config |
| D-3 colloquial Execution/Nutrition | Three-line structure, positive rule requiring zone/class/target references |

Also: API key moved to an environment variable; duplicate `athlete-summary.json`
rows merged instead of discarded; `supra` split into VO2max, anaerobic and
neuromuscular; `sub_threshold` added; taper parameters replaced with Bosquet 2007.

---

## 7. Known open items

- **`Mujika_Tapering_Peaking_Extraction.md`** exists in `Knowledge/`. Bosquet and
  Ingham KBs were discussed but not yet extracted.
- **Target TSB ranges by event type** in `decision_thresholds.yaml` are coach
  heuristic, explicitly not from Bosquet. Worth revisiting from experience.
- **`.gitignore` comments are in Spanish.** Project convention is English
  throughout; a cleanup pass is pending.
- **No athlete profiles exist yet.** `config/athletes/` holds only the template.
  Each athlete needs one before profile-dependent rules apply to them.
- **No golden tests** (Stage 7). Regression detection is still manual.
- **Curve data is fetched but unused.** Stage 6 consumes it.

---

## 8. Next stages

**Stage 6 — Longitudinal intelligence.** Power-curve progression across rolling
windows, durability trends, anaerobic repeatability. The data is already in
`athlete_data.json` under `curves`; what is missing is the analysis and its
integration into the state block.

**Stage 7 — Golden tests.** Frozen input/output pairs so every change is checked
against known-good results automatically. This is what makes the system safe to
keep modifying.

**Before either:** real-world use. v6 changes the daily workflow, and a week of
actual coaching will surface friction that no synthetic test reveals.

---

## 9. Restoring

1. Download the `v6.0-stage5` release from GitHub.
2. Replace the Claude Project instructions with `Prompt/infame_elite_endurance_coach.md`.
3. Upload to the Project: both files from `generated/`, the 6 KBs from
   `Knowledge/`, the syntax reference, `config/athletes/ATHLETE_INTAKE.md`, and
   `config/tss_classes.yaml`.
4. Confirm `ICU_API_KEY` is set, then run `build_zone_tables.py validate` as a
   smoke test — it should report 8/8.

To go further back, `v5.1-stable` restores the pre-refactor system.
