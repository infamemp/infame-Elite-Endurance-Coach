# STATE — AUTHORITATIVE

Athlete: Joel Mendez Diez (i182252)
Resolved: 2026-09-04 · data fetched 2026-09-04

> This block is computed deterministically from Intervals.icu data and config/decision_thresholds.yaml. Do not recalculate or contradict these values. Prescribe on top of them.

## Resolved state

- **Load/recovery state:** functional_overreach
- **Operational state:** recovery_priority
- **Governing signal:** tsb

How it was resolved:
- TSB -23.9 falls in band 'functional_overreach' (primary governor)
- Operational state: 'recovery_priority'

Flags:
- Durability degraded: 1 of 6 sessions above 10% decoupling
- ACWR 1.45 above the safe ceiling 1.3 — load is ramping faster than the chronic base supports

## Signals

| Signal | Value | Source |
| :--- | :--- | :--- |
| CTL / ATL / TSB | 43.9 / 67.8 / -23.9 (as of 2026-09-04) | pmc_series (daily wellness record) |
| Ramp rate | 4.95 | pmc_series (daily wellness record) |
| HRV ratio | 0.944 (normal) — 43.4 vs baseline 46.0 | wellness HRV, 7d mean vs 53d median |
| ACWR | 1.45 — acute 589 vs chronic 407.0/wk | activity training_load, 7d vs 28d/4 |
| Durability | degraded — median decoupling 7.6% over 6 sessions | activity decoupling, sessions of 45min or more |

## PMC projection

Banister exponential, CTL tau 42d, ATL tau 7d. Horizon 42 days, 0 with planned load.

| Date | Planned load | CTL | ATL | TSB |
| :--- | ---: | ---: | ---: | ---: |
| 2026-09-05 | — | 42.9 | 58.8 | -15.9 |
| 2026-09-12 | — | 36.3 | 21.6 | 14.7 |
| 2026-09-19 | — | 30.7 | 8.0 | 22.8 |
| 2026-09-26 | — | 26.0 | 2.9 | 23.1 |
| 2026-10-03 | — | 22.0 | 1.1 | 20.9 |
| 2026-10-10 | — | 18.6 | 0.4 | 18.2 |

Caveat: Unplanned days are projected as zero load. With few planned sessions on the calendar this understates future CTL.

## Longitudinal performance

Curve anchors in watts. **Trend** compares the last 42 days against the last 90; **level** is where that sits against the best of the past year.

The windows are nested, so the yearly figure is a level reading only — a 42-day window has far fewer chances to record a maximum than a 12-month one, and the gap between them is not decline.

| Anchor | 42d | 90d | Trend | 1y best | Level | Reading |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 5 | 699 | 699 | +0.0% | 699 | 100% | stable ·set in last 42d |
| 60 | 357 | 362 | -1.4% | 407 | 88% | stable |
| 300 | 269 | 269 | +0.0% | 304 | 88% | stable ·set in last 42d |
| 1200 | 235 | 235 | +0.0% | 254 | 92% | stable ·set in last 42d |
| 3600 | 198 | 212 | -6.6% | 213 | 93% | decline |

3/5 anchors were set within the last 42 days.
No data at: 7200

Curve shape:
- **glycolytic_bias** (60 over 1200): 1.519, shifted -5.2% vs 1y
- **aerobic_durability** (3600 over 300): 0.736, shifted +5.1% vs 1y
- **durability_gradient** (3600 over 1200): 0.843, shifted +0.5% vs 1y
- **anaerobic_reserve** (5 over 300): 2.599, shifted +13.0% vs 1y

**Durability:** degraded, degrading — median decoupling 7.6% recently vs -1.4% before (+9.0 points, 6 vs 6 sessions).
**Anaerobic depth:** maintained — peak W' depletion 100.0% recently vs 100.0% before; 6 of 64 sessions reached 80%.
  Note: 4 session(s) recorded depletion above 100% of W', which is not physically possible — the W' estimate has changed since. Clamped to 100%; the trend is directional, not exact.

**Adaptation state: plateau** — 4 of 5 anchors flat against 90d, 1 down (3600); closest to yearly best at 5 (100%); durability degraded and degrading; anaerobic depth maintained.

### Data quality

- **W' appears underestimated** — 4 session(s) recorded depletion above 100% of the configured W'. Every anaerobic reading derived from it is compressed. Refresh W' with a ramp or CP test, then update the athlete's sport settings in Intervals.icu.
- **Non-endurance sessions in the log** — 83 of 173 activities are 42 Walk, 39 WeightTraining, 1 Swim, 1 Rowing. These carry no endurance load and are excluded from the curve, durability and repeatability analyses. No action needed — noted so the session counts read correctly.

### Power profile

Ranked against the Coggan power profile (men, 94.8 kg). Threshold taken from configured FTP.

| Duration | Watts | W/kg | Score | Category |
| :--- | ---: | ---: | ---: | :--- |
| 5s | 699 | 7.37 | 0 | below table floor — likely not a maximal effort |
| 1min | 357 | 3.77 | 0 | below table floor — likely not a maximal effort |
| 5min | 269 | 2.84 | 16 | average untrained |
| FT | 250 | 2.64 | 25 | novice 2 |

**Phenotype: undetermined** — 5s, 1min sits below the table floor, which is under 'average untrained'. For a training athlete that means the effort was never made in this window, not that the capacity is absent. Phenotype cannot be read from an untested duration.

Day-2 test duration: **25 minutes** — all-rounder default — phenotype is unknown until the profile is tested, and the day-2 duration depends on it. Run the testing week at the default, then the phenotype resolves and later tests use its duration.

Scores are ordinal positions between the table's anchor rows, not true percentiles. Phenotype comes from the shape of the profile, never from one duration alone.
