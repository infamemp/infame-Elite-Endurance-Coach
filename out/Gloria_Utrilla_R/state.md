# STATE — AUTHORITATIVE

Athlete: Gloria Utrilla R (i174860)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** neutral
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB -1.5 falls in band 'neutral' (primary governor)
- Operational state: 'load_accepting'

Flags:
- Durability degraded: 5 of 6 sessions above 10% decoupling

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 10.7 / 12.3 / -1.5 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | -0.32 | pmc_series (daily wellness record) |
| HRV ratio | 0.968 (normal) — 51.3 vs baseline 53.0 | wellness HRV, 7d mean vs 53d median |
| ACWR | 1.12 — acute 61 vs chronic 54.5/wk | activity training_load, 7d vs 28d/4 |
| Durability | degraded — median decoupling 15.4% over 6 sessions | activity decoupling, sessions of 45min or more |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 10.4 | 10.7 | -0.2 |
| 2026-09-12 | — | 8.8 | 3.9 | 4.9 |
| 2026-09-19 | — | 7.5 | 1.4 | 6.0 |
| 2026-09-26 | — | 6.3 | 0.5 | 5.8 |
| 2026-10-03 | — | 5.4 | 0.2 | 5.2 |
| 2026-10-10 | — | 4.5 | 0.1 | 4.5 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve anchors in m/s. **Trend** compares the last 42 days against the last 90; **level** is where that sits against the best of the past year.

The windows are nested, so the yearly figure is a level reading only — a 42-day window has far fewer chances to record a maximum than a 12-month one, and the gap between them is not decline.

| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 400 | 2.3 | 3.5 | -36.2% | 3.6 | 63% | decline |
| 1000 | 2.1 | 3.5 | -39.8% | 3.5 | 60% | decline |
| 5000 | 1.9 | 2.0 | -7.4% | 2.0 | 93% | decline |

0/3 anchors were set within the last 42 days.
No data at: 3000, 10000, 21097

**Durability:** degraded, degrading — median decoupling 15.4% recently vs 9.6% before (+5.8 points, 6 vs 6 sessions).
**Anaerobic depth:** maintained — peak W' depletion 100.0% recently vs 100.0% before; 4 of 28 sessions reached 80%.
  Note: 4 session(s) recorded depletion above 100% of W', which is not physically possible — the W' estimate has changed since. Clamped to 100%; the trend is directional, not exact.

**Adaptation state: regression** — 3 of 3 anchors down against the 90d window; closest to yearly best at 5000 (93%); durability degraded and degrading; anaerobic depth maintained.

### Suggested testing

These anchors sit far enough below the yearly best that the data cannot say whether the capacity dropped or simply was not probed. Prescribe only the test that refreshes the anchor in question — not a full battery.

- **400** — at 63% of the yearly best (-36.2% vs 90d). 1-minute maximal effort from a FLYING start. Running power meters lag on a standing start, which corrupts the far left of the curve — Palladino recommends flying starts for short-duration testing.
- **1000** — at 60% of the yearly best (-39.8% vs 90d). 3-minute maximal effort, paced as evenly as possible. This is the SHORT leg of the CP test — always run before the long leg, never after.

- Warm up thoroughly before any maximal effort
- Easy 45 minutes at low endurance, then cool down
- Separate maximal tests by at least one day, with an easy recovery day before the sprint test. Test efforts need not fall on the same day.

### Data quality

- **W' appears underestimated** — 4 session(s) recorded depletion above 100% of the configured W'. Every anaerobic reading derived from it is compressed. Refresh W' with a ramp or CP test, then update the athlete's sport settings in Intervals.icu.
- **Non-endurance sessions in the log** — 2 of 71 activities are 2 Swim. These carry no endurance load and are excluded from the curve, durability and repeatability analyses. No action needed — noted so the session counts read correctly.
- **Limited power coverage** — only 28 of 69 endurance sessions carry power data Curve and repeatability analysis will stay thin until more sessions are recorded with a power meter.
