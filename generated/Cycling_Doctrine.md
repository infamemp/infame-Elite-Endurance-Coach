# Cycling Doctrine — v1.1

> GENERATED FILE — DO NOT EDIT. Source: `config/doctrine/cycling.yaml`. Built 2026-10-04 by `python build_zone_tables.py build`.

How the three cycling sources work as one system. Coggan and Allen give the language (levels, TSS, the Performance Manager), Friel gives the season (periods, annual volume, limiters), Mujika gives the taper, and Cusick gives the diagnosis and the fine control of training (the power-duration model, time to exhaustion, optimized intervals, intensity distribution). Use this file to decide which source answers a question; open the cited entries when you need the detail. Statements here are Infame doctrine: attribute them to Infame doctrine and name the source behind each one. Outside this file the one-author attribution rule applies unchanged. The zone table of the athlete's declared methodology always governs zone boundaries.

**How to read it.** Each decision has one **governing** source: its rule decides. **Refines** entries add precision inside that rule and never override it. The codes in brackets are KB entry IDs: search the Project for the code to open the exact passage. A code written §N is section N of that source's file (its `## N.` heading).

## Sources

| Key | Author | Work | Knowledge file | Entry IDs |
| :--- | :--- | :--- | :--- | :--- |
| `coggan` | Hunter Allen, Andrew Coggan & Stephen McGregor | Training and Racing with a Power Meter (3rd ed., 2019) | `Allen - Coggan_Training_and_Racing_With_a_Powermeter.md` | `TRPM-…` |
| `friel_tb` | Joe Friel | The Cyclist's Training Bible | `Friel_Cyclists_Training_Bible.md` | `CTB-…` |
| `friel_hpc` | Joe Friel | The High-Performance Cyclist | `Friel_High_Performance_Cyclist.md` | `HPC-…` |
| `cusick` | Tim Cusick | WKO Coaching Webinars (2016-2021) | `Cusick_WKO_Coaching_Webinars.md` | `WKOC-…` |
| `mujika` | Iñigo Mujika | Tapering and Peaking for Optimal Performance (2009) | `Mujika_Tapering_Peaking_Extraction.md` | `TPOP-…` |

## The matrix at a glance

| Decision | Governs | Refines | Executed in |
| :--- | :--- | :--- | :--- |
| Intensity language — levels, zones and TSS classes | `coggan` | `coggan`, `cusick` | Zone tables |
| Athlete diagnosis — phenotype, strengths and limiters | `cusick` | `coggan`, `friel_tb` | Engine → #STATE |
| Season structure — periods and their order | `friel_tb` | `cusick`, `friel_hpc` | This doctrine |
| Training volume — annual and weekly hours | `friel_tb` | `friel_hpc` | This doctrine |
| Load progression — CTL ramp rate | `coggan` | `cusick` | Engine → #STATE |
| Threshold and sub-threshold progression | `cusick` | `friel_tb`, `friel_hpc`, `coggan` | This doctrine |
| Above-threshold interval design (VO2max, anaerobic) | `cusick` | `coggan` | This doctrine |
| Intensity distribution across the season | `cusick` | `coggan`, `friel_tb` | This doctrine |
| Testing — protocol and cadence | `coggan` | `cusick`, `friel_tb` | Engine → #STATE |
| Cost and benefit of a training emphasis | `cusick` | `friel_tb` | This doctrine |
| Peak phase and taper | `mujika` | `friel_tb`, `cusick`, `coggan` | Config (decision_thresholds.yaml) |
| Race power and pacing | `cusick` | `coggan`, `friel_tb` | This doctrine |
| Weekly hours below what the plan needs | `friel_tb` | `cusick` | This doctrine |

---

## Intensity language — levels, zones and TSS classes

*Executed in: Zone tables*

**Governs — Hunter Allen, Andrew Coggan & Stephen McGregor.** Coggan Classic Levels 1-7 as % of FTP are the common language for every cycling prescription and for TSS. Levels are continuous; boundaries are not physiological walls. [`TRPM-C06-001`, `TRPM-C04-012`]

- **Refines — Hunter Allen, Andrew Coggan & Stephen McGregor.** Above Level 4, individualized levels (iLevels) from the power-duration model replace fixed percentages for riders who do not fit the classic levels; at and below Level 4 classic and individual levels coincide. Sweet spot (Level 4a) is kept as its own band. [`TRPM-C06-005`, `TRPM-C05-078`]
- **Refines — Tim Cusick.** iLevels describe training; they are the way to read time-in-zone across the whole curve. Classic levels, training targets and iLevels align as one ladder. [`WKOC-C05-019`, `WKOC-C06-019`]

## Athlete diagnosis — phenotype, strengths and limiters

*Executed in: Engine → #STATE*

**Governs — Tim Cusick.** Diagnose from the power-duration curve, not from a few test points: phenotype is the shape of the curve, not its height; read Pmax, FRC and FTP against reference bands, then strengths and limiters relative to the athlete's own average. [`WKOC-C07-001`, `WKOC-C04-003`, `WKOC-C05-015`]

- **Refines — Hunter Allen, Andrew Coggan & Stephen McGregor.** The Power Profile (5 s, 1 min, 5 min, FTP) ranks the athlete against standards and supplies the testing durations; the power-duration model is its continuous successor. [`TRPM-C07-005`, `TRPM-C04-022`, `TRPM-C02-010`]
- **Refines — Joe Friel.** A limiter is an ability the target race demands and the athlete lacks; limiters turn the diagnosis into training objectives. [`CTB-C05-063`, `CTB-C06-007`, `CTB-C08-016`]

## Season structure — periods and their order

*Executed in: This doctrine*

**Governs — Joe Friel.** Plan the season backward from the first A race with linear periodization as the default (Preparation, Base, Build, Peak, Race, Transition). Choose another model only with a reason that fits the athlete. [`CTB-C08-011`, `CTB-C08-020`, `CTB-C08-033`]

- **Refines — Tim Cusick.** Inside Friel's periods, stack the systems: chronic then acute aerobic work, extensive then intensive FTP building. When hours are capped, deepen the base (more time in zone) instead of stretching the cycles longer. [`WKOC-C08-010`, `WKOC-C08-015`, `WKOC-C08-016`]
- **Refines — Joe Friel.** The same six periods, with their purpose restated for the advanced rider. [`HPC-C05-058`]

## Training volume — annual and weekly hours

*Executed in: This doctrine*

**Governs — Joe Friel.** Set annual volume (hours or TSS) first, then read weekly hours per period from it. Weekly hours never exceed the athlete's declared availability. [`CTB-C08-017`, `CTB-C06-009`]

- **Refines — Joe Friel.** Suggested weekly riding hours by period for the advanced rider. [`HPC-C06-007`]

## Load progression — CTL ramp rate

*Executed in: Engine → #STATE*

**Governs — Hunter Allen, Andrew Coggan & Stephen McGregor.** Ramp CTL within the band for the athlete's training age and current CTL (long-term over 14-28 days; short-term over 7 days). A week or two at these rates requires a rest week afterward. [`TRPM-C06-019`, `TRPM-C06-018`]

- **Refines — Tim Cusick.** The same ramp bands, used as the main measure of volume uptake: aggressive early in base, managed in mid and late base. [`WKOC-C06-020`, `WKOC-C08-024`, `WKOC-C08-034`]

## Threshold and sub-threshold progression

*Executed in: This doctrine*

**Governs — Tim Cusick.** Decide for each session whether it builds extensively (same power, longer: time to exhaustion out) or intensively (more power: the curve up). Do not mix both in one session. FTP is built in phases, extensive before intensive. [`WKOC-C08-008`, `WKOC-C08-004`, `WKOC-C08-003`]

- **Refines — Joe Friel.** Muscular endurance is the ability this work develops in Friel's terms. [`CTB-C05-069`]
- **Refines — Joe Friel.** Time to exhaustion per zone is a moving target that follows fitness, fatigue and form. [`HPC-C04-007`]
- **Refines — Hunter Allen, Andrew Coggan & Stephen McGregor.** Sweet spot is the efficient band for extensive threshold work. [`TRPM-C05-078`]

## Above-threshold interval design (VO2max, anaerobic)

*Executed in: This doctrine*

**Governs — Tim Cusick.** Optimized intervals prescribe work from FTP to Pmax: rep length and power come from the athlete's own curve, so a more anaerobic rider does longer max aerobic reps. Round sensibly, and progress reps one step at a time. [`WKOC-C08-001`, `WKOC-C06-006`, `WKOC-C09-002`]

- **Refines — Hunter Allen, Andrew Coggan & Stephen McGregor.** Levels 5-7 name the target band and the expected adaptation. [`TRPM-C06-001`, `TRPM-C06-002`]

## Intensity distribution across the season

*Executed in: This doctrine*

**Governs — Tim Cusick.** Base moves from mostly easy volume to pyramidal (time between LT1 and LT2 grows). Polarized is a peak tool, effective for about 6-10 weeks. Events under about 4 hours peak polarized; longer events stay pyramidal with more Zone 1-2. [`WKOC-C08-036`, `WKOC-C08-039`, `WKOC-C08-042`]

- **Refines — Hunter Allen, Andrew Coggan & Stephen McGregor.** How time in each level is distributed across the season. [`TRPM-C11-006`]
- **Refines — Joe Friel.** Which abilities each period trains. [`CTB-C08-025`]

## Testing — protocol and cadence

*Executed in: Engine → #STATE*

**Governs — Hunter Allen, Andrew Coggan & Stephen McGregor.** FTP by the 20-minute protocol or the Power Profile test, repeated every 6-8 weeks in comparable conditions. [`TRPM-C07-004`, `TRPM-C07-005`, `TRPM-C07-002`]

- **Refines — Tim Cusick.** Testing is training: test in 4-6 week cycles, a full profile at the start of the season, and use unstructured testing to keep the curve current. [`WKOC-C09-012`]
- **Refines — Joe Friel.** Field-test options and where tests sit in the annual plan (recovery weeks). [`CTB-C07-002`, `CTB-C08-026`]

## Cost and benefit of a training emphasis

*Executed in: This doctrine*

**Governs — Tim Cusick.** Every emphasis gains somewhere and costs elsewhere; track the power-duration model across 4-week cycles and judge whether the cost is worth it for the target event. [`WKOC-C09-001`, `WKOC-C02-005`]

- **Refines — Joe Friel.** Training objectives follow the race's limiters, not the athlete's favourite strengths. [`CTB-C08-016`]

## Peak phase and taper

*Executed in: Config (decision_thresholds.yaml)*

**Governs — Iñigo Mujika.** Taper by cutting volume 21-60% (in cycling and running Bosquet found no clear cutoff inside that range; the pooled 41-60% optimum is driven by swimming), keeping intensity, and keeping frequency at or above about 80%, with a progressive reduction by default; two weeks is the default when the athlete's own response is unknown, and the taper is individualized. The numbers live in config/decision_thresholds.yaml (taper section). [`TPOP-C06-008`, `TPOP-C09-022`, `TPOP-C04-042`, `TPOP-C06-009`, `TPOP-C08-002`, `TPOP-C06-010`]

- **Refines — Joe Friel.** Taper workouts stay race-like, with frequent recovery; the Peak period sets its place in the season. [`CTB-C08-048`, `CTB-C08-049`, `CTB-C08-050`]
- **Refines — Tim Cusick.** The intensive peak block lasts 3-6 weeks and must progress (+1 each hard day); it only works on a solid aerobic foundation. [`WKOC-C08-040`, `WKOC-C08-041`]
- **Refines — Hunter Allen, Andrew Coggan & Stephen McGregor.** Target TSB for racing and how to time it for single or multiple peaks. [`TRPM-C06-020`, `TRPM-C08-007`, `TRPM-C08-006`]

## Race power and pacing

*Executed in: This doctrine*

**Governs — Tim Cusick.** Read the expected race duration on the power-duration curve for a starting power, and pace by segments of the course rather than one average. [`WKOC-C09-004`]

- **Refines — Hunter Allen, Andrew Coggan & Stephen McGregor.** Pacing with a power meter and race-file analysis. [`TRPM-C09-003`, `TRPM-C09-001`]
- **Refines — Joe Friel.** Pacing is emotional control; avoid early surging. [`CTB-C05-077`, `CTB-C02-008`]

## Weekly hours below what the plan needs

*Executed in: This doctrine*

**Governs — Joe Friel.** Keep the planned season volume and cap the weeks that exceed available time by shortening the longest sessions; as duration falls, intensity may rise by at most one zone in a few sessions. Never drop to a lower annual volume. The time-crunched mode (Carmichael) is a different thing and applies only when the head coach requests it. [`CTB-C08-036`]

- **Refines — Tim Cusick.** With capped hours, improve base quality instead of lengthening cycles. [`WKOC-C08-015`]
