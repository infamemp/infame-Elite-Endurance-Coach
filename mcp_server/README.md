# mcp_server — a local MCP server for Claude Desktop

Rebuild of `mcp_server/server.py`, removed in September 2026 after
production instability (`archive/RESTORE_POINT_v6.5.md`, `IMPROVEMENT_BACKLOG.md`
§5). Read both before changing anything here — they hold the incident
history and the architectural boundaries this rebuild is not allowed to
cross.

Every tool calls the exact same engine functions `coach.py` does.
`#STATE`, `profile.md`, and block validation are computed identically
either way — nothing here recomputes or reinterprets a single number. If
that ever stops being true, this package has drifted from the one property
that makes it safe to exist.

## What's here

| Tool | Reads/writes | What it does |
|:---|:---|:---|
| `get_athlete_state` | reads, fetches | Fetch (if stale) + resolve + return `#STATE` |
| `get_athlete_profile` | reads, fetches | Same pattern, for `profile.md` |
| `list_roster` | reads | `out/roster.md`, no network call |
| `save_continuity` | writes | `out/<athlete>/continuity.md` — requires a `#SESSION ... #END` envelope |
| `save_race_result` | writes | Appends a `#RACE_RESULT` block to `race_notes.md`, never overwrites |
| `save_block` | writes | `out/<athlete>/blocks/<today>_bloque.md` |
| `validate_block` | reads, may write | Runs `verify/validate_block.py` as a subprocess |
| `push_block` | writes (gated) | Builds the Intervals.icu bulk-events payload. **Never sends anything unless both `dry_run=False` and `confirm=True` are passed explicitly in the same call.** |

`push_block` is not wired into the Claude Project prompt, is not called
automatically by anything in this repository, and its default (and only
undemanded) mode does not touch the network at all. That is deliberate and
non-negotiable — see `IMPROVEMENT_BACKLOG.md` §6 ("do not let the engine
start giving advice... an engine that prescribes rather than reports would
undo the architecture") and this task's own scope limits. The Claude
Project prompt, its Knowledge base, and the phase workflow's STOP-AND-WAIT
gates are untouched by this rebuild — the coach still proposes, the human
still approves every phase before advancing, exactly as before.

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

The `mcp` SDK is **not** part of `requirements.txt`'s core install — it's
only needed to run this server, not for `coach.py`/`engine/`/`verify/`/the
main test suite. Install it separately, in a virtualenv:

```
python -m venv .venv-mcp
.venv-mcp/bin/pip install "mcp==1.30.0" pyyaml requests
```

Pinned, not `>=`: see the comment in the root `requirements.txt` for why.
`cancel_patch.py` will tell you (in the server's log, at startup) whether
its workaround was actually needed for whatever version ends up installed.

Point Claude Desktop's `claude_desktop_config.json` (outside this repo,
per machine, never synced by git — same as last time) at the **wrapper**,
not `server.py` directly:

```json
{
  "mcpServers": {
    "infame-coach": {
      "command": "/absolute/path/to/.venv-mcp/bin/python",
      "args": ["-m", "mcp_server.run_server"],
      "cwd": "/absolute/path/to/infame-Elite-Endurance-Coach",
      "env": { "ICU_API_KEY": "your_key_here" }
    }
  }
}
```

`env.ICU_API_KEY` is required here even if it's already set with `setx` on
this machine — Desktop does not reliably inherit environment variables for
the process it launches (the same finding `archive/RESTORE_POINT_v6.5.md`
§4 recorded).

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

Separate from `tests/run_tests.py` on purpose — the 193 tests there must
keep passing with zero new dependencies for anyone who never touches this
server. If `mcp` isn't installed, this file says so and exits 0 rather
than failing the whole suite over an optional package.

Covers, against the repo's own committed `config/athletes/TESTRAMP.yaml`
fixture and a synthetic `athlete_data.json` (same technique
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

Before running any of this against real athlete data: it was designed and
tested exclusively against `TESTRAMP` first, as this task required, and
only after `tests/run_tests.py`'s full 193-test suite was confirmed
unaffected.

## Known limitations, stated rather than hidden

- **The live `push_block` send path is unexercised against a real
  Intervals.icu account** — same as the original tool
  (`archive/RESTORE_POINT_v6.5.md` §5). Verified only against a mocked
  `requests.Session.post`. The payload shape matches
  `IMPROVEMENT_BACKLOG.md` §5's description of the endpoint as closely as
  this repository's own documentation allows; there was no way to confirm
  it against Intervals.icu's actual API response in this environment.
- **`[Discipline]: track_run`'s activity-type mapping is inference, not a
  confirmed fixture** — same honest gap the original restore point flagged
  for `track` generally. Marked as such in `push_block`'s own output
  (`type_inferred: true` on the affected event), not silently presented
  with the same confidence as the confirmed mappings.
- **Reach is Desktop-only**, by MCP protocol design — the browser Project
  can't connect to a local server. A head coach using both should expect
  the browser path to still be the manual, drag-and-drop workflow.
