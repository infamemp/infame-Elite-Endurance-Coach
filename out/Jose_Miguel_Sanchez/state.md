# STATE — AUTHORITATIVE

Athlete: José Miguel Sanchez (i181205)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** neutral
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB 9.4 falls in band 'neutral' (primary governor)
- Operational state: 'load_accepting'

Flags:
- Durability degraded: 2 of 6 sessions above 10% decoupling
- ACWR 0.6 below the safe floor 0.8 — recent load is detraining relative to the base

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 64.7 / 55.3 / 9.4 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | -5.37 | pmc_series (daily wellness record) |
| HRV ratio | 1.043 (normal) — 76.1 vs baseline 73.0 | wellness HRV, 7d mean vs 53d median |
| ACWR | 0.6 — acute 240 vs chronic 399.5/wk | activity training_load, 7d vs 28d/4 |
| Durability | degraded — median decoupling 1.6% over 6 sessions | activity decoupling, sessions of 45min or more |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 63.2 | 47.9 | 15.2 |
| 2026-09-12 | — | 53.5 | 17.6 | 35.8 |
| 2026-09-19 | — | 45.3 | 6.5 | 38.8 |
| 2026-09-26 | — | 38.3 | 2.4 | 35.9 |
| 2026-10-03 | — | 32.4 | 0.9 | 31.6 |
| 2026-10-10 | — | 27.5 | 0.3 | 27.1 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve anchors in watts. **Trend** compares the last 42 days against the last 90; **level** is where that sits against the best of the past year.

The windows are nested, so the yearly figure is a level reading only — a 42-day window has far fewer chances to record a maximum than a 12-month one, and the gap between them is not decline.

| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 5 | 301 | 377 | -20.2% | 411 | 73% | decline |
| 60 | 264 | 345 | -23.5% | 345 | 76% | decline |
| 300 | 225 | 262 | -14.1% | 262 | 86% | decline |
| 1200 | 225 | 225 | +0.0% | 225 | 100% | stable ·set in last 42d |
| 3600 | 224 | 224 | +0.0% | 224 | 100% | stable ·set in last 42d |

2/5 anchors were set within the last 42 days.
No data at: 7200

Curve shape:
- **glycolytic_bias** (60 over 1200): 1.173, shifted -23.5% vs 1y
- **aerobic_durability** (3600 over 300): 0.996, shifted +16.4% vs 1y
- **durability_gradient** (3600 over 1200): 0.996, shifted +0.0% vs 1y
- **anaerobic_reserve** (5 over 300): 1.338, shifted -14.7% vs 1y

**Durability:** degraded, improving — median decoupling 1.6% recently vs 5.5% before (-4.0 points, 6 vs 6 sessions).
**Anaerobic depth:** maintained — peak W' depletion 100.0% recently vs 100.0% before; 33 of 73 sessions reached 80%.
  Note: 28 session(s) recorded depletion above 100% of W', which is not physically possible — the W' estimate has changed since. Clamped to 100%; the trend is directional, not exact.

**Adaptation state: regression** — 3 of 5 anchors down against the 90d window; aerobic end at 100% of the yearly best while the short end sits at 73% — top-end capacity is the gap, not aerobic fitness; closest to yearly best at 1200 (100%); durability degraded and improving; anaerobic depth maintained.

### Suggested testing

These anchors sit far enough below the yearly best that the data cannot say whether the capacity dropped or simply was not probed. Prescribe only the test that refreshes the anchor in question — not a full battery.

- **5** — at 73% of the yearly best (-20.2% vs 90d). 2 x 10s maximal sprint, flying start, full recovery between. Day 5 of the baseline week — always after a recovery day, never on accumulated fatigue.
- **60** — at 76% of the yearly best (-23.5% vs 90d). 1-minute maximal test from a rolling start, fully rested. Day 3 of the baseline week.

- Warm up thoroughly before any maximal effort
- Easy 45 minutes at low endurance, then cool down
- Separate maximal tests by at least one day, with an easy recovery day before the sprint test. Test efforts need not fall on the same day.

### Data quality

- **W' appears underestimated** — 28 session(s) recorded depletion above 100% of the configured W'. Every anaerobic reading derived from it is compressed. Refresh W' with a ramp or CP test, then update the athlete's sport settings in Intervals.icu.
- **Non-endurance sessions in the log** — 2 of 122 activities are 2 Walk. These carry no endurance load and are excluded from the curve, durability and repeatability analyses. No action needed — noted so the session counts read correctly.

### Power profile

Ranked against the Coggan power profile (men, 84.0 kg). Threshold taken from configured FTP.

| Duration | Watts | W/kg | Score | Category |
| :--- | ---: | ---: | ---: | :--- |
| 5s | 301 | 3.58 | 0 | below table floor — likely not a maximal effort |
| 1min | 264 | 3.14 | 0 | below table floor — likely not a maximal effort |
| 5min | 225 | 2.68 | 13 | novice 1 |
| FT | 200 | 2.38 | 18 | average untrained |

**Phenotype: undetermined** — 5s, 1min sits below the table floor, which is under 'average untrained'. For a training athlete that means the effort was never made in this window, not that the capacity is absent. Phenotype cannot be read from an untested duration.

Day-2 test duration: **25 minutes** — all-rounder default — phenotype is unknown until the profile is tested, and the day-2 duration depends on it. Run the testing week at the default, then the phenotype resolves and later tests use its duration.

Scores are ordinal positions between the table's anchor rows, not true percentiles. Phenotype comes from the shape of the profile, never from one duration alone.
