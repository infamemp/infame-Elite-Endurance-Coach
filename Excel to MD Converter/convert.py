"""
intervals.icu Excel → Markdown Converter
Converts athlete sheets from athletes_report_production.xlsx into
clean .md context documents for use in Claude Projects.

Usage:  python convert.py
Req:    pip install pandas openpyxl
"""

import os
import sys
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    print("❌ Missing dependency: pip install pandas openpyxl")
    sys.exit(1)

# Sheet name to skip (summary is for humans, not AI context)
SUMMARY_SHEET = "Athletes Summary"

# Minimum filled columns to treat a row as a table row
TABLE_COL_THRESHOLD = 3


# ─── Value helpers ────────────────────────────────────────────────────────────

def clean_value(val):
    """Return clean string or empty string for nan/None/—."""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    s = str(val).strip()
    return "" if s in ("nan", "None") else s


def row_values(row):
    """All cell values in a row as clean strings."""
    return [clean_value(row.iloc[i]) for i in range(len(row))]


def filled_count(vals):
    """Number of non-empty values in a list."""
    return sum(1 for v in vals if v)


# ─── Block detection ─────────────────────────────────────────────────────────

def is_empty_row(vals):
    return not any(vals)


def is_separator(key):
    return key.startswith("===") or key.startswith("---")


def is_section_header(vals):
    """A section title: single non-empty cell that spans (rest empty)."""
    key = vals[0] if vals else ""
    rest_empty = filled_count(vals[1:]) == 0
    return rest_empty and key and not key.startswith("#")


def is_md_header(key):
    return key.startswith("# ") or key.startswith("## ") or key in ("# ", "## ")


def is_kv_row(vals):
    """Key in col0, value in col1, rest empty."""
    return (
        len(vals) >= 2
        and vals[0]
        and vals[1]
        and filled_count(vals[2:]) == 0
    )


def is_table_row(vals):
    """3+ filled cells across the row."""
    return filled_count(vals) >= TABLE_COL_THRESHOLD


# ─── Table rendering ─────────────────────────────────────────────────────────

def render_table(rows):
    """
    Given a list of rows (list of string lists), render as markdown table.
    First row is treated as header.
    Columns are determined by the widest row.
    """
    if not rows:
        return ""

    ncols = max(len(r) for r in rows)

    # Pad all rows to same width
    padded = [r + [""] * (ncols - len(r)) for r in rows]

    # Column widths
    widths = [max(len(str(padded[i][c])) for i in range(len(padded))) for c in range(ncols)]
    widths = [max(w, 3) for w in widths]

    def fmt_row(r):
        cells = [str(r[c]).ljust(widths[c]) for c in range(ncols)]
        return "| " + " | ".join(cells) + " |"

    lines = []
    lines.append(fmt_row(padded[0]))                          # header
    lines.append("| " + " | ".join("-" * w for w in widths) + " |")  # separator
    for r in padded[1:]:
        lines.append(fmt_row(r))

    return "\n".join(lines)


# ─── Sheet conversion ─────────────────────────────────────────────────────────

def convert_sheet(df, sheet_name):
    """
    Convert a DataFrame to markdown string.
    Detects blocks: section headers, key-value pairs, and tables.
    """
    lines = []

    # Collect all rows as value lists
    all_rows = [row_values(df.iloc[i]) for i in range(len(df))]

    i = 0
    while i < len(all_rows):
        vals = all_rows[i]
        key  = vals[0] if vals else ""

        # ── Empty row ──
        if is_empty_row(vals):
            if lines and lines[-1] != "":
                lines.append("")
            i += 1
            continue

        # ── Separator ──
        if is_separator(key):
            i += 1
            continue

        # ── Explicit markdown headers ──
        if is_md_header(key):
            lines.append(f"\n{key.strip()}")
            i += 1
            continue

        # ── Table block: collect consecutive table rows ──
        if is_table_row(vals):
            table_rows = []
            while i < len(all_rows) and is_table_row(all_rows[i]):
                # Trim trailing empty cells
                r = all_rows[i]
                while r and not r[-1]:
                    r = r[:-1]
                table_rows.append(r)
                i += 1
            if table_rows:
                if lines and lines[-1] != "":
                    lines.append("")
                lines.append(render_table(table_rows))
                lines.append("")
            continue

        # ── Section title (single cell, no value) ──
        if is_section_header(vals):
            lines.append(f"\n## {key}")
            i += 1
            continue

        # ── Key: Value pair ──
        if is_kv_row(vals):
            lines.append(f"**{key}:** {vals[1]}")
            i += 1
            continue

        # ── Fallback: key only ──
        if key:
            lines.append(key)
        i += 1

    return "\n".join(lines).strip()


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
    """Convert sheet name to safe filename."""
    safe = name.replace(" ", "_")
    for ch in r'\/*?:<>|"':
        safe = safe.replace(ch, "-")
    return safe


def resolve_sheets(all_sheets, choice):
    """Resolve user sheet choice to list of sheet names. Raises ValueError if invalid."""
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
    # ── File input ──
    input_file = input("Excel filename (e.g., athletes_report_production.xlsx): ").strip()
    if not input_file.endswith(".xlsx"):
        input_file += ".xlsx"

    if not os.path.exists(input_file):
        print(f"\n❌ File not found: '{input_file}'")
        sys.exit(1)

    # ── Load workbook ──
    try:
        xl = pd.ExcelFile(input_file, engine="openpyxl")
    except Exception as e:
        print(f"\n❌ Cannot open file: {e}")
        sys.exit(1)

    all_sheets = xl.sheet_names
    athlete_sheets = [s for s in all_sheets if s != SUMMARY_SHEET]

    # ── Sheet selection ──
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

    # ── Output folder ──
    out_dir = "athlete_docs"
    os.makedirs(out_dir, exist_ok=True)

    # ── Convert ──
    print()
    converted = []
    for sheet_name in sheets_to_convert:
        try:
            df = pd.read_excel(
                input_file, sheet_name=sheet_name, header=None, engine="openpyxl"
            )
            content   = convert_sheet(df, sheet_name)
            frontmatter = yaml_frontmatter(sheet_name, input_file)
            full_content = frontmatter + "\n" + content + "\n"

            out_filename = safe_filename(sheet_name) + ".md"
            out_path     = os.path.join(out_dir, out_filename)

            # Warn before overwrite
            if os.path.exists(out_path):
                print(f"  ⚠️  Overwriting existing: {out_filename}")

            with open(out_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(full_content)

            converted.append(out_path)
            print(f"  ✓ {sheet_name} → {out_path}")

        except Exception as e:
            print(f"  ❌ Error converting '{sheet_name}': {e}")

    print(f"\n✅ Done. {len(converted)} file(s) saved to '{out_dir}/'")


if __name__ == "__main__":
    main()
