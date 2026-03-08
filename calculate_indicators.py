"""Calculate technical indicators for all stocks in SPY_Data.db.

Computes RSI, MACD, ADX, NATR, MFI, Bollinger Bands, and Stochastic
Oscillator from OHLCV data, adds them as columns to a new
`daily_indicators` table compatible with the Genetic Trader system.

Also adds SMA/EMA moving averages and ATR for general use.

Usage:
    python calculate_indicators.py
    python calculate_indicators.py --db /path/to/SPY_Data.db
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import ta


def load_symbol_data(conn: sqlite3.Connection, symbol: str) -> pd.DataFrame:
    """Load OHLCV data for a single symbol from daily_prices.

    Args:
        conn: Active SQLite connection.
        symbol: Ticker symbol.

    Returns:
        DataFrame with datetime index and OHLCV + sector columns.
    """
    df = pd.read_sql_query(
        "SELECT date, open, high, low, close, adj_close, volume, sector "
        "FROM daily_prices WHERE symbol = ? ORDER BY date ASC",
        conn,
        params=[symbol],
    )
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    return df


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators from OHLCV data.

    Computes the 12 indicators used by the Genetic Trader strategy,
    plus SMA/EMA moving averages and ATR for general use.

    Args:
        df: DataFrame with OHLCV columns and datetime index.

    Returns:
        DataFrame with all original columns plus indicator columns.
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"].astype(float)

    # --- Momentum Indicators ---

    # RSI (14-period)
    df["rsi"] = ta.momentum.RSIIndicator(close, window=14).rsi()

    # MFI (14-period) — Money Flow Index (volume-weighted RSI)
    df["mfi"] = ta.volume.MFIIndicator(high, low, close, volume, window=14).money_flow_index()

    # Stochastic Oscillator (14, 3, 3)
    stoch = ta.momentum.StochasticOscillator(
        high, low, close, window=14, smooth_window=3
    )
    df["slowk"] = stoch.stoch()
    df["slowd"] = stoch.stoch_signal()

    # --- Trend Indicators ---

    # MACD (12, 26, 9)
    macd_obj = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd_obj.macd()
    df["signal"] = macd_obj.macd_signal()
    df["macdhist"] = macd_obj.macd_diff()

    # ADX (14-period) — Average Directional Index
    adx_obj = ta.trend.ADXIndicator(high, low, close, window=14)
    df["adx"] = adx_obj.adx()

    # SMA (20 and 50 period)
    df["sma_20"] = ta.trend.SMAIndicator(close, window=20).sma_indicator()
    df["sma_50"] = ta.trend.SMAIndicator(close, window=50).sma_indicator()

    # EMA (20 and 50 period)
    df["ema_20"] = ta.trend.EMAIndicator(close, window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(close, window=50).ema_indicator()

    # --- Volatility Indicators ---

    # Bollinger Bands (20-period, 2 std dev)
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    df["bb_top"] = bb.bollinger_hband()
    df["bb_mid"] = bb.bollinger_mavg()
    df["bb_bot"] = bb.bollinger_lband()

    # ATR (14-period) — Average True Range
    atr_obj = ta.volatility.AverageTrueRange(high, low, close, window=14)
    df["atr_14"] = atr_obj.average_true_range()

    # NATR — Normalized ATR (ATR as percentage of close)
    df["natr"] = (df["atr_14"] / close) * 100

    # --- Volume Indicators ---

    # OBV — On-Balance Volume
    df["obv"] = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()

    return df


def get_symbols(conn: sqlite3.Connection) -> List[str]:
    """Get all unique symbols from daily_prices.

    Args:
        conn: Active SQLite connection.

    Returns:
        Sorted list of symbol strings.
    """
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM daily_prices ORDER BY symbol"
    ).fetchall()
    return [r[0] for r in rows]


def create_indicators_table(conn: sqlite3.Connection) -> None:
    """Create the daily_indicators table with all columns.

    Args:
        conn: Active SQLite connection.
    """
    conn.execute("DROP TABLE IF EXISTS daily_indicators")
    conn.execute("""
        CREATE TABLE daily_indicators (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume INTEGER,
            sector TEXT,
            rsi REAL,
            mfi REAL,
            slowk REAL,
            slowd REAL,
            macd REAL,
            signal REAL,
            macdhist REAL,
            adx REAL,
            sma_20 REAL,
            sma_50 REAL,
            ema_20 REAL,
            ema_50 REAL,
            bb_top REAL,
            bb_mid REAL,
            bb_bot REAL,
            atr_14 REAL,
            natr REAL,
            obv REAL,
            PRIMARY KEY (symbol, date)
        )
    """)
    conn.execute("""
        CREATE INDEX idx_di_symbol ON daily_indicators (symbol)
    """)
    conn.execute("""
        CREATE INDEX idx_di_date ON daily_indicators (date)
    """)
    conn.execute("""
        CREATE INDEX idx_di_sector ON daily_indicators (sector)
    """)
    conn.commit()


def main() -> None:
    """Main entry point for calculating technical indicators."""
    parser = argparse.ArgumentParser(
        description="Calculate technical indicators for SPY_Data.db"
    )
    parser.add_argument(
        "--db",
        default=str(Path(__file__).parent / "SPY_Data.db"),
        help="Path to SQLite database (default: SPY_Data.db)",
    )
    args = parser.parse_args()

    db_path = args.db
    if not Path(db_path).exists():
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    try:
        symbols = get_symbols(conn)
        print(f"Database: {db_path}")
        print(f"Symbols to process: {len(symbols)}")
        print()

        # Create fresh daily_indicators table
        print("Creating daily_indicators table...")
        create_indicators_table(conn)

        processed = 0
        failed = []
        total_rows = 0
        start_time = time.time()

        for idx, symbol in enumerate(symbols, 1):
            try:
                df = load_symbol_data(conn, symbol)

                if len(df) < 50:
                    # Not enough data for meaningful indicators
                    failed.append((symbol, "insufficient data"))
                    continue

                df = calculate_indicators(df)

                # Reset index so date becomes a column for insertion
                df = df.reset_index()
                df["date"] = df["date"].dt.strftime("%Y-%m-%d")
                df["symbol"] = symbol

                columns = [
                    "symbol", "date", "open", "high", "low", "close",
                    "adj_close", "volume", "sector",
                    "rsi", "mfi", "slowk", "slowd",
                    "macd", "signal", "macdhist", "adx",
                    "sma_20", "sma_50", "ema_20", "ema_50",
                    "bb_top", "bb_mid", "bb_bot",
                    "atr_14", "natr", "obv",
                ]

                # Replace NaN/inf with None for SQLite
                insert_df = df[columns].copy()
                insert_df = insert_df.replace([np.inf, -np.inf], np.nan)

                records = [
                    tuple(
                        None if pd.isna(v) else v
                        for v in row
                    )
                    for row in insert_df.itertuples(index=False, name=None)
                ]

                placeholders = ", ".join(["?"] * len(columns))
                conn.executemany(
                    f"INSERT INTO daily_indicators ({', '.join(columns)}) "
                    f"VALUES ({placeholders})",
                    records,
                )

                processed += 1
                total_rows += len(records)

                if idx % 25 == 0 or idx == len(symbols):
                    elapsed = time.time() - start_time
                    rate = idx / elapsed if elapsed > 0 else 0
                    eta = (len(symbols) - idx) / rate if rate > 0 else 0
                    print(
                        f"  [{idx}/{len(symbols)}] {symbol} — "
                        f"{len(records)} rows — "
                        f"{rate:.1f} symbols/sec — "
                        f"ETA {eta:.0f}s",
                        flush=True,
                    )

                # Commit every 50 symbols
                if idx % 50 == 0:
                    conn.commit()

            except Exception as e:
                failed.append((symbol, str(e)))
                continue

        # Final commit
        conn.commit()

        elapsed = time.time() - start_time

        # Summary
        print()
        print("=" * 60)
        print("Technical indicator calculation complete!")
        print(f"  Time elapsed:      {elapsed:.1f}s")
        print(f"  Symbols processed: {processed}")
        print(f"  Total rows:        {total_rows:,}")
        print(f"  Failed:            {len(failed)}")

        if failed:
            print()
            print("Failed symbols:")
            for sym, reason in failed:
                print(f"  {sym}: {reason}")

        # Verify
        row_count = conn.execute(
            "SELECT COUNT(*) FROM daily_indicators"
        ).fetchone()[0]
        sym_count = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM daily_indicators"
        ).fetchone()[0]
        col_info = conn.execute(
            "PRAGMA table_info(daily_indicators)"
        ).fetchall()

        # Sample indicator coverage
        sample = conn.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN rsi IS NOT NULL THEN 1 ELSE 0 END) as rsi_count, "
            "SUM(CASE WHEN macd IS NOT NULL THEN 1 ELSE 0 END) as macd_count, "
            "SUM(CASE WHEN bb_top IS NOT NULL THEN 1 ELSE 0 END) as bb_count, "
            "SUM(CASE WHEN adx IS NOT NULL THEN 1 ELSE 0 END) as adx_count "
            "FROM daily_indicators"
        ).fetchone()

        print()
        print("Database verification:")
        print(f"  daily_indicators rows:    {row_count:,}")
        print(f"  Unique symbols:           {sym_count}")
        print(f"  Columns:                  {len(col_info)}")
        print()
        print("Indicator coverage:")
        print(f"  RSI populated:     {sample[1]:,}/{sample[0]:,} "
              f"({sample[1]/sample[0]*100:.1f}%)")
        print(f"  MACD populated:    {sample[2]:,}/{sample[0]:,} "
              f"({sample[2]/sample[0]*100:.1f}%)")
        print(f"  Bollinger populated: {sample[3]:,}/{sample[0]:,} "
              f"({sample[3]/sample[0]*100:.1f}%)")
        print(f"  ADX populated:     {sample[4]:,}/{sample[0]:,} "
              f"({sample[4]/sample[0]*100:.1f}%)")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
