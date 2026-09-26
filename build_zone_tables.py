"""
build_zone_tables.py — Infame Elite Endurance Coach v7.2
========================================================
Validates author configuration files and regenerates the standardized Markdown
zone tables consumed by the Claude Project.

The YAML files under config/authors/ hold ONLY each author's native values.
Estimated metrics, physiological class and intensity domain are computed by
zone_model.py through config/crosswalk.yaml and config/tss_classes.yaml. The
Markdown under generated/ is derived output and must never be hand-edited.

Usage:
    python build_zone_tables.py validate
    python build_zone_tables.py build
    python build_zone_tables.py diff <reference-markdown-file>

Commands:
    validate   Check every author file against the schema, resolve it (class,
               domain, estimates), report conflicts, RPE warnings and the
               crosswalk residuals. Exit code 1 on any error.
    build      Regenerate the Markdown zone tables into generated/.
    diff       Compare generated output against a reference file (migration check).

Paths are resolved relative to the repository root.

Version: 2.0 (v7.2 — native values + crosswalk + computed class/domain)
"""

import argparse
import datetime as _dt
import difflib
import os
import sys

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency. Run: pip install pyyaml jsonschema")
try:
    import json
    from jsonschema import Draft7Validator
except ImportError:
    sys.exit("Missing dependency. Run: pip install pyyaml jsonschema")


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import zone_model as zm  # noqa: E402
AUTHORS_DIR = os.path.join(ROOT, "config", "authors")
SCHEMA_PATH = os.path.join(ROOT, "config", "schema", "author.schema.json")
THRESHOLDS_PATH = os.path.join(ROOT, "config", "decision_thresholds.yaml")
OUTPUT_DIR = os.path.join(ROOT, "generated")

METRIC_LABELS = {
    "power": "% FTP",
    "lthr": "% LTHR",
    "pace": "% Threshold Pace",
    "hrmax": "% HRmax",
    "rpe": "RPE",
}

# Label used in the "<X> Status:" metadata lines. Independent of the column label:
# Palladino's power column reads "% FTP/CP" but its status line still says "Pace".
STATUS_LABELS = {
    "lthr": "LTHR",
    "pace": "Pace",
    "hrmax": "HRmax",
}

CLASS_LABELS = {
    "recovery": "Recovery",
    "endurance": "Endurance",
    "tempo": "Tempo",
    "sub_threshold": "Sub-threshold",
    "threshold": "Threshold",
    "supra_threshold": "Supra-threshold",
    "vo2max": "VO2max",
    "anaerobic": "Anaerobic",
    "neuromuscular": "Neuromuscular",
}

DOMAIN_LABELS = {"moderate": "Moderate", "heavy": "Heavy",
                 "severe": "Severe", "extreme": "Extreme"}

# Column label per sport. Running power is % of running threshold power
# (Stryd-type devices); it is written with the same bare "%" as cycling power.
SPORT_METRIC_LABELS = {
    "cycling": {"power": "% FTP", "lthr": "% LTHR", "hrmax": "% HRmax"},
    "running": {"pace": "% Threshold Pace", "lthr": "% LTHR",
                "power": "% FTP (run power)", "hrmax": "% HRmax"},
}

SPORT_TITLES = {
    "cycling": "Cycling Training Zones Reference Database (Standardized)",
    "running": "Running Training Zones Reference Database (Standardized)",
}

FILE_NAMES = {
    "cycling": "Simple_Table_Cycling_Training_Zones.md",
    "running": "Simple_Table_Running_Training_Zones.md",
}


# ──────────────────────────────────────────────────────────────────
# Loading and validation
# ──────────────────────────────────────────────────────────────────

def load_thresholds():
    """Load cross-cutting rules. Prescription floors govern how open lower bounds render."""
    if not os.path.exists(THRESHOLDS_PATH):
        sys.exit(f"Thresholds file not found: {THRESHOLDS_PATH}")
    with open(THRESHOLDS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_authors():
    """Load every author YAML. Returns a list of (filename, dict)."""
    if not os.path.isdir(AUTHORS_DIR):
        sys.exit(f"Author directory not found: {AUTHORS_DIR}")
    out = []
    for fn in sorted(os.listdir(AUTHORS_DIR)):
        if not fn.endswith((".yaml", ".yml")) or fn.startswith("_"):
            continue
        path = os.path.join(AUTHORS_DIR, fn)
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        out.append((fn, data))
    return out


def cross_field_errors(data, stem):
    """Checks the JSON Schema cannot express."""
    extra = []
    if data.get("id") != stem:
        extra.append(f"id '{data.get('id')}' does not match filename stem '{stem}'")
    available = set(data.get("available_metrics", []))
    resolvable = available | set(zm.sport_metrics(data.get("sport", "cycling")))
    if data.get("default_metric") not in resolvable:
        extra.append(f"default_metric '{data.get('default_metric')}' is neither published "
                     f"by the author nor a {data.get('sport')} metric")
    for key in data.get("metric_status", {}):
        if key not in available:
            extra.append(f"metric_status has '{key}' which is not in available_metrics")
    native_numeric = [m for m in available if m != "rpe"]
    for z in data.get("zones", []):
        for metric in (z.get("ranges") or {}):
            if metric not in available:
                extra.append(f"zone '{z.get('key')}' has a range for '{metric}' which is "
                             f"not in available_metrics — only native values belong here; "
                             f"estimates are computed")
    for m in native_numeric:
        if not any(m in (z.get("ranges") or {}) for z in data.get("zones", [])):
            extra.append(f"'{m}' is listed in available_metrics but no zone publishes it")
    if data.get("sport") == "cycling" and "pace" in available:
        extra.append("pace is not a cycling metric")
    anc = data.get("anchor")
    if anc:
        if anc.get("metric") not in available:
            extra.append(f"anchor metric '{anc.get('metric')}' is not in available_metrics")
        if anc.get("factor_from_threshold") and anc.get("duration_min"):
            extra.append("anchor declares both factor_from_threshold and duration_min — "
                         "use one")
        try:
            f = zm.anchor_factor_value(anc)
        except Exception as e:  # noqa: BLE001 — surfaced as a validation message
            f = None
            extra.append(f"anchor could not be evaluated: {e}")
        if not isinstance(f, (int, float)) or not 0.5 < f < 2.0:
            extra.append(f"anchor factor {f!r} is outside a plausible range")
        if f == 1.0:
            extra.append("anchor factor is 1.0 — the author anchors on threshold, so the "
                         "anchor block should be removed")
    if data.get("hrmax_threshold_pct") and "hrmax" not in available:
        extra.append("hrmax_threshold_pct is declared but the author publishes no % HRmax")
    dl = data.get("dual_layer")
    if dl and dl.get("required"):
        if not dl.get("engine_metric"):
            extra.append("dual_layer.required is true but engine_metric is missing")
        elif dl["engine_metric"] not in resolvable:
            extra.append(f"dual_layer engine_metric '{dl['engine_metric']}' is not a "
                         f"{data.get('sport')} metric")
    for z in data.get("zones", []):
        if z.get("race_anchor"):
            for msg in zm.validate_race_anchor(z["race_anchor"], data.get("sport")):
                extra.append(f"zone '{z.get('key')}': {msg}")
    sor = data.get("special_output_rule")
    if sor:
        if sor.get("native_metric") == sor.get("output_metric"):
            extra.append("special_output_rule native_metric equals output_metric")
        if sor.get("native_metric") not in available:
            extra.append("special_output_rule native_metric is not published by the author")
    return extra


def validate_all():
    """Schema-validate and resolve every author file. Returns the number of failures."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    validator = Draft7Validator(schema)

    authors = load_authors()
    if not authors:
        print("No author files found.")
        return 1

    failures = 0
    all_warns = []
    for fn, data in authors:
        stem = os.path.splitext(fn)[0]
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        extra = cross_field_errors(data, stem)
        res_errors, warns = [], []
        if not errors and not extra:
            _, res_errors, warns = zm.resolve_author(data)
            all_warns += warns

        if errors or extra or res_errors:
            failures += 1
            print(f"FAIL  {fn}")
            for e in errors:
                loc = " → ".join(str(p) for p in e.path) or "(root)"
                print(f"        [{loc}] {e.message}")
            for msg in extra:
                print(f"        [cross-field] {msg}")
            for msg in res_errors:
                print(f"        [class] {msg}")
        else:
            natives = [m for m in data['available_metrics'] if m != 'rpe'] or ["none (stated classes)"]
            print(f"OK    {fn}  ({len(data['zones'])} zones, native: {', '.join(natives)})")

    print()
    print(f"{len(authors) - failures}/{len(authors)} author files valid.")

    if all_warns:
        print()
        print("RPE notes (warnings only — the author's own RPE is what is emitted):")
        for w in all_warns:
            print(f"        {w}")

    print()
    print("Crosswalk residuals against authors publishing two metrics natively")
    print("(mean / max absolute difference, in percentage points):")
    for sport, aid, metric, n, mae, mx in zm.residuals():
        print(f"        {sport:8} {aid:14} {metric:6} n={n:<3} mean {mae:4.1f}   max {mx:4.1f}")

    rr = zm.race_anchor_residuals()
    tol = zm.load_crosswalk()["running"]["race_anchors"]["duration_model"]["residual_tolerance"]
    diffs = [abs(r[3]) for r in rr]
    mean_d, max_d = sum(diffs) / len(diffs), max(diffs)
    print()
    print("Race anchors (running): Daniels-Gilbert model vs Palladino's published ranges")
    print("(% of threshold pace; model range across VDOT 35-65; centre difference in points):")
    for k, pub, mod, dc in rr:
        print(f"        {k:14} published {pub[0]:>5.0f}\u2013{pub[1]:<5.0f} model "
              f"{mod[0]:>5.1f}\u2013{mod[1]:<5.1f} diff {dc:+4.1f}")
    print(f"        mean |diff| {mean_d:.2f}   max |diff| {max_d:.2f}   "
          f"(tolerance mean {tol['mean']}, max {tol['max']})")
    if mean_d > tol["mean"] or max_d > tol["max"]:
        print("        FAIL  the model no longer reproduces the published race anchors")
        failures += 1
    return failures


# ──────────────────────────────────────────────────────────────────
# Rendering
# ──────────────────────────────────────────────────────────────────

def fmt_range(rng, floor=None, estimated=False):
    """Render a {min,max} pair. An open lower bound renders from the prescription
    floor for that metric, so the table shows the usable range rather than an
    implied zero. Estimated values carry a leading '~'."""
    if rng is None:
        return "N/A"
    lo, hi = rng.get("min"), rng.get("max")
    if lo is None and hi is None:
        return "N/A"
    t = "~" if estimated else ""
    if lo is None:
        if floor is not None and (hi is None or floor < hi):
            return f"{t}{_num(floor)}–{_num(hi)}%"
        return f"{t}< {_num(hi)}%"
    if hi is None:
        return f"{t}> {_num(lo)}%"
    if lo == hi:
        return f"{t}{_num(lo)}%"
    return f"{t}{_num(lo)}–{_num(hi)}%"


def scale_range(rng, factor):
    """Convert a range from the author's anchor onto a threshold anchor."""
    if not rng:
        return None
    out = {}
    for k in ("min", "max"):
        v = rng.get(k)
        out[k] = round(v * factor) if v is not None else None
    return out


def fmt_rpe(rpe, estimated=False):
    if not rpe:
        return ""
    if rpe.get("label"):
        return rpe["label"]
    lo, hi = rpe.get("min"), rpe.get("max")
    if lo is None and hi is None:
        return ""
    t = "~" if estimated else ""
    if lo is None:
        return f"{t}< {_num(hi)}"
    if hi is None:
        return f"{t}> {_num(lo)}"
    if lo == hi:
        return t + _num(lo)
    return f"{t}{_num(lo)}–{_num(hi)}"


def _num(v):
    if v is None:
        return ""
    return str(int(v)) if float(v).is_integer() else str(v)


def _zone_notes(z):
    parts = []
    for f in z.get("flags") or []:
        if f.startswith("spans "):
            continue                      # shown in the Domain cell
        if f.startswith("touches the LT1"):
            parts.append("LT1 is individual: moderate or heavy depending on the athlete")
        elif f.startswith("open upper"):
            parts.append("Open-ended upward")
    if z.get("anchor_text"):
        parts.append(f"Anchor: {z['anchor_text']}")
    for f in z.get("flags") or []:
        if f.startswith("borderline"):
            b = f.split("of the ", 1)[1].replace("_", "-")
            parts.append(f"Borderline: within 1 point of the {b}")
    prov = z.get("class_provenance", "")
    if prov.startswith("stated by author"):
        parts.append("Class as stated by the author (numbers alone compute a different class)")
    elif prov.startswith("stated (no native"):
        parts.append("Class from the author's stated physiological target")
    elif "(author states" in prov:
        stated = prov.split("(author states ", 1)[1].split(";", 1)[0]
        parts.append(f"Author's stated target is {CLASS_LABELS.get(stated, stated)}; "
                     f"class follows the prescribed intensity")
    if z.get("note"):
        parts.append(z["note"].strip())
    return "; ".join(parts)


def _domain_cell(z):
    label = DOMAIN_LABELS[z["domain"]]
    for f in z.get("flags") or []:
        if f.startswith("spans "):
            a, b = f[6:].split("→")
            return f"{DOMAIN_LABELS.get(a, a)}→{DOMAIN_LABELS.get(b, b)}"
    return label


def render_author(author, thresholds):
    """Render one methodology section from the RESOLVED author."""
    floors = (thresholds or {}).get("prescription_floors", {})
    sport = author["sport"]
    labels = dict(SPORT_METRIC_LABELS[sport])
    labels["rpe"] = "RPE"
    labels.update(author.get("metric_labels") or {})
    natives = author.get("native_metrics") or []
    anchor = author.get("anchor")

    L = []
    L.append(f"## Methodology: {author['name']}")

    sport_label = author.get("sport_note") or sport.capitalize()
    L.append(f"* **Sport:** {sport_label}")
    L.append(f"* **Zone Identifier Style:** {author['zone_identifier_style']}")
    L.append("* **Default Metric:** " +
             (author.get("default_metric_label") or labels.get(author["default_metric"],
                                                              author["default_metric"])))
    L.append("* **Native Metrics (author's own numbers):** " +
             (", ".join(labels[m] for m in natives) or
              "none — RPE and the physiological target of each zone"))
    est = [m for m in zm.sport_metrics(sport) if m not in natives]
    if est:
        L.append("* **Estimated Metrics (`~`, computed through the crosswalk):** " +
                 ", ".join(labels[m] for m in est))
    L.append("* **Primary Metrics:** " + ", ".join(author["primary_metrics"]))

    dl = author.get("dual_layer") or {"required": False}
    L.append(f"* **Dual-Layer Required:** {'Yes' if dl.get('required') else 'No'}")
    if dl.get("required"):
        L.append(f"* **Dual-Layer Engine:** {labels[dl['engine_metric']]} Range "
                 f"— feeds Intervals.icu load calculation")
        L.append("* **Dual-Layer Steering:** " +
                 (dl.get("steering_label") or f"{labels[dl['steering_metric']]} per zone") +
                 " — athlete reads on device")

    sor = author.get("special_output_rule")
    if sor:
        L.append(f"* **Special Output Rule:** Native metric is "
                 f"{labels[sor['native_metric']]}, but Intervals.icu syntax MUST use the "
                 f"estimated {labels[sor['output_metric']]} {sor['rationale']}. "
                 f"Never output {labels[sor['native_metric']]} in syntax.")

    hp = author.get("hrmax_threshold_pct")
    if hp:
        L.append(f"* **Threshold on the author's HRmax scale:** {_num(hp['value'])}% HRmax "
                 f"= 100% LTHR. Source: {hp['source'].strip()}")

    for n in author.get("notes", []):
        L.append(f"* **Note:** {n}")

    if anchor:
        f = anchor["factor_from_threshold"]
        L.append(f"* **Anchor:** {anchor['reference']}. This is NOT threshold — "
                 f"it sits {(f - 1) * 100:.0f}% above it, so the "
                 f"{labels[anchor['metric']]} column below is the author's own "
                 f"scale and cannot be read as a percentage of threshold.")
        L.append(f"* **{anchor.get('equivalent_column_label', 'Threshold equivalent')}:** "
                 f"the author's percentages multiplied by {f}. Use this column for an "
                 f"athlete who has a threshold value but has not performed the author's "
                 f"own test. Source: {anchor['source'].strip()}")

    # Columns: the sport's metrics in crosswalk order, then native HRmax.
    metrics = list(zm.sport_metrics(sport))
    if "hrmax" in natives:
        metrics.append("hrmax")
    headers = ["Zone Key", "Zone Name"]
    for m in metrics:
        headers.append(labels[m])
        if anchor and anchor["metric"] == m:
            headers.append(anchor.get("equivalent_column_label", "Threshold equivalent"))
    headers += ["RPE (1-10)", "Domain", "Class", "Notes"]

    L.append("")
    L.append("| " + " | ".join(headers) + " |")
    L.append("| " + " | ".join([":---"] * len(headers)) + " |")
    for z in author["zones"]:
        row = [str(z["key"]), z["name"]]
        status = z.get("range_status") or {}
        for m in metrics:
            rng = (z.get("ranges") or {}).get(m)
            estimated = status.get(m) in ("estimated", "declared_estimate")
            fl = floors.get(m)
            if anchor and anchor["metric"] == m and fl is not None:
                fl = round(fl / anchor["factor_from_threshold"])
            row.append(fmt_range(rng, fl, estimated))
            if anchor and anchor["metric"] == m:
                row.append(fmt_range(scale_range(rng, anchor["factor_from_threshold"]),
                                     floors.get(m)))
        row += [fmt_rpe(z.get("rpe"), z.get("rpe_status") == "estimated"),
                _domain_cell(z),
                CLASS_LABELS[z["physiological_class"]],
                _zone_notes(z)]
        L.append("| " + " | ".join(row) + " |")

    return "\n".join(L)


HEADER_NOTES = """**How to read these tables (v7.2):**
- `Zone Key` and `Zone Name` preserve each author's own vocabulary.
- Values without a mark are the author's own numbers (native). Values marked `~` are ESTIMATES computed through `config/crosswalk.yaml` — from the author's native numbers, or, for an author who defines a zone by a race distance or a sustainable duration, from that anchor (`Anchor:` in the Notes; distances from Palladino's published table, durations from the Daniels-Gilbert model, about +/- 2 points). Use them when the athlete's metric is not one the author publishes. `N/A` means no estimate is meaningful (e.g. heart rate for efforts under ~2 minutes).
- Threshold (100%) is a band, not a point: authors place it anywhere from a ~30-minute effort to ~70 minutes, so every estimate carries about +/- 2-3 points of definitional uncertainty on top of the crosswalk error. `Borderline` in the Notes means the zone's midpoint is within 1 point of a class boundary.
- `Domain` is the physiological intensity domain (Moderate · Heavy · Severe · Extreme). `A→B` means the zone's range crosses from one domain into the next.
- `Class` determines TSS cost and is the only valid bridge between methodologies (never RPE). It is COMPUTED from the zone's position on the threshold scale, never assigned by hand; where the author explicitly states a different physiological target, the Notes say which one governs.
- `RPE` is the author's own scale (emit it as published). `~` RPE is the standard CR-10 reference for the class, used only where the author publishes none.
- Notation: ranges use `X–Y%` (en dash), open lower bound `< X%`, open upper bound `> X%`, undefined value `N/A`. Zones with an open lower bound are rendered from the prescription floor for that metric (see below), not from zero.

**GENERATED FILE — DO NOT EDIT.** Built {BUILD_DATE} by `build_zone_tables.py`.
If this date is older than your last change to `config/`, this file is stale —
run `python build_zone_tables.py build` and re-upload it to the Claude Project.
To change a zone, edit the YAML and rebuild. To add a methodology, copy
`config/authors/_template.yaml`, fill in the author's NATIVE values only, run
`validate`, then `build`. Hand edits here are lost on the next build."""


def render_class_reference(sport, thresholds):
    """Domains and classes with their band on every metric of the sport."""
    cls_cfg = zm.load_classes()
    cuts = zm.derived_cutpoints()[sport]
    labels = SPORT_METRIC_LABELS[sport]
    metrics = zm.sport_metrics(sport)
    lt1 = cls_cfg["lt1_band"][sport]
    canon = zm.load_crosswalk()[sport]["canonical_metric"]

    def band(metric, c):
        b = cuts.get(metric, {}).get(c)
        if not b:
            return "N/A"
        lo, hi = b.get("min"), b.get("max")
        if not lo:
            return f"< {_num(hi)}%"
        if hi is None:
            return f"≥ {_num(lo)}%"
        return f"{_num(lo)}–{_num(hi)}%"

    L = ["**Domains and classes — the standard every table below is resolved against:**",
         "",
         "| Domain | Class | " + " | ".join(labels[m] for m in metrics) +
         " | Standard RPE | Sustainable | TSS/min |",
         "| " + " | ".join([":---"] * (len(metrics) + 5)) + " |"]
    for c in zm.CLASS_ORDER:
        cc = cls_cfg["classes"][c]
        r = cc["rpe"]
        rpe = _num(r["min"]) if r["min"] == r["max"] else f"{_num(r['min'])}–{_num(r['max'])}"
        L.append(f"| {DOMAIN_LABELS[cc['domain']]} | {CLASS_LABELS[c]} | " +
                 " | ".join(band(m, c) for m in metrics) +
                 f" | {rpe} | {cc['max_sustainable']} | {_num(cc['tss_per_min'])} |")
    L.append("")
    L.append(f"Bands on {labels[canon]} are the standard; the other columns are the same "
             f"bands converted through the crosswalk. Heart rate cannot separate classes "
             f"above ~{_num(cuts['lthr'].get('vo2max', {}).get('min') or 0)}% LTHR "
             f"(it lags and saturates), so those efforts are governed by power, pace or RPE.")
    L.append(f"The moderate/heavy boundary (LT1) is individual: on {labels[canon]} it lies "
             f"between {_num(lt1['min'])}% and {_num(lt1['max'])}% for most athletes. "
             f"Zones touching that band are flagged in their Notes.")
    return "\n".join(L)


def render_syntax_block(thresholds):
    """Render the output-format and floor rules that govern generated syntax."""
    of = thresholds.get("output_formats", {})
    floors = thresholds.get("prescription_floors", {})
    L = ["**Output format — how these zones are written in Intervals.icu syntax:**",
         "",
         "| Metric | Table column | Emitted in syntax as | Never use |",
         "| :--- | :--- | :--- | :--- |"]
    for key in ("power", "lthr", "pace", "hrmax"):
        spec = of.get(key)
        if not spec:
            continue
        syntax = spec.get("syntax") or "never emitted — see Special Output Rule"
        forbidden = ", ".join(f"`{x}`" for x in spec.get("forbidden_suffixes", [])) or "—"
        L.append(f"| {spec.get('table_label', key)} | {spec.get('table_label', key)} "
                 f"| `{syntax}` | {forbidden} |")
    L.append("")
    L.append("The table columns below are documentation of where each zone lies. "
             "What is emitted in a workout block is the `Emitted in syntax as` form above — "
             "power (cycling or running) is a bare percentage with no metric suffix, and the "
             "`~` estimate mark is never written in syntax.")
    L.append("")
    L.append("**Prescription floors.** Lowest intensity that may be prescribed for each metric: " +
             ", ".join(f"{of.get(k, {}).get('table_label', k)} {v}%" for k, v in floors.items()) +
             ". Zones whose source definition has an open lower bound are rendered from the floor "
             "rather than from zero, because a near-zero target cannot be steered by a device.")
    return "\n".join(L)


def build():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    thresholds = load_thresholds()
    resolved = []
    for fn, raw in load_authors():
        a, errors, _ = zm.resolve_author(raw)
        if errors:
            print(f"FAIL  {fn}")
            for e in errors:
                print(f"        {e}")
            print("\nNothing written. Run `python build_zone_tables.py validate` for details.")
            return 1
        resolved.append(a)
    written = []

    for sport in ("cycling", "running"):
        group = [a for a in resolved if a["sport"] == sport]
        if not group:
            continue
        header_notes = HEADER_NOTES.replace("{BUILD_DATE}", _dt.date.today().isoformat())
        parts = [f"# {SPORT_TITLES[sport]}", "", header_notes, "",
                 render_syntax_block(thresholds), "",
                 render_class_reference(sport, thresholds), "", "---", ""]
        for i, a in enumerate(group):
            parts.append(render_author(a, thresholds))
            parts.append("")
            if i < len(group) - 1:
                parts.append("---")
                parts.append("")
        text = "\n".join(parts).rstrip() + "\n"

        path = os.path.join(OUTPUT_DIR, FILE_NAMES[sport])
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        written.append((path, len(group)))

    for path, n in written:
        print(f"Wrote {os.path.relpath(path, ROOT)}  ({n} methodologies)")
    if not written:
        print("Nothing to build — no author files found.")
    return 0


def diff(reference):
    """Compare generated output against a reference file, ignoring the header block."""
    if not os.path.exists(reference):
        sys.exit(f"Reference file not found: {reference}")
    sport = "running" if "Running" in os.path.basename(reference) else "cycling"
    generated = os.path.join(OUTPUT_DIR, FILE_NAMES[sport])
    if not os.path.exists(generated):
        sys.exit(f"Generated file not found: {generated}. Run 'build' first.")

    def sections(path):
        """Split a zone file into {methodology name: body lines}."""
        out, current, buf = {}, None, []
        for line in open(path, encoding="utf-8"):
            if line.startswith("## Methodology:"):
                if current:
                    out[current] = buf
                current, buf = line.split(":", 1)[1].strip(), []
            elif current:
                if line.strip() and line.strip() != "---":
                    buf.append(line.rstrip())
        if current:
            out[current] = buf
        return out

    ref, gen = sections(reference), sections(generated)
    only_ref = set(ref) - set(gen)
    only_gen = set(gen) - set(ref)
    if only_ref:
        print(f"Missing from generated: {', '.join(sorted(only_ref))}")
    if only_gen:
        print(f"Only in generated: {', '.join(sorted(only_gen))}")

    for name in sorted(set(ref) & set(gen)):
        d = list(difflib.unified_diff(ref[name], gen[name],
                                      fromfile=f"reference/{name}",
                                      tofile=f"generated/{name}", lineterm=""))
        if d:
            print(f"\n--- {name} ---")
            for line in d:
                print(line)
        else:
            print(f"IDENTICAL  {name}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Infame v6 zone-table config tool")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="schema-check every author file")
    sub.add_parser("build", help="regenerate the Markdown zone tables")
    d = sub.add_parser("diff", help="compare generated output to a reference file")
    d.add_argument("reference")
    args = ap.parse_args()

    if args.cmd == "validate":
        sys.exit(1 if validate_all() else 0)
    if args.cmd == "build":
        sys.exit(build())
    if args.cmd == "diff":
        sys.exit(diff(args.reference))


if __name__ == "__main__":
    main()
