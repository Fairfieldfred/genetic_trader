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

    # Williams %R (14-period)
    df["wr"] = ta.momentum.WilliamsRIndicator(high, low, close, lbp=14).williams_r()

    # CCI (20-period)
    df["cci"] = ta.trend.CCIIndicator(high, low, close, window=20).cci()

    # CMO (14-period) - manual
    delta_cmo = close.diff()
    gain_cmo = delta_cmo.clip(lower=0)
    loss_cmo = (-delta_cmo).clip(lower=0)
    sg = gain_cmo.rolling(14).sum()
    sl = loss_cmo.rolling(14).sum()
    total_cmo = sg + sl
    df["cmo"] = np.where(total_cmo != 0, 100 * (sg - sl) / total_cmo, 0.0)

    # Awesome Oscillator
    midprice = (high + low) / 2.0
    df["ao"] = midprice.rolling(5).mean() - midprice.rolling(34).mean()

    # Stochastic RSI
    stochrsi = ta.momentum.StochRSIIndicator(close, window=14, smooth1=3, smooth2=3)
    df["stochrsi_k"] = stochrsi.stochrsi_k()
    df["stochrsi_d"] = stochrsi.stochrsi_d()

    # Ultimate Oscillator
    df["uo"] = ta.momentum.UltimateOscillator(high, low, close, window1=7, window2=14, window3=28).ultimate_oscillator()

    # ROC (12-period)
    df["roc"] = ta.momentum.ROCIndicator(close, window=12).roc()

    # Parabolic SAR
    psar_obj = ta.trend.PSARIndicator(high, low, close, step=0.02, max_step=0.2)
    df["psar"] = psar_obj.psar()

    # Supertrend (period=10, multiplier=3.0) - manual
    atr_st = ta.volatility.AverageTrueRange(high, low, close, window=10).average_true_range()
    hl2 = (high + low) / 2.0
    upper_band_st = hl2 + 3.0 * atr_st
    lower_band_st = hl2 - 3.0 * atr_st
    n_st = len(close)
    st_vals = np.zeros(n_st)
    st_dir = np.ones(n_st, dtype=float)
    for i_st in range(1, n_st):
        if np.isnan(upper_band_st.iloc[i_st]) or np.isnan(lower_band_st.iloc[i_st]):
            st_dir[i_st] = st_dir[i_st-1]
            st_vals[i_st] = st_vals[i_st-1]
            continue
        prev_ub = upper_band_st.iloc[i_st-1] if not np.isnan(upper_band_st.iloc[i_st-1]) else upper_band_st.iloc[i_st]
        prev_lb = lower_band_st.iloc[i_st-1] if not np.isnan(lower_band_st.iloc[i_st-1]) else lower_band_st.iloc[i_st]
        lb = float(lower_band_st.iloc[i_st]) if float(lower_band_st.iloc[i_st]) > prev_lb or close.iloc[i_st-1] < prev_lb else prev_lb
        ub = float(upper_band_st.iloc[i_st]) if float(upper_band_st.iloc[i_st]) < prev_ub or close.iloc[i_st-1] > prev_ub else prev_ub
        prev_dir_st = int(st_dir[i_st-1])
        if prev_dir_st == 1:
            if float(close.iloc[i_st]) < lb:
                st_dir[i_st] = -1.0
                st_vals[i_st] = ub
            else:
                st_dir[i_st] = 1.0
                st_vals[i_st] = lb
        else:
            if float(close.iloc[i_st]) > ub:
                st_dir[i_st] = 1.0
                st_vals[i_st] = lb
            else:
                st_dir[i_st] = -1.0
                st_vals[i_st] = ub
    df["supertrend"] = st_vals
    df["supertrend_dir"] = st_dir

    # Ichimoku
    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2.0
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2.0
    senkou_a = ((tenkan + kijun) / 2.0).shift(26)
    senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2.0).shift(26)
    df["ichimoku_tenkan"] = tenkan
    df["ichimoku_kijun"] = kijun
    above_cloud = ((close > senkou_a) & (close > senkou_b)).astype(float)
    below_cloud = ((close < senkou_a) & (close < senkou_b)).astype(float)
    df["ichimoku_above_cloud"] = above_cloud - below_cloud

    # Linear Regression slope and R2 (20-period)
    n_lr = len(close)
    lr_slope = np.full(n_lr, np.nan)
    lr_r2 = np.full(n_lr, np.nan)
    x_lr = np.arange(20, dtype=float)
    xm_lr = x_lr.mean()
    xvar_lr = np.sum((x_lr - xm_lr) ** 2)
    for i_lr in range(19, n_lr):
        y_lr = close.values[i_lr-19:i_lr+1]
        ym_lr = y_lr.mean()
        cov_lr = np.sum((x_lr - xm_lr) * (y_lr - ym_lr))
        b_lr = cov_lr / xvar_lr if xvar_lr != 0 else 0.0
        a_lr = ym_lr - b_lr * xm_lr
        yp_lr = a_lr + b_lr * x_lr
        ss_tot = np.sum((y_lr - ym_lr) ** 2)
        ss_res = np.sum((y_lr - yp_lr) ** 2)
        lr_slope[i_lr] = b_lr
        lr_r2[i_lr] = 1.0 - ss_res / ss_tot if ss_tot != 0 else 0.0
    df["linreg_slope"] = lr_slope
    df["linreg_r2"] = lr_r2

    # TRIX (15-period, 9-period signal)
    ema1_tx = close.ewm(span=15, adjust=False).mean()
    ema2_tx = ema1_tx.ewm(span=15, adjust=False).mean()
    ema3_tx = ema2_tx.ewm(span=15, adjust=False).mean()
    trix_line = 100.0 * (ema3_tx - ema3_tx.shift(1)) / ema3_tx.shift(1)
    df["trix"] = trix_line
    df["trix_signal"] = trix_line.ewm(span=9, adjust=False).mean()

    # Chaikin Oscillator (3, 10)
    mfm_ch = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    mfm_ch = mfm_ch.fillna(0.0)
    mfv_ch = mfm_ch * volume
    adl_ch = mfv_ch.cumsum()
    df["chaikin"] = adl_ch.ewm(span=3, adjust=False).mean() - adl_ch.ewm(span=10, adjust=False).mean()

    # Force Index (13-period EMA)
    df["force_index"] = (close.diff() * volume).ewm(span=13, adjust=False).mean()

    # VWAP (rolling 20-bar)
    tp_vw = (high + low + close) / 3.0
    df["vwap"] = (tp_vw * volume).rolling(20).sum() / volume.rolling(20).sum()

    # VWMA (20-period)
    df["vwma_20"] = (close * volume).rolling(20).sum() / volume.rolling(20).sum()

    # Klinger Volume Oscillator (34, 55, 13)
    hlc_kl = (high + low + close) / 3.0
    trend_kl = np.sign(hlc_kl.diff()).fillna(0)
    dm_kl = (high - low).abs()
    vf_kl = (volume * trend_kl * 2.0 * ((dm_kl / dm_kl.replace(0, np.nan)) - 1.0).abs()).fillna(0)
    kvo = vf_kl.ewm(span=34, adjust=False).mean() - vf_kl.ewm(span=55, adjust=False).mean()
    df["klinger"] = kvo
    df["klinger_signal"] = kvo.ewm(span=13, adjust=False).mean()

    # NVI and PVI
    n_vi = len(close)
    nvi_arr = np.zeros(n_vi)
    pvi_arr = np.zeros(n_vi)
    nvi_arr[0] = 1000.0
    pvi_arr[0] = 1000.0
    vol_vi = volume.values
    cls_vi = close.values
    for i_vi in range(1, n_vi):
        ret_vi = (cls_vi[i_vi] - cls_vi[i_vi-1]) / cls_vi[i_vi-1] if cls_vi[i_vi-1] != 0 else 0.0
        if vol_vi[i_vi] < vol_vi[i_vi-1]:
            nvi_arr[i_vi] = nvi_arr[i_vi-1] + ret_vi * nvi_arr[i_vi-1]
        else:
            nvi_arr[i_vi] = nvi_arr[i_vi-1]
        if vol_vi[i_vi] > vol_vi[i_vi-1]:
            pvi_arr[i_vi] = pvi_arr[i_vi-1] + ret_vi * pvi_arr[i_vi-1]
        else:
            pvi_arr[i_vi] = pvi_arr[i_vi-1]
    df["nvi"] = nvi_arr
    df["pvi"] = pvi_arr
    df["nvi_sma"] = pd.Series(nvi_arr, index=df.index).rolling(255).mean().values
    df["pvi_sma"] = pd.Series(pvi_arr, index=df.index).rolling(255).mean().values

    # Donchian Channel (20-period)
    df["donchian_upper"] = high.rolling(20).max()
    df["donchian_lower"] = low.rolling(20).min()
    df["donchian_mid"] = (df["donchian_upper"] + df["donchian_lower"]) / 2.0

    # Keltner Channel (20-period EMA, 10-period ATR, 2.0x)
    kc_mid = close.ewm(span=20, adjust=False).mean()
    kc_atr = ta.volatility.AverageTrueRange(high, low, close, window=10).average_true_range()
    df["keltner_upper"] = kc_mid + 2.0 * kc_atr
    df["keltner_lower"] = kc_mid - 2.0 * kc_atr

    # Bollinger %B and Width
    bb_pctb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    bb_u2 = bb_pctb.bollinger_hband()
    bb_l2 = bb_pctb.bollinger_lband()
    bb_m2 = bb_pctb.bollinger_mavg()
    bw2 = bb_u2 - bb_l2
    df["bb_pct_b"] = np.where(bw2 != 0, (close - bb_l2) / bw2, 0.5)
    df["bb_width"] = np.where(bb_m2 != 0, bw2 / bb_m2 * 100.0, 0.0)

    # Ulcer Index (14-period)
    highest_u = close.rolling(14).max()
    dd_u = 100.0 * (close - highest_u) / highest_u
    df["ulcer"] = np.sqrt((dd_u ** 2).rolling(14).mean())

    # Pivot Points
    prev_h = high.shift(1)
    prev_l = low.shift(1)
    prev_c = close.shift(1)
    pivot_pp = (prev_h + prev_l + prev_c) / 3.0
    df["pivot_r1"] = 2.0 * pivot_pp - prev_l
    df["pivot_s1"] = 2.0 * pivot_pp - prev_h
    df["pivot_r2"] = pivot_pp + (prev_h - prev_l)
    df["pivot_s2"] = pivot_pp - (prev_h - prev_l)

    # Fibonacci Retracement (50-period)
    fib_ph = high.rolling(50).max()
    fib_pl = low.rolling(50).min()
    fib_diff = fib_ph - fib_pl
    df["fib_38"] = fib_pl + 0.382 * fib_diff
    df["fib_62"] = fib_pl + 0.618 * fib_diff

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
            wr REAL,
            cci REAL,
            cmo REAL,
            ao REAL,
            stochrsi_k REAL,
            stochrsi_d REAL,
            uo REAL,
            roc REAL,
            psar REAL,
            supertrend REAL,
            supertrend_dir REAL,
            ichimoku_tenkan REAL,
            ichimoku_kijun REAL,
            ichimoku_above_cloud REAL,
            linreg_slope REAL,
            linreg_r2 REAL,
            trix REAL,
            trix_signal REAL,
            chaikin REAL,
            force_index REAL,
            vwap REAL,
            vwma_20 REAL,
            klinger REAL,
            klinger_signal REAL,
            nvi REAL,
            nvi_sma REAL,
            pvi REAL,
            pvi_sma REAL,
            donchian_upper REAL,
            donchian_lower REAL,
            donchian_mid REAL,
            keltner_upper REAL,
            keltner_lower REAL,
            bb_pct_b REAL,
            bb_width REAL,
            ulcer REAL,
            pivot_r1 REAL,
            pivot_s1 REAL,
            pivot_r2 REAL,
            pivot_s2 REAL,
            fib_38 REAL,
            fib_62 REAL,
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
                    "wr", "cci", "cmo", "ao", "stochrsi_k", "stochrsi_d", "uo", "roc",
                    "psar", "supertrend", "supertrend_dir",
                    "ichimoku_tenkan", "ichimoku_kijun", "ichimoku_above_cloud",
                    "linreg_slope", "linreg_r2", "trix", "trix_signal",
                    "chaikin", "force_index", "vwap", "vwma_20",
                    "klinger", "klinger_signal", "nvi", "nvi_sma", "pvi", "pvi_sma",
                    "donchian_upper", "donchian_lower", "donchian_mid",
                    "keltner_upper", "keltner_lower",
                    "bb_pct_b", "bb_width", "ulcer",
                    "pivot_r1", "pivot_s1", "pivot_r2", "pivot_s2",
                    "fib_38", "fib_62",
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
