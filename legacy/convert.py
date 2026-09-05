"""
intervals.icu Excel → Markdown Converter
Converts athlete sheets from athletes_report_production.xlsx into
clean .md context documents for use in Claude Projects.

Usage:  python convert.py
Req:    pip install pandas openpyxl
"""

import os
import re
import sys
import unicodedata
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


def is_continuation_row(vals):
    """Col 0 vacía pero al menos una celda posterior tiene dato.
    Identifica sub-filas de un bloque agrupado (e.g. Indoor FTP, eFTP, Threshold HR
    bajo el sport 'Ride') que el umbral TABLE_COL_THRESHOLD no atrapa porque solo
    tienen 2 celdas llenas y col 0 vacía."""
    return bool(vals) and not vals[0] and filled_count(vals[1:]) >= 1


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


# ─── Sport config renderer ───────────────────────────────────────────────────

def is_sport_config_table(table_rows):
    """True si la primera fila es el header Sport / Metric / Configured Value."""
    if not table_rows:
        return False
    h = [v.lower().strip() for v in table_rows[0]]
    return "sport" in h and any("metric" in v for v in h)


def render_sport_table(table_rows):
    """Renderiza la config de deportes como sub-bloques independientes:
    ### Ride / Run / Swim  +  tabla de 2 columnas (Metric | Value).
    Elimina la columna 'Sport' redundante y separa visualmente cada deporte."""
    data_rows = table_rows[1:]   # saltar el header Sport|Metric|Value

    # Agrupar filas por deporte (col 0 no vacía = nuevo deporte)
    groups = []     # [(sport_name, [(metric, value), ...]), ...]
    current_sport   = None
    current_metrics = []
    for row in data_rows:
        sport  = row[0].strip() if row else ""
        metric = row[1].strip() if len(row) > 1 else ""
        value  = row[2].strip() if len(row) > 2 else ""
        if sport:
            if current_sport is not None:
                groups.append((current_sport, current_metrics))
            current_sport   = sport
            current_metrics = [(metric, value)]
        elif current_sport is not None:
            current_metrics.append((metric, value))
    if current_sport is not None:
        groups.append((current_sport, current_metrics))

    lines = []
    for idx, (sport_name, metrics) in enumerate(groups):
        if idx > 0:
            lines.append("")   # separador visual entre deportes
        lines.append(f"### {sport_name}")
        if metrics:
            w1 = max(len("Metric / Parameter"), max(len(m) for m, _ in metrics))
            w2 = max(len("Configured Value"),   max(len(v) for _, v in metrics))
            fmt = lambda m, v: f"| {m.ljust(w1)} | {v.ljust(w2)} |"
            lines.append(fmt("Metric / Parameter", "Configured Value"))
            lines.append(f"| {'-' * w1} | {'-' * w2} |")
            for metric, value in metrics:
                lines.append(fmt(metric, value))
    return "\n".join(lines)


# ─── Context Snapshot ─────────────────────────────────────────────────────────

def parse_duration_to_hours(dur_str):
    """Parse '1h 30m', '45m 10s' o '1h 30m 45s' a horas flotantes."""
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
            dur_str = parts[1]          # actualizar residuo para capturar segundos
        if "s" in dur_str:
            parts = dur_str.split("s")
            total += float(parts[0].strip()) / 3600
        return total
    except Exception:
        return 0.0


def _build_col_map(header_vals):
    """Construye un mapa nombre_columna_lowercase → índice a partir del header row.
    Permite acceder a columnas por nombre en lugar de índice hardcodeado."""
    return {v.lower().strip(): ci for ci, v in enumerate(header_vals) if v}


def _col(vals, col_map, name, default_idx):
    """Devuelve vals[idx].strip() usando col_map; cae al default_idx si no hay mapa."""
    idx = col_map.get(name, default_idx)
    return vals[idx].strip() if idx < len(vals) else ""


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
    race_cols     = {}          # mapa nombre → índice, construido desde el header row
    next_a = None
    for i in range(len(df)):
        vals = row_values(df.iloc[i])
        key  = vals[0] if vals else ""

        if "RACE CALENDAR" in key.upper() or "SCHEDULED RACES" in key.upper():
            in_race_table = True
            race_cols     = {}  # resetear al entrar en la sección
            continue

        # Salir al entrar en cualquier sección que no sea la de carreras
        if in_race_table and (is_section_header(vals) or is_md_header(key)) and "RACE" not in key.upper():
            in_race_table = False

        if in_race_table and is_table_row(vals) and not is_separator_row(vals):
            if vals[0].lower() in ("date", "fecha"):
                race_cols = _build_col_map(vals)    # capturar mapa desde el header
                continue
            raw_date  = _col(vals, race_cols, "date",       0)
            priority  = _col(vals, race_cols, "priority",   5)
            race_name = _col(vals, race_cols, "event name", 1) or "?"
            if priority.upper() == "A" and raw_date and not raw_date.startswith("="):
                try:
                    race_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
                    if race_date >= today:
                        if next_a is None or race_date < next_a[0]:
                            next_a = (race_date, race_name)
                except Exception:
                    pass

    if next_a:
        days = (next_a[0] - today).days
        lines.append(f"**Next A-race:** {next_a[1]} — {next_a[0].isoformat()} ({days} days away)")
    else:
        lines.append("**Next A-race:** None scheduled")

    # ── Activity stats (4w) ──
    in_act_table  = False
    act_cols      = {}          # mapa nombre → índice, construido desde el header row
    total_tss     = 0.0
    total_hours   = 0.0
    sport_counts  = {}
    act_count     = 0

    for i in range(len(df)):
        vals = row_values(df.iloc[i])
        key  = vals[0] if vals else ""

        if "RECENT ACTIVITIES" in key.upper() or "LAST 4 WEEKS" in key.upper():
            in_act_table = True
            act_cols     = {}   # resetear al entrar en la sección
            continue

        # Salir al entrar en una nueva sección
        if in_act_table and (is_section_header(vals) or is_md_header(key)):
            in_act_table = False

        if in_act_table and is_table_row(vals) and not is_separator_row(vals):
            if vals[0].lower() in ("date", "fecha"):
                act_cols = _build_col_map(vals)     # capturar mapa desde el header
                continue
            if vals[0].startswith("="):
                continue
            try:
                sport   = _col(vals, act_cols, "sport",    2)
                dur_str = _col(vals, act_cols, "duration", 3)
                tss_str = _col(vals, act_cols, "tss/load", 5)

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
                if is_empty_row(r):
                    # Peek-ahead: saltar la fila vacía solo si el siguiente contenido
                    # es también tabla/continuación (p.ej. bloques Run/Swim tras Ride).
                    # Si viene un section header, KV row u otro tipo → romper.
                    j = i + 1
                    while j < n and is_empty_row(all_rows[j]):
                        j += 1
                    if j < n and (is_table_row(all_rows[j]) or is_continuation_row(all_rows[j])):
                        i += 1   # absorber la(s) fila(s) vacía(s) y seguir
                        continue
                    break        # siguiente contenido no es tabla → fin del bloque
                if not is_table_row(r) and not is_continuation_row(r):
                    break
                trimmed = r[:]
                while trimmed and not trimmed[-1]:
                    trimmed.pop()
                table_rows.append(trimmed)
                i += 1
            if table_rows:
                if lines and lines[-1] != "":
                    lines.append("")
                if is_sport_config_table(table_rows):
                    lines.append(render_sport_table(table_rows))
                else:
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
    # 1. Normalizar unicode → ASCII (é→e, ñ→n, ü→u, á→a, etc.)
    normalized = unicodedata.normalize("NFKD", name)
    safe = normalized.encode("ascii", "ignore").decode("ascii")
    # 2. Convertir caracteres no alfanuméricos (excepto guión) a espacio,
    #    para que " & " o "/García" no produzcan "_-_" al colapsar
    safe = re.sub(r"[^\w\s-]", " ", safe)
    # 3. Colapsar whitespace y convertir a guiones bajos
    safe = re.sub(r"\s+", "_", safe.strip())
    # 4. Colapsar secuencias repetidas de guiones y guiones bajos
    safe = re.sub(r"_+", "_", safe)
    safe = re.sub(r"-+", "-", safe)
    # 5. Limpiar extremos
    safe = safe.strip("-_")
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
