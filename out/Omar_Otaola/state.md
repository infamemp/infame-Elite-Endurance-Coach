# STATE — AUTHORITATIVE

Athlete: Omar Otaola (i180398)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** neutral
- **Operational state:** load_accepting
- **Governing signal:** tsb

How it was resolved:
- TSB -3.6 falls in band 'neutral' (primary governor)
- Operational state: 'load_accepting'

Flags:
- ACWR 0.6 below the safe floor 0.8 — recent load is detraining relative to the base

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 12.5 / 16.1 / -3.6 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | -1.26 | pmc_series (daily wellness record) |
| HRV ratio | not available — only 0 HRV readings | — |
| ACWR | 0.6 — acute 95 vs chronic 157.8/wk | activity training_load, 7d vs 28d/4 |
| Durability | not available — only 1 qualifying sessions | — |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 12.2 | 14.0 | -1.8 |
| 2026-09-12 | — | 10.3 | 5.1 | 5.2 |
| 2026-09-19 | — | 8.7 | 1.9 | 6.9 |
| 2026-09-26 | — | 7.4 | 0.7 | 6.7 |
| 2026-10-03 | — | 6.3 | 0.3 | 6.0 |
| 2026-10-10 | — | 5.3 | 0.1 | 5.2 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve progression: not available — no 42d curve data

**Durability:** not available — only 1 qualifying sessions (need 6)
**Anaerobic depth:** maintained — peak W' depletion 100.0% recently vs 100.0% before; 3 of 6 sessions reached 80%.
  Note: 3 session(s) recorded depletion above 100% of W', which is not physically possible — the W' estimate has changed since. Clamped to 100%; the trend is directional, not exact.

### Data quality

- **W' appears underestimated** — 3 session(s) recorded depletion above 100% of the configured W'. Every anaerobic reading derived from it is compressed. Refresh W' with a ramp or CP test, then update the athlete's sport settings in Intervals.icu.
- **Non-endurance sessions in the log** — 47 of 145 activities are 37 WeightTraining, 5 Workout, 4 Walk, 1 Yoga. These carry no endurance load and are excluded from the curve, durability and repeatability analyses. No action needed — noted so the session counts read correctly.
- **Limited power coverage** — only 6 of 98 endurance sessions carry power data Curve and repeatability analysis will stay thin until more sessions are recorded with a power meter.
