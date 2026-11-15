#!/usr/bin/env python3
# =============================================================================
#  Waste-Adjusted Prep Quantity Advisor  (Python port of main.cpp)
#  For: Tapon Sahu, BH-7 Mess, NIT Silchar
#
#  Reads historical kitchen logs from data.csv and recommends how much of an
#  item to prepare for the coming shift, based on what students ACTUALLY
#  consumed per head in past meals (not what was cooked).
#
#  Run : python3 advisor.py "rice" 215            (item keyword, headcount)
#        python3 advisor.py "Aloo Chop" 250 other.csv   (optional CSV path)
#        python3 advisor.py                       (interactive prompts)
#
#  Expected CSV header (column ORDER does not matter, names do):
#  date,meal_type,item_name,prepared_qty,unit,students_served,
#  leftover_qty,shortage_refill_qty,recorded_by_place
#
#  Uses only the Python standard library (Python 3.7+).
# =============================================================================

import csv
import math
import sys
from dataclasses import dataclass

# =============================================================================
#  CONFIGURABLE THRESHOLDS  -- edit these live, then rerun.
# =============================================================================

# Extra buffer added on top of the average net consumed per student.
SAFETY_BUFFER_PERCENT = 5.0

# If average leftover OR average shortage-refill (as % of prepared quantity)
# exceeds this, the item is flagged as a waste / shortage risk.
HIGH_VARIANCE_ALERT_PERCENT = 8.0

# CSV file used when no path is given on the command line.
DEFAULT_CSV_PATH = "data.csv"

# =============================================================================
#  Data types
# =============================================================================

# Column names the CSV must contain.
REQUIRED_COLUMNS = [
    "date", "meal_type", "item_name", "prepared_qty", "unit",
    "students_served", "leftover_qty", "shortage_refill_qty",
    "recorded_by_place",
]

# Units that count whole things; recommendations for these round UP to integers.
COUNT_UNITS = {"pcs", "pc", "piece", "pieces", "nos", "no", "count", "eggs",
               "egg", "units", "unit"}


@dataclass
class Record:
    """One valid, fully parsed row of data.csv."""
    line_num: int            # physical line number in the file (for warnings)
    date: str
    meal_type: str
    item_name: str
    unit: str
    place: str
    prepared: float          # prepared_qty
    students: float          # students_served
    leftover: float          # leftover_qty
    refill: float            # shortage_refill_qty
    net_consumed: float      # prepared - leftover + refill
    per_student_rate: float  # net_consumed / students


# =============================================================================
#  Small helpers
# =============================================================================

def parse_number(raw):
    """Strict number parser: the WHOLE field must be a plain finite number.

    Returns a float, or None if the field is not valid. (float() alone would
    accept things like "nan", "inf" or "1_000".)
    """
    s = raw.strip()
    if not s or any(c not in "0123456789.+-eE" for c in s):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def is_count_unit(unit):
    return unit.strip().lower() in COUNT_UNITS


def round_up_for_unit(value, unit):
    """Round UP so we never under-recommend due to rounding."""
    if is_count_unit(unit):
        return float(math.ceil(value))
    return math.ceil(value * 10.0) / 10.0


def fmt_qty(value, unit):
    """0 decimals for counts, 1 decimal otherwise."""
    return f"{value:.{0 if is_count_unit(unit) else 1}f}"


def fmt_pct(v):
    return f"{v:.1f}%"


def split_csv_line(line):
    """Split one CSV line into fields (supports quotes). None if malformed."""
    try:
        rows = list(csv.reader([line], strict=True))
    except csv.Error:
        return None                      # e.g. unterminated quote
    return rows[0] if rows else [""]


# =============================================================================
#  CSV loading with bad-row handling
# =============================================================================

def parse_row(line, line_num, col, header_count):
    """Turn one data line into a Record.

    Returns (record, None) on success or (None, reason) on failure.
    """
    f = split_csv_line(line)
    if f is None:
        return None, "unterminated quote"
    if len(f) < header_count:
        return None, f"missing columns (expected {header_count}, found {len(f)})"
    if len(f) > header_count:
        return None, f"too many columns (expected {header_count}, found {len(f)})"

    # col[i] = index in the row of REQUIRED_COLUMNS[i]
    date = f[col[0]].strip()
    meal_type = f[col[1]].strip()
    item_name = f[col[2]].strip()
    unit = f[col[4]].strip()
    place = f[col[8]].strip()

    if not item_name:
        return None, "empty item_name"
    if not unit:
        return None, "empty unit"

    # Numeric fields: (REQUIRED_COLUMNS index, name)
    values = {}
    for idx, name in ((3, "prepared_qty"), (5, "students_served"),
                      (6, "leftover_qty"), (7, "shortage_refill_qty")):
        raw = f[col[idx]]
        num = parse_number(raw)
        if num is None:
            return None, f"non-numeric or missing {name} ('{raw.strip()}')"
        values[name] = num

    prepared = values["prepared_qty"]
    students = values["students_served"]
    leftover = values["leftover_qty"]
    refill = values["shortage_refill_qty"]

    if students <= 0:
        return None, f"students_served must be > 0 (got {f[col[5]].strip()})"
    if prepared <= 0:
        return None, "prepared_qty must be > 0"
    if leftover < 0 or refill < 0:
        return None, "negative leftover_qty or shortage_refill_qty"

    net = prepared - leftover + refill
    if net < 0:
        return None, ("net consumption is negative (leftover_qty larger than "
                      "prepared_qty + shortage_refill_qty)")

    return Record(line_num, date, meal_type, item_name, unit, place,
                  prepared, students, leftover, refill, net,
                  net / students), None


def load_csv(path):
    """Load the whole CSV. Bad rows are skipped with a [WARN] line.

    Returns (records, total_rows, skipped_rows), or None on a fatal problem
    (file missing / bad header).
    """
    try:
        # utf-8-sig strips a BOM; universal newlines handle CRLF files.
        fh = open(path, "r", encoding="utf-8-sig", errors="replace")
    except OSError:
        print(f"[ERROR] Cannot open '{path}'. "
              "Put data.csv next to the program or pass its path.",
              file=sys.stderr)
        return None

    records = []
    total_rows = skipped_rows = 0
    col = []                 # column mapping, filled from the header
    header_count = 0
    header_seen = False

    with fh:
        for line_num, line in enumerate(fh, start=1):
            line = line.rstrip("\r\n")
            if not line.strip():
                continue                                   # blank line

            if not header_seen:
                names = split_csv_line(line)
                if names is None:
                    print("[ERROR] Header row is malformed.", file=sys.stderr)
                    return None
                header_count = len(names)
                lowered = [n.strip().lower() for n in names]
                for req in REQUIRED_COLUMNS:
                    if req not in lowered:
                        print(f"[ERROR] Header is missing required column "
                              f"'{req}'.", file=sys.stderr)
                        return None
                    col.append(lowered.index(req))
                header_seen = True
                continue

            total_rows += 1
            rec, reason = parse_row(line, line_num, col, header_count)
            if rec is not None:
                records.append(rec)
            else:
                skipped_rows += 1
                print(f"[WARN] Skipping malformed row {line_num}: {reason}")

    if not header_seen:
        print(f"[ERROR] '{path}' is empty.", file=sys.stderr)
        return None
    return records, total_rows, skipped_rows


# =============================================================================
#  User input helpers (command-line args with interactive fallback)
# =============================================================================

def prompt_keyword():
    while True:
        try:
            keyword = input("Item keyword (e.g. rice, Boiled eggs, "
                            "Aloo Chop, Chicken): ").strip()
        except EOFError:
            return None
        if keyword:
            return keyword
        print("  Please enter a non-empty keyword.")


def prompt_headcount():
    while True:
        try:
            s = input("Expected student headcount for the upcoming shift: ")
        except EOFError:
            return None
        value = parse_number(s)
        if value is not None and value > 0:
            return value
        print("  Please enter a positive number (e.g. 215).")


# =============================================================================
#  Advisor report
# =============================================================================

def print_row(label, value):
    print(f"  {label:<32}: {value}")


def advise(records, keyword, headcount):
    # ---- 1. Find rows whose item_name contains the keyword -----------------
    kw = keyword.lower()
    matched = [r for r in records if kw in r.item_name.lower()]

    if not matched:
        print(f"\nNo valid historical rows match '{keyword}'.")
        print("Items available in data.csv:")
        seen = []
        for r in records:
            low = r.item_name.lower()
            if low not in seen:
                seen.append(low)
                print(f"  - {r.item_name}")
        return

    # ---- 2. Keep rows in the dominant unit (never mix kg with pieces) ------
    units, unit_count = [], []           # distinct units (lower-cased) + counts
    for r in matched:
        u = r.unit.lower()
        if u in units:
            unit_count[units.index(u)] += 1
        else:
            units.append(u)
            unit_count.append(1)
    best = max(range(len(units)), key=lambda i: unit_count[i])  # first max wins
    dominant_unit_lower = units[best]

    unit = next(r.unit for r in matched if r.unit.lower() == dominant_unit_lower)
    rows = []
    for r in matched:
        if r.unit.lower() == dominant_unit_lower:
            rows.append(r)
        else:
            print(f"[WARN] Skipping row {r.line_num}: unit '{r.unit}' differs "
                  f"from dominant unit '{unit}' for this item")

    # ---- 3. Aggregate statistics -------------------------------------------
    n = len(rows)
    sum_rate = sum_prepared = sum_students = 0.0
    sum_left_pct = sum_short_pct = 0.0
    heavy_leftover = heavy_shortage = 0
    names = []                           # distinct matched item names

    for r in rows:
        sum_rate += r.per_student_rate   # mean of per-row rates
        sum_prepared += r.prepared
        sum_students += r.students
        left_pct = r.leftover / r.prepared * 100.0
        short_pct = r.refill / r.prepared * 100.0
        sum_left_pct += left_pct
        sum_short_pct += short_pct
        if left_pct > HIGH_VARIANCE_ALERT_PERCENT:
            heavy_leftover += 1
        if short_pct > HIGH_VARIANCE_ALERT_PERCENT:
            heavy_shortage += 1
        if r.item_name.lower() not in [x.lower() for x in names]:
            names.append(r.item_name)

    avg_rate = sum_rate / n
    avg_prepared = sum_prepared / n
    avg_students = sum_students / n
    avg_left_pct = sum_left_pct / n
    avg_short_pct = sum_short_pct / n

    # ---- 4. Recommendation --------------------------------------------------
    raw_recommended = avg_rate * headcount * (1.0 + SAFETY_BUFFER_PERCENT / 100.0)
    recommended = round_up_for_unit(raw_recommended, unit)
    diff = recommended - avg_prepared

    print("\n=========== WASTE-ADJUSTED PREP ADVISOR (BH-7 Mess) ===========")
    print_row("Item keyword", keyword)
    print_row("Matched items", ", ".join(names))
    print_row("Historical meals matched", str(n))
    precision = 2 if is_count_unit(unit) else 3
    print_row("Avg net consumption / student", f"{avg_rate:.{precision}f} {unit}")
    print_row("Expected headcount", fmt_qty(headcount, "pcs"))
    print_row("Safety buffer", fmt_pct(SAFETY_BUFFER_PERCENT))
    print("  ----------------------------------------------------------")
    print_row("RECOMMENDED PREP QUANTITY", f"{fmt_qty(recommended, unit)} {unit}")
    print_row("Historical avg batch size",
              f"{fmt_qty(avg_prepared, unit)} {unit}  "
              f"(served ~{fmt_qty(avg_students, 'pcs')} students)")

    if abs(diff) < (0.5 if is_count_unit(unit) else 0.05):
        cmp = "about the same as the average batch"
    elif diff > 0:
        cmp = f"ADD {fmt_qty(diff, unit)} {unit} vs average batch"
    else:
        cmp = f"SAVE {fmt_qty(-diff, unit)} {unit} vs average batch"
    print_row("Versus average batch", cmp)

    # ---- 5. Waste / shortage risk alerts ------------------------------------
    print("  ----------------------------------------------------------")
    thr = fmt_pct(HIGH_VARIANCE_ALERT_PERCENT)
    print_row("Avg leftover (% of prepared)",
              f"{fmt_pct(avg_left_pct)}  ({heavy_leftover} of {n} meals above {thr})")
    print_row("Avg shortage refill (% prepared)",
              f"{fmt_pct(avg_short_pct)}  ({heavy_shortage} of {n} meals above {thr})")

    waste_risk = avg_left_pct > HIGH_VARIANCE_ALERT_PERCENT
    short_risk = avg_short_pct > HIGH_VARIANCE_ALERT_PERCENT
    if waste_risk:
        print(f"  [ALERT] WASTE RISK: leftovers average "
              f"{fmt_pct(avg_left_pct)} of what is prepared.")
    if short_risk:
        print(f"  [ALERT] SHORTAGE RISK: mid-shift refills average "
              f"{fmt_pct(avg_short_pct)} of what is prepared.")
    if waste_risk and short_risk:
        print("  [TIP]   Demand for this item swings both ways. "
              "Consider cooking in two smaller batches.")
    elif short_risk:
        print("  [TIP]   Keep raw material ready for a quick top-up.")
    elif waste_risk:
        print("  [TIP]   Consider preparing in smaller batches and "
              "topping up if needed.")
    if not waste_risk and not short_risk:
        print(f"  No high-variance alert: past prep matched demand within {thr}.")

    print("================================================================")


# =============================================================================
#  main
# =============================================================================

def main(argv):
    csv_path = argv[3] if len(argv) >= 4 else DEFAULT_CSV_PATH

    # ---- Load and validate the CSV -----------------------------------------
    loaded = load_csv(csv_path)
    if loaded is None:
        return 1
    records, total_rows, skipped_rows = loaded

    print(f"Loaded {len(records)} valid row(s) from '{csv_path}' "
          f"({skipped_rows} of {total_rows} data row(s) skipped).")
    if not records:
        print("[ERROR] No usable rows. Nothing to advise on.", file=sys.stderr)
        return 1

    # ---- Get keyword + headcount (arguments first, prompts as fallback) ----
    if len(argv) >= 2 and argv[1].strip():
        keyword = argv[1].strip()
    else:
        keyword = prompt_keyword()
        if keyword is None:
            return 1

    headcount = parse_number(argv[2]) if len(argv) >= 3 else None
    if headcount is None or headcount <= 0:
        if len(argv) >= 3:
            print(f"[WARN] Headcount '{argv[2]}' is not a positive number.")
        headcount = prompt_headcount()
        if headcount is None:
            return 1

    advise(records, keyword, headcount)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))