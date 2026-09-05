# STATE — AUTHORITATIVE

Athlete: Rafa Diaz (i179435)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** neutral
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB 6.4 falls in band 'neutral' (primary governor)
- Operational state: 'load_accepting'

Flags:
- Durability degraded: 1 of 6 sessions above 10% decoupling
- ACWR 0.47 below the safe floor 0.8 — recent load is detraining relative to the base

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 24.6 / 18.2 / 6.4 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | -2.35 | pmc_series (daily wellness record) |
| HRV ratio | not available — only 0 HRV readings | — |
| ACWR | 0.47 — acute 80 vs chronic 171.2/wk | activity training_load, 7d vs 28d/4 |
| Durability | degraded — median decoupling 2.9% over 6 sessions | activity decoupling, sessions of 45min or more |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 24.0 | 15.8 | 8.2 |
| 2026-09-12 | — | 20.3 | 5.8 | 14.5 |
| 2026-09-19 | — | 17.2 | 2.1 | 15.1 |
| 2026-09-26 | — | 14.6 | 0.8 | 13.8 |
| 2026-10-03 | — | 12.3 | 0.3 | 12.0 |
| 2026-10-10 | — | 10.4 | 0.1 | 10.3 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve anchors in m/s. **Trend** compares the last 42 days against the last 90; **level** is where that sits against the best of the past year.

The windows are nested, so the yearly figure is a level reading only — a 42-day window has far fewer chances to record a maximum than a 12-month one, and the gap between them is not decline.

| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 400 | 3.2 | 3.7 | -12.9% | 8.9 | 36% | decline |
| 1000 | 3.2 | 3.6 | -11.5% | 6.5 | 49% | decline |
| 5000 | 2.7 | 3.0 | -9.0% | 3.2 | 85% | decline |
| 10000 | 2.5 | 2.9 | -14.3% | 2.9 | 86% | decline |
| 21097 | 2.4 | 2.4 | +0.0% | 2.4 | 100% | stable ·set in last 42d |

1/5 anchors were set within the last 42 days.
No data at: 3000

**Durability:** degraded, improving — median decoupling 2.9% recently vs 6.8% before (-3.9 points, 6 vs 6 sessions).
**Anaerobic depth:** maintained — peak W' depletion 100.0% recently vs 100.0% before; 29 of 46 sessions reached 80%.
  Note: 27 session(s) recorded depletion above 100% of W', which is not physically possible — the W' estimate has changed since. Clamped to 100%; the trend is directional, not exact.

**Adaptation state: regression** — 4 of 5 anchors down against the 90d window; closest to yearly best at 21097 (100%); durability degraded and improving; anaerobic depth maintained.

### Suggested testing

These anchors sit far enough below the yearly best that the data cannot say whether the capacity dropped or simply was not probed. Prescribe only the test that refreshes the anchor in question — not a full battery.

- **400** — at 36% of the yearly best (-12.9% vs 90d). 1-minute maximal effort from a FLYING start. Running power meters lag on a standing start, which corrupts the far left of the curve — Palladino recommends flying starts for short-duration testing.
- **1000** — at 49% of the yearly best (-11.5% vs 90d). 3-minute maximal effort, paced as evenly as possible. This is the SHORT leg of the CP test — always run before the long leg, never after.

- Warm up thoroughly before any maximal effort
- Easy 45 minutes at low endurance, then cool down
- Separate maximal tests by at least one day, with an easy recovery day before the sprint test. Test efforts need not fall on the same day.

### Data quality

- **W' appears underestimated** — 27 session(s) recorded depletion above 100% of the configured W'. Every anaerobic reading derived from it is compressed. Refresh W' with a ramp or CP test, then update the athlete's sport settings in Intervals.icu.
- **Non-endurance sessions in the log** — 34 of 118 activities are 34 Swim. These carry no endurance load and are excluded from the curve, durability and repeatability analyses. No action needed — noted so the session counts read correctly.
