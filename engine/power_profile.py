"""
power_profile.py — Infame Elite Endurance Coach v6, Stage 6
============================================================
Ranks an athlete's power against the Coggan power profile table and reads their
phenotype from the SHAPE of that ranking.

The phenotype is not any single number. A sprinter ranks high at 5 seconds and
low at threshold; a time trialist is the reverse; a pursuiter sits high in the
middle. That shape is what selects the day-2 test duration in the structured
testing week, and it changes as the athlete's profile changes.

All table data and thresholds live in config/power_profile.yaml.
"""

from __future__ import annotations

COLUMNS = ["5s", "1min", "5min", "FT"]

NOTE = ("Scores are ordinal positions between the table's anchor rows, not true "
        "percentiles. Phenotype comes from the shape of the profile, never from "
        "one duration alone.")


def _score(value_wkg, column_index, rows):
    """Position a W/kg value on the 0-100 scale defined by the table rows for
    one column. Rows run highest to lowest, so the top row scores 100."""
    col = [r["values"][column_index] for r in rows]
    n = len(col)
    if value_wkg >= col[0]:
        return 100.0
    if value_wkg <= col[-1]:
        return 0.0
    for i in range(n - 1):
        hi, lo = col[i], col[i + 1]
        if lo <= value_wkg <= hi:
            span = hi - lo
            frac = (value_wkg - lo) / span if span else 0
            # Rows are evenly spaced on the scale: top row 100, bottom row 0.
            step = 100.0 / (n - 1)
            return (n - 2 - i) * step + frac * step
    return 0.0


def _label_for(value_wkg, column_index, rows):
    """The table row an athlete falls into, for a human-readable descriptor."""
    for r in rows:
        if value_wkg >= r["values"][column_index]:
            return r["label"]
    return rows[-1]["label"]


def _ft_watts(curve_points, profile, cfg):
    """Functional threshold power. The table has an FT column but the curve has
    no FT anchor, so resolve in the configured order: the athlete's own FTP
    first, then the 60-minute value, then a fraction of the 20-minute value."""
    fb = cfg.get("ft_fallback") or {}
    for s in (profile.get("sport_settings") or []):
        types = s.get("types") or []
        if any(t in ("Ride", "VirtualRide", "MountainBikeRide", "GravelRide")
               for t in types) and s.get("ftp"):
            return s["ftp"], "configured FTP"
    key = str(fb.get("then_seconds", 3600))
    if curve_points.get(key):
        return curve_points[key], f"{int(key) // 60}-minute curve value"
    if curve_points.get("1200"):
        factor = fb.get("then_from_1200_factor", 0.95)
        return curve_points["1200"] * factor, f"{factor:.0%} of the 20-minute value"
    return None, None


def analyze(curve_points, profile, cfg):
    """Rank the athlete and read their phenotype.

    curve_points: {anchor_seconds_as_str: watts} from the 42d window
    profile:      the athlete profile block from athlete_data.json
    cfg:          parsed config/power_profile.yaml
    """
    weight = profile.get("weight")
    if not weight:
        return {"available": False, "reason": "no body weight on the athlete profile"}

    sex = (profile.get("sex") or "M").upper()
    key = "women" if sex.startswith("F") else "men"
    rows = cfg["anchors"][key]

    ft, ft_source = _ft_watts(curve_points, profile, cfg)
    raw = {
        "5s": curve_points.get("5"),
        "1min": curve_points.get("60"),
        "5min": curve_points.get("300"),
        "FT": ft,
    }

    scored = {}
    for i, col in enumerate(COLUMNS):
        w = raw[col]
        if not w:
            continue
        wkg = w / weight
        scored[col] = {
            "watts": round(w),
            "w_per_kg": round(wkg, 2),
            "score": round(_score(wkg, i, rows), 1),
            "category": _label_for(wkg, i, rows),
        }

    if "5s" not in scored or "FT" not in scored:
        return {"available": False,
                "reason": "need both a 5s value and a threshold value to read "
                          "phenotype",
                "scored": scored or None}

    ph = cfg["phenotype"]

    # A value below the table floor is not a weak athlete — it is almost
    # certainly not a maximal effort. The bottom row sits under "average
    # untrained", so a trained cyclist scoring zero at 5s has simply never
    # sprinted in the window. Phenotype read from such a value is meaningless,
    # so it is refused rather than reported.
    untested = [c for c, s in scored.items() if s["score"] <= 0]
    if untested:
        return {
            "available": True,
            "sex_table": key,
            "weight_kg": weight,
            "ft_source": ft_source,
            "scored": scored,
            "phenotype": "undetermined",
            "untested_columns": untested,
            "phenotype_reason": (
                f"{', '.join(untested)} sits below the table floor, which is "
                f"under 'average untrained'. For a training athlete that means "
                f"the effort was never made in this window, not that the "
                f"capacity is absent. Phenotype cannot be read from an untested "
                f"duration."),
            "test_duration_minutes": ph["test_duration_minutes"]["all_rounder"],
            "test_duration_basis": (
                "all-rounder default — phenotype is unknown until the profile "
                "is tested, and the day-2 duration depends on it. Run the "
                "testing week at the default, then the phenotype resolves and "
                "later tests use its duration."),
            "note": NOTE,
        }

    gap = scored["5s"]["score"] - scored["FT"]["score"]
    ends = (scored["5s"]["score"] + scored["FT"]["score"]) / 2
    middles = [scored[c]["score"] for c in ("1min", "5min") if c in scored]
    middle = sum(middles) / len(middles) if middles else None

    if gap >= ph["sprint_vs_threshold_gap"]:
        phenotype = "sprinter"
        why = (f"5s score {scored['5s']['score']:.0f} sits "
               f"{gap:.0f} points above threshold")
    elif gap <= -ph["sprint_vs_threshold_gap"]:
        phenotype = "time_trialist"
        why = (f"threshold score {scored['FT']['score']:.0f} sits "
               f"{-gap:.0f} points above 5s")
    elif middle is not None and middle - ends >= ph["middle_elevation"]:
        phenotype = "pursuiter"
        why = (f"1min/5min mean {middle:.0f} rises {middle - ends:.0f} points "
               f"above the two ends")
    else:
        phenotype = "all_rounder"
        why = f"scores within {abs(gap):.0f} points across the profile"

    return {
        "available": True,
        "sex_table": key,
        "weight_kg": weight,
        "ft_source": ft_source,
        "scored": scored,
        "phenotype": phenotype,
        "phenotype_reason": why,
        "test_duration_minutes": ph["test_duration_minutes"].get(phenotype, 25),
        "note": NOTE,
    }


def render(pp):
    """Render the power profile block for state.md."""
    if not pp.get("available"):
        L = ["### Power profile", "",
             f"Not available — {pp.get('reason')}"]
        if pp.get("scored"):
            L.append("")
            for col, s in pp["scored"].items():
                L.append(f"- {col}: {s['watts']}W ({s['w_per_kg']} W/kg) — "
                         f"{s['category']}")
        L.append("")
        return "\n".join(L)

    L = ["### Power profile", ""]
    L.append(f"Ranked against the Coggan power profile "
             f"({pp['sex_table']}, {pp['weight_kg']} kg). "
             f"Threshold taken from {pp['ft_source']}.")
    L.append("")
    L.append("| Duration | Watts | W/kg | Score | Category |")
    L.append("| :--- | ---: | ---: | ---: | :--- |")
    untested = set(pp.get("untested_columns") or [])
    for col in COLUMNS:
        s = pp["scored"].get(col)
        if not s:
            L.append(f"| {col} | — | — | — | no data |")
            continue
        cat = ("below table floor — likely not a maximal effort"
               if col in untested else s["category"].replace("_", " "))
        L.append(f"| {col} | {s['watts']} | {s['w_per_kg']} | "
                 f"{s['score']:.0f} | {cat} |")
    L.append("")
    L.append(f"**Phenotype: {pp['phenotype'].replace('_', ' ')}** — "
             f"{pp['phenotype_reason']}")
    L.append("")
    L.append(f"Day-2 test duration: **{pp['test_duration_minutes']} minutes**"
             + (f" — {pp['test_duration_basis']}"
                if pp.get("test_duration_basis") else "."))
    L.append("")
    L.append(pp["note"])
    L.append("")
    return "\n".join(L)
