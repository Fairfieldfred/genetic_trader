"""
Data loader module for genetic trading system.
Loads stock data from SQLite databases into pandas DataFrames
formatted for Backtrader. Supports both spy.db and alpaca_Big_polygon.db schemas.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, Set


class DataLoader:
    """Handles loading and formatting stock and macro data for backtesting."""

    # Technical indicator columns to load when available
    TI_COLUMNS = [
        'rsi', 'adx', 'natr', 'mfi', 'macd', 'signal', 'macdhist',
        # Ensemble signal columns
        'bb_top', 'bb_mid', 'bb_bot', 'slowk', 'slowd',
    ]

    def __init__(self, db_path: str = "spy.db"):
        """
        Initialize the data loader.

        Auto-detects the database schema to support both spy.db
        and alpaca_Big_polygon.db layouts.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        self._available_columns: Optional[Set[str]] = None
        self._has_stocks_table: Optional[bool] = None

    def _get_available_columns(self) -> Set[str]:
        """Cache and return the set of columns in daily_indicators."""
        if self._available_columns is None:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(daily_indicators)")
                self._available_columns = {
                    row[1] for row in cursor.fetchall()
                }
            finally:
                conn.close()
        return self._available_columns

    def _has_stocks(self) -> bool:
        """Check if a separate 'stocks' table exists (alpaca DB layout)."""
        if self._has_stocks_table is None:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='stocks'"
                )
                self._has_stocks_table = cursor.fetchone() is not None
            finally:
                conn.close()
        return self._has_stocks_table

    def load_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load stock data for a given symbol.

        Automatically includes available technical indicator columns
        (rsi, adx, natr, mfi, macd, signal, macdhist) when present.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)

        Returns:
            DataFrame with datetime index and OHLCV + indicator columns
        """
        available = self._get_available_columns()

        # Base OHLCV columns (always required)
        select_cols = ['date', 'open', 'high', 'low', 'close', 'volume']

        # Add available technical indicator columns
        for col in self.TI_COLUMNS:
            if col in available:
                select_cols.append(col)

        cols_str = ', '.join(select_cols)

        conn = sqlite3.connect(self.db_path)

        query = f"""
            SELECT {cols_str}
            FROM daily_indicators
            WHERE symbol = ?
        """

        params = [symbol]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date ASC"

        try:
            df = pd.read_sql_query(query, conn, params=params)

            if df.empty:
                raise ValueError(f"No data found for symbol: {symbol}")

            # Convert date to datetime and set as index
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)

            # Ensure all required columns are present
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [
                col for col in required_cols if col not in df.columns
            ]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            # Drop rows with NaN in critical columns
            df = df.dropna(subset=['open', 'high', 'low', 'close'])

            return df

        finally:
            conn.close()

    def get_available_symbols(self, limit: int = 100) -> list:
        """
        Get list of available stock symbols in the database.

        Args:
            limit: Maximum number of symbols to return

        Returns:
            List of stock ticker symbols
        """
        conn = sqlite3.connect(self.db_path)

        try:
            query = """
                SELECT DISTINCT symbol
                FROM daily_indicators
                ORDER BY symbol
                LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=[limit])
            return df['symbol'].tolist()

        finally:
            conn.close()

    def load_macro_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Load macroeconomic indicator data.

        Returns None if the macro_indicators table does not exist
        or contains no data in the requested range.

        Args:
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)

        Returns:
            DataFrame with datetime index and macro columns, or None.
        """
        conn = sqlite3.connect(self.db_path)

        try:
            # Check if table exists
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='macro_indicators'"
            )
            if not cursor.fetchone():
                return None

            query = """
                SELECT
                    date,
                    vix_close,
                    us10y_yield,
                    us02y_yield,
                    yield_curve_slope,
                    fed_funds_rate,
                    cpi_yoy,
                    unemployment_rate
                FROM macro_indicators
                WHERE 1=1
            """
            params = []

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            query += " ORDER BY date ASC"

            df = pd.read_sql_query(query, conn, params=params)

            if df.empty:
                return None

            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)

            return df

        finally:
            conn.close()

    @staticmethod
    def merge_macro_into_stock(
        stock_df: pd.DataFrame,
        macro_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Left-join macro data onto a stock DataFrame by date index.

        Macro values are forward-filled to cover any date gaps.

        Args:
            stock_df: Stock OHLCV DataFrame with datetime index.
            macro_df: Macro indicator DataFrame with datetime index.

        Returns:
            Stock DataFrame with macro columns appended.
        """
        merged = stock_df.join(macro_df, how='left')
        # Forward-fill macro columns only (not stock data)
        macro_cols = macro_df.columns.tolist()
        merged[macro_cols] = merged[macro_cols].ffill()
        return merged

    def get_data_info(self, symbol: str) -> dict:
        """
        Get information about available data for a symbol.

        Adapts to database schema — uses 'stocks' table for name/sector
        when daily_indicators lacks those columns (alpaca DB layout).

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with data statistics, or None if symbol not found
        """
        available = self._get_available_columns()
        has_name_sector = 'name' in available and 'sector' in available

        conn = sqlite3.connect(self.db_path)

        try:
            if has_name_sector:
                query = """
                    SELECT
                        COUNT(*) as record_count,
                        MIN(date) as start_date,
                        MAX(date) as end_date,
                        name,
                        sector
                    FROM daily_indicators
                    WHERE symbol = ?
                """
            elif self._has_stocks():
                query = """
                    SELECT
                        COUNT(*) as record_count,
                        MIN(di.date) as start_date,
                        MAX(di.date) as end_date,
                        s.name,
                        s.exchange as sector
                    FROM daily_indicators di
                    JOIN stocks s ON di.symbol = s.symbol
                    WHERE di.symbol = ?
                """
            else:
                query = """
                    SELECT
                        COUNT(*) as record_count,
                        MIN(date) as start_date,
                        MAX(date) as end_date
                    FROM daily_indicators
                    WHERE symbol = ?
                """

            df = pd.read_sql_query(query, conn, params=[symbol])

            if df.empty or df['record_count'].iloc[0] == 0:
                return None

            result = {
                'symbol': symbol,
                'records': int(df['record_count'].iloc[0]),
                'start_date': df['start_date'].iloc[0],
                'end_date': df['end_date'].iloc[0]
            }

            if 'name' in df.columns:
                result['name'] = df['name'].iloc[0]
                result['sector'] = df['sector'].iloc[0]

            return result

        finally:
            conn.close()


# Example usage and testing
if __name__ == "__main__":
    loader = DataLoader("spy.db")

    # Show available symbols
    print("Available symbols (first 10):")
    symbols = loader.get_available_symbols(10)
    print(symbols)

    # Get info for first symbol
    if symbols:
        symbol = symbols[0]
        info = loader.get_data_info(symbol)
        print(f"\nData info for {symbol}:")
        print(info)

        # Load data
        print(f"\nLoading data for {symbol}...")
        df = loader.load_stock_data(symbol)
        print(f"Loaded {len(df)} records")
        print(f"\nFirst few rows:")
        print(df.head())
        print(f"\nColumns: {df.columns.tolist()}")
