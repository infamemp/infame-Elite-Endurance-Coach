# Cycling Training Zones Reference Database (Standardized)

**How to read these tables (v7.2):**
- `Zone Key` and `Zone Name` preserve each author's own vocabulary.
- Values without a mark are the author's own numbers (native). Values marked `~` are ESTIMATES computed through `config/crosswalk.yaml` — from the author's native numbers, or, for an author who defines a zone by a race distance or a sustainable duration, from that anchor (`Anchor:` in the Notes; distances from Palladino's published table, durations from the Daniels-Gilbert model, about +/- 2 points). Use them when the athlete's metric is not one the author publishes. `N/A` means no estimate is meaningful (e.g. heart rate for efforts under ~2 minutes).
- Threshold (100%) is a band, not a point: authors place it anywhere from a ~30-minute effort to ~70 minutes, so every estimate carries about +/- 2-3 points of definitional uncertainty on top of the crosswalk error. `Borderline` in the Notes means the zone's midpoint is within 1 point of a class boundary.
- `Domain` is the physiological intensity domain (Moderate · Heavy · Severe · Extreme). `A→B` means the zone's range crosses from one domain into the next.
- `Class` determines TSS cost and is the only valid bridge between methodologies (never RPE). It is COMPUTED from the zone's position on the threshold scale, never assigned by hand; where the author explicitly states a different physiological target, the Notes say which one governs.
- `RPE` is the author's own scale (emit it as published). `~` RPE is the standard CR-10 reference for the class, used only where the author publishes none.
- Notation: ranges use `X–Y%` (en dash), open lower bound `< X%`, open upper bound `> X%`, undefined value `N/A`. Zones with an open lower bound are rendered from the prescription floor for that metric (see below), not from zero.

**GENERATED FILE — DO NOT EDIT.** Built 2026-09-26 by `build_zone_tables.py`.
If this date is older than your last change to `config/`, this file is stale —
run `python build_zone_tables.py build` and re-upload it to the Claude Project.
To change a zone, edit the YAML and rebuild. To add a methodology, copy
`config/authors/_template.yaml`, fill in the author's NATIVE values only, run
`validate`, then `build`. Hand edits here are lost on the next build.

**Output format — how these zones are written in Intervals.icu syntax:**

| Metric | Table column | Emitted in syntax as | Never use |
| :--- | :--- | :--- | :--- |
| % FTP | % FTP | `%` | `FTP`, `CP`, `W`, `watts` |
| % LTHR | % LTHR | `% LTHR` | `HR`, `HRmax`, `bpm` |
| % Threshold Pace | % Threshold Pace | `% Pace` | `min/km`, `min/mi`, `/km`, `/mile` |
| % HRmax | % HRmax | `never emitted — see Special Output Rule` | — |

The table columns below are documentation of where each zone lies. What is emitted in a workout block is the `Emitted in syntax as` form above — power (cycling or running) is a bare percentage with no metric suffix, and the `~` estimate mark is never written in syntax.

**Prescription floors.** Lowest intensity that may be prescribed for each metric: % FTP 25%, % LTHR 50%, % Threshold Pace 40%, % HRmax 40%. Zones whose source definition has an open lower bound are rendered from the floor rather than from zero, because a near-zero target cannot be steered by a device.

**Domains and classes — the standard every table below is resolved against:**

| Domain | Class | % FTP | % LTHR | Standard RPE | Sustainable | TSS/min |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Moderate | Recovery | < 55% | < 75% | 1–2 | indefinitely | 0.5 |
| Moderate | Endurance | 55–75% | 75–86.5% | 2–3 | hours | 1 |
| Heavy | Tempo | 75–88% | 86.5–93% | 3–4 | 2 to 3 hours | 1.2 |
| Heavy | Sub-threshold | 88–95% | 93–97% | 4–5 | 60 to 120 minutes | 1.35 |
| Heavy | Threshold | 95–101% | 97–100.5% | 6–7 | 40 to 70 minutes | 1.5 |
| Severe | Supra-threshold | 101–106% | 100.5–102.6% | 7–8 | 10 to 30 minutes | 1.65 |
| Severe | VO2max | 106–121% | ≥ 102.6% | 8–9 | 3 to 8 minutes | 1.8 |
| Extreme | Anaerobic | 121–150% | N/A | 9–10 | 30 seconds to 2 minutes | 2.1 |
| Extreme | Neuromuscular | ≥ 150% | N/A | 10 | under 20 seconds | 2.4 |

Bands on % FTP are the standard; the other columns are the same bands converted through the crosswalk. Heart rate cannot separate classes above ~102.6% LTHR (it lags and saturates), so those efforts are governed by power, pace or RPE.
The moderate/heavy boundary (LT1) is individual: on % FTP it lies between 70% and 80% for most athletes. Zones touching that band are flagged in their Notes.

---

## Methodology: Carmichael / CTS Cycling Zones
* **Sport:** Cycling
* **Zone Identifier Style:** Letter code (2–3 letters)
* **Default Metric:** % CTS Field Test
* **Native Metrics (author's own numbers):** % CTS Field Test, % LTHR
* **Primary Metrics:** CTS Field Test Power, CTS Field Test Heart Rate (LTHR)
* **Knowledge Base (Project file):** `Chris_Carmichael_Time_Crunched_Cyclist.md` (`Knowledge/Principles/Chris_Carmichael_Time_Crunched_Cyclist.md`)
* **Dual-Layer Required:** No
* **Note:** The anchor applies to POWER only. The field test heart rate anchor is the average HR of an 8-minute maximal effort, which already sits at LTHR — heart rate saturates near maximum where power does not. The % LTHR column is the author's, used verbatim, with no conversion.
* **Note:** Prescribe from the native column when the athlete has performed the CTS Field Test (protocol in the Carmichael knowledge base). Prescribe from the "% FTP (equivalent)" column when the athlete has only an FTP from a 20 or 60 minute test. Both routes reach the same absolute intensity.
* **Note:** The gap between EM (top 73% FTP) and Tempo (bottom 80% FTP), and the overlap between EM (up to 91% LTHR) and Tempo (88–90% LTHR), are confirmed intentional per the author (source: *The Time-Crunched Cyclist: Race*, Ch. 4 — narrow ranges are deliberate to improve target precision; EM's wide range is meant to be ridden mid-range, not maxed out). Not an error — do not "fix" by widening or narrowing adjacent zones.
* **Anchor:** CTS Field Test result — higher average of two 8-minute maximal efforts. This is NOT threshold — it sits 10% above it, so the % CTS Field Test column below is the author's own scale and cannot be read as a percentage of threshold.
* **% FTP (equivalent):** the author's percentages multiplied by 1.1. Use this column for an athlete who has a threshold value but has not performed the author's own test. Source: The Time-Crunched Cyclist, 3rd ed. 2017, Ch. 4 — "CTS Field Test avg power is approximately 10% above lab-tested LT power. This 10% is already factored into the Table 4.1 percentages."

| Zone Key | Zone Name | % CTS Field Test | % FTP (equivalent) | % LTHR | RPE (1-10) | Domain | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| EM | EnduranceMiles | 45–73% | 50–80% | 50–91% | 5 | Moderate→Heavy | Endurance | LT1 is individual: moderate or heavy depending on the athlete |
| T | Tempo | 80–85% | 88–94% | 88–90% | 6 | Heavy | Sub-threshold |  |
| SS | SteadyState | 86–90% | 95–99% | 92–94% | 7 | Heavy | Threshold |  |
| CR | ClimbingRepeat | 95–100% | 105–110% | 95–97% | 8 | Severe | VO2max | Author's stated target is Threshold; class follows the prescribed intensity |
| OU | OverUnder | N/A | N/A | N/A | 9 | Heavy | Threshold | Class from the author's stated physiological target; Alternating Under and Over. Under = SS, Over = CR. Native scale 86-90 and 95-100 % CTS Field Test; FTP equivalent 95-99 and 105-110 %. Heart rate 92-94 and 95-97 % LTHR. |
| PI | PowerInterval | > 101% | > 111% | > 100% | 10 | Severe | VO2max | Open-ended upward; Max effort; no defined upper bound |

---

## Methodology: Coggan Cycling Levels
* **Sport:** Cycling
* **Zone Identifier Style:** Level N
* **Default Metric:** % FTP
* **Native Metrics (author's own numbers):** % FTP, % LTHR
* **Primary Metrics:** Power, Functional Threshold Heart Rate (LTHR)
* **Knowledge Base (Project file):** `Allen - Coggan_Training_and_Racing_With_a_Powermeter.md` (`Knowledge/Principles/Allen - Coggan_Training_and_Racing_With_a_Powermeter.md`)
* **Dual-Layer Required:** No
* **Note:** FTHR = LTHR. Output as % LTHR in all Intervals.icu syntax.

| Zone Key | Zone Name | % FTP | % LTHR | RPE (1-10) | Domain | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Level 1 | Active Recovery | 25–55% | 50–68% | < 2 | Moderate | Recovery |  |
| Level 2 | Endurance | 56–75% | 69–83% | 2–3 | Moderate | Endurance | LT1 is individual: moderate or heavy depending on the athlete |
| Level 3 | Tempo | 76–90% | 84–94% | 3–4 | Heavy | Tempo | LT1 is individual: moderate or heavy depending on the athlete |
| Level 4 | Lactate Threshold | 91–105% | 95–105% | 4–5 | Heavy→Severe | Threshold |  |
| Level 5 | VO2max | 106–120% | > 106% | 6–7 | Severe | VO2max |  |
| Level 6 | Anaerobic Capacity | 121–150% | N/A | > 7 | Extreme | Anaerobic |  |
| Level 7 | Neuromuscular Power | N/A | N/A | Maximal | Extreme | Neuromuscular | Class from the author's stated physiological target |

---

## Methodology: Friel Cycling Zones
* **Sport:** Cycling
* **Zone Identifier Style:** Zone N (with sub-zone letters, e.g. "Zone 5 / 5a")
* **Default Metric:** % FTP
* **Native Metrics (author's own numbers):** % FTP, % LTHR
* **Primary Metrics:** Power, Functional Threshold Heart Rate (LTHR)
* **Knowledge Base (Project file):** `Joe_Friel_cyclists_training_bible_knowledge_base.md` (`Knowledge/Joe_Friel_cyclists_training_bible_knowledge_base.md`)
* **Dual-Layer Required:** No
* **Note:** FTHR = LTHR. Output as % LTHR in all Intervals.icu syntax.

| Zone Key | Zone Name | % FTP | % LTHR | RPE (1-10) | Domain | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Zone 1 | Active Recovery | 25–55% | 50–81% | 1–2 | Moderate | Recovery |  |
| Zone 2 | Endurance | 55–74% | 82–89% | 3–4 | Moderate | Endurance | LT1 is individual: moderate or heavy depending on the athlete |
| Zone 3 | Tempo | 75–89% | 90–93% | 5–6 | Heavy | Tempo | LT1 is individual: moderate or heavy depending on the athlete |
| Zone 4 | Lactate Threshold | 90–104% | 94–99% | 7 | Heavy→Severe | Threshold |  |
| Zone 5 / 5a | VO2max / Threshold Aerobic | 105–120% | 100–102% | 8 | Severe | VO2max |  |
| Zone 6 / 5b | Anaerobic Capacity | 121–150% | 103–106% | 9 | Extreme | Anaerobic |  |
| Zone 7 / 5c | Neuromuscular Power | > 150% | > 107% | 10 | Extreme | Neuromuscular |  |
