# STATE — AUTHORITATIVE

Athlete: Michel Patjane (i18969)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** neutral
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB 2.6 falls in band 'neutral' (primary governor)
- Operational state: 'load_accepting'

Flags:
- Durability degraded: 1 of 3 sessions above 10% decoupling
- ACWR 0.0 below the safe floor 0.8 — recent load is detraining relative to the base

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 6.7 / 4.1 / 2.6 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | -0.54 | pmc_series (daily wellness record) |
| HRV ratio | 0.911 (normal) — 33.7 vs baseline 37.0 | wellness HRV, 7d mean vs 53d median |
| ACWR | 0.0 — acute 0 vs chronic 27.2/wk | activity training_load, 7d vs 28d/4 |
| Durability | degraded — median decoupling 6.7% over 3 sessions | activity decoupling, sessions of 45min or more |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 35 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | 22 | 7.1 | 6.5 | 0.6 |
| 2026-09-12 | 22 | 8.7 | 13.4 | -4.7 |
| 2026-09-19 | 22 | 10.7 | 18.9 | -8.2 |
| 2026-09-26 | 22 | 12.2 | 20.0 | -7.8 |
| 2026-10-03 | 22 | 13.7 | 21.4 | -7.7 |
| 2026-10-10 | 22 | 15.0 | 22.3 | -7.3 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve anchors in watts. **Trend** compares the last 42 days against the last 90; **level** is where that sits against the best of the past year.

The windows are nested, so the yearly figure is a level reading only — a 42-day window has far fewer chances to record a maximum than a 12-month one, and the gap between them is not decline.

| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 5 | 307 | 389 | -21.1% | 997 | 31% | decline |
| 60 | 258 | 310 | -16.8% | 530 | 49% | decline |
| 300 | 172 | 198 | -13.1% | 258 | 67% | decline |
| 1200 | 150 | 169 | -11.2% | 212 | 71% | decline |

0/4 anchors were set within the last 42 days.
No data at: 3600, 7200

Curve shape:
- **glycolytic_bias** (60 over 1200): 1.72, shifted -31.2% vs 1y
- **anaerobic_reserve** (5 over 300): 1.785, shifted -53.8% vs 1y

**Durability:** not available — only 3 qualifying sessions (need 6)
**Anaerobic depth:** declining — peak W' depletion 62.5% recently vs 100.0% before; 3 of 43 sessions reached 80%.
  Note: 2 session(s) recorded depletion above 100% of W', which is not physically possible — the W' estimate has changed since. Clamped to 100%; the trend is directional, not exact.

**Adaptation state: regression** — 4 of 4 anchors down against the 90d window; aerobic end at 71% of the yearly best while the short end sits at 31% — top-end capacity is the gap, not aerobic fitness; closest to yearly best at 1200 (71%); anaerobic depth declining.

### Suggested testing

These anchors sit far enough below the yearly best that the data cannot say whether the capacity dropped or simply was not probed. Prescribe only the test that refreshes the anchor in question — not a full battery.

- **5** — at 31% of the yearly best (-21.1% vs 90d). 2 x 10s maximal sprint, flying start, full recovery between. Day 5 of the baseline week — always after a recovery day, never on accumulated fatigue.
- **60** — at 49% of the yearly best (-16.8% vs 90d). 1-minute maximal test from a rolling start, fully rested. Day 3 of the baseline week.
- **300** — at 67% of the yearly best (-13.1% vs 90d). 5-minute maximal test. Day 1 of the baseline week — it opens the week because it is the least fatiguing of the long efforts and anchors VO2max.
- **1200** — at 71% of the yearly best (-11.2% vs 90d). Maximal test of 20-30 minutes, duration set by phenotype: 20 min for a time trialist, 25 for an all-rounder or sprinter, 30 for a pursuiter. Day 2 of the baseline week, followed by easy 20 minutes at low endurance.

- Warm up thoroughly before any maximal effort
- Easy 45 minutes at low endurance, then cool down
- Separate maximal tests by at least one day, with an easy recovery day before the sprint test. Test efforts need not fall on the same day.

### Data quality

- **W' appears underestimated** — 2 session(s) recorded depletion above 100% of the configured W'. Every anaerobic reading derived from it is compressed. Refresh W' with a ramp or CP test, then update the athlete's sport settings in Intervals.icu.
- **Non-endurance sessions in the log** — 4 of 51 activities are 4 Hike. These carry no endurance load and are excluded from the curve, durability and repeatability analyses. No action needed — noted so the session counts read correctly.

### Power profile

Ranked against the Coggan power profile (men, 81.5 kg). Threshold taken from configured FTP.

| Duration | Watts | W/kg | Score | Category |
| :--- | ---: | ---: | ---: | :--- |
| 5s | 307 | 3.77 | 0 | below table floor — likely not a maximal effort |
| 1min | 258 | 3.17 | 0 | below table floor — likely not a maximal effort |
| 5min | 172 | 2.11 | 4 | lowest |
| FT | 225 | 2.76 | 28 | novice 2 |

**Phenotype: undetermined** — 5s, 1min sits below the table floor, which is under 'average untrained'. For a training athlete that means the effort was never made in this window, not that the capacity is absent. Phenotype cannot be read from an untested duration.

Day-2 test duration: **25 minutes** — all-rounder default — phenotype is unknown until the profile is tested, and the day-2 duration depends on it. Run the testing week at the default, then the phenotype resolves and later tests use its duration.

Scores are ordinal positions between the table's anchor rows, not true percentiles. Phenotype comes from the shape of the profile, never from one duration alone.
