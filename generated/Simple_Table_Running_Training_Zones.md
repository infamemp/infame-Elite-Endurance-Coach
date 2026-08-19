# Running Training Zones Reference Database (Standardized)

**Schema notes:**
- `Zone Key` preserves each author's native zone identifier vocabulary (e.g. "Zone 1", "Level 1", letter codes).
- `Class` is the cross-author physiological class that determines TSS cost. It is the only valid bridge between methodologies.
- Metric status fields indicate whether a metric is native to that methodology or a cross-referenced estimate.
- Notation: ranges use `X–Y%` (en dash), open lower bound `< X%`, open upper bound `> X%`, undefined value `N/A`.
- Compound or non-numeric details are captured in the `Notes` column rather than embedded in range cells.
- Zones with an open lower bound in the source are rendered from the prescription floor for that metric (see below), not from zero.

**GENERATED FILE — DO NOT EDIT.**
This file is built from `config/authors/*.yaml` by `build_zone_tables.py`.
To change a zone, edit the YAML and rebuild. To add a methodology, copy
`config/authors/_template.yaml`, fill it in, run `validate`, then `build`.
Hand edits here are lost on the next build.

**Output format — how these zones are written in Intervals.icu syntax:**

| Metric | Table column | Emitted in syntax as | Never use |
| :--- | :--- | :--- | :--- |
| % FTP | % FTP | `%` | `FTP`, `CP`, `W`, `watts` |
| % LTHR | % LTHR | `% LTHR` | `HR`, `HRmax`, `bpm` |
| % Threshold Pace | % Threshold Pace | `% Pace` | `min/km`, `min/mi`, `/km`, `/mile` |
| % HRmax | % HRmax | `never emitted — see Special Output Rule` | — |

The table columns below are documentation of where each zone lies. What is emitted in a workout block is the `Emitted in syntax as` form above — power is a bare percentage with no metric suffix.

**Prescription floors.** Lowest intensity that may be prescribed for each metric: % FTP 25%, % LTHR 50%, % Threshold Pace 40%, % HRmax 40%. Zones whose source definition has an open lower bound are rendered from the floor rather than from zero, because a near-zero target cannot be steered by a device.

---

## Methodology: Daniels Running Zones
* **Sport:** Running
* **Zone Identifier Style:** Letter code
* **Default Metric:** % Threshold Pace
* **Available Metrics:** % Threshold Pace, % LTHR
* **Primary Metrics:** Lactate Threshold (LT) Pace, Lactate Threshold Heart Rate (LTHR)
* **Intensity Anchors:** % Threshold Pace, % LTHR
* **Pace Status:** Native
* **LTHR Status:** Estimated
* **Dual-Layer Required:** No

| Zone Key | Zone Name | % Threshold Pace Range | % LTHR Range | RPE (1-10) | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| E | Easy | 75–85% | 72–88% | 1–3 | Endurance |  |
| M | Marathon | 85–95% | 89–99% | 3–4 | Tempo |  |
| T | Threshold | 100% | 100% | 4–5 | Threshold |  |
| I | Interval | 105–115% | > 100% | 6–8 | VO2max |  |
| R | Repetition | 115–125% | N/A | 9–10 | Anaerobic |  |

---

## Methodology: Friel Running Zones
* **Sport:** Running
* **Zone Identifier Style:** Zone N (with sub-zone letters, e.g. "Zone 5a")
* **Default Metric:** % Threshold Pace
* **Available Metrics:** % Threshold Pace, % LTHR
* **Primary Metrics:** Lactate Threshold (LT) Pace, Lactate Threshold Heart Rate (LTHR)
* **Intensity Anchors:** % Threshold Pace, % LTHR
* **Pace Status:** Native
* **LTHR Status:** Native
* **Dual-Layer Required:** No

| Zone Key | Zone Name | % Threshold Pace Range | % LTHR Range | RPE (1-10) | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Zone 1 | Active Recovery | 40–78% | 50–85% | 1 | Recovery |  |
| Zone 2 | Endurance | 78–88% | 85–89% | 2–3 | Endurance |  |
| Zone 3 | Tempo | 88–94% | 90–94% | 4–5 | Tempo |  |
| Zone 4 | Lactate Threshold | 95–101% | 95–99% | 6–7 | Threshold |  |
| Zone 5a | Sub-Aerobic Threshold | 100–103% | 100–102% | 8 | VO2max |  |
| Zone 5b | Aerobic Capacity / VO2max | 104–111% | 103–106% | 9 | VO2max |  |
| Zone 5c | Anaerobic Capacity | > 111% | N/A | 10 | Anaerobic |  |

---

## Methodology: Koop Running Workout Zones
* **Sport:** Ultrarunning / Running
* **Zone Identifier Style:** Letter code (workout code)
* **Default Metric:** RPE (workout-code specific)
* **Available Metrics:** RPE, % LTHR
* **Primary Metrics:** Perceived Exertion, Physiological Adaptation Target
* **Intensity Anchors:** RPE, % LTHR
* **LTHR Status:** Estimated
* **Dual-Layer Required:** Yes
* **Dual-Layer Engine:** % LTHR Range — feeds Intervals.icu load calculation
* **Dual-Layer Steering:** RPE per workout code — athlete reads on device

| Zone Key | Zone Name | % LTHR Range | RPE (1-10) | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| RR | RecoveryRun | 50–75% | 4–5 | Recovery | Physiological target: Active Recovery |
| ER | EnduranceRun | 75–85% | 5–6 | Endurance | Physiological target: Aerobic Endurance / "Forever" Pace |
| SSR | SteadyStateRun | 85–95% | 7–8 | Sub-threshold | Physiological target: High-End Aerobic |
| TR | TempoRun | 95–102% | 8–9 | Threshold | Physiological target: Lactate Threshold |
| RI | RunningIntervals | > 102% | 9–10 | VO2max | Physiological target: VO2 Max |

---

## Methodology: Olbrich Running Zones
* **Sport:** Running
* **Zone Identifier Style:** Descriptive name (no native code; codes below derived for schema consistency)
* **Default Metric:** % LTHR
* **Available Metrics:** % LTHR, % HRmax
* **Primary Metrics:** Maximum Heart Rate (HRmax), Estimated LTHR
* **Intensity Anchors:** % LTHR, % HRmax
* **LTHR Status:** Estimated
* **HRmax Status:** Native
* **Dual-Layer Required:** No
* **Special Output Rule:** Native metric is % HRmax, but Intervals.icu syntax MUST use Estimated % LTHR per Olbrich Exception. Never output % HRmax in syntax.

| Zone Key | Zone Name | % LTHR Range | % HRmax Range | RPE (1-10) | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| LRJ | Long recovery jog | 50–80% | 40–70% | 1–2 | Recovery |  |
| EER | Extensive endurance run | 85–90% | 75–80% | 2–3 | Endurance |  |
| IER | Intensive endurance run | 90–95% | 80–85% | 4–5 | Sub-threshold |  |
| TER | Tempo endurance run | 95–100% | 85–90% | 6–7 | Threshold |  |
| INT | Interval | > 100% | > 90% | 8–10 | VO2max |  |
| FAR | Fartlek | 80–100% | 70–90% | 2–7 | Endurance | Variable effort by design |

---

## Methodology: Palladino Running Power/Pace Zones
* **Sport:** Running
* **Zone Identifier Style:** Number with letter sub-zone (e.g. "1A", "3B")
* **Default Metric:** % FTP/CP
* **Available Metrics:** % FTP/CP, % Threshold Pace, % LTHR
* **Primary Metrics:** Functional Threshold Power (FTP) / Critical Power (CP), LT Pace, LTHR
* **Intensity Anchors:** % FTP/CP, % Threshold Pace, % LTHR
* **Pace Status:** Estimated
* **LTHR Status:** Estimated
* **Dual-Layer Required:** No

| Zone Key | Zone Name | % FTP/CP Range | % Threshold Pace Range | % LTHR Range | RPE (1-10) | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1A | Post Interval Recovery | 50–65% | 50–65% | 50–75% | 1–2 | Recovery |  |
| 1B | EZ Warm-Up | 65–75% | 65–75% | 75–80% | 2 | Recovery |  |
| 1C | EZ Aerobic Running | 75–80% | 75–80% | 80–85% | 2–3 | Endurance |  |
| 2 | Endurance / Long Run | 80–88% | 80–88% | 85–89% | 3–4 | Endurance |  |
| 3A | Extensive Threshold Stimulus | 88–95% | 88–95% | 89–95% | 4–5 | Sub-threshold |  |
| 3B | Intensive Threshold Stimulus | 95–101% | 95–101% | 95–100% | 5–6 | Threshold |  |
| 4 | Supra Threshold | 101–106% | 101–106% | > 100% | 7–8 | VO2max |  |
| 5 | Maximal Aerobic Power | 106–116% | 106–116% | > 100% | 8–9 | VO2max |  |
| 6 | Anaerobic Power | 116–150% | 116–150% | N/A | 9–10 | Anaerobic |  |
| 7 | Sprint / Maximal Power | > 150% | > 150% | N/A | 10 | Neuromuscular |  |
