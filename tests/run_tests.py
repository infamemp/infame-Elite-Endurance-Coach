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
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
sys.path.insert(0, os.path.join(ROOT, "verify"))

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
    return rd("decision_thresholds.yaml"), rd("tss_classes.yaml"), \
        rd("power_profile.yaml")


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
    check("ramps: road forbidden", "road" in r["forbidden_disciplines"])
    check("ramps: trail forbidden", "trail" in r["forbidden_disciplines"])
    check("ramps: treadmill is override-eligible, not forbidden",
          "treadmill" in (r.get("override_eligible") or {})
          and "treadmill" not in r["forbidden_disciplines"])
    check("ramps: no magnitude cap is imposed",
          "no_magnitude_limit" in r,
          "a cap would prohibit a progressive ramp test")

    # ── Anchored authors are converted before matching ────────────
    carm = yaml.safe_load(open(os.path.join(ROOT, "config", "authors",
                                            "carmichael.yaml"), encoding="utf-8"))
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

    th, _, _ = load_cfg()
    # build() reports where it wrote; that is useful in normal use and noise here.
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        result = build_state.build(f"_test_{name}", th, quiet=True)
    return strip_volatile(result)


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
# The two treadmill cases are the same block pointed at different athletes, and
# together they prove the override works in both directions: permitted when the
# profile asks for it, blocked when it does not. They reference the committed
# TESTRAMP profile rather than a real athlete, because a real profile is
# gitignored and the test would then pass on one machine and fail on another.
BLOCK_CASES = [
    ("good_trainer_coggan.md", 0, []),
    ("bad_road.md", 1, ["HC-LANG", "HC-NESTED", "HC-FORMAT", "HC-RAMP",
                        "HC-FLOOR", "HC-CAT"]),
    ("koop_trail.md", 1, ["HC-DUAL", "HC-RAMP"]),
    ("treadmill_ramp.md", 0, []),
    ("treadmill_ramp_denied.md", 1, ["HC-RAMP"]),
    # Carmichael anchors on his own field test, not on threshold. A block written
    # on the threshold scale must still match his zones, via the declared factor.
    ("carmichael_ss.md", 0, []),
    # A real Infame delivery, pasted exactly as the coach receives it -- missing
    # code fences, a Duration with "(estimado)" and a leading ~, a Rest day with
    # "--" as methodology, and a race session titled with a bare distance line.
    # None of this should require manual cleanup before validating.
    ("vianey_raw_unfixed.md", 0, []),
]


def block_tests():
    script = os.path.join(ROOT, "verify", "validate_block.py")
    for fname, want_code, want_errors in BLOCK_CASES:
        path = os.path.join(BLOCKS, fname)
        if not os.path.exists(path):
            FAILED.append((f"block: {fname}", "fixture not found"))
            continue
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
