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
| `python coach.py prep <id>` | Pull fresh data for one athlete and build the files you'll use in the chat |
| `python coach.py prep --all` | Same, for every athlete on the account |
| `python coach.py prep --list` | List every athlete and when each was last updated — downloads nothing new |
| `python coach.py check <file>` | Check a generated training block for errors before uploading it |
| `python coach.py review <id> --since <date>` | Compare an athlete's numbers today against a past date |

`<id>` is the athlete's Intervals.icu ID — it looks like `i123456`. Find it
with `python coach.py prep --list` if you don't have it memorized.

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

Full detail in Manual §1.

---

## Every time you open a new chat with an athlete

From the folder `out/<athlete_name>/`, drag these files into the Claude
Project chat window:

- [ ] `state.md` — always
- [ ] `profile.md` — always
- [ ] `continuity.md` — only if it exists (means a session already
      happened during this training block)

Do this once per chat — not again partway through the same conversation.

---

## Mid-week question, staying in the same chat

1. Run `python coach.py prep <id>` first, so the coach is working from
   fresh numbers.
2. Ask your question. Nothing else to do.

## Mid-week question, opening a brand-new chat instead

1. `python coach.py prep <id>`
2. Before closing the chat you're in now, ask the coach:
   *"give me the continuity header"*
3. Copy what it gives you into `out/<athlete_name>/continuity.md`,
   replacing whatever was already there.
4. Open the new chat and drag in the files as usual.

---

## End of a training block

1. The coach shows you a boxed `#SESSION` block on its own once the block
   ends — you don't have to ask for it.
2. Copy it into `out/<athlete_name>/continuity.md`, replacing the old one.
3. Run `python coach.py prep <id>` before your next chat with that
   athlete.
4. Optional: `python coach.py review <id> --since <block start date>` to
   see what actually changed.

## After a race

1. During the debrief, the coach gives you a `#RACE_RESULT` block.
2. Add it to the **end** of `out/<athlete_name>/race_notes.md` — never
   delete what's already there.
3. `review` picks it up automatically the next time you use it.

---

## Validating a block before upload

1. From the coach's message, copy only the training block — from the
   first `[Week]` line through the `[Nutrition]:` line of the last
   session. **Never** copy the one-line instruction to run the
   validator, or the `───`-bordered `#SESSION ... #END` header that
   follows — that header goes in `continuity.md` instead (see above),
   not in the block file.
2. Paste it into Notepad, save it anywhere under
   `out/<athlete_name>/blocks/` (`.txt` or `.md`, doesn't matter).
3. `python coach.py check path\to\file`
4. Seeing `pending` in the coach's chat message is always normal — the
   coach never fills that in, only `check` does, directly in your file.
   If a block that already passed shows `pending` again, you likely
   pasted a fresh, unprocessed copy over it — just run `check` again.
5. Don't upload anything until the result says `PASS`. Full detail in
   Manual §6.

---

## Golden rules

- A fix isn't real until it exists on **both** machines and is pushed to
  GitHub — see Manual §0.
- Run `python tests/run_tests.py` any time you edit anything inside
  `config/` or `engine/`.
- If the coach says `#STATE` is more than 7 days old, run `prep` again
  before continuing — it will refuse to guess with stale data.
- Never type inside `continuity.md` by hand. The only thing that ever
  goes in there is a fresh `#SESSION` block, pasted in whole.
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

---

Need more than this? Everything above is explained step by step, with the
reasoning behind it, in `manual/OPERATIONS_MANUAL.md`.
