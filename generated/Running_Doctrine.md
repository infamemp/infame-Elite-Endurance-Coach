# Running Doctrine — v1.1

> GENERATED FILE — DO NOT EDIT. Source: `config/doctrine/running.yaml`. Built 2026-10-02 by `python build_zone_tables.py build`.

How the running sources work as one system. Palladino is the spine: the intensity language, the load guardrails and the testing logic, anchored to tested fitness and usable with power, pace or heart rate. Daniels governs road training structure and session doses, Koop governs trail and ultra, and Training for the Uphill Athlete governs vertical, muscular-endurance and strength work. Mujika governs the taper; Hansons, Hudson, Rosario and Olbrich refine inside those rules; Run Less, Run Faster is a mode used only on request. The methodology the athlete declared still supplies the zone table; this file decides which source answers each question. Statements here are Infame doctrine: attribute them to Infame doctrine and name the source behind each one. Outside this file the one-author attribution rule applies unchanged.

**How to read it.** Each decision has one **governing** source: its rule decides. **Refines** entries add precision inside that rule and never override it. The codes in brackets are KB entry IDs: search the Project for the code to open the exact passage. A code written §N is section N of that source's file (its `## N.` heading).

## Sources

| Key | Author | Work | Knowledge file | Entry IDs |
| :--- | :--- | :--- | :--- | :--- |
| `palladino` | Steve Palladino | Running with Power (coaching knowledge base) | `Steve_Palladino_Running_with_Power.md` | sections `§N` |
| `daniels` | Jack Daniels | Daniels' Running Formula (4th ed., 2022) | `Jack_Daniels_Running_Formula.md` | `DRF-…` |
| `koop` | Jason Koop, Jim Rutberg & Corrine Malcolm | Training Essentials for Ultrarunning (2nd ed., 2021) | `Jason_Koop_Training_essentials_ultrarunning.md` | `TEU-…` |
| `uphill` | Steve House, Scott Johnston & Kilian Jornet | Training for the Uphill Athlete (2019) | `House_Johnston_Jornet_Training_for_the_Uphill_Athlete.md` | `TUA-…` |
| `mujika` | Iñigo Mujika | Tapering and Peaking for Optimal Performance (2009) | `Mujika_Tapering_Peaking_Extraction.md` | `TPOP-…` |
| `hansons_marathon` | Luke Humphrey with Keith and Kevin Hanson | Hansons Marathon Method | `Hansons_Marathon_Method.md` | sections `§N` |
| `hansons_half` | Luke Humphrey with Keith and Kevin Hanson | Hansons Half-Marathon Method | `Hansons_Half_Marathon_Method.md` | sections `§N` |
| `hudson` | Brad Hudson & Matt Fitzgerald | Run Faster from the 5K to the Marathon | `Hudson_Run_Faster_From_5K_to_Marathon.md` | sections `§N` |
| `rosario` | Matt Fitzgerald & Ben Rosario | Run Like a Pro (Even If You're Slow) | `Rosario_Run_Like_a_Pro.md` | sections `§N` |
| `olbrich` | Wolfgang Olbrich | Ultramarathon Training | `Wolfgang_Olbrich_Ultramarathon_Training.md` | sections `§N` |
| `rlrf` | Bill Pierce, Scott Murr & Ray Moss | Run Less, Run Faster (3rd ed.) | `Run_Less_Run_Faster.md` | sections `§N` |

## The matrix at a glance

| Decision | Governs | Refines | Executed in |
| :--- | :--- | :--- | :--- |
| Intensity language — zones across power, pace and heart rate | `palladino` | `daniels`, `koop` | Zone tables |
| Threshold, testing and fitness markers | `palladino` | `daniels`, `uphill` | Engine → #STATE |
| Load progression — ramp rate and weekly volume | `palladino` | `daniels`, `koop` | This doctrine |
| Intensity distribution | `palladino` | `rosario`, `uphill` | This doctrine |
| Dose per session for each intensity | `daniels` | `palladino` | This doctrine |
| Road season structure (5K to marathon) | `daniels` | `hansons_marathon`, `hansons_half`, `hudson` | This doctrine |
| Trail and ultra season structure | `koop` | `uphill`, `olbrich` | This doctrine |
| Vertical, muscular endurance and strength | `uphill` | `koop` | This doctrine |
| Which metric on hills and trail | `palladino` | `koop` | This doctrine |
| Treadmill running | `palladino` | `daniels` | This doctrine |
| Returning after a break | `daniels` | `palladino` | This doctrine |
| Peaking, taper and race pacing | `mujika` | `palladino`, `daniels`, `koop` | Config (decision_thresholds.yaml) |

---

## Intensity language — zones across power, pace and heart rate

*Executed in: Zone tables*

**Governs — Steve Palladino.** Intensity is anchored to the athlete's tested threshold (CP/FTP for power, the threshold-pace or LTHR equivalent otherwise) and read through Palladino's zones and intensity domains, whatever metric the athlete's device gives. [`§1`, `§2`]

- **Refines — Jack Daniels.** On the road, E, M, T, I and R are the named training types, each with its purpose and its pace from the current VDOT. [`DRF-C06-003`, `DRF-C06-009`]
- **Refines — Jason Koop, Jim Rutberg & Corrine Malcolm.** On trail and in ultras, RPE and the talk test govern effort; heart rate is a poor intensity tool on its own there. [`TEU-C06-011`, `TEU-C04-019`]

## Threshold, testing and fitness markers

*Executed in: Engine → #STATE*

**Governs — Steve Palladino.** Prescribe only from a valid, recent tested threshold; targets rise only after a retest shows the threshold rose ("let the fitness come to you"). [`§1`, `§9`, `§17`]

- **Refines — Jack Daniels.** A recent race sets the VDOT, and the VDOT sets the training paces. [`DRF-C02-015`, `DRF-C06-008`]
- **Refines — Steve House, Scott Johnston & Kilian Jornet.** For trail and mountain athletes, test the aerobic threshold too: a gap of more than about 10% between AeT and LT marks an aerobic deficiency to fix first. [`TUA-C07-001`, `TUA-C05-005`]

## Load progression — ramp rate and weekly volume

*Executed in: This doctrine*

**Governs — Steve Palladino.** Load is duration times relative intensity (RSS), not mileage alone. Keep the weekly CTL ramp at about 1-5 for most runners; above 7 is unsustainable. Watch trends, not single days, and never chase a CTL number. [`§1`, `§4`]

- **Refines — Jack Daniels.** Raise weekly amount in steps and hold each new level before the next increase. [`DRF-C08-004`]
- **Refines — Jason Koop, Jim Rutberg & Corrine Malcolm.** On trail, load uses graded pace (NGP/GAP) so climbing and descending count. [`TEU-C05-028`, `TEU-C06-009`]

## Intensity distribution

*Executed in: This doctrine*

**Governs — Steve Palladino.** Pyramidal in general preparation: most time easy, a minority near threshold, a touch of short hill sprints; the middle zones above threshold are used deliberately, not by drift. [`§5`, `§6`]

- **Refines — Matt Fitzgerald & Ben Rosario.** Keep easy running genuinely easy (the 80/20 balance of the pros). [`§3`, `§5`]
- **Refines — Steve House, Scott Johnston & Kilian Jornet.** Base for mountain athletes: 80-85% (up to 90% when building base) at or below the aerobic threshold. [`TUA-C02-011`, `TUA-C08-010`]

## Dose per session for each intensity

*Executed in: This doctrine*

**Governs — Jack Daniels.** Per-session ceilings by type: long run, M, T, I and R each limited by a share of weekly volume and by time per bout. [`DRF-C06-004`, `DRF-C06-007`]

- **Refines — Steve Palladino.** Workout protocols and execution rules by zone. [`§7`]

## Road season structure (5K to marathon)

*Executed in: This doctrine*

**Governs — Jack Daniels.** Four phases — foundation and injury prevention, early quality, transition quality, final quality — with lengths adapted to the time available; each stress level is held 6-8 weeks before it is raised. [`DRF-C08-015`, `DRF-C08-016`, `DRF-C08-017`, `DRF-C08-001`]

- **Refines — Luke Humphrey with Keith and Kevin Hanson.** Marathon goal with 5-6 run days: cumulative fatigue, SOS days, long run capped at 16 miles. The goal event chooses the Hansons book: marathon here, half marathon below. [`§2`, `§7`]
- **Refines — Luke Humphrey with Keith and Kevin Hanson.** The same structure aimed at the half marathon, with its own paces. [`§2`, `§10`]
- **Refines — Brad Hudson & Matt Fitzgerald.** Adapt the plan to how the athlete is responding, week to week. [`§2`, `§7`]

## Trail and ultra season structure

*Executed in: This doctrine*

**Governs — Jason Koop, Jim Rutberg & Corrine Malcolm.** Build from the event's demands (course, grade, duration) and Koop's hierarchy of needs; train weaknesses early and strengths late, become specific close to the event, and visit every intensity even for slow races. [`TEU-C02-026`, `TEU-C08-019`, `TEU-C09-021`, `TEU-C09-022`, `TEU-C08-020`]

- **Refines — Steve House, Scott Johnston & Kilian Jornet.** Periods (transition, base, precompetition, competition) and gradual annual volume growth. [`TUA-C08-009`, `TUA-C08-005`]
- **Refines — Wolfgang Olbrich.** Flat road ultras (100 km, 24 h) follow Olbrich's periodization. [`§7`]

## Vertical, muscular endurance and strength

*Executed in: This doctrine*

**Governs — Steve House, Scott Johnston & Kilian Jornet.** Muscular endurance is its own quality, built after a strength base and with care; strength work for the legs and core progresses in stages through the season. [`TUA-C04-020`, `TUA-C08-016`, `TUA-C08-014`, `TUA-C08-017`]

- **Refines — Jason Koop, Jim Rutberg & Corrine Malcolm.** Match training grade to the race's grades, decide when to hike by grade and speed, and use eccentric work against downhill muscle damage. [`TEU-C08-005`, `TEU-C04-017`, `TEU-C09-007`]
- **Refines — Jason Koop, Jim Rutberg & Corrine Malcolm.** Organize strength training across the season and the week. [`TEU-C08-024`, `TEU-C08-025`]

## Which metric on hills and trail

*Executed in: This doctrine*

**Governs — Steve Palladino.** With a run power meter, power is the metric on grade: it accounts for hills that pace cannot; compare running economy only on comparable terrain. [`§4`, `§7`]

- **Refines — Jason Koop, Jim Rutberg & Corrine Malcolm.** Without power, use graded pace or RPE on trail, never raw pace. [`TEU-C05-028`, `TEU-C06-011`]

## Treadmill running

*Executed in: This doctrine*

**Governs — Steve Palladino.** Treadmill running with power and how it compares with outdoor running. [`§12`]

- **Refines — Jack Daniels.** Grade and speed combinations that give equivalent effort on the treadmill. [`DRF-C06-017`, `DRF-C04-006`]

## Returning after a break

*Executed in: This doctrine*

**Governs — Jack Daniels.** After a planned or unplanned break, reduce VDOT and training load by the length of the break before resuming. [`DRF-C08-012`, `DRF-C08-013`, `DRF-C06-019`]

- **Refines — Steve Palladino.** Recovery, injury prevention and longevity rules. [`§11`]

## Peaking, taper and race pacing

*Executed in: Config (decision_thresholds.yaml)*

**Governs — Iñigo Mujika.** Taper by cutting volume 41-60%, keeping intensity, and keeping frequency at or above about 80%, with a progressive (non-linear) reduction; two weeks is the default when the athlete's own response is unknown, and the taper is individualized. The numbers live in config/decision_thresholds.yaml (taper section). [`TPOP-C06-008`, `TPOP-C04-042`, `TPOP-C06-009`, `TPOP-C08-002`, `TPOP-C06-010`]

- **Refines — Steve Palladino.** Peak and race by power or effort plans built from tested fitness. [`§8`]
- **Refines — Jack Daniels.** How marathon pace is estimated and practised. [`DRF-C06-005`]
- **Refines — Jason Koop, Jim Rutberg & Corrine Malcolm.** Ultra taper by variable, and effort-based race-day strategy calibrated by RPE. [`TEU-C08-032`, `TEU-C08-033`, `TEU-C08-040`]

## Mode: Time-crunched runner

*Activation: on request only — the head coach asks for it or the athlete declares it, and you confirm before applying it. Recorded as `#SESSION Notes — Time-crunched: on`.*

**Structure from Bill Pierce, Scott Murr & Ray Moss.** Zones: the paces Run Less, Run Faster prescribes for its three key runs, read from its own knowledge file; easy cross-training stays in the active methodology's zones.

- Three quality runs a week — track repeats, a tempo run and a long run — plus cross-training on the other days; no easy junk miles. [`§2`, `§7`]
- Paces and progressions come from the athlete's current race performance. [`§5`, `§15`]
