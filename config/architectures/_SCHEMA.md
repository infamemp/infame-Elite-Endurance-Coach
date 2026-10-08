# Architecture library — schema and rules

## What this is
Each file in this folder is one **session architecture**: a shape a main set can
take, distilled from ~1,700 distinct MyWhoosh / Whatsonzwift workouts. An
architecture carries **no intensities and no absolute numbers**. Percent-of-FTP,
RPE, and TSS still come only from the athlete's assigned author zone table, per
the existing rule that workout libraries may supply ideas, never numbers.

An architecture answers three questions:
1. What does one work bout look like? (`rep_shape`)
2. How do bouts relate to each other across the set? (`set_shape`)
3. How is the athlete recovering between bouts? (`recovery`)

## Fields
- `name` — slug, matches the file name.
- `display_name` — human label.
- `frequency_in_corpus` — how many of the ~1,700 analyzed workouts had this as
  their primary main-set shape. Context only, not a ranking of value — never
  used to bias selection toward the most common shape, which is the opposite
  of the goal.
- `intent` — one paragraph: the physiological/tactical purpose of this shape,
  as opposed to a plain identical-interval set.
- `rep_shape` — the pattern inside one work bout (see `_SCHEMA.md` vocabulary
  below).
- `set_shape` — how bouts relate to each other: `identical`, `ladder_up`,
  `ladder_down`, `pyramid`, `progressive` (harder each rep), `regressive`
  (easier each rep), `single` (one bout only).
- `applicable_classes` — which physiological classes (from
  `config/tss_classes.yaml`) this architecture suits. An architecture is a
  shape; the class is still chosen by the coach/prompt per session.
- `disciplines` — which disciplines this shape fits without modification.
  `trainer` always applies. Outdoor road_bike/mtb keep their existing monotony
  exemption for recovery/endurance/tempo regardless of what's listed here.
- `progression_levers` — which knobs change this architecture week to week
  without changing its identity (see Progression below).
- `combinable` — `standalone`, `pre_fatigue` (used before the key work),
  `finisher` (used after it), or both. See Combinations below.
- `notes` — anything a coach should know before prescribing this (fatigue
  profile, equipment needs, athlete population).
- `category` — `aerobic` for the shapes of aerobic sessions (`steady_aerobic`,
  `aerobic_touches`, `rolling_aerobic`), `technique` for drill sessions; absent
  for the interval shapes. A technique session is never counted as aerobic
  variety. (v7.36)
- `on_request` — `true` when the shape is used only if the head coach or the
  athlete asks for it (`technique_drills`). (v7.36)
- `sources` — the Knowledge entries the shape rests on (KB entry IDs, or
  `<author> §N` for files in the older numbered format). Every ID must exist in
  `Knowledge/`; the tests check it. (v7.36)
- `example_shapes` — 1–3 structural illustrations using relative notation only
  (e.g. "3–5 × (work bout / recovery ≥ work duration)"), never % or absolute
  power. These exist to make the shape unambiguous, not to hand back numbers.

## Progression levers (shared vocabulary)
Only four levers exist. A week-to-week change should name one or two, not
invent a new one:
- `reps` — number of work bouts.
- `bout_duration` — length of each work bout.
- `recovery_duration` — length of recovery between bouts.
- `intensity` — how hard, resolved by the athlete's zone table, never a raw
  number here.

## Combinations
246 of the ~1,700 workouts chain two or more architectures in one main set.
This is not a new architecture — it's how the ones below get combined. Order
matters:
- **pre_fatigue**: an easier or shorter architecture placed before the key
  work, to blunt freshness (e.g. `sprints` before `sustained_effort`).
- **finisher**: placed after the key work, to add a stimulus once the athlete
  is already fatigued (e.g. `sprints` after `classic_intervals`).
See `_combinations.yaml` for the combination patterns actually observed.

## What is deliberately excluded
- Warm-up and cool-down shapes are not covered here; they are a separate,
  smaller gap already identified in the prompt.
- No file encodes a ranking of "creative" vs "boring" architectures. The
  picker's job (a separate, later piece of work) is to avoid repeating the
  same architecture recently, not to prefer rare ones for their own sake.

## Session class and touches (v7.36)
A session's class is the purpose the coach declares in `[Zone]`, not its
hardest step, in every class. Harder minutes inside it are its **touches**:
the validator lists them beside the class and warns (`CHK-PURPOSE`, never
blocks) only when most of the load sits in a harder class than the one
declared. No file here sets how many touches a session may carry or how hard
they may be. The Oct 2026 re-analysis of the 1,694 distinct library workouts:

| Session class | Sessions | With touches | Typical touch time |
| :--- | ---: | ---: | ---: |
| Aerobic (recovery, endurance) | 401 | 81% | a few minutes |
| Tempo | 456 | 81% | ~7 min |
| Sub-threshold (sweet spot) | 269 | 81% | ~5 min |
| Threshold | 212 | 67% | ~4 min |
| VO2max | 183 | 40% | ~1 min |
| Anaerobic | 137 | 22% | ~1 min |

Only 25 of the 401 aerobic sessions are one flat level with no touch and no
cadence work. All of this is context for the coach, not a target.
