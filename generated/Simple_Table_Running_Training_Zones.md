# Running Training Zones Reference Database (Standardized)

**How to read these tables (v7.2):**
- `Zone Key` and `Zone Name` preserve each author's own vocabulary.
- Values without a mark are the author's own numbers (native). Values marked `~` are ESTIMATES computed through `config/crosswalk.yaml` from the author's native numbers — use them when the athlete's metric is not one the author publishes. `N/A` means the author publishes nothing there and no estimate is meaningful (e.g. heart rate for efforts under ~2 minutes).
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

| Domain | Class | % Threshold Pace | % LTHR | % FTP (run power) | Standard RPE | Sustainable | TSS/min |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Moderate | Recovery | < 75% | < 77% | < 75% | 1–2 | indefinitely | 0.5 |
| Moderate | Endurance | 75–85% | 77–88.3% | 75–85% | 2–3 | hours | 1 |
| Heavy | Tempo | 85–91.5% | 88.3–94% | 85–91.5% | 3–4 | 2 to 3 hours | 1.2 |
| Heavy | Sub-threshold | 91.5–97% | 94–98.2% | 91.5–97% | 4–5 | 60 to 120 minutes | 1.35 |
| Heavy | Threshold | 97–101% | 98.2–100.7% | 97–101% | 6–7 | 40 to 70 minutes | 1.5 |
| Severe | Supra-threshold | 101–106% | 100.7–103.7% | 101–106% | 7–8 | 10 to 30 minutes | 1.65 |
| Severe | VO2max | 106–115% | ≥ 103.7% | 106–115% | 8–9 | 3 to 8 minutes | 1.8 |
| Extreme | Anaerobic | 115–150% | N/A | 115–150% | 9–10 | 30 seconds to 2 minutes | 2.1 |
| Extreme | Neuromuscular | ≥ 150% | N/A | ≥ 150% | 10 | under 20 seconds | 2.4 |

Bands on % Threshold Pace are the standard; the other columns are the same bands converted through the crosswalk. Heart rate cannot separate classes above ~103.7% LTHR (it lags and saturates), so those efforts are governed by power, pace or RPE.
The moderate/heavy boundary (LT1) is individual: on % Threshold Pace it lies between 80% and 90% for most athletes. Zones touching that band are flagged in their Notes.

---

## Methodology: Daniels Running Zones
* **Sport:** Running
* **Zone Identifier Style:** Letter code
* **Default Metric:** % Threshold Pace
* **Native Metrics (author's own numbers):** % Threshold Pace, % HRmax
* **Estimated Metrics (`~`, computed through the crosswalk):** % LTHR, % FTP (run power)
* **Primary Metrics:** Lactate Threshold (LT) Pace (T-pace, from VDOT), Maximum Heart Rate (HRmax) — secondary, conditions-dependent
* **Dual-Layer Required:** No
* **Threshold on the author's HRmax scale:** 90% HRmax = 100% LTHR. Source: Daniels' Running Formula — master zone table: T = 85-88% VO2max, 88-92% HRmax (well-trained).
* **Note:** Pace is the operational primary signal; heart rate is secondary and conditions-dependent (Daniels: follow HR when the purpose is intensity, ignore it when the purpose is a specific speed). % HRmax is documentation only and is never emitted — the syntax uses the estimated % LTHR.

| Zone Key | Zone Name | % Threshold Pace | % LTHR | % FTP (run power) | % HRmax | RPE (1-10) | Domain | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| E | Easy | 75–85% | ~77–88% | ~75–85% | 65–79% | 1–3 | Moderate | Endurance | LT1 is individual: moderate or heavy depending on the athlete |
| M | Marathon | 85–95% | ~88–97% | ~85–95% | 80–89% | 3–4 | Heavy | Tempo | LT1 is individual: moderate or heavy depending on the athlete |
| T | Threshold | 100% | ~100% | ~100% | 88–92% | 4–5 | Heavy | Threshold |  |
| I | Interval | 105–115% | ~> 103% | ~105–115% | N/A | 6–8 | Severe | VO2max |  |
| R | Repetition | 115–125% | N/A | ~115–125% | N/A | 9–10 | Extreme | Anaerobic |  |

---

## Methodology: Friel Running Zones
* **Sport:** Running
* **Zone Identifier Style:** Zone N (with sub-zone letters, e.g. "Zone 5a")
* **Default Metric:** % Threshold Pace
* **Native Metrics (author's own numbers):** % Threshold Pace, % LTHR
* **Estimated Metrics (`~`, computed through the crosswalk):** % FTP (run power)
* **Primary Metrics:** Lactate Threshold (LT) Pace, Lactate Threshold Heart Rate (LTHR)
* **Dual-Layer Required:** No
* **Note:** Verified against Friel's published run zones (TrainingPeaks, "Joe Friel's Quick Guide to Setting Zones"). His pace zones are given as % of threshold pace TIME (e.g. Zone 2 = 114-129%); the values here are the same zones as % of threshold SPEED, the form Intervals.icu uses (Zone 2 = 78-88%).
* **Note:** This is the only author in the repository that publishes running pace and heart rate natively in the same table; the running pace-to-LTHR crosswalk is built from it.

| Zone Key | Zone Name | % Threshold Pace | % LTHR | % FTP (run power) | RPE (1-10) | Domain | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Zone 1 | Active Recovery | 40–78% | 50–85% | ~40–78% | 1 | Moderate | Recovery |  |
| Zone 2 | Endurance | 78–88% | 85–89% | ~78–88% | 2–3 | Moderate→Heavy | Endurance | LT1 is individual: moderate or heavy depending on the athlete |
| Zone 3 | Tempo | 88–94% | 90–94% | ~88–94% | 4–5 | Heavy | Tempo | LT1 is individual: moderate or heavy depending on the athlete |
| Zone 4 | Lactate Threshold | 95–101% | 95–99% | ~95–101% | 6–7 | Heavy | Threshold |  |
| Zone 5a | Sub-Aerobic Threshold | 100–103% | 100–102% | ~100–103% | 8 | Heavy→Severe | Supra-threshold |  |
| Zone 5b | Aerobic Capacity / VO2max | 104–111% | 103–106% | ~104–111% | 9 | Severe | VO2max |  |
| Zone 5c | Anaerobic Capacity | > 111% | > 106% | ~> 111% | 10 | Extreme | Anaerobic | Open-ended upward; Class as stated by the author (numbers alone compute a different class) |

---

## Methodology: Koop Running Workout Zones
* **Sport:** Ultrarunning / Running
* **Zone Identifier Style:** Letter code (workout code)
* **Default Metric:** RPE (workout-code specific)
* **Native Metrics (author's own numbers):** none — RPE and the physiological target of each zone
* **Estimated Metrics (`~`, computed through the crosswalk):** % Threshold Pace, % LTHR, % FTP (run power)
* **Primary Metrics:** Perceived Exertion, Physiological Adaptation Target
* **Dual-Layer Required:** Yes
* **Dual-Layer Engine:** % LTHR Range — feeds Intervals.icu load calculation
* **Dual-Layer Steering:** RPE per workout code — athlete reads on device
* **Note:** Koop also states each workout code as a fraction of VO2max (ER ~50-65%, SSR ~65-75%, TR ~75-85%, RI >= 90%). There is no %VO2max column in the standard tables, so those figures stay in his knowledge base.
* **Note:** Koop's RPE scale runs higher than the standard reference (RecoveryRun 4-5, EnduranceRun 5-6). His RPE is what is emitted; the difference is reported by the build as a warning, not corrected.

| Zone Key | Zone Name | % Threshold Pace | % LTHR | % FTP (run power) | RPE (1-10) | Domain | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| RR | RecoveryRun | ~40–75% | ~50–77% | ~40–75% | 4–5 | Moderate | Recovery | Class from the author's stated physiological target; Physiological target: Active Recovery |
| ER | EnduranceRun | ~75–85% | ~77–88% | ~75–85% | 5–6 | Moderate | Endurance | LT1 is individual: moderate or heavy depending on the athlete; Class from the author's stated physiological target; Physiological target: Aerobic Endurance / "Forever" Pace |
| SSR | SteadyStateRun | ~92–97% | ~94–98% | ~92–97% | 7–8 | Heavy | Sub-threshold | Class from the author's stated physiological target; Physiological target: High-End Aerobic |
| TR | TempoRun | ~97–101% | ~98–101% | ~97–101% | 8–9 | Heavy | Threshold | Class from the author's stated physiological target; Physiological target: Lactate Threshold |
| RI | RunningIntervals | ~106–115% | ~> 104% | ~106–115% | 9–10 | Severe | VO2max | Class from the author's stated physiological target; Physiological target: VO2 Max |

---

## Methodology: Olbrich Running Zones
* **Sport:** Ultramarathon / Running
* **Zone Identifier Style:** Descriptive name (no native code; codes below derived for schema consistency)
* **Default Metric:** % LTHR
* **Native Metrics (author's own numbers):** % HRmax
* **Estimated Metrics (`~`, computed through the crosswalk):** % Threshold Pace, % LTHR, % FTP (run power)
* **Primary Metrics:** Maximum Heart Rate (HRmax)
* **Dual-Layer Required:** No
* **Special Output Rule:** Native metric is % HRmax, but Intervals.icu syntax MUST use the estimated % LTHR per Olbrich Exception. Never output % HRmax in syntax.
* **Threshold on the author's HRmax scale:** 90% HRmax = 100% LTHR. Source: Ultramarathon Training (2012): tempo endurance run 85-90% HRmax for "threshold development" (Ch. 17.2); intervals "usually above the anaerobic threshold (>= 90% of max)" (Ch. 6.2.5).
* **Note:** Source: Wolfgang Olbrich, "Ultramarathon Training" (2012), Ch. 17.2 zone table. Olbrich is a German Athletics Federation licensed high-performance running coach; the methodology targets 100 km, 24-hour and multi-day racing, not shorter road distances.
* **Note:** The book defines zones in % HRmax only. The % LTHR column is computed from it with the author's own threshold point (90% HRmax, see hrmax_threshold_pct), which is why the Special Output Rule exists: HRmax is native but cannot be emitted, so syntax uses the estimated % LTHR.
* **Note:** Olbrich prefers heart rate over pace outright, on the grounds that terrain, temperature and weather change daily while heart rate does not lie.
* **Note:** The book carries an internal discrepancy on the long recovery jog: Ch. 6 gives 65-70% HRmax, Ch. 17.2 gives under 70%. The Ch. 17.2 value is used here as the plan-execution figure, per the knowledge base.
* **Note:** The gap between 70% and 75% HRmax is in the source: no zone covers it. Left as the author has it rather than closed artificially.

| Zone Key | Zone Name | % Threshold Pace | % LTHR | % FTP (run power) | % HRmax | RPE (1-10) | Domain | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| LRJ | Long recovery jog | ~40–76% | ~50–78% | ~40–76% | 40–70% | 1–2 | Moderate | Recovery |  |
| EER | Extensive endurance run | ~81–86% | ~83–89% | ~81–86% | 75–80% | 2–3 | Moderate→Heavy | Endurance | LT1 is individual: moderate or heavy depending on the athlete |
| IER | Intensive endurance run | ~86–92% | ~89–94% | ~86–92% | 80–85% | 4–5 | Heavy | Tempo | LT1 is individual: moderate or heavy depending on the athlete |
| TER | Tempo endurance run | ~92–100% | ~94–100% | ~92–100% | 85–90% | 6–7 | Heavy | Threshold | Class as stated by the author (numbers alone compute a different class) |
| INT | Interval | ~> 100% | ~> 100% | ~> 100% | > 90% | 8–10 | Severe | VO2max | Open-ended upward; Class as stated by the author (numbers alone compute a different class) |
| FAR | Fartlek | ~76–100% | ~78–100% | ~76–100% | 70–90% | 2–7 | Moderate→Heavy | Tempo | LT1 is individual: moderate or heavy depending on the athlete; Variable effort by design |

---

## Methodology: Palladino Running Power/Pace Zones
* **Sport:** Running
* **Zone Identifier Style:** Number with letter sub-zone (e.g. "1A", "3B")
* **Default Metric:** % FTP/CP
* **Native Metrics (author's own numbers):** % FTP/CP
* **Estimated Metrics (`~`, computed through the crosswalk):** % Threshold Pace, % LTHR
* **Primary Metrics:** Functional Threshold Power (FTP) / Critical Power (CP)
* **Dual-Layer Required:** No
* **Note:** Palladino states the intensity domain of his own zones: heavy >80% to ~100% (zones 2, 3A, 3B), severe >100% to ~116% (4, 5), extreme >116% (6, 7). His zone 2 (80-88%) is heavy by that statement while it computes as Endurance here; the table flags it as touching the LT1 band, where the domain depends on the athlete.

| Zone Key | Zone Name | % Threshold Pace | % LTHR | % FTP/CP | RPE (1-10) | Domain | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1A | Post Interval Recovery | ~50–65% | ~58–69% | 50–65% | 1–2 | Moderate | Recovery |  |
| 1B | EZ Warm-Up | ~65–75% | ~69–77% | 65–75% | 2 | Moderate | Recovery |  |
| 1C | EZ Aerobic Running | ~75–80% | ~77–83% | 75–80% | 2–3 | Moderate | Endurance |  |
| 2 | Endurance / Long Run | ~80–88% | ~83–91% | 80–88% | 3–4 | Moderate→Heavy | Endurance | LT1 is individual: moderate or heavy depending on the athlete |
| 3A | Extensive Threshold Stimulus | ~88–95% | ~91–97% | 88–95% | 4–5 | Heavy | Sub-threshold |  |
| 3B | Intensive Threshold Stimulus | ~95–101% | ~97–101% | 95–101% | 5–6 | Heavy | Threshold |  |
| 4 | Supra Threshold | ~101–106% | ~101–104% | 101–106% | 7–8 | Severe | Supra-threshold |  |
| 5 | Maximal Aerobic Power | ~106–116% | ~> 104% | 106–116% | 8–9 | Severe→Extreme | VO2max |  |
| 6 | Anaerobic Power | ~116–150% | N/A | 116–150% | 9–10 | Extreme | Anaerobic |  |
| 7 | Sprint / Maximal Power | ~> 150% | N/A | > 150% | 10 | Extreme | Neuromuscular |  |

---

## Methodology: Rosario / Fitzgerald Running Intensities
* **Sport:** Road running (5K to marathon and ultramarathon)
* **Zone Identifier Style:** Named intensity, anchored to sustainable duration rather than zone number
* **Default Metric:** % LTHR
* **Native Metrics (author's own numbers):** % HRmax
* **Estimated Metrics (`~`, computed through the crosswalk):** % Threshold Pace, % LTHR, % FTP (run power)
* **Primary Metrics:** Maximum Heart Rate (HRmax), Ventilatory Threshold reference points (VT1, VT2)
* **Dual-Layer Required:** No
* **Special Output Rule:** Native metric is % HRmax, but Intervals.icu syntax MUST use the estimated % LTHR per the Olbrich Exception (native % HRmax is never emitted in syntax). Never output % HRmax in syntax.
* **Threshold on the author's HRmax scale:** 92% HRmax = 100% LTHR. Source: Run Like a Pro (2022), Ch. 4: VT2 = 91-93% HRmax, "aligns closely with critical velocity (CV); running to exhaustion at CV usually lasts 20-30 min" (QR-3). Midpoint of the stated range.
* **Note:** This author defines intensity almost entirely by SUSTAINABLE DURATION (the fastest pace held for 6 min, 30 min, 1h, 2h, a race distance), not by a percentage table. Only two points carry a native number: VT1 (77-81% HRmax, the moderate/heavy boundary, QR-2) and VT2 (91-93% HRmax, the heavy/severe boundary, QR-3). Every other zone's class below is assigned from its stated duration against the sustainable-duration bands in config/tss_classes.yaml, not from a number the author gives — this is the coach's classification, not the author's own numeric claim, and it is marked as such in each zone's stated_class source.
* **Note:** Because most zones carry no native number, most rows below show N/A in every metric column: there is nothing to estimate from. This is a known limitation, not an error (see IMPROVEMENT_BACKLOG.md) — a future engine enhancement can read the athlete's own pace-duration curve from Intervals.icu (already fetched by fetch_athlete_data.py) to give each of these duration-anchored zones a real, athlete-specific number.
* **Note:** Population reference from the same source (QR-4/QR-5): ~80% of training time below VT1 (below ~82% HRmax) and ~20% at moderate+high combined, applied on weekly/monthly/yearly timescales — this is a training distribution, not a zone, and is not represented as a row here.
* **Note:** T-1/T-2/T-3 give three field tests to locate VT1/VT2 without a lab: a 6-minute all-out test (pace x0.65 = VT1), an HRmax test, and the Talk Test.

| Zone Key | Zone Name | % Threshold Pace | % LTHR | % FTP (run power) | % HRmax | RPE (1-10) | Domain | Class | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Easy | Easy | ~40–85% | ~50–88% | ~40–85% | 40–81% | < 4 | Moderate | Endurance | LT1 is individual: moderate or heavy depending on the athlete; Class as stated by the author (numbers alone compute a different class); Upper bound is the top of the author's own VT1 range (77-81% HRmax, "fitter runners are nearer the top"). |
| MP | Marathon Pace (MP) | N/A | N/A | N/A | N/A | ~3–4 | Heavy | Tempo | Class from the author's stated physiological target |
| SSP | Steady-State Pace (SSP) | N/A | N/A | N/A | N/A | ~4–5 | Heavy | Sub-threshold | Class from the author's stated physiological target |
| HMP | Half-Marathon Pace (HMP) | N/A | N/A | N/A | N/A | ~4–5 | Heavy | Sub-threshold | Class from the author's stated physiological target |
| LTP | Lactate-Threshold Pace (LTP) | N/A | N/A | N/A | N/A | ~6–7 | Heavy | Threshold | Class from the author's stated physiological target |
| 10KP | 10K Pace (10KP) | N/A | N/A | N/A | N/A | ~7–8 | Severe | Supra-threshold | Class from the author's stated physiological target |
| CV | Critical Velocity (CV) | ~98–102% | ~99–101% | ~98–102% | 91–93% | ~6–7 | Heavy→Severe | Threshold |  |
| HI | High Intensity (HI) | N/A | N/A | N/A | N/A | ~8–9 | Severe | VO2max | Class from the author's stated physiological target |
| 5KP | 5K Pace (5KP) | N/A | N/A | N/A | N/A | ~8–9 | Severe | VO2max | Class from the author's stated physiological target |
| MAS | Maximum Aerobic Speed (MAS) | N/A | N/A | N/A | N/A | ~8–9 | Severe | VO2max | Class from the author's stated physiological target |
| VHI | Very-High Intensity (VHI) | N/A | N/A | N/A | N/A | ~9–10 | Extreme | Anaerobic | Class from the author's stated physiological target |
