# Session Architectures — shape library

> GENERATED FILE — DO NOT EDIT. Source: `config/architectures/*.yaml`. Built 2026-10-08 by `python build_zone_tables.py build`.

Shapes a Main Set can take, distilled from ~1,700 MyWhoosh / Whatsonzwift cycling workouts and from the running catalogs (Daniels, Hudson & Fitzgerald, Hansons, Run Less Run Faster, Moehl, Canova). **No numbers live here**: every duration, intensity and RPE comes from the active author's zone table and the athlete's #STATE. `#STATE → RECENT ARCHITECTURES` names which of these the athlete has used in the last 8 weeks and which not at all.

**Progression levers** (the only four): `reps`, `bout_duration`, `recovery_duration`, `intensity`. A week-to-week change names one or two.

**Session class and touches.** In every class, a session's class is the purpose declared in [Zone]; harder minutes inside it are touches and do not change it (bursts in a tempo ride, a spike opening a sweet-spot interval, strides in an easy run). **Aerobic sessions** take one of the aerobic shapes (`steady_aerobic`, `aerobic_touches`, `rolling_aerobic`, or a progression). `technique_drills` is its own category, on request only.

| Architecture | Classes | Disciplines | Levers | Role |
| :--- | :--- | :--- | :--- | :--- |
| `aerobic_touches` — Aerobic with touches | recovery, endurance | trainer, road_bike, mtb, gravel, road_run, trail_run, treadmill, track_run | reps, bout_duration, intensity, recovery_duration | standalone |
| `cadence_contrast` — Cadence contrast | endurance, tempo, sub_threshold | trainer | reps, bout_duration | standalone, pre_fatigue |
| `classic_intervals` — Classic intervals | tempo, sub_threshold, threshold, supra_threshold, vo2max, anaerobic, neuromuscular | trainer, road_bike, mtb, gravel, road_run, trail_run, treadmill, track_run | reps, bout_duration, recovery_duration, intensity | standalone, pre_fatigue, finisher |
| `climb_simulation` — Climb simulation | threshold, supra_threshold, vo2max, anaerobic | trainer, road_bike, mtb, road_run, trail_run, treadmill | reps, bout_duration, intensity | standalone, finisher |
| `descending_ramp` — Descending ramp effort | threshold, supra_threshold, vo2max | trainer, treadmill | bout_duration, intensity | standalone |
| `duration_ladder` — Duration ladder | tempo, sub_threshold, threshold, supra_threshold, vo2max | trainer, road_run, trail_run, treadmill, track_run | reps, bout_duration, intensity, recovery_duration | standalone, finisher |
| `hard_start_fading` — Hard start, then fading | sub_threshold, threshold, supra_threshold, vo2max, anaerobic | trainer, road_bike, road_run | reps, bout_duration, intensity | standalone, pre_fatigue |
| `over_unders` — Over-unders | threshold, supra_threshold, vo2max | trainer, road_bike, road_run, treadmill | reps, bout_duration, intensity | standalone, finisher |
| `progression_run` — Progression (run or ride) | endurance, tempo, sub_threshold, threshold | trainer, road_bike, mtb, gravel, road_run, trail_run, treadmill, track_run | bout_duration, intensity, reps | standalone |
| `progressive_intervals` — Progressive intervals | tempo, sub_threshold, threshold, supra_threshold, vo2max | trainer, road_bike, road_run, treadmill | reps, bout_duration, intensity | standalone, finisher |
| `pyramid` — Pyramid | tempo, sub_threshold, threshold, supra_threshold, vo2max | trainer, road_bike, road_run, treadmill | bout_duration, intensity, reps | standalone |
| `rolling_aerobic` — Rolling aerobic (fartlek) | endurance, tempo | trainer, road_bike, mtb, gravel, road_run, trail_run, treadmill, track_run | bout_duration, intensity, reps | standalone, pre_fatigue |
| `single_ramp` — Single ramp effort | tempo, sub_threshold, threshold, supra_threshold, vo2max, anaerobic | trainer, road_run, treadmill | bout_duration, intensity | standalone, finisher |
| `sprints` — Sprints | neuromuscular | trainer, road_bike, mtb, gravel, road_run, track_run | reps, recovery_duration | pre_fatigue, finisher, standalone |
| `steady_aerobic` — Steady aerobic | recovery, endurance | trainer, road_bike, mtb, gravel, road_run, trail_run, treadmill, track_run | bout_duration, reps, intensity | standalone, pre_fatigue |
| `stepped_build` — Stepped build within each rep | tempo, sub_threshold, threshold, supra_threshold, vo2max | trainer, road_run, treadmill | reps, bout_duration, intensity | standalone, finisher |
| `surges_on_base` — Surges on a base | tempo, sub_threshold, threshold, vo2max, anaerobic, neuromuscular | trainer, road_bike, mtb, gravel, road_run, trail_run | reps, bout_duration, intensity | standalone, finisher |
| `sustained_effort` — Sustained single effort | endurance, tempo, sub_threshold, threshold, supra_threshold, vo2max | trainer, road_bike, mtb, gravel, road_run, trail_run, treadmill, track_run | bout_duration, intensity | standalone, finisher |
| `technique_drills` — Technique drills (pedalling or running) | recovery, endurance | trainer, road_bike, mtb, gravel, road_run, track_run | reps, bout_duration | standalone |

---

## `aerobic_touches` — Aerobic with touches

**Purpose.** An aerobic session whose purpose and most of whose load stay aerobic, with small doses of harder work placed inside it: tempo or sweet-spot blocks, short threshold, VO2max or anaerobic efforts, sprints or bursts on the bike, strides or pick-ups on the run. The touches keep the session alive, rehearse other gears and give the athlete something to look forward to; they do not change the session's class. The class is the purpose the coach declares in [Zone], and the validator lists the touches beside it. The libraries build most aerobic sessions this way, and so do the authors: Allen and Coggan's endurance rides with bursts, a tempo drill, threshold hills, VO2max intervals or anaerobic hill jams; Palladino's easy and long runs with accelerations, fartlek or half-marathon blocks; Uphill Athlete's pick-ups and tempo segments inside long aerobic runs; Daniels' strides.

**Rep shape:** touches_on_base · **Set shape:** single, identical, progressive

**Coach notes.** The touch follows the purpose of the day, not a quota. An easy run leaves room only for brief accelerations (Palladino keeps excursions short there, Daniels' strides are light with full recovery); a long run or ride can carry substantial touches (fartlek or half-marathon blocks in Palladino's long run, a tempo segment in the middle of Uphill Athlete's long run, Allen and Coggan's long endurance rides). Where the touches go is a design choice: early, while fresh, for speed and strength; late, on tired legs, for endurance (Friel's easy-hard variation keeps the steady part first); or spread as terrain and feel invite (Uphill Athlete). Between touches the athlete returns to the aerobic base, not to recovery. Touches can mix classes in one session (a tempo block early, short spikes later). Cadence can shape a touch, but a touch is a change of intensity, not only of cadence. In the libraries, the time above tempo in these sessions is usually a few minutes, context and not a limit; when the touches become the main work, the session has changed: declare that class instead. Plan checks still count every step at its own class, so heavy touches show in the week's picture.

**Sources:** TRPM-L2-036, TRPM-L2-037, TRPM-L2-039, TRPM-L2-040, TRPM-L2-042, TRPM-L2-002, HPC-L2-004, TUA-L2-004, TUA-L2-005, DRF-C05-019, TEU-C05-038, Palladino §7 (EZ Aerobic Run, EZ Long Run)

**Shape (relative notation only):**
- Long aerobic block with N short touches spread through it, each followed by a return to the aerobic base
- Aerobic base, a set of touches in the middle or in the last third, then aerobic to the end
- Aerobic run with N strides or pick-ups, early (fresh) or late (on tired legs)
- Aerobic ride with touches of two classes: a tempo or sweet-spot block early, short efforts later

## `cadence_contrast` — Cadence contrast

**Purpose.** Same power target, alternating cadence (e.g. 60rpm / 95rpm blocks). The stimulus is neuromuscular/technical, not metabolic — intensity barely moves, only the pedaling demand does. A genuine, if rare, architecture for low-cadence strength work or spin efficiency, distinct from cadence cues layered onto another architecture (which many workouts in the corpus also do, without this being their primary shape).

**Rep shape:** cadence_contrast · **Set shape:** identical

**Coach notes.** Cycling-specific; has no running equivalent. Intensity is deliberately not a lever here — moving it turns this into a different architecture with a cadence label attached, not a harder version of this one.

**Shape (relative notation only):**
- N x (low-cadence block / high-cadence block), same power target throughout

## `classic_intervals` — Classic intervals

**Purpose.** The default interval structure: N identical work bouts separated by full (near-recovery) rest. Isolates one physiological stimulus cleanly and lets the athlete hit the same target repeatedly. The baseline architecture that every other one in this library is a deliberate departure from — this is what the coach falls back to when nothing else has been chosen, which is exactly why the picker should not default to it silently.

**Rep shape:** steady · **Set shape:** identical

**Coach notes.** Recovery is full active recovery, not float — that is what separates this from "surges_on_base" or "over_unders". If recovery is shortened toward the work intensity, the architecture has changed, not just its dose.

**Shape (relative notation only):**
- N x (work bout / recovery ≈ work duration or longer), N typically 3-8
- 2 sets of N x (...) with a longer easy block between sets

## `climb_simulation` — Climb simulation

**Purpose.** A short ramp up into a harder finish, repeated across several "climbs" of varying length/cadence, each separated by a descent-style recovery. Distinct from a plain ramp because the ramp is always followed by a short, harder punch at the top — it simulates cresting a climb, not just a progressive effort.

**Rep shape:** climb_simulation · **Set shape:** identical

**Coach notes.** Low frequency in the cycling corpus likely reflects that most "climb" workouts on those platforms are tagged as over_unders or stepped_build. In running it is central: hill repeats appear in Hudson & Fitzgerald, Palladino, Rosario/Fitzgerald and Olbrich. For running the "climb" is the terrain itself (or the treadmill incline), not a ramp in the target: N x (uphill rep / jog or walk back down). Say "uphill" / "subida" / "incline" in the step cue — the engine can only recognise this shape from that word, because the target alone looks like any other interval.

**Shape (relative notation only):**
- N x (ramp up / short hard punch at the top / easy descent), repeated

## `descending_ramp` — Descending ramp effort

**Purpose.** A single bout whose target falls steadily through the effort — the mirror of single_ramp. Rare in the corpus; mostly appears as a deliberately front-loaded effort (start at the hardest point while fresh, ease off as fatigue accumulates) rather than as a repeated architecture.

**Rep shape:** ramp · **Set shape:** single

**Coach notes.** Low frequency in the corpus is informative, not disqualifying — this is a legitimate, distinct shape, just an uncommon prescription. Don't merge it into single_ramp; the direction of the ramp changes what's trained (arriving fresh vs. finishing fresh).

**Shape (relative notation only):**
- One block, target falling steadily from hard to moderate over its full duration

## `duration_ladder` — Duration ladder

**Purpose.** Same intensity throughout (or, in a documented variant, intensity that climbs or falls in lockstep with duration), with the duration of each rep changing monotonically -- longer each time, or shorter each time -- and full recovery between reps. Distinct from progressive_intervals (same duration, changing intensity) and from pyramid (duration rises then falls symmetrically): here duration moves in one direction only. Trains the same pace under a changing time-horizon, or lets an athlete accumulate volume at a hard pace by front-loading the longest rep while fresh (duration_down) or building confidence into it (duration_up).

**Rep shape:** steady · **Set shape:** duration_ladder_up, duration_ladder_down

**Coach notes.** Identified from the running-catalog analysis, not the original cycling corpus: Daniels' T-pace tables ("2x12min / 2x5min", "15min/10min/5min"), Hudson & Fitzgerald's "Ladder Intervals," Moehl's "Ladder" (with a documented half-time-recovery variant: shorter rungs also get shorter recovery, and a faster pace), and Canova's "Medium Speed Variation" (5000/4000/3000m, pace rising as distance falls) -- five independent authors converging on the same shape. In several of these (Hudson, Canova), pace changes together with duration rather than staying fixed; treat that as a valid variant of this architecture (both levers moving together), not a separate one. A rung can itself be a small repeated block (Daniels' "2x12min / 2x5min" is a 2-rung ladder where each rung is 2 reps, not 1) -- the ladder applies to the block-to-block trend, not necessarily to single reps.

**Shape (relative notation only):**
- Reps at one target, full recovery between, each rep's duration longer (or shorter) than the last -- e.g. 3 reps at 15, 10, 5 minutes
- As above, but the target also gets harder (or easier) each rep, moving with duration
- A rung may itself be a small repeated block rather than a single rep (2x12min, then 2x5min)

## `hard_start_fading` — Hard start, then fading

**Purpose.** The inverse of stepped_build: the rep opens at its hardest and steps down without recovery. Trains starting a race/effort hard and holding on as it decays, or simulates going off the front and settling — a different skill from building into a hard finish.

**Rep shape:** hard_start_fading · **Set shape:** identical

**Coach notes.** Easy to confuse with stepped_build read backwards — the distinguishing fact is which end of the rep is hardest, since that changes what's being trained (starting hard vs. finishing hard). Sweet spot uses it too (v7.36): Cusick's Hard Start SST opens each sweet-spot interval with a short spike above threshold to force better lactate management; the session is still sweet spot, and the spike is its touch.

**Sources:** WKOC-L2-022, WKOC-L2-017

**Shape (relative notation only):**
- One bout: hardest step first, each following step easier, no recovery between steps, then full recovery, then repeat

## `over_unders` — Over-unders

**Purpose.** Alternating just above and just below threshold with no full recovery between the two — the "under" is still working, just easier. Trains clearing lactate while still producing meaningful power, directly relevant to racing where pace surges above threshold before settling only partway down.

**Rep shape:** over_under · **Set shape:** identical

**Coach notes.** The "under" segment must stay clearly below the "over" segment but still above tempo — if it drops to a full recovery power, this has become classic_intervals; if it rises to match the "over", it has become sustained_effort.

**Shape (relative notation only):**
- N x (over segment / under segment, no recovery between them), repeated with full recovery between sets

## `progression_run` — Progression (run or ride)

**Purpose.** One continuous effort split into two or more discrete segments, each harder than the last, with no recovery between segments -- each segment held at its own roughly steady effort, not a smooth continuous rise. Distinct from single_ramp (power/pace rises continuously through the whole effort, never settling) and from stepped_build (several short steps within one shorter, harder effort): here there are typically only 2-3 segments, each substantial in its own right (often 15+ minutes), and the run reads as "a run that gets harder partway through," not as a structured interval session. Trains finishing strong on tired legs and practices even-to-negative pacing for a race.

**Rep shape:** progression_run · **Set shape:** single

**Coach notes.** Identified from the running-catalog analysis, not the original cycling corpus -- it is the single most cross-validated new finding in that work: named explicitly as "Progression Run" by Hudson & Fitzgerald (6 worked formats) and, independently, as "Progressive Run" by Canova (2 more worked formats); the same shape also appears unlabeled in Hansons ("4 and Go!", "Five and GO!", "Last 3 GO!") and in Run Less Run Faster's long-run guidance ("start slightly slower... pick up mid-run, finish strong"). Four independent sources, one shape. `reps` as a progression lever here means the number of discrete segments (2 vs. 3), not repeated bouts -- there is still only one continuous run. Cycling has the same shape (v7.36): the Oct 2026 re-analysis of the library found 50 aerobic rides that rise through the session, and Cusick prescribes it outright: base miles that start lower and finish equal or slightly higher, never softer, and an aerobic endurance session in three steady blocks, each a little higher. It is also how an aerobic session can end with a harder part: Friel's easy-hard ride keeps the steady zone 2 part first and raises the intensity in the last part, and Uphill Athlete's progressive distance workout climbs from zone 1 to a short time near threshold. A progression that stays inside the aerobic zone is an aerobic session (declare Endurance); one that ends at tempo or above is declared by its purpose.

**Sources:** WKOC-L2-006, WKOC-L2-020, HPC-L2-004, TUA-L2-006

**Shape (relative notation only):**
- One continuous run: an easier first segment, then 1-2 more segments each harder than the last, no recovery between them
- A long run whose final third or quarter rises to a faster, sustained pace
- An aerobic ride in two or three steady blocks, each a little higher than the last, finishing equal or stronger, never softer

## `progressive_intervals` — Progressive intervals

**Purpose.** Identical-duration reps, but each rep is harder than the last (as opposed to stepped_build, where the rise happens inside one rep). Trains pacing a set that gets harder as fatigue accumulates, and is a natural test of whether an athlete can hold form under rising demand across a session.

**Rep shape:** steady · **Set shape:** progressive

**Coach notes.** The regressive mirror (each rep easier than the last) is the same architecture with the direction reversed — represent it as `set_shape: regressive` on the same rep_shape rather than as a separate file.

**Shape (relative notation only):**
- N x (work bout / full recovery), each work bout's target higher than the previous one

## `pyramid` — Pyramid

**Purpose.** A set of reps whose duration (or intensity) rises to a peak rep and then falls back down symmetrically, rather than climbing steadily (ladder_up) or descending steadily (ladder_down). Mentally distinct from a plain ladder because the athlete knows they're past the hardest point once the descent begins.

**Rep shape:** steady · **Set shape:** pyramid

**Coach notes.** Only one clean example survived deduplication in this corpus; most apparent "pyramids" turned out to be ladders miscounted before the set-shape fix, or genuinely irregular sets better filed under a combination of other architectures. Keep this one narrow: true up-then-down symmetry only.

**Shape (relative notation only):**
- Reps stepping up in duration to a peak, then back down, same intensity, full recovery between reps

## `rolling_aerobic` — Rolling aerobic (fartlek)

**Purpose.** Continuous aerobic work whose intensity keeps moving, with no stop: it rolls between the low and the high part of the aerobic zone and rises briefly into tempo or sweet spot, like rolling terrain, a group ride or a run by feel. There are no recovery steps and the base never drops to recovery. Distinct from `aerobic_touches`, where discrete efforts sit on a steady base: here the whole session undulates. Distinct from `over_unders`, where both sides sit around threshold.

**Rep shape:** undulating · **Set shape:** single, identical

**Coach notes.** Allen and Coggan's fartlek accelerates and varies power at random to simulate a mass-start race, and they shorten the ride because the stress is higher than steady work; Friel's fartlek lets feel choose the durations and stops well before fatigue; on the trainer Friel shifts gears to simulate hills. Outdoors this is often what the terrain already gives: describe it in words and RPE (rise on the climbs, settle on the flats) rather than as steps the road will not allow. On the trainer or treadmill, write the undulation out so it is not a guess.

**Sources:** TRPM-L2-003, HPC-L2-013, CTB-L2-007, TRPM-L2-042, TUA-L2-004

**Shape (relative notation only):**
- One continuous block whose intensity rolls between the low and high aerobic zone with brief rises into tempo, no recovery
- N x (aerobic segment / short rise / aerobic segment at another level), continuous
- A run or ride by feel over rolling terrain: rise on each climb, settle on the flats

## `single_ramp` — Single ramp effort

**Purpose.** The work bout itself is a ramp rather than a steady target — power rises (or falls) continuously through the effort instead of holding one number. Removes the option to settle into a pace; the athlete is always chasing a slightly harder (or recovering from a slightly easier) target.

**Rep shape:** ramp · **Set shape:** single

**Coach notes.** Outdoor cycling and unstructured running can't reliably execute a continuous ramp target the way ERG mode or a treadmill program can; keep this one mainly to trainer/treadmill/structured-pace contexts.

**Shape (relative notation only):**
- One block, power/pace rising steadily from moderate to hard over its full duration
- Rise then hold the final target for a short tail

## `sprints` — Sprints

**Purpose.** Very short (<=30s), very hard (>150% FTP equivalent / max effort) bouts with long full recovery. Neuromuscular power and technique, not aerobic load — the TSS contribution is almost incidental to the point of the session.

**Rep shape:** sprint · **Set shape:** identical

**Coach notes.** Intensity is not really a progression lever here — it's already maximal. Recovery should stay long enough that quality doesn't degrade rep to rep; shortening it changes the architecture into anaerobic capacity work, not a harder version of the same sprint set.

**Shape (relative notation only):**
- N x (max sprint <=15-30s / full recovery 2-5min)

## `steady_aerobic` — Steady aerobic

**Purpose.** Aerobic work with nothing above the aerobic zone: one continuous effort, or several blocks placed at different points of the zone. It is the simple session, and simple is a decision with a reason, never the default. Good reasons are specific: a recovery day; an aerobic-threshold ride whose steadiness is the point and whose drift or efficiency factor is being tracked (Friel's AE2 asks to avoid surges into zone 3 for exactly this); an athlete with a large aerobic deficiency early in base (Uphill Athlete); the day before a key session or race; outdoors when traffic or a group decide the ride. Without such a reason, an aerobic session is better built with `aerobic_touches`, `rolling_aerobic` or a progression.

**Rep shape:** steady · **Set shape:** single, identical

**Coach notes.** Even with nothing above the zone, the session can still change shape: blocks at different points of the aerobic zone, a progressive ride that starts lower and finishes equal or slightly higher, never softer (Cusick's base miles), gear changes that simulate terrain (Friel AE3), or a cadence section. Cadence is one modifier among several, not the default way to make an aerobic session different: if every steady session of a block varies only cadence, the block is still monotonous. Until v7.36 this file was `endurance_cadence`; its name made cadence look like the only lever.

**Sources:** HPC-L2-004, CTB-L2-005, CTB-L2-006, CTB-L2-007, WKOC-L2-006, WKOC-L2-020, TUA-C08-002, Palladino §7 (EZ Aerobic Run)

**Shape (relative notation only):**
- One long block in the aerobic zone
- Two or three blocks at different points of the aerobic zone, no rest between them
- N x (aerobic block at one cadence / aerobic block at another), same intensity

## `stepped_build` — Stepped build within each rep

**Purpose.** Each rep climbs through several steps of rising intensity with no recovery between the steps (e.g. tempo -> sweet-spot -> threshold -> VO2max inside one continuous bout), then a full recovery, then the whole climb repeats. Builds tolerance to accumulating intensity within a single effort rather than isolating one zone.

**Rep shape:** stepped_build · **Set shape:** identical

**Coach notes.** The number of steps and the intensity spread between the first and last step are what actually varies across the corpus's versions of this architecture; treat "add one more step" as a distinct lever from "raise the top step."

**Shape (relative notation only):**
- One continuous bout: 3-5 steps, each harder than the last, no recovery between steps, then full recovery, then repeat 2-4x

## `surges_on_base` — Surges on a base

**Purpose.** A sustained base (tempo, sweet spot or threshold) with short, much harder bursts layered inside it, and no easy recovery after each burst: the athlete returns to the base. Trains producing a hard effort without a preceding recovery, and clearing it while still working: the closest simulation of race accelerations out of a paceline or on a climb. The session's class is its declared purpose: usually the base (a tempo or sweet-spot session with bursts as its touches, as in Allen and Coggan's tempo rides with anaerobic-capacity bursts or Cusick's sweet spot with FTP surges), and the bursts' class when they are the point of the day (race-like accelerations).

**Rep shape:** surge_on_base · **Set shape:** identical, single

**Coach notes.** Two numbers move somewhat independently: the base intensity (usually fixed for the session) and the bursts' intensity, length and count (the usual progression lever). After each burst the athlete comes back to the base, not lower: Allen and Coggan say to recover at tempo and no lower. Don't let the base drift: if the base itself becomes the thing progressing, this has turned into classic_intervals with a longer "recovery" that isn't really recovery. Before v7.36 the class was always the bursts'; with the class declared in [Zone], a tempo or sweet-spot session with bursts is declared by its base and the bursts are its touches.

**Sources:** TRPM-L2-045, TRPM-L2-047, TRPM-L2-048, TRPM-L2-037, WKOC-L2-017, WKOC-L2-022

**Shape (relative notation only):**
- Base effort held continuously, with N short bursts (5-30s) inserted at intervals, no return to easy between them
- N x (base segment / burst), base and burst both continuous — no easy recovery step
- Each base block opened by a few short maximal bursts, then straight into the base with no rest

## `sustained_effort` — Sustained single effort

**Purpose.** One continuous block at a single target, no internal structure. Builds the ability to hold a pace/power without the mental and physiological relief of a recovery. The architecture behind classic tempo/sweet-spot/threshold rides and long steady-state efforts.

**Rep shape:** steady · **Set shape:** single

**Coach notes.** Duration is the only real lever besides intensity. A common progression is simply the same effort held longer block to block (see the "5min FTP" / "TT Speed" style series in the corpus, which grow the single effort from ~10min to ~25min with intensity essentially unchanged).

**Shape (relative notation only):**
- One block, 8-60 min, single target

## `technique_drills` — Technique drills (pedalling or running)

**Purpose.** A session whose purpose is skill, not metabolic load: pedalling drills (spin-ups, isolated leg, high-cadence pedalling, the 9-to-3 stroke) or running form work (form drills, quick-step and posture cues). Its own category, apart from the aerobic shapes: a drill session is not how an aerobic session gets its variety, and it is not counted as one.

**Rep shape:** drill · **Set shape:** identical, single

**On request only** — when the head coach or the athlete asks for it.

**Coach notes.** Only when the head coach or the athlete asks for it. It belongs mostly to the start of the season or of the base, and to the first years of structured training: Friel places speed skills in Base and says they matter most in the first three years. Effort stays low; for the drills themselves Friel says power and heart rate are not meaningful, so the step targets stay in the recovery or aerobic zone and the cue carries the drill. Write the drill's name in the cue (drill, técnica, pierna aislada, spin-up) so the engine records the session as technique.

**Sources:** CTB-L2-011, CTB-L2-012, CTB-L2-013, HPC-L2-008, TRPM-L2-038, TRPM-L2-064, TUA-C04-009, Palladino §10

**Shape (relative notation only):**
- Easy aerobic riding with N drill sets (spin-ups, isolated leg, high cadence), easy riding between sets
- Easy running with form drills, then a few relaxed strides to fix the pattern at speed

---

## Combining architectures in one Main Set

Touches are not a combination: a few harder minutes inside a session of any class (bursts in a tempo ride, a spike opening a sweet-spot interval, strides in an easy run) leave it one architecture of its declared class, and the validator lists them as touches. The harder the session, the more a touch has to earn its place, since it competes with the quality of the key work: in the library, 81% of tempo and sweet-spot sessions carry touches, 67% of threshold, 40% of VO2max and 22% of anaerobic ones, and they get shorter as the class rises. Context, not a rule. A combination is described as an ordered list of architecture names plus their role (pre_fatigue / standalone / finisher — see each architecture's `combinable` field for which roles it can take). The picker should treat a combination as optional, reached for deliberately, not as the default way to fill a main set.

- **pre_fatigue_into_key_work** — `[short, easier architecture] -> [main architecture at full freshness-adjusted target]` (e.g. sprints (pre_fatigue) -> sustained_effort). Blunts freshness before the architecture that actually matters for the session's training goal, so the key work is done partially fatigued — closer to how it will be executed late in a race.
- **key_work_into_finisher** — `[main architecture] -> [short, different architecture]` (e.g. classic_intervals -> sprints). Adds a second, usually shorter and differently-shaped stimulus once the key work is already done, without diluting the key work itself.
- **two_distinct_sets** — `[architecture A, full set] -> full recovery block -> [architecture B, full set]` (e.g. surges_on_base -> classic_intervals). Two separate training goals in one session (common in longer/harder days). Each set should still be legible as its own architecture; if A and B share the same rep_shape and set_shape, this is not a combination — it is one longer set of a single architecture.
- **sandwich** — `[sustained_effort or steady_aerobic] -> [a different architecture] -> [sustained_effort or steady_aerobic]` (e.g. sustained_effort -> classic_intervals -> sustained_effort). A repeated running pattern (Hansons' P-017 "2 miles / 8x800 / 2 miles", Moehl's multi-part hill workout, Canova's "Long Resistance w/ Variation") — an easy-to-moderate bookend both before and after the key work, rather than only a pre_fatigue lead-in or only a finisher. The two bookends need not be identical in duration or pace; what makes this a sandwich rather than two separate combinations is that both sides are the same (easier) architecture as each other, framing one harder block in the middle. A common running variant increases the difficulty of each block in the sequence (Moehl's multi-part hill workout: power-hike, then a runnable segment, then a hard uphill surge) — still a sandwich in shape, with a progressive dose across the blocks rather than a flat one.
