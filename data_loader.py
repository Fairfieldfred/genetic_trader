"""
Data loader module for genetic trading system.
Loads stock data from spy.db SQLite database into pandas DataFrames
formatted for Backtrader.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional


class DataLoader:
    """Handles loading and formatting stock and macro data for backtesting."""

    def __init__(self, db_path: str = "spy.db"):
        """
        Initialize the data loader.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

    def load_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load stock data for a given symbol.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)

        Returns:
            DataFrame with datetime index and OHLCV columns for Backtrader
        """
        conn = sqlite3.connect(self.db_path)

        # Build query with optional date filtering
        query = """
            SELECT
                date,
                open,
                high,
                low,
                close,
                volume,
                rsi,
                macd,
                signal,
                macdhist
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
            missing_cols = [col for col in required_cols if col not in df.columns]
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

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with data statistics
        """
        conn = sqlite3.connect(self.db_path)

        try:
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
            df = pd.read_sql_query(query, conn, params=[symbol])

            if df.empty or df['record_count'].iloc[0] == 0:
                return None

            return {
                'symbol': symbol,
                'name': df['name'].iloc[0],
                'sector': df['sector'].iloc[0],
                'records': int(df['record_count'].iloc[0]),
                'start_date': df['start_date'].iloc[0],
                'end_date': df['end_date'].iloc[0]
            }

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
