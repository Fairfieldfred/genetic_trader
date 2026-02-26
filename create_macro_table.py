"""
Create the macro_indicators table in spy.db.

Stores daily-frequency macroeconomic data used by macro-aware
genetic trading strategies. Monthly/quarterly indicators are
forward-filled to daily frequency during population.
"""

import sqlite3
import sys
from pathlib import Path


def create_macro_table(db_path: str = "spy.db"):
    """
    Create the macro_indicators table if it doesn't exist.

    Args:
        db_path: Path to the SQLite database file.
    """
    db_file = Path(db_path)
    if not db_file.exists():
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS macro_indicators (
            date TEXT NOT NULL PRIMARY KEY,
            vix_close NUMERIC,
            us10y_yield NUMERIC,
            us02y_yield NUMERIC,
            yield_curve_slope NUMERIC,
            fed_funds_rate NUMERIC,
            cpi_yoy NUMERIC,
            unemployment_rate NUMERIC
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_macro_date
        ON macro_indicators(date)
    """)

    conn.commit()

    # Verify creation
    cursor.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='macro_indicators'"
    )
    if cursor.fetchone():
        print("Table 'macro_indicators' created successfully.")
    else:
        print("Error: Table creation failed.")
        sys.exit(1)

    # Show existing row count
    cursor.execute("SELECT COUNT(*) FROM macro_indicators")
    count = cursor.fetchone()[0]
    print(f"Current row count: {count}")

    conn.close()


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "spy.db"
    create_macro_table(db)
