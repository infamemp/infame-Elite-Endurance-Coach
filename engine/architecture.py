"""
engine/architecture.py — Infame Elite Endurance Coach v7
=========================================================
Classifies one session's Main Set into an architecture family, from the
session's own written text alone -- no header, no author, no methodology
needed. Built for one purpose: answer "what did I already prescribe this
athlete recently, and in what shape" from the record Intervals.icu already
keeps (each event's own `description` field), so nothing has to be pasted
into continuity.md by hand to be checked.

The 14 families this file recognizes are the ones in
config/architectures/*.yaml, derived from a structural analysis of ~1,700
real MyWhoosh / Whatsonzwift workouts (see that folder's _SCHEMA.md). This
module does not read those YAML files -- it only needs to produce the same
`name` slugs, so the two stay in vocabulary lock-step by convention, not by
a runtime dependency.

Deliberately reuses `parse_block()` and `SUFFIX_TO_METRIC` from
verify/validate_block.py rather than writing a second parser for the same
syntax -- that parser is already the one thing in this repo tested against
193 real cases of exactly this text. This file adds only what that parser
does not do: turning its flat, mult-tagged step list into repeat units,
naming the shape those units form, and giving the shape an approximate
physiological class.

That class is deliberately approximate. A past session's `description` has
no [Methodology] header, so the author-specific zone table that would
normally classify it is unknown here -- only the generic cutpoints in
decision_thresholds.yaml are used. This is correct for grouping recent
architectures by rough class ("another VO2max session this week") but must
never be read as a number to prescribe from; #STATE and the active
author's zones remain the only authority for that, per <engine_contract>.

Known, accepted gaps in this first version (rare in the 14-family corpus,
each under 30 of ~1,700 real workouts -- revisit only if real use shows
they matter):
  - Cadence is not read from the step line, so `cadence_contrast` is never
    produced.
  - A ladder, pyramid, or progressive/regressive set written as separate
    single-effort lines (rather than wrapped in one `Nx` repeat) is read as
    several `sustained_effort` units in sequence, not as one of those three
    shapes. A true `Nx` repeat is unaffected -- this only misses a ladder
    written step-by-step outside any repeat.
  - `climb_simulation`, `progressive_intervals`, `pyramid` are consequently
    not produced by this version.
  - A "criss-cross" pattern (alternating high/low, both sides sub-threshold)
    has no architecture file of its own in config/architectures/ -- it is
    folded into `over_unders`, the nearest shape, rather than invented as an
    unreviewed 15th family.
  - A strictly monotonic multi-step rep (each step harder or easier than
    the last, no repetition) can match either `surges_on_base` or
    `hard_start_fading`'s detection; the surge check runs first and wins
    the tie. Both are rare in the corpus (128 and 19 of ~1,700), so this is
    left as a disclosed tie-break rather than a disambiguation worth the
    extra rule.
"""

import validate_block  # noqa: E402 -- sibling module; caller puts verify/ on sys.path

parse_block = validate_block.parse_block
SUFFIX_TO_METRIC = validate_block.SUFFIX_TO_METRIC


# ══════════════════════════════════════════════════════════════════
# EVENT TYPE -> SPORT
# Intervals.icu's own `type` string on the event, not this project's
# canonical discipline vocabulary (that only exists once a session has a
# written [Discipline] header, which a bare `description` never carries).
# Best-effort and intentionally short: an unrecognized type simply means no
# approximate class is reported, never a guess.
# ══════════════════════════════════════════════════════════════════

_CYCLING_TYPES = {"ride", "virtualride", "gravelride", "mtb",
                   "mountainbikeride", "ebikeride"}
_RUNNING_TYPES = {"run", "virtualrun", "trailrun"}


def _sport_from_type(event_type):
    t = (event_type or "").strip().lower()
    if t in _CYCLING_TYPES:
        return "cycling"
    if t in _RUNNING_TYPES:
        return "running"
    return None


# ══════════════════════════════════════════════════════════════════
# STEP -> UNIT
# parse_block() returns a flat list of steps, each already tagged with
# `mult` (its repeat count, 1 outside any repeat) and `section`. This turns
# consecutive Main Set steps sharing the same mult>1 into one repeat unit,
# and leaves every other step standing alone. Steps with no usable target
# (RPE-only prescription) are dropped here -- classifying them would be a
# guess, not a reading of what was written.
# ══════════════════════════════════════════════════════════════════

def _leaf(step):
    """One parse_block() step -> the small shape this module reasons about."""
    if step.get("freeride"):
        return {"k": "free", "d": step["secs"] or 0, "suffix": ""}
    lo, hi = step["pct"]
    return {"k": "ramp" if step["ramp"] else "steady",
            "d": step["secs"] or 0, "lo": lo, "hi": hi,
            "suffix": step.get("suffix", "")}


def _build_units(main_steps):
    units, i = [], 0
    while i < len(main_steps):
        s = main_steps[i]
        n = s["mult"]
        if n > 1:
            j = i
            while j < len(main_steps) and main_steps[j]["mult"] == n:
                j += 1
            units.append({"k": "repeat", "n": n,
                           "steps": [_leaf(x) for x in main_steps[i:j]]})
            i = j
        else:
            units.append(_leaf(s))
            i += 1
    return units


# ══════════════════════════════════════════════════════════════════
# SHAPE OF ONE UNIT
# ══════════════════════════════════════════════════════════════════

def _avg(s):
    return (s["lo"] + s["hi"]) / 2


def _mono(values, tol=2):
    if len(values) < 2:
        return "single"
    if max(values) - min(values) <= tol:
        return "constant"
    if all(a <= b for a, b in zip(values, values[1:])):
        return "up"
    if all(a >= b for a, b in zip(values, values[1:])):
        return "down"
    return "varied"


def _rep_pattern(leaves):
    """The shape of the work inside one rep -- a repeat's steps, or a lone
    unit read as a rep of one. Independent of the metric: it works on the
    written percentage alone, so power, %LTHR and %Pace all classify the
    same way (the coach's own convention already makes higher = harder in
    every metric it allows)."""
    ws = [s for s in leaves if s["k"] in ("steady", "ramp")]
    if not ws:
        return "endurance"
    if not any(max(s["lo"], s["hi"]) >= 76 for s in ws):
        return "endurance"
    if len(ws) == 1:
        s = ws[0]
        if s["k"] == "ramp":
            return "ramp up" if s["hi"] > s["lo"] else "ramp down"
        if max(s["lo"], s["hi"]) > 150 and s["d"] <= 30:
            return "sprint"
        return "steady"

    # Surge checked first: it is the more specific pattern -- a short, much
    # harder burst riding on a long, still-substantial base. Checking it
    # ahead of the generic alternation below matters because a base/burst
    # pair can otherwise also read as "two different levels alternating."
    base = [s for s in ws if max(s["lo"], s["hi"]) <= 95 and s["d"] >= 90]
    burst = [s for s in ws if max(s["lo"], s["hi"]) >= 115 and s["d"] <= 75]
    if base and burst and sum(s["d"] for s in base) >= 1.5 * sum(s["d"] for s in burst):
        return "surges on a base"

    a = [round(_avg(s)) for s in ws]
    # Two or more real-work levels, each clearly different from its
    # neighbor, alternating: over-under if either side reaches threshold,
    # criss-cross when both stay sub-threshold. Both map to the same
    # architecture file (see _DIRECT_FAMILY), so the distinction only
    # matters for the class estimate, not the label.
    if all(abs(a[i] - a[i + 1]) >= 6 for i in range(len(a) - 1)):
        return "over-under" if max(a) >= 100 else "criss-cross"

    m = _mono(a)
    if m == "up":
        return "stepped build"
    if m == "down":
        return "hard start, fading"
    return "free-form"


def _unit_info(u):
    """(rep_pattern, set_pattern, n_reps, work_leaf). work_leaf is the one
    leaf step whose target best represents the unit's work -- used only to
    look up an approximate class, never to prescribe from."""
    if u["k"] == "repeat":
        st = u["steps"]
        # A TRUE on/off pair -- the lower side is recovery (<=60%), so the
        # rep's shape is just the work step. When BOTH sides are real work
        # (over-unders, criss-cross, surges), fall through to the full
        # multi-step reading below instead -- stripping the lower side
        # there would erase exactly the pattern that makes it that shape.
        if (len(st) == 2 and st[0]["k"] in ("steady", "ramp")
                and st[1]["k"] in ("steady", "ramp")
                and min(_avg(st[0]), _avg(st[1])) <= 60):
            work, _rec = ((st[0], st[1]) if _avg(st[0]) >= _avg(st[1])
                          else (st[1], st[0]))
            return (_rep_pattern([work]),
                    "identical" if u["n"] > 1 else "single", u["n"], work)
        work = max((x for x in st if x["k"] in ("steady", "ramp")),
                   key=_avg, default=None)
        return (_rep_pattern(st), "identical" if u["n"] > 1 else "single",
                u["n"], work)
    if u["k"] in ("steady", "ramp"):
        return _rep_pattern([u]), "single", 1, u
    if u["k"] in ("free", "max"):
        return "test/free", "single", 1, u
    return "free-form", "single", 1, None


# rep_pattern -> architecture slug. Matches config/architectures/*.yaml's
# `name` field. None means "not one named architecture" -- a free-form or
# test/freeride unit, excluded from the record rather than mislabeled.
_DIRECT_FAMILY = {
    "over-under": "over_unders",
    "criss-cross": "over_unders",   # nearest shape; no dedicated file (see module docstring)
    "surges on a base": "surges_on_base",
    "sprint": "sprints",
    "ramp up": "single_ramp",
    "ramp down": "descending_ramp",
    "stepped build": "stepped_build",
    "hard start, fading": "hard_start_fading",
    "endurance": "endurance_cadence",
}


def _family(rep_pattern, set_pattern):
    if rep_pattern in _DIRECT_FAMILY:
        return _DIRECT_FAMILY[rep_pattern]
    if rep_pattern == "steady":
        return "classic_intervals" if set_pattern == "identical" else "sustained_effort"
    return None  # "test/free", "free-form"


def _load_of(u):
    """Approximate training load of one unit -- for picking which unit in a
    combined Main Set is the primary one, never for TSS (the engine's own
    normalized-power computation in verify/validate_block.py is authoritative
    for that)."""
    def leaves(x):
        if x["k"] == "repeat":
            for _ in range(x["n"]):
                for s in x["steps"]:
                    yield from leaves(s)
        else:
            yield x

    total = 0.0
    for s in leaves(u):
        if s["k"] in ("steady", "ramp"):
            mid = _avg(s) / 100
            if mid >= 0.76:
                total += mid * mid * s["d"]
    return total


# ══════════════════════════════════════════════════════════════════
# APPROXIMATE CLASS -- generic cutpoints only, see module docstring
# ══════════════════════════════════════════════════════════════════

def _class_from_cutpoints(mid, metric, sport, cutpoints):
    table = (cutpoints.get(sport) or {}).get(metric) or {}
    for cls, r in table.items():
        lo = r.get("min") or 0
        hi = r.get("max")
        if lo <= mid and (hi is None or mid < hi):
            return cls
    return None


# ══════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def _result(ok, reason, architecture=None, cls=None, combo=False, sequence=None):
    return {"ok": ok, "reason": reason, "architecture": architecture,
            "class": cls, "combo": combo, "sequence": sequence or []}


def classify_session(description, event_type=None, thresholds=None):
    """Classify one session's Main Set from its own written text.

    `description` -- the event's raw text (a Warmup / Main Set / Cooldown
    code block, with or without the fenced ```text wrapper).
    `event_type`  -- Intervals.icu's own event `type` (e.g. "Ride", "Run"),
    used only to pick which cutpoint table approximates the class.
    `thresholds`  -- the dict from decision_thresholds.yaml (verify.
    validate_block.load_thresholds_only()). Omit to skip class entirely.

    Returns a dict:
      ok           -- False when there is nothing classifiable: no text, a
                      rest day, a freeform note with no parsed Main Set step.
      reason       -- why, when ok is False. None otherwise.
      architecture -- the primary family's slug (matches a file name under
                      config/architectures/), or None if the one classifiable
                      unit is not a named architecture (e.g. a bare test).
      class        -- an approximate physiological class, or None. Never a
                      number to prescribe from -- see module docstring.
      combo        -- True when the Main Set combines more than one family.
      sequence     -- the distinct families in written order (one entry
                      when combo is False).
    """
    if not description or not description.strip():
        return _result(False, "no description text")

    steps, _findings = parse_block(description)
    # A distance step ("3km 85-95% Pace") has a target but no duration --
    # parse_block() reports its length as a distance, not seconds. Every
    # duration and load calculation here is seconds-based, so a distance
    # step is left out rather than counted as zero-length work. Excluding
    # it can leave a distance-only session with nothing classifiable; that
    # reads as "no classifiable step" (ok: False), never as a wrong shape.
    classifiable = [s for s in steps
                    if (s.get("pct") is not None or s.get("freeride"))
                    and (s.get("secs") is not None or s.get("freeride"))]
    if not classifiable:
        return _result(False, "no classifiable step")

    main_steps = [s for s in classifiable if s.get("section") == "main"]
    if main_steps:
        units = _build_units(main_steps)
    else:
        # No step declared section='main' -- true for the current
        # output_contract template, but real historical text (written
        # before that hard constraint, or edited by hand) sometimes never
        # names "Main Set" at all. Fall back to finding it by position
        # among every classifiable step: the run from the first to the
        # last unit that reaches a quarter of the session's peak load.
        all_units = _build_units(classifiable)
        all_loads = [_load_of(u) for u in all_units]
        if max(all_loads, default=0) == 0:
            return _result(True, None, architecture="endurance_cadence",
                            cls="endurance", combo=False,
                            sequence=["endurance_cadence"])
        top_i = all_loads.index(max(all_loads))
        thresh = 0.25 * all_loads[top_i]
        idx = [i for i, load in enumerate(all_loads) if load >= thresh]
        units = all_units[idx[0]:idx[-1] + 1]

    infos = [_unit_info(u) for u in units]
    loads = [_load_of(u) for u in units]

    fams = [_family(rp, sp) for rp, sp, _n, _work in infos]
    # A zero-load unit (an easy filler step sitting in the Main Set between
    # real work) is not itself a trained architecture -- it does not count
    # toward the sequence or make an otherwise single-architecture session
    # read as a combo.
    sequence = []
    for f, load in zip(fams, loads):
        if f and load > 0 and (not sequence or sequence[-1] != f):
            sequence.append(f)

    if max(loads, default=0) == 0:
        # Nothing in the Main Set reaches work intensity -- a legitimate
        # architecture (endurance_cadence), not "no Main Set."
        return _result(True, None, architecture="endurance_cadence",
                        cls="endurance", combo=False,
                        sequence=["endurance_cadence"])

    top = loads.index(max(loads))
    primary = fams[top]
    _rp, _sp, _n, work = infos[top]

    cls = None
    if work and thresholds:
        sport = _sport_from_type(event_type)
        if sport:
            metric = SUFFIX_TO_METRIC.get(work.get("suffix", ""), "power")
            cutpoints = thresholds.get("classification_cutpoints") or {}
            cls = _class_from_cutpoints(_avg(work), metric, sport, cutpoints)

    # The session's biggest single unit can itself be a real, deliberate
    # design that simply is not one of the 14 named shapes (a compound
    # block mixing several cadence and intensity changes, for instance).
    # That is a legitimate answer, distinct from "nothing to classify" --
    # ok stays True, but architecture is honestly None rather than a
    # smaller classifiable fragment standing in for what was actually the
    # main work.
    reason = None if primary else ("main work does not match a named "
                                    "architecture (complex or free-form)")
    return _result(True, reason, architecture=primary, cls=cls,
                    combo=len(sequence) > 1, sequence=sequence)


# ══════════════════════════════════════════════════════════════════
# STATE.MD SECTION -- one analyze()/render() pair, same shape as
# longitudinal.py and power_profile.py, so build_state.py wires this in
# the same two-line way it already wires those.
# ══════════════════════════════════════════════════════════════════

# The 14 architecture slugs in config/architectures/*.yaml, kept here as
# plain data so the frequency tally below can report a zero count for one
# that never appeared -- this module does not read those YAML files (see
# module docstring), so this list is kept in sync by convention, the same
# way _DIRECT_FAMILY's slugs already are.
ALL_ARCHITECTURES = [
    "classic_intervals", "sustained_effort", "endurance_cadence", "single_ramp",
    "surges_on_base", "sprints", "stepped_build", "hard_start_fading",
    "over_unders", "descending_ramp", "progressive_intervals", "cadence_contrast",
    "climb_simulation", "pyramid",
]


def frequency(rows):
    """How many times each architecture appears in `rows` (summarize_recent's
    output). A combo counts every shape in its sequence once each, not just
    the primary one -- a session that combines sprints with classic_intervals
    used both, and hiding the sprints because classic_intervals had the
    bigger load would understate exactly the thing this exists to reveal.

    Returns (counts, unused): `counts` is every architecture's tally,
    including zero; `unused` is the ones that never appeared, in their
    ALL_ARCHITECTURES order."""
    counts = {a: 0 for a in ALL_ARCHITECTURES}
    for r in rows:
        seq = r.get("sequence") or ([r["architecture"]] if r.get("architecture") else [])
        for a in seq:
            if a in counts:
                counts[a] += 1
    unused = [a for a in ALL_ARCHITECTURES if counts[a] == 0]
    return counts, unused


def summarize_recent(recent_sessions, thresholds):
    """Classify every one of the last ~8 weeks' events (fetch_athlete_data.
    fetch_recent_sessions()) into an architecture family. Never raises on a
    single bad session -- one unparseable entry is skipped, not fatal to the
    whole state build, exactly like every other signal in this module."""
    rows = []
    for s in recent_sessions or []:
        desc = (s.get("description") or "").strip()
        if not desc:
            continue  # rest day, or an event with nothing written on it
        try:
            r = classify_session(desc, event_type=s.get("type"), thresholds=thresholds)
        except Exception:
            continue
        if not r["ok"]:
            continue
        rows.append({"date": s.get("date"), "type": s.get("type"),
                     "architecture": r["architecture"], "class": r["class"],
                     "combo": r["combo"], "sequence": r["sequence"]})
    rows.sort(key=lambda x: x["date"] or "")
    return {"rows": rows}


def render(summary):
    rows = (summary or {}).get("rows") or []
    lines = ["## RECENT ARCHITECTURES (last 8 weeks, computed)", ""]
    if not rows:
        lines.append("No classifiable session found in the last 8 weeks.")
        return "\n".join(lines)
    lines += [
        "Read automatically from each session's own text already saved on "
        "Intervals.icu -- not a substitute for `Recent Architectures` in "
        "`continuity.md` when that is present and current; a backstop for "
        "when it is not, and a cross-check either way. Class is "
        "approximate (generic cutpoints, not the athlete's active author) "
        "-- for grouping only, never a number to prescribe from. A blank "
        "row is a session whose text did not parse into a named shape or "
        "had nothing to classify (a rest day, a bare imported ride).",
        "",
        "| Date | Type | Architecture | Approx. class |",
        "|:---|:---|:---|:---|",
    ]
    for r in rows:
        arch = " + ".join(r["sequence"]) if r["combo"] else (r["architecture"] or "_complex/free-form_")
        lines.append(f"| {r['date']} | {r['type'] or '-'} | {arch} | {r['class'] or '-'} |")

    counts, unused = frequency(rows)
    lines += [
        "",
        "**Architecture frequency in this window** (a combo counts every "
        "shape it uses, not only the primary one). Not split by class or "
        "discipline -- read against each architecture's own "
        "`applicable_classes` in `config/architectures/` for whether it "
        "fits the class actually being designed.",
        "",
        "| Architecture | Count |", "|:---|---:|",
    ]
    for a in ALL_ARCHITECTURES:
        lines.append(f"| {a} | {counts[a]} |")
    lines.append("")
    lines.append("**Not used in this window:** " +
                 (", ".join(unused) if unused else "none — all 14 appeared."))
    return "\n".join(lines)
