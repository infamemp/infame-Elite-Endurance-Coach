# Roadmap — Infame Elite Endurance Coach

What comes next, in order. Replaces `IMPROVEMENT_BACKLOG.md` (v7.33); the old
backlog, with its full reasoning, is in the git history. Items move to
`CHANGELOG.md` when they ship.

## Next: the web interface (batch 7)

Built only on `services/` — the interface never reaches into `engine/` or
`mcp_server/` directly, so it and Claude always run the same rules.
Local, FastAPI + HTMX, one command to start.

1. **v1, read only.** The roster with load state, TSB, days since the last
   activity, next A race and pending reviews (`services.roster_overview`); the
   athlete page with `#STATE` as cards, the PMC chart and planned versus done
   (`services.athlete_state`, `services.execution`).
2. **v2, approvals.** Every saved week validated on screen
   (`services.validate(...)["summary"]`), the upload approved from its dry run
   (`services.push_block`), the declared profile edited in a form
   (`services.save_declared_profile`), and the ledger history
   (`services.ledger`).

Done when: save → validate → approve → upload is done with clicks, without
opening Claude for the mechanical part.

## Open items

- `push_block` does not delete workouts already planned on those dates that
  this system did not upload; the coach names them and the head coach removes
  them.
- `coach.py review` has no tool yet.
- `data/<id>/history/` has no retention limit.
- Target TSB ranges by event type are the coach's judgement, not a source:
  revisit them with real taper outcomes.

## Possible later

Worth building only when real use asks for it.

- **Prescribe toward a TSS target** — the engine proposes interval durations
  that land a session on its planned load.
- **W' reconstitution (Skiba)** for interval recovery durations.
- **Scenarios in the PMC projection** beyond `what_if_targets`.
- **Illness signature** — a sharp HRV drop with rising resting HR, flagged in
  `#STATE`.
- **Altitude and heat** as first-class variables.
- **Interval-level data** from structured sessions.
- **New methodologies:** Seiler (polarized distribution — needs a new kind of
  config, a distribution target), Pfitzinger, vertical work for trail,
  strength (needs its own config type). Check the author's anchor before
  adding any: `config/authors/_template.yaml`.
- **A scheduled morning fetch**, so `#STATE` is fresh before the first chat.

## Lines not to cross

- **The engine reports; the coach decides.** An engine that prescribes rather
  than reports would undo the architecture even if each step seemed
  reasonable. Uploading to Intervals.icu keeps two gates (`dry_run=False` and
  `confirm=True`) for the same reason.
- **Keep `#STATE` short.** What is only occasionally relevant belongs in a
  tool the coach calls on purpose, not in the block every conversation loads.
- **Read every golden diff** before `--update`. That is the whole value of the
  suite.
- **The Coggan power profile** ranks W/kg against road cyclists: it under-rates
  heavier and multisport athletes. The engine reports it; the coach gives the
  context.
