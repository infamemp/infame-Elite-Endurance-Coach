# 🏃 Infame Elite Endurance Coach

A methodology-agnostic coaching engine that turns athlete data into structured,
platform-ready training prescriptions for cycling and running. It pairs a
reasoning-driven system prompt with a standardized knowledge base and an
Intervals.icu data pipeline.

The engine prescribes individualized training load — optimizing performance on
road and mountain alike — by reasoning per athlete, per block, and per session
rather than filling templates.

---

## 🧩 Architecture

Four layers, each with one responsibility and an explicit contract with the next.
Deterministic computation lives in code; coaching judgement lives in the model.

| Layer | Location | Responsibility |
|:---|:---|:---|
| Configuration | `config/` | All coaching knowledge as schema-governed data |
| Engine | `engine/` | Fetch, resolve state, project PMC, longitudinal analysis |
| Reasoning | Claude Project | Methodology, session design, conversation |
| Verification | `verify/` | Hard-constraint gate before anything reaches an athlete |

**The governing rule:** the `#STATE` block produced by the engine is
authoritative. The model prescribes on top of it and never recalculates it.

### What lives where

- **`config/`** — 8 methodologies as YAML validated against a JSON schema, plus
  physiological classes, decision thresholds, the Coggan power profile, and
  athlete profiles. Zero magic numbers anywhere else.
- **`engine/`** — pulls wellness, PMC series, activities and power/pace curves
  from Intervals.icu; resolves training state deterministically; projects the PMC
  forward; reads curve progression, durability and anaerobic repeatability across
  rolling windows.
- **`verify/`** — parses generated workout blocks and checks every hard
  constraint, recomputing TSS from the same config the engine uses. A block that
  fails is not uploaded.
- **`generated/`** — zone tables built from `config/`, never hand-edited.
- **`tests/`** — 75 regression tests over synthetic athletes with frozen expected
  outputs. Run after any change to config or engine.
- **`Prompt/`** — the gated state machine, Phases 0–6.
- **`Knowledge/`** — 8 book-derived knowledge bases.

### Daily use

```
python engine/fetch_athlete_data.py --athlete <id>
python engine/build_state.py --athlete <id>
# paste state.md into the Claude Project, design the block in conversation
python verify/validate_block.py <file> --fill-tss
```

Full step-by-step in `WORKFLOW_CHECKLIST.md`. Architecture rationale in
`ARCHITECTURE_v6.md`. Current state and open items in `RESTORE_POINT_v6.2.md`.
Where the project could go next: `IMPROVEMENT_BACKLOG.md`.

---

## 📑 Prescription Principles

Defaults that keep the engine's output consistent and portable:

- **Percentages only.** Every intensity target is expressed as a percentage tied
  to the athlete's threshold values — never raw watts, pace, or bpm.
- **Load by zone class.** Session TSS is computed by the verification engine from
  each interval's physiological class, not by the model and not from the raw
  percentage — keeping HR- and pace-based sessions accurate.
- **Anchors declared, not assumed.** Most methodologies express percentages
  against functional threshold. Any that does not declares an `anchor` and gets a
  generated threshold-equivalent column, so zones stay interchangeable between
  authors without altering the author's own numbers.
- **KB first.** The knowledge base is the first source of truth; verified web
  research complements it and never replaces it.

### 🌲 Trail Running
- **Primary metric:** `% LTHR` by default, or run power when available.
- **Pace is discouraged, not prohibited.** Gradient and surface break the
  relationship between pace and effort. If the coach or athlete chooses it
  anyway, the choice is recorded in the athlete profile so it is not
  re-litigated every block.
- With neither power nor heart rate, prescription falls back to RPE.

### 🚴 Cycling / Multisport
- Power and structured heart-rate zones, selected per the athlete's available
  hardware.
- **Ramps** are permitted on indoor trainers with power, permitted on a treadmill
  only by express request in the athlete profile, and prohibited outdoors.

---

## 🗂️ Repository Structure

```
config/          authors, athletes, schema, thresholds, TSS classes, power profile
engine/          fetch, state resolution, longitudinal analysis, power profile
verify/          the hard-constraint gate
generated/       zone tables built from config — never hand-edited
tests/           fixtures, golden baselines, the regression runner
Prompt/          the coach system prompt, with dated archive
Knowledge/       8 book-derived methodology KBs
Syntax/          Intervals.icu workout builder reference
```

Not in version control: `data/` (athlete data pulled from Intervals.icu), real
athlete profiles, spreadsheets, and generated athlete documents. The Intervals.icu
API key lives in the `ICU_API_KEY` environment variable, never in code.

---

## 🔄 Changelog

**v6 — deterministic engine architecture (current)**

Rebuilt around four layers so that computation and judgement stop competing for
the same pass. What changed:

- **Configuration became data.** 8 methodologies as schema-validated YAML; zone
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
- **A regression suite** of 75 tests over synthetic athletes with frozen expected
  outputs.
- **Non-threshold anchors** declared per author, keeping zones interchangeable
  across methodologies without altering any author's published numbers.

**v5.1 and earlier**
- TSS assigned by the KB zone's physiological class instead of the raw % number.
- Special Output Rule generalized, replacing the hardcoded Olbrich exception.
- Two-class rule hierarchy: inviolable output-format constraints vs. overridable
  coaching defaults.
- Self-sufficient `#SESSION` continuation header; terminal Phase 6.

---

## 🛠️ Updating the Engine

Any change to `config/` or `engine/` follows the same sequence:

```bash
python build_zone_tables.py validate    # schema-check the authors
python build_zone_tables.py build       # regenerate the zone tables
python tests/run_tests.py               # 75 regression tests
```

A failing golden test does not automatically mean a bug — it means output
changed. Read the diff. If the change was intended, accept the new baseline with
`python tests/run_tests.py --update` and commit the updated goldens alongside the
change that caused them.

If the zone tables were rebuilt, re-upload both files from `generated/` to the
Claude Project. They carry a build date: if the Project's copies are older than
the last config change, they are stale.

```bash
git add .
git commit -m "Update: [short description of the change]"
git push origin main
```
