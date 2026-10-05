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

- **`config/`** — 13 methodologies as YAML validated against a JSON schema, plus
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
- **`mcp_server/`** — the primary way to work: a local MCP server exposing the engine as 9 tools
  (`get_athlete_state`, `get_athlete_profile`, `list_roster`, `save_continuity`,
  `save_race_result`, `save_availability`, `save_block`, `validate_block`, `push_block`) to Claude
  Desktop, so a conversation can pull state, save a block, validate it, and
  upload it without dragging files. `push_block` stays dry-run unless both
  `dry_run=False` and `confirm=True` are passed explicitly, and refuses a
  BLOCKED block unless `override_validation=True` is also passed. See
  `manual/OPERATIONS_MANUAL.md` §4a.
- **`tests/`** — 409 regression tests (plus 76 in `tests/test_mcp_server.py`) over synthetic athletes with frozen expected
  outputs. Run after any change to config or engine.
- **`Prompt/`** — the gated state machine, Phases 0–6.
- **`Knowledge/`** — 14 book-derived knowledge bases (each methodology's YAML
  declares its file in `knowledge_file`, plus any further book by the same author
  in `supplementary_knowledge_files` — Friel cycling has two: the 2018 Cyclist's
  Training Bible and the 2025 High-Performance Cyclist; Friel running is
  zones-only, and Mujika on tapering belongs to no single methodology). 13 are
  split into `Principles/` (binding zone definitions, ratios, ceilings — loaded in
  the Project) and `Catalogs/` (the author's own named worked examples, for
  calibration only, never loaded by default). Palladino has no worked-plan content
  to split out and stays as a single file. The originals before the split are in
  the git history.

### Daily use

**Primary path — MCP server connected in Claude Desktop.** Open a chat in
the Claude Project and name the athlete. The coach calls the tools by
itself (prompt v7.3+): it loads `#STATE`, the profile and the saved
`#SESSION`, and after each week it saves, validates and — once you
approve the dry-run — uploads to Intervals.icu. See
`manual/QUICK_GUIDE.md`.

**Fallback — only if the server is down** (or in the browser Project):

```
python coach.py prep <id>
# attach out/<athlete_name>/ (state.md, profile.md, continuity.md if present)
python coach.py check <file>
```

Onboarding a new athlete: `python coach.py new <id>`. Measuring what a block
actually did: `python coach.py review <id> --since <date>` — compares
CTL/ATL/TSB, ACWR, durability, and (once enough history has accumulated)
curve progression between two dates, folding in `race_notes.md` if present.

Full step-by-step in `manual/OPERATIONS_MANUAL.md` (day-to-day athlete
workflow). Historical design docs (`ARCHITECTURE_v6.md`, `WORKFLOW_CHECKLIST.md`,
`WORKFLOW_ACTUAL.md`, `AUTOMATION_OPTIONS.md`) are in `archive/`. Current state
and open items in the `RESTORE_POINT_v*.md` at the root; every version in
`CHANGELOG.md`. Where the project could go next:
`IMPROVEMENT_BACKLOG.md`.

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
coach.py         single entry point: prep / new / check
config/          authors, athletes, schema, thresholds, TSS classes, power profile
engine/          fetch, state resolution, profile rendering, longitudinal analysis
verify/          the hard-constraint gate
generated/       zone tables built from config — never hand-edited
mcp_server/      optional local MCP server — see manual/OPERATIONS_MANUAL.md §4a
out/             per-athlete state.md/profile.md/continuity.md — what you drag
                 into the Claude Project; out/roster.md lists every athlete
tests/           fixtures, golden baselines, the regression runner
Prompt/          the coach system prompt, with dated archive
Knowledge/       13 book-derived KBs — 11 split into Principles/ (loaded
                 in the Project) + Catalogs/ (worked examples, not loaded by
                 default); Friel and Palladino stay single-file (no plan content
                 to split)
Syntax/          Intervals.icu workout builder reference
manual/          OPERATIONS_MANUAL.md + QUICK_GUIDE.md
archive/         historical design docs and the v6.5 MCP incident record
```

Not in version control: `data/` and `out/` (athlete data pulled from
Intervals.icu and what's rendered from it), real athlete profiles,
spreadsheets, and generated athlete documents. The Intervals.icu API key
lives in the `ICU_API_KEY` environment variable, never in code.

---

## 🔄 Changelog

Every version, newest first, is in `CHANGELOG.md`.

---

## 🛠️ Updating the Engine

Any change to `config/` or `engine/` follows the same sequence:

```bash
python build_zone_tables.py validate    # schema-check the authors
python build_zone_tables.py build       # regenerate the zone tables
python tests/run_tests.py               # regression tests (all must pass)
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
