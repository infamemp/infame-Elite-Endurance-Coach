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

## Mid-week off-calendar consult

1. `python coach.py prep <id>`
2. Staying in the same chat? Nothing else needed.
3. Opening a **new** chat instead? Before closing this one, ask the coach:
   *"give me the continuity header"*
4. Paste the `#SESSION` it returns into `out/<name>/continuity.md`

## End of block

1. Coach auto-emits a bordered `#SESSION` after the last session
2. Copy it into `out/<name>/continuity.md`
3. `python coach.py prep <id>` before the next chat
4. Optional: `python coach.py review <id> --since <block start>` to see
   what actually moved (CTL/ATL/TSB, ACWR, durability work now; curve
   progression needs snapshot history to accumulate first)

## After a race (Phase 6)

1. Coach emits a `#RACE_RESULT` block during the debrief
2. Append (never overwrite) it to `out/<name>/race_notes.md`
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
