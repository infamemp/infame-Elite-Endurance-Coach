# Infame Elite Endurance Coach

A methodology-agnostic coaching system for cycling and running. Claude designs
the training; a deterministic Python engine supplies every number it plans on
and checks every week before it reaches an athlete's Intervals.icu calendar.

**Current version:** see the newest `RESTORE_POINT_v*.md` at the root (what the
Claude Project must contain, the machines, the open items). Every version is
in `CHANGELOG.md`; what comes next is in `ROADMAP.md`.

## How it works

| Layer | Where | Job |
|:---|:---|:---|
| Configuration | `config/` | All coaching knowledge as data: 13 methodologies, classes, thresholds |
| Engine | `engine/` | Fetch from Intervals.icu, resolve `#STATE`, project the PMC, check plans |
| Reasoning | Claude Project (`Prompt/`) | Methodology, session design, conversation |
| Verification | `verify/` | The gate: a week that fails is not uploaded |

**The governing rule:** `#STATE` from the engine is authoritative. The coach
plans on top of it and never recalculates it.

Every client reaches the engine the same way: Claude through the MCP server
(`mcp_server/`, 20 tools), scripts and the coming web interface through
`services/`. A rule fixed once is fixed for all of them.

## Daily use

Open a chat in the Claude Project and name the athlete. The coach calls the
tools itself: it loads `#STATE` and the profile, writes each week, saves and
validates it, shows the upload as a dry run and sends it only when you approve.

Setup, the fallback without the server and common problems: `manual/GUIDE.md`.

## Repository

```
coach.py         command line: prep / new / check / review / ledger
config/          authors, thresholds, TSS classes, templates (athletes/ is not in git)
engine/          fetch, state, profile, plan checks, ledger; shared.py = common helpers
verify/          validate_block.py, the hard-constraint gate
services/        the engine as plain functions for scripts and the interface
mcp_server/      the local MCP server Claude Desktop uses
generated/       zone tables, architectures, doctrines — built from config/, never edited
Prompt/          the coach's system prompt, with the two previous versions
Knowledge/       book knowledge bases (Principles/ read by get_knowledge; Catalogs/)
Syntax/          Intervals.icu workout builder reference
tests/           fixtures, golden baselines, both test suites
manual/          GUIDE.md — the one-page guide
archive/         historical design documents
```

Not in git: `data/`, `out/` and `config/athletes/` (real athletes; on the head
coach's computers they are junctions to Google Drive). The Intervals.icu key
lives in the `ICU_API_KEY` environment variable.

## Changing the engine

```bash
python build_zone_tables.py validate    # after editing config/authors/
python build_zone_tables.py build       # regenerate generated/
python tests/run_tests.py               # engine, validator, golden outputs
python tests/test_mcp_server.py         # the MCP server and services/ (needs mcp==1.30.0)
```

GitHub Actions runs both suites on every push. A failing golden test means the
output changed, not necessarily a bug: read the diff, and only if the change
was intended run `python tests/run_tests.py --update` and commit the new
baselines with the change that caused them.
