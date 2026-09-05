# STATE — AUTHORITATIVE

Athlete: elias caballero (i347129)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** neutral
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB 4.9 falls in band 'neutral' (primary governor)
- Operational state: 'load_accepting'

Flags:
- ACWR 0.77 below the safe floor 0.8 — recent load is detraining relative to the base

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 55.3 / 50.5 / 4.9 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | -1.8 | pmc_series (daily wellness record) |
| HRV ratio | not available — only 0 HRV readings | — |
| ACWR | 0.77 — acute 321 vs chronic 419.5/wk | activity training_load, 7d vs 28d/4 |
| Durability | drifting — median decoupling 5.8% over 6 sessions | activity decoupling, sessions of 45min or more |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 54.0 | 43.8 | 10.2 |
| 2026-09-12 | — | 45.7 | 16.1 | 29.6 |
| 2026-09-19 | — | 38.7 | 5.9 | 32.8 |
| 2026-09-26 | — | 32.8 | 2.2 | 30.6 |
| 2026-10-03 | — | 27.7 | 0.8 | 26.9 |
| 2026-10-10 | — | 23.5 | 0.3 | 23.2 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve anchors in watts. **Trend** compares the last 42 days against the last 90; **level** is where that sits against the best of the past year.

The windows are nested, so the yearly figure is a level reading only — a 42-day window has far fewer chances to record a maximum than a 12-month one, and the gap between them is not decline.

| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 5 | 695 | 695 | +0.0% | 865 | 80% | stable ·set in last 42d |
| 60 | 291 | 299 | -2.7% | 360 | 81% | decline |
| 300 | 230 | 230 | +0.0% | 266 | 86% | stable ·set in last 42d |
| 1200 | 202 | 202 | +0.0% | 239 | 84% | stable ·set in last 42d |
| 3600 | 192 | 192 | +0.0% | 192 | 100% | stable ·set in last 42d |

4/5 anchors were set within the last 42 days.
No data at: 7200

Curve shape:
- **glycolytic_bias** (60 over 1200): 1.441, shifted -4.4% vs 1y
- **aerobic_durability** (3600 over 300): 0.835, shifted +15.7% vs 1y
- **durability_gradient** (3600 over 1200): 0.95, shifted +18.3% vs 1y
- **anaerobic_reserve** (5 over 300): 3.022, shifted -7.1% vs 1y

**Durability:** drifting, improving — median decoupling 5.8% recently vs 8.4% before (-2.7 points, 6 vs 6 sessions).
**Anaerobic depth:** not available — only 0 sessions with W' data (need 3)

**Adaptation state: plateau** — 4 of 5 anchors flat against 90d, 1 down (60); aerobic end at 100% of the yearly best while the short end sits at 80% — top-end capacity is the gap, not aerobic fitness; closest to yearly best at 3600 (100%); durability drifting and improving.

### Suggested testing

These anchors sit far enough below the yearly best that the data cannot say whether the capacity dropped or simply was not probed. Prescribe only the test that refreshes the anchor in question — not a full battery.

- **5** — at 80% of the yearly best (+0.0% vs 90d). 2 x 10s maximal sprint, flying start, full recovery between. Day 5 of the baseline week — always after a recovery day, never on accumulated fatigue.
- **60** — at 81% of the yearly best (-2.7% vs 90d). 1-minute maximal test from a rolling start, fully rested. Day 3 of the baseline week.
- **1200** — at 84% of the yearly best (+0.0% vs 90d). Maximal test of 20-30 minutes, duration set by phenotype: 20 min for a time trialist, 25 for an all-rounder or sprinter, 30 for a pursuiter. Day 2 of the baseline week, followed by easy 20 minutes at low endurance.

- Warm up thoroughly before any maximal effort
- Easy 45 minutes at low endurance, then cool down
- Separate maximal tests by at least one day, with an easy recovery day before the sprint test. Test efforts need not fall on the same day.

### Power profile

Ranked against the Coggan power profile (men, 95.3 kg). Threshold taken from configured FTP.

| Duration | Watts | W/kg | Score | Category |
| :--- | ---: | ---: | ---: | :--- |
| 5s | 695 | 7.29 | 0 | below table floor — likely not a maximal effort |
| 1min | 291 | 3.05 | 0 | below table floor — likely not a maximal effort |
| 5min | 230 | 2.41 | 7 | lowest |
| FT | 228 | 2.39 | 18 | average untrained |

**Phenotype: undetermined** — 5s, 1min sits below the table floor, which is under 'average untrained'. For a training athlete that means the effort was never made in this window, not that the capacity is absent. Phenotype cannot be read from an untested duration.

Day-2 test duration: **25 minutes** — all-rounder default — phenotype is unknown until the profile is tested, and the day-2 duration depends on it. Run the testing week at the default, then the phenotype resolves and later tests use its duration.

Scores are ordinal positions between the table's anchor rows, not true percentiles. Phenotype comes from the shape of the profile, never from one duration alone.
