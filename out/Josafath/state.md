# STATE — AUTHORITATIVE

Athlete: Josafath (i327889)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** fresh
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB 11.4 falls in band 'fresh' (primary governor)
- Operational state: 'load_accepting'

Flags:
- Durability degraded: 2 of 6 sessions above 10% decoupling
- ACWR 0.0 below the safe floor 0.8 — recent load is detraining relative to the base

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 12.1 / 0.6 / 11.4 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | -2.19 | pmc_series (daily wellness record) |
| HRV ratio | 1.071 (normal) — 105.0 vs baseline 98.0 | wellness HRV, 7d mean vs 37d median |
| ACWR | 0.0 — acute 0 vs chronic 33.8/wk | activity training_load, 7d vs 28d/4 |
| Durability | degraded — median decoupling 9.2% over 6 sessions | activity decoupling, sessions of 45min or more |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 11.8 | 0.5 | 11.3 |
| 2026-09-12 | — | 10.0 | 0.2 | 9.8 |
| 2026-09-19 | — | 8.5 | 0.1 | 8.4 |
| 2026-09-26 | — | 7.2 | 0.0 | 7.1 |
| 2026-10-03 | — | 6.1 | 0.0 | 6.1 |
| 2026-10-10 | — | 5.1 | 0.0 | 5.1 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve progression: not available — no 42d curve data

**Durability:** degraded, degrading — median decoupling 9.2% recently vs 8.1% before (+1.1 points, 6 vs 6 sessions).
**Anaerobic depth:** untested — peak W' depletion 17.9% recently vs 63.9% before; 0 of 22 sessions reached 80%.
  'untested' means no session reached the anaerobic depth threshold — it says nothing about capacity, only that capacity was not probed.

### Data quality

- **Non-endurance sessions in the log** — 45 of 73 activities are 37 Swim, 7 Hike, 1 WeightTraining. These carry no endurance load and are excluded from the curve, durability and repeatability analyses. No action needed — noted so the session counts read correctly.
