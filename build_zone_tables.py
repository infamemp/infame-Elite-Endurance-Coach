"""
build_zone_tables.py — Infame Elite Endurance Coach v6, Stage 1
===============================================================
Validates author configuration files against the schema and regenerates the
Markdown zone tables consumed by the Claude Project.

The YAML files under config/authors/ are the single source of truth. The Markdown
under generated/ is derived output and must never be hand-edited.

Usage:
    python build_zone_tables.py validate
    python build_zone_tables.py build
    python build_zone_tables.py diff <reference-markdown-file>

Commands:
    validate   Check every author file against config/schema/author.schema.json.
    build      Regenerate the Markdown zone tables into generated/.
    diff       Compare generated output against a reference file (migration check).

Paths are resolved relative to the repository root.

Version: 1.0
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
    "vo2max": "VO2max",
    "anaerobic": "Anaerobic",
    "neuromuscular": "Neuromuscular",
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


def validate_all():
    """Schema-validate every author file. Returns the number of failures."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    validator = Draft7Validator(schema)

    authors = load_authors()
    if not authors:
        print("No author files found.")
        return 1

    failures = 0
    for fn, data in authors:
        stem = os.path.splitext(fn)[0]
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

        # Cross-field checks the JSON Schema cannot express
        extra = []
        if data.get("id") != stem:
            extra.append(f"id '{data.get('id')}' does not match filename stem '{stem}'")
        available = set(data.get("available_metrics", []))
        if data.get("default_metric") not in available:
            extra.append(f"default_metric '{data.get('default_metric')}' not in available_metrics")
        for key in data.get("metric_status", {}):
            if key not in available:
                extra.append(f"metric_status has '{key}' which is not in available_metrics")
        for i, z in enumerate(data.get("zones", [])):
            for metric in z.get("ranges", {}):
                if metric not in available:
                    extra.append(f"zone '{z.get('key')}' has range for '{metric}' "
                                 f"which is not in available_metrics")
        anc = data.get("anchor")
        if anc:
            if anc.get("metric") not in available:
                extra.append(f"anchor metric '{anc.get('metric')}' is not in "
                             f"available_metrics")
            f = anc.get("factor_from_threshold")
            if not isinstance(f, (int, float)) or not 0.5 < f < 2.0:
                extra.append(f"anchor factor_from_threshold {f!r} is outside a "
                             f"plausible range")
            if f == 1.0:
                extra.append("anchor factor is 1.0 — the author anchors on "
                             "threshold, so the anchor block should be removed")

        dl = data.get("dual_layer")
        if dl and dl.get("required") and not dl.get("engine_metric"):
            extra.append("dual_layer.required is true but engine_metric is missing")
        sor = data.get("special_output_rule")
        if sor and sor.get("native_metric") == sor.get("output_metric"):
            extra.append("special_output_rule native_metric equals output_metric")

        if errors or extra:
            failures += 1
            print(f"FAIL  {fn}")
            for e in errors:
                loc = " → ".join(str(p) for p in e.path) or "(root)"
                print(f"        [{loc}] {e.message}")
            for msg in extra:
                print(f"        [cross-field] {msg}")
        else:
            print(f"OK    {fn}  ({len(data['zones'])} zones, "
                  f"metrics: {', '.join(data['available_metrics'])})")

    print()
    print(f"{len(authors) - failures}/{len(authors)} author files valid.")

    check_cutpoints([a for _, a in authors])
    return failures


def check_cutpoints(authors):
    """Report where an author's declared zone class differs from the fallback
    cutpoints. Divergences are expected: authors genuinely disagree, and the
    author's class is authoritative. This is a visibility check, not a failure."""
    th = load_thresholds()
    cuts = th.get("classification_cutpoints", {})
    if not cuts:
        return

    def classify(sport, metric, mid):
        bands = cuts.get(sport, {}).get(metric)
        if not bands:
            return None
        for cls, r in bands.items():
            lo = r.get("min") or 0
            hi = r.get("max")
            if lo <= mid and (hi is None or mid < hi):
                return cls
        return None

    total = diverge = 0
    lines = []
    for a in authors:
        anc = a.get("anchor")
        for z in a["zones"]:
            for metric, r in (z.get("ranges") or {}).items():
                lo, hi = r.get("min"), r.get("max")
                if lo is None or hi is None:
                    continue
                # Compare against the cutpoints on the same scale they were
                # calibrated on: threshold. An anchored column must be converted
                # first or every zone reads as a false divergence.
                if anc and anc["metric"] == metric:
                    f = anc["factor_from_threshold"]
                    lo, hi = lo * f, hi * f
                pred = classify(a["sport"], metric, (lo + hi) / 2)
                if pred is None:
                    continue
                total += 1
                if pred != z["physiological_class"]:
                    diverge += 1
                    lines.append(f"        {a['id']} {z['key']} ({metric} {_num(lo)}\u2013{_num(hi)}%): "
                                 f"author says {z['physiological_class']}, cutpoints say {pred}")
    print()
    print(f"Cutpoint agreement: {total - diverge}/{total} zones.")
    if lines:
        print("      Divergences below are author disagreements, not errors \u2014")
        print("      the author's class governs (see class_resolution in decision_thresholds.yaml):")
        for l in lines:
            print(l)


# ──────────────────────────────────────────────────────────────────
# Rendering
# ──────────────────────────────────────────────────────────────────

def fmt_range(rng, floor=None):
    """Render a {min,max} pair. An open lower bound renders from the prescription
    floor for that metric, so the table shows the usable range rather than an
    implied zero. The author's source value is preserved in the YAML."""
    if rng is None:
        return "N/A"
    lo, hi = rng.get("min"), rng.get("max")
    if lo is None and hi is None:
        return "N/A"
    if lo is None:
        if floor is not None and (hi is None or floor < hi):
            return f"{_num(floor)}\u2013{_num(hi)}%"
        return f"< {_num(hi)}%"
    if hi is None:
        return f"> {_num(lo)}%"
    if lo == hi:
        return f"{_num(lo)}%"
    return f"{_num(lo)}\u2013{_num(hi)}%"


def scale_range(rng, factor):
    """Convert a range from the author's anchor onto a threshold anchor."""
    if not rng:
        return None
    out = {}
    for k in ("min", "max"):
        v = rng.get(k)
        out[k] = round(v * factor) if v is not None else None
    return out


def fmt_rpe(rpe):
    if not rpe:
        return ""
    if rpe.get("label"):
        return rpe["label"]
    lo, hi = rpe.get("min"), rpe.get("max")
    if lo is None and hi is None:
        return ""
    if lo is None:
        return f"< {_num(hi)}"
    if hi is None:
        return f"> {_num(lo)}"
    if lo == hi:
        return _num(lo)
    return f"{_num(lo)}\u2013{_num(hi)}"


def _num(v):
    if v is None:
        return ""
    return str(int(v)) if float(v).is_integer() else str(v)


def render_author(author, thresholds):
    """Render one methodology section."""
    floors = (thresholds or {}).get("prescription_floors", {})
    labels = dict(METRIC_LABELS)
    labels.update(author.get("metric_labels") or {})

    L = []
    L.append(f"## Methodology: {author['name']}")

    sport_label = author.get("sport_note") or author["sport"].capitalize()
    L.append(f"* **Sport:** {sport_label}")
    L.append(f"* **Zone Identifier Style:** {author['zone_identifier_style']}")
    L.append("* **Default Metric:** " +
             (author.get("default_metric_label") or labels[author["default_metric"]]))
    L.append("* **Available Metrics:** " +
             ", ".join(labels[m] for m in author["available_metrics"]))
    L.append("* **Primary Metrics:** " + ", ".join(author["primary_metrics"]))
    anchors = author.get("intensity_anchors") or [labels[m] for m in author["available_metrics"]]
    L.append("* **Intensity Anchors:** " + ", ".join(anchors))

    for metric, status in (author.get("metric_status") or {}).items():
        if metric == "power":
            continue
        L.append(f"* **{STATUS_LABELS.get(metric, metric.upper())} Status:** {status.capitalize()}")

    dl = author.get("dual_layer") or {"required": False}
    L.append(f"* **Dual-Layer Required:** {'Yes' if dl.get('required') else 'No'}")
    if dl.get("required"):
        L.append(f"* **Dual-Layer Engine:** {labels[dl['engine_metric']]} Range "
                 f"\u2014 feeds Intervals.icu load calculation")
        L.append("* **Dual-Layer Steering:** " +
                 (dl.get("steering_label") or f"{labels[dl['steering_metric']]} per zone") +
                 " \u2014 athlete reads on device")

    sor = author.get("special_output_rule")
    if sor:
        status = (author.get("metric_status") or {}).get(sor["output_metric"], "")
        qualifier = "Estimated " if status == "estimated" else ""
        L.append(f"* **Special Output Rule:** Native metric is "
                 f"{labels[sor['native_metric']]}, but Intervals.icu syntax MUST use "
                 f"{qualifier}{labels[sor['output_metric']]} {sor['rationale']}. "
                 f"Never output {labels[sor['native_metric']]} in syntax.")

    for n in author.get("notes", []):
        L.append(f"* **Note:** {n}")

    # An author whose percentages are not measured against threshold gets a
    # second column for the same metric, converted so it can be read against
    # threshold. The author's own numbers stay untouched in the native column.
    anchor = author.get("anchor")
    if anchor:
        f = anchor["factor_from_threshold"]
        L.append(f"* **Anchor:** {anchor['reference']}. This is NOT threshold — "
                 f"it sits {(f - 1) * 100:.0f}% above it, so the "
                 f"{labels[anchor['metric']]} column below is the author's own "
                 f"scale and cannot be read as a percentage of threshold.")
        L.append(f"* **{anchor.get('equivalent_column_label', 'Threshold equivalent')}:** "
                 f"generated by multiplying the author's percentages by {f}. Use "
                 f"this column for an athlete who has a threshold value but has "
                 f"not performed the author's own test. Source: "
                 f"{anchor['source'].strip()}")
        L.append(f"* **Class assigned from:** the "
                 f"{anchor.get('class_from', 'equivalent')} column — "
                 f"classification cutpoints are calibrated on threshold, so TSS "
                 f"stays comparable with the other methodologies.")

    # Table
    metrics = [m for m in author["available_metrics"] if m != "rpe"]
    headers = ["Zone Key", "Zone Name"]
    for m in metrics:
        headers.append(f"{labels[m]} Range")
        if anchor and anchor["metric"] == m:
            headers.append(anchor.get("equivalent_column_label",
                                      "Threshold equivalent"))
    headers += ["RPE (1-10)", "Class", "Notes"]

    L.append("")
    L.append("| " + " | ".join(headers) + " |")
    L.append("| " + " | ".join([":---"] * len(headers)) + " |")
    for z in author["zones"]:
        row = [z["key"], z["name"]]
        for m in metrics:
            rng = z.get("ranges", {}).get(m)
            row.append(fmt_range(rng, floors.get(m)))
            if anchor and anchor["metric"] == m:
                row.append(fmt_range(scale_range(rng,
                                                 anchor["factor_from_threshold"]),
                                     floors.get(m)))
        row += [fmt_rpe(z.get("rpe")),
                CLASS_LABELS[z["physiological_class"]],
                z.get("note", "")]
        L.append("| " + " | ".join(row) + " |")

    return "\n".join(L)


HEADER_NOTES = """**Schema notes:**
- `Zone Key` preserves each author's native zone identifier vocabulary (e.g. "Zone 1", "Level 1", letter codes).
- `Class` is the cross-author physiological class that determines TSS cost. It is the only valid bridge between methodologies.
- Metric status fields indicate whether a metric is native to that methodology or a cross-referenced estimate.
- Notation: ranges use `X\u2013Y%` (en dash), open lower bound `< X%`, open upper bound `> X%`, undefined value `N/A`.
- Compound or non-numeric details are captured in the `Notes` column rather than embedded in range cells.
- Zones with an open lower bound in the source are rendered from the prescription floor for that metric (see below), not from zero.

**GENERATED FILE \u2014 DO NOT EDIT.** Built {BUILD_DATE} by `build_zone_tables.py`.
If this date is older than your last change to `config/`, this file is stale \u2014
run `python build_zone_tables.py build` and re-upload it to the Claude Project.
To change a zone, edit the YAML and rebuild. To add a methodology, copy
`config/authors/_template.yaml`, fill it in, run `validate`, then `build`.
Hand edits here are lost on the next build."""


def render_syntax_block(thresholds):
    """Render the output-format and floor rules that govern generated syntax."""
    of = thresholds.get("output_formats", {})
    floors = thresholds.get("prescription_floors", {})
    L = ["**Output format \u2014 how these zones are written in Intervals.icu syntax:**",
         "",
         "| Metric | Table column | Emitted in syntax as | Never use |",
         "| :--- | :--- | :--- | :--- |"]
    for key in ("power", "lthr", "pace", "hrmax"):
        spec = of.get(key)
        if not spec:
            continue
        syntax = spec.get("syntax") or "never emitted \u2014 see Special Output Rule"
        forbidden = ", ".join(f"`{x}`" for x in spec.get("forbidden_suffixes", [])) or "\u2014"
        L.append(f"| {spec.get('table_label', key)} | {spec.get('table_label', key)} "
                 f"| `{syntax}` | {forbidden} |")
    L.append("")
    L.append("The table columns below are documentation of where each zone lies. "
             "What is emitted in a workout block is the `Emitted in syntax as` form above \u2014 "
             "power is a bare percentage with no metric suffix.")
    L.append("")
    L.append("**Prescription floors.** Lowest intensity that may be prescribed for each metric: " +
             ", ".join(f"{of.get(k, {}).get('table_label', k)} {v}%" for k, v in floors.items()) +
             ". Zones whose source definition has an open lower bound are rendered from the floor "
             "rather than from zero, because a near-zero target cannot be steered by a device.")
    return "\n".join(L)


def build():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    authors = [a for _, a in load_authors()]
    thresholds = load_thresholds()
    written = []

    for sport in ("cycling", "running"):
        group = [a for a in authors if a["sport"] == sport]
        if not group:
            continue
        header_notes = HEADER_NOTES.replace("{BUILD_DATE}", _dt.date.today().isoformat())
        parts = [f"# {SPORT_TITLES[sport]}", "", header_notes, "",
                 render_syntax_block(thresholds), "", "---", ""]
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
        print("Nothing to build \u2014 no author files found.")
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
