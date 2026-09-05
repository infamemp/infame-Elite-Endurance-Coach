# STATE — AUTHORITATIVE

Athlete: Torres 10 (i180550)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** fresh
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB 15.7 falls in band 'fresh' (primary governor)
- Operational state: 'load_accepting'

Flags:
- ACWR 0.23 below the safe floor 0.8 — recent load is detraining relative to the base

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 36.8 / 21.1 / 15.7 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | -5.17 | pmc_series (daily wellness record) |
| HRV ratio | not available — only 0 HRV readings | — |
| ACWR | 0.23 — acute 58 vs chronic 248.5/wk | activity training_load, 7d vs 28d/4 |
| Durability | stable — median decoupling -1.0% over 6 sessions | activity decoupling, sessions of 45min or more |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 35.9 | 18.3 | 17.6 |
| 2026-09-12 | — | 30.4 | 6.7 | 23.7 |
| 2026-09-19 | — | 25.7 | 2.5 | 23.3 |
| 2026-09-26 | — | 21.8 | 0.9 | 20.9 |
| 2026-10-03 | — | 18.4 | 0.3 | 18.1 |
| 2026-10-10 | — | 15.6 | 0.1 | 15.5 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve anchors in watts. **Trend** compares the last 42 days against the last 90; **level** is where that sits against the best of the past year.

The windows are nested, so the yearly figure is a level reading only — a 42-day window has far fewer chances to record a maximum than a 12-month one, and the gap between them is not decline.

| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 5 | 480 | 480 | +0.0% | 593 | 81% | stable ·set in last 42d |
| 60 | 288 | 288 | +0.0% | 353 | 82% | stable ·set in last 42d |
| 300 | 259 | 259 | +0.0% | 274 | 94% | stable ·set in last 42d |
| 1200 | 223 | 223 | +0.0% | 228 | 98% | stable ·set in last 42d |
| 3600 | 185 | 185 | +0.0% | 211 | 88% | stable ·set in last 42d |

5/5 anchors were set within the last 42 days.
No data at: 7200

Curve shape:
- **glycolytic_bias** (60 over 1200): 1.291, shifted -16.6% vs 1y
- **aerobic_durability** (3600 over 300): 0.714, shifted -7.2% vs 1y
- **durability_gradient** (3600 over 1200): 0.83, shifted -10.4% vs 1y
- **anaerobic_reserve** (5 over 300): 1.853, shifted -14.4% vs 1y

**Durability:** stable, improving — median decoupling -1.0% recently vs 1.7% before (-2.7 points, 6 vs 6 sessions).
**Anaerobic depth:** maintained — peak W' depletion 100.0% recently vs 100.0% before; 4 of 99 sessions reached 80%.
  Note: 3 session(s) recorded depletion above 100% of W', which is not physically possible — the W' estimate has changed since. Clamped to 100%; the trend is directional, not exact.

**Adaptation state: plateau** — 5 of 5 anchors flat against 90d; aerobic end at 98% of the yearly best while the short end sits at 81% — top-end capacity is the gap, not aerobic fitness; closest to yearly best at 1200 (98%); durability stable and improving; anaerobic depth maintained.

### Suggested testing

These anchors sit far enough below the yearly best that the data cannot say whether the capacity dropped or simply was not probed. Prescribe only the test that refreshes the anchor in question — not a full battery.

- **5** — at 81% of the yearly best (+0.0% vs 90d). 2 x 10s maximal sprint, flying start, full recovery between. Day 5 of the baseline week — always after a recovery day, never on accumulated fatigue.
- **60** — at 82% of the yearly best (+0.0% vs 90d). 1-minute maximal test from a rolling start, fully rested. Day 3 of the baseline week.

- Warm up thoroughly before any maximal effort
- Easy 45 minutes at low endurance, then cool down
- Separate maximal tests by at least one day, with an easy recovery day before the sprint test. Test efforts need not fall on the same day.

### Data quality

- **W' appears underestimated** — 3 session(s) recorded depletion above 100% of the configured W'. Every anaerobic reading derived from it is compressed. Refresh W' with a ramp or CP test, then update the athlete's sport settings in Intervals.icu.
- **Non-endurance sessions in the log** — 37 of 142 activities are 37 Swim. These carry no endurance load and are excluded from the curve, durability and repeatability analyses. No action needed — noted so the session counts read correctly.

### Power profile

Ranked against the Coggan power profile (men, 67.0 kg). Threshold taken from configured FTP.

| Duration | Watts | W/kg | Score | Category |
| :--- | ---: | ---: | ---: | :--- |
| 5s | 480 | 7.16 | 0 | below table floor — likely not a maximal effort |
| 1min | 288 | 4.3 | 0 | below table floor — likely not a maximal effort |
| 5min | 259 | 3.87 | 38 | moderate low |
| FT | 230 | 3.43 | 40 | moderate low |

**Phenotype: undetermined** — 5s, 1min sits below the table floor, which is under 'average untrained'. For a training athlete that means the effort was never made in this window, not that the capacity is absent. Phenotype cannot be read from an untested duration.

Day-2 test duration: **25 minutes** — all-rounder default — phenotype is unknown until the profile is tested, and the day-2 duration depends on it. Run the testing week at the default, then the phenotype resolves and later tests use its duration.

Scores are ordinal positions between the table's anchor rows, not true percentiles. Phenotype comes from the shape of the profile, never from one duration alone.
