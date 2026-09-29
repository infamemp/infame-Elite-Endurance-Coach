"""
engine/load_targets.py — Infame Elite Endurance Coach v7
=========================================================
Weekly load targets for a block. The head coach chooses every input; this
module only does the arithmetic and hands back each week's TSS and hours
target, so the design table starts from numbers instead of guesses.

Inputs (all chosen by the coach, none defaulted from the athlete's data):

  start_weekly_tss  TSS of the first build week
  weeks             how many weeks to plan (1-52)
  cycle             "3:1" = 3 build weeks then 1 recovery week ("N:M" in general)
  growth_pct        growth from one build week to the next, in percent. One
                    number applies to every step; a list gives step 1 (week 2
                    of a cycle), step 2 (week 3), and its last value repeats.
  recovery_pct      how far a recovery week drops below the last build week
  tss_per_hour      optional: turns each TSS target into an hours target

Rules, fixed and stated so they can be checked:
  * A build week after the first grows on the build week before it.
  * A recovery week is the last build week times (1 - recovery_pct/100).
  * The first build week of the next cycle continues the progression: the last
    build week times (1 + first growth step). It does not restart at the start.
  * A week's tolerance is max(5, 3% of its target): that is how far the TSS
    of the written sessions may sit from the target before the week is
    reported as off target.

Reports only. Nothing here says a target is right for an athlete: the coach
compares it with #STATE (CTL, ramp rate, ACWR) and decides.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

MIN_TOLERANCE = 5
TOLERANCE_PCT = 3


def tolerance(target):
    """TSS a week may sit away from its target: max(5, 3% of the target)."""
    return round(max(MIN_TOLERANCE, target * TOLERANCE_PCT / 100), 1)


def check_week(target, actual):
    """Where a written week's summed TSS sits against its target."""
    tol = tolerance(target)
    diff = round(actual - target, 1)
    return {"target": target, "actual": actual, "difference": diff,
            "tolerance": tol, "within": abs(diff) <= tol}


def _parse_cycle(cycle):
    try:
        build, rec = str(cycle).replace(" ", "").split(":")
        build, rec = int(build), int(rec)
    except (ValueError, TypeError):
        raise ValueError(f"cycle '{cycle}' is not of the form N:M, e.g. 3:1")
    if build < 1 or build > 8 or rec < 0 or rec > 3:
        raise ValueError("cycle needs 1-8 build weeks and 0-3 recovery weeks")
    return build, rec


def _growth_steps(growth_pct):
    steps = list(growth_pct) if isinstance(growth_pct, (list, tuple)) else [growth_pct]
    if not steps:
        raise ValueError("growth_pct needs at least one value")
    for g in steps:
        if isinstance(g, bool) or not isinstance(g, (int, float)) or not 0 <= g <= 25:
            raise ValueError("growth_pct values must be numbers from 0 to 25")
    return steps


def plan(start_weekly_tss, weeks, cycle="3:1", growth_pct=5, recovery_pct=30,
         tss_per_hour=None, start_date=None):
    """Return {"weeks": [...], "inputs": {...}, "rules": [...]}. Raises
    ValueError with a plain message on any input that makes no sense."""
    if isinstance(start_weekly_tss, bool) or not isinstance(start_weekly_tss, (int, float)) \
            or not 20 <= start_weekly_tss <= 2000:
        raise ValueError("start_weekly_tss must be a number from 20 to 2000")
    if isinstance(weeks, bool) or not isinstance(weeks, int) or not 1 <= weeks <= 52:
        raise ValueError("weeks must be a whole number from 1 to 52")
    if isinstance(recovery_pct, bool) or not isinstance(recovery_pct, (int, float)) \
            or not 0 <= recovery_pct <= 60:
        raise ValueError("recovery_pct must be a number from 0 to 60")
    if tss_per_hour is not None and (isinstance(tss_per_hour, bool)
                                     or not isinstance(tss_per_hour, (int, float))
                                     or not 20 <= tss_per_hour <= 150):
        raise ValueError("tss_per_hour must be a number from 20 to 150")
    build_n, rec_n = _parse_cycle(cycle)
    steps = _growth_steps(growth_pct)

    first = None
    if start_date is not None:
        try:
            first = (start_date if isinstance(start_date, date)
                     else datetime.strptime(str(start_date)[:10], "%Y-%m-%d").date())
        except ValueError:
            raise ValueError(f"start_date '{start_date}' is not a date (YYYY-MM-DD)")

    out, last_build, build_in_cycle, rec_in_cycle = [], None, 0, 0
    for i in range(weeks):
        in_recovery = rec_in_cycle > 0 or (build_in_cycle == build_n and rec_n > 0)
        if in_recovery:
            if rec_in_cycle == 0:
                rec_in_cycle = rec_n
            kind = "recovery"
            tss = last_build * (1 - recovery_pct / 100)
            rec_in_cycle -= 1
            if rec_in_cycle == 0:
                build_in_cycle = 0
        else:
            if build_in_cycle == build_n:          # cycle without recovery weeks
                build_in_cycle = 0
            kind = "build"
            if last_build is None:
                tss = float(start_weekly_tss)
            else:
                step = steps[min(build_in_cycle - 1, len(steps) - 1)] if build_in_cycle > 0 else steps[0]
                tss = last_build * (1 + step / 100)
            last_build = tss
            build_in_cycle += 1
        tss = round(tss)
        row = {"week": i + 1, "type": kind, "target_tss": tss,
               "tolerance": tolerance(tss)}
        if tss_per_hour:
            row["target_hours"] = round(tss / tss_per_hour, 1)
        if first:
            row["week_start"] = (first + timedelta(days=7 * i)).isoformat()
        out.append(row)

    return {
        "weeks": out,
        "inputs": {"start_weekly_tss": start_weekly_tss, "weeks": weeks,
                   "cycle": f"{build_n}:{rec_n}", "growth_pct": steps,
                   "recovery_pct": recovery_pct, "tss_per_hour": tss_per_hour},
        "rules": ["a build week grows on the build week before it",
                  "a recovery week is the last build week reduced by recovery_pct",
                  "the next cycle continues the progression, it does not restart",
                  f"a week is on target within max({MIN_TOLERANCE}, {TOLERANCE_PCT}%) of its TSS target"],
    }


def render(result):
    """Markdown table for the design table. Reports only."""
    has_h = any("target_hours" in w for w in result["weeks"])
    has_d = any("week_start" in w for w in result["weeks"])
    head = ["Week"] + (["Starts"] if has_d else []) + ["Type", "TSS target", "± TSS"] \
        + (["Hours"] if has_h else [])
    L = ["## Load targets", "",
         "Arithmetic on the coach's own inputs; compare with #STATE before using. "
         f"Cycle {result['inputs']['cycle']}, growth {result['inputs']['growth_pct']}%, "
         f"recovery -{result['inputs']['recovery_pct']:g}%.", "",
         "| " + " | ".join(head) + " |",
         "| " + " | ".join([":---"] * len(head)) + " |"]
    for w in result["weeks"]:
        cells = [str(w["week"])] + ([w.get("week_start", "—")] if has_d else []) \
            + [w["type"], str(w["target_tss"]), f"{w['tolerance']:g}"] \
            + ([f"{w['target_hours']:g}"] if has_h else [])
        L.append("| " + " | ".join(cells) + " |")
    L.append("")
    return "\n".join(L)
