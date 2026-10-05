# RESTORE POINT — Infame Elite Endurance Coach v7.31

**Date frozen:** 2026-10-05
**Previous:** v7.30 — every version is in `CHANGELOG.md`; older restore points are in the git history
**Prompt:** `Prompt/infame_elite_endurance_coach.md` v7.31
**Tests:** `python tests/run_tests.py` → 755/755 · `.venv-mcp\Scripts\python.exe tests/test_mcp_server.py` → 174/174

## What changed in v7.31

Batch 4 of the 2026-10-05 audit: fewer tokens per conversation, no rule removed.
`python tests/context_budget.py` measures what a conversation loads before any design
work: **~57,400 tokens in v7.30 → ~33,100 in v7.31 (−42%)**.

| Part | v7.30 | v7.31 |
| :--- | ---: | ---: |
| Project instructions (prompt) | ~19,300 | ~18,800 |
| Project knowledge files | ~31,400 (9 files) | ~8,700 (4 files) |
| MCP tool definitions | ~5,400 (19 tools) | ~4,400 (20 tools) |
| `get_athlete_state` (test athlete) | ~1,200 | ~1,200 |

- **New tool `get_reference`** (`engine/reference.py`): the zone tables, the architecture
  library, the intake script and the profile template leave the Project. The coach asks
  for one methodology's zone table (~1,500 tokens instead of ~13,000 for both tables),
  and for the architectures that fit a session's class and discipline.
- **Tool descriptions written for the model.** Each says what the tool does, when to use
  it and what it returns; the development history moved to code comments.
- **`get_knowledge` answers default to 6 KB** (`max_chars` up to 12 KB when needed).
- **Prompt:** the tools table is one line per tool (the details live in each tool's
  description); the validator section says once that `HC-`/`SYN-` codes block and
  `CHK-` codes warn, instead of listing every check; every reference to the files that
  left the Project points to `get_reference`, with a fallback for when the tools are down.
- **`tests/context_budget.py`** (new) for before/after measurements.
- **Deploy:** paste the prompt into the Project instructions; **remove** from the Project
  knowledge `Simple_Table_Cycling_Training_Zones.md`, `Simple_Table_Running_Training_Zones.md`,
  `Session_Architectures.md`, `ATHLETE_INTAKE.md` and `_template.yaml`; restart Claude Desktop.

## How the system is used

1. **Primary path — Claude Desktop + `infame-coach` MCP server.** Open a chat
   in the Claude Project and name the athlete. The coach calls the tools
   itself: `get_athlete_state` (brings `#STATE`, `continuity`, `race_notes`),
   `get_athlete_profile`, then per week `save_block` → `validate_block` →
   `push_block` dry-run → head coach approves → live `push_block`.
   `save_continuity` / `save_race_result` whenever it emits those blocks.
2. **Fallback — only if the server is down:** `python coach.py prep <id>`,
   attach the files, `python coach.py check <file>`, upload by hand.

## What the Project must contain

- **Instructions:** the full text of `Prompt/infame_elite_endurance_coach.md` (v7.31).
- **Knowledge files (flat, no folders):** `generated/Cycling_Doctrine.md`,
  `generated/Running_Doctrine.md`, `generated/Language_Guide_es-MX.md`,
  `Syntax/Intervals Workout Builder Syntax.md`.
- **Read with `get_reference`, not in the Project (v7.31):** the two zone tables
  (`generated/Simple_Table_*_Training_Zones.md`), `generated/Session_Architectures.md`,
  `config/athletes/ATHLETE_INTAKE.md`, `config/athletes/_template.yaml`.
- **Not in the Project:** every book KB (`Knowledge/Principles/*.md`, the Palladino file) —
  the coach reads them with `get_knowledge`. Nothing from `Knowledge/Catalogs/`, `tests/` or
  other `config/` files either.

## Machines

- Laptop: `C:\Dev\Github\infame_elite_endurance_coach` · PC: `E:\Dev\github\infame_elite_endurance_coach`.
- `config/athletes/`, `data/`, `out/` are junctions to Google Drive (never in git).
- The MCP server runs from `.venv-mcp/` on each machine (Claude Desktop config per machine).

## Open items

- **Privacy:** athlete files were removed from the whole git history on 2026-10-02
  (`git filter-repo`). Never commit `out/`, `data/` or `config/athletes/<id>.yaml`; they live
  in Google Drive through junctions. A local `coach_BACKUP.git` on the PC still holds the old
  history: delete it once it is no longer needed.
- `push_block` does not delete workouts already planned on those dates;
  the coach names them and the head coach removes them.
- `coach.py review` has no tool yet.
- Knowledge layer plan (audit of 2026-10-02): complete. Every new book goes to
  `Knowledge/Principles/` and is reached with `get_knowledge`; never upload books to the Project.
