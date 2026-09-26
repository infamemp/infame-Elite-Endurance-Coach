"""
zone_model.py — Infame Elite Endurance Coach v7.2
=================================================
The one place where an author's native zones become a full, standardized zone
table: every metric of the sport, the physiological class and the domain.

    native author YAML  +  config/crosswalk.yaml  +  config/tss_classes.yaml
                              │
                              ▼
                    resolve_author()  →  resolved author dict

Everything downstream reads the resolved form: the Markdown generator
(build_zone_tables.py), the block validator (verify/validate_block.py) and the
state engine (through the derived cutpoints). No estimate, class or domain is
ever typed by hand into an author file.

Resolution rules (deterministic — the same input always gives the same output):

  1. Canonical axis. Each zone's range is converted to "% of threshold" using
     the author's most reliable native metric, in this order:
     power > pace > lthr > hrmax. An anchored metric (Carmichael) is first
     multiplied by its sourced factor. HRmax is converted to LTHR by the
     author's own threshold-%-of-HRmax, or the crosswalk default.
  2. Class. The class band (tss_classes.yaml → bands) that contains the
     midpoint of the canonical range. An open upper bound ("> X") uses X; an
     open lower bound uses the prescription floor.
  3. Stated class. When the author explicitly names the zone's physiological
     target (`stated_class`), it is compared with the computed class. A
     disagreement is an ERROR unless the zone carries a `resolution`
     (use: stated | computed, reason). A zone with no native numbers at all
     (Koop, Coggan Level 7) takes its class from `stated_class`, which is then
     required.
  4. Estimates. Every metric of the sport the author does not publish is
     filled from the canonical range through the crosswalk and flagged
     "estimated". Heart rate is not estimated for extreme-domain zones.
     A zone with no native numbers gets its class band as its range.
  5. Domain. The domain of the class. The zone is additionally flagged when its
     range crosses into another domain, or touches the LT1 band.
  5b. Race anchors (running). A zone may declare `race_anchor` — a race
     distance ("marathon"), a sustainable duration (`duration_min: 120`), a
     span between two of them (`from`/`to`), either of two (`any_of`), or a
     distance with a pace offset in seconds per mile (`offset_s_per_mile`,
     positive = slower: "goal marathon pace + 1:00 to 2:00") — instead of a
     number. The range is read from
     config/crosswalk.yaml → running.race_anchors: distances from Palladino's
     published table, durations from the Daniels-Gilbert model. When a zone has
     both native numbers and an anchor, the native numbers govern and the
     anchor is used as a consistency check (warning above 3 points apart).
  5c. Threshold definition. An author whose own 100% is not the 60-minute
     pace declares `anchor.duration_min`; the factor is computed from the model
     and applied like any other anchor. Nothing is shifted silently.
  5d. Borderline. A zone whose midpoint is within 1 point of a class boundary
     is flagged in its Notes; the class stays as computed.
  6. RPE. The author's native RPE. When the author publishes none, the class's
     standard CR-10 band, flagged "estimated". A native RPE that does not
     overlap the class band widened by one point is reported (warning only —
     authors calibrate RPE differently, and the author's RPE is what is emitted).
"""

import copy
import math
import os

try:
    import yaml
except ImportError:  # pragma: no cover
    raise SystemExit("Missing dependency. Run: pip install pyyaml jsonschema")

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(ROOT, "config")

CLASS_ORDER = ["recovery", "endurance", "tempo", "sub_threshold", "threshold",
               "supra_threshold", "vo2max", "anaerobic", "neuromuscular"]
CLASS_RANK = {c: i for i, c in enumerate(CLASS_ORDER)}
DOMAIN_ORDER = ["moderate", "heavy", "severe", "extreme"]

# Order in which a zone's native metric is trusted for the canonical axis.
PRIMARY_ORDER = ["power", "pace", "lthr", "hrmax"]

# A zone whose midpoint is this close to a class boundary is flagged borderline.
# 1 point (not 2): the threshold class is only 4 points wide, so at 2 nearly
# every threshold zone would be flagged and the flag would mean nothing.
BORDERLINE_PTS = 1.0

_cache = {}


def _read(name):
    if name not in _cache:
        with open(os.path.join(CONFIG, name), encoding="utf-8") as f:
            _cache[name] = yaml.safe_load(f)
    return _cache[name]


def load_crosswalk():
    return _read("crosswalk.yaml")


def load_classes():
    return _read("tss_classes.yaml")


def load_thresholds_raw():
    return _read("decision_thresholds.yaml")


def sport_metrics(sport):
    """The metric columns every table of this sport carries (besides RPE)."""
    return list(load_crosswalk()[sport]["metrics"])


# ──────────────────────────────────────────────────────────────────
# Piecewise conversions
# ──────────────────────────────────────────────────────────────────

def _interp(x, pts):
    """Linear interpolation through sorted (x, y) knots. None outside."""
    if x is None:
        return None
    if x < pts[0][0] or x > pts[-1][0]:
        return None
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return None


def _conv(sport, metric):
    return load_crosswalk()[sport]["conversions"].get(metric)


def hrmax_threshold_pct(author):
    own = author.get("hrmax_threshold_pct")
    if own:
        return float(own["value"])
    return float(load_crosswalk()["hrmax_to_lthr"]["default_threshold_pct_of_hrmax"])


def anchor_factor_value(anc):
    """The factor of an `anchor` block: the sourced `factor_from_threshold`, or,
    for an author who defines threshold by a sustainable duration, the factor
    the duration model computes. None if the block declares neither."""
    if not anc:
        return None
    if anc.get("factor_from_threshold"):
        return float(anc["factor_from_threshold"])
    if anc.get("duration_min"):
        return round(speed_pct_at_duration(float(anc["duration_min"])) / 100.0, 3)
    return None


def anchor_factor(author, metric):
    anc = author.get("anchor")
    if anc and anc.get("metric") == metric:
        f = anchor_factor_value(anc)
        return float(f) if f else 1.0
    return 1.0


# ──────────────────────────────────────────────────────────────────
# Race anchors (running): distance and duration → % of threshold pace
# ──────────────────────────────────────────────────────────────────

def _ra():
    return load_crosswalk()["running"]["race_anchors"]


def _dm():
    return _ra()["duration_model"]


def _frac_vo2(t):
    m = _dm()["fraction_vo2max"]
    return (m["a"] + m["b"] * math.exp(-m["k1"] * t) + m["c"] * math.exp(-m["k2"] * t))


def _vo2(v):
    m = _dm()["vo2_of_speed"]
    return m["p0"] + m["p1"] * v + m["p2"] * v * v


def _speed(vo):
    m = _dm()["vo2_of_speed"]
    a, b, c = m["p2"], m["p1"], m["p0"] - vo
    return (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)


def _speed_at(vdot, t):
    return _speed(_frac_vo2(t) * vdot)


def speed_pct_at_duration(t_min, vdot=None):
    """Speed sustainable for `t_min` minutes as a % of the 60-minute speed.
    Level-independent within ~0.1 point, so a reference VDOT is enough."""
    dm = _dm()
    vdot = vdot or dm["reference_vdots"][1]
    return 100.0 * _speed_at(vdot, t_min) / _speed_at(vdot, dm["threshold_duration_min"])


def _race_minutes(vdot, meters):
    lo, hi = 1.0, 900.0
    for _ in range(80):
        t = (lo + hi) / 2.0
        if _vo2(meters / t) / _frac_vo2(t) > vdot:
            lo = t
        else:
            hi = t
    return t


def model_pct_for_distance(meters):
    """(min, max) across the reference VDOTs, as % of the 60-minute speed."""
    dm = _dm()
    xs = [100.0 * (meters / _race_minutes(v, meters)) /
          _speed_at(v, dm["threshold_duration_min"]) for v in dm["reference_vdots"]]
    return min(xs), max(xs)


def _distance_key(name):
    ra = _ra()
    n = str(name)
    n = ra["aliases"].get(n, n)
    return n if n in ra["distances"] else None


def _anchor_point(spec):
    """One end of a span: (lo, hi) of a single distance or duration anchor."""
    if not isinstance(spec, dict):
        raise ValueError(f"race anchor point must be a mapping, got {spec!r}")
    if "distance" in spec:
        k = _distance_key(spec["distance"])
        if not k:
            raise ValueError(f"unknown race distance '{spec['distance']}'")
        d = _ra()["distances"][k]
        name = k.replace("_", " ")
        if spec.get("offset_s_per_mile") is not None:
            lo_off, hi_off = _offset_bounds(spec["offset_s_per_mile"])
            lo, hi = model_pct_for_offset(d["meters"], lo_off, hi_off)
            return lo, hi, f"{name} race pace {_fmt_offset(lo_off, hi_off)}"
        return float(d["min"]), float(d["max"]), f"{name} race pace"
    if "duration_min" in spec:
        c = speed_pct_at_duration(float(spec["duration_min"]))
        h = float(_dm()["half_width"])
        return c - h, c + h, f"{_num_min(spec['duration_min'])} sustainable pace"
    raise ValueError("race anchor needs `distance` or `duration_min`")


def _offset_bounds(off):
    """`offset_s_per_mile`: a number or {min, max}, in seconds per mile,
    positive = slower than the anchor pace. Returns (lo, hi)."""
    if isinstance(off, dict):
        a, b = off.get("min"), off.get("max")
    else:
        a = b = off
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (a, b)):
        raise ValueError("offset_s_per_mile must be a number or {min, max} in seconds")
    return float(min(a, b)), float(max(a, b))


def _fmt_offset(lo, hi):
    def one(x):
        s = abs(int(round(x)))
        return f"{s // 60}:{s % 60:02d}"
    sign = lambda x: "+" if x >= 0 else "-"  # noqa: E731
    if lo == hi:
        return f"{sign(lo)}{one(lo)} per mile"
    if lo >= 0 and hi >= 0:
        return f"+{one(lo)} to +{one(hi)} per mile"
    return f"{sign(lo)}{one(lo)} to {sign(hi)}{one(hi)} per mile"


MILE_M = 1609.344


def model_pct_for_offset(meters, off_lo, off_hi):
    """Pace at a race distance plus an offset in seconds per mile, as a % of the
    60-minute speed, across the reference VDOTs. The anchor pace depends on the
    runner's level, so the range is the full spread over levels and offsets."""
    dm = _dm()
    xs = []
    for v in dm["reference_vdots"]:
        speed = meters / _race_minutes(v, meters)               # m/min at the anchor
        pace = MILE_M / speed * 60.0                            # s per mile
        for off in (off_lo, off_hi):
            new_speed = MILE_M / (pace + off) * 60.0            # m/min
            xs.append(100.0 * new_speed / _speed_at(v, dm["threshold_duration_min"]))
    return min(xs), max(xs)


def _num_min(v):
    v = float(v)
    if v >= 60 and v % 30 == 0:
        h = v / 60
        return f"{h:g} h"
    return f"{v:g} min"


def race_anchor_range(ra):
    """(t_lo, t_hi, description) on the canonical axis. t_hi None = open."""
    if "any_of" in ra:
        pts = [_anchor_point(p) for p in ra["any_of"]]
        return (min(p[0] for p in pts), max(p[1] for p in pts),
                " or ".join(p[2] for p in pts))
    if "from" in ra or "to" in ra:
        a = _anchor_point(ra["from"])
        centre_a = (a[0] + a[1]) / 2.0
        if ra.get("to") is None:
            return centre_a, None, f"from {a[2]} upward"
        b = _anchor_point(ra["to"])
        centre_b = (b[0] + b[1]) / 2.0
        lo, hi = sorted((centre_a, centre_b))
        return lo, hi, f"between {a[2]} and {b[2]}"
    lo, hi, desc = _anchor_point(ra)
    return lo, hi, desc


def validate_race_anchor(ra, sport):
    errs = []
    if sport != "running":
        errs.append("race_anchor is running-only")
        return errs
    try:
        race_anchor_range(ra)
    except (ValueError, KeyError, TypeError) as e:
        errs.append(str(e))
    if not ({"distance", "duration_min", "from", "any_of"} & set(ra)):
        errs.append("race_anchor needs `distance`, `duration_min`, `from` or `any_of`")
    if "any_of" in ra and (not isinstance(ra["any_of"], list) or len(ra["any_of"]) < 2):
        errs.append("any_of needs a list of at least two anchors")
    if ra.get("offset_s_per_mile") is not None and "distance" not in ra:
        errs.append("offset_s_per_mile only applies to a distance anchor")
    return errs


def race_anchor_residuals():
    """The model against the published distance ranges: rows of
    (distance, published (min,max), model (min,max), centre difference)."""
    out = []
    for k, d in _ra()["distances"].items():
        mlo, mhi = model_pct_for_distance(d["meters"])
        dc = (mlo + mhi) / 2.0 - (d["min"] + d["max"]) / 2.0
        out.append((k, (d["min"], d["max"]), (mlo, mhi), dc))
    return out


def to_canonical(value, metric, sport, author=None):
    """Convert a value in `metric` (as the author publishes it) to % threshold.
    Returns None when the conversion is undefined for that value."""
    if value is None:
        return None
    author = author or {}
    value = value * anchor_factor(author, metric)
    if metric == "hrmax":
        value = value * 100.0 / hrmax_threshold_pct(author)
        metric = "lthr"
    c = _conv(sport, metric)
    if c is None:
        return None
    if c.get("identity"):
        return float(value)
    # knots are [canonical, metric] — invert
    pts = sorted((m, t) for t, m in c["knots"])
    return _interp(value, pts)


def from_canonical(t, metric, sport, author=None):
    """Convert % threshold to `metric` on the threshold scale. None when
    outside the crosswalk (no extrapolation)."""
    if t is None:
        return None
    if metric == "hrmax":
        lthr = from_canonical(t, "lthr", sport, author)
        if lthr is None:
            return None
        return lthr * hrmax_threshold_pct(author or {}) / 100.0
    c = _conv(sport, metric)
    if c is None:
        return None
    if c.get("identity"):
        return float(t)
    pts = sorted((a, b) for a, b in c["knots"])
    return _interp(t, pts)


# ──────────────────────────────────────────────────────────────────
# Classes and domains
# ──────────────────────────────────────────────────────────────────

def class_bands(sport):
    return load_classes()["bands"][sport]


def class_of(t, sport):
    for cls in CLASS_ORDER:
        b = class_bands(sport)[cls]
        lo = b.get("min") or 0
        hi = b.get("max")
        if lo <= t and (hi is None or t < hi):
            return cls
    return None


def domain_of_class(cls):
    return load_classes()["classes"][cls]["domain"]


def domain_of(t, sport):
    cls = class_of(t, sport)
    return domain_of_class(cls) if cls else None


def class_rpe(cls):
    return dict(load_classes()["classes"][cls]["rpe"])


def derived_cutpoints():
    """Per-sport, per-metric class cutpoints on each metric's own scale,
    derived from the canonical bands through the crosswalk. Consumers that
    classify a loose target (validator fallback, architecture record) use
    these. They are computed, never stored."""
    out = {}
    for sport in ("cycling", "running"):
        out[sport] = {}
        metrics = sport_metrics(sport) + ["hrmax"]
        for metric in metrics:
            bands = {}
            no_hr = set(load_crosswalk().get("no_hr_estimate_domains") or [])
            for cls in CLASS_ORDER:
                if metric in ("lthr", "hrmax") and domain_of_class(cls) in no_hr:
                    # heart rate cannot resolve efforts that end before it
                    # catches up: those classes merge into the one below
                    continue
                b = class_bands(sport)[cls]
                lo_t, hi_t = b.get("min") or 0, b.get("max")
                lo = 0 if lo_t == 0 else from_canonical(lo_t, metric, sport)
                hi = None if hi_t is None else from_canonical(hi_t, metric, sport)
                if lo_t and lo is None:
                    # band starts beyond the crosswalk: the metric cannot
                    # distinguish it — it merges into the previous band
                    continue
                bands[cls] = {"min": round(lo, 1) if lo else 0,
                              "max": round(hi, 1) if hi is not None else None}
            # close gaps left by merged bands: each max = next min
            keys = list(bands)
            for a, b in zip(keys, keys[1:]):
                bands[a]["max"] = bands[b]["min"]
            if keys:
                bands[keys[-1]]["max"] = None
            out[sport][metric] = bands
    return out


def with_derived_cutpoints(thresholds):
    """Return decision_thresholds with `classification_cutpoints` injected."""
    th = dict(thresholds or {})
    th["classification_cutpoints"] = derived_cutpoints()
    return th


# ──────────────────────────────────────────────────────────────────
# Author resolution
# ──────────────────────────────────────────────────────────────────

def _floors():
    return (load_thresholds_raw() or {}).get("prescription_floors", {})


def _native_metrics(author):
    status = author.get("metric_status") or {}
    return [m for m in author.get("available_metrics", [])
            if m != "rpe" and status.get(m, "native") == "native"]


def canonical_range(zone, author):
    """(t_lo, t_hi, metric_used) of a zone, or (None, None, None)."""
    sport = author["sport"]
    ranges = zone.get("ranges") or {}
    natives = _native_metrics(author)
    floors = _floors()
    for m in PRIMARY_ORDER:
        if m not in ranges or m not in natives:
            continue
        r = ranges[m]
        lo, hi = r.get("min"), r.get("max")
        if lo is None and hi is None:
            continue
        if lo is None:
            f = floors.get(m, 0)
            lo = f / anchor_factor(author, m) if m in floors else 0
        t_lo = to_canonical(lo, m, sport, author)
        t_hi = to_canonical(hi, m, sport, author) if hi is not None else None
        if t_lo is None and t_hi is not None:
            # the lower bound sits below the crosswalk (e.g. a recovery zone
            # written "< 70% HRmax"): start at the crosswalk's floor
            t_lo = min(t_hi, _canonical_floor(sport))
        if t_lo is None:
            continue
        return t_lo, t_hi, m
    ra = zone.get("race_anchor")
    if ra:
        t_lo, t_hi, _ = race_anchor_range(ra)
        return t_lo, t_hi, "race_anchor"
    return None, None, None


def _canonical_floor(sport):
    """Lowest canonical value any conversion of this sport is defined for —
    the prescription floor of the canonical metric."""
    canon = load_crosswalk()[sport]["canonical_metric"]
    return float(_floors().get(canon, 0))


def _round(v):
    return None if v is None else int(round(v))


def _estimate_range(t_lo, t_hi, metric, sport, author):
    lo = from_canonical(t_lo, metric, sport, author)
    hi = from_canonical(t_hi, metric, sport, author) if t_hi is not None else None
    if lo is None and hi is None:
        # below the first knot: start from the floor; above the last: open
        return None
    if lo is None:
        return {"min": None, "max": _round(hi)}
    if t_hi is not None and hi is None:
        return {"min": _round(lo), "max": None}
    return {"min": _round(lo), "max": _round(hi)}


def _overlap(a, b):
    """Do two {min,max} RPE ranges overlap?"""
    alo = a.get("min") if a.get("min") is not None else 0
    ahi = a.get("max") if a.get("max") is not None else 10
    blo = b.get("min") if b.get("min") is not None else 0
    bhi = b.get("max") if b.get("max") is not None else 10
    return alo <= bhi and blo <= ahi


def resolve_author(raw):
    """Return (resolved_author, errors, warnings)."""
    a = copy.deepcopy(raw)
    sport = a["sport"]
    errors, warns = [], []
    natives = _native_metrics(a)
    sm = sport_metrics(sport)
    cw = load_crosswalk()
    no_hr = set(cw.get("no_hr_estimate_domains") or [])
    lt1 = load_classes()["lt1_band"][sport]
    classes = load_classes()["classes"]

    resolved_metrics = list(dict.fromkeys(sm + [m for m in a.get("available_metrics", [])
                                                 if m not in ("rpe",)]))
    a["resolved_metrics"] = resolved_metrics
    a["native_metrics"] = natives

    anc = a.get("anchor")
    if anc and not anc.get("factor_from_threshold") and anc.get("duration_min"):
        if sport != "running" or anc.get("metric") not in ("pace", "power"):
            errors.append(f"{a['id']}: anchor.duration_min is only defined for running "
                          f"pace or power (no duration model exists for {sport}/"
                          f"{anc.get('metric')})")
        else:
            anc["factor_from_threshold"] = anchor_factor_value(anc)
            anc["factor_computed_from"] = (f"{_num_min(anc['duration_min'])} sustainable "
                                           f"pace, {_dm()['name']} model")

    for z in a["zones"]:
        key = f"{a['id']} {z['key']}"
        t_lo, t_hi, used = canonical_range(z, a)
        stated = (z.get("stated_class") or {}).get("class")
        resolution = z.get("resolution") or {}
        flags = []

        ra = z.get("race_anchor")
        anchor_text = None
        if ra:
            ra_errs = validate_race_anchor(ra, sport)
            if ra_errs:
                errors.append(f"{key}: race_anchor: " + "; ".join(ra_errs))
                continue
            r_lo, r_hi, anchor_text = race_anchor_range(ra)
            if used != "race_anchor" and t_lo is not None:
                # native numbers govern; the anchor is a consistency check
                n_mid = t_lo if t_hi is None else (t_lo + t_hi) / 2.0
                r_mid = r_lo if r_hi is None else (r_lo + r_hi) / 2.0
                if abs(n_mid - r_mid) > 3.0:
                    warns.append(f"{key}: native numbers put the zone at {n_mid:.1f}% of "
                                 f"threshold but its race anchor ({anchor_text}) says "
                                 f"{r_mid:.1f}% — {abs(n_mid - r_mid):.1f} points apart")

        if t_lo is None:
            if not stated:
                errors.append(f"{key}: no native numeric range and no stated_class "
                              f"— the class cannot be determined")
                continue
            cls = stated
            provenance = "stated (no native numbers)"
            if natives:
                # A composite or maximal zone of an author who publishes
                # numbers elsewhere (Carmichael OverUnder, Coggan Level 7):
                # its class is stated, but no range is invented for it.
                t_lo = t_hi = None
            else:
                # An author with no numeric scale at all (Koop): the zone
                # takes its class band as its estimated range.
                b = class_bands(sport)[cls]
                t_lo, t_hi = (b.get("min") or 0), b.get("max")
                if t_lo == 0:
                    t_lo = _canonical_floor(sport)
        else:
            mid = t_lo if t_hi is None else (t_lo + t_hi) / 2.0
            computed = class_of(mid, sport)
            cls = computed
            provenance = (f"computed from {anchor_text}" if used == "race_anchor"
                          else f"computed from {used}")
            if stated and stated != computed:
                use = resolution.get("use")
                if use not in ("stated", "computed") or not resolution.get("reason"):
                    errors.append(
                        f"{key}: author states '{stated}' but the numbers compute "
                        f"'{computed}' (canonical {t_lo:.1f}–"
                        f"{'open' if t_hi is None else f'{t_hi:.1f}'}%). Add "
                        f"`resolution: {{use: stated|computed, reason: ...}}`.")
                    continue
                if use == "stated":
                    cls = stated
                    provenance = (f"stated by author (computed {computed}; "
                                  f"resolution: {resolution['reason'].strip()})")
                else:
                    provenance = (f"computed from {used} (author states {stated}; "
                                  f"resolution: {resolution['reason'].strip()})")
            elif stated:
                provenance += "; matches author's stated target"

        dom = domain_of_class(cls)

        if t_lo is None:
            z["range_status"] = {m: ("native" if m in natives else "declared_estimate")
                                 for m in (z.get("ranges") or {})}
            z["ranges"] = dict(z.get("ranges") or {})
            if z.get("rpe"):
                z["rpe_status"] = "native"
            else:
                z["rpe"], z["rpe_status"] = class_rpe(cls), "estimated"
            z.update(physiological_class=cls, domain=dom, anchor_text=anchor_text,
                     class_provenance=provenance, canonical=None, flags=[])
            continue

        # Domain crossings and the LT1 band
        dom_lo = domain_of(t_lo, sport)
        dom_hi = domain_of(t_hi - 1e-9, sport) if t_hi is not None else None
        if t_hi is None:
            if CLASS_RANK[cls] < CLASS_RANK["neuromuscular"]:
                flags.append(f"open upper bound — extends from {dom_lo} upward")
        elif dom_lo != dom_hi:
            flags.append(f"spans {dom_lo}→{dom_hi}")
        hi_for_lt1 = t_hi if t_hi is not None else t_lo
        if t_lo < lt1["max"] and hi_for_lt1 > lt1["min"] and \
                CLASS_RANK[cls] <= CLASS_RANK["tempo"]:
            flags.append("touches the LT1 band — moderate or heavy depending on the athlete")

        # Borderline: midpoint within 1 point of a class boundary. The class
        # stays as computed; the flag says how thin the margin is.
        # Measured against the class the NUMBERS compute (an author-stated class
        # that overrides it is not what the margin is about), and skipped for an
        # open-ended zone, whose "midpoint" is its own lower edge.
        if t_hi is not None:
            mid_c = (t_lo + t_hi) / 2.0
            bcls = class_of(mid_c, sport)
            band = class_bands(sport)[bcls]
            i = CLASS_ORDER.index(bcls)
            if band.get("min") and mid_c - band["min"] <= BORDERLINE_PTS and i > 0:
                flags.append(f"borderline: within {BORDERLINE_PTS:g} point of the "
                             f"{CLASS_ORDER[i - 1]}/{bcls} boundary")
            if band.get("max") is not None and band["max"] - mid_c <= BORDERLINE_PTS \
                    and i < len(CLASS_ORDER) - 1:
                flags.append(f"borderline: within {BORDERLINE_PTS:g} point of the "
                             f"{bcls}/{CLASS_ORDER[i + 1]} boundary")

        # Ranges and per-metric status
        status = {}
        ranges = dict(z.get("ranges") or {})
        for m in list(ranges):
            status[m] = "native" if m in natives else "declared_estimate"
        for m in sm:
            if m in ranges:
                continue
            if m == "lthr" and dom in no_hr:
                continue
            est = _estimate_range(t_lo, t_hi, m, sport, a)
            if est is not None:
                ranges[m] = est
                status[m] = "estimated"

        # RPE
        std = class_rpe(cls)
        if z.get("rpe"):
            rpe_status = "native"
            zr = z["rpe"]
            if (zr.get("min") is not None or zr.get("max") is not None):
                wide = {"min": max(1, std["min"] - 1), "max": min(10, std["max"] + 1)}
                if not _overlap(zr, wide):
                    warns.append(f"{key}: author RPE {zr.get('min')}–{zr.get('max')} "
                                 f"vs standard {std['min']}–{std['max']} for {cls} "
                                 f"(author's RPE is kept)")
        else:
            z["rpe"] = std
            rpe_status = "estimated"

        z["ranges"] = ranges
        z["range_status"] = status
        z["rpe_status"] = rpe_status
        z["physiological_class"] = cls
        z["domain"] = dom
        z["class_provenance"] = provenance
        z["anchor_text"] = anchor_text
        z["canonical"] = {"min": round(t_lo, 1),
                          "max": round(t_hi, 1) if t_hi is not None else None}
        z["flags"] = flags

    return a, errors, warns


def load_author_raw(author_id):
    path = os.path.join(CONFIG, "authors", f"{author_id}.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_author(author_id):
    """Resolved author. Raises ValueError on resolution errors."""
    a, errors, _ = resolve_author(load_author_raw(author_id))
    if errors:
        raise ValueError("; ".join(errors))
    return a


def residuals():
    """Mean absolute error (in percentage points) of the crosswalk against
    every author that publishes two metrics natively. Returns a list of
    (sport, author_id, metric, n, mae, max_err)."""
    out = []
    cw = load_crosswalk()
    for sport in ("cycling", "running"):
        canon = cw[sport]["canonical_metric"]
        for conv_metric, spec in cw[sport]["conversions"].items():
            for aid in spec.get("residual_check", []) or []:
                try:
                    a = load_author_raw(aid)
                except FileNotFoundError:
                    continue
                errs = []
                for z in a["zones"]:
                    r = z.get("ranges") or {}
                    measured = r.get(conv_metric)
                    scale = 1.0
                    if measured is None and conv_metric == "lthr" and "hrmax" in r:
                        # an author publishing % HRmax: compare on % LTHR
                        measured, scale = r["hrmax"], 100.0 / hrmax_threshold_pct(a)
                    if canon not in r or measured is None:
                        continue
                    for k in ("min", "max"):
                        cv, mv = r[canon].get(k), measured.get(k)
                        if cv is None or mv is None:
                            continue
                        mv = mv * scale
                        t = cv * anchor_factor(a, canon)
                        pred = from_canonical(t, conv_metric, sport, a)
                        if pred is not None:
                            errs.append(abs(pred - mv))
                if errs:
                    out.append((sport, aid, conv_metric, len(errs),
                                sum(errs) / len(errs), max(errs)))
    return out
