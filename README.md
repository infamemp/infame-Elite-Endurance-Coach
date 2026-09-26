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
- **`mcp_server/`** — optional local MCP server exposing the engine as 8 tools
  (`get_athlete_state`, `get_athlete_profile`, `list_roster`, `save_continuity`,
  `save_race_result`, `save_block`, `validate_block`, `push_block`) to Claude
  Desktop, so a conversation can pull state, save a block, validate it, and
  upload it without dragging files. `push_block` stays dry-run unless both
  `dry_run=False` and `confirm=True` are passed explicitly, and refuses a
  BLOCKED block unless `override_validation=True` is also passed. See
  `manual/OPERATIONS_MANUAL.md` §4a.
- **`tests/`** — 390 regression tests over synthetic athletes with frozen expected
  outputs. Run after any change to config or engine.
- **`Prompt/`** — the gated state machine, Phases 0–6.
- **`Knowledge/`** — 13 book-derived knowledge bases (each methodology's YAML
  declares its file in `knowledge_file`; Friel cycling and running share one, and
  Mujika on tapering belongs to no single methodology). 11 are split into `Principles/`
  (binding zone definitions, ratios, ceilings — loaded in the Project) and
  `Catalogs/` (the author's own named worked examples, for calibration only,
  never loaded by default). The other 2 (Friel, Palladino) have no worked-plan
  content to split out and stay as a single file. Originals before the split
  are in `archive/Knowledge_legacy/`.

### Daily use

```
python coach.py prep <id>
# drag out/<athlete_name>/ (state.md, profile.md, continuity.md if present)
# into the Claude Project, design the block in conversation
python coach.py check <file>
```

**With the MCP server (`mcp_server/`) connected in Claude Desktop**, the
drag-and-drop and the separate `check` call are no longer necessary: the
coach calls `get_athlete_state`/`get_athlete_profile` directly, mid-
conversation, and validates and uploads with `validate_block`/
`push_block` — see `manual/OPERATIONS_MANUAL.md` §4a and
`manual/QUICK_GUIDE.md` for the tool-by-tool flow. The commands above
remain the fallback path for the browser Project or a machine where the
server isn't configured.

Onboarding a new athlete: `python coach.py new <id>`. Measuring what a block
actually did: `python coach.py review <id> --since <date>` — compares
CTL/ATL/TSB, ACWR, durability, and (once enough history has accumulated)
curve progression between two dates, folding in `race_notes.md` if present.

Full step-by-step in `manual/OPERATIONS_MANUAL.md` (day-to-day athlete
workflow) and `WORKFLOW_CHECKLIST.md` (system setup, maintenance, adding a
methodology). Architecture rationale in `ARCHITECTURE_v6.md`. Current state
and open items in the newest `RESTORE_POINT_v6.*.md` (root or `archive/`,
whichever is most recent). Where the project could go next:
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
legacy/          retired scripts (pre-coach.py Excel pipeline), kept for reference
archive/         older RESTORE_POINT_*.md and Prompt versions
```

Not in version control: `data/` and `out/` (athlete data pulled from
Intervals.icu and what's rendered from it), real athlete profiles,
spreadsheets, and generated athlete documents. The Intervals.icu API key
lives in the `ICU_API_KEY` environment variable, never in code.

---

## 🔄 Changelog

**v6.7 — MCP server rebuilt**

`mcp_server/` is back, with the root cause of the v6.6 removal fixed
structurally rather than patched around. The removal postmortem
(`archive/RESTORE_POINT_v6.5.md`) named a monkeypatch of a private SDK
class as the actual cause of the earlier instability; this rebuild
replaces that guesswork with a confirmed diagnosis and a version-pinned
fix:

- **Root cause, confirmed against upstream, not re-guessed.** The v6.5
  instability traced to `modelcontextprotocol/python-sdk#2610` — cancelling
  an in-flight request over stdio makes `RequestResponder.__exit__` let a
  `CancelledError` escape after the responder had already completed;
  because that task is a sibling of the stdio receive loop's own task
  group, one cancelled tool call took the whole server down. Confirmed
  still present in `mcp` 1.30.0 by reading its source directly, and
  confirmed a correct no-op against `mcp` 2.x, where `RequestResponder` no
  longer exists.
- **The fix:** a pinned SDK version plus `mcp_server/cancel_patch.py`, a
  self-detecting workaround — it constructs a real `RequestResponder` and
  empirically probes whether the installed SDK still exhibits the bug
  before patching anything, so it becomes a deliberate no-op the day the
  upstream fix (`python-sdk#2624`) ships in whatever version is installed,
  with nothing else to remember to change.
- **The 8 tools are back**, unchanged in shape from v6.5:
  `get_athlete_state`, `get_athlete_profile`, `list_roster` (reads),
  `save_continuity`, `save_race_result`, `save_block` (writes),
  `validate_block` (wraps the existing verifier as a subprocess), and
  `push_block` (uploads to Intervals.icu, dry-run by default).
- **Three real bugs found and fixed during manual end-to-end testing on
  Windows** — none caught by the test suite beforehand, since it runs on
  Linux:
  - `validate_block` crashed with an uncaught `UnicodeEncodeError` on
    Windows: `subprocess.run`'s `encoding="utf-8"` only controls how the
    *parent* decodes output, not what encoding the *child* uses to
    encode it, and a Windows child piped (not console) stdout defaults to
    cp1252, which can't encode the box-drawing characters
    `validate_block.py` prints on every run. The crash surfaced as
    `passed: False`, indistinguishable from a real hard-constraint
    failure. Fixed by forcing `PYTHONIOENCODING=utf-8`/`PYTHONUTF8=1` in
    the child's environment.
  - `validate_block` and `push_block` both resolved a relative
    `file_path` against the current process's working directory instead
    of the server's own `ROOT` — worked when called from a fresh
    interpreter launched at `ROOT`, failed with a spurious "File not
    found" through the live server process launched by Claude Desktop,
    whose actual working directory didn't match `ROOT` despite
    `claude_desktop_config.json`'s `cwd` field. Fixed by resolving a
    relative path against `ROOT` explicitly in both tools.
  - `validate_block` hung for several minutes over Desktop's live stdio
    connection while returning in 0.2s called directly: its
    `subprocess.run()` never redirected the child's stdin, so the child
    inherited the server's own stdin — the live JSON-RPC pipe Desktop
    uses under stdio transport, which a standalone CLI call never has.
    Fixed with an explicit `stdin=DEVNULL`.
- **One design gap closed, not a bug in the strict sense:** `push_block`
  never checked `validate_block`'s own result before sending. The
  original two-command CLI made "BLOCKED" and "upload" a full
  conversation turn apart, so a human seeing BLOCKED simply wouldn't run
  the next command; inside one MCP conversation they're a single tool
  call apart, and that protective friction doesn't exist by default.
  Confirmed directly during testing: a block with real HC-METRIC failures
  was assembled and would have been sent to Intervals.icu with both
  `dry_run=False` and `confirm=True`, rejected only because the test used
  invalid credentials, not because the tool stopped it. `push_block` now
  runs the same validation check internally before its live send and
  refuses a BLOCKED block unless `override_validation=True` is also
  passed explicitly.

**v6.6 — MCP server removed**

`mcp_server/server.py` caused enough production instability that it was
removed entirely — code, prompt references, and the `mcp:` config block in
`decision_thresholds.yaml`. The daily workflow is back to dragging
`out/<athlete_name>/` into the Claude Project, as described in Daily Use
above. There is currently no automated upload path to Intervals.icu; a
verified block is pasted into its Workout Builder by hand. The full
incident history — what the server did, the two real bugs it surfaced, and
why it was reverted — is kept in `archive/RESTORE_POINT_v6.5.md` rather
than deleted, specifically so a future attempt does not start from zero.

**v6.5 — MCP server (built, then removed — see v6.6 above)**

The daily workflow required dragging files into the Claude Project for
every new chat. What changed:

- **`mcp_server/server.py`** exposed the engine itself as 8 tools a local
  Claude Desktop connection could call mid-conversation — never a wrapper
  around the raw Intervals.icu API, so `#STATE`'s determinism guarantee
  carried over unchanged: `get_athlete_state`, `get_athlete_profile`,
  `list_roster` (reads), `save_continuity`, `save_race_result`,
  `save_block` (writes), `validate_block` (wrapped the existing verifier as
  a subprocess), and `push_block` (uploaded to Intervals.icu via
  `POST /events/bulk?upsert=true`, defaulting to a dry run).
- **The prompt called these tools itself** — `save_block`, `save_continuity`,
  `save_race_result`, and `validate_block` — when available, falling back
  to the manual copy-paste flow otherwise (e.g. the browser Project,
  where the server could never connect). `push_block` was deliberately
  never called automatically.
- **A real classification bug found and fixed in the process:**
  `[Discipline]: road` is ambiguous — confirmed real for both cycling
  (Coggan) and running (Daniels) methodologies in the repo's own test
  fixtures. The fix read the author's own `sport:` field from
  `config/authors/<methodology>.yaml` instead of a flat lookup table,
  which would have silently classified a marathon as a bike ride. This
  fix lived only inside the now-removed code — see `IMPROVEMENT_BACKLOG.md`
  §5 for why the underlying lesson still matters.

**v6.4 — results module**

The system could generate and verify plans but never measured whether they
worked. What changed:

- **`coach.py review`** compares an athlete's signals between any past date
  and today: CTL/ATL/TSB and ACWR (both fully reconstructable from the
  180-day pull already fetched — no new data needed), durability, and curve
  progression (needs a dated snapshot — see next point).
- **Curve snapshots** are captured on every `coach.py prep`, since
  Intervals.icu's curves endpoint only ever returns the best value as of
  today, never a historical one. Progression tracking is only as old as the
  first snapshot captured after this shipped.
- **`#RACE_RESULT`** — Phase 6 of the prompt now emits a small saveable block
  after a race debrief, appended to `out/<athlete>/race_notes.md`, which
  `review` reads automatically for any race inside the requested window.
- **A dormant regression-suite bug was found and fixed:** the golden tests'
  synthetic fixtures are dated relative to whenever `make_fixtures.py` was
  last run, not to the calendar — so a fixture generated once and left on
  disk silently drifts out of its own rolling windows as real time passes,
  failing for reasons unrelated to any code change. `run_tests.py` now
  regenerates every fixture immediately before comparing, closing the gap
  for good.

**v6.3 — unified daily workflow**

- **`coach.py`** gained `prep` (fetch + resolve + render in one call,
  delivered to a named `out/<athlete>/` folder instead of `data/<id>/`),
  `new` (athlete onboarding), and a live `continuity.md` staleness check.
  `out/roster.md` gives a name-to-id index across the whole account.
- **`build_profile.py`** replaced the Excel-based `intervals_export.py` +
  `convert.py` pipeline for the athlete-facing context document, recovering
  data the old pipeline silently dropped (Avg Power on every activity).
- **`#SESSION` can be requested on demand mid-block**, not only at
  block-end, so an off-calendar consult in a fresh chat has a continuity
  artifact to resume from.

**v6 — deterministic engine architecture**

Rebuilt around four layers so that computation and judgement stop competing for
the same pass. What changed:

- **Configuration became data.** 13 methodologies as schema-validated YAML; zone
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
- **A regression suite** of 392 tests over synthetic athletes with frozen expected
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
python tests/run_tests.py               # 392 regression tests
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
