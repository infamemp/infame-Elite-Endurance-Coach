# Improvement Backlog — Infame Elite Endurance Coach

**Written:** 2026-08-22 · **Revised:** 2026-09-06
**Status:** Nothing here is committed work. It is a considered list of where the
system could go, with honest reasoning about what each item costs and what it is
worth.

Read it when deciding what to build next, not as a plan to execute in order. The
most valuable item on this list is usually the one that real use has just proven
necessary — and that item is not written down yet.

---

## 1. Loose ends from v6.2

Small, known, and cheap. Worth clearing before starting anything larger.

**Create real athlete profiles.** `config/athletes/` holds only a template and a
test fixture. Until a real profile exists for an athlete, several rules that were
built for them do nothing: treadmill ramp permission, trail metric override, cue
language. Start with two or three athletes rather than all seventeen — the first
few will reveal whether the template asks the right questions.

**Translate the `.gitignore` comments to English.** Trivial, and the project
convention is English throughout.

**Give Friel running its own knowledge base.** It currently shares the cycling
Training Bible. The zones are correctly migrated, but the methodology text Claude
reads is about cycling. The Triathlete's Training Bible or Friel's running
material would close the last KB gap.

**Bosquet — resolved, no further action needed.** His 2007 meta-analysis already
drove the taper parameters in `decision_thresholds.yaml` (14-day duration, 41-60%
volume reduction, intensity maintained, frequency >=80%, progressive pattern), and
`Knowledge/Mujika_Tapering_Peaking_Extraction.md` already covers the reasoning —
Mujika co-authored the meta-analysis. A separate Bosquet KB would duplicate it.

**Ingham — open, contingent on interest rather than a gap.** Discussed once, never
sourced. His book (*How to Support a Champion*) is not a zone system or a taper
method — it is about the practice of supporting elite athletes. It would enter as
a general knowledge base if the coach wants it, not as a prescriptive author.

**Revisit the target TSB ranges by event type.** They are currently the coach's
working numbers, flagged as heuristic in config. After a season of real races,
they can be replaced with observed values — which is a stronger basis than any
literature would give, because they would be the coach's own athletes.

**Add a data-quality flag for missing signals.** The engine reports problems with
data it has, but says nothing about data it lacks. An athlete with no HRV loses
the secondary recovery signal; one with no configured W' cannot be assessed for
anaerobic depth. Both are worth telling the coach. *Update, September:* worth
auditing which wellness fields (HRV, sleep, respiration, subjective fatigue) are
actually populated across the real roster before assuming they're absent —
Intervals.icu's wellness endpoint supports more fields than the fetcher
currently reads, and "not available" in `#STATE` today conflates "the athlete's
device doesn't track it" with "the field exists and we never asked for it."

**Cap `data/<id>/history/` retention.** New as of the results module
(September): `coach.py prep` now writes one dated curve snapshot per athlete
per run, with no expiry. Not a problem yet at seventeen athletes; worth a cap
(e.g. keep one per week beyond a year old) before it becomes one.

**Scrub `out/`'s brief public-repo exposure from git history.** The repo was
made public for review in early September and `out/` — which holds real
athlete names, ages, weights, and training history — was briefly committed
before being caught and untracked. `git rm --cached` stops it going forward;
the already-pushed commits from that window still contain it until a history
rewrite (`git filter-repo` or BFG) is run. Low realistic risk given the short
window and that this is a single-maintainer repo, but not automatically safe.

**`User-Agent` header — resolved, no further action needed.** The official API
guide warns Cloudflare (which fronts Intervals.icu) can silently challenge or
block requests from bare-Python clients. Added to `fetch_athlete_data.py`'s
session headers in September. Worth checking any future script that calls the
API directly does the same.

**Golden-test date drift — resolved, worth remembering why.** The regression
suite's synthetic fixtures are dated relative to whenever `make_fixtures.py`
was last run, specifically so they never age out of a rolling window — but
that guarantee only held if the fixture was regenerated before each
comparison, and `run_tests.py` never did that. A fixture generated once and
left on disk silently drifted out of its own 7/28-day ACWR windows as real
time passed, failing all seven cases identically for a reason unrelated to any
code change. `run_tests.py` now regenerates every fixture immediately before
comparing. The lesson generalizes: any test harness that reads "now" is
exposed to the same class of bug the fixtures were built to avoid against
athlete data — worth a second look if `longitudinal.py`'s rolling-window
tests are ever extended.

---

## 2. Integration with the cycling workout engine

The `cycling-workout-engine-gemini` repository solves the same problem from the
automated side, and was reviewed in full during v6 development.

**The agreed direction: share Layer 1, do not merge repositories.** The engine
would read `config/authors/` instead of its hardcoded single-author `zones.py`,
and use `verify/validate_block.py` as its output gate. That leaves one knowledge
base with two front ends — Infame conversational for real coaching, the engine
automated for batch generation. Adding an author benefits both.

**The blocker, which must be settled first.** The two compute TSS incompatibly.
The workout engine uses `IF² × 100` with normalized power; Infame uses minutes ×
physiological class multiplier, and `tss_classes.yaml` explicitly forbids the IF
formula.

The likely resolution is that both are right in their own domain. IF² is the
actual TrainingPeaks formula and is what Intervals.icu itself computes on upload —
but it requires normalized power, which only exists with a power meter. Class
multipliers are the only workable approach for heart-rate and pace sessions, where
no NP exists. So: **power sessions use IF², everything else uses class
multipliers.** That would make Infame's TSS measurably more accurate for power
work, and it is a finding that only emerged from comparing the two projects.

**What Infame should take from the engine, regardless of integration:**

`resolve_intensity.py` solves work-segment intensity in closed form to hit a TSS
target, and reports infeasibility with concrete numbers when the answer falls
outside the zone. Infame currently designs a session and computes TSS afterward;
this would let it design *toward* a target. That is a capability gap, not a
duplicate.

Its budget-ceiling, zone-containment, and post-build IF verification checks are
three validations the Infame gate does not have.

`catalog.py` — a SQLite library of generated sessions, designed explicitly as
memory for the reasoning layer rather than as a mechanical anti-repetition filter.
Infame has no equivalent. It would let the coach reason about variety and
progression across a block instead of designing each session cold.

---

## 3. Adding coaches and methodologies

The extension mechanism works: copy `config/authors/_template.yaml`, fill it,
validate, build. No prompt or code changes. What follows is about *which* authors
would add something Infame does not already have.

### The eight already present

Cycling: Coggan, Friel, Carmichael. Running: Daniels, Palladino, Friel, Koop,
Olbrich.

### Genuine gaps

**Seiler — polarized training.** The most significant methodological absence.
Every current author prescribes by zone; none carries an explicit intensity
*distribution* model. Polarized training is a claim about how a training week
should be shaped — roughly 80% low intensity, 20% high, with the middle
deliberately avoided. That is not a zone table, so it does not fit the author
schema cleanly. It would need a new kind of config: a distribution target the
engine could verify a block against. This is the most interesting extension on the
list, and the one that would most change what the system can say.

**Pfitzinger — marathon-specific.** Lactate-threshold-driven marathon plans with a
distinctive treatment of the long run and of medium-long runs during the week.
Fits the schema without difficulty. Worth it if marathon athletes are a meaningful
share of the roster.

**Hansons — cumulative fatigue.** A deliberately different philosophy: shorter
long runs performed on accumulated fatigue rather than fresh. Its value is not the
zones — it is that the plan structure contradicts the conventional long-run
approach, so having it available gives the coach a genuine alternative to offer
rather than a variation.

**Skiba — W' balance.** Complements Palladino rather than competing with him.
Where Palladino gives CP and RWC as static estimates, Skiba models W' depletion
and reconstitution *within* a session. Infame already fetches W' balance data and
uses it for repeatability. A Skiba model would let it prescribe interval recovery
durations from W' reconstitution rather than from convention.

**Uphill and vertical-specific work for trail.** Koop covers ultrarunning, but
vertical gain as a training variable in its own right is not represented. For a
coach in Mexico with mountain terrain available, this is more relevant than most
of the list.

**Strength and conditioning.** Entirely absent, and deliberately outside the
current architecture: the zone schema has no vocabulary for load, sets, or reps.
Adding it would require a parallel config type rather than a new author. Worth
considering only if the coaching practice actually prescribes it.

### Check the anchor before adding any author

A mechanism added in August 2026, after Carmichael revealed the gap. Most authors
express their percentages against functional threshold; some do not, and reading
their table as if they did prescribes every session at the wrong intensity.

Carmichael anchors on the CTS Field Test — two 8-minute maximal efforts — which
his book places about 10% above threshold power. Read as % FTP, his PowerInterval
lands at threshold instead of VO2max, which is the one place the method cannot
afford to be wrong.

The `anchor` block in the author schema declares the metric, the conversion
factor and its source. The YAML keeps the author's own numbers; the generator
emits an additional threshold-equivalent column; the validator converts before
matching. **When adding an author, the first question is what their 100% actually
is.** If it is not threshold, declare the anchor.

Two more that already anchor differently and are handled by other means: Olbrich
on HRmax, via a special output rule; Koop on RPE, via dual-layer.

### Two cautions on adding authors

**More authors is not automatically better.** Each one adds a way to be
inconsistent across athletes. The value is in having the right author for a given
athlete, not in coverage for its own sake.

**Watch the cutpoint agreement number.** It sits at 66/78 today. Every new author
adds zones that may disagree with the fallback cutpoints, and the `validate`
command reports each one. A steadily falling agreement rate is a signal that the
cutpoints need revisiting — not that the authors are wrong.

---

## 4. Engine improvements

**Prescribe toward a TSS target.** See `resolve_intensity.py` above. The single
most useful capability the engine currently lacks.

**Model W' reconstitution for interval design.** Infame knows how deeply an
athlete depletes W'; it does not model how fast they recover it. That is what
determines whether a set of intervals is repeatable. Skiba's model plus the W'
data already being fetched would close this.

**Extend the PMC projection to compare scenarios.** Today it projects one future
from the planned calendar. Projecting two or three candidate blocks side by side
would turn it from a report into a planning tool.

**Track running effectiveness over time.** Palladino's RE metric is a
power-to-pace efficiency measure that improves with technique and fitness. Infame
fetches the data to compute it but does not.

**Detect the fitness/fatigue signature of illness.** A sharp HRV drop with an
elevated resting heart rate and a normal TSB is a distinctive pattern. The engine
has all three signals and does not look for the combination.

**Handle altitude and heat as first-class variables.** Palladino is explicit that a
CP from sea level is not valid at altitude, and one from 18°C is not valid at 27°C.
The engine records neither. For a coach in Mexico with athletes at varying
elevations, this is not academic.

**Pull interval-level data for structured sessions.** Intervals.icu's
`GET /activity/{id}?intervals=true` returns per-interval decoupling, estimated
CP, zone actually worked, and training load — not just the session aggregate
Infame reads today. This is the missing piece for two items already on this
list: it is what would let the engine measure whether a prescribed 4x8' at
105% was actually executed at 105% (rather than degrading by the third
repetition), and it is a second, session-level source of estimated CP to
cross-check against Skiba's W'-balance model above. Costs one API call per
activity, so worth scoping to sessions with prescribed structure rather than
every aerobic ride — see the rate-limit note in the September API research if
this is pursued.

---

## 5. Workflow and automation

**Package the engine as a single command — resolved, September.** `coach.py
prep <id>` runs fetch, state resolution, and profile rendering together, per
the original architecture document — `new` and `check` joined it as the
onboarding and verification shortcuts. Removed a step from every day, as
predicted.

**Upload verified blocks via the Intervals.icu API.** The last manual step in
the daily loop. `POST /api/v1/athlete/{id}/events/bulk?upsert=true` accepts
the coach's native workout-description syntax directly — no format
conversion needed — and an `external_id` makes it idempotent: re-uploading a
corrected block updates it instead of duplicating it, which today requires
deleting by hand in Intervals.icu. A secondary benefit: Intervals computes
its own TSS from the same description on upload, which is a free,
independent check against the verifier's — if they disagree systematically,
that is worth investigating on its own. Natural fit as a `coach.py push`
subcommand once `check` has passed.

**A dedicated MCP server exposing this engine — scoped, deferred in favor of
the results module, September.** Not a generic wrapper around the raw
Intervals.icu API — several already exist and hand the model unresolved
data, reintroducing exactly the interpretation risk the `#STATE` contract
exists to prevent. The version worth building exposes the engine's own
functions as tools (`get_athlete_state`, `get_athlete_profile`,
`validate_block`, `push_block`, `list_roster`), so the Project could call
them mid-conversation without losing determinism — closer to a lower-friction
alternative to dragging files than to the "automate the reasoning layer" item
below, which is a much larger and different change.

**A `.exe` via PyInstaller.** Double-click instead of a terminal. Cheap to build,
and it makes the tools usable from a machine without Python installed.

**A scheduled task.** Windows can run the fetcher every morning so the data is
already current when the coach sits down.

**Automate the reasoning layer via the Anthropic API.** The largest possible
change, and the one to approach last. It would mean rebuilding the phase flow in
code, paying per token, and losing the ability to simply talk to the coach. The
workout engine already demonstrates the two-call pattern that would be needed. My
honest recommendation: do not do this until the conversational version has been
used long enough to know exactly which parts should stay conversational. Some of
them should — the coach's approval gate almost certainly.

**A web interface, eventually.** Only worth it if other coaches will use the
system. For a single coach it adds maintenance without adding capability.

---

## 6. Things I would think carefully about before building

**Do not let the engine start giving advice.** The current division is the source
of the system's reliability: the engine resolves facts, the coach decides what to
do about them. Every proposal above respects that line. A future feature that
crosses it — an engine that prescribes rather than reports — would undo the
architecture even if each individual step seemed reasonable.

**Resist making the state block longer.** It has grown with each stage and is now
substantial. There is a point at which the reasoning layer stops reading it
carefully. If a future addition is only occasionally relevant, it belongs in a
separate report the coach opens deliberately, not in the block that goes into
every conversation.

**The golden tests will feel like an obstacle at some point.** A change will be
obviously correct and three goldens will fail. The temptation will be to run
`--update` without reading the diff. That is the moment the safety net stops
working. Read the diff, every time — it takes thirty seconds and it is the entire
value of the suite.

**One caution about the Coggan power profile.** It ranks in W/kg against a road
cycling population, so it systematically under-rates heavier athletes and
multisport athletes. The engine reports the category honestly; the coach has to
supply the context. If that becomes a recurring irritation, the fix is a note in
the output rather than a change to the table.

---

## 7. What I would do first

If it were my decision, in this order:

1. **Use it for a month.** Everything above is speculation until real use tests it.
2. **Create three or four real athlete profiles** and see whether the intake asks
   the right things.
3. **Resolve the TSS formula question** — it improves Infame on its own and
   unblocks the engine integration.
4. **Add Seiler**, because polarized distribution is the one thing the system
   genuinely cannot express today.
5. **Then decide about automation**, with a month of real use informing what
   should stay manual.

**September update on item 1:** real use has started — seventeen athletes,
several weeks. It has already done exactly what real use is supposed to do:
surfaced a silently-broken Avg Power field the Excel pipeline never caught,
a dormant date-drift bug in the golden-test fixtures, and confirmed the
wellness-field question above is worth an actual audit rather than an
assumption. None of that would have surfaced from reasoning about the system
in the abstract. Items 2 through 5 are unaffected by this and remain open in
the order above.
