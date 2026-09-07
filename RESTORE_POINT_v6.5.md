# RESTORE POINT — Infame Elite Endurance Coach v6.5

**Date frozen:** 2026-09-06
**Git tag:** `v6.5-mcp` (tag this commit once pushed)
**Previous restore points:** `v6.4-results`, `v6.3-workflow`, `v6.2-complete`,
`v6.1-stage6`, `v6.0-stage5`, `v5.1-stable`
**Status:** The daily workflow no longer requires dragging files into the
Claude Project, on machines running Claude Desktop. In production use
across 17 athletes.

---

## 1. Purpose

Two jobs, as always: freezes the definition of "working" for v6.5, and is
the handoff brief for a new conversation to resume from without
re-deriving anything.

v6.5 does not change the four-layer architecture, and it does not change
what the coach decides or how — it changes how `state.md`, `profile.md`,
`continuity.md`, `race_notes.md`, and a generated block get read and
written. Everything that was true about the phases, the gates, and the
STOP-AND-WAIT discipline in `RESTORE_POINT_v6.4.md` still holds exactly.

---

## 2. What's new

### `mcp_server/server.py` — 8 tools, local only

A local MCP server, stdio transport, that Claude Desktop launches as a
subprocess and connects to via `claude_desktop_config.json` (which lives
outside the repo, per machine, and is never synced by git). It is
deliberately **not** a wrapper around the raw Intervals.icu API — every
tool returns something the engine already resolved deterministically, the
same guarantee `state.md` has always carried. It only connects to Claude
Desktop; the browser Project can never reach it, by design of the MCP
protocol itself (custom connectors in the browser must be remote HTTP
servers, confirmed against Anthropic's own documentation before any code
was written).

| Tool | Does |
|:---|:---|
| `get_athlete_state` | Fetch + resolve + return `state.md`'s content. Reuses data fetched within the last hour (`mcp.state_cache_minutes` in `decision_thresholds.yaml`, default 60) instead of re-querying Intervals.icu on every question; `force_refresh=true` bypasses it |
| `get_athlete_profile` | Same pattern, for `profile.md`. Shares the same cache — asking for both back to back doesn't double-fetch |
| `list_roster` | Reads `out/roster.md` — no network call of its own |
| `save_continuity` | Writes `out/<athlete>/continuity.md`, always overwriting |
| `save_race_result` | Appends a `#RACE_RESULT` block to `out/<athlete>/race_notes.md`, normalizing the header if the caller omitted it |
| `save_block` | Writes `out/<athlete>/blocks/<today>_bloque.md`, overwriting same-day |
| `validate_block` | Runs `verify/validate_block.py` as a subprocess against the file `save_block` just wrote — chosen specifically because a subprocess's stdout can never corrupt this server's own stdio protocol stream, unlike the in-process calls below |
| `push_block` | `POST /athlete/{id}/events/bulk?upsert=true`. Defaults to `dry_run=true`; nothing reaches Intervals.icu until asked twice, explicitly. Built and tested; **not wired into the prompt** — Michel's explicit choice, to keep doing this step by hand so he can catch corrections before anything uploads |

### The prompt calls these itself, when available

`save_block`, `save_continuity`, `save_race_result`, and `validate_block`
are called directly by the coach — Phase 4 delivery, Phase 5/6 `#SESSION`
emission (including the on-demand mid-block case), and the Phase 6
`#RACE_RESULT` block all check for the tool first, falling back to the
original copy-paste instructions when it isn't present (the browser
Project, or Desktop without the connector configured). `push_block` is
excluded from this on purpose — see above.

### Two bugs found and fixed while building this, worth remembering the shape of

**A `SystemExit` inside a tool call killed the entire server, not just
that call.** `sys.exit()` (used throughout the reused CLI code —
`fetch_athlete_data.py` checks `ICU_API_KEY` this way at import time) does
not inherit from `Exception`. A bare `except Exception` let it through,
and inside an MCP tool handler that took the whole subprocess down —
confirmed against Claude Desktop's own logs, which showed the exact
`SystemExit('Missing environment variable ICU_API_KEY...')` traceback
tearing down the asyncio event loop. Every fetch/resolve/render call is
now wrapped through a shared `_guarded()` helper that catches
`(Exception, SystemExit)` explicitly and returns a plain error string
instead.

**A classification bug: `[Discipline]: road` is genuinely ambiguous, not a
typo.** First evidence (`bad_road.md`, `coggan` + `road`) looked like
confirmation that `road` meant cycling only. A contradicting fixture
(`vianey_bloque1.md`, `daniels` + `road`) was initially dismissed as an
error in that file rather than treated as evidence — caught and corrected
only because it was independently re-checked and a *second* fixture
(`vianey_raw_unfixed.md`) turned up with the same `daniels` + `road`
pairing. `road` is shared between cycling and running, disambiguated by
the athlete's active methodology. `push_block` now resolves the
Intervals.icu activity `type` by reading the author's own `sport:` field
from `config/authors/<methodology>.yaml` (confirmed `cycling`/`running`
against `coggan.yaml`, `daniels.yaml`, `palladino.yaml`, `koop.yaml`)
rather than a flat `[Discipline]` → type table. Without this fix, a
Daniels marathon block would have been pushed to Intervals.icu classified
as a bike ride. `track` is treated the same defensive way (methodology
decides `TrackRide` vs `Run`) but has no confirming fixture either way —
flagged in the code as inference, not evidence, unlike `road`.

### `SystemExit`-safe design pattern, established here for future tools

Any new MCP tool that calls into the reused CLI modules
(`fetch_athlete_data`, `build_state`, `build_profile`, `coach`) must route
through `_guarded()` or an equivalent — never a bare `except Exception`.
The CLI code was written to `sys.exit()` on user-facing errors, correctly,
for its original context; an MCP tool handler is a different context
where that same call is fatal to the whole process if not caught
explicitly.

---

## 3. Also resolved this session

| Item | Resolution |
|:---|:---|
| `fetch_one()` and `build_profile.build()` print unconditionally, even with `quiet=True` | Every call that might print now runs inside `contextlib.redirect_stdout` — critical here because this process's real stdout is the MCP protocol channel to Desktop; a leaked `print()` corrupts it and causes exactly the "hangs, then disconnects" symptom seen and fixed mid-session |
| `pmc_at()` (used by `coach.py review`, unrelated to this session's main work) returned unrounded CTL/ATL floats | Rounded to 1 decimal, matching `latest_pmc()`'s existing convention — found while testing `get_athlete_state` against real data |
| `render_review`'s race-notes path message used the unsanitized athlete name | Fixed to use the same `safe_filename()`-sanitized folder name the file is actually written under |
| `WORKFLOW_CHECKLIST.md` §A3 still said `67/67 passed` | Corrected to `76/76`, matching the real confirmed count from `v6.4` |
| Two Python installs on the same Windows machine (`python` → 3.14, `pip` → 3.12) caused three separate silent-mismatch failures during setup | No code fix possible for this — documented explicitly in both manuals: always verify `python -c "import sys; print(sys.executable)"` matches `python -m pip show <package>`'s `Location:`, and always use `python -m pip`, never bare `pip`, on a machine with more than one Python |

---

## 4. Repository layout — changes since v6.4

```
mcp_server/                 NEW
└─ server.py                the 8 tools above

config/
└─ decision_thresholds.yaml + mcp: state_cache_minutes: 60 (new section)

out/<athlete_name>/
└─ blocks/<date>_bloque.md  NEW — written by save_block, read by
                            validate_block and push_block
```

`claude_desktop_config.json` (outside the repo, per machine, in
`%APPDATA%\Claude\`) now carries an `infame-coach` entry under
`mcpServers`, with an `env.ICU_API_KEY` block — added because Desktop
does not reliably inherit environment variables set via `setx` for the
process it launches the server as.

Everything else matches `RESTORE_POINT_v6.4.md` §5 exactly.

---

## 5. Known open items

Carried over from v6.4, still open: 16 of 17 athletes have no real profile
in `config/athletes/`; Bosquet and Ingham KBs not yet extracted; Friel
running shares the cycling KB; target TSB ranges are coach heuristic;
Coggan power profile under-ranks heavier/multisport athletes; cycling
workout engine integration not started; `eW'`/`ePmax` rule confirmed
against only one athlete; `build_profile.py` has no dedicated test
fixture; the `out/` PII exposure is closed going forward but not scrubbed
from git history; the `continuity.md` staleness threshold (10 days) is
hardcoded in `coach.py` rather than living in `decision_thresholds.yaml`;
`data/<id>/history/` has no retention limit.

New in v6.5:

- **`push_block` is built and tested, but not yet used for a real upload.**
  Every scenario was verified with a mocked `requests.Session.post` — the
  URL, payload shape, and auth header construction match the documented
  API exactly, but the first real call to Intervals.icu from this tool
  has not happened yet. Michel's current workflow keeps the upload step
  manual regardless, so this isn't blocking anything — just worth knowing
  the live path is unexercised.
- **`[Discipline]: track` paired with a running methodology has no
  confirming fixture.** Resolves to `Run` by the same logic as `road`,
  but unlike `road` (confirmed twice), this is inference. Revisit if a
  real track-running block ever surfaces.
- **Whether the coach should ever start a session from just an athlete id**
  (calling `get_athlete_state`/`get_athlete_profile` itself, with nothing
  dragged in) was raised and explicitly deferred, not decided against —
  Michel wants to keep dragging files as the primary entry point for now.
  If revisited, it needs to work in both the browser Project and Desktop,
  which the current design doesn't address.

---

## 6. Restoring

1. Download the `v6.5-mcp` release from GitHub (tag it if not done yet).
2. Replace the Claude Project instructions with
   `Prompt/infame_elite_endurance_coach.md`.
3. Upload to the Project: both files from `generated/`, the 8 KBs from
   `Knowledge/`, the syntax reference, `config/athletes/ATHLETE_INTAKE.md`,
   and `config/tss_classes.yaml`.
4. Confirm `ICU_API_KEY` is set, then run as a smoke test:
   - `python build_zone_tables.py validate` — expect 8/8
   - `python tests/run_tests.py` — expect 76/76
   - `python coach.py prep --list` — expect all 17 athletes
5. **If this machine also runs the MCP server:** `python -m pip install
   "mcp[cli]" pyyaml requests`, then configure `claude_desktop_config.json`
   with this machine's own Python path and an `ICU_API_KEY` env block —
   see `manual/OPERATIONS_MANUAL.md` §0 and §10 for the full walkthrough.
   `claude_desktop_config.json` is per-machine and not restored by cloning
   the repo.

Earlier points: `v6.4-results` before the results module, `v6.3-workflow`
before the daily-workflow unification, `v6.2-complete` before that,
`v6.1-stage6` before the regression suite, `v6.0-stage5` before
longitudinal analysis, `v5.1-stable` before the refactor entirely.
