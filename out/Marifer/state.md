# STATE — AUTHORITATIVE

Athlete: Marifer (i250096)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** neutral
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB -4.0 falls in band 'neutral' (primary governor)
- Operational state: 'load_accepting'

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 22.6 / 26.5 / -4.0 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | 0.26 | pmc_series (daily wellness record) |
| HRV ratio | not available — only 0 HRV readings | — |
| ACWR | 1.08 — acute 164 vs chronic 152.2/wk | activity training_load, 7d vs 28d/4 |
| Durability | drifting — median decoupling 4.9% over 6 sessions | activity decoupling, sessions of 45min or more |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 22.1 | 23.0 | -0.9 |
| 2026-09-12 | — | 18.7 | 8.5 | 10.2 |
| 2026-09-19 | — | 15.8 | 3.1 | 12.7 |
| 2026-09-26 | — | 13.4 | 1.1 | 12.2 |
| 2026-10-03 | — | 11.3 | 0.4 | 10.9 |
| 2026-10-10 | — | 9.6 | 0.2 | 9.4 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve anchors in m/s. **Trend** compares the last 42 days against the last 90; **level** is where that sits against the best of the past year.

The windows are nested, so the yearly figure is a level reading only — a 42-day window has far fewer chances to record a maximum than a 12-month one, and the gap between them is not decline.

| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 400 | 3.2 | 8.9 | -64.3% | 8.9 | 36% | decline |
| 1000 | 3.2 | 3.2 | +0.0% | 3.2 | 100% | stable ·set in last 42d |
| 5000 | 2.8 | 2.8 | +0.0% | 2.8 | 100% | stable ·set in last 42d |
| 10000 | 2.6 | 2.6 | +0.0% | 2.6 | 98% | stable ·set in last 42d |

3/4 anchors were set within the last 42 days.
No data at: 3000, 21097

**Durability:** drifting, degrading — median decoupling 5.4% recently vs -4.9% before (+10.3 points, 5 vs 4 sessions).
**Anaerobic depth:** not available — only 0 sessions with W' data (need 3)

**Adaptation state: plateau** — 3 of 4 anchors flat against 90d, 1 down (400); closest to yearly best at 1000 (100%); durability drifting and degrading.

### Suggested testing

These anchors sit far enough below the yearly best that the data cannot say whether the capacity dropped or simply was not probed. Prescribe only the test that refreshes the anchor in question — not a full battery.

- **400** — at 36% of the yearly best (-64.3% vs 90d). 1-minute maximal effort from a FLYING start. Running power meters lag on a standing start, which corrupts the far left of the curve — Palladino recommends flying starts for short-duration testing.

- Warm up thoroughly before any maximal effort
- Easy 45 minutes at low endurance, then cool down
- Separate maximal tests by at least one day, with an easy recovery day before the sprint test. Test efforts need not fall on the same day.

### Data quality

- **Limited power coverage** — only 16 of 101 endurance sessions carry power data Curve and repeatability analysis will stay thin until more sessions are recorded with a power meter.
