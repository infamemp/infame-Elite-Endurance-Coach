"""
validate_block.py — Infame Elite Endurance Coach v6, Stage 2
=============================================================
Deterministic verification gate for generated Intervals.icu workout blocks.

Nothing reaches the athlete unverified. This tool parses a generated block,
checks it against the hard constraints, and recomputes its TSS. A failed check
blocks the upload; it never repairs silently.

Every rule and every number comes from config/ — this file contains no zone
data, no thresholds, and no multipliers of its own.

Methodology and discipline are read from the session header fields
[Methodology] and [Discipline]. Passing them on the command line would risk
validating a block against zones that do not apply and reporting a clean pass on
a defective block, so the flags exist only as an override for raw blocks with no
header.

Usage:
    python validate_block.py <file> --fill-tss
    python validate_block.py block.md
    python validate_block.py raw.txt --methodology coggan --discipline trainer --tss 66

Options:
    --methodology   Override the [Methodology] header field
    --discipline    Override the [Discipline] header field
    --tss           Expected TSS for a raw block with no header
    --tolerance     Override the divergence tolerance from config (percent)
    --quiet         Report findings only, omit the per-interval TSS breakdown
    --fill-tss      Write the computed TSS into the header. The model writes
                    [Estimated TSS] pending; the engine supplies the number.
                    Refused if any hard constraint fails — a defective block is
                    never completed, only reported.

Exit code: 0 = upload-safe · 1 = hard-constraint violation.

Version: 2.1
"""

import argparse
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency. Run: pip install pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config")

VALID_CATEGORIES = {"Training", "Rest", "Race"}
SECTION_WORDS = {"warmup", "warm up", "main set", "main", "cooldown", "cool down"}
FOREIGN_SECTIONS = {"calentamiento", "principal", "enfriamiento", "enfriar",
                    "warm down", "warmdown", "vuelta a la calma", "recuperacion"}


# ══════════════════════════════════════════════════════════════════
# CONFIG LOADING
# ══════════════════════════════════════════════════════════════════

def load_thresholds_only():
    path = os.path.join(CONFIG, "decision_thresholds.yaml")
    if not os.path.exists(path):
        sys.exit(f"Config file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config(methodology):
    def read(path):
        full = os.path.join(CONFIG, path)
        if not os.path.exists(full):
            sys.exit(f"Config file not found: {full}")
        with open(full, encoding="utf-8") as f:
            return yaml.safe_load(f)

    th = read("decision_thresholds.yaml")
    tss = read("tss_classes.yaml")

    author_path = os.path.join(CONFIG, "authors", f"{methodology}.yaml")
    if not os.path.exists(author_path):
        available = sorted(f[:-5] for f in os.listdir(os.path.join(CONFIG, "authors"))
                           if f.endswith(".yaml") and not f.startswith("_"))
        sys.exit(f"Unknown methodology '{methodology}'.\nAvailable: {', '.join(available)}")
    with open(author_path, encoding="utf-8") as f:
        author = yaml.safe_load(f)

    return author, th, tss


# ══════════════════════════════════════════════════════════════════
# PARSER
# ══════════════════════════════════════════════════════════════════

DUR_RE = re.compile(r"^(?:(\d+)h)?(?:(\d+)m(?!tr))?(?:(\d+)s)?$")
DIST_RE = re.compile(r"^(\d+(?:\.\d+)?)(km|mtr)$", re.I)
TARGET_RE = re.compile(
    r"(?P<lo>\d+(?:\.\d+)?)(?:\s*-\s*(?P<hi>\d+(?:\.\d+)?))?\s*%"
    r"(?:\s*(?P<metric>FTP|CP|LTHR|Pace|HRmax|HR)\b)?", re.I)
RPE_RE = re.compile(r"\[\s*RPE\s+\d+(?:\s*-\s*\d+)?\s*\]", re.I)
CUE_RE = re.compile(r'"[^"]*"')
FENCE_RE = re.compile(r"```(?:text)?\n(.*?)```", re.S)
HEADER_START_RE = re.compile(r"^\[Week\]", re.M)
FIELD_RE = re.compile(r"\[(\w[\w ]*)\]\s*([^\[|]*)")


def parse_duration(tokens):
    """Consume leading duration tokens. Returns (seconds, distance, tokens_used)."""
    joined, used, secs = "", 0, None
    for i, t in enumerate(tokens[:3]):
        cand = joined + t
        if DIST_RE.match(cand):
            return None, cand, i + 1
        m = DUR_RE.match(cand)
        if m and any(m.groups()):
            joined, used = cand, i + 1
            h, mi, s = (int(g) if g else 0 for g in m.groups())
            secs = h * 3600 + mi * 60 + s
        else:
            break
    return (secs, None, used) if used else (None, None, 0)


def parse_block(text):
    """Parse one code block into steps plus structural findings."""
    steps, findings = [], []
    in_repeat, mult, prev_blank = False, 1, True

    for ln, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if not s:
            prev_blank, in_repeat, mult = True, False, 1
            continue
        if s.startswith("#") or re.fullmatch(r"[*_\-=]{3,}", s):
            prev_blank = False
            continue

        sec = re.match(r"^([A-Za-zÁÉÍÓÚáéíóúñÑ ]+?)(?:\s+(\d+)x)?$", s)
        if sec and sec.group(1).strip().lower() in SECTION_WORDS | FOREIGN_SECTIONS:
            name = sec.group(1).strip()
            if name.lower() in FOREIGN_SECTIONS:
                findings.append(("HC-LANG", ln,
                                 f"Section keyword not canonical English: '{name}'"))
            if sec.group(2):
                if in_repeat:
                    findings.append(("HC-NESTED", ln, "Nested repeat"))
                in_repeat, mult = True, int(sec.group(2))
                if not prev_blank:
                    findings.append(("FMT-BLANK", ln, "Repeat header needs a blank line above"))
            else:
                in_repeat, mult = False, 1
            prev_blank = False
            continue

        rep = re.fullmatch(r"(\d+)x", s)
        if rep:
            if in_repeat:
                findings.append(("HC-NESTED", ln, "Nested repeat"))
            in_repeat, mult = True, int(rep.group(1))
            if not prev_blank:
                findings.append(("FMT-BLANK", ln, "Repeat line needs a blank line above"))
            prev_blank = False
            continue

        if s.startswith("-"):
            body = s.lstrip("- ").strip()
            tokens = body.split()
            secs, dist, used = parse_duration(tokens)
            rest = " ".join(tokens[used:])
            is_ramp = bool(re.match(r"^ramp\b", rest, re.I))
            if is_ramp:
                rest = rest[4:].strip()
            tgt = TARGET_RE.search(rest)
            step = {"line": ln, "raw": s, "secs": secs, "dist": dist, "ramp": is_ramp,
                    "mult": mult if in_repeat else 1,
                    "rpe": bool(RPE_RE.search(s)), "cue": bool(CUE_RE.search(s)),
                    "freeride": "freeride" in s.lower()}
            if tgt:
                lo = float(tgt.group("lo"))
                step["pct"] = (lo, float(tgt.group("hi")) if tgt.group("hi") else lo)
                step["suffix"] = (tgt.group("metric") or "").upper()
            else:
                step["suffix"] = ""
            steps.append(step)
            if secs is None and dist is None and not step["freeride"]:
                findings.append(("SYN-DUR", ln, f"Unparseable duration: '{body[:40]}'"))
            prev_blank = False
            continue

        prev_blank = False
        findings.append(("SYN-LINE", ln, f"Unrecognized line: '{s[:50]}'"))

    return steps, findings


def split_sessions(text):
    """Split a Phase-4 delivery into (header, code) pairs."""
    starts = [m.start() for m in HEADER_START_RE.finditer(text)]
    if not starts:
        blocks = FENCE_RE.findall(text)
        return [({}, blocks[0] if blocks else text)]
    out = []
    for i, st in enumerate(starts):
        chunk = text[st: starts[i + 1] if i + 1 < len(starts) else len(text)]
        header = {}
        for line in chunk.splitlines():
            if not line.strip().startswith("["):
                continue
            for m in FIELD_RE.finditer(line):
                header[m.group(1).strip()] = m.group(2).strip().lstrip(":").strip(" |")
        blocks = FENCE_RE.findall(chunk)
        out.append((header, blocks[0] if blocks else ""))
    return out


# ══════════════════════════════════════════════════════════════════
# CLASSIFICATION — author zone first, cutpoints as fallback
# ══════════════════════════════════════════════════════════════════

SUFFIX_TO_METRIC = {"": "power", "FTP": "power", "CP": "power",
                    "LTHR": "lthr", "PACE": "pace", "HRMAX": "hrmax", "HR": "lthr"}


def classify(mid, metric, author, thresholds):
    """Return (class, source). The author's declared zone governs; the
    cutpoints in decision_thresholds.yaml apply only when no zone contains
    the value.

    An author who anchors on something other than threshold (see `anchor` in
    the author file) publishes zones on their own scale. A target written in a
    workout block is always on the threshold scale, so the author's zones are
    converted before comparison — otherwise a correct Carmichael target would
    match the wrong zone."""
    anc = author.get("anchor")
    factor = (anc["factor_from_threshold"]
              if anc and anc.get("metric") == metric else 1.0)
    for z in author["zones"]:
        r = (z.get("ranges") or {}).get(metric)
        if not r:
            continue
        lo, hi = r.get("min"), r.get("max")
        lo = (lo if lo is not None else 0) * factor
        hi = hi * factor if hi is not None else None
        if lo <= mid and (hi is None or mid <= hi):
            src = f"{author['id']} {z['key']}"
            if factor != 1.0:
                src += " (threshold-equivalent)"
            return z["physiological_class"], src

    cuts = (thresholds.get("classification_cutpoints", {})
            .get(author["sport"], {}).get(metric))
    if not cuts:
        return None, None
    for cls, r in cuts.items():
        lo = r.get("min") or 0
        hi = r.get("max")
        if lo <= mid and (hi is None or mid < hi):
            return cls, "cutpoints"
    return None, None


# ══════════════════════════════════════════════════════════════════
# HARD CONSTRAINTS
# ══════════════════════════════════════════════════════════════════

def load_profile(athlete_id):
    """Athlete-declared profile. Absent is normal — most checks do not need it."""
    if not athlete_id:
        return {}
    path = os.path.join(CONFIG, "athletes", f"{athlete_id}.yaml")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def profile_flag(profile, dotted):
    """Read a dotted path such as ramp_overrides.treadmill_ramps_requested."""
    node = profile
    for part in (dotted or "").split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return bool(node)


def check_constraints(steps, code, author, th, discipline, profile=None):
    errors, warns = [], []
    profile = profile or {}
    of = th["output_formats"]
    floors = th["prescription_floors"]
    ramps = th["ramps"]
    disc = discipline.lower()

    # Absolute values anywhere in the block
    for metric, spec in of.items():
        for suf in spec.get("forbidden_suffixes", []):
            esc = re.escape(suf)
            if suf.lower() in ("w", "watts"):
                pat = re.compile(r"\b\d+\s?" + esc + r"\b", re.I)
            elif "/" in suf:
                pat = re.compile(r"\b\d{1,2}:\d{2}\s*" + esc + r"\b", re.I)
            else:
                pat = re.compile(r"%\s*" + esc + r"\b", re.I)
            for m in pat.finditer(code):
                errors.append(("HC-FORMAT", "-",
                               f"'{m.group(0).strip()}' is forbidden for {metric} "
                               f"— {spec.get('note', '').strip()}"))

    dl = author.get("dual_layer") or {}
    sor = author.get("special_output_rule") or {}

    for s in steps:
        if s["freeride"] or "pct" not in s:
            continue
        suffix = s["suffix"]
        metric = SUFFIX_TO_METRIC.get(suffix, "power")
        lo, hi = s["pct"]

        # Prescription floor
        floor = floors.get(metric)
        if floor is not None and lo < floor:
            errors.append(("HC-FLOOR", s["line"],
                           f"{lo:g}% is below the {metric} prescription floor of {floor}%"))

        # Special output rule: the native metric must not be emitted
        if sor and metric == sor.get("native_metric"):
            errors.append(("HC-SOR", s["line"],
                           f"{author['name']} must emit "
                           f"{of[sor['output_metric']]['syntax']}, never "
                           f"{of[sor['native_metric']]['table_label']}"))

        # Metric must belong to this author
        if metric not in author["available_metrics"] and metric != "power":
            warns.append(("CHK-METRIC", s["line"],
                          f"{author['name']} does not define {metric}"))

        # Ramp eligibility — three cases, per `ramps` in decision_thresholds.yaml
        if s["ramp"]:
            allowed = [x.lower() for x in ramps.get("allowed_disciplines", [])]
            forbidden = [x.lower() for x in ramps.get("forbidden_disciplines", [])]
            override = {k.lower(): v for k, v in
                        (ramps.get("override_eligible") or {}).items()}

            if disc in forbidden:
                errors.append(("HC-RAMP", s["line"],
                               f"Ramps are forbidden for discipline '{discipline}' "
                               f"— no device control over a changing target"))
            elif disc in allowed:
                if metric not in ramps.get("required_metrics", []):
                    errors.append(("HC-RAMP", s["line"],
                                   f"Ramps in '{discipline}' require metric "
                                   f"{'/'.join(ramps['required_metrics'])}, found {metric}"))
            elif disc in override:
                spec = override[disc]
                if not profile_flag(profile, spec.get("flag", "")):
                    errors.append(("HC-RAMP", s["line"],
                                   f"Ramps in '{discipline}' require express request — "
                                   f"set {spec.get('flag')} in the athlete profile"))
                elif metric not in spec.get("permitted_metrics", []):
                    errors.append(("HC-RAMP", s["line"],
                                   f"Ramps in '{discipline}' permit metric "
                                   f"{'/'.join(spec.get('permitted_metrics', []))}, "
                                   f"found {metric}"))
            else:
                errors.append(("HC-RAMP", s["line"],
                               f"Discipline '{discipline}' is not ramp-eligible"))

        # Dual-layer completeness
        if dl.get("required"):
            missing = []
            if metric != dl["engine_metric"]:
                missing.append(f"{of[dl['engine_metric']]['syntax']} engine metric")
            if not s["rpe"]:
                missing.append("[RPE x-y]")
            if not s["cue"]:
                missing.append("quoted cue")
            if missing:
                errors.append(("HC-DUAL", s["line"],
                               f"Dual-layer incomplete — missing {', '.join(missing)}"))

    return errors, warns


def check_header(header):
    errors, warns = [], []
    if not header:
        return errors, warns
    cat = header.get("Category", "")
    if cat and cat not in VALID_CATEGORIES:
        errors.append(("HC-CAT", "-", f"Category '{cat}' must be one of "
                                      f"{sorted(VALID_CATEGORIES)}"))
    dur = header.get("Duration", "")
    if dur and not re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", dur):
        warns.append(("CHK-DUR", "-", f"Duration '{dur}' is not HH:MM:SS"))
    for req in ("Week", "Date", "Category", "Focus"):
        if req not in header:
            warns.append(("CHK-HDR", "-", f"Header field [{req}] missing"))
    return errors, warns


# ══════════════════════════════════════════════════════════════════
# TSS
# ══════════════════════════════════════════════════════════════════

def compute_tss(steps, author, th, tssc):
    """Recompute session TSS. Rules come from tss_rules; multipliers from
    tss_classes; classification from the author's zones."""
    rules = th["tss_rules"]
    mults = {k: v["tss_per_min"] for k, v in tssc["classes"].items()}
    point = rules.get("range_cost_point", "midpoint")

    total, detail, skipped = 0.0, [], []
    for s in steps:
        if s["freeride"] or "pct" not in s or s["dist"] or s["secs"] is None:
            if s["freeride"] or s["dist"]:
                skipped.append((s, "distance-based or freeride — no duration to cost"))
            continue
        lo, hi = s["pct"]
        mid = {"midpoint": (lo + hi) / 2, "low": lo, "high": hi}[point]
        metric = SUFFIX_TO_METRIC.get(s["suffix"], "power")
        cls, src = classify(mid, metric, author, th)
        if cls is None:
            skipped.append((s, f"no class for {mid:g}% {metric}"))
            continue
        mult = s["mult"] if rules.get("repeats_multiply", True) else 1
        minutes = s["secs"] / 60 * mult
        cost = minutes * mults[cls]
        total += cost
        detail.append((s, mid, metric, cls, src, minutes, cost))

    if rules.get("rounding") == "nearest_integer":
        total = round(total)
    return total, detail, skipped


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def fill_tss(path, text, computed_by_session):
    """Replace each [Estimated TSS] value with the computed figure, in session
    order. The file is rewritten in place; only the TSS field changes."""
    starts = [m.start() for m in HEADER_START_RE.finditer(text)]
    if not starts:
        return 0

    field = re.compile(r"(\[Estimated TSS\]\s*:?\s*)([^\[|\n]*)")
    pieces, written = [], 0
    for i, st in enumerate(starts):
        if i == 0 and st > 0:
            pieces.append(text[:st])
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        chunk = text[st:end]
        value = computed_by_session.get(i + 1)
        if value is not None and field.search(chunk):
            chunk = field.sub(lambda m: f"{m.group(1)}{value}", chunk, count=1)
            written += 1
        pieces.append(chunk)

    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(pieces))
    return written


def main():
    ap = argparse.ArgumentParser(description="Infame v6 block verification gate")
    ap.add_argument("file")
    ap.add_argument("--methodology", help="override the [Methodology] header field")
    ap.add_argument("--discipline", help="override the [Discipline] header field")
    ap.add_argument("--tss", type=float)
    ap.add_argument("--tolerance", type=float)
    ap.add_argument("--athlete", help="athlete id, to load config/athletes/<id>.yaml")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--fill-tss", action="store_true",
                    help="write the computed TSS into each [Estimated TSS] header field. "
                         "Only applied when the block passes every hard constraint.")
    args = ap.parse_args()

    if not os.path.exists(args.file):
        sys.exit(f"File not found: {args.file}")
    text = open(args.file, encoding="utf-8").read()
    sessions = split_sessions(text)

    th = load_thresholds_only()
    tol = args.tolerance if args.tolerance is not None else \
        th["tss_rules"].get("divergence_tolerance_pct", 10)

    print(f"validate_block v2.1 — {os.path.basename(args.file)}")
    print()

    failed = False
    computed_by_session = {}
    for n, (header, code) in enumerate(sessions, 1):
        methodology = args.methodology or header.get("Methodology")
        discipline = args.discipline or header.get("Discipline")
        if not methodology or not discipline:
            missing = []
            if not methodology:
                missing.append("[Methodology]")
            if not discipline:
                missing.append("[Discipline]")
            print(f"── Session {n}: cannot validate — header is missing "
                  f"{' and '.join(missing)}")
            print(f"   Add the field(s) to the session header, or pass "
                  f"--methodology / --discipline for a raw block.\n")
            failed = True
            continue

        author, _, tssc = load_config(methodology.strip().lower())
        label = (f"Week {header.get('Week', '?')} · {header.get('Date', '?')} · "
                 f"{header.get('Focus', '')}".strip(" ·") if header else "block")
        print(f"── Session {n}: {label}")
        print(f"   {author['name']} · {author['sport']} · discipline: {discipline}")

        steps, findings = parse_block(code)
        errors = [f for f in findings if f[0].startswith(("HC-", "SYN-"))]
        warns = [f for f in findings if f[0].startswith("FMT-")]
        profile = load_profile(header.get("Athlete ID") or args.athlete)
        e, w = check_constraints(steps, code, author, th, discipline, profile)
        errors += e
        warns += w
        e, w = check_header(header)
        errors += e
        warns += w

        if steps and header.get("Category", "Training") == "Training":
            computed, detail, skipped = compute_tss(steps, author, th, tssc)
            if not args.quiet:
                for s, mid, metric, cls, src, minutes, cost in detail:
                    rep = f"{s['mult']}x " if s["mult"] > 1 else ""
                    print(f"   L{s['line']:>3}  {rep}{s['secs']//60}m{s['secs']%60:02d}s "
                          f"@ {mid:g}% {metric:<5} → {cls:<14} [{src}]  {cost:.1f}")
                for s, why in skipped:
                    print(f"   L{s['line']:>3}  not costed: {why}")

            computed_by_session[n] = computed
            declared = args.tss
            raw_field = (header.get("Estimated TSS") or "").strip().lower()
            if raw_field in ("pending", "tbd", "", "—", "-"):
                declared = None
            elif header.get("Estimated TSS"):
                m = re.search(r"\d+(?:\.\d+)?", header["Estimated TSS"])
                if m:
                    declared = float(m.group(0))
            print(f"   Computed TSS: {computed}", end="")
            if declared is None and raw_field in ("pending", "tbd"):
                print(" · header marked pending"
                      + (" — will be filled" if args.fill_tss else
                         " (run with --fill-tss to write it)"))
            elif declared is not None:
                div = abs(computed - declared) / declared * 100 if declared else 0
                ok = div <= tol
                print(f" · declared {declared:g} · divergence {div:.1f}% "
                      f"{'OK' if ok else 'EXCEEDS TOLERANCE'}")
                if not ok:
                    errors.append(("TSS-DIV", "-",
                                   f"Computed {computed} vs declared {declared:g} "
                                   f"({div:.1f}% > {tol}%)"))
            else:
                print(" · no declared TSS to compare")

        for c, ln, msg in errors:
            print(f"   FAIL [{c}] L{ln}: {msg}")
        for c, ln, msg in warns:
            print(f"   WARN [{c}] L{ln}: {msg}")
        if not errors and not warns:
            print("   clean")
        if errors:
            failed = True
        print()

    if failed:
        if args.fill_tss:
            print("TSS not written: the block must pass every hard constraint first.")
        print("RESULT: BLOCKED — hard-constraint violations. Do not upload.")
        sys.exit(1)

    if args.fill_tss and computed_by_session:
        written = fill_tss(args.file, text, computed_by_session)
        print(f"Wrote computed TSS into {written} header(s) in "
              f"{os.path.basename(args.file)}")

    print("RESULT: PASS — verified against config. Upload-safe.")
    sys.exit(0)


if __name__ == "__main__":
    main()
