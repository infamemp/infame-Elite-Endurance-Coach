# ARCHITECTURE — Infame Elite Endurance Coach v6

**Status:** Design. Not yet implemented.
**Baseline:** `v5.1-stable` (see `archive/RESTORE_POINT_v5.1.md`)
**Date:** 2026-08-18

> **Implementation note (2026-09-06):** this is the original design document,
> kept as written. The built system follows its layer model and contracts
> exactly, but diverged on naming and a few mechanics as it was actually
> built:
> - The single entry point is `coach.py prep` / `new` / `check` — not
>   `prepare` / `verify` / `upload` / `validate-config` / `build-project-files`
>   as sketched in §5 and §6.
> - The fetcher is `engine/fetch_athlete_data.py`, not `intervals_client.py`.
>   The state resolver is `engine/build_state.py`, not `training_state.py` +
>   `pmc_forecast.py`. There is no separate `power_curve.py` or
>   `durability.py` — both live inside `engine/longitudinal.py`.
> - A fourth output, `engine/build_profile.py` → `profile.md`, was added
>   later (v6.3) for raw athlete context; it isn't in the §4 layout below.
> - Delivery to the Claude Project is a folder, `out/<athlete_name>/`, not a
>   single "context pack" file.
> - A results module (v6.4) — `coach.py review`, dated curve snapshots, and
>   a `#RACE_RESULT` block emitted by the prompt — was added after this
>   design was written; the design's four layers held without modification.
>
> For what actually exists today, read `README.md` and the current
> `RESTORE_POINT_v6.*.md` in `archive/` (or the repo root, whichever is
> newest) — not this file's §4 and §5. The goal, the layer model, and the
> contracts in §1–3 still hold exactly as designed.

---

## 1. Goal

Build a single system that combines the strengths of Infame v5.1 (multi-author
schema-governed methodology, gated coaching state machine, multi-athlete, real coaching
reasoning) with the strengths of the Montis approach (deterministic computation,
traceable state, governed LLM output, longitudinal performance intelligence).

Three properties must hold simultaneously:

| Property | Meaning | How it is achieved |
|:---|:---|:---|
| **Deterministic** | Same input produces the same output, always | All arithmetic and classification live in code, not in the prompt |
| **Intelligent** | Real coaching reasoning, not template filling | The model receives resolved state and spends its capacity on prescription |
| **Extensible** | The coach can add authors and rules without a rewrite | All knowledge lives in schema-governed config files read by both layers |

The design tension is between the first two. v5.1 chose intelligence and lost
repeatability; Montis chose determinism and lost coaching depth. v6 does not choose —
it **separates**, then defines contracts between the parts.

---

## 2. Layer model

### Layer 1 — Configuration and Knowledge (`config/`, `knowledge/`)

The single source of truth for everything the system *knows*. Neither the prompt nor
the engine contains coaching knowledge; both read it from here.

Contents:
- **Authors / methodologies** — one file per methodology: zone table, metric metadata
  (default metric, available metrics, native/estimated status, dual-layer requirement,
  special output rules), physiological class mapping per zone, session archetypes.
- **TSS classes** — physiological class definitions and multipliers.
- **Decision thresholds** — TSB bands, ACWR gates, HRV ratio bands, taper windows,
  target TSB ranges per event type, power-curve delta bands per sport.
- **Controlled vocabulary** — permitted and prohibited terms for athlete-facing fields.
- **Book knowledge bases** — the existing extracted book KBs, unchanged in role.

**Rule: zero magic numbers anywhere outside this layer.** Any threshold that appears in
code or in the prompt is a defect.

**Format decision:** YAML is the source of truth. The Markdown files uploaded to the
Claude Project are **generated** from the YAML by the engine. This eliminates the
possibility of repository/Project divergence — the two views cannot disagree because
one is derived from the other.

### Layer 2 — Deterministic Engine (`engine/`)

Python. Everything that is computation or classification.

Responsibilities:
- Fetch from Intervals.icu (profile, PMC series, wellness/HRV, activities, power
  curves, calendar events).
- Resolve athlete state: load/recovery state hierarchy (TSB governs, HRV secondary,
  ACWR validation gates), operational state.
- Project PMC forward (Banister) over planned load.
- Longitudinal performance intelligence: power-curve progression across rolling
  windows, durability, repeatability.
- Compute TSS from an interval structure.

Output: an **authoritative, traceable state block**. Every value carries its source.
The engine never gives an opinion; it gives resolved facts.

### Layer 3 — Reasoning (`prompt/` — the Claude Project)

The coaching intelligence. Receives resolved state and is forbidden from recomputing or
contradicting it.

Responsibilities:
- Methodology selection and application per athlete and phase.
- Session and block design.
- Athlete conversation, intake, confirmation gates, adaptation.
- Explanation of decisions in the athlete's language.

The existing `<coaching_intelligence>` section and the gated state machine are preserved
— they are the system's real advantage and are not to be diluted.

### Layer 4 — Verification (`verify/`)

A deterministic gate between generated output and the athlete. Nothing reaches
Intervals.icu unverified.

Checks:
- Intervals.icu syntax validity.
- Hard constraints (ramp eligibility, metric format, dual-layer completeness,
  no nested repeats, header schema, language rules).
- TSS recomputation against the declared value, using Layer 1 config.

A failed check blocks upload. The gate does not repair silently — it reports and stops.

---

## 3. Contracts between layers

Contracts are what make the system failure-proof. Each is explicit and testable.

| Contract | Direction | Rule |
|:---|:---|:---|
| C1 | L1 → L2 | The engine reads all thresholds and zone data from config. No hardcoded values. |
| C2 | L1 → L3 | Project files are generated from config, never hand-edited. |
| C3 | L2 → L3 | The state block is authoritative. The model must not recalculate or contradict it. |
| C4 | L3 → L4 | Every generated block must pass verification before upload. |
| C5 | L1 → L4 | The validator classifies intensities using the same config the engine uses. |

C3 is the pivotal one. It replaces a long list of procedural instructions ("calculate
this way", "check that first") with a single prohibitive rule, which a language model
follows far more reliably than a multi-step procedure.

---

## 4. Target repository structure

```
infame-elite-endurance-coach/
├─ config/
│  ├─ schema/                    # JSON Schema definitions
│  │  ├─ author.schema.json
│  │  └─ thresholds.schema.json
│  ├─ authors/                   # one file per methodology
│  │  ├─ coggan.yaml
│  │  ├─ friel_cycling.yaml
│  │  ├─ daniels.yaml
│  │  ├─ koop.yaml
│  │  └─ ...
│  ├─ tss_classes.yaml
│  ├─ decision_thresholds.yaml
│  └─ vocabulary.yaml
├─ engine/
│  ├─ intervals_client.py        # API access
│  ├─ training_state.py          # state resolution
│  ├─ pmc_forecast.py            # Banister projection
│  ├─ power_curve.py             # longitudinal progression
│  ├─ durability.py
│  ├─ tss.py                     # shared with verify/
│  └─ build_context.py           # emits the Project context pack
├─ prompt/
│  ├─ infame_coach_v6.md
│  └─ archive/                   # dated snapshots of prior versions
├─ verify/
│  ├─ parser.py                  # Intervals.icu syntax parser
│  └─ validate_block.py          # hard-constraint gate + TSS audit
├─ tests/
│  ├─ golden/                    # frozen input → expected output pairs
│  └─ baseline_sessions/         # v5.1 reference sessions
├─ knowledge/                    # book-derived KBs
├─ generated/                    # Project files built from config — never hand-edited
├─ coach.py                      # single CLI entry point
├─ ARCHITECTURE_v6.md
└─ RESTORE_POINT_v5.1.md
```

---

## 5. Daily workflow

Three commands, one entry point:

```
python coach.py prepare --athlete <name>
```
Fetches data, computes state, writes the context pack (athlete context + authoritative
state block) plus the generated Project files. Upload the result to the Claude Project.

```
python coach.py verify <block-file> --athlete <name>
```
Parses the generated block, checks hard constraints, recomputes TSS. Reports pass/fail.

```
python coach.py upload <block-file> --athlete <name>
```
Runs `verify` first. Uploads only on a clean pass.

---

## 6. Extension procedure — adding an author

The requirement that drove this design. Adding a methodology must not touch the prompt
or the engine.

1. Copy `config/authors/_template.yaml` to `config/authors/<author>.yaml`.
2. Fill the zone table, metric metadata, physiological class mapping, and any special
   output rule.
3. Run `python coach.py validate-config`. The schema check reports missing or malformed
   fields.
4. Run `python coach.py build-project-files`. The generated Markdown is rewritten.
5. Upload the regenerated files to the Claude Project.

No prompt edit. No code edit. The author is now selectable for any athlete.

The same principle applies to new thresholds, new session archetypes, and new
vocabulary rules.

---

## 7. Build order

Each stage delivers standalone value and does not break the previous one. The system
remains usable throughout — v5.1 keeps running until each piece is ready to replace a
part of it.

| Stage | Deliverable | Acceptance criterion |
|:---|:---|:---|
| **0** | Restore point | `v5.1-stable` tagged; Project and repo verified identical |
| **1** | Config layer | Zones, TSS classes, thresholds in YAML with schema; generator reproduces the current Markdown tables exactly |
| **2** | Verification gate | Validator runs against config; catches all three known v5.1 defect classes on test material |
| **3** | Engine — data | Fetcher extended: wellness/HRV, PMC history, power curves |
| **4** | Engine — state | State resolution and PMC projection in code; context pack emitted with the authoritative state block |
| **5** | Prompt v6 | Computation removed from prompt; C3 contract added; controlled vocabulary enforced |
| **6** | Longitudinal intelligence | Power-curve progression, durability, repeatability in the state block |
| **7** | Golden tests | Frozen datasets with expected outputs; every change runs against them |

Rationale for the order: Stage 1 first because every other layer reads from it. Stage 2
before the engine work because it protects the output immediately, independent of what
generates it. Stage 5 only after Stage 4, because the prompt cannot delegate computation
until something else performs it.

---

## 8. Explicit non-goals

- **Not a web service.** The engine runs locally. No hosting, no deployment surface.
- **Not an autonomous coach.** Confirmation gates stay. The coach approves; the system
  proposes.
- **Not a replacement for Intervals.icu.** The platform remains the source of truth for
  executed load; the engine reads from it and never duplicates its role.
- **Not a port of Montis.** Concepts and methods are adopted selectively; no code is
  copied, and its known weaknesses — hardcoded values outside config, silent exception
  handling, self-repairing validation, single-athlete globals, absent tests — are
  explicitly avoided.
