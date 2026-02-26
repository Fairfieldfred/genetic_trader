"""
Populate macro_indicators table from FRED API and Yahoo Finance.

Fetches macroeconomic data, forward-fills to daily frequency,
and inserts into spy.db. Safe to re-run (upserts).

Requirements:
    pip install fredapi yfinance

Usage:
    # Set your FRED API key first (free at https://fred.stlouisfed.org/docs/api/api_key.html)
    export FRED_API_KEY="your_key_here"
    python populate_macro_data.py

    # Or pass key directly
    python populate_macro_data.py --fred-key YOUR_KEY

    # Custom date range
    python populate_macro_data.py --start 2012-03-05 --end 2022-03-04
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def fetch_fred_series(fred, series_id: str, start: str, end: str) -> pd.Series:
    """
    Fetch a single FRED series.

    Args:
        fred: fredapi.Fred instance.
        series_id: FRED series identifier.
        start: Start date (YYYY-MM-DD).
        end: End date (YYYY-MM-DD).

    Returns:
        pandas Series indexed by date.
    """
    print(f"  Fetching FRED series: {series_id}...")
    data = fred.get_series(series_id, start, end)
    if data is None or data.empty:
        print(f"    Warning: No data returned for {series_id}")
        return pd.Series(dtype=float)
    print(f"    Got {len(data)} observations")
    return data


def fetch_vix_from_yahoo(start: str, end: str) -> pd.Series:
    """
    Fetch VIX closing prices from Yahoo Finance.

    Args:
        start: Start date (YYYY-MM-DD).
        end: End date (YYYY-MM-DD).

    Returns:
        pandas Series of VIX closing prices indexed by date.
    """
    import yfinance as yf

    print("  Fetching VIX from Yahoo Finance...")
    vix = yf.download("^VIX", start=start, end=end, progress=False)
    if vix.empty:
        print("    Warning: No VIX data returned")
        return pd.Series(dtype=float)

    # Handle multi-level columns from yfinance
    if isinstance(vix.columns, pd.MultiIndex):
        closes = vix["Close"].squeeze()
    else:
        closes = vix["Close"]

    print(f"    Got {len(closes)} daily observations")
    return closes


def compute_cpi_yoy(cpi_monthly: pd.Series) -> pd.Series:
    """
    Compute year-over-year CPI change from monthly CPI levels.

    Args:
        cpi_monthly: Monthly CPI index values.

    Returns:
        Year-over-year percentage change.
    """
    return cpi_monthly.pct_change(periods=12) * 100


def build_daily_macro_df(
    vix: pd.Series,
    us10y: pd.Series,
    us02y: pd.Series,
    fed_funds: pd.Series,
    cpi_monthly: pd.Series,
    unemployment: pd.Series,
    start: str,
    end: str,
) -> pd.DataFrame:
    """
    Merge all macro series into a single daily DataFrame.

    Daily series (VIX, yields, fed funds) are used as-is.
    Monthly series (CPI, unemployment) are forward-filled.

    Args:
        vix: Daily VIX closing prices.
        us10y: Daily 10-Year Treasury yield.
        us02y: Daily 2-Year Treasury yield.
        fed_funds: Daily effective fed funds rate.
        cpi_monthly: Monthly CPI index levels.
        unemployment: Monthly unemployment rate.
        start: Start date for the output range.
        end: End date for the output range.

    Returns:
        DataFrame with daily-frequency macro indicators.
    """
    # Create a daily business-day date range
    date_range = pd.bdate_range(start=start, end=end)

    df = pd.DataFrame(index=date_range)
    df.index.name = "date"

    # Daily series: reindex to fill trading-day gaps
    df["vix_close"] = vix.reindex(date_range).ffill()
    df["us10y_yield"] = us10y.reindex(date_range).ffill()
    df["us02y_yield"] = us02y.reindex(date_range).ffill()
    df["fed_funds_rate"] = fed_funds.reindex(date_range).ffill()

    # Derived: yield curve slope
    df["yield_curve_slope"] = df["us10y_yield"] - df["us02y_yield"]

    # Monthly series: compute YoY CPI, then forward-fill to daily
    cpi_yoy = compute_cpi_yoy(cpi_monthly)
    df["cpi_yoy"] = cpi_yoy.reindex(date_range).ffill()

    df["unemployment_rate"] = unemployment.reindex(date_range).ffill()

    # Drop any rows that are all-NaN (before first data point)
    df = df.dropna(how="all")

    return df


def upsert_macro_data(df: pd.DataFrame, db_path: str):
    """
    Insert or replace macro data into the database.

    Args:
        df: DataFrame with macro indicators (date index).
        db_path: Path to SQLite database.
    """
    conn = sqlite3.connect(db_path)

    # Prepare data for insertion
    records = []
    for date_val, row in df.iterrows():
        date_str = date_val.strftime("%Y-%m-%d")
        records.append((
            date_str,
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
    print(f"\nInserted/updated {len(records)} rows in macro_indicators")

    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM macro_indicators")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT MIN(date), MAX(date) FROM macro_indicators")
    date_range = cursor.fetchone()
    print(f"Total rows: {total}")
    print(f"Date range: {date_range[0]} to {date_range[1]}")

    conn.close()


def _to_db_val(value):
    """Convert a value to a database-safe format (None for NaN)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return float(value)


def main():
    parser = argparse.ArgumentParser(
        description="Populate macro_indicators table from FRED and Yahoo Finance"
    )
    parser.add_argument(
        "--fred-key",
        default=os.environ.get("FRED_API_KEY"),
        help="FRED API key (or set FRED_API_KEY env var)",
    )
    parser.add_argument(
        "--db", default="spy.db", help="Path to SQLite database"
    )
    parser.add_argument(
        "--start", default="2011-01-01",
        help="Fetch start date (earlier than stock data to allow CPI YoY calc)",
    )
    parser.add_argument(
        "--end", default="2022-12-31",
        help="Fetch end date",
    )
    parser.add_argument(
        "--output-start", default="2012-03-05",
        help="Start date for output (aligned with stock data)",
    )
    parser.add_argument(
        "--output-end", default="2022-03-04",
        help="End date for output (aligned with stock data)",
    )
    args = parser.parse_args()

    if not args.fred_key:
        print("Error: FRED API key required.")
        print("  Set FRED_API_KEY environment variable or use --fred-key")
        print("  Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html")
        sys.exit(1)

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found: {args.db}")
        sys.exit(1)

    # Ensure table exists
    from create_macro_table import create_macro_table
    create_macro_table(args.db)

    # Import FRED client
    from fredapi import Fred
    fred = Fred(api_key=args.fred_key)

    print("\nFetching macroeconomic data...")
    print("=" * 50)

    # Fetch all series
    us10y = fetch_fred_series(fred, "DGS10", args.start, args.end)
    us02y = fetch_fred_series(fred, "DGS2", args.start, args.end)
    fed_funds = fetch_fred_series(fred, "FEDFUNDS", args.start, args.end)
    cpi = fetch_fred_series(fred, "CPIAUCSL", args.start, args.end)
    unemployment = fetch_fred_series(fred, "UNRATE", args.start, args.end)
    vix = fetch_vix_from_yahoo(args.start, args.end)

    print("\nBuilding daily macro DataFrame...")
    df = build_daily_macro_df(
        vix=vix,
        us10y=us10y,
        us02y=us02y,
        fed_funds=fed_funds,
        cpi_monthly=cpi,
        unemployment=unemployment,
        start=args.output_start,
        end=args.output_end,
    )

    print(f"DataFrame shape: {df.shape}")
    print(f"Date range: {df.index.min()} to {df.index.max()}")
    print(f"\nNull counts:")
    print(df.isnull().sum())
    print(f"\nSample rows:")
    print(df.head(3))
    print("...")
    print(df.tail(3))

    # Write to database
    print("\nWriting to database...")
    upsert_macro_data(df, args.db)

    print("\nDone!")


if __name__ == "__main__":
    main()
