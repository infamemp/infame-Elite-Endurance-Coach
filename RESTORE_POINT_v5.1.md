# RESTORE POINT — Infame Elite Endurance Coach v5.1

**Date frozen:** 2026-08-18
**Git tag:** `v5.1-stable`
**Status:** Known-good baseline. Last state before the deterministic refactor.

---

## 1. Purpose

This document freezes the definition of "working" for Infame v5.1. It exists so that
any future change can be judged against a known baseline: if a modification produces
worse output than what is described here, the change is a regression and must be
reverted to `v5.1-stable`.

Freezing the files is not enough. What must be preserved is the *behavior*, and
behavior can only be judged against a written record of what the system did on this
date.

---

## 2. What is frozen

| Layer | Location | Notes |
|:---|:---|:---|
| System prompt | `Prompt/infame_elite_endurance_coach.md` (v5.1) | Must match the Claude Project instructions verbatim |
| Zone tables | `Training_Zones/` | Source of truth for zones and physiological classes |
| Knowledge base | `Knowledge/` | 6 book-derived KB files |
| Syntax reference | `Syntax/` | Intervals.icu workout builder grammar |
| Data pipeline | `Athlete Template/intervals_export.py` (v1.6) | API key now read from `ICU_API_KEY` env var |
| Context converter | `Excel to MD Converter/convert.py` | Excel → athlete context markdown |

**Runtime environment:** Claude Project. The system prompt lives in the Project
instructions; the zone tables, KB, and syntax reference are uploaded as Project files.
The two Python scripts run locally on Windows.

**Verification requirement:** the repository and the Claude Project must be confirmed
identical before this restore point is considered valid. The Project is the system that
actually runs; the repository is the backup of it.

---

## 3. Restore procedure

1. Download the `v5.1-stable` release from GitHub (or unzip the local archive).
2. Replace the Claude Project instructions with the full contents of
   `Prompt/infame_elite_endurance_coach.md`.
3. Re-upload the Project files from `Training_Zones/`, `Knowledge/`, and `Syntax/`.
4. Restore the local scripts.
5. Confirm `ICU_API_KEY` is set in the environment, then run `intervals_export.py`
   as a smoke test.

---

## 4. Confirmed working behavior (baseline)

As of the freeze date, v5.1 reliably performs the following:

- **Gated state machine.** Phases 0–6 execute in order. Code generation does not occur
  before Phase 4 without explicit athlete approval of Phase 3.
- **Metric Map.** Builds and locks per-discipline metric selection in Phase 1, including
  the athlete preference override, power-meter hierarchy, trail-pace prohibition, and
  the Olbrich Special Output Rule.
- **Multi-methodology prescription.** Correctly reads zones from the KB tables across
  Coggan, Friel, Carmichael, Daniels, Palladino, Koop, and Olbrich.
- **Syntax generation.** Produces valid Intervals.icu blocks: English keywords,
  percentage-based targets, non-nested repeats, blank lines around repeat blocks.
- **Macrocycle continuity.** The `#SESSION` continuation header carries state across
  conversations.
- **Data pipeline.** `intervals_export.py` pulls profile, PMC snapshot, sport settings,
  365-day events, and 4 weeks of activities for all athletes on the coach account.

---

## 5. Known defects tolerated at this baseline

These are accepted as present in v5.1. They define the work queue for the next version.
Any of them appearing in a future version is *not* a regression — it is unfinished work.

### D-1 — Ramps generated where prohibited
**Severity:** High (produces an unexecutable session on the target device)
**Symptom:** `ramp` steps appear in disciplines where STEP 7 forbids them — outdoor
cycling and any form of running, including treadmill.
**Root cause:** ramp eligibility is resolved in Phase 1 (Metric Map, STEP 7) but is not
restated as a constraint at Phase 4 generation time. It is absent from the Absolute
Prescription Rules table, so at the moment of writing a block there is no hard rule in
scope. The Metric Map table carries a `Ramp` column, but nothing requires it to be
consulted before emitting a ramp.

### D-2 — TSS calculation is imprecise
**Severity:** Medium (propagates into block-level load planning and PMC projection)
**Symptom:** Estimated TSS values diverge from what the interval structure implies.
**Root cause:** the multiplier table and the physiological-class master rule are sound,
but the procedure has unspecified cases:
- No rule for which value of a target *range* to cost (`85-95%` → low, mid, or high).
- No rule for costing a `ramp` step.
- No explicit statement that repeat blocks multiply by their count.
- No rule for whether recovery intervals inside repeats are costed.
- No rule for a range that straddles two physiological classes.
- No rule for distance-based steps (`2km`, `500mtr`), which have no duration.
- `Do not display the calculation steps` removes all auditability, so an arithmetic
  error is invisible.

### D-3 — Execution and Nutrition header fields drift into vague/colloquial language
**Severity:** Medium (degrades athlete-facing quality and clarity)
**Symptom:** Fields use imprecise colloquialisms — e.g. "rodaje", "ritmo regalado" —
instead of directives anchored to the prescribed zones and targets of the session.
**Root cause:** both fields are specified only by tone and length ("Max 3 lines,
directive tone"). There is no required structure, no controlled vocabulary, no
requirement to reference the actual metric targets in the code block, and no
prohibition against subjective intensity descriptors. The Nutrition Protocol delegates
almost everything to coach judgement, which yields inconsistent specificity between
sessions.

---

## 6. Regression test material

Reference sessions generated by v5.1 and confirmed correct are stored in
`tests/baseline_sessions/`. After any prompt change, regenerate equivalent sessions and
compare. Degradation relative to these outputs is a regression.

> **Pending:** populate this directory with 2–3 real accepted sessions covering
> different disciplines and methodologies (one trainer/power, one trail/LTHR dual-layer,
> one road or run).

---

## 7. Planned direction after this point

The next version moves deterministic work out of the prompt and into code, while
leaving coaching reasoning in the model:

1. Prompt hardening — fix D-1, D-2, D-3 by tightening rules only. No new tooling.
2. Extend `intervals_export.py` — wellness/HRV, power curves, PMC history.
3. Move state resolution into Python — deliver a resolved, authoritative athlete state
   to the model instead of having it infer one.
4. Output verification — `validate_block.py` as a hard gate before upload.
