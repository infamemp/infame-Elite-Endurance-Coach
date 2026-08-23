# Workflow Checklist — Infame Elite Endurance Coach v6.2

How to actually use the system, start to finish. Written to be followed without
remembering anything.

Every command is run from the repository root:
```
cd "C:\Dev\Github\infame_elite _endurance_coach"
```

---

## A — One-time setup, per machine

Done once. Skip if the machine is already working.

**A1.** Confirm Python and the dependencies:
```
pip install pyyaml jsonschema requests openpyxl
```

**A2.** Set the Intervals.icu API key as an environment variable:
```
setx ICU_API_KEY "your_key_here"
```
Then close the terminal and open a new one — `setx` only affects new sessions.

**A3.** Smoke test:
```
python build_zone_tables.py validate
python tests\run_tests.py
```
Expect `8/8 author files valid` and `67/67 passed`.

---

## B — One-time setup, per athlete

Done once per athlete, then only when something structural changes.

**B1.** Have the athlete complete `config/athletes/ATHLETE_INTAKE.md`. It takes
about ten minutes. A complete beginner skips sections 6 and 7 entirely.

For a new athlete with no history, conduct the intake as a conversation in the
Claude Project using that file as the script — it will produce a filled profile.

**B2.** Copy the template and fill it from their answers:
```
copy config\athletes\_template.yaml config\athletes\<athlete_id>.yaml
```
The `<athlete_id>` must match their Intervals.icu id exactly, e.g. `i347129`.
Find it with:
```
python engine\fetch_athlete_data.py --list
```

**B3.** Fill in the YAML. Only what the athlete declares — never copy FTP, zones,
PMC or history into it. Those come from Intervals.icu automatically.

**B4.** Confirm the profile parses:
```
python -c "import yaml;yaml.safe_load(open('config/athletes/<athlete_id>.yaml'));print('ok')"
```

> Real athlete profiles are gitignored. They live on the machine, not in the
> repository. Back them up separately.

---

## C — Planning a training block

The main workflow. Repeat per athlete, per block.

### Step 1 — Pull fresh data

```
python engine\fetch_athlete_data.py --athlete <athlete_id>
```

Writes `data/<athlete_id>/athlete_data.json`. Pulls 180 days of wellness, PMC,
activities, planned events, and power/pace curves.

### Step 2 — Resolve the state

```
python engine\build_state.py --athlete <athlete_id>
```

Writes `data/<athlete_id>/state.md` and `state.json`, and prints the state block.

**Read it before going further.** Check that the resolved state matches your own
judgement of the athlete. If it does not, that is worth understanding before you
prescribe anything on top of it.

Pay particular attention to:
- **Flags** — durability, ACWR, HRV divergence
- **Suggested testing** — which anchors need refreshing, and with what protocol
- **Data quality** — underestimated W', missing signals, non-endurance sessions

### Step 3 — Open the Claude Project

Start a new conversation and paste, in this order:

1. The full contents of `data/<athlete_id>/state.md`
2. The `#SESSION` block from the end of the previous block, if this is a
   continuation

For a brand new macrocycle there is no `#SESSION` — the profile and the state are
enough.

> If you paste `#SESSION` without `#STATE`, the coach will stop and ask for it.
> That is correct behaviour, not a fault.

### Step 4 — Work through the phases

The coach runs a gated state machine. It will not skip ahead, and it will stop and
wait at each gate for your confirmation.

- **Phase 1** — Metric Map: which metric governs each discipline
- **Phase 2** — Macrocycle design
- **Phase 3** — Block proposal — **you approve before any code is generated**
- **Phase 4** — Session generation, in Intervals.icu syntax
- **Phase 5** — Recalibration between blocks
- **Phase 6** — Macrocycle close and race debrief

The `[Estimated TSS]` field will read `pending`. That is intended — the engine
fills it in step 6.

### Step 5 — Save the generated block

Copy the delivered sessions into a `.md` file. Keep the session headers: the
validator reads `[Methodology]`, `[Discipline]` and `[Athlete ID]` from them.

### Step 6 — Verify before uploading

```
python verify\validate_block.py <file> --fill-tss
```

- **PASS** — the block is upload-safe and the TSS has been written into each header
- **BLOCKED** — do not upload. Take the reported failures back to the coach as a
  correction task and re-verify.

The gate checks syntax, ramp eligibility, metric formats, prescription floors,
dual-layer completeness, the author's special output rule, and recomputes TSS
against the zone tables.

### Step 7 — Upload to Intervals.icu

Only a block that passed step 6.

### Step 8 — Save the continuation state

At the end of the block, the coach emits a `#SESSION` header. Save it — it is what
resumes the macrocycle next time. It deliberately carries no numbers; those come
from a fresh `#STATE`.

---

## D — Between blocks

**D1.** Repeat steps 1 and 2 for fresh data and a fresh state.

**D2.** Return to the Project with the new `state.md` and the saved `#SESSION`.
The coach resumes at Phase 5 and recalibrates.

**D3.** It will ask for what the engine cannot know: compliance, how the sessions
felt, any niggles. That qualitative half is yours.

---

## E — Changing the system

Any edit to `config/` or `engine/`.

**E1.** Make the change.

**E2.** If it touched zone data:
```
python build_zone_tables.py validate
python build_zone_tables.py build
```

**E3.** Run the regression suite:
```
python tests\run_tests.py
```

**E4.** If a golden test fails, **read the diff**. It tells you exactly what
output moved.
- Unintended → you introduced a bug. Fix it.
- Intended → accept the new baseline:
  ```
  python tests\run_tests.py --update
  ```
  and commit the updated goldens together with the change that caused them.

**E5.** If the zone tables were rebuilt, re-upload both files from `generated/` to
the Claude Project. The generated files carry a build date — if the Project's
copies are older than your last config change, they are stale.

**E6.** Commit and push.

---

## F — Adding a coaching methodology

**F1.** Copy the template:
```
copy config\authors\_template.yaml config\authors\<author_id>.yaml
```

**F2.** Fill it in: zones, metric metadata, physiological class per zone, and any
special output rule. The file is commented field by field.

**F3.** Validate:
```
python build_zone_tables.py validate
```
Expect the new author to appear as OK. The cutpoint agreement report will list any
zone where the author disagrees with the fallback cutpoints — that is information,
not an error.

**F4.** Build and test:
```
python build_zone_tables.py build
python tests\run_tests.py
```

**F5.** Upload the regenerated tables from `generated/` to the Claude Project.

No prompt edit. No code edit.

---

## G — When something goes wrong

**The coach invented a number.** It should not. Check that `state.md` was actually
pasted and that its `Resolved:` date is recent. Without a `#STATE`, the coach is
supposed to stop rather than estimate.

**The validator rejects a block you believe is correct.** Read the specific error
code. If the rule itself is wrong, it lives in `config/decision_thresholds.yaml` —
change it there, then run the test suite to see what else moves.

**The state does not match your judgement of the athlete.** Look at the signal
table: each figure names its source. The most common causes are stale data, a
misconfigured W' or FTP in Intervals.icu, or a genuine disagreement worth taking
seriously.

**Tests fail after a change you did not make.** Someone edited config on the other
machine. Pull, run the suite, read the diff.

**The suite fails on one machine and passes on another.** Something depends on a
gitignored file. Tests must only rely on what is committed.

---

## H — Quick reference

| Task | Command |
|:---|:---|
| List athletes | `python engine\fetch_athlete_data.py --list` |
| Pull data | `python engine\fetch_athlete_data.py --athlete <id>` |
| Resolve state | `python engine\build_state.py --athlete <id>` |
| Resolve all athletes | `python engine\build_state.py --all` |
| Verify a block | `python verify\validate_block.py <file> --fill-tss` |
| Check config | `python build_zone_tables.py validate` |
| Rebuild tables | `python build_zone_tables.py build` |
| Run tests | `python tests\run_tests.py` |
| Accept new baselines | `python tests\run_tests.py --update` |
| Excel report, all athletes | `python "Athlete Template\intervals_export.py"` |
