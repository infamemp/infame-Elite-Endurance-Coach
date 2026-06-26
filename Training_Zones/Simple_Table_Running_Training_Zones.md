# Running Training Zones Reference Database (Standardized)

This file contains standardized intensity training zones for running across major coaching and scientific methodologies (Daniels, Palladino, Friel, Koop, Olbrich). All methodologies follow a unified metadata and column schema to simplify adding new authors in the future.

**Schema notes:**
- `Zone Key` preserves each author's native zone identifier vocabulary (e.g. "Zone 1", letter codes, workout codes). Where the original methodology had no native code (Olbrich), a short code was derived from the zone name for schema consistency.
- `Pace Status` and `LTHR Status` in metadata indicate whether that metric is native to the methodology or a cross-referenced estimate.
- Notation: ranges use `X–Y%` (en dash), open lower bound `< X%`, open upper bound `> X%`, undefined value `N/A`.
- Compound or non-numeric details (e.g. physiological targets, variable-effort qualifiers) are captured in the `Notes` column rather than embedded in range cells.

**Schema Extension Rules (for adding new authors/methodologies):**
1. **Column inclusion is conditional on `Available Metrics`.** Only add a numeric range column for a metric if that metric is listed in the methodology's `Available Metrics` metadata field. Do not add empty or placeholder columns for metrics the author does not define.
2. **`Special Output Rule` (optional metadata field).** Use this field only when a methodology's native intensity metric must NOT be the metric used in Intervals.icu syntax output (see Olbrich: native % HRmax, output forced to Estimated % LTHR). State explicitly which metric is native and which metric must be output, and that the native metric must never appear in generated syntax. Omit this field entirely when no such substitution applies.
3. **`Dual-Layer Required` and `Special Output Rule` are independent fields** — a methodology may need one, both, or neither:
   - `Dual-Layer Required: Yes` → the athlete-facing intensity cue (e.g. RPE) differs from the engine-facing load metric (e.g. % LTHR), and both must be tracked side by side (see Koop).
   - `Special Output Rule` → the native metric is substituted entirely for a different output metric (see Olbrich).
   - A future author could require both simultaneously; the schema supports this without modification.
4. **RPE is not cross-author normalizable.** RPE (1–10) reflects each author's own perceived-exertion calibration, not a shared physiological anchor — the same training intensity can map to very different RPE values across authors (e.g. a Threshold-equivalent effort is RPE 4–5 in Daniels but RPE 8–9 in Koop). Only `% Threshold Pace`, `% LTHR`, and `% FTP/CP` (where applicable) are valid for cross-author comparison or normalization. Never use RPE as a bridge between methodologies.

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

| Zone Key | Zone Name | % Threshold Pace Range | % LTHR Range | RPE (1-10) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| E | Easy | 75–85% | 72–88% | 1–3 | |
| M | Marathon | 85–95% | 89–99% | 3–4 | |
| T | Threshold | 100% | 100% | 4–5 | |
| I | Interval | 105–115% | > 100% | 6–8 | |
| R | Repetition | 115–125% | N/A | 9–10 | |

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

| Zone Key | Zone Name | % FTP/CP Range | % Threshold Pace Range | % LTHR Range | RPE (1-10) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1A | Post Interval Recovery | 50–65% | 50–65% | < 75% | 1–2 | |
| 1B | EZ Warm-Up | 65–75% | 65–75% | 75–80% | 2 | |
| 1C | EZ Aerobic Running | 75–80% | 75–80% | 80–85% | 2–3 | |
| 2 | Endurance / Long Run | 80–88% | 80–88% | 85–89% | 3–4 | |
| 3A | Extensive Threshold Stimulus | 88–95% | 88–95% | 89–95% | 4–5 | |
| 3B | Intensive Threshold Stimulus | 95–101% | 95–101% | 95–100% | 5–6 | |
| 4 | Supra Threshold | 101–106% | 101–106% | > 100% | 7–8 | |
| 5 | Maximal Aerobic Power | 106–116% | 106–116% | > 100% | 8–9 | |
| 6 | Anaerobic Power | 116–150% | 116–150% | N/A | 9–10 | |
| 7 | Sprint / Maximal Power | > 150% | > 150% | N/A | 10 | |

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

| Zone Key | Zone Name | % Threshold Pace Range | % LTHR Range | RPE (1-10) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Zone 1 | Active Recovery | < 78% | < 85% | 1 | |
| Zone 2 | Endurance | 78–88% | 85–89% | 2–3 | |
| Zone 3 | Tempo | 88–94% | 90–94% | 4–5 | |
| Zone 4 | Lactate Threshold | 95–101% | 95–99% | 6–7 | |
| Zone 5a | Sub-Aerobic Threshold | 100–103% | 100–102% | 8 | |
| Zone 5b | Aerobic Capacity / VO2max | 104–111% | 103–106% | 9 | |
| Zone 5c | Anaerobic Capacity | > 111% | N/A | 10 | |

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

| Zone Key | Zone Name | % LTHR Range | RPE (1-10) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| RR | RecoveryRun | < 75% | 4–5 | Physiological target: Active Recovery |
| ER | EnduranceRun | 75–85% | 5–6 | Physiological target: Aerobic Endurance / "Forever" Pace |
| SSR | SteadyStateRun | 85–95% | 7–8 | Physiological target: High-End Aerobic |
| TR | TempoRun | 95–102% | 8–9 | Physiological target: Lactate Threshold |
| RI | RunningIntervals | > 102% | 9–10 | Physiological target: VO2 Max |

---

## Methodology: Olbrich Running Zones
* **Sport:** Running
* **Zone Identifier Style:** Descriptive name (no native code; codes below derived for schema consistency)
* **Default Metric:** % LTHR
* **Available Metrics:** % LTHR, % HRmax
* **Primary Metrics:** Maximum Heart Rate (HRmax), Estimated LTHR
* **Intensity Anchors:** % LTHR, % HRmax
* **LTHR Status:** Estimated
* **Dual-Layer Required:** No
* **Special Output Rule:** Native metric is % HRmax, but Intervals.icu syntax MUST use Estimated % LTHR per Olbrich Exception. Never output % HRmax in syntax.

| Zone Key | Zone Name | % LTHR Range | % HRmax Range | RPE (1-10) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| LRJ | Long recovery jog | < 80% | < 70% | 1–2 | |
| EER | Extensive endurance run | 85–90% | 75–80% | 2–3 | |
| IER | Intensive endurance run | 90–95% | 80–85% | 4–5 | |
| TER | Tempo endurance run | 95–100% | 85–90% | 6–7 | |
| INT | Interval | > 100% | > 90% | 8–10 | |
| FAR | Fartlek | 80–100% | 70–90% | 2–7 | Variable effort by design |
