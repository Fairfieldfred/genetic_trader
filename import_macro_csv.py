"""
Import macroeconomic data from a CSV file into spy.db.

Fallback for users who cannot use the FRED API or want to
provide custom macro indicator data.

Usage:
    # Import from CSV
    python import_macro_csv.py macro_data.csv

    # Generate a sample template CSV
    python import_macro_csv.py --template

    # Specify database path
    python import_macro_csv.py macro_data.csv --db spy.db
"""

import argparse
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXPECTED_COLUMNS = [
    "date",
    "vix_close",
    "us10y_yield",
    "us02y_yield",
    "yield_curve_slope",
    "fed_funds_rate",
    "cpi_yoy",
    "unemployment_rate",
]

REQUIRED_COLUMNS = ["date"]


def generate_template(output_path: str = "macro_template.csv"):
    """
    Generate a sample CSV template with column headers and example rows.

    Args:
        output_path: Path for the output CSV file.
    """
    sample = pd.DataFrame({
        "date": ["2020-01-02", "2020-01-03", "2020-01-06"],
        "vix_close": [13.78, 14.02, 14.58],
        "us10y_yield": [1.88, 1.82, 1.80],
        "us02y_yield": [1.57, 1.53, 1.53],
        "yield_curve_slope": [0.31, 0.29, 0.27],
        "fed_funds_rate": [1.55, 1.55, 1.55],
        "cpi_yoy": [2.3, 2.3, 2.3],
        "unemployment_rate": [3.5, 3.5, 3.5],
    })
    sample.to_csv(output_path, index=False)
    print(f"Template written to: {output_path}")
    print(f"\nColumns: {', '.join(EXPECTED_COLUMNS)}")
    print("\nNotes:")
    print("  - 'date' column is required (YYYY-MM-DD format)")
    print("  - All other columns are optional (missing = NULL)")
    print("  - Monthly data should be forward-filled to daily frequency")
    print("  - yield_curve_slope = us10y_yield - us02y_yield")


def validate_csv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and clean a CSV DataFrame for import.

    Args:
        df: Raw DataFrame from CSV.

    Returns:
        Cleaned DataFrame ready for database insertion.

    Raises:
        ValueError: If required columns are missing or dates are invalid.
    """
    # Check required columns
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Warn about unexpected columns
    unexpected = [c for c in df.columns if c not in EXPECTED_COLUMNS]
    if unexpected:
        print(f"  Warning: Ignoring unexpected columns: {unexpected}")
        df = df[[c for c in df.columns if c in EXPECTED_COLUMNS]]

    # Validate date format
    try:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    except Exception as e:
        raise ValueError(f"Invalid date format: {e}") from e

    # Check for duplicate dates
    dupes = df[df["date"].duplicated()]
    if not dupes.empty:
        print(f"  Warning: {len(dupes)} duplicate dates found, keeping last")
        df = df.drop_duplicates(subset=["date"], keep="last")

    # Convert numeric columns
    numeric_cols = [c for c in df.columns if c != "date"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def import_csv(csv_path: str, db_path: str):
    """
    Import a CSV file into the macro_indicators table.

    Args:
        csv_path: Path to the CSV file.
        db_path: Path to the SQLite database.
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    db_file = Path(db_path)
    if not db_file.exists():
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    # Ensure table exists
    from create_macro_table import create_macro_table
    create_macro_table(db_path)

    # Read and validate
    print(f"\nReading: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"  Rows: {len(df)}, Columns: {list(df.columns)}")

    df = validate_csv(df)
    print(f"  Valid rows: {len(df)}")

    # Insert into database
    conn = sqlite3.connect(db_path)

    records = []
    for _, row in df.iterrows():
        records.append((
            row["date"],
            _to_db_val(row.get("vix_close")),
            _to_db_val(row.get("us10y_yield")),
            _to_db_val(row.get("us02y_yield")),
            _to_db_val(row.get("yield_curve_slope")),
            _to_db_val(row.get("fed_funds_rate")),
            _to_db_val(row.get("cpi_yoy")),
            _to_db_val(row.get("unemployment_rate")),
        ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO macro_indicators
            (date, vix_close, us10y_yield, us02y_yield,
             yield_curve_slope, fed_funds_rate, cpi_yoy,
             unemployment_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        records,
    )

    conn.commit()

    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM macro_indicators")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT MIN(date), MAX(date) FROM macro_indicators")
    date_range = cursor.fetchone()

    print(f"\nInserted/updated {len(records)} rows")
    print(f"Total rows in macro_indicators: {total}")
    print(f"Date range: {date_range[0]} to {date_range[1]}")

    conn.close()
    print("\nDone!")


def _to_db_val(value):
    """Convert a value to a database-safe format (None for NaN)."""
    if value is None:
        return None
    try:
        if np.isnan(value):
            return None
    except (TypeError, ValueError):
        pass
    return float(value)


def main():
    parser = argparse.ArgumentParser(
        description="Import macroeconomic data from CSV into spy.db"
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        help="Path to the CSV file to import",
    )
    parser.add_argument(
        "--db", default="spy.db", help="Path to SQLite database"
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="Generate a sample CSV template",
    )
    args = parser.parse_args()

    if args.template:
        generate_template()
        return

    if not args.csv_path:
        parser.print_help()
        print("\nError: Provide a CSV path or use --template")
        sys.exit(1)

    import_csv(args.csv_path, args.db)


if __name__ == "__main__":
    main()
