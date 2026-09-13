# Operations Manual — Infame Elite Endurance Coach

Step-by-step guide to the daily workflow. Written so that someone who has
never touched this system before can follow it from the first page to
running their first athlete, without having to already know what a
terminal, a repository, or a config file is.

This manual covers **operational use** — what you actually do, day to
day. For internal architecture (why the system is built the way it is),
see `ARCHITECTURE_v6.md`. For system setup, maintenance, and adding a new
coaching methodology, see `WORKFLOW_CHECKLIST.md` — that document
complements this one, it does not repeat it.

> **Already know the system and just need a fast reminder?** Use
> `manual/QUICK_GUIDE.md` instead — a one-page cheat sheet that assumes
> you've read this manual once already.

---

## Before you start — a few things this manual assumes

If any of this is unfamiliar, read this section once. Everything else in
the manual builds on it.

**"The terminal" / "PowerShell."** This is a program on Windows where you
type commands instead of clicking buttons. To open it: press the Windows
key, type `PowerShell`, and press Enter. A black or blue window opens with
a blinking cursor — that's where every `python ...` command in this
manual gets typed, one line at a time, followed by Enter.

**"The repo" / "the repository."** This is the whole project folder —
all the code, configuration files, and documents that make up Infame
Elite Endurance Coach. You have a copy of it on each of your two
machines. "Cloning" or "pulling" the repo means downloading that copy
through GitHub Desktop.

**"Commit" and "push."** When you change a file in the repo, GitHub
Desktop lets you save that change with a short description (a "commit"),
and then send it up to GitHub online (a "push") so both your machines —
and this system's own backup — have the same version. A change that
only exists on your computer and hasn't been pushed is not safe yet.

**"The Claude Project."** This is a saved conversation space in
claude.ai, set up once, that already contains the coach's instructions
and its knowledge base. Every day-to-day conversation with the coach
happens by opening a new chat *inside* that Project — never a plain,
unrelated Claude chat.

**"Dragging files into the chat."** Several steps below tell you to
"drag `state.md` into the Claude Project." This means: open the folder
where that file lives (in Windows File Explorer), and drag the file's
icon into the open chat window in your browser or the Claude desktop
app, the same way you'd attach a file to an email.

**"Athlete config" / "the YAML file."** Each athlete you coach has one
file, `config/athletes/<their_id>.yaml`, that stores what *they* told you
about themselves — age, weight, available equipment, methodology
preferences. It never stores measured numbers like current fitness or
race history; those come from Intervals.icu automatically every time you
run `prep` (explained in section 2).

**Command formatting in this manual.** Anything shown like this:
```
python coach.py prep i123456
```
is meant to be typed into the terminal exactly as written, replacing
placeholders like `i123456` with the real value for your situation
(here, an actual athlete id).

---

## 0. Before you start — requirements on each machine

This must be in place on **both** machines (laptop and desktop) before
running anything else in this manual.

1. **Python installed**, with the project's dependencies installed:
   ```
   pip install -r requirements.txt
   ```
   Run this from the repo's root folder (where `requirements.txt`
   lives, next to `coach.py`). It installs everything the daily
   workflow needs: `requests`, `pyyaml`, and `jsonschema`.

2. **`ICU_API_KEY` set as an environment variable** — this is your
   Intervals.icu API key, stored so the scripts can use it without you
   typing it every time:
   ```
   setx ICU_API_KEY "your_key_here"
   ```
   After running this, close the terminal window completely and open a
   new one — `setx` only takes effect in terminals opened after it runs.

3. **The repo up to date — same commit on both machines.** If you just
   received a corrected file from a Claude chat, it has to reach **both**
   paths before you continue:
   ```
   C:\Dev\Github\infame_elite _endurance_coach\
   E:\Dev\github\infame_elite_endurance_coach\
   ```
   (the space in the first path, between `elite` and `_endurance`, is
   real — it's how that folder was originally named on that machine, not
   a typo you need to fix)

**Golden rule:** a fix you got from a Claude chat is not "installed"
until it exists on both machines and is committed and pushed to GitHub.
A corrected file that only lives in a chat download, sitting in your
Downloads folder, does not count yet.

---

## 1. Onboard a new athlete

Three things are worth knowing before you start, because the words
"template" and "profile" suggest a form you'd fill in yourself — that's
not how this works.

- **You never open or edit the template directly.** It already lives in
  your repo at `config/athletes/_template.yaml`. The command below
  copies it for you automatically — you don't fetch it from anywhere,
  and you don't need to find it first.
- **You don't fill it in — a conversation with the coach does.** The
  athlete's answers go in through a normal back-and-forth chat, and the
  coach hands you the finished file at the end. You never write YAML by
  hand for this.
- **"Uploading" it just means saving it in place.** There's no separate
  destination — it's the same file the command already created,
  overwritten with real content, then committed and pushed like any
  other file in the repo.

**Step 1 — create the empty profile.**
```
python coach.py new i123456
```
This confirms the id is real on your Intervals.icu account (catching a
typo before anything is created), then copies the template to
`config/athletes/i123456.yaml`. If that file already exists for this
athlete, the command stops and changes nothing — it never overwrites a
real profile.

**Step 2 — run the intake conversation.**
Open a new chat in the Claude Project and tell the coach you're
onboarding a new athlete (or just start describing the situation). You
don't need to open, attach, or drag in `config/athletes/ATHLETE_INTAKE.md`
— that file was already uploaded to the Project once, when it was set
up, so the coach already knows the full interview script and will
conduct it for you, in the athlete's own language. It's eight short
parts — identity, goal, injuries, weekly availability, training
environment, history, devices, preferences — roughly ten minutes for
someone with a training history, less for a complete beginner.

**Step 3 — save what the coach gives you.**
At the end of the conversation, the coach delivers the completed profile
as plain text, already in the right format. Open
`config/athletes/i123456.yaml` in Notepad, select everything, and
replace it with what the coach gave you — the whole file, not a partial
edit. Save.

**Step 4 — treat it like any other repo file.**
Copy it to both machines, commit, and push — same as every other
correction in this manual. There is no other place this file needs to
go. The athlete is now ready for their first `prep` (section 2); running
`prep` is not part of onboarding itself, since intake never depends on
any Intervals.icu data — only on what the athlete declares about
themselves.

---

## 2. Prepare one athlete for a session (daily use)

This is the command you'll run most often — once per athlete, before
every chat where you'll design or discuss their training.

**Command:**
```
python coach.py prep i123456
```

**What it does, in order:**
1. Pulls fresh data from Intervals.icu (wellness, fitness numbers,
   recent activities, upcoming calendar).
2. Resolves their current training state into `state.md` — the
   authoritative numbers the coach will reason from.
3. Renders their raw context into `profile.md` — everything else about
   them (profile details, calendar, activity history).
4. Copies both files into `out/<athlete_name>/` — the folder you'll drag
   into the chat.
5. Tells you whether `continuity.md` exists in that folder already, and
   how many days old it is.
6. Refreshes `out/roster.md`, a name-to-id list of every athlete, with
   today's date.

**Expected console output:**
```
Ready — drag out/elias_caballero/ (state.md, profile.md) into the Claude Project
continuity.md last updated 3 day(s) ago
```

Seeing `note: no continuity.md here yet` is normal for an athlete's first
week, or the start of a new training block — it is not an error, just a
statement of fact.

---

## 3. Prepare every athlete at once

**Command:**
```
python coach.py prep --all
```

Runs section 2's steps for every athlete with data on your Intervals.icu
account. At the end:
```
Done. 21/23 athletes ready in out/
```

If any athlete fails (for example, an inactive account), the summary
line tells you how many of how many succeeded — scroll up to see the
per-athlete detail printed above it for the specific reason.

**To see who's who without downloading anything new:**
```
python coach.py prep --list
```
Lists every athlete (id and name) and regenerates `out/roster.md` with
each one's real last-fetch date — useful for spotting, at a glance, who
is overdue for a refresh.

---

## 4. What to drag into the Claude Project, and when

**If the MCP server is set up (see §4a), you don't need this section for
day-to-day work** — the coach pulls the same data itself, on request,
with no dragging. This section is now the manual fallback path: what to
do if the MCP server isn't configured on the machine you're using, or if
it's ever down.

When opening a new chat for an athlete, drag the whole `out/<athlete_name>/`
folder, or the individual files inside it, into the chat window:

| File | Always present? | What it is |
|---|---|---|
| `state.md` | Yes | The authoritative numbers — fitness, fatigue, form, testing status, everything the engine has calculated |
| `profile.md` | Yes | Raw context — the athlete's profile, sport setup, calendar, and recent activity history |
| `continuity.md` | Only once a session has already happened in this training block | The saved `#SESSION` note — where the current macrocycle stands |

**You don't need to re-drag anything partway through a conversation** —
once a chat has the files, the coach keeps them in context for the rest
of that session. Only re-drag when opening a **brand-new** chat.

---

## 4a. Using the MCP server instead (recommended)

The MCP server (`mcp_server/`) connects Claude Desktop directly to the
coaching tools, so the coach can pull an athlete's data, save a block,
validate it, and upload it — all from inside the conversation, with no
terminal command and no drag-and-drop. This replaces §4 and most of §6
for day-to-day use. It runs on whichever machine has it configured; it
does not remove the need to sync **code** changes between machines (§11
still applies for that).

**What it does *not* change:** the phase-gated approval workflow (§5) is
untouched. The coach still proposes and stops at every STOP-AND-WAIT
point; you still explicitly approve before it advances. This is purely
about how data moves in and out — not about what the coach decides or
when.

### One-time setup, per machine

1. Create a dedicated virtual environment inside the repo, so this
   dependency never mixes with the regular `coach.py` environment:
   ```
   python -m venv .venv-mcp
   .venv-mcp\Scripts\pip.exe install "mcp==1.30.0" pyyaml requests
   ```
2. Find Claude Desktop's actual config file. **Don't assume the path** —
   inside the app, go to **Settings → Developer → Edit config**, and read
   the address bar of the file explorer window it opens. This has landed
   in different places across different installs of Desktop.
3. Add this block to that file (merge it in if the file already has other
   content — don't overwrite the whole file):
   ```json
   {
     "mcpServers": {
       "infame-coach": {
         "command": "C:\\Dev\\Github\\infame_elite_endurance_coach\\.venv-mcp\\Scripts\\python.exe",
         "args": ["-m", "mcp_server.run_server"],
         "cwd": "C:\\Dev\\Github\\infame_elite_endurance_coach",
         "env": {
           "ICU_API_KEY": "your Intervals.icu API key",
           "PYTHONPATH": "C:\\Dev\\Github\\infame_elite_endurance_coach"
         }
       }
     }
   }
   ```
   Both `cwd` **and** `PYTHONPATH` are needed — Desktop has not reliably
   honored `cwd` on its own, so `PYTHONPATH` is a required backup, not
   redundant.
4. **If editing this file with PowerShell**, don't use
   `Set-Content -Encoding UTF8` — it adds a byte-order-mark that Desktop
   can't parse and the app will fail to open with "Couldn't load app
   settings." Use:
   ```
   [System.IO.File]::WriteAllText($path, $json, [System.Text.Encoding]::ASCII)
   ```
5. Fully quit Claude Desktop (system tray → Quit, not just closing the
   window) and reopen it.
6. Confirm in **Settings → Developer** that `infame-coach` shows
   **Running**, not **Failed**.

### The tools

| Tool | Replaces | Notes |
|---|---|---|
| `list_roster` | `coach.py prep --list` | Read-only |
| `get_athlete_state` | `coach.py prep` + dragging `state.md` | Read-only; pulls fresh data itself, same as `prep` |
| `get_athlete_profile` | dragging `profile.md` | Read-only |
| `save_continuity` | pasting a `#SESSION` block into `continuity.md` by hand | Requires the `#SESSION ... #END` wrapper — the coach adds it if you don't |
| `save_block` | pasting a block into Notepad | Write only — doesn't check anything |
| `validate_block` | `coach.py check` | Same exit codes: 0 = upload-safe, 1 = blocked |
| `save_race_result` | editing `race_notes.md` by hand | Appends; rejects a duplicate `Date:` field to prevent conflicting data |
| `push_block` | pasting into Intervals.icu's Workout Builder by hand | Requires **both** `dry_run=False` and `confirm=True`; also refuses on its own if `validate_block` reports the file `BLOCKED`, unless `override_validation=True` is explicitly passed |

**`continuity.md` is the one piece that stays manual either way** — no
tool reads it back for the coach yet. When opening a new chat for an
athlete who already has one, open `out/<athlete_name>/continuity.md` and
paste its contents into the chat as a message (this is confirmed to
still land in the same `out/<athlete_name>/` folder the manual has always
used, keyed off the athlete's declared name — not a new ID-based folder —
as long as that athlete has been fetched at least once already).

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Couldn't load app settings" on Desktop launch | BOM added by `Set-Content -Encoding UTF8` | Rewrite with `WriteAllText(..., Encoding.ASCII)` |
| Server shows "Failed" / `ModuleNotFoundError: No module named 'mcp_server'` | `cwd` not honored by Desktop | Add `PYTHONPATH` to the `env` block |
| `validate_block`/`push_block` say "File not found" for a file that demonstrably exists | Relative path resolved against process cwd instead of the repo root | Fixed in the current server code — pull latest and restart Desktop |
| A tool call hangs for several minutes then times out | The subprocess inherited the live stdio pipe as its own stdin | Fixed in the current server code — pull latest and restart Desktop |
| `validate_block` fails with no real error content | Unicode encoding crash on Windows (box-drawing characters) | Fixed in the current server code — pull latest and restart Desktop |
| Errors mentioning a device name or "remote-devices" | The conversation was in Cowork or Code mode, not plain Chat | Retry from a plain Chat conversation |
| `push_block` refuses, citing `validate_block` as BLOCKED | Working as intended | Fix the flagged issue and validate again; `override_validation=True` only for a deliberate, conscious bypass |

---

## 5. Generate a plan or follow up (inside the chat)

Once the files are dragged in, just talk to the coach in plain language
— there's no special syntax to learn. The system moves through a
sequence of six phases (Phase 0 through Phase 6) that it manages on its
own, based on what it reads from the files you dragged in:

- **Athlete with no prior `#SESSION`** (a brand-new macrocycle) → the
  coach starts at Phase 1 (verification, and intake if that's still
  needed), builds the overall training plan, and reaches Phase 4 (where
  it starts generating actual sessions).
- **Athlete with a `continuity.md`** → the coach reads the saved
  `#SESSION` note, reconstructs exactly where things stood, and resumes
  directly from there — you don't need to re-explain anything.

At every phase, the coach stops and waits for your explicit
confirmation before moving forward — for example, before it generates
the actual Intervals.icu code in Phase 4. This is intentional: review
what it proposes before approving it, the same way you'd review a plan
before telling an athlete to start it.

---

## 6. Validate and upload a block to Intervals.icu

**With the MCP server (§4a), this whole section collapses to three asks
in the chat:** save the block with `save_block`, check it with
`validate_block`, and once it's upload-safe, ask for `push_block` — which
now refuses on its own if the block is still `BLOCKED`, so you can't
accidentally upload a failed one. No Notepad, no manual paste into the
Workout Builder. The rest of this section is the manual fallback path —
useful if the MCP server isn't set up on the machine you're using, or as
background for understanding what the tools above are actually doing
under the hood.

When the coach delivers a block of sessions, its message has up to three
distinct parts, always in this order. **Only the first one goes into a
file.**

1. **The training block itself.** Starts at the first line that begins
   with `[Week]`, and runs through every session's fields (`[Category]`,
   `[Methodology]`, `[Discipline]`, `[Focus]`, `[Duration]`/
   `[Estimated TSS]`, `[Execution]`, `[Nutrition]`) plus its code snippet,
   repeating session after session. **It ends at the `[Nutrition]:` line
   of the very last session.**
2. **A one-line instruction telling you to run the validator.** Never
   copy this — it's a note to you, not training content.
3. **A row of `───` characters, followed by a boxed `#SESSION ... #END`
   header.** This is the continuity header, covered in sections 7 and 8
   — a completely different file (`continuity.md`), never the block file.

**How to spot the boundary, for any block the coach ever gives you —
not just this one:** the block is nothing but repeating
`[Week]` → `[Nutrition]:` sessions, one after another. The instant the
text stops looking like that — a plain sentence, or a row of `───` —
you've reached the end. Stop copying there, every time, regardless of
the dates or the number of sessions involved.

**Getting it into a file:**
1. Open Notepad (Windows key → type `notepad` → Enter).
2. Select and copy only the block, using the boundary above.
3. Paste it into Notepad.
4. Save As, into `out\<athlete_name>\blocks\` (create that folder if it
   doesn't exist yet), with any name you like. The file extension
   doesn't matter — `.txt` and `.md` both work identically; the
   validator only ever reads it as plain text.

**Before uploading anything**, run it through the validator:

**Command:**
```
python coach.py check path\to\block.txt
```

This checks syntax, prescription limits, and whether ramps are allowed
for that session type. Two things it does are easy to misread the first
few times, so they're worth knowing up front:

- **It computes the real training load number and writes it into the
  file on disk.** The coach itself never calculates TSS or Duration —
  only the code does, and the only place the real number ever appears is
  inside your file, the moment `check` runs successfully on it. This
  means the coach's own chat message will *always* show
  `[Duration] pending | [Estimated TSS] pending`, every single time,
  even for a block that has already passed — because the coach's copy of
  the text never gets that calculation done to it. Seeing "pending" in
  the chat, or in something you just copied from the chat, is never a
  sign that something is broken.

- **Re-running `check` is always safe — but watch what you paste over
  what.** If you go back to the coach for a correction, the corrected
  block it gives you will *also* say "pending" — as always, per the
  point above. If you paste that fresh copy over a file that had
  *already passed* `check`, you erase the real numbers that were written
  into it, and the file goes back to looking un-validated. That's
  expected, not a bug — it only means you haven't run `check` on the
  corrected version yet. Do that, and it resolves the same way it did
  the first time.

If the check fails for any other reason, take the specific error back
to the coach as a correction, fix it, and re-run the command. Don't
upload a block that hasn't passed.

If the block needs a methodology or discipline different from what its
own header declares:
```
python coach.py check block.txt --methodology daniels --discipline running
```

**Uploading itself is a manual step only without the MCP server.** With
it, ask for `push_block` instead — see §4a for the tool and the
validation gate it now enforces. Without it, paste the passed block's
sessions into Intervals.icu's own Workout Builder, the normal way you'd
enter any workout by hand.

---

## 7. Off-calendar mid-week consult

This is for the case where you need to resolve something for an athlete
mid-week, without waiting for their current training block to finish.

**With the MCP server:** if you're still in that week's existing chat,
just ask your question — no `prep` needed, the coach already has fresh
context. Opening a new chat instead: ask the current chat for the
continuity header, ask the coach to save it with `save_continuity`, then
in the new chat ask for `get_athlete_state`/`get_athlete_profile` and
paste in the continuity content as described in §4a.

**Without the MCP server:**
1. Run `python coach.py prep i123456` so you're working from fresh data.
2. If you're still inside that week's existing chat, just ask your
   question — the coach already has full context, nothing else is
   needed.
3. If you're opening a **new** chat for this one-off question instead:
   before closing the chat you're currently in, ask the coach
   *"give me the continuity header."*
4. The coach delivers a `#SESSION` block noting the real week of the
   block you're on and what was just resolved.
5. Copy that whole block and paste it into
   `out\i123456\continuity.md` (or `out\<athlete_name>\continuity.md`),
   replacing whatever was there before.
6. Next time you open a chat for this athlete, drag in all three files
   as usual — this consult's adjustment is already captured in the notes.

---

## 8. Block close and recalibration (Phase 5)

When the coach delivers the final session of a training block, it
automatically shows you the closing `#SESSION` on its own, visually set
apart with a border, along with an instruction to copy it.

**With the MCP server:** ask the coach to save that block with
`save_continuity`. Open a new chat, ask for `get_athlete_state`/
`get_athlete_profile`, paste in the continuity content (§4a) — no `prep`
needed in between, since `get_athlete_state` fetches fresh numbers
itself.

**Without the MCP server:**
1. Copy that block into `out\<athlete_name>\continuity.md`, replacing
   the previous contents.
2. Before your next conversation with this athlete, run
   `python coach.py prep <id>` to refresh `state.md` with current
   numbers.
3. Open a new chat, drag in all three files.

**Either way:** the coach plans the next block **from `state.md` alone**
— it won't ask how the athlete felt or how compliant they were with the
last block unless you choose to share that; if you do, it's extra
context, never a requirement.

---

## 9. Measuring what a block actually did

**Command:**
```
python coach.py review <id> --since <block start date>
```

**What it does:**
- Compares fitness, fatigue, form, and durability (how much an
  athlete's efficiency drops late in a session) between the date you
  gave and today — this works immediately for any athlete, no waiting
  required, because it's reconstructed from data already pulled by
  `prep`.
- Compares an athlete's power/pace curves (their best efforts across
  different durations) between a saved snapshot near that date and
  today's — see below for why this part needs patience.
- Folds in any race results recorded in
  `out/<athlete_name>/race_notes.md` whose date falls inside the window
  you asked about.
- Writes the result to `out/<athlete_name>/review.md`.

**Why curve progress needs patience.** Intervals.icu only ever reports
an athlete's *current* best effort in a given window — never what it
was on a specific past date. `coach.py prep` now saves a dated snapshot
every time it runs, specifically so this comparison becomes possible
later. Until enough time has passed since snapshot-saving started for a
given athlete, this section of the report will say so honestly instead
of making up a number:
```
No curve history yet for this athlete — snapshot capture started with
the first `coach.py prep` run after this feature shipped.
```
That message is expected, not a bug — it resolves on its own the longer
`prep` keeps running for that athlete.

**Recording a race result.** After a race debrief in Phase 6 (section
10), the coach gives you a `#RACE_RESULT` block. With the MCP server, ask
the coach to save it with `save_race_result` (§4a) — it appends to the
end of `race_notes.md` itself and refuses a conflicting duplicate `Date:`
field. Without it, add the block to the end of
`out/<athlete_name>/race_notes.md` by hand — never delete or overwrite
what's already there. A season can have several races; `review` only
pulls in the ones whose date falls inside the window you asked for with
`--since`.

---

## 10. Macrocycle close / race debrief (Phase 6)

When the macrocycle's final block ends (usually right after the A-race),
the coach enters Phase 6:

1. **If there was a race:** share the result in the chat. The coach
   evaluates it against the athlete's current state and tells you
   whether re-testing their training thresholds is warranted.
2. **If the macrocycle ended without a race** (a goal change, or the
   plan being cut short): the coach summarizes what the athlete adapted
   over that time instead.
3. **To start the next macrocycle:** with the MCP server, just tell the
   coach you're ready — asking for `get_athlete_state` pulls fresh data
   on its own. Without it, run `prep` again first. Either way, confirm to
   the coach that you want to start a new one — it loops back to Phase 1.

---

## 11. Maintenance — keeping machines in sync, running tests

**Any time you edit something in `config/` or `engine/`:**
```
python tests/run_tests.py
```
Runs all 193 tests (unit tests, block validation, and a comparison
against known-correct results for the state-resolving engine). If
anything fails, don't consider the change finished until you understand
why — a failing test doesn't always mean a bug, but it always means the
output changed, and that's worth reading before moving on.

**Any time Claude delivers a corrected file in a chat:**
1. Download it.
2. Copy it to **both** machine paths.
3. Confirm it worked by running the relevant command once on each
   machine.
4. Push the commit to GitHub from whichever machine you tested first.
5. Pull it on the other machine before your next working session there.

This last point is exactly what failed once with an older data pipeline
and cost weeks of a field silently showing blank — worth treating as a
checklist you follow every time, not something to remember from memory.

**Note on the MCP server (§4a):** this checklist is about **code and
config** changes — it's unaffected either way. The MCP server itself only
runs on the machine it's configured on, and writes `out/<athlete>/` files
(continuity, blocks, race notes) to that machine's local repo copy, the
same as the old manual files did. If you work from both machines, those
`out/` files still need the same attention as before if you want them
available on the other one — the MCP server doesn't sync anything
between machines on its own.

**Public vs. private repo:** if you ever make the repo public so Claude
can review it directly, set it back to private as soon as you're done —
GitHub → Settings → Danger Zone → Change visibility.

---

## 12. Common issues

| Symptom | Likely cause | What to do |
|---|---|---|
| `Missing environment variable ICU_API_KEY` | Not set in this terminal/machine | `setx ICU_API_KEY "your_key"`, then open a brand-new terminal |
| `Athlete 'iXXXXXX' not found` | Typo in the id, or you're not the coach for this athlete on Intervals.icu | `python coach.py prep --list` to see the real ids |
| `config/athletes/iXXXXXX.yaml already exists` | This athlete was already onboarded | Edit the existing YAML directly — don't run `new` again |
| Avg Power showing `—` for power-meter activities | Your local copy is out of sync with the repo | Repeat section 11 (sync machines) |
| `PROFILE BUILD FAILED (non-blocking)` | The profile-rendering step failed, but `state.md` was still delivered | Check the printed error; the chat can proceed with `state.md` alone while you fix the underlying issue |
| `note: no continuity.md here yet` | First week for this athlete or this block, or it was never saved | Normal in the first case; in the second, ask the coach for the header again (section 7) |
| `#STATE` older than 7 days | Haven't run `prep` recently — only applies to the manual/CLI path, since `get_athlete_state` (§4a) always fetches fresh | Run `python coach.py prep <id>` before continuing — the coach will refuse to advance on stale numbers |
| `No data for '<id>'` (running `review`) | Never ran `prep` for this athlete | Run `python coach.py prep <id>` first — `review` reads what `prep` already saved, it doesn't fetch new data itself |
| "No curve history yet" (running `review`) | Snapshot capture only just started for this athlete | Not an error — see section 9. Clears up as `prep` keeps running over time |
| `cannot validate — Unknown methodology 'X'` (running `check`) | The `[Methodology]` field in that session doesn't match a real file in `config/authors/` — e.g. plain `friel` instead of `friel_cycling`/`friel_running` | Take it back to the coach as a correction — see section 6 |
| `FAIL [HC-DUAL] ... missing quoted cue` (running `check`) | A line is missing its short quoted coaching phrase — some methodologies (e.g. Koop for trail) require one on *every* line, not only the Main Set | Take it back to the coach as a correction — see section 6 |
| A block that already showed `RESULT: PASS` shows `pending` again after running `check` once more | You pasted a fresh, unprocessed copy of the block (straight from the coach) over a file that had already been validated, erasing the real numbers that were written into it | Not a bug — see section 6. Just run `check` again on the file as it is now |
| `infame-coach` shows "Failed" in Claude Desktop → Settings → Developer | The MCP server didn't start | Click **View logs**, then check §4a's troubleshooting table |
| A tool call through the MCP server hangs for several minutes then times out | Known stdio issue in an older version of the server code | Confirm `git pull` is current and Desktop has been restarted since — see §4a |
| `push_block` refuses, citing `validate_block` as BLOCKED | Working as intended — the tool now enforces this itself | Fix the flagged issue and validate again; see §4a for the deliberate override |
| Errors mentioning a device name or "remote-devices" during an MCP tool call | The conversation was in Cowork or Code mode, not plain Chat | Retry from a plain Chat conversation in the Project |

---

## 13. Quick file and folder reference

```
infame_elite_endurance_coach/
├── coach.py                      single entry point: prep / new / check / review
├── requirements.txt               dependencies — pip install -r requirements.txt
├── engine/
│   ├── fetch_athlete_data.py     pulls Intervals.icu data → athlete_data.json
│   ├── build_state.py            resolves state → state.md / state.json
│   ├── build_profile.py          renders profile.md
│   ├── longitudinal.py           trend/curves module (used by build_state)
│   └── power_profile.py          power-profile module (used by build_state)
├── verify/
│   └── validate_block.py         deterministic gate — called by coach.py check
├── mcp_server/                   MCP server for Claude Desktop — see §4a
│   ├── server.py                 tool registration
│   ├── run_server.py             entry point; logs a crash traceback on fatal exit
│   ├── common.py                 shared plumbing — routes every tool through the
│   │                             same engine functions coach.py uses
│   ├── guard.py                  the @guarded decorator every tool uses
│   ├── cancel_patch.py           self-detecting workaround for python-sdk#2610
│   ├── tools_read.py / tools_write.py / tools_validate.py / tools_push.py
│   └── logs/last_crash.txt       written on a fatal server crash, if one occurs
├── .venv-mcp/                    MCP server's own dependencies — never committed
├── config/
│   ├── athletes/
│   │   ├── _template.yaml        template used by coach.py new
│   │   ├── ATHLETE_INTAKE.md     script for the onboarding conversation
│   │   └── <id>.yaml             one file per athlete — declared, not measured
│   ├── authors/*.yaml            per-methodology zones (Coggan, Daniels, etc.)
│   ├── tss_classes.yaml          training-load multipliers by physiological class
│   └── decision_thresholds.yaml  decision bands — no number lives in code instead
├── generated/                    zone tables — never hand-edited
├── data/<id>/                    the engine's internal layer — don't browse by hand
│   ├── athlete_data.json
│   ├── state.md / state.json
│   ├── profile.md
│   └── history/<date>.json       dated curve snapshots — feeds `review`'s
│                                 progression comparison, written by `prep`
├── out/<athlete_name>/           what you drag into the Claude Project
│   ├── state.md
│   ├── profile.md
│   ├── continuity.md             the only file you write by hand, for #SESSION
│   ├── race_notes.md             #RACE_RESULT blocks, appended by hand
│   └── review.md                 written by `coach.py review`, not hand-edited
├── out/roster.md                 name ↔ id ↔ last-updated table
├── tests/
│   ├── run_tests.py               193 tests — run after any config/engine change
│   ├── test_mcp_server.py         MCP server's own regression suite — run after
│   │                              any mcp_server/ change
│   └── make_fixtures.py
└── Prompt/
    └── infame_elite_endurance_coach.md   the prompt — also lives in the Claude Project
```

---

## Future ideas

None of these are required to run the system as it stands today — they're
possible improvements worth considering once the current workflow has been
proven in real practice across your roster of athletes.

1. **Verify the `eW'`/`ePmax` rule against more athletes.** Left out of
   `profile.md` on purpose because it was only confirmed against one
   case. If the pattern holds across 3–4 more athletes, it can be added
   with confidence.

2. **Automatic flag for stale athlete data.** `roster.md` already shows
   each athlete's last-fetch date — a further step would have
   `coach.py prep --list` highlight any athlete overdue by more than N
   days, instead of requiring you to scan the whole table.

3. **Detect more calendar entries with a missing `type`.** Some generic
   calendar entries (like a travel day or a rest-day note) don't come
   from Intervals.icu with a `type` field populated. Worth checking
   whether other cases deserve the same default treatment.

4. **Configurable threshold for the stale-`continuity.md` warning.**
   Currently hardcoded inside `coach.py`. Could live in
   `decision_thresholds.yaml` alongside the rest of the thresholds,
   instead of a loose number in orchestration code.

5. **A `coach.py prep --stale` mode** that only refreshes athletes with
   data older than N days, instead of `--all` hitting everyone every
   time — useful as the roster grows.

6. **Surface missing/stale `continuity.md` in `roster.md` itself.**
   Right now that information only appears on screen when running `prep`
   for one athlete at a time — centralizing it in the roster would give
   an at-a-glance view across all athletes.

7. **Backlog authors** (Seiler, Pfitzinger, Hansons, Skiba) — content
   work, not infrastructure, but still open and worth returning to once
   the operational workflow is stable. See `IMPROVEMENT_BACKLOG.md` for
   the reasoning behind each.

8. **A dedicated golden test for `build_profile.py`.** The other two
   engine scripts are covered by the regression suite; `build_profile.py`
   was verified by hand but has no fixture of its own in `tests/`. Adding
   one would catch a silent regression the next time it's touched.

9. **A sync-check script between machines.** Something as simple as
   comparing a hash of the `engine/` files on both paths would catch a
   drift between machines before it ever touches a real athlete's data.

10. **`data/<id>/history/` has no retention limit.** `coach.py prep`
    writes one dated snapshot per athlete per day it runs. With a full
    roster run regularly, this is a slow but unbounded accumulation of
    small files. Not a problem yet; worth a cap (e.g. keep one per week
    beyond a year old) before it becomes one.

11. **Scrub `out/`'s brief public-repo exposure from git history.**
    Untracking it (`git rm --cached`) stops future commits from
    carrying it, but any already-pushed commits from a window when the
    repo was public still contain it until a history rewrite
    (`git filter-repo` or BFG) is run. Left as your call — low realistic
    risk given a single-maintainer repo and a short exposure window, but
    not automatically safe to ignore indefinitely.
