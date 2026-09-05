# STATE — AUTHORITATIVE

Athlete: Ranacleto (i194319)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** neutral
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB -1.7 falls in band 'neutral' (primary governor)
- Operational state: 'load_accepting'

Flags:
- ACWR 0.75 below the safe floor 0.8 — recent load is detraining relative to the base

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 51.0 / 52.7 / -1.7 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | -0.38 | pmc_series (daily wellness record) |
| HRV ratio | not available — only 0 HRV readings | — |
| ACWR | 0.75 — acute 322 vs chronic 429.5/wk | activity training_load, 7d vs 28d/4 |
| Durability | drifting — median decoupling 5.9% over 6 sessions | activity decoupling, sessions of 45min or more |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 49.8 | 45.7 | 4.1 |
| 2026-09-12 | — | 42.2 | 16.8 | 25.3 |
| 2026-09-19 | — | 35.7 | 6.2 | 29.5 |
| 2026-09-26 | — | 30.2 | 2.3 | 27.9 |
| 2026-10-03 | — | 25.6 | 0.8 | 24.7 |
| 2026-10-10 | — | 21.6 | 0.3 | 21.3 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve anchors in watts. **Trend** compares the last 42 days against the last 90; **level** is where that sits against the best of the past year.

The windows are nested, so the yearly figure is a level reading only — a 42-day window has far fewer chances to record a maximum than a 12-month one, and the gap between them is not decline.

| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 5 | 690 | 758 | -9.0% | 780 | 88% | decline |
| 60 | 399 | 421 | -5.2% | 436 | 92% | decline |
| 300 | 291 | 306 | -4.9% | 308 | 94% | decline |
| 1200 | 252 | 258 | -2.3% | 285 | 88% | stable |
| 3600 | 218 | 220 | -0.9% | 264 | 83% | stable |

0/5 anchors were set within the last 42 days.
No data at: 7200

Curve shape:
- **glycolytic_bias** (60 over 1200): 1.583, shifted +3.5% vs 1y
- **aerobic_durability** (3600 over 300): 0.749, shifted -12.6% vs 1y
- **durability_gradient** (3600 over 1200): 0.865, shifted -6.6% vs 1y
- **anaerobic_reserve** (5 over 300): 2.371, shifted -6.4% vs 1y

**Durability:** drifting, degrading — median decoupling 5.9% recently vs 2.1% before (+3.8 points, 6 vs 6 sessions).
**Anaerobic depth:** declining — peak W' depletion 68.0% recently vs 100.0% before; 7 of 81 sessions reached 80%.
  Note: 5 session(s) recorded depletion above 100% of W', which is not physically possible — the W' estimate has changed since. Clamped to 100%; the trend is directional, not exact.

**Adaptation state: regression** — 3 of 5 anchors down against the 90d window; closest to yearly best at 300 (94%); durability drifting and degrading; anaerobic depth declining.

### Suggested testing

These anchors sit far enough below the yearly best that the data cannot say whether the capacity dropped or simply was not probed. Prescribe only the test that refreshes the anchor in question — not a full battery.

- **3600** — at 83% of the yearly best (-0.9% vs 90d). 60-minute maximal effort, or a ramp test to refresh CP and W'. Substantial fatigue cost — schedule it deliberately, not casually.

- Warm up thoroughly before any maximal effort
- Easy 45 minutes at low endurance, then cool down
- Separate maximal tests by at least one day, with an easy recovery day before the sprint test. Test efforts need not fall on the same day.

### Data quality

- **W' appears underestimated** — 5 session(s) recorded depletion above 100% of the configured W'. Every anaerobic reading derived from it is compressed. Refresh W' with a ramp or CP test, then update the athlete's sport settings in Intervals.icu.

### Power profile

Ranked against the Coggan power profile (men, 90.5 kg). Threshold taken from configured FTP.

| Duration | Watts | W/kg | Score | Category |
| :--- | ---: | ---: | ---: | :--- |
| 5s | 690 | 7.62 | 0 | below table floor — likely not a maximal effort |
| 1min | 399 | 4.41 | 0 | below table floor — likely not a maximal effort |
| 5min | 291 | 3.22 | 25 | novice 2 |
| FT | 270 | 2.98 | 33 | fair |

**Phenotype: undetermined** — 5s, 1min sits below the table floor, which is under 'average untrained'. For a training athlete that means the effort was never made in this window, not that the capacity is absent. Phenotype cannot be read from an untested duration.

Day-2 test duration: **25 minutes** — all-rounder default — phenotype is unknown until the profile is tested, and the day-2 duration depends on it. Run the testing week at the default, then the phenotype resolves and later tests use its duration.

Scores are ordinal positions between the table's anchor rows, not true percentiles. Phenotype comes from the shape of the profile, never from one duration alone.
