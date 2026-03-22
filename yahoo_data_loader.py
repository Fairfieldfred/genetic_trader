"""
Yahoo Finance data loader for genetic trading system.

Produces DataFrames in the same format as DataLoader (SQLite)
so they are interchangeable with both Backtrader and Tradix engines.

Downloads OHLCV data via yfinance, computes technical indicators
using the `ta` library, and caches results as Parquet files to
avoid Yahoo Finance rate limits during evolution runs.

Macro data: VIX and 10Y Treasury yield come from Yahoo Finance (free).
Fed funds, CPI, unemployment, 2Y yield come from FRED (requires
FRED_API_KEY env var — free at https://fred.stlouisfed.org/docs/api/api_key.html).
"""

import os
import hashlib
import time
import numpy as np
import pandas as pd
import yfinance as yf
from pathlib import Path
from typing import Optional, List


class YahooDataLoader:
    """Loads OHLCV + technical indicator data from Yahoo Finance."""

    def __init__(self, cache_dir: str = ".yahoo_cache", cache_max_age_hours: int = 24):
        """
        Initialize Yahoo Finance data loader.

        Args:
            cache_dir: Directory for Parquet cache files.
            cache_max_age_hours: Re-download if cache is older than this.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_max_age_seconds = cache_max_age_hours * 3600
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, symbol: str, start_date: str, end_date: str) -> Path:
        """Generate a unique cache file path for this query."""
        key = f"{symbol}_{start_date}_{end_date}"
        hashed = hashlib.md5(key.encode()).hexdigest()[:12]
        return self.cache_dir / f"{symbol}_{hashed}.parquet"

    def _is_cache_valid(self, path: Path) -> bool:
        """Check if a cache file exists and is fresh enough."""
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age < self.cache_max_age_seconds

    def load_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Download stock data from Yahoo Finance with technical indicators.

        Returns a DataFrame with the same schema as DataLoader.load_stock_data():
        datetime index, columns: open, high, low, close, volume, plus
        TI columns (rsi, adx, natr, mfi, macd, signal, macdhist,
        bb_top, bb_mid, bb_bot, slowk, slowd).

        Args:
            symbol: Ticker symbol (e.g. 'AAPL', 'MSFT').
            start_date: Start date string 'YYYY-MM-DD'.
            end_date: End date string 'YYYY-MM-DD'.

        Returns:
            pandas DataFrame indexed by date.

        Raises:
            ValueError: If no data is returned for the symbol.
        """
        cache_path = self._cache_path(symbol, start_date or "", end_date or "")

        if self._is_cache_valid(cache_path):
            df = pd.read_parquet(cache_path)
            return df

        # Download from Yahoo Finance
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, auto_adjust=True)

        if df.empty:
            raise ValueError(f"No data returned from Yahoo Finance for {symbol}")

        # Normalize column names to lowercase
        df.columns = [c.lower() for c in df.columns]

        # Keep only OHLCV columns
        keep_cols = ['open', 'high', 'low', 'close', 'volume']
        df = df[[c for c in keep_cols if c in df.columns]]

        # Remove timezone info from index if present
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        # Drop rows with NaN in OHLC
        df = df.dropna(subset=['open', 'high', 'low', 'close'])

        # Compute technical indicators to match SQLite schema
        df = self._add_technical_indicators(df)

        # Cache to Parquet
        df.to_parquet(cache_path)

        return df

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute technical indicator columns to match the SQLite
        daily_indicators schema.

        Args:
            df: DataFrame with OHLCV columns.

        Returns:
            DataFrame with added TI columns.
        """
        import ta

        if len(df) < 30:
            return df

        high = df['high']
        low = df['low']
        close = df['close']
        volume = df['volume']

        # RSI (14-period)
        df['rsi'] = ta.momentum.RSIIndicator(close, window=14).rsi()

        # ADX (14-period)
        adx_ind = ta.trend.ADXIndicator(high, low, close, window=14)
        df['adx'] = adx_ind.adx()

        # NATR (normalized ATR as percentage of close)
        atr_ind = ta.volatility.AverageTrueRange(high, low, close, window=14)
        df['natr'] = (atr_ind.average_true_range() / close) * 100

        # MFI (14-period Money Flow Index)
        df['mfi'] = ta.volume.MFIIndicator(
            high, low, close, volume, window=14
        ).money_flow_index()

        # MACD (12, 26, 9)
        macd_ind = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
        df['macd'] = macd_ind.macd()
        df['signal'] = macd_ind.macd_signal()
        df['macdhist'] = macd_ind.macd_diff()

        # Bollinger Bands (20-period, 2 std)
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        df['bb_top'] = bb.bollinger_hband()
        df['bb_mid'] = bb.bollinger_mavg()
        df['bb_bot'] = bb.bollinger_lband()

        # Stochastic Oscillator (14-period K, 3-period D)
        stoch = ta.momentum.StochasticOscillator(
            high, low, close, window=14, smooth_window=3
        )
        df['slowk'] = stoch.stoch()
        df['slowd'] = stoch.stoch_signal()

        return df

    def load_macro_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch macroeconomic data from Yahoo Finance and FRED.

        Yahoo Finance (no API key): VIX (^VIX), 10Y Treasury (^TNX).
        FRED (requires FRED_API_KEY env var): 2Y Treasury (DGS2),
        fed funds rate (FEDFUNDS), CPI YoY (CPIAUCSL),
        unemployment rate (UNRATE).

        Returns the same schema as DataLoader.load_macro_data():
        vix_close, us10y_yield, us02y_yield, yield_curve_slope,
        fed_funds_rate, cpi_yoy, unemployment_rate.

        Returns None only if no data at all could be fetched.
        """
        cache_key = f"macro_{start_date}_{end_date}"
        cache_path = self.cache_dir / f"macro_{hashlib.md5(cache_key.encode()).hexdigest()[:12]}.parquet"

        if self._is_cache_valid(cache_path):
            df = pd.read_parquet(cache_path)
            if not df.empty:
                return df

        # Fetch earlier data for CPI YoY calculation (needs 12-month lookback)
        fetch_start = start_date
        if start_date:
            from datetime import datetime, timedelta
            dt = datetime.strptime(start_date, '%Y-%m-%d')
            fetch_start_dt = dt - timedelta(days=400)  # ~13 months earlier
            fetch_start = fetch_start_dt.strftime('%Y-%m-%d')

        # --- Yahoo Finance data (free, no API key) ---
        vix = self._fetch_yahoo_series('^VIX', fetch_start, end_date, 'VIX')
        us10y = self._fetch_yahoo_series('^TNX', fetch_start, end_date, '10Y Treasury')

        # --- FRED data (requires API key) ---
        us02y = None
        fed_funds = None
        cpi_monthly = None
        unemployment = None

        fred_key = self._get_fred_api_key()
        if fred_key:
            try:
                from fredapi import Fred
                fred = Fred(api_key=fred_key)
                us02y = self._fetch_fred_series(fred, 'DGS2', fetch_start, end_date, '2Y Treasury')
                fed_funds = self._fetch_fred_series(fred, 'FEDFUNDS', fetch_start, end_date, 'Fed Funds')
                cpi_monthly = self._fetch_fred_series(fred, 'CPIAUCSL', fetch_start, end_date, 'CPI')
                unemployment = self._fetch_fred_series(fred, 'UNRATE', fetch_start, end_date, 'Unemployment')
            except ImportError:
                print("    fredapi not installed — FRED indicators unavailable")
            except Exception as e:
                print(f"    FRED API error: {e}")
        else:
            print("    FRED_API_KEY not set — only VIX and 10Y yield available")
            print("    Set FRED_API_KEY for full macro data (free at fred.stlouisfed.org)")

        # Check if we got anything at all
        if vix is None and us10y is None:
            return None

        # Build daily DataFrame
        date_range = pd.bdate_range(
            start=start_date or '2000-01-01',
            end=end_date or '2099-12-31',
        )
        df = pd.DataFrame(index=date_range)
        df.index.name = 'date'

        # Daily series: reindex and forward-fill gaps
        if vix is not None:
            df['vix_close'] = vix.reindex(date_range).ffill()
        else:
            df['vix_close'] = np.nan

        if us10y is not None:
            df['us10y_yield'] = us10y.reindex(date_range).ffill()
        else:
            df['us10y_yield'] = np.nan

        if us02y is not None:
            df['us02y_yield'] = us02y.reindex(date_range).ffill()
        else:
            df['us02y_yield'] = np.nan

        # Derived: yield curve slope
        df['yield_curve_slope'] = df['us10y_yield'] - df['us02y_yield']

        if fed_funds is not None:
            df['fed_funds_rate'] = fed_funds.reindex(date_range).ffill()
        else:
            df['fed_funds_rate'] = np.nan

        # CPI: compute YoY from monthly levels, then forward-fill
        if cpi_monthly is not None:
            cpi_yoy = cpi_monthly.pct_change(periods=12) * 100
            df['cpi_yoy'] = cpi_yoy.reindex(date_range).ffill()
        else:
            df['cpi_yoy'] = np.nan

        if unemployment is not None:
            df['unemployment_rate'] = unemployment.reindex(date_range).ffill()
        else:
            df['unemployment_rate'] = np.nan

        # Drop rows that are entirely NaN
        df = df.dropna(how='all')

        if df.empty:
            return None

        # Cache result
        df.to_parquet(cache_path)

        return df

    @staticmethod
    def _get_fred_api_key() -> Optional[str]:
        """
        Look for FRED API key in multiple locations (first match wins):
        1. FRED_API_KEY environment variable
        2. config.FRED_API_KEY in config.py
        3. .env file in project directory
        """
        # 1. Environment variable
        key = os.environ.get('FRED_API_KEY')
        if key:
            return key

        # 2. config.py
        try:
            import config as cfg
            key = getattr(cfg, 'FRED_API_KEY', None)
            if key:
                return key
        except Exception:
            pass

        # 3. .env file (simple KEY=VALUE format)
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                if k.strip() == 'FRED_API_KEY':
                    v = v.strip().strip('"').strip("'")
                    if v:
                        return v

        return None

    def _fetch_yahoo_series(
        self, ticker: str, start: str, end: str, label: str
    ) -> Optional[pd.Series]:
        """Fetch closing price series from Yahoo Finance."""
        try:
            data = yf.download(ticker, start=start, end=end, progress=False)
            if data.empty:
                print(f"    {label}: no data returned")
                return None

            # Handle multi-level columns from newer yfinance
            if isinstance(data.columns, pd.MultiIndex):
                closes = data['Close'].squeeze()
            else:
                closes = data['Close']

            # Remove timezone if present
            if hasattr(closes.index, 'tz') and closes.index.tz is not None:
                closes.index = closes.index.tz_localize(None)

            print(f"    {label}: {len(closes)} daily observations")
            return closes
        except Exception as e:
            print(f"    {label}: fetch failed — {e}")
            return None

    def _fetch_fred_series(
        self, fred, series_id: str, start: str, end: str, label: str
    ) -> Optional[pd.Series]:
        """Fetch a single FRED series."""
        try:
            data = fred.get_series(series_id, start, end)
            if data is None or data.empty:
                print(f"    {label}: no data returned from FRED")
                return None
            print(f"    {label}: {len(data)} observations from FRED")
            return data
        except Exception as e:
            print(f"    {label}: FRED fetch failed — {e}")
            return None

    @staticmethod
    def merge_macro_into_stock(
        stock_df: pd.DataFrame,
        macro_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Left-join macro data onto a stock DataFrame by date index.
        Same interface as DataLoader.merge_macro_into_stock().
        """
        merged = stock_df.join(macro_df, how='left')
        macro_cols = macro_df.columns.tolist()
        merged[macro_cols] = merged[macro_cols].ffill()
        return merged

    def get_available_symbols(self) -> list:
        """Not applicable for Yahoo Finance."""
        return []
