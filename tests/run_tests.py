"""
run_tests.py — Infame Elite Endurance Coach v6, Stage 7
========================================================
The regression net. Run it after any change to config or engine code.

Two kinds of test:

  UNIT — deterministic functions checked against known answers. A TSS figure
  computed by hand, a band boundary, a floor rejection. These fail loudly and
  point at the exact rule that broke.

  GOLDEN — each synthetic athlete in tests/fixtures/ is put through the full
  state engine and compared against a frozen expected output. Any difference is
  reported field by field. These catch the changes nobody predicted: a threshold
  edit that quietly moves an unrelated athlete into a different state.

Volatile fields — dates, timestamps, anything that changes purely because time
passed — are stripped before comparison. A test suite that fails at midnight
teaches people to ignore it.

Usage:
    python tests/run_tests.py              run everything
    python tests/run_tests.py --unit       unit tests only
    python tests/run_tests.py --golden     golden comparisons only
    python tests/run_tests.py --update     accept current output as the new golden

--update is deliberate, never automatic. When a change is intended, run it, read
the diff it prints, and commit the new goldens as part of that change.

Exit code: 0 all passed · 1 at least one failure.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
sys.path.insert(0, os.path.join(ROOT, "verify"))
sys.path.insert(0, ROOT)

FIXTURES = os.path.join(ROOT, "tests", "fixtures")
BLOCKS = os.path.join(ROOT, "tests", "blocks")

PASSED, FAILED = [], []

# Fields that change with the calendar rather than with the code.
VOLATILE = {"date", "resolved_at", "fetched_at", "from", "to", "dates",
            "date_range", "window", "windows", "series", "last_session_date"}


# ══════════════════════════════════════════════════════════════════
# HARNESS
# ══════════════════════════════════════════════════════════════════

def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
    else:
        FAILED.append((name, detail))


def equal(name, got, want, tolerance=None):
    if tolerance is not None and isinstance(got, (int, float)) \
            and isinstance(want, (int, float)):
        ok = abs(got - want) <= tolerance
    else:
        ok = got == want
    check(name, ok, f"got {got!r}, expected {want!r}")


def strip_volatile(obj):
    """Remove time-dependent fields so the comparison tests logic, not the clock."""
    if isinstance(obj, dict):
        return {k: strip_volatile(v) for k, v in obj.items()
                if k not in VOLATILE}
    if isinstance(obj, list):
        return [strip_volatile(x) for x in obj]
    return obj


def diff(path, got, want, out):
    """Walk two structures and record every difference with its full path."""
    if isinstance(want, dict) and isinstance(got, dict):
        for k in sorted(set(want) | set(got)):
            if k not in got:
                out.append(f"    {path}.{k}: MISSING (expected {want[k]!r})")
            elif k not in want:
                out.append(f"    {path}.{k}: UNEXPECTED ({got[k]!r})")
            else:
                diff(f"{path}.{k}", got[k], want[k], out)
    elif isinstance(want, list) and isinstance(got, list):
        if len(want) != len(got):
            out.append(f"    {path}: length {len(got)}, expected {len(want)}")
        for i, (g, w) in enumerate(zip(got, want)):
            diff(f"{path}[{i}]", g, w, out)
    elif isinstance(want, float) and isinstance(got, float):
        if abs(got - want) > 0.05:
            out.append(f"    {path}: {got}, expected {want}")
    elif got != want:
        out.append(f"    {path}: {got!r}, expected {want!r}")


# ══════════════════════════════════════════════════════════════════
# UNIT TESTS
# ══════════════════════════════════════════════════════════════════

def load_cfg():
    import yaml
    def rd(n):
        with open(os.path.join(ROOT, "config", n), encoding="utf-8") as f:
            return yaml.safe_load(f)
    import zone_model
    return zone_model.with_derived_cutpoints(rd("decision_thresholds.yaml")), \
        rd("tss_classes.yaml"), rd("power_profile.yaml")


def unit_tests():
    import yaml
    th, tssc, ppcfg = load_cfg()
    import longitudinal, power_profile
    import validate_block as vb

    # ── TSS from a known structure ────────────────────────────────
    # 60 min endurance at 1.0/min plus 20 min threshold at 1.5/min = 90 TSS.
    m = {k: v["tss_per_min"] for k, v in tssc["classes"].items()}
    equal("tss: endurance multiplier", m["endurance"], 1.0)
    equal("tss: threshold multiplier", m["threshold"], 1.5)
    equal("tss: sub_threshold sits between tempo and threshold",
          m["tempo"] < m["sub_threshold"] < m["threshold"], True)
    equal("tss: hand-computed 60min endurance + 20min threshold",
          60 * m["endurance"] + 20 * m["threshold"], 90.0)
    equal("tss: supra split ascends",
          m["vo2max"] < m["anaerobic"] < m["neuromuscular"], True)

    # ── Cutpoints are disjoint and cover the range ────────────────
    cuts = th["classification_cutpoints"]["cycling"]["power"]
    bounds = sorted((v.get("min") or 0, v.get("max")) for v in cuts.values())
    gaps = []
    for i in range(len(bounds) - 1):
        if bounds[i][1] != bounds[i + 1][0]:
            gaps.append((bounds[i], bounds[i + 1]))
    check("cutpoints: cycling power has no gaps or overlaps", not gaps, str(gaps))
    equal("cutpoints: sub_threshold starts at 88",
          cuts["sub_threshold"]["min"], 88)
    equal("cutpoints: threshold starts at 95", cuts["threshold"]["min"], 95)

    # ── Prescription floors ───────────────────────────────────────
    fl = th["prescription_floors"]
    equal("floors: power", fl["power"], 25)
    equal("floors: lthr", fl["lthr"], 50)
    equal("floors: pace", fl["pace"], 40)

    # ── Ramp rules ────────────────────────────────────────────────
    r = th["ramps"]
    check("ramps: trainer allowed", "trainer" in r["allowed_disciplines"])
    check("ramps: road bike forbidden", "road_bike" in r["forbidden_disciplines"])
    check("ramps: road run forbidden", "road_run" in r["forbidden_disciplines"])
    check("ramps: trail run forbidden", "trail_run" in r["forbidden_disciplines"])

    # ── Discipline vocabulary ─────────────────────────────────────
    # One canonical name per discipline; old names still resolve, "road"
    # resolves by the methodology's sport, and cross-sport pairs are errors.
    rd = vb.resolve_discipline
    canon = th["disciplines"]["canonical"]
    for disc in ("road_bike", "mtb", "gravel", "trainer",
                 "road_run", "trail_run", "treadmill", "track_run"):
        check(f"disciplines: {disc} is canonical", disc in canon)
    for listed in (r["allowed_disciplines"] + r["forbidden_disciplines"]
                   + list(r.get("override_eligible") or {})
                   + list(th["metric_defaults"])):
        check(f"disciplines: '{listed}' in config uses the canonical vocabulary",
              listed in canon)
    equal("disciplines: 'road' + cycling -> road_bike",
          rd("road", "cycling", th)[:2], ("road_bike", "road"))
    equal("disciplines: 'road' + running -> road_run",
          rd("road", "running", th)[:2], ("road_run", "road"))
    equal("disciplines: 'run' -> road_run", rd("run", "running", th)[0], "road_run")
    equal("disciplines: 'Trail' -> trail_run (case-insensitive)",
          rd("Trail", "running", th)[0], "trail_run")
    equal("disciplines: canonical name has no alias note",
          rd("mtb", "cycling", th), ("mtb", None, None))
    check("disciplines: unknown name is an error",
          rd("bici", "cycling", th)[2] is not None)
    check("disciplines: running methodology on trainer is an error",
          rd("trainer", "running", th)[2] is not None)
    check("disciplines: cycling methodology on 'run' is an error",
          rd("run", "cycling", th)[2] is not None)

    # ── Validator hardening: targets, metrics, equipment, RPE ─────
    # Each case is a code block the validator used to pass silently even
    # though Intervals.icu would execute a different workout (or none).
    def findings(code, methodology, discipline, profile=None):
        author, th_, tss_ = vb.load_config(methodology)
        steps, found = vb.parse_block(code)
        errs, warns_ = vb.check_constraints(steps, code, author, th_, discipline, profile)
        return found + errs + warns_

    def hc_codes(code, methodology, discipline, profile=None):
        return {c for c, _, _ in findings(code, methodology, discipline, profile)
                if c.startswith("HC-")}

    def all_codes(code, methodology, discipline, profile=None):
        return {c for c, _, _ in findings(code, methodology, discipline, profile)}

    check("hardening: zone shorthand (Z2) is rejected",
          "HC-ZONE" in hc_codes("- 20m Z2 [RPE 3]", "coggan", "trainer"))
    check("hardening: zone shorthand with suffix (Z3 Pace) is rejected",
          "HC-ZONE" in hc_codes("- 20m Z3 Pace [RPE 3]", "daniels", "road_run"))
    check("hardening: raw bpm is rejected",
          "HC-FORMAT" in hc_codes("- 20m 150-160bpm [RPE 3]", "friel_running", "road_run"))
    check("hardening: a step with no target is rejected",
          "HC-TARGET" in hc_codes("- 20m 90rpm", "coggan", "trainer"))
    check("hardening: a % inside the cue does not count as the target",
          "HC-TARGET" in hc_codes('- 20m "sube al 90%"', "coggan", "trainer"))
    check("hardening: an RPE-only step is accepted (no HR, no power case)",
          not hc_codes('- 20m [RPE 5] "Conversacional."', "koop", "trail_run"))
    check("hardening: freeride needs no target",
          not hc_codes("- 20m freeride [RPE 3]", "coggan", "trainer"))
    check("hardening: a clean trainer block has no hard-constraint findings",
          not hc_codes('- 10m ramp 50-70% 90rpm [RPE 2-3] "a"\n- 20m 88-92% [RPE 4] "b"',
                       "coggan", "trainer"))

    # Any methodology, any metric of its sport
    check("metrics: running power with a pace-only methodology is accepted",
          not hc_codes("- 20m 75-80% [RPE 2]", "daniels", "treadmill"))
    check("metrics: ...and reported as classified by generic ranges",
          "CHK-METRIC" in all_codes("- 20m 75-80% [RPE 2]", "daniels", "treadmill"))
    check("metrics: LTHR with a power-first cycling methodology is accepted",
          not hc_codes("- 20m 75-80% LTHR [RPE 2]", "coggan", "road_bike"))
    check("metrics: pace on a cycling discipline is rejected",
          "HC-METRIC" in hc_codes("- 20m 75-80% Pace [RPE 2]", "coggan", "road_bike"))
    check("metrics: running power with a power methodology is accepted, no warning",
          not all_codes("- 20m 75-80% [RPE 3]", "palladino", "road_run"))
    check("metrics: Olbrich's native metric reports HC-SOR, not HC-METRIC",
          "HC-METRIC" not in hc_codes("- 20m 70% HRmax [RPE 2]", "olbrich", "trail_run"))
    pace_map = {"metric_overrides": {"road_run": "pace"}}
    check("metrics: a bare % against a declared pace Metric Map is rejected",
          "HC-METRIC" in hc_codes("- 20m 75-80% [RPE 2]", "daniels", "road_run", pace_map))
    check("metrics: the declared metric passes the Metric Map",
          not hc_codes("- 20m 75-80% Pace [RPE 2]", "daniels", "road_run", pace_map))

    # Equipment: blocked only when every device for the metric is false
    check("equipment: running power with run_power_meter false is rejected",
          "HC-METRIC" in hc_codes("- 20m 75-80% [RPE 3]", "palladino", "road_run",
                                  {"equipment": {"run_power_meter": False}}))
    check("equipment: an undeclared device (null) never blocks",
          not hc_codes("- 20m 75-80% [RPE 3]", "palladino", "road_run",
                       {"equipment": {"run_power_meter": None}}))
    check("equipment: LTHR with hr_monitor false is rejected",
          "HC-METRIC" in hc_codes("- 20m 80-85% LTHR [RPE 2]", "friel_running", "road_run",
                                  {"equipment": {"hr_monitor": False}}))
    check("equipment: pace on a treadmill needs no device",
          not hc_codes("- 20m 78-82% Pace [RPE 2]", "daniels", "treadmill",
                       {"equipment": {"run_power_meter": False, "hr_monitor": False}}))
    check("equipment: trainer power from a smart trainer alone is accepted",
          not hc_codes("- 20m 60-65% [RPE 3]", "friel_cycling", "trainer",
                       {"equipment": {"bike_power_meter": False, "smart_trainer": True}}))
    check("equipment: outdoor bike power needs the power meter, not the trainer",
          "HC-METRIC" in hc_codes("- 20m 60-65% [RPE 3]", "friel_cycling", "road_bike",
                                  {"equipment": {"bike_power_meter": False,
                                                 "smart_trainer": True}}))

    # RPE: always present, and consistent with the author's table
    check("rpe: a step without RPE is rejected",
          "HC-RPE" in hc_codes("- 20m 60-65%", "friel_cycling", "trainer"))
    check("rpe: an RPE outside the author's zone is rejected (Friel Z2 is 3-4)",
          "HC-RPE" in hc_codes("- 20m 58-62% [RPE 2]", "friel_cycling", "trainer"))
    check("rpe: an RPE inside the author's zone is accepted",
          not hc_codes("- 20m 58-62% [RPE 3]", "friel_cycling", "trainer"))
    check("rpe: a range spanning two zones accepts either zone's RPE",
          not hc_codes("- 20m 70-80% [RPE 5]", "friel_cycling", "trainer"))
    check("rpe: a metric the author lacks is checked by physiological class",
          "HC-RPE" in hc_codes("- 20m 99-101% [RPE 1]", "daniels", "treadmill"))
    check("rpe: an open lower bound does not stretch a zone's RPE to zero",
          not hc_codes("- 10m 40% [RPE 1]", "carmichael", "trainer"))

    # Dual layer still demands the engine metric and the cue
    check("dual layer: a Koop step without its cue is rejected",
          "HC-DUAL" in hc_codes("- 20m 80-85% LTHR [RPE 5]", "koop", "trail_run"))

    # Ramps
    check("ramps: a ramp on a treadmill is rejected (write steps)",
          "HC-RAMP" in hc_codes("- 10m ramp 80-95% Pace [RPE 3-5]", "daniels", "treadmill"))
    check("ramps: disable_ramps in the profile blocks a trainer ramp",
          "HC-RAMP" in hc_codes("- 10m ramp 50-70% [RPE 2-3]", "coggan", "trainer",
                                {"ramp_overrides": {"disable_ramps": ["trainer"]}}))

    author, th_, tss_ = vb.load_config("daniels")
    steps, _ = vb.parse_block("- 10m 75-80% Pace\n- 2km 88-92% Pace")
    total, _, skipped = vb.compute_tss(steps, author, th_, tss_)
    equal("hardening: a distance step is reported as not costed", len(skipped), 1)

    # A partial TSS is written as such, and still re-validates cleanly
    import shutil, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        blk = os.path.join(tmp, "partial.md")
        shutil.copy2(os.path.join(ROOT, "tests", "blocks", "vianey_bloque1.md"), blk)
        script = os.path.join(ROOT, "verify", "validate_block.py")
        # Same guard as block_tests(): on Windows a captured child inherits the
        # locale encoding (cp1252) and crashes printing "—" or "─".
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        subprocess.run([sys.executable, script, blk, "--fill-tss", "--quiet"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
        with open(blk, encoding="utf-8") as f:
            written = f.read()
        check("hardening: TSS with uncosted steps is written as '(partial)'",
              "(partial)" in written)
        again = subprocess.run([sys.executable, script, blk, "--quiet"],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env=env)
        equal("hardening: a '(partial)' TSS re-validates without divergence",
              again.returncode, 0)
    check("ramps: only the trainer can follow a continuous ramp",
          r["allowed_disciplines"] == ["trainer"]
          and "treadmill" in r["forbidden_disciplines"])
    check("ramps: no magnitude cap is imposed",
          "no_magnitude_limit" in r,
          "a cap would prohibit a progressive ramp test")

    # ── Anchored authors are converted before matching ────────────
    import zone_model
    carm = zone_model.load_author("carmichael")
    anc = carm.get("anchor")
    check("anchor: carmichael declares a non-threshold anchor", bool(anc))
    if anc:
        equal("anchor: factor is 1.10", anc["factor_from_threshold"], 1.10)
        equal("anchor: applies to power", anc["metric"], "power")
        equal("anchor: class taken from the equivalent column",
              anc.get("class_from"), "equivalent")
        # SS is 86-90 on the author's scale; on the threshold scale that is 95-99.
        cls, src = vb.classify(97, "power", carm, th)
        equal("anchor: a 97% FTP target matches SteadyState", cls, "threshold")
        check("anchor: the source names the conversion",
              "threshold-equivalent" in (src or ""), src)
        # Without conversion 97% would fall in ClimbingRepeat (95-100 native).
        cls2, _ = vb.classify(107, "power", carm, th)
        equal("anchor: a 107% FTP target matches ClimbingRepeat", cls2, "vo2max")

    # ── Author zone classification wins over cutpoints ────────────
    author = {"id": "coggan", "sport": "cycling", "zones": [
        {"key": "Level 3", "physiological_class": "tempo",
         "ranges": {"power": {"min": 76, "max": 90}}}]}
    cls, src = vb.classify(85, "power", author, th)
    equal("precedence: author zone governs", (cls, src), ("tempo", "coggan Level 3"))
    cls, src = vb.classify(150, "power", author, th)
    equal("precedence: cutpoints are the fallback", src, "cutpoints")

    # ── v7.2 zone model: native values → estimates, class, domain ──
    import zone_model as zm
    import glob
    for sport in ("cycling", "running"):
        b = sorted(((v.get("min") or 0), v.get("max"))
                   for v in tssc["bands"][sport].values())
        gaps = [(x, y) for x, y in zip(b, b[1:]) if x[1] != y[0]]
        check(f"bands: {sport} canonical bands are disjoint and contiguous",
              not gaps, str(gaps))
    for c, spec in tssc["classes"].items():
        check(f"classes: {c} belongs to a declared domain",
              spec.get("domain") in tssc["domains"])
    m9 = [tssc["classes"][c]["tss_per_min"] for c in zm.CLASS_ORDER]
    equal("tss: multipliers ascend through all nine classes", m9, sorted(m9))
    equal("tss: supra_threshold sits between threshold and vo2max",
          m["threshold"] < tssc["classes"]["supra_threshold"]["tss_per_min"]
          < m["vo2max"], True)
    for sport in ("cycling", "running"):
        for c in zm.CLASS_ORDER:
            doms = {zm.domain_of_class(c)}
            check(f"domain: {sport} {c} maps to exactly one domain", len(doms) == 1)
    # Crosswalk: anchor holds and conversions are monotonic
    equal("crosswalk: 100% FTP = 100% LTHR (cycling)",
          zm.from_canonical(100, "lthr", "cycling"), 100.0)
    equal("crosswalk: 100% pace = 100% LTHR (running)",
          zm.from_canonical(100, "lthr", "running"), 100.0)
    equal("crosswalk: running power equals pace", zm.from_canonical(93, "power", "running"), 93.0)
    for sport, canon in (("cycling", "power"), ("running", "pace")):
        vals = [zm.from_canonical(t, "lthr", sport) for t in range(45, 111, 5)]
        vals = [v for v in vals if v is not None]
        equal(f"crosswalk: {sport} LTHR is monotonic", vals, sorted(vals))
        rt = zm.to_canonical(zm.from_canonical(92, "lthr", sport), "lthr", sport)
        check(f"crosswalk: {sport} LTHR round-trips", abs(rt - 92) < 0.01, rt)
    check("crosswalk: no extrapolation past the last knot",
          zm.from_canonical(160, "lthr", "cycling") is None)
    equal("crosswalk: Olbrich HRmax 90% = 100% LTHR (author's own point)",
          round(zm.to_canonical(90, "hrmax", "running",
                                zm.load_author_raw("olbrich")), 1), 100.0)
    # Every author resolves with no errors, and no author file carries a
    # hand-assigned class
    for f in sorted(glob.glob(os.path.join(ROOT, "config", "authors", "[!_]*.yaml"))):
        aid = os.path.basename(f)[:-5]
        raw = zm.load_author_raw(aid)
        _, errs, _ = zm.resolve_author(raw)
        check(f"authors: {aid} resolves without class conflicts", not errs, errs)
        check(f"authors: {aid} carries no hand-assigned class",
              not any("physiological_class" in z for z in raw["zones"]))
    # Known classes after the v7.2 reclassification
    def zc(aid, key):
        return next(z for z in zm.load_author(aid)["zones"] if str(z["key"]) == key)
    for aid, key, want in [
            ("coggan", "Level 4", "threshold"), ("friel_cycling", "Zone 4", "threshold"),
            ("carmichael", "T", "sub_threshold"), ("carmichael", "CR", "vo2max"),
            ("daniels", "M", "tempo"), ("daniels", "T", "threshold"),
            ("palladino", "3A", "sub_threshold"), ("palladino", "4", "supra_threshold"),
            ("friel_running", "Zone 5a", "supra_threshold"),
            ("friel_running", "Zone 5c", "anaerobic"),
            ("olbrich", "TER", "threshold"), ("olbrich", "INT", "vo2max"),
            ("koop", "SSR", "sub_threshold")]:
        equal(f"reclass: {aid} {key}", zc(aid, key)["physiological_class"], want)
    equal("domain: Coggan Level 4 crosses heavy→severe",
          _dom_cell := zc("coggan", "Level 4")["flags"][0], "spans heavy→severe")
    equal("estimate: Daniels E gets an estimated LTHR range",
          zc("daniels", "E")["range_status"]["lthr"], "estimated")
    check("estimate: no heart-rate estimate in the extreme domain",
          "lthr" not in zc("daniels", "R")["ranges"])
    equal("estimate: native values are never overwritten",
          zc("coggan", "Level 3")["ranges"]["lthr"], {"min": 84, "max": 94})
    # A stated class that disagrees with the numbers must fail without a resolution
    bad = zm.load_author_raw("coggan")
    bad["zones"][2]["stated_class"] = {"class": "vo2max", "source": "test"}
    _, errs, _ = zm.resolve_author(bad)
    check("conflict: stated vs computed class fails the build", bool(errs))

    # ── v7.2 race anchors (running) ────────────────────────────────
    rr = zm.race_anchor_residuals()
    tol = zm.load_crosswalk()["running"]["race_anchors"]["duration_model"]["residual_tolerance"]
    diffs = [abs(r[3]) for r in rr]
    check("race anchors: model reproduces Palladino's published ranges (mean)",
          sum(diffs) / len(diffs) <= tol["mean"], f"{sum(diffs) / len(diffs):.2f}")
    check("race anchors: model reproduces Palladino's published ranges (max)",
          max(diffs) <= tol["max"], f"{max(diffs):.2f}")
    equal("race anchors: 60 minutes is the threshold anchor",
          round(zm.speed_pct_at_duration(60), 1), 100.0)
    equal("race anchors: 30-minute pace is 103.8% of threshold",
          round(zm.speed_pct_at_duration(30), 1), 103.8)
    equal("race anchors: 2-hour pace is 95.7% of threshold",
          round(zm.speed_pct_at_duration(120), 1), 95.7)
    check("race anchors: duration result does not depend on the reference level",
          abs(zm.speed_pct_at_duration(30, vdot=35) - zm.speed_pct_at_duration(30, vdot=65)) < 0.3)
    dur = [zm.speed_pct_at_duration(t) for t in (6, 15, 30, 60, 90, 120, 180)]
    equal("race anchors: sustainable speed falls as duration grows", dur, sorted(dur, reverse=True))
    equal("race anchors: 1500m and mile use the 1600m row",
          zm._anchor_point({"distance": "mile"}), zm._anchor_point({"distance": "1600m"}))
    check("race anchors: unknown distance is rejected",
          bool(zm.validate_race_anchor({"distance": "marathn"}, "running")))
    check("race anchors: cycling has no race anchors",
          bool(zm.validate_race_anchor({"duration_min": 30}, "cycling")))
    r_lo, r_hi, _ = zm.race_anchor_range({"from": {"duration_min": 6}, "to": None})
    check("race anchors: an open span has no upper bound", r_hi is None and r_lo > 110)
    # Rosario: every class is computed from the anchors
    def rz(key):
        return next(z for z in zm.load_author("rosario")["zones"] if str(z["key"]) == key)
    for key, want in [("Easy", "endurance"), ("MP", "sub_threshold"), ("SSP", "sub_threshold"),
                      ("HMP", "sub_threshold"), ("LTP", "threshold"), ("10KP", "supra_threshold"),
                      ("CV", "supra_threshold"), ("HI", "vo2max"), ("5KP", "vo2max"),
                      ("MAS", "vo2max"), ("VHI", "anaerobic")]:
        equal(f"rosario: {key} class", rz(key)["physiological_class"], want)
    check("rosario: no zone is left without numbers",
          all(rz(k)["ranges"].get("pace") for k in ("MP", "SSP", "HMP", "LTP", "10KP", "CV", "HI", "5KP", "MAS", "VHI")))
    equal("rosario: MP is estimated, not native", rz("MP")["range_status"]["pace"], "estimated")
    check("rosario: the native VT2 heart rate agrees with the 30-minute anchor",
          not [w for w in zm.resolve_author(zm.load_author_raw("rosario"))[2] if "race anchor" in w])
    check("rosario: MP is flagged borderline",
          any(f.startswith("borderline") for f in rz("MP")["flags"]))
    # Borderline is not a class change
    check("borderline: Coggan Level 4 is not flagged (midpoint 98, four points wide)",
          not any(f.startswith("borderline") for f in zc("coggan", "Level 4")["flags"]))
    # Author-level threshold definition by duration (running)
    fake = zm.load_author_raw("daniels")
    fake["anchor"] = {"metric": "pace", "reference": "30-minute test", "duration_min": 30,
                      "source": "test"}
    fa, ferrs, _ = zm.resolve_author(fake)
    equal("anchor by duration: factor is computed from the model",
          fa["anchor"]["factor_from_threshold"], 1.038)
    equal("anchor by duration: a native 75% reads as 77.9% of threshold",
          next(z for z in fa["zones"] if z["key"] == "E")["canonical"]["min"], 77.9)
    check("anchor by duration: moving the definition surfaces the class conflict",
          any("daniels T" in e and "supra_threshold" in e for e in ferrs), ferrs)
    bad = zm.load_author_raw("coggan")
    bad["anchor"] = {"metric": "power", "reference": "x", "duration_min": 30, "source": "x"}
    _, berrs, _ = zm.resolve_author(bad)
    check("anchor by duration: refused for cycling (no duration model)", bool(berrs))
    # Palladino: his published 10K range sits on the 60-minute scale (no factor needed)
    pal10 = zm._anchor_point({"distance": "10K"})
    mlo, mhi = zm.model_pct_for_distance(10000)
    check("palladino: his 10K range and the 60-minute model overlap",
          pal10[0] <= mhi and mlo <= pal10[1])

    # ── v7.2 pace offsets and Hansons ──────────────────────────────
    lo, hi, desc = zm.race_anchor_range({"distance": "marathon",
                                          "offset_s_per_mile": {"min": 60, "max": 120}})
    check("offset: goal marathon pace +1:00 to +2:00 reads 70-84% of threshold",
          69.5 < lo < 71 and 83.5 < hi < 85, (lo, hi))
    check("offset: the description names the offset", "+1:00 to +2:00 per mile" in desc, desc)
    slow = zm.model_pct_for_offset(42195, 60, 60)
    check("offset: a slower pace than the anchor is a lower % of threshold",
          slow[1] < zm.model_pct_for_distance(42195)[0])
    fast = zm.race_anchor_range({"distance": "marathon", "offset_s_per_mile": -10})
    check("offset: 10 s per mile faster than marathon pace sits 1-4 points above it",
          94 < fast[0] and fast[1] < 98, fast)
    z0 = zm.model_pct_for_offset(42195, 0, 0)
    equal("offset: a zero offset reproduces the model's own marathon range",
          (round(z0[0], 1), round(z0[1], 1)),
          tuple(round(x, 1) for x in zm.model_pct_for_distance(42195)))
    # the half-marathon book says strength (HMP - 10 s) is about 10K-15K pace
    hs = zm.race_anchor_range({"distance": "half_marathon", "offset_s_per_mile": -10})
    m10, m15 = zm.model_pct_for_distance(10000), zm.model_pct_for_distance(15000)
    check("hansons: HMP - 10 s lands between the model's 15K and 10K paces",
          m15[0] - 1 <= hs[0] and hs[1] <= m10[1] + 1, (hs, m15, m10))
    su = zm.race_anchor_range({"any_of": [{"distance": "5K"}, {"distance": "10K"}]})
    equal("any_of: '5K or 10K pace' is the union of both ranges", (su[0], su[1]), (100.0, 108.0))
    check("any_of: needs at least two alternatives",
          bool(zm.validate_race_anchor({"any_of": [{"distance": "5K"}]}, "running")))
    check("offset: a text offset is rejected",
          bool(zm.validate_race_anchor({"distance": "marathon", "offset_s_per_mile": "1:00"}, "running")))
    check("offset: refused on a duration anchor",
          bool(zm.validate_race_anchor({"duration_min": 30, "offset_s_per_mile": 10}, "running")))
    def hz(aid, key):
        return next(z for z in zm.load_author(aid)["zones"] if str(z["key"]) == key)
    for aid, key, want in [
            ("hansons_marathon", "Easy", "endurance"), ("hansons_marathon", "Tempo", "sub_threshold"),
            ("hansons_marathon", "Strength", "sub_threshold"), ("hansons_marathon", "Speed", "supra_threshold"),
            ("hansons_half", "Easy", "endurance"), ("hansons_half", "Long", "endurance"),
            ("hansons_half", "Marathon", "sub_threshold"), ("hansons_half", "Tempo", "sub_threshold"),
            ("hansons_half", "Strength", "threshold"), ("hansons_half", "Speed", "supra_threshold")]:
        equal(f"{aid}: {key} class", hz(aid, key)["physiological_class"], want)
    check("hansons: the two books are separate authors with different Tempo anchors",
          hz("hansons_marathon", "Tempo")["canonical"] != hz("hansons_half", "Tempo")["canonical"])
    check("hansons: an author with no native numbers still gets every metric estimated",
          all(hz("hansons_marathon", "Tempo")["ranges"].get(m) for m in ("pace", "lthr", "power")))
    # Every author file must be offered to the coach in the prompt
    import re as _re
    ptxt = open(os.path.join(ROOT, "Prompt", "infame_elite_endurance_coach.md"),
                encoding="utf-8").read()
    mm = _re.search(r"\[Methodology\][`*]* is one of: (.*?)\.\n", ptxt)
    listed = set(_re.findall(r"`([a-z_]+)`", mm.group(1))) if mm else set()
    on_disk = {os.path.basename(f)[:-5] for f in
               glob.glob(os.path.join(ROOT, "config", "authors", "[!_]*.yaml"))}
    check("prompt: the [Methodology] list names every author file", listed == on_disk,
          f"missing from prompt: {sorted(on_disk - listed)}; not on disk: {sorted(listed - on_disk)}")

    # Every author declares its KB file; every KB on disk is claimed (Mujika is a topic KB)
    claimed = {zm.load_author_raw(a).get("knowledge_file") for a in on_disk}
    check("authors: every author declares an existing knowledge_file",
          all(k and os.path.isfile(os.path.join(ROOT, "Knowledge", k)) for k in claimed), claimed)
    kb_disk = {os.path.relpath(f, os.path.join(ROOT, "Knowledge")).replace(os.sep, "/")
               for f in glob.glob(os.path.join(ROOT, "Knowledge", "**", "*.md"), recursive=True)
               if os.sep + "Catalogs" + os.sep not in f}
    orphans = {k for k in kb_disk - claimed if "Mujika" not in k}
    check("authors: no Knowledge file is left without an author", not orphans, sorted(orphans))

    # The KB file reaches the coach: zone-table headers and profile.md name it
    gen_txt = "".join(open(os.path.join(ROOT, "generated", fn), encoding="utf-8").read()
                      for fn in ("Simple_Table_Cycling_Training_Zones.md",
                                 "Simple_Table_Running_Training_Zones.md"))
    for a_id in sorted(on_disk):
        kf = zm.load_author_raw(a_id)["knowledge_file"]
        check(f"generated: {a_id} header names its Knowledge Base file",
              f"`Knowledge/{kf}`" in gen_txt, kf)
    check("generated: one Knowledge Base line per methodology",
          gen_txt.count("**Knowledge Base (Project file):**") == len(on_disk))
    import build_profile as _bp
    kl = "\n".join(_bp.knowledge_lines({"preferences": {"methodology": {
        "road_run": "hudson", "road_bike": "coggan", "trail_run": None, "gravel": "nope"}}}))
    check("profile: declared methodologies list their Knowledge file",
          "Hudson_Run_Faster_From_5K_to_Marathon.md" in kl and
          "Allen - Coggan_Training_and_Racing_With_a_Powermeter.md" in kl, kl)
    check("profile: null or unknown methodologies add no line",
          "nope" not in kl and "trail_run" not in kl)
    equal("profile: no declared methodology adds nothing", _bp.knowledge_lines({}), [])

    # ── Run Less Run Faster ────────────────────────────────────────
    def rl(key):
        return next(z for z in zm.load_author("run_less_run_faster")["zones"] if str(z["key"]) == key)
    for key, want in [("Long (HM/M)", "tempo"), ("MP", "sub_threshold"), ("Long (5K/10K)", "sub_threshold"),
                      ("LT", "sub_threshold"), ("HMP", "sub_threshold"), ("MT", "threshold"),
                      ("ST", "supra_threshold"), ("Repeats", "vo2max")]:
        equal(f"run_less_run_faster: {key} class", rl(key)["physiological_class"], want)
    tempo = [rl(k)["canonical"]["min"] for k in ("LT", "MT", "ST")]
    equal("run_less_run_faster: the three tempo paces ascend (LT < MT < ST)", tempo, sorted(tempo))
    check("run_less_run_faster: the repeats are faster than every tempo pace",
          rl("Repeats")["canonical"]["min"] > rl("ST")["canonical"]["max"])
    m5 = zm.model_pct_for_distance(5000)
    equal("speed ratio: MP is 86.7% of 5K speed",
          tuple(round(x, 1) for x in zm.race_anchor_range({"distance": "5K", "speed_ratio": 0.867})[:2]),
          (round(0.867 * m5[0], 1), round(0.867 * m5[1], 1)))
    check("speed ratio: refused together with an offset",
          bool(zm.validate_race_anchor({"distance": "5K", "speed_ratio": 0.9, "offset_s_per_mile": 5}, "running")))
    check("speed ratio: refused on a duration anchor",
          bool(zm.validate_race_anchor({"duration_min": 30, "speed_ratio": 0.9}, "running")))
    # The book's ratios sit close to the generic anchors: measured about 2.3 points
    # (MP) and 1.7 points (HMP) below them at the range edges — a documented gap
    check("run_less_run_faster: the book's MP is within 2.5 points of the marathon anchor",
          all(abs(rl("MP")["canonical"][k] - v) <= 2.5 for k, v in
              zip(("min", "max"), zm.model_pct_for_distance(42195))))
    check("run_less_run_faster: the book's HMP is within 2.0 points of the half-marathon anchor",
          all(abs(rl("HMP")["canonical"][k] - v) <= 2.0 for k, v in
              zip(("min", "max"), zm.model_pct_for_distance(21097.5))))

    # ── Hudson ─────────────────────────────────────────────────────
    def hd(key):
        return next(z for z in zm.load_author("hudson")["zones"] if str(z["key"]) == key)
    for key, want in [("Easy", "endurance"), ("MP", "sub_threshold"), ("T1", "sub_threshold"),
                      ("HMP", "sub_threshold"), ("T2", "threshold"), ("T3", "threshold"),
                      ("10K", "supra_threshold"), ("5K", "vo2max"), ("3K", "vo2max"),
                      ("1500m", "anaerobic"), ("Max", "neuromuscular")]:
        equal(f"hudson: {key} class", hd(key)["physiological_class"], want)
    ts = [hd(k)["canonical"]["min"] for k in ("T1", "T2", "T3")]
    equal("hudson: the three thresholds ascend (2.5 h < 90 min < 1 h)", ts, sorted(ts))
    # The book says a sub-elite runner's thresholds are about marathon pace,
    # half-marathon pace and a little slower than 10K pace: the crosswalk must agree.
    def mid(k):
        c = hd(k)["canonical"]
        return (c["min"] + c["max"]) / 2
    check("hudson: Threshold 1 is within 2 points of marathon pace", abs(mid("T1") - mid("MP")) <= 2.0,
          (mid("T1"), mid("MP")))
    check("hudson: Threshold 2 is within 2 points of half-marathon pace", abs(mid("T2") - mid("HMP")) <= 2.0,
          (mid("T2"), mid("HMP")))
    check("hudson: Threshold 3 is at or a little below 10K pace (within 3 points)",
          0 <= mid("10K") - mid("T3") <= 3.0, (mid("T3"), mid("10K")))
    check("hudson: Moderate and Hard are not rows (no published pace or class)",
          not any(str(z["key"]) in ("Moderate", "Hard") for z in zm.load_author("hudson")["zones"]))

    # ── Delta bands ───────────────────────────────────────────────
    cb = th["longitudinal"]["delta_bands"]["cycling"]
    equal("bands: cycling stable floor widened to -2.5", cb["stable"], -2.5)
    equal("bands: -2.0% reads as stable, not decline",
          longitudinal._band(-2.0, cb), "stable")
    equal("bands: -7.4% reads as decline",
          longitudinal._band(-7.4, cb), "decline")
    equal("bands: +5.0% reads as strong gain",
          longitudinal._band(5.0, cb), "strong_gain")

    # ── Power profile scoring ─────────────────────────────────────
    rows = ppcfg["anchors"]["men"]
    equal("profile: at the top row scores 100",
          power_profile._score(rows[0]["values"][0], 0, rows), 100.0)
    equal("profile: below the bottom row scores 0",
          power_profile._score(1.0, 0, rows), 0.0)
    check("profile: a mid value lands between",
          0 < power_profile._score(16.0, 0, rows) < 100)

    # A trained cyclist who never sprints must not be given a phenotype.
    pts = {"5": 431, "60": 343, "300": 236, "1200": 202, "3600": 185}
    pp = power_profile.analyze(pts, {"weight": 73.5, "sex": "M"}, ppcfg)
    equal("profile: untested sprint yields undetermined phenotype",
          pp["phenotype"], "undetermined")
    check("profile: names which columns were untested",
          "5s" in (pp.get("untested_columns") or []))
    equal("profile: falls back to the all-rounder test duration",
          pp["test_duration_minutes"],
          ppcfg["phenotype"]["test_duration_minutes"]["all_rounder"])

    # ── W' clamping ───────────────────────────────────────────────
    acts = [{"date": "2026-01-0%d" % (i + 1), "w_prime": 10000,
             "max_wbal_depletion": d}
            for i, d in enumerate([12000, 11000, 5000, 4000])]
    rep = longitudinal.repeatability(acts, th)
    equal("w_prime: impossible depletion is clamped to 100",
          rep["peak_depletion_previous_pct"], 100.0)
    equal("w_prime: clamped sessions are counted", rep["clamped_sessions"], 2)

    # ── Testing protocols ─────────────────────────────────────────
    prot = th["longitudinal"]["testing"]["protocols"]
    for anchor in ("5", "60", "300", "1200", "400", "1000", "3000"):
        check(f"protocols: {anchor} is defined", anchor in prot)
    check("protocols: no protocol prescribes a distance",
          not any(x in prot[k].lower()
                  for k in prot for x in (" 150m ", " 400m ", " 1200m ", " 2400m "))
          , "protocols must be duration-based")
    cp = th["longitudinal"]["testing"]["running_ftp_protocol"]
    equal("cp test: short leg is 3 minutes", cp["components"]["short_minutes"], 3)
    equal("cp test: long leg is 12 minutes", cp["components"]["long_minutes"], 12)
    equal("cp test: short runs before long", cp["order"], "short_before_long")
    equal("cp test: 30 minutes between components",
          cp["components"]["recovery_between_minutes"], 30)


    # ── Taper is evidence-based ───────────────────────────────────
    tp = th["taper"]
    equal("taper: 2 weeks per Bosquet 2007", tp["optimal_duration_days"], 14)
    equal("taper: volume cut 41-60%", (tp["volume_reduction_pct"]["min"],
                                       tp["volume_reduction_pct"]["max"]), (41, 60))
    equal("taper: intensity is maintained", tp["maintain_intensity"], True)
    equal("taper: TSB targets are labelled as heuristic, not evidence",
          tp["target_tsb_source"], "coach_heuristic")

    # ── Declared profile reaches profile.md ───────────────────────
    # config/athletes/<id>.yaml must be embedded in profile.md, because
    # profile.md is what actually reaches the Claude Project.
    import tempfile
    import build_profile as bpf
    cfg_dir = os.path.join(ROOT, "config", "athletes")

    lines, status = bpf.render_declared("TESTRAMP", cfg_dir)
    text = "\n".join(lines)
    equal("declared: committed TESTRAMP profile is included", status, "included")
    check("declared: section title names the yaml path",
          "## DECLARED PROFILE (config/athletes/TESTRAMP.yaml)" in text)
    check("declared: fields are embedded verbatim",
          "run_power_meter: true" in text)
    check("declared: full-line comments are removed",
          "TEST FIXTURE" not in text)
    check("declared: an empty intake date is flagged",
          "intake.completed" in text)

    lines, status = bpf.render_declared("i_does_not_exist", cfg_dir)
    equal("declared: a missing yaml is reported, not hidden", status, "missing")
    check("declared: a missing yaml tells the coach not to assume",
          "Do not assume them" in "\n".join(lines))

    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "iTEST.yaml"), "w", encoding="utf-8") as f:
            f.write("id: iTEST\navailability:\n  days: {mon: null, tue: 90, "
                    "wed: 60, thu: null, fri: 60, sat: 120, sun: null}\n")
        lines, _ = bpf.render_declared("iTEST", tmp)
        check("declared: weekly availability total is computed (5h 30m)",
              "total 5h 30m" in "\n".join(lines))

        with open(os.path.join(tmp, "iTEST.yaml"), "w", encoding="utf-8") as f:
            f.write("id: i000000\navailability:\n  days: {mon: 60, tue: \"varies\"}\n")
        text = "\n".join(bpf.render_declared("iTEST", tmp)[0])
        check("declared: an id that does not match the athlete is flagged",
              "may be a copy of another athlete" in text)
        check("declared: a non-numeric day marks the total as partial",
              "partial total 1h 00m" in text)

        # Current format: number = maximum, null = rest, ask/other text = undeclared
        with open(os.path.join(tmp, "iTEST.yaml"), "w", encoding="utf-8") as f:
            f.write("id: iTEST\navailability:\n  max_minutes: {mon: 60, tue: 150, "
                    "wed: ask, thu: 60, fri: varies, sat: 180, sun: null}\n"
                    "  long_days: {cycling: [tue], running: [sat]}\n"
                    "  weekly_hours: {min: 12, max: 14}\n"
                    "  changes_week_to_week: true\n")
        text = "\n".join(bpf.render_declared("iTEST", tmp)[0])
        check("availability: null is a declared rest day",
              "Rest days declared by the athlete:** sun" in text)
        check("availability: ask and unknown text are both 'not declared'",
              "Not declared — ask the head coach before planning:** wed, fri" in text)
        check("availability: declared maximums are summed (7h 30m)",
              "Sum of declared daily maximums:** 7h 30m" in text)
        check("availability: long days per sport are shown",
              "cycling tue · running sat" in text)
        check("availability: weekly hours range is shown", "12–14 h" in text)
        check("availability: week-to-week change asks for confirmation",
              "confirm the real week" in text)

        # Names the system would not recognize are flagged, not ignored
        with open(os.path.join(tmp, "iTEST.yaml"), "w", encoding="utf-8") as f:
            f.write("id: iTEST\ngoals:\n  - {priority: A+, event_type: stage_race, "
                    "discipline: mtb, stages: 4}\n  - {priority: AA, event_type: "
                    "etapas, discipline: bici}\ncontext: {disciplines: [road_bike, run]}\n"
                    "metric_overrides: {trail: lthr}\npreferences:\n  methodology: "
                    "{road_bike: friel_cycling, road_run: coggan, mtb: nadie}\n")
        text = "\n".join(bpf.render_declared("iTEST", tmp)[0])
        check("profile check: A+ and stage_race are valid (goal 1 clean)",
              "goals[1]" not in text)
        check("profile check: unknown priority is flagged", "'AA' is not one of" in text)
        check("profile check: unknown event type is flagged", "'etapas' is not one of" in text)
        check("profile check: unknown goal discipline is flagged",
              "`goals[2].discipline`: 'bici'" in text)
        check("profile check: old discipline name in context is flagged",
              "`context.disciplines`: 'run'" in text)
        check("profile check: old metric_overrides key is flagged",
              "`metric_overrides.trail`" in text)
        check("profile check: cross-sport methodology is flagged",
              "'coggan' is a cycling methodology on a running discipline" in text)
        check("profile check: unknown author is flagged", "'nadie' is not an author" in text)
        check("profile check: valid methodology is not flagged",
              "road_bike`: 'friel_cycling'" not in text)

        # The template itself must pass its own checks
        with open(os.path.join(cfg_dir, "_template.yaml"), encoding="utf-8") as f:
            tpl = yaml.safe_load(f)
        equal("template: passes the profile check with no warnings",
              bpf.profile_warnings(tpl), [])
        check("template: availability uses max_minutes, all days 'ask'",
              set(tpl["availability"]["max_minutes"].values()) == {"ask"})

        with open(os.path.join(tmp, "iTEST.yaml"), "w", encoding="utf-8") as f:
            f.write("id: iTEST\ngoals: [unclosed\n")
        _, status = bpf.render_declared("iTEST", tmp)
        equal("declared: invalid YAML is reported as unreadable", status, "unreadable")

    # ── PMC projection: weekday pattern fallback ──────────────────
    # An unplanned future day should fall back to the athlete's own
    # historical average for that weekday, never to zero -- and an
    # explicit Intervals.icu event (including an explicit zero, a declared
    # rest day) must always override that fallback. Dates are relative to
    # the real today, not a fixed date, because project_pmc anchors
    # weekday_load_pattern's history window to date.today() internally.
    from datetime import date, timedelta
    import build_state as bs
    today = date.today()
    wd_a = today.weekday()               # "heavy" weekday: load 80
    wd_b = (today.weekday() + 3) % 7     # "light" weekday: load 20
    wd_c = (today.weekday() + 1) % 7     # untouched weekday: load 0
    assert wd_c not in (wd_a, wd_b)      # +1 can never land on +0 or +3

    activities = (
        [{"date": (today - timedelta(days=7 * i)).isoformat(), "training_load": 80}
         for i in range(1, 9)] +
        [{"date": (today - timedelta(days=7 * i - 3)).isoformat(), "training_load": 20}
         for i in range(1, 9)]
    )

    pattern = bs.weekday_load_pattern(activities, as_of=today)
    check("pmc pattern: enough history produces a pattern", pattern is not None)
    if pattern is not None:
        equal("pmc pattern: heavy weekday average", pattern[wd_a], 80.0)
        equal("pmc pattern: light weekday average", pattern[wd_b], 20.0)
        equal("pmc pattern: untouched weekday averages to zero", pattern[wd_c], 0.0)

    equal("pmc pattern: below min_activities returns None",
          bs.weekday_load_pattern(activities[:8], as_of=today), None)

    short_span = [{"date": (today - timedelta(days=i + 1)).isoformat(),
                   "training_load": 50} for i in range(10)]
    equal("pmc pattern: enough activities but under 3 weeks of span returns None",
          bs.weekday_load_pattern(short_span, as_of=today), None)

    pmc = {"date": (today - timedelta(days=1)).isoformat(), "ctl": 50.0, "atl": 40.0}
    events = [
        {"date": (today + timedelta(days=2)).isoformat(), "planned_load": 0},
        {"date": (today + timedelta(days=5)).isoformat(), "planned_load": 150},
    ]
    proj = bs.project_pmc(pmc, events, activities, horizon_days=10)
    by_date = {s["date"]: s for s in proj["series"]}

    zeroed = by_date[(today + timedelta(days=2)).isoformat()]
    check("pmc projection: explicit zero-load event has no assumed_load",
          "assumed_load" not in zeroed)
    equal("pmc projection: explicit zero-load event keeps planned_load at 0",
          zeroed["planned_load"], 0)

    loaded = by_date[(today + timedelta(days=5)).isoformat()]
    check("pmc projection: explicit nonzero event has no assumed_load",
          "assumed_load" not in loaded)
    equal("pmc projection: explicit event's planned_load wins over the pattern",
          loaded["planned_load"], 150)

    unplanned_date = today + timedelta(days=1)
    unplanned = by_date[unplanned_date.isoformat()]
    check("pmc projection: unplanned day gets an assumed_load",
          "assumed_load" in unplanned)
    if "assumed_load" in unplanned and pattern is not None:
        equal("pmc projection: assumed_load matches the weekday pattern",
              unplanned["assumed_load"], pattern[unplanned_date.weekday()])

    equal("pmc projection: only the nonzero explicit day counts as planned",
          proj["days_with_planned_load"], 1)
    equal("pmc projection: the other 8 days (10 - 2 explicit) are assumed",
          proj["days_with_assumed_load"], 8)

    # ── taper_check: description whitespace ────────────────────────
    # A YAML `>` folded block scalar keeps a trailing newline by default;
    # left unstripped, it lands inside the rendered "**{race}**" line and
    # breaks it mid-markdown. Any athlete's goals[].description written
    # that way must still render clean.
    thresholds = bs.load_thresholds()
    messy_goal = [{"description": "Barbie 10k — llegar en su mejor forma.\n",
                   "date": (today + timedelta(days=10)).isoformat(),
                   "priority": "A", "event_type": "road_race"}]
    messy_taper = bs.taper_check(None, messy_goal, thresholds)
    equal("taper_check strips a trailing newline from goals[].description",
          messy_taper["race"], "Barbie 10k — llegar en su mejor forma.")


# ══════════════════════════════════════════════════════════════════
# GOLDEN TESTS — full state engine per fixture
# ══════════════════════════════════════════════════════════════════

def build_for_fixture(name):
    """Run the real state engine over one fixture and return its state.json."""
    import build_state
    src = os.path.join(FIXTURES, name, "athlete_data.json")
    data_dir = os.path.join(ROOT, "data", f"_test_{name}")
    os.makedirs(data_dir, exist_ok=True)
    with open(src, encoding="utf-8") as f:
        payload = json.load(f)
    with open(os.path.join(data_dir, "athlete_data.json"), "w",
              encoding="utf-8") as f:
        json.dump(payload, f)

    # A fixture may also declare a goals profile (taper_check reads it from
    # config/athletes/<id>.yaml, never from Intervals.icu event fields --
    # see build_state.load_declared_goals). Copy it into place under the
    # same _test_<name> id, or remove any stale one left by a previous run
    # if this fixture no longer ships one.
    athletes_cfg = os.path.join(ROOT, "config", "athletes")
    os.makedirs(athletes_cfg, exist_ok=True)
    decl_src = os.path.join(FIXTURES, name, "declared_profile.yaml")
    decl_dst = os.path.join(athletes_cfg, f"_test_{name}.yaml")
    if os.path.exists(decl_src):
        shutil.copy(decl_src, decl_dst)
    elif os.path.exists(decl_dst):
        os.remove(decl_dst)

    th, _, _ = load_cfg()
    # build() reports where it wrote; that is useful in normal use and noise here.
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        result = build_state.build(f"_test_{name}", th, quiet=True)
    return strip_volatile(result)



def architecture_tests():
    """engine/architecture.py: classify a session's Main Set from its own
    written text alone. Every case here is either a hand-built example of
    one named shape, or a real session pulled from a live account during
    development (kept verbatim as a regression case, not just a synthetic
    one) -- see engine/architecture.py's own module docstring for the
    documented, deliberate gaps these cases do not cover."""
    import architecture
    from validate_block import load_thresholds_only
    th = load_thresholds_only()

    def classify(text, event_type="Ride"):
        return architecture.classify_session(text, event_type=event_type,
                                              thresholds=th)

    r = classify("Main Set 5x\n- 4m 100-105%\n- 4m 50-55%")
    equal("architecture: identical on/off reps -> classic_intervals",
          r["architecture"], "classic_intervals")
    check("architecture: no combo on a single shape", not r["combo"])

    r = classify("Main Set\n- 25m 94-96%")
    equal("architecture: one continuous block -> sustained_effort",
          r["architecture"], "sustained_effort")

    r = classify("Main Set 4x\n- 3m 96-98%\n- 2m 109-111%")
    equal("architecture: alternating sub/supra-threshold -> over_unders",
          r["architecture"], "over_unders")

    r = classify("Main Set 4x\n- 3m 84-86%\n- 3m 96-98%")
    equal("architecture: alternating, both sub-threshold, folds into over_unders",
          r["architecture"], "over_unders")

    r = classify("Main Set 3x\n- 4m 88-90%\n- 15s 130-140%")
    equal("architecture: short burst on a long base -> surges_on_base",
          r["architecture"], "surges_on_base")

    r = classify("Main Set 6x\n- 10s 180-190%\n- 50s 45-55%")
    equal("architecture: short/max/long-recovery -> sprints",
          r["architecture"], "sprints")

    r = classify("Main Set\n- 20m ramp 70-100%")
    equal("architecture: a rising ramp as the work itself -> single_ramp",
          r["architecture"], "single_ramp")

    r = classify("Main Set 4x\n- 10s 180-190%\n- 50s 45-55%\n\n"
                  "- 5m 55-65%\n\nMain Set 4x\n- 4m 100-105%\n- 3m 55-65%")
    equal("architecture: two distinct shapes -> the bigger one is primary",
          r["architecture"], "classic_intervals")
    check("architecture: two distinct shapes flag as a combo", r["combo"])
    equal("architecture: combo sequence keeps only real-load shapes, in order",
          r["sequence"], ["sprints", "classic_intervals"])
    check("architecture: a zero-load filler step between shapes is not its own entry",
          "endurance_cadence" not in r["sequence"])

    r = classify("- 20m 55-70%")
    equal("architecture: nothing reaches work intensity -> endurance_cadence",
          r["architecture"], "endurance_cadence")

    r = classify("# Descanso\n")
    check("architecture: a rest-day note has nothing classifiable",
          not r["ok"] and r["architecture"] is None)

    r = classify("")
    check("architecture: an empty description has nothing classifiable",
          not r["ok"])

    r = classify("- 3km 75-85% Pace")
    check("architecture: a distance-only step is excluded, not zero-length",
          not r["ok"])

    # No explicit "Main Set" header at all -- real historical text written
    # before that hard constraint existed. Confirms the position-based
    # fallback, not just the declared-section path above.
    real_sst_ramp = (
        "Warmup\n- 10m ramp 75-75%\n- 1m 45-55%\n\n"
        "2x\n- 5m ramp 76-86%\n- 2m ramp 45-55%\n\n"
        "5x\n- 3m 76-86%\n- 3m 45-55%\n\n- 5m 45-55%\n\n"
        "Cooldown\n- 5m ramp 65-50%\n")
    r = classify(real_sst_ramp)
    check("architecture: no declared Main Set falls back to finding it by position",
          r["ok"] and r["architecture"] is not None)
    equal("architecture: real SST-ramp session reads as a combo of two shapes",
          r["sequence"], ["single_ramp", "classic_intervals"])

    # A real, genuinely compound session (cadence-alternating work, several
    # intensity changes inside one repeat) -- the biggest unit matches none
    # of the 14 shapes. Confirms this reads as ok / architecture None with a
    # reason, never as a wrong shape standing in for it.
    real_compound = (
        "Warmup\n- 8m ramp 44-75%\n\n- 30s 104-113.9%\n- 3m 45-55%\n"
        "- 30s 104-113.9%\n\n2x\n- 5m 45-55%\n- 1m 80-90% 85rpm\n"
        "- 1m 80-90% 65rpm\n- 1m 80-90%\n- 1m 80-90% 65rpm\n- 1m 80-90%\n"
        "- 1m 80-90% 65rpm\n- 1m 80-90%\n- 1m 80-90% 65rpm\n- 1m30s 45-55%\n"
        "- 5m 90-100%\n- 1m30s 45-55%\n- 3m 95-105%\n\n- 10m 45-55%\n")
    r = classify(real_compound)
    check("architecture: a real compound session is ok with no forced match",
          r["ok"] and r["architecture"] is None and r["reason"])

    r = classify("Main Set\n- 120m 55-75% Pace", event_type="Run")
    equal("architecture: %Pace classifies the same way as %power",
          r["architecture"], "endurance_cadence")

    r = classify("Main Set 5x\n- 8m 95-100%\n- 4m 50-55%")
    equal("class: a threshold interval reads as threshold from generic cutpoints",
          r["class"], "threshold")
    r = classify("Main Set 5x\n- 4m 100-105%\n- 4m 50-55%")
    equal("class: 100-105% (above LT2/CP) reads as supra_threshold (v7.2)",
          r["class"], "supra_threshold")

    # ── Frequency tally (the idea-bank input) ───────────────────────
    rows = [
        {"architecture": "sustained_effort", "sequence": ["sustained_effort"]},
        {"architecture": "sustained_effort", "sequence": ["sustained_effort"]},
        {"architecture": "classic_intervals", "sequence": ["sprints", "classic_intervals"]},
    ]
    counts, unused = architecture.frequency(rows)
    equal("frequency: counts each occurrence", counts["sustained_effort"], 2)
    equal("frequency: a combo counts every shape in it, not just the primary",
          counts["sprints"], 1)
    check("frequency: an architecture with zero uses is still in the tally",
          counts["over_unders"] == 0)
    check("frequency: unused lists every architecture that never appeared",
          "over_unders" in unused and "sustained_effort" not in unused
          and "sprints" not in unused)
    equal("frequency: all 14 known architectures are covered",
          set(counts), set(architecture.ALL_ARCHITECTURES))

def golden_tests(update=False):
    if not os.path.isdir(FIXTURES):
        FAILED.append(("golden: fixtures missing",
                       "run: python tests/make_fixtures.py"))
        return

    # Every fixture's athlete_data.json is dated relative to "today" (see
    # make_fixtures.py) precisely so it never ages out of a rolling window —
    # but that guarantee only holds at the moment the fixture is generated.
    # A fixture written once and left on disk drifts the same way real
    # athlete data would if nobody ever pulled fresh data: acute/chronic
    # load windows, curve-progression windows, and durability windows all
    # silently stop matching what expected_state.json was frozen against,
    # for no reason connected to any code change. Regenerating here, right
    # before comparison, keeps every fixture anchored to the same "today"
    # the engine is about to evaluate it against — so the golden suite can
    # never again fail purely because time passed since someone last
    # remembered to run make_fixtures.py by hand.
    import make_fixtures
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        make_fixtures.main()

    for name in sorted(os.listdir(FIXTURES)):
        fdir = os.path.join(FIXTURES, name)
        if not os.path.isdir(fdir):
            continue
        expected_path = os.path.join(fdir, "expected_state.json")

        try:
            got = build_for_fixture(name)
        except Exception as e:
            FAILED.append((f"golden: {name}", f"engine raised {type(e).__name__}: {e}"))
            continue

        if update or not os.path.exists(expected_path):
            with open(expected_path, "w", encoding="utf-8") as f:
                json.dump(got, f, indent=2, ensure_ascii=False, sort_keys=True)
            PASSED.append(f"golden: {name} (written)")
            continue

        with open(expected_path, encoding="utf-8") as f:
            want = json.load(f)

        out = []
        diff(name, got, want, out)
        if out:
            FAILED.append((f"golden: {name}", "\n" + "\n".join(out[:25])
                           + (f"\n    ... and {len(out) - 25} more"
                              if len(out) > 25 else "")))
        else:
            PASSED.append(f"golden: {name}")


# ══════════════════════════════════════════════════════════════════
# BLOCK VALIDATION TESTS
# ══════════════════════════════════════════════════════════════════

# file, expected exit code, error codes that must appear.
#
# The treadmill cases prove that a continuous ramp is rejected on a treadmill
# whether or not the athlete has a profile, while a stepped progression passes.
# They reference the committed TESTRAMP profile rather than a real athlete,
# because a real profile is gitignored and the test would then pass on one
# machine and fail on another.
BLOCK_CASES = [
    ("good_trainer_coggan.md", 0, []),
    ("bad_road.md", 1, ["HC-LANG", "HC-NESTED", "HC-FORMAT", "HC-RAMP",
                        "HC-FLOOR", "HC-CAT"]),
    ("koop_trail.md", 1, ["HC-RPE", "HC-RAMP"]),
    # A continuous ramp is impossible on a treadmill even when the athlete's
    # profile exists; a progression there is a staircase of ordinary steps.
    ("treadmill_ramp.md", 1, ["HC-RAMP"]),
    ("treadmill_steps.md", 0, []),
    ("treadmill_ramp_denied.md", 1, ["HC-RAMP"]),
    # Carmichael anchors on his own field test, not on threshold. A block written
    # on the threshold scale must still match his zones, via the declared factor.
    ("carmichael_ss.md", 0, []),
    # Header labels translated to Spanish ([Semana], [Fecha], [Categoría]...) and
    # one header wrapped in markdown bold. The validator must translate them and
    # pass, instead of reading the whole file as one session with no header.
    ("spanish_labels.md", 0, ["translated header label [Semana] -> [Week]",
                              "translated header label [Metodología] -> [Methodology]",
                              "removed markdown bold"]),
    # A real Infame delivery, pasted exactly as the coach receives it -- missing
    # code fences, a Duration with "(estimado)" and a leading ~, a Rest day with
    # "--" as methodology, and a race session titled with a bare distance line.
    # None of this should require manual cleanup before validating.
    ("vianey_raw_unfixed.md", 0, []),
]


def block_tests():
    import shutil
    import tempfile
    script = os.path.join(ROOT, "verify", "validate_block.py")
    tmpdir = tempfile.mkdtemp(prefix="infame_blocks_")
    for fname, want_code, want_errors in BLOCK_CASES:
        src = os.path.join(BLOCKS, fname)
        if not os.path.exists(src):
            FAILED.append((f"block: {fname}", "fixture not found"))
            continue
        # The validator rewrites the file it checks when it auto-corrects
        # something. Validate a temporary copy, so a fixture that exists to
        # test those corrections is never repaired on disk by its own test.
        path = os.path.join(tmpdir, fname)
        shutil.copy2(src, path)
        # On Windows a captured subprocess inherits the locale encoding (cp1252),
        # not UTF-8, and the validator prints em dashes and middle dots. Without
        # this the child crashes on encoding rather than on anything real.
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        proc = subprocess.run([sys.executable, script, path, "--quiet"],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env)
        out = proc.stdout + proc.stderr
        if proc.returncode not in (0, 1):
            FAILED.append((f"block: {fname} crashed",
                           f"exit {proc.returncode}\n{out.strip()[:500]}"))
            continue
        equal(f"block: {fname} exit code", proc.returncode, want_code)
        for code in want_errors:
            check(f"block: {fname} reports {code}", code in out,
                  "not found in validator output")
    shutil.rmtree(tmpdir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def cleanup():
    import shutil
    data = os.path.join(ROOT, "data")
    if not os.path.isdir(data):
        return
    for d in os.listdir(data):
        if d.startswith("_test_"):
            shutil.rmtree(os.path.join(data, d), ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Infame v6 regression tests")
    ap.add_argument("--unit", action="store_true")
    ap.add_argument("--golden", action="store_true")
    ap.add_argument("--blocks", action="store_true")
    ap.add_argument("--update", action="store_true",
                    help="accept current output as the new golden baseline")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    run_all = not (args.unit or args.golden or args.blocks)

    print("Infame v6 — regression tests\n")

    if run_all or args.unit:
        print("Unit tests...")
        try:
            unit_tests()
        except Exception as e:
            FAILED.append(("unit tests", f"raised {type(e).__name__}: {e}"))
        try:
            architecture_tests()
        except Exception as e:
            FAILED.append(("architecture tests", f"raised {type(e).__name__}: {e}"))

    if run_all or args.blocks:
        print("Block validation...")
        block_tests()

    if run_all or args.golden:
        print("Golden comparisons..."
              + ("  (updating baselines)" if args.update else ""))
        golden_tests(update=args.update)
        cleanup()

    print()
    if args.verbose:
        for name in PASSED:
            print(f"  PASS  {name}")
        print()

    for name, detail in FAILED:
        print(f"  FAIL  {name}")
        if detail:
            print(f"        {detail}")

    total = len(PASSED) + len(FAILED)
    print()
    print(f"{len(PASSED)}/{total} passed.")
    if FAILED:
        print("\nA golden failure is not automatically a bug — it means output "
              "changed.\nRead the diff. If the change was intended, re-run with "
              "--update and\ncommit the new baselines alongside the change that "
              "caused them.")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
