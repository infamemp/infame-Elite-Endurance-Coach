# STATE — AUTHORITATIVE

Athlete: Alvaro Fernandez (i175069)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** neutral
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB 0.3 falls in band 'neutral' (primary governor)
- Operational state: 'load_accepting'

Flags:
- Durability degraded: 2 of 6 sessions above 10% decoupling

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 67.9 / 67.5 / 0.3 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | 1.9 | pmc_series (daily wellness record) |
| HRV ratio | not available — only 0 HRV readings | — |
| ACWR | 1.18 — acute 559 vs chronic 474.2/wk | activity training_load, 7d vs 28d/4 |
| Durability | degraded — median decoupling 8.4% over 6 sessions | activity decoupling, sessions of 45min or more |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 66.3 | 58.5 | 7.8 |
| 2026-09-12 | — | 56.1 | 21.5 | 34.6 |
| 2026-09-19 | — | 47.5 | 7.9 | 39.6 |
| 2026-09-26 | — | 40.2 | 2.9 | 37.3 |
| 2026-10-03 | — | 34.0 | 1.1 | 33.0 |
| 2026-10-10 | — | 28.8 | 0.4 | 28.4 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve anchors in watts. **Trend** compares the last 42 days against the last 90; **level** is where that sits against the best of the past year.

The windows are nested, so the yearly figure is a level reading only — a 42-day window has far fewer chances to record a maximum than a 12-month one, and the gap between them is not decline.

| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 5 | 865 | 938 | -7.8% | 1022 | 85% | decline |
| 60 | 466 | 472 | -1.3% | 496 | 94% | stable |
| 300 | 314 | 359 | -12.5% | 359 | 88% | decline |
| 1200 | 286 | 286 | +0.0% | 286 | 100% | stable ·set in last 42d |
| 3600 | 204 | 245 | -16.7% | 245 | 83% | decline |

1/5 anchors were set within the last 42 days.
No data at: 7200

Curve shape:
- **glycolytic_bias** (60 over 1200): 1.629, shifted -6.0% vs 1y
- **aerobic_durability** (3600 over 300): 0.65, shifted -4.8% vs 1y
- **durability_gradient** (3600 over 1200): 0.713, shifted -16.7% vs 1y
- **anaerobic_reserve** (5 over 300): 2.755, shifted -3.2% vs 1y

**Durability:** degraded, degrading — median decoupling 8.4% recently vs 1.4% before (+6.9 points, 6 vs 6 sessions).
**Anaerobic depth:** maintained — peak W' depletion 100.0% recently vs 99.1% before; 9 of 181 sessions reached 80%.
  Note: 2 session(s) recorded depletion above 100% of W', which is not physically possible — the W' estimate has changed since. Clamped to 100%; the trend is directional, not exact.

**Adaptation state: regression** — 3 of 5 anchors down against the 90d window; aerobic end at 100% of the yearly best while the short end sits at 85% — top-end capacity is the gap, not aerobic fitness; closest to yearly best at 1200 (100%); durability degraded and degrading; anaerobic depth maintained.

### Suggested testing

These anchors sit far enough below the yearly best that the data cannot say whether the capacity dropped or simply was not probed. Prescribe only the test that refreshes the anchor in question — not a full battery.

- **5** — at 85% of the yearly best (-7.8% vs 90d). 2 x 10s maximal sprint, flying start, full recovery between. Day 5 of the baseline week — always after a recovery day, never on accumulated fatigue.
- **3600** — at 83% of the yearly best (-16.7% vs 90d). 60-minute maximal effort, or a ramp test to refresh CP and W'. Substantial fatigue cost — schedule it deliberately, not casually.

- Warm up thoroughly before any maximal effort
- Easy 45 minutes at low endurance, then cool down
- Separate maximal tests by at least one day, with an easy recovery day before the sprint test. Test efforts need not fall on the same day.

### Data quality

- **W' appears underestimated** — 2 session(s) recorded depletion above 100% of the configured W'. Every anaerobic reading derived from it is compressed. Refresh W' with a ramp or CP test, then update the athlete's sport settings in Intervals.icu.

### Power profile

Ranked against the Coggan power profile (men, 71.0 kg). Threshold taken from configured FTP.

| Duration | Watts | W/kg | Score | Category |
| :--- | ---: | ---: | ---: | :--- |
| 5s | 865 | 12.18 | 22 | novice 2 |
| 1min | 466 | 6.56 | 24 | novice 2 |
| 5min | 314 | 4.42 | 45 | moderate |
| FT | 290 | 4.08 | 54 | good |

**Phenotype: time trialist** — threshold score 54 sits 32 points above 5s

Day-2 test duration: **20 minutes**.

Scores are ordinal positions between the table's anchor rows, not true percentiles. Phenotype comes from the shape of the profile, never from one duration alone.
