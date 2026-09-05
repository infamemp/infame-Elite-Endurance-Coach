# STATE — AUTHORITATIVE

Athlete: José Ángel Govela (i174628)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** neutral
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB 5.6 falls in band 'neutral' (primary governor)
- Operational state: 'load_accepting'

Flags:
- ACWR 0.77 below the safe floor 0.8 — recent load is detraining relative to the base

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 65.6 / 60.0 / 5.6 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | -1.85 | pmc_series (daily wellness record) |
| HRV ratio | 0.971 (normal) — 34.0 vs baseline 35.0 | wellness HRV, 7d mean vs 53d median |
| ACWR | 0.77 — acute 406 vs chronic 528.5/wk | activity training_load, 7d vs 28d/4 |
| Durability | drifting — median decoupling 3.2% over 6 sessions | activity decoupling, sessions of 45min or more |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 64.1 | 52.0 | 12.0 |
| 2026-09-12 | — | 54.2 | 19.1 | 35.1 |
| 2026-09-19 | — | 45.9 | 7.0 | 38.9 |
| 2026-09-26 | — | 38.9 | 2.6 | 36.3 |
| 2026-10-03 | — | 32.9 | 1.0 | 31.9 |
| 2026-10-10 | — | 27.8 | 0.4 | 27.5 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve anchors in watts. **Trend** compares the last 42 days against the last 90; **level** is where that sits against the best of the past year.

The windows are nested, so the yearly figure is a level reading only — a 42-day window has far fewer chances to record a maximum than a 12-month one, and the gap between them is not decline.

| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 5 | 493 | 498 | -1.0% | 748 | 66% | stable |
| 60 | 326 | 343 | -5.0% | 374 | 87% | decline |
| 300 | 221 | 236 | -6.4% | 280 | 79% | decline |
| 1200 | 202 | 202 | +0.0% | 233 | 87% | stable ·set in last 42d |
| 3600 | 185 | 185 | +0.0% | 191 | 97% | stable ·set in last 42d |

2/5 anchors were set within the last 42 days.
No data at: 7200

Curve shape:
- **glycolytic_bias** (60 over 1200): 1.614, shifted +0.5% vs 1y
- **aerobic_durability** (3600 over 300): 0.837, shifted +22.7% vs 1y
- **durability_gradient** (3600 over 1200): 0.916, shifted +11.7% vs 1y
- **anaerobic_reserve** (5 over 300): 2.231, shifted -16.5% vs 1y

**Durability:** drifting, improving — median decoupling 3.2% recently vs 6.0% before (-2.9 points, 6 vs 6 sessions).
**Anaerobic depth:** maintained — peak W' depletion 100.0% recently vs 100.0% before; 11 of 120 sessions reached 80%.
  Note: 7 session(s) recorded depletion above 100% of W', which is not physically possible — the W' estimate has changed since. Clamped to 100%; the trend is directional, not exact.

**Adaptation state: plateau** — 3 of 5 anchors flat against 90d, 2 down (60, 300); aerobic end at 97% of the yearly best while the short end sits at 66% — top-end capacity is the gap, not aerobic fitness; closest to yearly best at 3600 (97%); durability drifting and improving; anaerobic depth maintained.

### Suggested testing

These anchors sit far enough below the yearly best that the data cannot say whether the capacity dropped or simply was not probed. Prescribe only the test that refreshes the anchor in question — not a full battery.

- **5** — at 66% of the yearly best (-1.0% vs 90d). 2 x 10s maximal sprint, flying start, full recovery between. Day 5 of the baseline week — always after a recovery day, never on accumulated fatigue.
- **300** — at 79% of the yearly best (-6.4% vs 90d). 5-minute maximal test. Day 1 of the baseline week — it opens the week because it is the least fatiguing of the long efforts and anchors VO2max.

- Warm up thoroughly before any maximal effort
- Easy 45 minutes at low endurance, then cool down
- Separate maximal tests by at least one day, with an easy recovery day before the sprint test. Test efforts need not fall on the same day.

### Data quality

- **W' appears underestimated** — 7 session(s) recorded depletion above 100% of the configured W'. Every anaerobic reading derived from it is compressed. Refresh W' with a ramp or CP test, then update the athlete's sport settings in Intervals.icu.
- **Non-endurance sessions in the log** — 48 of 180 activities are 47 Yoga, 1 Hike. These carry no endurance load and are excluded from the curve, durability and repeatability analyses. No action needed — noted so the session counts read correctly.

### Power profile

Ranked against the Coggan power profile (men, 73.5 kg). Threshold taken from configured FTP.

| Duration | Watts | W/kg | Score | Category |
| :--- | ---: | ---: | ---: | :--- |
| 5s | 493 | 6.71 | 0 | below table floor — likely not a maximal effort |
| 1min | 326 | 4.44 | 0 | below table floor — likely not a maximal effort |
| 5min | 221 | 3.01 | 20 | average untrained |
| FT | 205 | 2.79 | 28 | novice 2 |

**Phenotype: undetermined** — 5s, 1min sits below the table floor, which is under 'average untrained'. For a training athlete that means the effort was never made in this window, not that the capacity is absent. Phenotype cannot be read from an untested duration.

Day-2 test duration: **25 minutes** — all-rounder default — phenotype is unknown until the profile is tested, and the day-2 duration depends on it. Run the testing week at the default, then the phenotype resolves and later tests use its duration.

Scores are ordinal positions between the table's anchor rows, not true percentiles. Phenotype comes from the shape of the profile, never from one duration alone.
