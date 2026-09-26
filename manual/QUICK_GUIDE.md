# Quick Guide — Infame Elite Endurance Coach

One-page reference for daily use.

**This assumes you've already read `OPERATIONS_MANUAL.md` once.** That's
where every term below — `out/`, `#SESSION`, `#STATE`, "the Claude
Project" — is explained the first time, along with the one-time setup.
Come back here once you know the workflow and just need a fast reminder
of the exact steps.

This guide assumes the `infame-coach` MCP server is connected in Claude
Desktop. That's the everyday path from here on — you talk to the coach,
it calls the tools **by itself** (prompt v7.3+), you only approve.
You never need to name a tool; the table below is for reference. If the server is ever down, see the **Fallback:
without the MCP server** appendix at the end; nothing there is the normal
path anymore.

---

## Tool reference

| Tool | What it does | When to use it | How to ask for it | Where the result lands |
|---|---|---|---|---|
| `get_athlete_state` | Fetches the current `#STATE` (CTL/ATL/TSB, etc.). Skips re-downloading if the cache is fresh. | Opening any new chat with an athlete. Mid-week, if it's been a while since this chat last checked. | *"use get_athlete_state for `<id>`"* — to force a fresh pull: *"…forcing refresh"* | Nothing written to disk — returned straight into the chat. |
| `get_athlete_profile` | Fetches the declared `#PROFILE` (methodology, metric map, availability, etc.). | Same moments as `get_athlete_state` — normally asked together. | *"use get_athlete_profile for `<id>`"* (asking both together never double-fetches) | Nothing written to disk — returned into the chat. |
| `list_roster` | Lists every athlete and when each was last updated. | You forgot an athlete's ID, or want to see who's overdue for an update. | *"use list_roster"* | Nothing written — just reads `out/roster.md` as it was left by the last `prep` run. |
| `save_block` | Saves each week the coach just wrote. Does not validate it. | Automatic, after every week (and again after a correction). | — (the coach does it) | Writes `out/<athlete>/blocks/<today>_bloque_w<week>.md`. A corrected week **overwrites** its own file; a different week saved the same day gets its own file. |
| `validate_block` | Checks the saved block against the validator's rules (RPE tags, methodology, format, etc.) and reports `pending` / `BLOCKED` / upload-safe. Fixes nothing itself. | Immediately after `save_block`, every time — never skip straight to uploading. | — (the coach does it, on the file it just saved; without a path it checks the most recently saved week) | Nothing written — just a report in the chat. |
| `push_block` | Uploads the block to Intervals.icu. By default sends nothing (dry-run); only sends when explicitly told to for real. Validates internally first and refuses a `BLOCKED` block unless told to override. | Automatic after a PASS: the coach first shows a dry-run (how many sessions, which dates) and **waits for your OK** before sending. | Approve with *"sí, súbela"* | Nothing written locally — sends events to Intervals.icu. Re-pushing a corrected block **updates** the same sessions instead of duplicating them; nothing to delete on the Intervals.icu side first. |
| `save_continuity` | Saves the `#SESSION…#END` header that lets you resume the macrocycle in another chat. | Closing a chat you'll need to continue later (end of block, or before opening a new chat mid-week). | *"save this with save_continuity for `<id>`"* | Writes `out/<athlete>/continuity.md`, **always overwriting** what was there. Refuses to save if the block is incomplete, so it never leaves you with a half-written file. |
| `save_race_result` | Saves a `#RACE_RESULT` summary after a race debrief. | Right after the coach gives you the race summary. | *"save this with save_race_result for `<id>`, date `<YYYY-MM-DD>`"* | **Appends** to `out/<athlete>/race_notes.md` — never deletes or overwrites what's already there. Adds the header/date automatically if the coach's text is missing them. |

---

## Onboarding a new athlete

1. Tell the coach: **"let's onboard a new athlete, ID `<id>`"**
2. The coach walks you through a conversational intake (~10 minutes):
   methodology, availability, equipment, terrain, etc.
3. At the end, the coach gives you the completed profile as text (YAML).
4. **There's no tool for this step yet** — it's the one piece of the
   whole flow still done by hand. Open `config/athletes/<id>.yaml` in
   Notepad, select all, replace with what the coach gave you, and save.
5. Tell the coach it's saved; it reloads the profile by itself.

**Note:** athlete files are gitignored by design (they hold personal
data). `config/athletes/`, `data/` and `out/` point to Google Drive on
both machines, so the file is already available on the other machine —
no copy, no commit.

---

## Opening a new chat with an athlete

1. Tell the coach who: **"Trabajemos con `<nombre o id>`"**
   → The coach calls `list_roster` (if needed), `get_athlete_state` and
   `get_athlete_profile` by itself. `get_athlete_state` also brings the
   saved `continuity.md` and race notes — nothing to paste or drag.

Do this once per chat — not again partway through the same conversation.

---

## Mid-week question, staying in the same chat

Just ask — the coach already has current numbers in context from earlier
in this chat. If it's been a while, ask it to re-run `get_athlete_state`
first.

## Mid-week question, opening a brand-new chat instead

1. Before closing the chat you're in now, ask the coach: **"guarda la
   continuidad"** — it emits `#SESSION` and saves it with
   `save_continuity` by itself.
2. Open the new chat and repeat "Opening a new chat with an athlete"
   above.

---

## End of a training block

1. The coach shows you a boxed `#SESSION` block on its own once the
   block ends — you don't have to ask for it.
   It saves it with `save_continuity` by itself (overwrites
   `continuity.md` completely).
2. Optional: to see what actually changed, ask the coach to run
   `python coach.py review <id> --since <block start date>` — this one
   is still a terminal command; there's no tool for it yet.

## After a race

1. During the debrief, the coach gives you a `#RACE_RESULT` block.
2. The coach saves it with `save_race_result` by itself → appends to
   `race_notes.md`, never deleting what's there.
3. The next time you run `review`, this result shows up automatically —
   no extra step.

---

## Validating and uploading a week

All automatic after each week the coach writes — you only approve the upload:

1. The coach writes the week, saves it (`save_block`) and validates it
   (`validate_block`), and tells you **PASS** or **BLOCKED**.
2. **BLOCKED** → the coach corrects the full week, saves and validates
   again by itself. Nothing is uploaded.
3. **PASS** → the coach shows a dry-run: how many sessions, which dates,
   and any workouts already planned in Intervals.icu on those dates.
4. You approve (*"sí, súbela"*) → the coach sends it with `push_block`.
   Re-uploading a corrected week **updates** the same sessions, never
   duplicates them. Workouts that were already planned on those dates
   are not deleted — remove them in Intervals.icu if the coach flags any.

Never ask for an override of a BLOCKED week unless you know exactly what
you're bypassing.

---

## Golden rules

- A **code** fix isn't real until it exists on **both** machines and is
  pushed to GitHub — see Manual §0. The MCP server doesn't change how
  code changes get synced.
- The MCP server only runs on the machine it's configured on. If you
  work from both machines, the git sync discipline in Manual §11 still
  matters — the server writes to the local repo copy on whichever
  machine you're using.
- Run `python tests/run_tests.py` any time you edit anything inside
  `config/` or `engine/`.
- `get_athlete_state` tells you itself whether its answer came from
  cache or a fresh pull — you don't need to eyeball a file's date to
  judge staleness anymore.
- Never type inside `continuity.md` by hand. The only thing that ever
  goes in there is a fresh `#SESSION` block, saved through
  `save_continuity`.
- If you ever make the repo public for a review, set it back to private
  the same day: GitHub → Settings → Danger Zone → Change visibility.

---

## Common problems

| You see | It means | What to do |
|---|---|---|
| `infame-coach` shows "Failed" in Claude Desktop → Settings → Developer | The server didn't start | Click **View logs** and check the error against Manual §4a's troubleshooting table |
| A tool call hangs for several minutes then times out | Known stdio issue, already fixed in the current server code | Make sure you're on the latest `git pull` and restarted Desktop after |
| `push_block` refuses with "validate_block reports this file is BLOCKED" | Working as intended — it won't upload a block that failed validation | Fix the flagged issue, `save_block` and `validate_block` again; only pass an override if you're deliberately bypassing it |
| `validate_block` keeps reporting `BLOCKED` on the same field after a correction | The coach's correction didn't actually change the flagged line, or `save_block` wasn't re-run after it | Confirm the coach re-emitted the full corrected block, then `save_block` again before validating |
| Errors mentioning device name or "remote-devices" | You're in a Cowork/Code session, not plain Chat | Retry from a plain Chat conversation in the Project |
| `cannot validate — Unknown methodology 'X'` | The `[Methodology]` field doesn't match a real file in `config/authors/` | Take it back to the coach as a correction — see Manual §6 |
| `FAIL [HC-DUAL] … missing quoted cue` | A line is missing its quoted coaching phrase — some methodologies require one on every line | Take it back to the coach as a correction — see Manual §6 |
| `Missing environment variable ICU_API_KEY` | This machine/terminal doesn't have your Intervals.icu key set | See Manual §0 |

---

## Fallback: without the MCP server

Use this only if `infame-coach` is disconnected or down in Claude
Desktop. None of this is the everyday path anymore.

### Opening a terminal

On Windows: press the Windows key, type `PowerShell`, press Enter. Every
command below is typed there, one line at a time, followed by Enter.

### Manual daily commands

| Command | What it does |
|---|---|
| `python coach.py new <id>` | Onboard a new athlete — creates their config file from a template |
| `python coach.py prep --all` | Refresh every athlete at once — mainly useful for a full-roster overview |
| `python coach.py prep --list` | List every athlete and when each was last updated — downloads nothing new |
| `python coach.py review <id> --since <date>` | Compare an athlete's numbers today against a past date |

`<id>` is the athlete's Intervals.icu ID — it looks like `i123456`. Find
it with `python coach.py prep --list` if you don't have it memorized.

### Opening a chat without the MCP server

Run `python coach.py prep <id>`, then drag `state.md`, `profile.md`, and
`continuity.md` (if present) from `out/<athlete_name>/` into the chat
window. Full detail in Manual §4.

### Validating and uploading without the MCP server

Copy only the training block from the coach's message — from the first
`[Week]` line through the `[Nutrition]:` line of the last session, never
the one-line validator instruction or the `───`-bordered `#SESSION …
#END` header (that goes in `continuity.md`, not here). Paste into
Notepad, save under `out/<athlete_name>/blocks/`, then run
`python coach.py check path\to\file` and paste the passed sessions into
Intervals.icu's Workout Builder by hand. Full detail in Manual §6.

### Saving continuity / race results without the MCP server

Copy the coach's `#SESSION…#END` block into `out/<athlete_name>/continuity.md`
by hand, replacing whatever was there. For a race result, add it to the
**end** of `out/<athlete_name>/race_notes.md` by hand — never delete what's
already there.

### Common problems specific to the manual flow

| You see | It means | What to do |
|---|---|---|
| `Athlete not found` | Typo in the id | `python coach.py prep --list` to check the real id |
| `...already exists` (running `new`) | This athlete is already onboarded | Don't run `new` again — edit their existing file directly |
| Avg Power shows blank | Your two machines have different versions of a file | See Manual §11 (keeping machines in sync) |
| `note: no continuity.md here yet` | Normal for week 1 of a new athlete or a new block | Nothing to do |
| `No data for '<id>'` (running `review`) | You haven't run `prep` for this athlete yet | Run `python coach.py prep <id>` first |
| "No curve history yet" (running `review`) | Not an error — this builds up automatically as `prep` keeps running over time | Nothing to do |
| A passed block shows `pending` again after re-running `check` | You pasted an unprocessed copy over an already-validated file | Not a bug — run `check` again on the file as it is now |

---

Need more than this? Everything above is explained step by step, with the
reasoning behind it, in `manual/OPERATIONS_MANUAL.md`.
