"""
engine/pd_diagnosis.py — Infame Elite Endurance Coach v7.14
============================================================
Power-duration diagnosis for cycling: the numbers the Cycling Doctrine asks
for (config/doctrine/cycling.yaml — rows athlete_diagnosis,
threshold_progression, above_threshold_intervals, load_progression).

  * TTE at FTP — how long the athlete's own curve stays at or above the FTP
    set in Intervals.icu (Cusick: time to exhaustion, WKOC-C05-041).
  * Level windows — the durations over which the curve sits inside Coggan
    Level 5 and Level 6. That is where this athlete can actually hold those
    levels, which is what sets rep length (Cusick: optimized intervals,
    WKOC-C08-001).
  * Pmax — best 1-second power.
  * The 20-minute best as a share of FTP — a plain fact.
  * W' as set in Intervals.icu, only when set.
  * CTL ramp band from Coggan's Table 9.2 for the declared training age.

Indoor and outdoor apart. Intervals.icu keeps a separate indoor FTP and
applies it to indoor rides, so each environment's curve is judged against its
own FTP (config/pd_diagnosis.yaml `environments`): outdoor against `ftp`,
indoor against `indoor_ftp` (or `ftp` when no indoor FTP is set, said so).
An environment with no rides in the window is left out.

Measured values only. Every number is read off the power curves Intervals.icu
returns (`pd_points`, stored by engine/fetch_athlete_data.py under
`curves.power_indoor` / `curves.power_outdoor`); no fitted model is read. A curve ends where the athlete's longest effort in that window
ended, so a crossing beyond the end is reported as "at least", never guessed.
Crossings between two points are interpolated on a log-time scale.

Reports only. Nothing here prescribes, blocks or judges.
"""

from __future__ import annotations

import math
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config")


def load_cfg():
    path = os.path.join(CONFIG, "pd_diagnosis.yaml")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def level_bounds(cfg):
    """{level key: (min %, max %)} read from the author file named in config."""
    path = os.path.join(CONFIG, "authors", f"{cfg['levels_author']}.yaml")
    with open(path, encoding="utf-8") as f:
        author = yaml.safe_load(f)
    out = {}
    for z in author.get("zones", []):
        if z.get("key") in cfg["levels"]:
            p = (z.get("ranges") or {}).get("power") or {}
            if p.get("min") is not None and p.get("max") is not None:
                out[z["key"]] = (p["min"], p["max"])
    return out


def ride_settings(profile):
    """The sport settings that hold "Ride" itself (not merely a type whose
    name contains it, such as "VirtualRide" alone)."""
    for s in (profile or {}).get("sport_settings") or []:
        if "Ride" in (s.get("types") or []):
            return s
    return {}


def _curve(window):
    """Sorted [(secs, watts)] from a window's pd_points, positive values only."""
    pts = (window or {}).get("pd_points") or {}
    return sorted((int(k), float(v)) for k, v in pts.items() if v and v > 0)


def crossing(curve, watts):
    """Longest duration the curve holds `watts`.

    Returns (secs, kind): kind 'exact' (interpolated between two points),
    'at_least' (still above at the curve's end: secs is that end),
    'below' (already below at the first point: secs is that first point)."""
    if not curve:
        return None, None
    if curve[0][1] < watts:
        return curve[0][0], "below"
    last = None
    for i, (t, w) in enumerate(curve):
        if w >= watts:
            last = i
    if last == len(curve) - 1:
        return curve[-1][0], "at_least"
    (t1, w1), (t2, w2) = curve[last], curve[last + 1]
    if w1 == w2:
        return t1, "exact"
    frac = (w1 - watts) / (w1 - w2)
    secs = math.exp(math.log(t1) + frac * (math.log(t2) - math.log(t1)))
    return round(secs), "exact"


def ramp_band(cfg, training_age_years, ctl):
    if training_age_years is None or ctl is None:
        return None
    try:
        years = float(training_age_years)
    except (TypeError, ValueError):
        return None
    rr = cfg["ramp_rates"]
    side = "below" if ctl < rr["ctl_split"] else "above"
    for b in rr["bands"]:
        hi = b["max_years"]
        if years >= b["min_years"] and (hi is None or years < hi):
            return {"training_age": b["training_age"], "ctl_side": side,
                    "ctl_split": rr["ctl_split"],
                    "long_term": b["long_term"][side],
                    "short_term": b["short_term"][side]}
    return None


def _window_row(curve, ftp, bounds, cfg):
    end = curve[-1][0]
    row = {"curve_end_secs": end, "points": len(curve)}
    row["pmax"] = curve[0][1] if curve[0][0] <= 1 else None
    if end >= cfg["min_curve_secs_for_tte"]:
        secs, kind = crossing(curve, ftp)
        row["tte"] = {"secs": secs, "kind": kind}
    else:
        row["tte"] = None
    ref = dict(curve).get(cfg["reference_secs"])
    row["ref_pct_ftp"] = round(100 * ref / ftp) if ref else None
    levels = {}
    for key, (lo, hi) in bounds.items():
        top = crossing(curve, ftp * hi / 100)
        bottom = crossing(curve, ftp * lo / 100)
        levels[key] = {"min_pct": lo, "max_pct": hi,
                       "from": {"secs": top[0], "kind": top[1]},
                       "to": {"secs": bottom[0], "kind": bottom[1]}}
    row["levels"] = levels
    return row


def analyze(data, declared=None, ctl=None, cfg=None):
    """The diagnosis, or None when there is nothing to diagnose (no config,
    no FTP set, or no indoor/outdoor curve in any window)."""
    cfg = cfg or load_cfg()
    if not cfg:
        return None
    settings = ride_settings(data.get("profile"))
    curves = data.get("curves") or {}
    bounds = level_bounds(cfg)

    envs = []
    for e in cfg["environments"]:
        power = curves.get(e["curve"]) or {}
        if not any(_curve(power.get(w)) for w in cfg["windows"]):
            continue
        ftp, ftp_field = settings.get(e["ftp_field"]), e["ftp_field"]
        if not ftp and e.get("fallback_ftp_field"):
            ftp, ftp_field = settings.get(e["fallback_ftp_field"]), e["fallback_ftp_field"]
        if not ftp:
            continue
        windows = {}
        for w in cfg["windows"]:
            curve = _curve(power.get(w))
            windows[w] = _window_row(curve, ftp, bounds, cfg) if curve else None
        envs.append({"key": e["key"], "label": e["label"], "ftp": ftp,
                     "ftp_field": ftp_field,
                     "ftp_fallback": ftp_field != e["ftp_field"],
                     "windows": windows})
    if not envs:
        return None

    training_age = ((declared or {}).get("history") or {}).get("training_age_years")
    wp = settings.get("w_prime")
    return {
        "environments": envs,
        "w_prime_j": wp if wp else None,
        "training_age_years": training_age,
        "ramp_band": ramp_band(cfg, training_age, ctl),
        "levels_author": cfg["levels_author"],
    }


def _clock(secs):
    secs = int(round(secs))
    return f"{secs // 3600}:{secs % 3600 // 60:02d}:{secs % 60:02d}" if secs >= 3600 \
        else f"{secs // 60}:{secs % 60:02d}"


def _point(p):
    if not p or p.get("secs") is None:
        return "—"
    if p["kind"] == "at_least":
        return f"≥ {_clock(p['secs'])} (curve ends)"
    if p["kind"] == "below":
        return f"< {_clock(p['secs'])}"
    return f"≈ {_clock(p['secs'])}"


def _level_cell(lv):
    a, b = lv["from"], lv["to"]
    if b["kind"] == "below":
        return "not reached"
    start = "0:00" if a["kind"] == "below" else _clock(a["secs"])
    end = _point(b).replace("≈ ", "")
    return f"{start} – {end}"


def _env_table(env, author):
    ws = list(env["windows"])
    note = (f" — no indoor FTP set, so the FTP ({env['ftp']:.0f} W) is used"
            if env["ftp_fallback"] else "")
    field = "indoor FTP" if env["ftp_field"] == "indoor_ftp" else "FTP"
    L = [f"### {env['label']} — {field} {env['ftp']:.0f} W (Intervals.icu setting){note}", "",
         "| Measure | " + " | ".join(ws) + " | Source |",
         "| :--- | " + " | ".join(":---" for _ in ws) + " | :--- |"]

    def row(label, fn, source):
        cells = [fn(env["windows"][w]) if env["windows"][w] else "no rides" for w in ws]
        L.append(f"| {label} | " + " | ".join(cells) + f" | {source} |")

    row("TTE at FTP", lambda r: _point(r["tte"]) if r["tte"] else
        f"curve too short ({_clock(r['curve_end_secs'])})", "Cusick: time to exhaustion")
    any_w = next(r for r in env["windows"].values() if r)
    for key, lv in any_w["levels"].items():
        row(f"{key} window ({lv['min_pct']}–{lv['max_pct']}% FTP)",
            lambda r, k=key: _level_cell(r["levels"][k]),
            f"durations the curve holds {author.capitalize()} {key}")
    row("Best 20 min", lambda r: f"{r['ref_pct_ftp']}% of FTP" if r["ref_pct_ftp"] else "—",
        "measured")
    row("Pmax (best 1 s)", lambda r: f"{r['pmax']:.0f} W" if r["pmax"] else "—", "measured")
    row("Curve length", lambda r: _clock(r["curve_end_secs"]), "longest effort in window")
    return L


def render(dx):
    L = ["## POWER-DURATION DIAGNOSIS (cycling)", "",
         "> Cycling Doctrine rows: athlete diagnosis, threshold progression, above-threshold "
         "intervals, load progression. Read straight off the power curves Intervals.icu "
         "returns — measured values, no fitted model. Indoor and outdoor are kept apart, each "
         "against its own FTP; an environment with no rides is not shown. A curve ends where "
         "the longest effort of that window ended; a value marked ≥ may be longer. A window "
         "without recent maximal efforts understates the athlete (Cusick: test every 4-6 "
         "weeks).", ""]
    for env in dx["environments"]:
        L += _env_table(env, dx["levels_author"]) + [""]
    if dx["w_prime_j"]:
        L.append(f"- W′ as set in Intervals.icu: {dx['w_prime_j'] / 1000:.1f} kJ "
                 "(the setting, not a measurement).")
    rb = dx["ramp_band"]
    if rb:
        side = f"CTL {'<' if rb['ctl_side'] == 'below' else '≥'} {rb['ctl_split']}"
        L.append(f"- CTL ramp band (Coggan Table 9.2; training age {rb['training_age']}, "
                 f"{side}): {rb['long_term'][0]}–{rb['long_term'][1]} TSS/day over 14–28 "
                 f"days; short term {rb['short_term'][0]}–{rb['short_term'][1]} TSS/day, "
                 "then a rest week.")
    else:
        L.append("- CTL ramp band: training age not declared (`history.training_age_years`), "
                 "so no band is shown.")
    return "\n".join(L).rstrip() + "\n"
