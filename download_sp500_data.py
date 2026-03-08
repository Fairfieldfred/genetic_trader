"""Download S&P 500 daily OHLC data from Yahoo Finance and store in SQLite.

Fetches 10 years of daily price data (OHLCV + adjusted close), stock metadata,
dividend history, and stock split history for all current S&P 500 constituents.
Each stock's GICS sector is stored as a column on every price row.

Usage:
    python download_sp500_data.py
    python download_sp500_data.py --db /path/to/SPY_Data.db
    python download_sp500_data.py --batch-size 50
"""

import argparse
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests
import yfinance as yf


def get_sp500_symbols() -> List[Dict[str, str]]:
    """Fetch current S&P 500 constituents from Wikipedia.

    Returns:
        List of dicts with 'symbol' and 'sector' keys.
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "GeneticTrader/1.0 (stock data download script)"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    tables = pd.read_html(StringIO(resp.text))
    df = tables[0]

    stocks = []
    for _, row in df.iterrows():
        symbol = row["Symbol"].replace(".", "-")  # BRK.B -> BRK-B for yfinance
        sector = row["GICS Sector"]
        stocks.append({"symbol": symbol, "sector": sector})

    print(f"Found {len(stocks)} S&P 500 constituents", flush=True)
    return stocks


def download_batch(
    symbols: List[str], start_date: str, end_date: str
) -> pd.DataFrame:
    """Download OHLCV + Adj Close data for a batch of symbols.

    Args:
        symbols: List of ticker symbols.
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).

    Returns:
        DataFrame with columns: symbol, date, open, high, low, close,
        adj_close, volume.
    """
    data = yf.download(
        symbols,
        start=start_date,
        end=end_date,
        progress=False,
        group_by="ticker",
        threads=True,
        auto_adjust=False,
    )

    if data.empty:
        return pd.DataFrame()

    rows = []
    for symbol in symbols:
        try:
            if len(symbols) == 1:
                ticker_data = data
            else:
                ticker_data = data[symbol]

            if ticker_data.empty:
                continue

            # Handle MultiIndex columns from yfinance
            if isinstance(ticker_data.columns, pd.MultiIndex):
                ticker_data.columns = ticker_data.columns.get_level_values(-1)

            cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
            ticker_df = ticker_data[cols].copy()
            ticker_df = ticker_df.dropna(subset=["Open", "High", "Low", "Close"])
            ticker_df = ticker_df.reset_index()
            ticker_df.columns = [
                "date", "open", "high", "low", "close", "adj_close", "volume",
            ]
            ticker_df["symbol"] = symbol
            rows.append(ticker_df)
        except (KeyError, TypeError):
            print(f"  Warning: No price data for {symbol}, skipping")
            continue

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)


def download_stock_metadata(symbol: str) -> Optional[Dict]:
    """Download metadata for a single stock from yfinance.

    Args:
        symbol: Ticker symbol.

    Returns:
        Dict of metadata fields, or None if download failed.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info or info.get("quoteType") is None:
            return None

        return {
            "symbol": symbol,
            "long_name": info.get("longName"),
            "short_name": info.get("shortName"),
            "exchange": info.get("exchange"),
            "currency": info.get("currency"),
            "country": info.get("country"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "beta": info.get("beta"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "fifty_day_average": info.get("fiftyDayAverage"),
            "two_hundred_day_average": info.get("twoHundredDayAverage"),
            "average_volume": info.get("averageVolume"),
            "dividend_rate": info.get("dividendRate"),
            "dividend_yield": info.get("dividendYield"),
            "payout_ratio": info.get("payoutRatio"),
            "total_revenue": info.get("totalRevenue"),
            "revenue_per_share": info.get("revenuePerShare"),
            "gross_margins": info.get("grossMargins"),
            "ebitda_margins": info.get("ebitdaMargins"),
            "profit_margins": info.get("profitMargins"),
            "total_debt": info.get("totalDebt"),
            "total_cash": info.get("totalCash"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "book_value": info.get("bookValue"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "float_shares": info.get("floatShares"),
            "full_time_employees": info.get("fullTimeEmployees"),
        }
    except Exception as e:
        print(f"  Warning: Could not fetch metadata for {symbol}: {e}")
        return None


def download_dividends_and_splits(
    symbol: str, start_date: str, end_date: str
) -> tuple:
    """Download dividend and stock split history for a single stock.

    Args:
        symbol: Ticker symbol.
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).

    Returns:
        Tuple of (dividends_df, splits_df). Either may be empty.
    """
    try:
        ticker = yf.Ticker(symbol)

        # Dividends
        divs = ticker.dividends
        if not divs.empty:
            divs = divs.loc[start_date:end_date]
            divs_df = divs.reset_index()
            divs_df.columns = ["date", "amount"]
            divs_df["symbol"] = symbol
            divs_df["date"] = pd.to_datetime(divs_df["date"]).dt.strftime("%Y-%m-%d")
        else:
            divs_df = pd.DataFrame()

        # Splits
        splits = ticker.splits
        if not splits.empty:
            splits = splits.loc[start_date:end_date]
            splits = splits[splits != 0]  # Filter out zero-ratio entries
            splits_df = splits.reset_index()
            splits_df.columns = ["date", "ratio"]
            splits_df["symbol"] = symbol
            splits_df["date"] = pd.to_datetime(
                splits_df["date"]
            ).dt.strftime("%Y-%m-%d")
        else:
            splits_df = pd.DataFrame()

        return divs_df, splits_df
    except Exception as e:
        print(f"  Warning: Could not fetch dividends/splits for {symbol}: {e}")
        return pd.DataFrame(), pd.DataFrame()


def create_database(db_path: str) -> None:
    """Create the SQLite database and all tables.

    Args:
        db_path: Path to the SQLite database file.
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                symbol TEXT PRIMARY KEY,
                sector TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_prices (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume INTEGER,
                sector TEXT NOT NULL,
                PRIMARY KEY (symbol, date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_metadata (
                symbol TEXT PRIMARY KEY,
                long_name TEXT,
                short_name TEXT,
                exchange TEXT,
                currency TEXT,
                country TEXT,
                sector TEXT,
                industry TEXT,
                market_cap INTEGER,
                enterprise_value INTEGER,
                trailing_pe REAL,
                forward_pe REAL,
                price_to_book REAL,
                beta REAL,
                fifty_two_week_high REAL,
                fifty_two_week_low REAL,
                fifty_day_average REAL,
                two_hundred_day_average REAL,
                average_volume INTEGER,
                dividend_rate REAL,
                dividend_yield REAL,
                payout_ratio REAL,
                total_revenue INTEGER,
                revenue_per_share REAL,
                gross_margins REAL,
                ebitda_margins REAL,
                profit_margins REAL,
                total_debt INTEGER,
                total_cash INTEGER,
                debt_to_equity REAL,
                current_ratio REAL,
                book_value REAL,
                shares_outstanding INTEGER,
                float_shares INTEGER,
                full_time_employees INTEGER,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dividends (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                PRIMARY KEY (symbol, date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_splits (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                ratio REAL NOT NULL,
                PRIMARY KEY (symbol, date)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol
            ON daily_prices (symbol)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_prices_date
            ON daily_prices (date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_prices_sector
            ON daily_prices (sector)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dividends_symbol
            ON dividends (symbol)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_splits_symbol
            ON stock_splits (symbol)
        """)

        conn.commit()
    finally:
        conn.close()


def insert_stocks(db_path: str, stocks: List[Dict[str, str]]) -> None:
    """Insert stock metadata into the stocks table.

    Args:
        db_path: Path to the SQLite database file.
        stocks: List of dicts with 'symbol' and 'sector' keys.
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR REPLACE INTO stocks (symbol, sector) VALUES (?, ?)",
            [(s["symbol"], s["sector"]) for s in stocks],
        )
        conn.commit()
    finally:
        conn.close()


def insert_price_data(
    db_path: str, df: pd.DataFrame, sector_map: Dict[str, str]
) -> int:
    """Insert price data into the daily_prices table.

    Args:
        db_path: Path to the SQLite database file.
        df: DataFrame with price columns including adj_close.
        sector_map: Mapping of symbol to sector.

    Returns:
        Number of rows inserted.
    """
    if df.empty:
        return 0

    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["sector"] = df["symbol"].map(sector_map)

    columns = [
        "symbol", "date", "open", "high", "low", "close",
        "adj_close", "volume", "sector",
    ]

    records = [
        (
            row["symbol"],
            row["date"],
            row["open"],
            row["high"],
            row["low"],
            row["close"],
            row["adj_close"],
            int(row["volume"]) if pd.notna(row["volume"]) else None,
            row["sector"],
        )
        for _, row in df[columns].iterrows()
    ]

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executemany(
            """INSERT OR IGNORE INTO daily_prices
               (symbol, date, open, high, low, close,
                adj_close, volume, sector)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            records,
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def insert_metadata(db_path: str, metadata: Dict) -> None:
    """Insert a single stock's metadata into stock_metadata table.

    Args:
        db_path: Path to the SQLite database file.
        metadata: Dict of metadata fields.
    """
    conn = sqlite3.connect(db_path)
    try:
        metadata["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        columns = ", ".join(metadata.keys())
        placeholders = ", ".join(["?"] * len(metadata))
        conn.execute(
            f"INSERT OR REPLACE INTO stock_metadata ({columns}) "
            f"VALUES ({placeholders})",
            list(metadata.values()),
        )
        conn.commit()
    finally:
        conn.close()


def insert_dividends(db_path: str, df: pd.DataFrame) -> int:
    """Insert dividend records into the dividends table.

    Args:
        db_path: Path to the SQLite database file.
        df: DataFrame with columns: symbol, date, amount.

    Returns:
        Number of rows inserted.
    """
    if df.empty:
        return 0

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        count = 0
        for _, row in df.iterrows():
            cursor.execute(
                "INSERT OR IGNORE INTO dividends (symbol, date, amount) "
                "VALUES (?, ?, ?)",
                (row["symbol"], row["date"], row["amount"]),
            )
            count += cursor.rowcount
        conn.commit()
        return count
    finally:
        conn.close()


def insert_splits(db_path: str, df: pd.DataFrame) -> int:
    """Insert stock split records into the stock_splits table.

    Args:
        db_path: Path to the SQLite database file.
        df: DataFrame with columns: symbol, date, ratio.

    Returns:
        Number of rows inserted.
    """
    if df.empty:
        return 0

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        count = 0
        for _, row in df.iterrows():
            cursor.execute(
                "INSERT OR IGNORE INTO stock_splits (symbol, date, ratio) "
                "VALUES (?, ?, ?)",
                (row["symbol"], row["date"], row["ratio"]),
            )
            count += cursor.rowcount
        conn.commit()
        return count
    finally:
        conn.close()


def main() -> None:
    """Main entry point for downloading S&P 500 data."""
    parser = argparse.ArgumentParser(
        description="Download S&P 500 daily OHLC data from Yahoo Finance"
    )
    parser.add_argument(
        "--db",
        default=str(Path(__file__).parent / "SPY_Data.db"),
        help="Path to output SQLite database (default: SPY_Data.db)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Number of symbols to download per batch (default: 25)",
    )
    args = parser.parse_args()

    db_path = args.db
    batch_size = args.batch_size

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365 * 10)).strftime("%Y-%m-%d")

    print(f"Date range: {start_date} to {end_date}")
    print(f"Database: {db_path}")
    print()

    # Step 1: Get S&P 500 constituents
    print("Fetching S&P 500 constituent list...")
    stocks = get_sp500_symbols()
    sector_map = {s["symbol"]: s["sector"] for s in stocks}
    symbols = [s["symbol"] for s in stocks]

    # Step 2: Create database
    print("Creating database...")
    create_database(db_path)
    insert_stocks(db_path, stocks)

    # Step 3: Download price data in batches
    total_price_rows = 0
    failed_symbols = []
    num_batches = (len(symbols) + batch_size - 1) // batch_size

    print(f"\n--- Phase 1: Daily Price Data ({num_batches} batches) ---\n")

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        batch_num = i // batch_size + 1

        print(
            f"Batch {batch_num}/{num_batches}: "
            f"{batch[0]}...{batch[-1]} ({len(batch)} symbols)"
        )

        try:
            df = download_batch(batch, start_date, end_date)
            if not df.empty:
                inserted = insert_price_data(db_path, df, sector_map)
                total_price_rows += inserted
                downloaded_symbols = df["symbol"].nunique()
                print(f"  Downloaded {downloaded_symbols} symbols, {inserted} rows")

                missing = set(batch) - set(df["symbol"].unique())
                if missing:
                    failed_symbols.extend(missing)
                    print(f"  Missing: {', '.join(sorted(missing))}")
            else:
                failed_symbols.extend(batch)
                print("  No data returned for batch")
        except Exception as e:
            failed_symbols.extend(batch)
            print(f"  Error: {e}")

        if batch_num < num_batches:
            time.sleep(2)

    # Step 4: Download metadata, dividends, and splits per symbol
    print(f"\n--- Phase 2: Metadata, Dividends & Splits ---\n")

    total_metadata = 0
    total_dividends = 0
    total_splits = 0

    for idx, symbol in enumerate(symbols, 1):
        if idx % 25 == 1 or idx == len(symbols):
            print(f"Processing {idx}/{len(symbols)}: {symbol}")

        # Metadata
        meta = download_stock_metadata(symbol)
        if meta:
            insert_metadata(db_path, meta)
            total_metadata += 1

        # Dividends and splits
        divs_df, splits_df = download_dividends_and_splits(
            symbol, start_date, end_date
        )
        total_dividends += insert_dividends(db_path, divs_df)
        total_splits += insert_splits(db_path, splits_df)

        # Rate limiting — small delay every 5 symbols
        if idx % 5 == 0:
            time.sleep(1)

    # Summary
    print()
    print("=" * 60)
    print("Download complete!")
    print(f"  Price rows inserted:   {total_price_rows:,}")
    print(f"  Metadata records:      {total_metadata}")
    print(f"  Dividend records:      {total_dividends:,}")
    print(f"  Stock split records:   {total_splits}")
    print(f"  Symbols with prices:   {len(symbols) - len(failed_symbols)}")

    if failed_symbols:
        print(
            f"  Failed symbols ({len(failed_symbols)}): "
            f"{', '.join(sorted(failed_symbols))}"
        )

    # Print database stats
    conn = sqlite3.connect(db_path)
    try:
        row_count = conn.execute(
            "SELECT COUNT(*) FROM daily_prices"
        ).fetchone()[0]
        symbol_count = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM daily_prices"
        ).fetchone()[0]
        sector_count = conn.execute(
            "SELECT COUNT(DISTINCT sector) FROM daily_prices"
        ).fetchone()[0]
        date_range = conn.execute(
            "SELECT MIN(date), MAX(date) FROM daily_prices"
        ).fetchone()

        print()
        print("Database summary:")
        print(f"  Total price rows:  {row_count:,}")
        print(f"  Unique symbols:    {symbol_count}")
        print(f"  Unique sectors:    {sector_count}")
        print(f"  Date range:        {date_range[0]} to {date_range[1]}")

        div_count = conn.execute(
            "SELECT COUNT(*) FROM dividends"
        ).fetchone()[0]
        div_symbols = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM dividends"
        ).fetchone()[0]
        split_count = conn.execute(
            "SELECT COUNT(*) FROM stock_splits"
        ).fetchone()[0]
        meta_count = conn.execute(
            "SELECT COUNT(*) FROM stock_metadata"
        ).fetchone()[0]

        print(f"  Dividend records:  {div_count:,} across {div_symbols} symbols")
        print(f"  Split records:     {split_count}")
        print(f"  Metadata records:  {meta_count}")

        # Sector breakdown
        sectors = conn.execute(
            "SELECT sector, COUNT(DISTINCT symbol) "
            "FROM daily_prices GROUP BY sector ORDER BY sector"
        ).fetchall()
        print()
        print("Sector breakdown:")
        for sector, count in sectors:
            print(f"  {sector}: {count} stocks")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
