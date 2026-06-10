import pandas as pd
import os
import sys


def clean_value(val):
    """Return clean string or empty string for nan/None."""
    if pd.isna(val):
        return ""
    s = str(val).strip()
    return "" if s == "nan" else s


def row_values(row):
    """Return all non-empty values from a row."""
    return [clean_value(row.iloc[i]) for i in range(len(row))]


def is_separator(key):
    return key.startswith("===") or key.startswith("---")


def is_multi_column(row):
    """True if this row has meaningful data beyond column 1."""
    vals = row_values(row)
    return sum(1 for v in vals[2:] if v) > 0


def convert_sheet(df):
    lines = []

    for _, row in df.iterrows():
        vals = row_values(row)
        key = vals[0] if vals else ""
        val = vals[1] if len(vals) > 1 else ""

        # Fully empty row → blank line
        if not any(vals):
            if lines and lines[-1] != "":
                lines.append("")
            continue

        # Separator → skip
        if is_separator(key):
            continue

        # Section headers
        if key.startswith("## ") or key == "##":
            lines.append(f"\n{key}")
            continue
        if key.startswith("# ") or key == "#":
            lines.append(f"\n{key}")
            continue

        # Multi-column row (races, activities, sport config)
        if is_multi_column(row):
            non_empty = [v for v in vals if v]
            lines.append("  ".join(non_empty))
            continue

        # Standard key: value
        if key and val:
            lines.append(f"{key:<28} {val}")
        elif key and not val:
            lines.append(key)
        elif not key and val:
            lines.append(f"{'':28} {val}")

    return "\n".join(lines).strip()


def main():
    input_file = input("Enter your Excel filename (e.g., Athlete_Template.xlsx): ").strip()

    if not input_file.endswith(".xlsx"):
        input_file += ".xlsx"

    if not os.path.exists(input_file):
        print(f"\n❌ Error: '{input_file}' not found in this folder.")
        sys.exit(1)

    try:
        xl = pd.ExcelFile(input_file, engine="openpyxl")
        all_sheets = xl.sheet_names

        if len(all_sheets) > 1:
            print(f"\nSheets found:")
            for i, name in enumerate(all_sheets, 1):
                print(f"  {i}. {name}")
            choice = input("\nConvert which sheet? (name or number, or 'all'): ").strip()

            if choice.lower() == "all":
                sheets_to_convert = all_sheets
            elif choice.isdigit():
                sheets_to_convert = [all_sheets[int(choice) - 1]]
            else:
                sheets_to_convert = [choice]
        else:
            sheets_to_convert = all_sheets

        for sheet_name in sheets_to_convert:
            df = pd.read_excel(
                input_file, sheet_name=sheet_name, header=None, engine="openpyxl"
            )

            output_file = f"{sheet_name.replace(' ', '_')}.md"
            content = convert_sheet(df)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content + "\n")

            print(f"✓ {sheet_name} → {output_file}")

        print("\nDone.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
