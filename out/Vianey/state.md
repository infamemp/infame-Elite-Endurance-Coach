# STATE — AUTHORITATIVE

Athlete: Vianey (i549015)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** neutral
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB 6.3 falls in band 'neutral' (primary governor)
- Operational state: 'load_accepting'

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 44.2 / 37.9 / 6.3 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | 1.81 | pmc_series (daily wellness record) |
| HRV ratio | not available — only 0 HRV readings | — |
| ACWR | 1.04 — acute 398 vs chronic 381.5/wk | activity training_load, 7d vs 28d/4 |
| Durability | not available — only 0 qualifying sessions | — |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 2 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | 26 | 43.8 | 36.3 | 7.5 |
| 2026-09-12 | — | 37.7 | 15.1 | 22.6 |
| 2026-09-19 | — | 31.9 | 5.6 | 26.3 |
| 2026-09-26 | — | 27.0 | 2.0 | 25.0 |
| 2026-10-03 | — | 22.9 | 0.8 | 22.1 |
| 2026-10-10 | — | 19.3 | 0.3 | 19.1 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve anchors in m/s. **Trend** compares the last 42 days against the last 90; **level** is where that sits against the best of the past year.

The windows are nested, so the yearly figure is a level reading only — a 42-day window has far fewer chances to record a maximum than a 12-month one, and the gap between them is not decline.

| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 400 | 10.3 | 400.0 | -97.4% | 400.0 | 3% | decline |
| 1000 | 9.5 | 1000.0 | -99.0% | 1000.0 | 1% | decline |
| 5000 | 3.1 | 5000.0 | -99.9% | 5000.0 | 0% | decline |
| 10000 | 3.0 | 10000.0 | -100.0% | 10000.0 | — | decline |
| 21097 | 2.9 | 21097.5 | -100.0% | 21097.5 | — | decline |

0/5 anchors were set within the last 42 days.
No data at: 3000

**Durability:** not available — only 0 qualifying sessions (need 6)
**Anaerobic depth:** not available — only 0 sessions with W' data (need 3)

**Adaptation state: regression** — 5 of 5 anchors down against the 90d window; closest to yearly best at 400 (3%).

### Suggested testing

These anchors sit far enough below the yearly best that the data cannot say whether the capacity dropped or simply was not probed. Prescribe only the test that refreshes the anchor in question — not a full battery.

- **400** — at 3% of the yearly best (-97.4% vs 90d). 1-minute maximal effort from a FLYING start. Running power meters lag on a standing start, which corrupts the far left of the curve — Palladino recommends flying starts for short-duration testing.
- **1000** — at 1% of the yearly best (-99.0% vs 90d). 3-minute maximal effort, paced as evenly as possible. This is the SHORT leg of the CP test — always run before the long leg, never after.
- **5000** — at 0% of the yearly best (-99.9% vs 90d). 20-minute maximal effort, or a 5k race run to duration rather than to distance. Palladino prefers races as CP surrogates because a race is more likely to produce a genuinely maximal effort than a solo test.
- **10000** — at 0% of the yearly best (-100.0% vs 90d). 40-45 minute maximal effort, or a 10k race. His preferred single-parameter input — the modified Riegel model works best in this duration range.
- **21097** — at 0% of the yearly best (-100.0% vs 90d). A maximal effort of 80-100 minutes, or a half marathon race.

- Warm up thoroughly before any maximal effort
- Easy 45 minutes at low endurance, then cool down
- Separate maximal tests by at least one day, with an easy recovery day before the sprint test. Test efforts need not fall on the same day.

### Data quality

- **Non-endurance sessions in the log** — 48 of 121 activities are 48 WeightTraining. These carry no endurance load and are excluded from the curve, durability and repeatability analyses. No action needed — noted so the session counts read correctly.
- **Limited power coverage** — only 0 of 73 endurance sessions carry power data Curve and repeatability analysis will stay thin until more sessions are recorded with a power meter.
