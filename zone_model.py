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
  6. RPE. The author's native RPE. When the author publishes none, the class's
     standard CR-10 band, flagged "estimated". A native RPE that does not
     overlap the class band widened by one point is reported (warning only —
     authors calibrate RPE differently, and the author's RPE is what is emitted).
"""

import copy
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


def anchor_factor(author, metric):
    anc = author.get("anchor")
    if anc and anc.get("metric") == metric:
        return float(anc["factor_from_threshold"])
    return 1.0


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

    for z in a["zones"]:
        key = f"{a['id']} {z['key']}"
        t_lo, t_hi, used = canonical_range(z, a)
        stated = (z.get("stated_class") or {}).get("class")
        resolution = z.get("resolution") or {}
        flags = []

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
            cls, provenance = computed, f"computed from {used}"
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
            z.update(physiological_class=cls, domain=dom,
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
