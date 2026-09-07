# RESTORE POINT — Infame Elite Endurance Coach v6.6

**Date frozen:** 2026-09-07
**Git tag:** `v6.6-mcp-removed` (tag this commit once pushed)
**Previous restore points:** `v6.5-mcp`, `v6.4-results`, `v6.3-workflow`,
`v6.2-complete`, `v6.1-stage6`, `v6.0-stage5`, `v5.1-stable`
**Status:** Back to the pre-v6.5 workflow. Dragging `out/<athlete_name>/`
into the Claude Project is once again the only way to start a session —
there is no MCP connection option on any machine.

---

## 1. Purpose

Same two jobs as every restore point: freezes the definition of "working"
for v6.6, and is the handoff brief for a new conversation to resume from.

v6.6 does not change the four-layer architecture, and it does not change
what the coach decides or how. It removes an entire alternate entry point
(the MCP server) that v6.5 added. Everything that was true about the
phases, the gates, and the STOP-AND-WAIT discipline in
`RESTORE_POINT_v6.4.md` still holds exactly — this restore point only
undoes what v6.5 added on top of it.

---

## 2. What changed

**The MCP server is gone — code, config, and prompt references, all of
them.**

- `mcp_server/server.py` — deleted. No folder of that name exists in the
  repo anymore.
- `Prompt/infame_elite_endurance_coach.md` — every call to `save_block`,
  `save_continuity`, `save_race_result`, and `validate_block` as tools,
  and the fallback logic around them, was removed. The prompt no longer
  knows MCP tools can exist.
- `config/decision_thresholds.yaml` — the `mcp:` section
  (`state_cache_minutes: 60`) was removed; nothing reads it anymore.
- `coach.py` and everything in `engine/` and `verify/` — confirmed to have
  zero references to MCP. They were never modified to know about the
  server in the first place; the server called them, not the reverse, so
  removing it required no changes here.
- `claude_desktop_config.json` (outside the repo, per machine) — the
  `infame-coach` entry under `mcpServers` should be removed on any machine
  where it was added. Not tracked by git, so this step has to be done by
  hand on each machine; it does no harm left in place (the server it
  points to no longer exists, so Desktop will just fail to connect it),
  but removing it stops Desktop from showing a permanently-broken
  connector.

**Why:** repeated instability in production use, beyond what the two fixes
recorded in `RESTORE_POINT_v6.5.md` addressed. This restore point does not
carry a second incident log — v6.5 already documents the specific bugs
found and fixed (the `SystemExit`-kills-the-server failure, and the
`[Discipline]: road` classification bug) — the decision to remove the
server rather than continue patching it was Michel's, made after
continued problems beyond those two.

**What did NOT change:** the daily workflow itself. `coach.py prep`,
dragging `out/<athlete_name>/` into the Claude Project, and the 6-phase
state machine all work exactly as they did before v6.5 existed. Nothing
about the coaching logic, the config schema, or the verification gate was
touched by either adding or removing MCP.

---

## 3. Repository layout — changes since v6.5

```
mcp_server/                 REMOVED (entire folder)

config/
└─ decision_thresholds.yaml   mcp: section REMOVED

Prompt/
└─ infame_elite_endurance_coach.md   MCP tool-calling logic REMOVED
```

Everything else matches `RESTORE_POINT_v6.5.md` §4 exactly — the
`out/<athlete_name>/blocks/` folder that `save_block` used to write stays
as a folder concept, but nothing writes to it automatically anymore; a
generated block is saved there by hand, the same as `continuity.md` and
`race_notes.md` always have been.

`RESTORE_POINT_v6.5.md` itself was moved to `archive/` rather than
deleted — it is the only complete record of what the MCP server did, the
two bugs it surfaced, and the design of `push_block` (payload shape,
`dry_run` default, idempotent `external_id`). Kept specifically so a
future attempt does not have to re-derive any of that from scratch.

---

## 4. Consequence: no automated upload path

`push_block` lived only inside the MCP server. It has no standalone
existence anywhere else in the codebase. Removing the server means there
is currently **no way to upload a verified block to Intervals.icu except
pasting it by hand into the Workout Builder** — exactly as it worked
before v6.5. This is not a regression introduced by accident; it is the
direct, expected consequence of removing the server that `push_block`
lived inside. See `IMPROVEMENT_BACKLOG.md` §5 for the up-to-date status of
that item.

---

## 5. Known open items

Carried over from v6.5, still open: 16 of 17 athletes have no real profile
in `config/athletes/`; Bosquet and Ingham KBs not yet extracted (Bosquet
resolved as not needed — see `IMPROVEMENT_BACKLOG.md`); Friel running
shares the cycling KB; target TSB ranges are coach heuristic; Coggan power
profile under-ranks heavier/multisport athletes; cycling workout engine
integration not started; `eW'`/`ePmax` rule confirmed against only one
athlete; `build_profile.py` has no dedicated test fixture; the `out/` PII
exposure is closed going forward but not scrubbed from git history; the
`continuity.md` staleness threshold (10 days) is hardcoded in `coach.py`
rather than living in `decision_thresholds.yaml`; `data/<id>/history/` has
no retention limit.

Closed in v6.6:
- **MCP server instability** — resolved by removal rather than further
  patching. No longer an open item; if MCP is attempted again in the
  future, it starts as new work informed by `archive/RESTORE_POINT_v6.5.md`,
  not as a continuation of a known-unstable implementation.

New in v6.6:
- **Documentation-vs-code drift.** `RESTORE_POINT_v6.5.md`, `README.md`,
  `WORKFLOW_CHECKLIST.md`, `IMPROVEMENT_BACKLOG.md`, and both operations
  manuals all continued describing the MCP server as active after it was
  removed from code. Corrected across all of them as part of this same
  documentation audit. Worth a standing habit going forward: when code is
  removed, grep the whole repo for its name before considering the change
  finished — a code-only removal is only half the job.

---

## 6. Restoring

1. Confirm no `mcp_server/` folder exists and no MCP references remain in
   `Prompt/infame_elite_endurance_coach.md` or
   `config/decision_thresholds.yaml`.
2. Replace the Claude Project instructions with
   `Prompt/infame_elite_endurance_coach.md` (the MCP-free version).
3. Upload to the Project: both files from `generated/`, the 8 KBs from
   `Knowledge/`, the syntax reference, `config/athletes/ATHLETE_INTAKE.md`,
   and `config/tss_classes.yaml` — unchanged from v6.5.
4. Confirm `ICU_API_KEY` is set, then run as a smoke test:
   - `python build_zone_tables.py validate` — expect 8/8
   - `python tests/run_tests.py` — expect 76/76
   - `python coach.py prep --list` — expect all 17 athletes
5. On any machine that has Claude Desktop configured with an
   `infame-coach` entry in `claude_desktop_config.json`: removing that
   entry is optional cleanup, not required for the system to work.

Earlier points: `v6.5-mcp` before this removal (kept in `archive/` as the
full incident history), `v6.4-results` before the results module,
`v6.3-workflow` before the daily-workflow unification, `v6.2-complete`
before that, `v6.1-stage6` before the regression suite, `v6.0-stage5`
before longitudinal analysis, `v5.1-stable` before the refactor entirely.
