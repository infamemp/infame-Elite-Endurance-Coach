# AUTOMATION_OPTIONS — proposals only, nothing implemented

Ground truth for this comparison is `WORKFLOW_ACTUAL.md` (all six sections,
including §5 Undocumented behavior and §6 Stale docs). Four options are
presented side by side. **No recommendation is made** — each is scored
against the same four questions, and the choice is left open.

The manual steps these target, per `WORKFLOW_ACTUAL.md` §2, are: the intake
transcription, dragging `state.md`/`profile.md`/`continuity.md` into the
Claude Project, copying the delivered block into a file, pasting the passed
block into Intervals.icu's Workout Builder, hand-writing `continuity.md`/
`race_notes.md`, and the two-machine git sync dance.

**The one constraint every option is held to:** nothing may change what
`#STATE` or the validator actually compute, or how confidently a head coach
can trust either. `build_state.py` and `verify/validate_block.py` are
covered by 193 golden/unit/block tests today; any automation that calls
them as-is inherits that coverage for free, and any automation that
reimplements or bypasses their logic starts back at zero coverage. That
line is called out explicitly in each option below.

---

## At a glance

| | Removes drag-and-drop into the Project? | New always-on process? | Touches the phase/approval gates? | Biggest new failure mode |
|---|---|---|---|---|
| 1. Leaner self-hosted MCP server | Yes (Desktop only) | Yes — a local server | No — gates stay in the prompt | A transport crash again takes the whole server down mid-conversation |
| 2. Direct API script | Yes (replaces the Project entirely) | Yes — the script itself, plus its own state | Yes — has to reimplement them in code | A gate silently not enforced because the script's phase tracking desynced from the model |
| 3. Local desktop app | Only if built on top of 1 or 2 | Yes — the app | Depends what it wraps | An unattended git-sync button pushing something wrong |
| 4. Baseline: script the file-shuffling only | No | Only a scheduled task, optionally | No | An unattended overnight `prep --all` failing silently |

---

## Option 1 — A leaner self-hosted MCP server

Direct history: `mcp_server/server.py` (v6.5) exposed 8 tools —
`get_athlete_state`, `get_athlete_profile`, `list_roster`,
`save_continuity`, `save_race_result`, `save_block`, `validate_block`,
`push_block` (built, dry-run only, never wired into the prompt) — over a
local stdio transport to Claude Desktop, and ran in production across 17
athletes before being fully removed the same week.

**1. What it would concretely change day to day.** For a head coach on
Claude Desktop: `prep` still runs the same way, but the coach can call
`get_athlete_state`/`get_athlete_profile` itself instead of being handed
files to drag in — removing that step entirely. `save_continuity`,
`save_race_result`, and `save_block` let the coach write
`continuity.md`/`race_notes.md`/the block file directly instead of the
head coach hand-pasting them (closing the exact "no validation layer on
the hand-written files" friction point `WORKFLOW_ACTUAL.md` §4 names).
`validate_block` lets the coach run the gate itself and report the result
inline rather than the head coach running `coach.py check` separately.
Uploading to Intervals.icu stays manual — `push_block` existed once,
dry-run only, and was deliberately never called by the coach even before
removal; nothing here argues for changing that. **Added step:** per-machine
`claude_desktop_config.json` setup (outside git, per the v6.5 restore
point) on both of the head coach's machines, and keeping the local server
process itself in sync across them — a second sync surface on top of the
repo sync `WORKFLOW_ACTUAL.md` §4 already flags as trust-based and
unverified.

**2. Effort/complexity.** Medium to build — the tool surface is already
designed and was working; this is closer to "resurrect and fix the one
thing that killed it" than a from-scratch build. Ongoing maintenance is
real, though: every new tool that calls into `fetch_athlete_data`,
`build_state`, `build_profile`, or `coach.py` must be wrapped the same
disciplined way the v6.5 postmortem describes (see below), and that
discipline has to be re-verified on every change to those modules, since
none of it is enforced by a test today — the MCP layer has no test
coverage of its own in `tests/run_tests.py`.

**3. Failure modes.** The v6.5 restore point and its removal commits
identify the actual root causes precisely, not vaguely:
- `sys.exit()` inside a tool handler (used throughout the reused CLI code,
  e.g. `fetch_athlete_data.py` checking `ICU_API_KEY` at import time) does
  not inherit from `Exception` — a bare `except Exception` let it through
  and took down the whole server process, not just that call. Fixed once
  with a `_guarded()` helper.
- A leaked `print()` anywhere in reused CLI code corrupts the server's own
  stdout, which doubles as the MCP protocol channel — this produced the
  "hangs, then disconnects" symptom actually observed in production.
  Fixed once with `contextlib.redirect_stdout` wrapping, added ad hoc when
  discovered.
- The actual removal cause: an **upstream bug in the `mcp` Python SDK
  itself** (`modelcontextprotocol/python-sdk#2610`) — a `CancelledError`
  escaping after a request responder had already completed, killing the
  stdio receive loop, observed on Windows with `mcp` 1.26.0/1.27.1 (the
  head coach's machines are both Windows, per
  `manual/OPERATIONS_MANUAL.md`). A narrow monkeypatch of
  `RequestResponder.__exit__` was shipped same-day as a workaround; the
  server was fully removed the same day regardless, rather than shipping
  with a patch against a private class in someone else's SDK.
- A logic bug independent of the transport: `[Discipline]: road` is
  genuinely ambiguous between cycling and running, and was initially
  misread as cycling-only from one fixture until a contradicting one
  surfaced twice. Fixed by reading the author's own `sport:` field instead
  of a hardcoded table — a good example of the "config is the source of
  truth" principle holding even under time pressure, but also evidence
  that this surface accumulates its own bugs independent of the transport
  problem that ultimately killed it.
- Reach is Desktop-only by MCP protocol design (the browser Project can
  only add remote HTTP connectors) — a head coach who sometimes uses the
  browser Project or a phone gets no automation there and silently reverts
  to copy-paste, so the two paths can drift out of sync with each other.

**What would need to be different this time**, specific to why it broke
last time rather than generic hardening:
- Switch to a local **HTTP transport on loopback** instead of stdio. The
  root-cause bug is specifically in the stdio receive loop's cancellation
  handling; an HTTP transport sidesteps that bug class entirely rather than
  re-patching around it, at the cost of running a small local web server
  instead of a subprocess Desktop manages for you.
- Pin an `mcp` SDK version confirmed to include the upstream fix (tracked
  as PR #2624 against the same issue) instead of carrying a monkeypatch of
  a private class — a patch like that is a silent breakage risk on every
  future SDK upgrade and was explicitly flagged as "safe to remove once
  upstream is fixed," i.e. always meant to be temporary.
- Make `_guarded()` (catch `Exception` and `SystemExit`) and
  `contextlib.redirect_stdout` wrapping **structural** — a lint rule or a
  shared decorator every tool must use, checked by a test, rather than
  something discovered mid-session and patched ad hoc, which is how both
  bugs were actually found last time.
- Add a supervisor around the server process (even a simple wrapper script
  that restarts it and logs the crash) so a transport-level death is
  visible to the head coach the same day, not a silent, unexplained
  disconnect they have to notice on their own.

**4. Reproducibility/determinism.** Neutral to positive if scoped
correctly: every tool is a thin wrapper calling the exact same
`build_state.build()` / `verify/validate_block.py` code already covered by
the 193-test suite — nothing new is computed, so the existing guarantee
holds by construction as long as no tool reimplements any of that logic
itself. The one real risk: the original design cached a resolved state for
`mcp.state_cache_minutes` (60 minutes) before re-fetching, meaning a coach
could ask for state twice in one conversation and silently get an hour-old
answer without a human ever looking at a file's timestamp before using it
— which is exactly the "7-day staleness rule is prompt-only, not
code-enforced" gap `WORKFLOW_ACTUAL.md` §3 already flags, now happening one
layer further from human eyes. If this is rebuilt, the staleness check
described only in the prompt today should move into the tool response
itself (refuse or loudly flag a stale answer) rather than staying a
convention the model has to remember to apply on every call.

---

## Option 2 — A direct script using `ANTHROPIC_API_KEY`, skipping the Project UI

**1. What it would concretely change day to day.** This is the most
invasive of the four options, because "skip dragging files into the
Project" also means giving up the Project itself — its persistent chat
history, its uploaded Knowledge library, and Anthropic-hosted conversation
state. A new script would need to assemble, per call: the system prompt
(`Prompt/infame_elite_endurance_coach.md`), every Knowledge file currently
uploaded to the Project (the zone tables, one `Knowledge/Principles/
<author>.md` per active methodology, the syntax reference,
`ATHLETE_INTAKE.md`, `config/athletes/_template.yaml`), and
`state.md`/`profile.md`/`continuity.md` — then drive the multi-turn
conversation and, ideally, wire tool-use back into the existing engine
(`validate_block`, `prep`) so the loop can act rather than just talk.
Day-to-day, the head coach would run one command instead of opening a
browser tab and dragging files in, but everything the Project currently
holds for free (history, uploaded files, account-level continuity) becomes
this script's problem to maintain.

**2. Effort/complexity.** High, and open-ended. Every future prompt edit
or Knowledge update (`WORKFLOW_CHECKLIST.md` §E/§F already describes this
workflow for config/prompt changes) now also requires touching the
integration's context-assembly code — doubling the maintenance surface for
every change of that kind, forever. The conversation loop itself has to
reimplement, in code, things that today are just a well-written prompt a
general-purpose model reads fresh each time: the seven-phase state machine
(`WORKFLOW_ACTUAL.md` §1's Phase 0–6 breakdown), the Metric Map decision,
and — the part that matters most for the determinism question — the
STOP-AND-WAIT approval gates.

**3. Failure modes.** Token cost becomes direct and metered per call
instead of hidden inside a flat-rate claude.ai subscription — a loop bug
that resends all ~10 Knowledge files every turn (a real, easy mistake) is
now a billing incident, not just slow. More importantly: a bug in the
script's own tracking of "which phase are we in" can silently desync from
what the model actually said and did, producing output that skips a gate
it wasn't supposed to skip — e.g. emitting Phase 4 session code on a turn
that never actually received explicit Phase 3 blueprint approval, because
the script's state and the model's turn got out of step. That failure mode
has no equivalent today, because today a human is the phase-tracking
mechanism.

**4. Reproducibility/determinism — the sharpest risk of the four
options.** Nothing here would change what `#STATE` or the validator
compute; those stay identical if this script still calls them unmodified.
What it changes is the layer `IMPROVEMENT_BACKLOG.md` §6 explicitly warns
about touching: "the coach's approval gate — almost certainly" the one
thing that should stay conversational, and the general principle stated
right above it — "an engine that prescribes rather than reports would undo
the architecture even if each individual step seemed reasonable." A script
that "continues" a conversation automatically past what is today a literal
human-typed confirmation converts a deliberate design choice into an
automated one without changing a single line of the deterministic engine —
which is precisely why this risk is easy to miss in review: the diff would
show no change to `build_state.py` or `validate_block.py` at all, while
the actual guarantee eroded is "a human looked at this before it became
code." This is buildable safely only if the approval gates are kept as
literal blocking waits for a human action in the new script too — that has
to be a first-class, tested design requirement, not an assumption that the
model will keep behaving the way the prompt says.

---

## Option 3 — A local desktop app (Fit-Forge-style) wrapping the whole flow

**1. What it would concretely change day to day.** A GUI shell over the
existing CLI: an athlete picker backed by `out/roster.md`, a "Prep" button
running `coach.py prep <id>`, `state.md`/`profile.md` rendered inline
instead of opened separately, a "Validate" button running `coach.py check`,
and a "Sync" button doing the two-machine git commit/push/pull dance that
`OPERATIONS_MANUAL.md` §0/§11 currently walks a human through by hand. The
chat itself has to come from somewhere — embedding Option 1's MCP
connection, embedding Option 2's API integration, or simply embedding a
browser view of claude.ai (in which case this option only removes the
"open a separate browser tab and find the right files" friction, not the
drag-and-drop itself). This option is genuinely additive on top of
whichever of the first two it's built on, not a replacement for either.

**2. Effort/complexity.** Medium to high for the shell itself
(Electron/Tauri or a native GUI), but comparatively low-risk *if* it only
ever shells out to the existing scripts — `coach.py` already returns
everything a GUI needs (exit codes, `roster.md`, `state.md`/`profile.md`
as plain files) with no changes required to `engine/`, `verify/`, or
`config/`. The chat pane's cost is whichever of Option 1 or 2 it embeds,
plus a new UI-level maintenance surface (styling, packaging, per-OS
installer) that has nothing to do with the coaching engine at all.

**3. Failure modes.** If built as a thin subprocess wrapper (the safe
design — matching how `coach.py` itself already shells out to
`validate_block.py`), failures are identical to running the CLI by hand
today; nothing new is introduced there. The new risk is concentrated
entirely in the convenience layer: an unattended "Sync" button running
`git add`/`commit`/`push` removes the human review step
`OPERATIONS_MANUAL.md`'s own git-safety guidance implicitly relies on (a
human typing each command and seeing what's staged) — exactly the class of
mistake this system's own operating rules elsewhere treat as needing a
pause, not a button. A GUI's own state (a stale cached roster, a
wrong-athlete selection) is also a new error class the CLI's explicit
`<id>` argument simply doesn't have room for.

**4. Reproducibility/determinism.** Neutral, strictly on the condition that
the app never reimplements any engine or validator logic in its own
runtime — only ever shelling out to the existing Python scripts. The
moment any part of `#STATE` resolution or block validation gets
reimplemented in the GUI's language for a smoother inline experience, this
creates exactly the two-sources-of-truth failure class
`engine/build_profile.py`'s own docstring warns about (the real,
already-experienced desync between the old Excel export and `state.md`
that motivated retiring the Excel pipeline in the first place). The
git-sync convenience feature is the one part of this option with zero
inherited test coverage — nothing in `tests/run_tests.py` checks what a
sync button would actually commit.

---

## Option 4 — Baseline: automate only the file-shuffling, touch nothing else

No new server, no new app, no API integration. Small, independent
additions to what already exists, each already named somewhere in this
repo's own backlog rather than invented for this comparison:
- A scheduled `coach.py prep --all` — already listed as a "future idea" in
  `manual/OPERATIONS_MANUAL.md` ("A scheduled task. Windows can run the
  fetcher every morning so the data is already current").
- A helper that detects the `[Week]` … last `[Nutrition]` boundary
  automatically instead of asking a human to eyeball it, per
  `WORKFLOW_CHECKLIST.md` §C Step 4 / `OPERATIONS_MANUAL.md` §6's manual
  copy instructions.
- The two-machine sync-check script already named as an open backlog item
  in `IMPROVEMENT_BACKLOG.md` §1 ("comparing a hash of the `engine/` files
  on both paths would catch a drift between machines before it ever
  touches a real athlete's data").

**1. What it would concretely change day to day.** `prep` for every
athlete happens automatically each morning instead of being triggered by
hand; copying the delivered block into a file becomes a paste-and-confirm
step instead of a manual eyeball-the-boundary-and-select step; before
starting work on a second machine, a quick check flags whether it's
actually caught up with the first. The Claude Project, the phases, the
approval gates, and the git commit/push themselves are all untouched.

**2. Effort/complexity.** Low, and incremental — each piece is independent,
separately shippable, and small enough to get its own test coverage the
way `validate_block.py` already has, rather than standing up a new
always-on process or a new conversational integration.

**3. Failure modes.** An unattended overnight `prep --all` that hits a
network blip or an expired API key just fails silently until someone
checks — the same failure that exists today (`prep`'s own `FETCH FAILED`
handling is unchanged), just now unsupervised instead of watched
interactively; the fix is as simple as surfacing the failure somewhere the
head coach will actually see it (e.g. `roster.md` already shows last-fetch
date — a stale row after an overnight run is a visible, honest signal, not
a silent one). A boundary-detection helper that gets the split wrong is
strictly less risky than what it replaces, since it can be built to refuse
loudly ("boundary not found — nothing pasted") rather than silently
guessing wrong the way a rushed human copy-paste might.

**4. Reproducibility/determinism.** No effect, by construction — this
option deliberately never touches how `#STATE` is computed, how a block is
validated, or how the phase conversation proceeds. It only removes toil
around file-copying, timing, and machine-syncing. Of the four options,
this is the only one with zero exposure to the determinism/approval-gate
risk the other three carry in some form, precisely because it automates
the least.

---

## Decision is open

All four are presented without a ranking. They are not mutually exclusive
— Option 4's pieces could ship regardless of what (if anything) is chosen
from 1–3, and Option 3 is only meaningful once 1 or 2 is chosen for its
chat layer. No implementation work starts until you pick a direction (or
a combination) from this list.
