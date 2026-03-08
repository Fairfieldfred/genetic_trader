"""
Populate sector data for all stocks in the database using yfinance.

Adds a 'sector' column to the stocks table and fetches sector info
for each symbol. Handles rate limiting, failures, and supports
resuming interrupted runs.

Requirements:
    pip install yfinance

Usage:
    python populate_sectors.py

    # Resume after interruption (skips already-populated symbols)
    python populate_sectors.py --resume

    # Custom batch size and delay
    python populate_sectors.py --batch-size 50 --delay 1.0

    # Use a different database
    python populate_sectors.py --db /path/to/database.db
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

import yfinance as yf

import config


def ensure_sector_column(conn: sqlite3.Connection) -> None:
    """Add 'sector' column to stocks table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(stocks)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'sector' not in columns:
        cursor.execute("ALTER TABLE stocks ADD COLUMN sector TEXT")
        conn.commit()
        print("Added 'sector' column to stocks table.")
    else:
        print("'sector' column already exists.")


def get_symbols(conn: sqlite3.Connection, resume: bool) -> list[str]:
    """Get list of symbols to process."""
    cursor = conn.cursor()
    if resume:
        cursor.execute(
            "SELECT symbol FROM stocks WHERE sector IS NULL ORDER BY symbol"
        )
    else:
        cursor.execute("SELECT symbol FROM stocks ORDER BY symbol")
    return [row[0] for row in cursor.fetchall()]


def fetch_sector(symbol: str) -> str | None:
    """Fetch sector for a single symbol from yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return info.get('sector')
    except Exception:
        return None


def populate_sectors(
    db_path: str,
    batch_size: int = 20,
    delay: float = 0.5,
    resume: bool = False,
) -> None:
    """Fetch and store sector data for all stocks."""
    conn = sqlite3.connect(db_path)
    ensure_sector_column(conn)

    symbols = get_symbols(conn, resume)
    total = len(symbols)

    if total == 0:
        print("All symbols already have sector data.")
        conn.close()
        return

    print(f"\nFetching sectors for {total} symbols...")
    print(f"Batch size: {batch_size}, Delay: {delay}s between batches\n")

    cursor = conn.cursor()
    success = 0
    failed = 0
    no_sector = 0

    for i, symbol in enumerate(symbols):
        sector = fetch_sector(symbol)

        if sector:
            cursor.execute(
                "UPDATE stocks SET sector = ? WHERE symbol = ?",
                (sector, symbol),
            )
            success += 1
        elif sector is None:
            # Mark as checked but no sector available (ETFs, etc.)
            cursor.execute(
                "UPDATE stocks SET sector = ? WHERE symbol = ?",
                ('N/A', symbol),
            )
            no_sector += 1
        else:
            failed += 1

        # Progress output
        done = i + 1
        if done % 10 == 0 or done == total:
            pct = done / total * 100
            print(
                f"  [{done:>5}/{total}] {pct:5.1f}% | "
                f"OK: {success}  N/A: {no_sector}  Failed: {failed} | "
                f"Current: {symbol} -> {sector or 'N/A'}"
            )

        # Commit and pause every batch_size symbols
        if done % batch_size == 0:
            conn.commit()
            time.sleep(delay)

    # Final commit
    conn.commit()

    # Summary
    print(f"\n{'=' * 50}")
    print("SECTOR POPULATION COMPLETE")
    print(f"{'=' * 50}")
    print(f"  Total processed: {total}")
    print(f"  With sector:     {success}")
    print(f"  No sector (N/A): {no_sector}")
    print(f"  Failed:          {failed}")

    # Show sector distribution
    cursor.execute("""
        SELECT sector, COUNT(*) as cnt
        FROM stocks
        WHERE sector IS NOT NULL AND sector != 'N/A'
        GROUP BY sector
        ORDER BY cnt DESC
    """)
    rows = cursor.fetchall()
    if rows:
        print(f"\nSector Distribution:")
        for sector, count in rows:
            print(f"  {sector:<30} {count:>5}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Populate sector data from yfinance"
    )
    parser.add_argument(
        '--db',
        default=config.DATABASE_PATH,
        help=f"Database path (default: {config.DATABASE_PATH})",
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=20,
        help="Commit and pause every N symbols (default: 20)",
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help="Delay in seconds between batches (default: 0.5)",
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help="Skip symbols that already have sector data",
    )
    args = parser.parse_args()

    db_path = args.db
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Database: {db_path}")
    populate_sectors(
        db_path=db_path,
        batch_size=args.batch_size,
        delay=args.delay,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
