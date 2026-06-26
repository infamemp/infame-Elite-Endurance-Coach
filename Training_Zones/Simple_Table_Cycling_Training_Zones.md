# Cycling Training Zones Reference Database (Standardized)

This file contains standardized intensity training zones for cycling across major coaching methodologies (Friel, Coggan, Carmichael). All methodologies follow a unified metadata and column schema to simplify adding new authors in the future.

**Schema notes:**
- `Zone Key` preserves each author's native zone identifier vocabulary (e.g. "Zone 1", "Level 1", letter codes).
- `LTHR Status` in metadata indicates whether % LTHR is a native metric for that methodology or a cross-referenced estimate.
- Notation: ranges use `X–Y%` (en dash), open lower bound `< X%`, open upper bound `> X%`, undefined value `N/A`.
- Compound or non-numeric details (e.g. structured intervals, max-effort qualifiers) are captured in the `Notes` column rather than embedded in range cells.

**Schema Extension Rules (for adding new authors/methodologies):**
1. **Column inclusion is conditional on `Available Metrics`.** Only add a numeric range column for a metric if that metric is listed in the methodology's `Available Metrics` metadata field. Do not add empty or placeholder columns for metrics the author does not define.
2. **`Special Output Rule` (optional metadata field).** Use this field only when a methodology's native intensity metric must NOT be the metric used in Intervals.icu syntax output (see the Running Zones file's Olbrich methodology for a worked example: native % HRmax, output forced to Estimated % LTHR). State explicitly which metric is native and which metric must be output, and that the native metric must never appear in generated syntax. None of the current cycling authors (Friel, Coggan, Carmichael) require this field — all output natively as % FTP / % LTHR — so omit it unless a future author needs it.
3. **`Dual-Layer Required` and `Special Output Rule` are independent fields** — a methodology may need one, both, or neither:
   - `Dual-Layer Required: Yes` → the athlete-facing intensity cue (e.g. RPE) differs from the engine-facing load metric (e.g. % LTHR), and both must be tracked side by side (see the Running Zones file's Koop methodology for a worked example).
   - `Special Output Rule` → the native metric is substituted entirely for a different output metric (see Olbrich, as above).
   - A future cycling author could require either or both; the schema supports this without modification. None of the current 3 cycling authors need either field.
4. **RPE is not cross-author normalizable.** RPE (1–10) reflects each author's own perceived-exertion calibration, not a shared physiological anchor — the same training intensity can map to very different RPE values across authors (e.g. Lactate Threshold is RPE 7 in Friel's Zone 4 but RPE 4–5 in Coggan's Level 4, even though both target the same physiological intensity). Only `% FTP` and `% LTHR` are valid for cross-author comparison or normalization. Never use RPE as a bridge between methodologies.

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

| Zone Key | Zone Name | % FTP Range | % LTHR Range | RPE (1-10) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Zone 1 | Active Recovery | < 55% | < 81% | 1–2 | |
| Zone 2 | Endurance | 55–74% | 82–89% | 3–4 | |
| Zone 3 | Tempo | 75–89% | 90–93% | 5–6 | |
| Zone 4 | Lactate Threshold | 90–104% | 94–99% | 7 | |
| Zone 5 / 5a | VO2max / Threshold Aerobic | 105–120% | 100–102% | 8 | |
| Zone 6 / 5b | Anaerobic Capacity | 121–150% | 103–106% | 9 | |
| Zone 7 / 5c | Neuromuscular Power | > 150% | > 107% | 10 | |

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

| Zone Key | Zone Name | % FTP Range | % LTHR Range | RPE (1-10) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Level 1 | Active Recovery | < 55% | < 68% | < 2 | |
| Level 2 | Endurance | 56–75% | 69–83% | 2–3 | |
| Level 3 | Tempo | 76–90% | 84–94% | 3–4 | |
| Level 4 | Lactate Threshold | 91–105% | 95–105% | 4–5 | |
| Level 5 | VO2max | 106–120% | > 106% | 6–7 | |
| Level 6 | Anaerobic Capacity | 121–150% | N/A | > 7 | |
| Level 7 | Neuromuscular Power | N/A | N/A | Maximal | |

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

| Zone Key | Zone Name | % FTP Range | % LTHR Range | RPE (1-10) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| EM | EnduranceMiles | 45–73% | 50–91% | 5 | |
| T | Tempo | 80–85% | 88–90% | 6 | |
| SS | SteadyState | 86–90% | 92–94% | 7 | |
| CR | ClimbingRepeat | 95–100% | 95–97% | 8 | |
| OU | OverUnder | N/A | N/A | 9 | Structured as alternating Under (86–90% FTP / 92–94% LTHR) and Over (95–100% FTP / 95–97% LTHR) intervals |
| PI | PowerInterval | > 100% | 100%–Max | 10 | Max effort; no defined upper bound |
