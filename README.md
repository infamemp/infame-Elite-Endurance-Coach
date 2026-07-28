# 🏃 Infame Elite Endurance Coach

A methodology-agnostic coaching engine that turns athlete data into structured,
platform-ready training prescriptions for cycling and running. It pairs a
reasoning-driven system prompt with a standardized knowledge base and an
Intervals.icu data pipeline.

The engine prescribes individualized training load — optimizing performance on
road and mountain alike — by reasoning per athlete, per block, and per session
rather than filling templates.

---

## 🧩 Engine Components

- **System prompt** (`Prompt/`) — a gated state machine spanning intake →
  strategy → macrocycle → block execution → recalibration → close (Phases 0–6).
  Enforces hard output-format constraints for reliable Intervals.icu import
  while leaving every load, structure, and timing decision to coaching judgment.
- **Standardized training-zone KB** — cycling (Friel, Coggan, Carmichael) and
  running (Daniels, Palladino, Friel, Koop, Olbrich) under one metadata and
  column schema, with formal Schema Extension Rules for adding authors,
  dual-layer (engine/steering) support, and special-output-rule handling.
- **Intervals.icu syntax reference** — the workout-builder grammar the engine
  targets when generating code blocks.
- **Book-derived methodology KBs** — structured extractions from the source
  texts backing each methodology (zones, field tests, taper design, nutrition).
- **Athlete data pipeline** (`Athlete Template/`, `Excel to MD Converter/`) —
  Python tooling that pulls PMC and activity data from the Intervals.icu API and
  converts it into coach-ready Markdown context.

---

## 📑 Prescription Principles

Defaults that keep the engine's output consistent and portable:

- **Percentages only.** Every intensity target is expressed as a percentage tied
  to the athlete's threshold values — never raw watts, pace, or bpm.
- **Load by zone class.** Session TSS is estimated from each interval's
  physiological zone class (per the KB), not from the raw percentage number —
  keeping HR- and pace-based sessions accurate.
- **KB first.** The knowledge base is the first source of truth; verified web
  research complements it and never replaces it.

### 🌲 Trail Running
- **Primary metric:** `% LTHR` by default.
- **Secondary:** `RPE`, to manage terrain variability.
- **Exception:** overridden only when the runner has a running power meter, in
  which case power takes priority. Pace is prohibited on trail terrain.

### 🚴 Cycling / Multisport
- Power and structured heart-rate zones, selected per the athlete's available
  hardware.
- Ramp targets are valid only for indoor / trainer cycling.

---

## 🗂️ Repository Structure

> Adjust these paths to match your actual tree.

- `Prompt/` — the coach system prompt.
- `Athlete Template/` — athlete report templates and generated exports.
- `Excel to MD Converter/` — Excel-to-Markdown conversion for athlete intake docs.
- KB assets — standardized zone tables, the Intervals.icu syntax reference, and
  book-derived methodology files.

---

## 🔄 Changelog

**Coach prompt — v5.1 (current)**
- TSS assigned by the KB zone's physiological class instead of the raw % number,
  fixing load overestimation on pace- and HR-based intervals.
- Special Output Rule generalized (native metric ≠ syntax output), replacing the
  hardcoded Olbrich exception.

**Coach prompt — v5.0**
- Two-class rule hierarchy: inviolable output-format constraints vs. overridable
  coaching defaults.
- Self-sufficient `#SESSION` continuation header carrying macrocycle-immutable
  state.
- New terminal Phase 6 (Macrocycle Close / Race Debrief).
- File-availability checks before code generation.

**Infrastructure**
- Migrated to Git; Markdown assets organized by category for continuous updates.

---

## 🛠️ Updating the Engine

After adding a plan or modifying a methodology locally, run:

```bash
git add .
git commit -m "Update: [short description of the change]"
git push origin main
```
