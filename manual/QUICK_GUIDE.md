# Quick Guide — Infame Elite Endurance Coach v6.1

One-page reference. Full detail in `OPERATIONS_MANUAL.md`.

## Daily commands

| Command | Does |
|---|---|
| `python coach.py new <id>` | Onboard a new athlete (creates config from template) |
| `python coach.py prep <id>` | Fetch + resolve + render one athlete → `out/<name>/` |
| `python coach.py prep --all` | Same, for every athlete on the account |
| `python coach.py prep --list` | List athletes, refresh `out/roster.md`, fetch nothing |
| `python coach.py check <file>` | Validate a block and fill its TSS before uploading |
| `python coach.py review <id> --since <date>` | Compare a block's signals against today |

## Every new chat with an athlete

Drag from `out/<athlete_name>/`:

- [ ] `state.md` — always
- [ ] `profile.md` — always
- [ ] `continuity.md` — only if it exists (means a session already happened this block)

No need to re-drag mid-conversation — only when opening a **new** chat.

## Working via MCP (Claude Desktop only, not the browser)

One-time setup per machine: `python -m pip install "mcp[cli]" pyyaml
requests`, then add `infame-coach` to `claude_desktop_config.json` with an
`"env": {"ICU_API_KEY": "..."}` block (Desktop doesn't reliably inherit
`setx` env vars). Full detail: `OPERATIONS_MANUAL.md` §0 and §10.

| Tool | Replaces |
|---|---|
| `get_athlete_state` / `get_athlete_profile` | dragging `state.md` / `profile.md` (1h cache, say "give me the updated state" to force) |
| `list_roster` | `coach.py prep --list` |
| `save_continuity` / `save_race_result` / `save_block` | copy-pasting into `continuity.md` / `race_notes.md` / a block file — coach calls these itself now |
| `validate_block` | `coach.py check <file>` — coach calls this itself right after `save_block` |
| `push_block` | pasting into Intervals.icu's Workout Builder — **never automatic**; ask for it, defaults to a dry run |

## Mid-week off-calendar consult

1. `python coach.py prep <id>`
2. Staying in the same chat? Nothing else needed.
3. Opening a **new** chat instead? Before closing this one, ask the coach:
   *"give me the continuity header"*
4. Paste the `#SESSION` it returns into `out/<name>/continuity.md`

## End of block

1. Coach auto-emits a bordered `#SESSION` after the last session
2. Copy it into `out/<name>/continuity.md` — automatic if `save_continuity`
   is available as a tool
3. `python coach.py prep <id>` before the next chat
4. Optional: `python coach.py review <id> --since <block start>` to see
   what actually moved (CTL/ATL/TSB, ACWR, durability work now; curve
   progression needs snapshot history to accumulate first)

## After a race (Phase 6)

1. Coach emits a `#RACE_RESULT` block during the debrief
2. Append (never overwrite) it to `out/<name>/race_notes.md` — automatic
   if `save_race_result` is available as a tool
3. `review` picks it up automatically for any window that includes that date

## Golden rules

- A fix isn't "installed" until it's on **both** machines and committed
- Run `python tests/run_tests.py` after touching `config/` or `engine/`
- `#STATE` older than 7 days → coach refuses to proceed; re-run `prep`
- Never hand-edit `continuity.md` except by pasting a fresh `#SESSION`
- Repo made public for a review? Set it back to private when done

## Common errors

| Error | Fix |
|---|---|
| `Missing environment variable ICU_API_KEY` | `setx ICU_API_KEY "..."`, open a new terminal |
| `Athlete not found` | `python coach.py prep --list` to check the real id |
| `...already exists` (on `new`) | Athlete already onboarded — edit the YAML directly |
| Avg Power blank on power-meter activities | Machines out of sync — recopy the affected file to both |
| `note: no continuity.md here yet` | Normal for week 1 of a block — not an error |
| `No data for '<id>'` (on `review`) | Run `python coach.py prep <id>` first |
| "No curve history yet" (on `review`) | Not an error — snapshot capture just started, clears up over time |
| MCP: "Server disconnected" / hangs then times out | `ICU_API_KEY` missing from the `env` block in `claude_desktop_config.json` — check `%APPDATA%\Claude\logs\mcp-server-infame-coach.log` |
| MCP tool missing after config edit | Quit Desktop from the tray icon (not just the window), reopen |
