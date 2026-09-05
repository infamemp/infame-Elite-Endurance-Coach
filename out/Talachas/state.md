# STATE — AUTHORITATIVE

Athlete: Talachas (i321006)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** neutral
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB 0.0 falls in band 'neutral' (primary governor)
- Operational state: 'load_accepting'

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 0.0 / 0.0 / 0.0 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | 0.0 | pmc_series (daily wellness record) |
| HRV ratio | not available — only 0 HRV readings | — |
| ACWR | not available — no activities | — |
| Durability | not available — only 0 qualifying sessions | — |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 0.0 | 0.0 | 0.0 |
| 2026-09-12 | — | 0.0 | 0.0 | 0.0 |
| 2026-09-19 | — | 0.0 | 0.0 | 0.0 |
| 2026-09-26 | — | 0.0 | 0.0 | 0.0 |
| 2026-10-03 | — | 0.0 | 0.0 | 0.0 |
| 2026-10-10 | — | 0.0 | 0.0 | 0.0 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve progression: not available — no 42d curve data

**Durability:** not available — only 0 qualifying sessions (need 6)
**Anaerobic depth:** not available — only 0 sessions with W' data (need 3)
