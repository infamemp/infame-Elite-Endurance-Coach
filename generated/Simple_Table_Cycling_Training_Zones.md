# Cycling Training Zones Reference Database (Standardized)

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

## Methodology: Carmichael / CTS Cycling Zones
* **Sport:** Cycling
* **Zone Identifier Style:** Letter code (2–3 letters)
* **Default Metric:** % FTP
* **Available Metrics:** % FTP, % LTHR
* **Primary Metrics:** CTS Field Test Power, CTS Field Test Heart Rate (LTHR)
* **Intensity Anchors:** % FTP, % LTHR
* **LTHR Status:** Native
* **Dual-Layer Required:** No
* **Note:** Use the athlete's provided FTP. If FTP is missing and athlete uses Carmichael methodology, suggest the CTS field test protocol from the Carmichael KB file.
* **Note:** The gap between EM (top 73% FTP) and Tempo (bottom 80% FTP), and the overlap between EM (up to 91% LTHR) and Tempo (88–90% LTHR), are confirmed intentional per the author (source: *The Time-Crunched Cyclist: Race*, Ch. 4 — narrow ranges are deliberate to improve target precision; EM's wide range is meant to be ridden mid-range, not maxed out). Not an error — do not "fix" by widening or narrowing adjacent zones.

| Zone Key | Zone Name | % FTP Range | % LTHR Range | RPE (1-10) | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| EM | EnduranceMiles | 45–73% | 50–91% | 5 | Endurance |  |
| T | Tempo | 80–85% | 88–90% | 6 | Tempo |  |
| SS | SteadyState | 86–90% | 92–94% | 7 | Sub-threshold |  |
| CR | ClimbingRepeat | 95–100% | 95–97% | 8 | Threshold |  |
| OU | OverUnder | N/A | N/A | 9 | Threshold | Structured as alternating Under (86–90% FTP / 92–94% LTHR) and Over (95–100% FTP / 95–97% LTHR) intervals |
| PI | PowerInterval | > 100% | > 100% | 10 | Supra-threshold | Max effort; no defined upper bound |

---

## Methodology: Coggan Cycling Levels
* **Sport:** Cycling
* **Zone Identifier Style:** Level N
* **Default Metric:** % FTP
* **Available Metrics:** % FTP, % LTHR
* **Primary Metrics:** Power, Functional Threshold Heart Rate (LTHR)
* **Intensity Anchors:** % FTP, % LTHR
* **LTHR Status:** Native
* **Dual-Layer Required:** No
* **Note:** FTHR = LTHR. Output as % LTHR in all Intervals.icu syntax.

| Zone Key | Zone Name | % FTP Range | % LTHR Range | RPE (1-10) | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Level 1 | Active Recovery | 25–55% | 50–68% | < 2 | Recovery |  |
| Level 2 | Endurance | 56–75% | 69–83% | 2–3 | Endurance |  |
| Level 3 | Tempo | 76–90% | 84–94% | 3–4 | Tempo |  |
| Level 4 | Lactate Threshold | 91–105% | 95–105% | 4–5 | Threshold |  |
| Level 5 | VO2max | 106–120% | > 106% | 6–7 | Supra-threshold |  |
| Level 6 | Anaerobic Capacity | 121–150% | N/A | > 7 | Supra-threshold |  |
| Level 7 | Neuromuscular Power | N/A | N/A | Maximal | Supra-threshold |  |

---

## Methodology: Friel Cycling Zones
* **Sport:** Cycling
* **Zone Identifier Style:** Zone N (with sub-zone letters, e.g. "Zone 5 / 5a")
* **Default Metric:** % FTP
* **Available Metrics:** % FTP, % LTHR
* **Primary Metrics:** Power, Functional Threshold Heart Rate (LTHR)
* **Intensity Anchors:** % FTP, % LTHR
* **LTHR Status:** Native
* **Dual-Layer Required:** No
* **Note:** FTHR = LTHR. Output as % LTHR in all Intervals.icu syntax.

| Zone Key | Zone Name | % FTP Range | % LTHR Range | RPE (1-10) | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Zone 1 | Active Recovery | 25–55% | 50–81% | 1–2 | Recovery |  |
| Zone 2 | Endurance | 55–74% | 82–89% | 3–4 | Endurance |  |
| Zone 3 | Tempo | 75–89% | 90–93% | 5–6 | Tempo |  |
| Zone 4 | Lactate Threshold | 90–104% | 94–99% | 7 | Threshold |  |
| Zone 5 / 5a | VO2max / Threshold Aerobic | 105–120% | 100–102% | 8 | Supra-threshold |  |
| Zone 6 / 5b | Anaerobic Capacity | 121–150% | 103–106% | 9 | Supra-threshold |  |
| Zone 7 / 5c | Neuromuscular Power | > 150% | > 107% | 10 | Supra-threshold |  |
