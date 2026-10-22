# mcp_server — a local MCP server for Claude Desktop

Rebuild of `mcp_server/server.py`, removed in September 2026 after
production instability (`archive/RESTORE_POINT_v6.5.md`). Read it before
changing anything here — it holds the incident history; the boundaries this
server must not cross are in `ROADMAP.md` ("Lines not to cross").

Every tool calls the exact same engine functions `coach.py` does.
`#STATE`, `profile.md`, and block validation are computed identically
either way — nothing here recomputes or reinterprets a single number. If
that ever stops being true, this package has drifted from the one property
that makes it safe to exist.

## What's here

21 tools, registered in `server.py`. The prompt's `<tools>` table says when the
coach uses each one.

| Tool | Reads/writes | What it does |
|:---|:---|:---|
| `get_athlete_state` | reads, fetches | Fetch (if stale) + resolve + return `#STATE`, with continuity, race notes, availability, `review_due` and the last 30 days of the ledger |
| `get_athlete_profile` | reads, fetches | Same pattern, for `profile.md` |
| `get_reference` | reads | A methodology's zone table, the architecture library (filtered by class and discipline), the intake script, the profile template |
| `get_knowledge` | reads | The book knowledge bases: principles by entry ID, section or query; the author's catalog with `catalog=true` |
| `list_roster` | reads | `out/roster.md`, no network call |
| `roster_overview` | reads | All athletes in one table from each `state.json` (+ `out/roster.md` for never-prepared ones); no network call |
| `get_execution` | reads, fetches | Planned vs done via Intervals.icu's `paired_event_id`; refreshes once if the cache predates pairing |
| `load_targets` | computes | Weekly TSS and hours targets from the coach's own cycle (e.g. 3:1), start TSS, growth and recovery; pure arithmetic, no athlete data, no network |
| `what_if_targets` | reads | CTL and TSB on race morning with vs without the weekly TSS targets, using the state's own projection; uses the cached data, refetches only when stale |
| `save_block` | writes | `out/<athlete>/blocks/<today>_bloque_w<N>.md` (one file per week) |
| `replace_session` | writes | The corrected cards inside a saved week file; the other sessions stay as saved |
| `validate_block` | reads, may write | Runs `verify/validate_block.py` as a subprocess; with `fill_tss` writes Duration and TSS into the headers |
| `push_block` | writes (gated) | Uploads a validated week as Intervals.icu events (indoor box, tags from the card, notes). **Never sends unless both `dry_run=False` and `confirm=True` are passed in the same call, and refuses a BLOCKED week unless `override_validation=True`.** After a live send it compares each session's load with Intervals.icu's (`load_check`) and confirms the indoor box (`indoor_check`) |
| `remove_block` | writes (gated) | Deletes only `infame-<athlete>-…` WORKOUT events from tomorrow on; everything else is left alone and counted |
| `post_activity_comment` | writes (gated) | Comment on an athlete's activity; refuses an activity that is not theirs. Dry run by default |
| `update_threshold` | writes (gated) | Sets ftp / lthr / max_hr / threshold_pace in Intervals.icu, shows old → new, re-reads to verify, marks the local cache stale |
| `save_declared_profile` | writes (gated) | `config/athletes/<id>.yaml` after an intake or an approved change; dry run shows the diff, the previous version is kept in `data/<id>/profile_history/` |
| `save_training_age` | writes | Years of consistent endurance training as the head coach stated it (0 for a beginner); sets the CTL ramp band in `#STATE`. A value in the declared profile wins |
| `save_continuity` | writes | `out/<athlete>/continuity.md` — requires a `#SESSION ... #END` envelope |
| `save_race_result` | writes | Appends a `#RACE_RESULT` block to `race_notes.md`, never overwrites |
| `save_availability` | writes | `out/<athlete>/availability.md` — the head coach's stated daily maximums, returned by `get_athlete_state` |

Since prompt v7.3 (2026-09-26) the coach calls every tool itself,
`push_block` included — but only through the prompt's upload gate: a
dry-run first, then an explicit approval from the head coach, then the
live call with `dry_run=False, confirm=True`. Nothing in this repository
calls it automatically, and its default mode does not touch the network
at all. That is deliberate and
non-negotiable — see `ROADMAP.md`, "Lines not to cross" ("the engine
reports; the coach decides"). The coach still proposes and the head coach
still approves every phase before advancing.

**Validating and uploading are no longer independent, on purpose.** The
original two-command CLI workflow could describe them as fully separate
manual steps — with `validate_block` and `push_block` a whole conversation
turn apart, a human seeing "BLOCKED" simply wouldn't go on to run the next
command. Inside one MCP conversation they're one tool call apart, and that
protective friction doesn't exist by default anymore: nothing stopped
`push_block` from being called on a block just reported BLOCKED, in the
same turn — confirmed directly, once, before this fix (a real BLOCKED
block was assembled and would have been sent to Intervals.icu; it was only
rejected because the test used invalid credentials). `push_block` now runs
the same check internally before its live send and refuses to send a
BLOCKED block unless `override_validation=True` is passed explicitly — a
deterministic-fact check, the same category as `validate_block`'s own
HC-METRIC-style rules, not the engine giving advice, so it does not cross
that line.

## Why it broke last time, and what's different now

Three separate bugs took the previous server down or made it misbehave.
All three are addressed structurally this time, not patched ad hoc after
being found in production:

1. **The actual crash: [python-sdk#2610](https://github.com/modelcontextprotocol/python-sdk/issues/2610).**
   Cancelling an in-flight request over stdio makes
   `RequestResponder.__exit__` re-raise a `CancelledError` even after the
   responder already sent its response, killing the task group that runs
   the whole stdio receive loop — one cancelled tool call ended the entire
   conversation. Confirmed still present in `mcp` 1.30.0 (the latest 1.x
   release) by directly inspecting its source. The upstream fix
   ([python-sdk#2624](https://github.com/modelcontextprotocol/python-sdk/pull/2624))
   is not yet released. `cancel_patch.py` installs that exact fix as a
   monkeypatch — but only after `is_needed()` has **empirically confirmed**
   the installed SDK still has the bug, by constructing a real
   `RequestResponder` and exercising it the same way upstream's own
   regression test does. On an SDK that already has the fix, or a future
   major version that restructures this away (confirmed against `mcp`
   2.2.0, where `RequestResponder` doesn't exist anymore), `is_needed()`
   returns `False` and the patch is a deliberate no-op. `tests/test_mcp_server.py`
   runs this exact check against whatever SDK is actually installed —
   nothing here is trusted on a version number alone.

   **Why stdio, not a different transport.** An earlier draft of this
   project's automation options considered moving to a local HTTP
   transport specifically to sidestep this bug class. Once the precise
   upstream fix was found and verified reproducible/fixable with a small,
   auditable patch, that tradeoff no longer made sense — stdio is the
   standard, well-documented mechanism Claude Desktop uses for a fully
   local subprocess server, and switching require assumptions about
   Desktop's local-HTTP-connector support that couldn't be verified in
   this environment. Fix the actual bug; don't route around it into
   unverified territory.

2. **`sys.exit()` killing the server, not just one tool call.** Reused CLI
   code (`fetch_athlete_data.py` checking `ICU_API_KEY` at import time, and
   others) calls `sys.exit()` on user-facing errors — correct for a CLI,
   fatal for a long-running server, since `SystemExit` doesn't inherit from
   `Exception` and slips past a bare `except Exception`. Every tool this
   time goes through `guard.py`'s `@guarded` decorator, which catches
   `SystemExit` explicitly (and `Exception`, and this package's own
   `ToolError`) and returns a structured error instead of ever letting
   either escape.

3. **A leaked `print()` corrupting the stdio protocol channel.** `fetch_one()`
   and `build_profile.build()` print unconditionally, `quiet=True` or not —
   and stdout doubles as the wire protocol on this transport, so a stray
   print produced exactly the "hangs, then disconnects" symptom actually
   observed in production. `@guarded` redirects every tool call's stdout
   into the server's own log instead, and serializes calls through one
   process-wide lock — `contextlib.redirect_stdout` swaps `sys.stdout` for
   the whole process, so two calls redirecting concurrently in different
   threads could otherwise race and leak. This system is single-coach,
   single-conversation by design; there's no real concurrency being given
   up, only a class of bug being removed.

A fourth, unrelated bug from last time — `[Discipline]: road` being
genuinely ambiguous between cycling and running rather than a typo — is
also carried forward in `tools_push.py`: the Intervals.icu activity `type`
is resolved from the methodology's own `sport:` field
(`config/authors/<id>.yaml`), never a flat discipline-to-type table.

## Setup

Step by step, for Windows and the Claude Desktop config (including the
`PYTHONPATH` the PC needs): `manual/GUIDE.md` §1. Two points that matter here:

- `mcp` is pinned (`mcp==1.30.0`), not `>=`: see the comment in the root
  `requirements.txt`. `cancel_patch.py` says in the server's log at startup
  whether its workaround was needed for the installed version.
- Point Desktop at the **wrapper** (`-m mcp_server.run_server`), not
  `server.py`, and put `ICU_API_KEY` in the config's `env` even if it is set
  with `setx`: Desktop does not reliably inherit environment variables
  (`archive/RESTORE_POINT_v6.5.md` §4).

`run_server.py` is a thin wrapper around `server.py`, not a process
supervisor that restarts a crashed server transparently — that isn't
actually achievable at this layer (an MCP stdio session's identity is the
subprocess itself; a respawned process would need to redo the `initialize`
handshake Desktop's client already completed, so nothing can make a crash
invisible mid-conversation). What it does instead: guarantee that a crash
always leaves a specific, timestamped record at `mcp_server/logs/last_crash.txt`
(gitignored — it can contain athlete data in a traceback) instead of an
unexplained disconnect. Desktop relaunching the configured command the
next time a tool is needed is what actually recovers; this wrapper just
makes sure that when it happens, there's a reason on disk.

## Testing

```
python tests/test_mcp_server.py
```

Separate from `tests/run_tests.py` on purpose — the tests there must
keep passing with zero new dependencies for anyone who never touches this
server. If `mcp` isn't installed, this file says so and exits 0 rather
than failing the whole suite over an optional package.

Covers, against the repo's own committed `tests/profiles/TESTRAMP.yaml`
fixture (copied into `config/athletes/` for the run and taken out after) and a synthetic `athlete_data.json` (same technique
`tests/make_fixtures.py` uses for the engine's own golden tests, so no real
account or network access is needed):

- `cancel_patch`'s empirical bug probe, against whatever `mcp` version is
  actually installed.
- `guard`'s three failure modes: `SystemExit`, a plain exception, and a
  leaked `print()`.
- The fetch-cache freshness check.
- Every read tool, every write tool (including a full round-trip through
  `coach.py`'s own, unmodified `read_race_notes()` — proof this server's
  output is readable by code that has never heard of it).
- `validate_block` against the repo's own known-good and known-bad block
  fixtures (`tests/blocks/`).
- `push_block`'s dry-run default, both single-gate-open cases, and — only
  with `requests.Session.post` mocked, never a real network call — the
  fully-gated send path.
- `push_block` refusing to send a known-BLOCKED block even with both gates
  open, and proceeding (still against the mock only) once
  `override_validation=True` is passed explicitly.

- `[Architecture]` and `[Zone]` reaching the upload as tags, and tags the
  head coach added in Intervals.icu surviving a re-push.

## Known limitations, stated rather than hidden

- **The test suite never touches the network.** The live `push_block` path is
  tested against a mocked `requests.Session`; it has run against the real
  Intervals.icu account since 21 September 2026 (the first real push found
  the DD-MM-YYYY date bug fixed in `_iso_date`), and every live send reads the
  events back to check load and the indoor box.
- **`[Discipline]: track_run`'s activity-type mapping is inference, not a
  confirmed fixture** — same honest gap the original restore point flagged
  for `track` generally. Marked as such in `push_block`'s own output
  (`type_inferred: true` on the affected event), not silently presented
  with the same confidence as the confirmed mappings.
- **Reach is Desktop-only**, by MCP protocol design — the browser Project
  can't connect to a local server. A head coach using both should expect
  the browser path to still be the manual, drag-and-drop workflow.
