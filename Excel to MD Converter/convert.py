"""
intervals.icu Excel → Markdown Converter
Converts athlete sheets from athletes_report_production.xlsx into
clean .md context documents for use in Claude Projects.

Usage:  python convert.py
Req:    pip install pandas openpyxl
"""

import os
import sys
from datetime import datetime, date

try:
    import pandas as pd
except ImportError:
    print("❌ Missing dependency: pip install pandas openpyxl")
    sys.exit(1)

SUMMARY_SHEET       = "Athletes Summary"
TABLE_COL_THRESHOLD = 3


# ─── Value helpers ────────────────────────────────────────────────────────────

def clean_value(val):
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    s = str(val).strip()
    return "" if s in ("nan", "None") else s


def row_values(row):
    return [clean_value(row.iloc[i]) for i in range(len(row))]


def filled_count(vals):
    return sum(1 for v in vals if v)


# ─── Row classification ───────────────────────────────────────────────────────

def is_empty_row(vals):
    return not any(vals)


def is_separator_val(v):
    return v.startswith("===") or v.startswith("---")


def is_separator_row(vals):
    """True if any cell looks like a visual separator (===, ---)."""
    return any(is_separator_val(v) for v in vals if v)


def is_md_header(key):
    return key.startswith("# ") or key.startswith("## ") or key in ("#", "##")


def is_section_header(vals):
    """Single non-empty cell, rest empty — treated as section title."""
    key = vals[0] if vals else ""
    return bool(key) and filled_count(vals[1:]) == 0 and not is_md_header(key)


def is_kv_row(vals):
    return (
        len(vals) >= 2
        and vals[0]
        and vals[1]
        and filled_count(vals[2:]) == 0
    )


def is_table_row(vals):
    return filled_count(vals) >= TABLE_COL_THRESHOLD


# ─── Table rendering ─────────────────────────────────────────────────────────

def render_table(rows):
    if not rows:
        return ""
    ncols   = max(len(r) for r in rows)
    padded  = [r + [""] * (ncols - len(r)) for r in rows]
    widths  = [max(len(str(padded[i][c])) for i in range(len(padded))) for c in range(ncols)]
    widths  = [max(w, 3) for w in widths]

    def fmt_row(r):
        cells = [str(r[c]).ljust(widths[c]) for c in range(ncols)]
        return "| " + " | ".join(cells) + " |"

    lines = [fmt_row(padded[0]),
             "| " + " | ".join("-" * w for w in widths) + " |"]
    for r in padded[1:]:
        lines.append(fmt_row(r))
    return "\n".join(lines)


# ─── Context Snapshot ─────────────────────────────────────────────────────────

def parse_duration_to_hours(dur_str):
    """Parse '1h 30m' or '45m 10s' to float hours."""
    if not dur_str or dur_str == "—":
        return 0.0
    try:
        total = 0.0
        if "h" in dur_str:
            parts = dur_str.split("h")
            total += float(parts[0].strip())
            dur_str = parts[1]
        if "m" in dur_str:
            parts = dur_str.split("m")
            total += float(parts[0].strip()) / 60
        return total
    except Exception:
        return 0.0


def build_context_snapshot(df):
    """
    Scan the dataframe for race calendar and recent activities to compute:
    - Days to next A-race
    - Avg weekly TSS (4w)
    - Avg weekly hours (4w)
    - Sport distribution (4w)
    """
    today = date.today()
    lines = ["\n## CONTEXT SNAPSHOT"]

    # ── Next A-race ──
    in_race_table = False
    next_a = None
    for i in range(len(df)):
        vals = row_values(df.iloc[i])
        key  = vals[0] if vals else ""

        if "RACE CALENDAR" in key.upper() or "SCHEDULED RACES" in key.upper():
            in_race_table = True
            continue

        if in_race_table and is_table_row(vals) and not is_separator_row(vals):
            # Skip header row (first row of table, contains "Date", "Event Name" etc.)
            if vals[0].lower() in ("date", "fecha"):
                continue
            # Check if this is a data row with a date and priority A
            raw_date = vals[0].strip()
            priority = vals[5].strip() if len(vals) > 5 else ""
            if priority.upper() == "A" and raw_date and not raw_date.startswith("="):
                try:
                    race_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
                    if race_date >= today:
                        if next_a is None or race_date < next_a[0]:
                            race_name = vals[1].strip() if len(vals) > 1 else "?"
                            next_a = (race_date, race_name)
                except Exception:
                    pass

        # Stop at next major section
        if in_race_table and key.startswith("# ") and "RACE" not in key.upper():
            in_race_table = False

    if next_a:
        days = (next_a[0] - today).days
        lines.append(f"**Next A-race:** {next_a[1]} — {next_a[0].isoformat()} ({days} days away)")
    else:
        lines.append("**Next A-race:** None scheduled")

    # ── Activity stats (4w) ──
    in_act_table  = False
    total_tss     = 0.0
    total_hours   = 0.0
    sport_counts  = {}
    act_count     = 0

    for i in range(len(df)):
        vals = row_values(df.iloc[i])
        key  = vals[0] if vals else ""

        if "RECENT ACTIVITIES" in key.upper() or "LAST 4 WEEKS" in key.upper():
            in_act_table = True
            continue

        if in_act_table and is_table_row(vals) and not is_separator_row(vals):
            if vals[0].lower() in ("date", "fecha"):
                continue
            if vals[0].startswith("="):
                continue
            try:
                sport    = vals[2].strip() if len(vals) > 2 else ""
                dur_str  = vals[3].strip() if len(vals) > 3 else ""
                tss_str  = vals[5].strip() if len(vals) > 5 else ""

                hours = parse_duration_to_hours(dur_str)
                tss   = float(tss_str) if tss_str and tss_str != "—" else 0.0

                total_hours  += hours
                total_tss    += tss
                act_count    += 1

                if sport:
                    # Normalize sport names
                    s = sport.lower()
                    if "run" in s or "trail" in s:
                        cat = "Running"
                    elif "ride" in s or "bike" in s or "gravel" in s or "mountain" in s:
                        cat = "Cycling"
                    elif "swim" in s:
                        cat = "Swimming"
                    else:
                        cat = sport
                    sport_counts[cat] = sport_counts.get(cat, 0) + 1
            except Exception:
                pass

    if act_count > 0:
        weeks = 4
        avg_tss   = total_tss   / weeks
        avg_hours = total_hours / weeks
        lines.append(f"**Avg weekly TSS (4w):** {avg_tss:.0f}")
        lines.append(f"**Avg weekly hours (4w):** {avg_hours:.1f} h")

        total_acts = sum(sport_counts.values())
        if total_acts > 0:
            dist_parts = [
                f"{cat} {round(cnt/total_acts*100)}%"
                for cat, cnt in sorted(sport_counts.items(), key=lambda x: -x[1])
            ]
            lines.append(f"**Sport distribution (4w):** {' · '.join(dist_parts)}")
    else:
        lines.append("**Avg weekly TSS (4w):** No activity data")

    return "\n".join(lines)


# ─── Section-aware conversion ─────────────────────────────────────────────────

def convert_sheet(df, sheet_name):
    """
    Convert DataFrame to markdown.
    - Skips separator rows inside tables (=== rows)
    - Skips entirely empty sections
    - Renders multi-column blocks as markdown tables
    - Appends computed Context Snapshot
    """
    lines      = []
    all_rows   = [row_values(df.iloc[i]) for i in range(len(df))]
    n          = len(all_rows)

    i = 0
    while i < n:
        vals = all_rows[i]
        key  = vals[0] if vals else ""

        # ── Empty row ──
        if is_empty_row(vals):
            if lines and lines[-1] != "":
                lines.append("")
            i += 1
            continue

        # ── Separator row (anywhere) ──
        if is_separator_row(vals):
            i += 1
            continue

        # ── Explicit markdown headers ──
        if is_md_header(key):
            lines.append(f"\n{key.strip()}")
            i += 1
            continue

        # ── Section header (single cell) — check if section is empty ──
        if is_section_header(vals):
            # Look ahead: collect lines until next section header or EOF
            j = i + 1
            section_content = []
            while j < n:
                ahead = all_rows[j]
                ahead_key = ahead[0] if ahead else ""
                if is_section_header(ahead) or is_md_header(ahead_key):
                    break
                if not is_empty_row(ahead) and not is_separator_row(ahead):
                    section_content.append(ahead)
                j += 1

            # Only emit section header if it has content
            if section_content:
                lines.append(f"\n## {key}")
            i += 1
            continue

        # ── Table block ──
        if is_table_row(vals):
            table_rows = []
            while i < n:
                r = all_rows[i]
                if is_separator_row(r):       # skip === rows inside table
                    i += 1
                    continue
                if not is_table_row(r):
                    break
                trimmed = r[:]
                while trimmed and not trimmed[-1]:
                    trimmed.pop()
                table_rows.append(trimmed)
                i += 1
            if table_rows:
                if lines and lines[-1] != "":
                    lines.append("")
                lines.append(render_table(table_rows))
                lines.append("")
            continue

        # ── Key: Value ──
        if is_kv_row(vals):
            lines.append(f"**{key}:** {vals[1]}")
            i += 1
            continue

        # ── Fallback ──
        if key:
            lines.append(key)
        i += 1

    body = "\n".join(lines).strip()

    # Append computed snapshot
    snapshot = build_context_snapshot(df)
    return body + "\n" + snapshot


# ─── Output helpers ───────────────────────────────────────────────────────────

def yaml_frontmatter(sheet_name, source_file):
    return (
        f"---\n"
        f"athlete: {sheet_name}\n"
        f"generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"source: {os.path.basename(source_file)}\n"
        f"---\n"
    )


def safe_filename(name):
    safe = name.replace(" ", "_")
    for ch in r'\/*?:<>|"':
        safe = safe.replace(ch, "-")
    return safe


def resolve_sheets(all_sheets, choice):
    if choice.lower() == "all":
        return [s for s in all_sheets if s != SUMMARY_SHEET]
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(all_sheets):
            return [all_sheets[idx]]
        raise ValueError(f"Number {choice} out of range (1–{len(all_sheets)})")
    if choice in all_sheets:
        return [choice]
    raise ValueError(f"Sheet '{choice}' not found")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    input_file = input("Excel filename (e.g., athletes_report_production.xlsx): ").strip()
    if not input_file.endswith(".xlsx"):
        input_file += ".xlsx"

    if not os.path.exists(input_file):
        print(f"\n❌ File not found: '{input_file}'")
        sys.exit(1)

    try:
        xl = pd.ExcelFile(input_file, engine="openpyxl")
    except Exception as e:
        print(f"\n❌ Cannot open file: {e}")
        sys.exit(1)

    all_sheets     = xl.sheet_names
    athlete_sheets = [s for s in all_sheets if s != SUMMARY_SHEET]

    if len(all_sheets) == 1:
        sheets_to_convert = all_sheets
    else:
        print(f"\nSheets found ({len(all_sheets)} total, {len(athlete_sheets)} athlete sheets):")
        for idx, name in enumerate(all_sheets, 1):
            tag = "  [summary — skipped in 'all']" if name == SUMMARY_SHEET else ""
            print(f"  {idx}. {name}{tag}")

        choice = input(
            "\nConvert which sheet? (number / name / 'all' for all athlete sheets): "
        ).strip()

        try:
            sheets_to_convert = resolve_sheets(all_sheets, choice)
        except ValueError as e:
            print(f"\n❌ {e}")
            sys.exit(1)

    out_dir = "athlete_docs"
    os.makedirs(out_dir, exist_ok=True)

    print()
    converted = []
    for sheet_name in sheets_to_convert:
        try:
            df = pd.read_excel(
                input_file, sheet_name=sheet_name, header=None, engine="openpyxl"
            )
            content      = convert_sheet(df, sheet_name)
            frontmatter  = yaml_frontmatter(sheet_name, input_file)
            full_content = frontmatter + "\n" + content + "\n"

            out_filename = safe_filename(sheet_name) + ".md"
            out_path     = os.path.join(out_dir, out_filename)

            if os.path.exists(out_path):
                print(f"  ⚠️  Overwriting: {out_filename}")

            with open(out_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(full_content)

            converted.append(out_path)
            print(f"  ✓ {sheet_name} → {out_path}")

        except Exception as e:
            print(f"  ❌ Error converting '{sheet_name}': {e}")

    print(f"\n✅ Done. {len(converted)} file(s) saved to '{out_dir}/'")


if __name__ == "__main__":
    main()
