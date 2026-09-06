# Operations Manual — Infame Elite Endurance Coach v6.1

Step-by-step guide to the daily workflow after the September 2026 redesign
(extended engine + unified `coach.py` + continuity as a file).

This manual covers **operational use**. For internal architecture, see
`ARCHITECTURE_v6.md`, `WORKFLOW_CHECKLIST.md`, and `IMPROVEMENT_BACKLOG.md`
at the repo root — this document complements those, it does not replace them.

> `WORKFLOW_CHECKLIST.md` specifically covers system setup, maintenance
> (editing `config/`/`engine/`, regression tests), and adding a coaching
> methodology. This document covers the day-to-day athlete workflow.

---

## 0. Before you start — requirements on each machine

This must be in place on **both** machines (laptop and desktop) before
running anything in this manual:

1. `ICU_API_KEY` set as an environment variable
2. Python installed, with `pip install -r requirements.txt` run (or at least
   `requests`, `pyyaml`, `openpyxl`)
3. The repo up to date — same commit on both machines. If you just received
   a corrected file from a Claude chat, it has to reach **both** paths
   before you continue:
   ```
   C:\Dev\Github\infame_elite _endurance_coach\
   E:\Dev\github\infame_elite_endurance_coach\
   ```
   (the space in the laptop's folder name is real, not a typo)

**Golden rule:** a fix you got from a Claude chat is not "installed" until
it exists on both machines and is committed to GitHub. A corrected file
that only lives in the chat download does not count.

---

## 1. Onboard a new athlete

**Command:**
```
python coach.py new i123456
```

**What it does:**
- Confirms the id is real on your Intervals.icu account (catches typos
  before creating anything)
- If the athlete already has a profile (`config/athletes/i123456.yaml`
  already exists), it stops without touching anything — it never
  overwrites a real profile
- Otherwise, copies the template and creates `config/athletes/i123456.yaml`

**What you do next:**
1. Open a new chat in the Claude Project
2. Run the intake conversation using `config/athletes/ATHLETE_INTAKE.md` as
   the script — the coach conducts it in the athlete's language
3. The coach delivers a completed profile at the end of intake — copy it
   into `config/athletes/i123456.yaml`, replacing the template
4. Save the file. The athlete is now ready for their first `prep`

There is no need to run `prep` as part of onboarding — intake does not
depend on any Intervals.icu data, only on what the athlete declares.

---

## 2. Prepare one athlete for a session (daily use)

**Command:**
```
python coach.py prep i123456
```

**What it does, in order:**
1. Pulls fresh data from Intervals.icu (`fetch_athlete_data.py`)
2. Resolves their training state (`build_state.py`) → `state.md`
3. Renders their raw context (`build_profile.py`) → `profile.md`
4. Copies both into `out/<athlete_name>/`
5. Reports whether `continuity.md` exists in that folder, and how old it is
6. Refreshes `out/roster.md` with this fetch's date

**Expected console output:**
```
Ready — drag out/elias_caballero/ (state.md, profile.md) into the Claude Project
continuity.md last updated 3 day(s) ago
```

Seeing `note: no continuity.md here yet` is normal for an athlete's first
week or a new block — it is not an error.

---

## 3. Prepare every athlete at once

**Command:**
```
python coach.py prep --all
```

Runs step 2 for every athlete with data on the account. At the end:
```
Done. 21/23 athletes ready in out/
```

If any athlete fails (for example, an inactive account), the summary tells
you how many of how many succeeded — check the per-athlete detail printed
above it for the specific failure.

**To see who's who without fetching anything:**
```
python coach.py prep --list
```
Lists every athlete (id + name) and regenerates `out/roster.md` with each
one's real last-fetch date — useful for spotting who's overdue for a
refresh without running a full prep.

---

## 4. What to drag into the Claude Project, and when

When opening a new chat for an athlete, drag the whole `out/<athlete_name>/`
folder, or the individual files inside it:

| File | Always present? | What it is |
|---|---|---|
| `state.md` | Yes | Authoritative state — CTL/ATL/TSB, ACWR, longitudinal, testing |
| `profile.md` | Yes | Raw context — profile, sport config, calendar, activity history |
| `continuity.md` | Only once a session has already happened this block | The `#SESSION` header — where the macrocycle stands |

**You don't need to re-drag anything mid-conversation** — once a chat has
the files, the coach keeps them in context for the rest of that session.
Only re-drag when opening a **new** chat.

---

## 5. Generate a plan or follow up (inside the chat)

Once the files are dragged in, just talk to the coach in plain language.
The system is a 6-phase state machine (Phase 0 through Phase 6) that drives
itself:

- **Athlete with no prior `#SESSION`** → starts at Phase 1 (verification and
  intake if needed), builds the macrocycle, and reaches Phase 4 (block
  generation)
- **Athlete with a `continuity.md`** → the coach reads the `#SESSION`,
  reconstructs where things stood, and resumes directly from there

At every phase the coach stops and waits for your explicit confirmation
before advancing (for example, before generating Intervals.icu code in
Phase 4). That's intentional — review what it proposes before approving.

---

## 6. Validate and upload a block to Intervals.icu

When the coach delivers a code block (Intervals.icu syntax), before
uploading it:

**Command:**
```
python coach.py check path\to\block.txt
```

This runs the deterministic validator: checks syntax, prescription floors,
ramp eligibility, and **computes the real TSS** (filling in whatever the
coach left as `pending`). If it fails, fix it and re-run the command — don't
upload a block that hasn't passed.

If the block needs a methodology or discipline different from what its
header declares:
```
python coach.py check block.txt --methodology daniels --discipline running
```

---

## 7. Off-calendar mid-week consult

This is the case that drove much of this redesign: you need to resolve
something for an athlete without waiting for the block to finish.

**Steps:**
1. Run `python coach.py prep i123456` to have fresh data
2. Open that week's **existing** chat if you're still in it — the coach
   already has full context, nothing else is needed
3. If you're opening a **new** chat for this one-off question: before
   closing it, ask the coach *"give me the continuity header"*
4. The coach delivers a `#SESSION` with `Active Phase: 4` (not a
   transition value), the real week of the block you're on, and a note of
   what was just resolved
5. Copy that whole block and paste it into `out\i123456\continuity.md` (or
   `out\<athlete_name>\continuity.md`), replacing the previous one
6. Next time you open a chat for this athlete, drag all three files — this
   consult's adjustment is already captured in the notes

---

## 8. Block close and recalibration (Phase 5)

When the coach delivers the final session of a block, it automatically
emits the closing `#SESSION`, with a visual border and instructions to
copy it.

**Steps:**
1. Copy that block into `out\<athlete_name>\continuity.md`
2. Before the next conversation with this athlete, run
   `python coach.py prep <id>` to refresh `state.md`
3. Open a new chat, drag all three files
4. The coach recalibrates the next block **from `#STATE` alone** — it will
   not ask how the athlete felt or their compliance; if you want to share
   that, it's additional context, never a requirement

---

## 9. Measuring what a block actually did

**Command:**
```
python coach.py review <id> --since <block start date>
```

**What it does:**
- Compares CTL/ATL/TSB, ACWR, and durability (median decoupling) between
  the given date and today — all reconstructable from the 180-day pull
  `coach.py prep` already fetches, so this works immediately, for any
  athlete, no waiting required
- Compares power/pace curve anchors between a dated snapshot near that date
  and today's curves — see below for why this one takes time to become useful
- Folds in any `#RACE_RESULT` entries from `out/<athlete_name>/race_notes.md`
  whose date falls inside the window
- Writes `out/<athlete_name>/review.md`

**Why curve progression needs patience.** Intervals.icu's curve endpoint
only ever returns the best value in a window as of *today* — never a
historical one. `coach.py prep` now saves a dated snapshot
(`data/<id>/history/<date>.json`) every time it runs, specifically so this
comparison becomes possible later. Until enough time has passed since
snapshot capture started, this section will honestly say so instead of
faking a number:
```
No curve history yet for this athlete — snapshot capture started with
the first `coach.py prep` run after this feature shipped.
```
That's expected, not a bug — it clears up on its own as `prep` keeps running.

**Recording a race result.** After a race debrief in Phase 6, the coach
emits a `#RACE_RESULT` block (see the prompt's Phase 6). Append it — never
overwrite — to `out/<athlete_name>/race_notes.md`. A season can have
several races; `review` only pulls in the ones whose date falls inside the
`--since` window you asked for.

---

## 10. Macrocycle close / race debrief (Phase 6)

When the macrocycle's final block ends (usually after the A-race), the
coach enters Phase 6:

1. If there was a race: share the result in the chat — the coach evaluates
   it against `#STATE` and tells you whether re-testing thresholds is
   warranted
2. If the macrocycle ended without a race (goal change, plan cut short): the
   coach summarizes the adaptation achieved
3. To start the next macrocycle: run `prep` again and confirm you want to
   start a new one — the coach loops back to Phase 1

---

## 11. Maintenance — keeping machines in sync, running tests

**Any time you edit something in `config/` or `engine/`:**
```
python tests/run_tests.py
```
Runs all 67 tests (unit, block validation, state-engine golden comparison).
If anything fails, don't ship the change until you understand why.

**Any time Claude delivers a corrected file in a chat:**
1. Download it
2. Copy it to **both** machine paths
3. Confirm it by running the relevant command once on each machine
4. Push the commit to GitHub from whichever machine you tested first
5. Pull it on the other machine before your next working session there

This last point is exactly what failed with `intervals_export.py` and cost
weeks of empty Avg Power — worth treating as a checklist, not memory.

**Public vs. private repo:** if you ever make it public so Claude can review
it directly (as we did for this session's cross-reference), set it back to
private as soon as you're done. GitHub → Settings → Danger Zone → Change
visibility.

---

## 12. Common issues

| Symptom | Likely cause | What to do |
|---|---|---|
| `Missing environment variable ICU_API_KEY` | Not set in this terminal/machine | `setx ICU_API_KEY "your_key"`, open a new terminal |
| `Athlete 'iXXXXXX' not found` | Typo in the id, or not a coach for this athlete | `python coach.py prep --list` to see real ids |
| `config/athletes/iXXXXXX.yaml already exists` | This athlete was already onboarded | Edit the existing YAML directly, don't use `new` again |
| Avg Power showing `—` for power-meter activities | Local copy out of sync with the repo | Repeat step 11 (sync machines) |
| `PROFILE BUILD FAILED (non-blocking)` | `build_profile.py` failed, but `state.md` was still delivered | Check the printed error; the chat can proceed with `state.md` alone while you fix it |
| `note: no continuity.md here yet` | First week for this athlete/block, or it was never saved | Normal in the first case; in the second, request the header from the coach (step 7) |
| `#STATE` older than 7 days | Haven't run `prep` recently | `python coach.py prep <id>` before continuing — the coach will refuse to advance on stale state |
| `No data for '<id>'` (on `review`) | Never ran `prep` for this athlete | `python coach.py prep <id>` first — `review` reads `data/<id>/athlete_data.json`, it doesn't fetch |
| "No curve history yet" (on `review`) | Snapshot capture only just started | Not an error — see section 9. Clears up as `prep` keeps running over time |

---

## 13. Quick file and folder reference

```
infame_elite_endurance_coach/
├── coach.py                      single entry point: prep / new / check
├── engine/
│   ├── fetch_athlete_data.py     pulls Intervals.icu data → athlete_data.json
│   ├── build_state.py            resolves #STATE → state.md / state.json
│   ├── build_profile.py          renders profile.md
│   ├── longitudinal.py           trend/curves module (used by build_state)
│   └── power_profile.py          power-profile module (used by build_state)
├── verify/
│   └── validate_block.py         deterministic gate — called by coach.py check
├── config/
│   ├── athletes/
│   │   ├── _template.yaml        template used by coach.py new
│   │   ├── ATHLETE_INTAKE.md     script for the onboarding conversation
│   │   └── <id>.yaml             one file per athlete — declared, not measured
│   ├── authors/*.yaml            per-methodology zones (Coggan, Daniels, etc.)
│   ├── tss_classes.yaml          TSS multipliers by physiological class
│   └── decision_thresholds.yaml  decision bands — no number lives in code
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
│   ├── continuity.md             the only file you write by hand for #SESSION
│   ├── race_notes.md             #RACE_RESULT blocks, appended by hand
│   └── review.md                 written by `coach.py review`, not hand-edited
├── out/roster.md                 name ↔ id ↔ last-updated table
├── tests/
│   ├── run_tests.py               76 tests — run after any config/engine change
│   └── make_fixtures.py
└── Prompt/
    └── infame_elite_endurance_coach.md   the prompt — also lives in the Claude Project
```

---

## Future ideas

None of these are required to run the system as delivered — they're
possible improvements worth considering once the current workflow has been
proven in real practice across your 16–23 athletes.

1. **Verify the `eW'`/`ePmax` rule against more athletes.** Left out of
   `profile.md` on purpose because it was only confirmed against one case
   (Elias). If the pattern (`FFT_CURVES` model, 90d window) holds across
   3–4 more athletes, it can be added with confidence.

2. **Automatic flag for stale athlete data.** `roster.md` already shows
   each athlete's last-fetch date — a further step would have
   `coach.py prep --list` highlight any athlete overdue by more than N days,
   instead of requiring you to scan the whole table.

3. **Detect more calendar entries with a missing `type`.** The "🚗 Trip 🚗" /
   "REST" case showing `Type: —` revealed that Intervals.icu doesn't always
   populate that field for generic calendar entries. Worth checking whether
   other cases (e.g. athlete notes) deserve the same default treatment.

4. **Configurable threshold for the stale-`continuity.md` warning.**
   Currently hardcoded at 10 days inside `coach.py`. Could live in
   `decision_thresholds.yaml` alongside the rest of the thresholds, instead
   of a loose number in orchestration code.

5. **A `coach.py prep --stale` mode** that only refreshes athletes with data
   older than N days, instead of `--all` hitting all 23 every time — useful
   as the roster grows.

6. **Surface missing/stale `continuity.md` in `roster.md` itself.** Right
   now that information only appears on screen when running `prep` for one
   athlete at a time — centralizing it in the roster would give an
   at-a-glance view across all athletes.

7. **Backlog authors** (Seiler, Pfitzinger, Hansons, Skiba) — content work,
   not infrastructure, but still open and worth returning to once the
   operational workflow is stable.

8. **A dedicated golden test for `build_profile.py`.** The other two engine
   scripts (`fetch_athlete_data.py`, `build_state.py`) are covered by the
   76-test suite; `build_profile.py` was verified by hand this session but
   has no fixture of its own in `tests/`. Adding one would catch a silent
   regression the next time it's touched.

9. **A sync-check script between machines.** Something as simple as
   comparing a hash of the `engine/` files on both paths would have caught
   the `intervals_export.py` drift before it ever touched a real athlete's
   data.

10. ~~Consider retiring `intervals_export.py` and `convert.py`~~ — **done**:
    moved to `legacy/` when the repo was cleaned up (see `RESTORE_POINT_v6.4.md`).

11. **`data/<id>/history/` has no retention limit.** `coach.py prep` writes
    one dated snapshot per athlete per day it runs. With 16–23 athletes run
    regularly, this is a slow but unbounded accumulation of small files.
    Not a problem yet; worth a cap (e.g. keep one per week beyond a year
    old) before it becomes one.

12. **Scrub `out/`'s brief public-repo exposure from git history.**
    `git rm --cached` (done) stops future commits from carrying it, but the
    already-pushed commits from the window the repo was public still
    contain it until a history rewrite (`git filter-repo` or BFG) is run.
    Left as your call — low realistic risk given the short window and
    single-maintainer repo, but not automatically safe.
