# Quick Guide — Infame Elite Endurance Coach

One-page reference for daily use.

**This assumes you've already read `OPERATIONS_MANUAL.md` once.** That's
where every term below — `out/`, `#SESSION`, `#STATE`, "the Claude
Project" — is explained the first time, along with the one-time setup.
Come back here once you know the workflow and just need a fast reminder
of the exact steps.

---

## Opening a terminal (if you need the reminder)

On Windows: press the Windows key, type `PowerShell`, press Enter. Every
command below is typed there, one line at a time, followed by Enter.

---

## Daily commands

| Command | What it does |
|---|---|
| `python coach.py new <id>` | Onboard a new athlete — creates their config file from a template |
| `python coach.py prep --all` | Refresh every athlete at once — mainly useful for a full-roster overview |
| `python coach.py prep --list` | List every athlete and when each was last updated — downloads nothing new |
| `python coach.py review <id> --since <date>` | Compare an athlete's numbers today against a past date |

`<id>` is the athlete's Intervals.icu ID — it looks like `i123456`. Find it
with `python coach.py prep --list` if you don't have it memorized.

**If the MCP server (`infame-coach`) is connected in Claude Desktop**,
you no longer run `python coach.py prep <id>` or `python coach.py check
<file>` by hand for day-to-day work — just ask the coach to use the
matching tool directly (`get_athlete_state`, `get_athlete_profile`,
`save_block`, `validate_block`, `save_race_result`, `push_block`). See
the sections below. The CLI commands above still exist and still work;
they're just no longer the everyday path. Full detail in Manual §4a.

---

## Onboarding a new athlete

1. `python coach.py new i123456` — creates their config file automatically.
   You never open or edit the template yourself.
2. Open a new chat in the Claude Project and tell the coach you're
   onboarding someone new. No need to attach or drag in anything — the
   coach already knows the intake script.
3. Answer the coach's questions conversationally (~10 minutes).
4. At the end, the coach gives you the completed profile as text. Open
   `config/athletes/i123456.yaml` in Notepad, select all, replace it
   with what the coach gave you, and save.
5. Copy to both machines, commit, push — same as any other file.

Full detail in Manual §1. This flow is unchanged by the MCP server —
there's no tool yet for writing an athlete's declared profile.

---

## Every time you open a new chat with an athlete

**With the MCP server connected:** just ask the coach directly, e.g.
*"use get_athlete_state and get_athlete_profile for i123456."* No prep
command, no dragging files — it pulls fresh data itself.

**Then, only if this athlete already has a `continuity.md`** (meaning a
session already happened during this training block): open
`out/<athlete_name>/continuity.md` and paste its contents into the chat
as a message. There's no tool that reads this file for the coach yet —
this is the one piece still done by hand, but it's a paste, not a drag.

**Without the MCP server** (fallback, or if it's ever down): follow the
old flow — run `python coach.py prep <id>`, then drag `state.md`,
`profile.md`, and `continuity.md` (if present) from `out/<athlete_name>/`
into the chat window. Full detail in Manual §4.

Do this once per chat — not again partway through the same conversation.

---

## Mid-week question, staying in the same chat

Just ask your question — the coach already has current numbers in
context from earlier in this chat. If it's been a while, ask it to
re-run `get_athlete_state` first.

## Mid-week question, opening a brand-new chat instead

1. Before closing the chat you're in now, ask the coach: *"give me the
   continuity header."*
2. Ask the coach to save it with `save_continuity` for this athlete —
   or, if the MCP server isn't available, copy what it gives you into
   `out/<athlete_name>/continuity.md` by hand, replacing whatever was
   there.
3. Open the new chat, ask for `get_athlete_state` / `get_athlete_profile`,
   then paste in the continuity content as described above.

---

## End of a training block

1. The coach shows you a boxed `#SESSION` block on its own once the block
   ends — you don't have to ask for it.
2. Ask the coach to save it with `save_continuity` for this athlete (or,
   without the MCP server, copy it into `out/<athlete_name>/continuity.md`
   by hand, replacing the old one).
3. Optional: `python coach.py review <id> --since <block start date>` to
   see what actually changed.

## After a race

1. During the debrief, the coach gives you a `#RACE_RESULT` block.
2. Ask the coach to save it with `save_race_result` for this athlete — it
   appends to the end of `race_notes.md` itself and refuses a conflicting
   duplicate `Date:` field. Without the MCP server, add it to the **end**
   of `out/<athlete_name>/race_notes.md` by hand instead — never delete
   what's already there.
3. `review` picks it up automatically the next time you use it.

---

## Validating and uploading a block

**With the MCP server:**
1. Ask the coach to save the block with `save_block` for this athlete.
   (`save_block` only writes — it doesn't check anything yet.)
2. Ask it to run `validate_block` on what it just saved.
3. Seeing `pending` for TSS/Duration is still normal until `validate_block`
   actually runs — same as before, the coach's own text never carries the
   computed number.
4. If it reports `BLOCKED`, take the specific failure back to the coach as
   a correction, save again, and validate again — same loop as always,
   just without Notepad in between.
5. Once it says upload-safe, ask the coach to `push_block`. It will
   **refuse on its own** if the block is still `BLOCKED` — you'd have to
   explicitly ask for an override to bypass that, which you should never
   need in normal use.

**Without the MCP server** (fallback): copy only the training block from
the coach's message — from the first `[Week]` line through the
`[Nutrition]:` line of the last session, never the one-line validator
instruction or the `───`-bordered `#SESSION ... #END` header (that goes
in `continuity.md`, not here). Paste into Notepad, save under
`out/<athlete_name>/blocks/`, then `python coach.py check path\to\file`
and paste the passed sessions into Intervals.icu's Workout Builder by
hand. Full detail in Manual §6.

---

## Golden rules

- A **code** fix isn't real until it exists on **both** machines and is
  pushed to GitHub — see Manual §0. This still applies fully; the MCP
  server doesn't change how code changes get synced.
- The MCP server only runs on the machine it's configured on. If you
  work from both machines, `out/<athlete>/continuity.md` and the git
  sync discipline in Manual §11 still matter — the MCP server writes to
  the local repo copy on whichever machine you're using, same as the old
  manual files did.
- Run `python tests/run_tests.py` any time you edit anything inside
  `config/` or `engine/`.
- `get_athlete_state` always pulls fresh data itself — there's no "stale
  #STATE" warning to watch for anymore when using the MCP server. The old
  7-day-staleness warning only applies to the manual/CLI fallback path.
- Never type inside `continuity.md` by hand. The only thing that ever
  goes in there is a fresh `#SESSION` block — whether written by
  `save_continuity` or pasted in whole.
- If you ever make the repo public for a review, set it back to private
  the same day: GitHub → Settings → Danger Zone → Change visibility.

---

## Common problems

| You see | It means | What to do |
|---|---|---|
| `Missing environment variable ICU_API_KEY` | This terminal doesn't have your Intervals.icu key set | See Manual §0 |
| `Athlete not found` | Typo in the id | `python coach.py prep --list` to check the real id |
| `...already exists` (running `new`) | This athlete is already onboarded | Don't run `new` again — edit their existing file directly |
| Avg Power shows blank | Your two machines have different versions of a file | See Manual §11 (keeping machines in sync) |
| `note: no continuity.md here yet` | Normal for week 1 of a new athlete or a new block | Nothing to do |
| `No data for '<id>'` (running `review`) | You haven't run `prep` for this athlete yet | Run `python coach.py prep <id>` first |
| "No curve history yet" (running `review`) | Not an error — this builds up automatically as `prep` keeps running over time | Nothing to do |
| `cannot validate — Unknown methodology 'X'` (running `check`) | The `[Methodology]` field doesn't match a real file in `config/authors/` | Take it back to the coach as a correction — see Manual §6 |
| `FAIL [HC-DUAL] ... missing quoted cue` (running `check`) | A line is missing its quoted coaching phrase — some methodologies require one on every line | Take it back to the coach as a correction — see Manual §6 |
| A passed block shows `pending` again after re-running `check` | You pasted an unprocessed copy over an already-validated file | Not a bug — run `check` again on the file as it is now |
| `infame-coach` shows "Failed" in Claude Desktop → Settings → Developer | Server didn't start | Click **View logs** and check the error against Manual §4a's troubleshooting table |
| A tool call hangs for several minutes then times out | Known stdio issue, already fixed in the current server code | Make sure you're on the latest `git pull` and restarted Desktop after |
| `push_block` refuses with "validate_block reports this file is BLOCKED" | Working as intended — it won't upload a block that failed validation | Fix the flagged issue and validate again; only pass `override_validation=True` if you're deliberately bypassing it |
| Errors mentioning device name or "remote-devices" | You're in a Cowork/Code session, not plain Chat | Retry from a plain Chat conversation in the Project |

---

Need more than this? Everything above is explained step by step, with the
reasoning behind it, in `manual/OPERATIONS_MANUAL.md`.
