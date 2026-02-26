"""
Benchmark calculations for comparing strategy performance.
Includes buy-and-hold, market returns, and other baseline strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List


def calculate_buy_and_hold(
    data: pd.DataFrame,
    initial_capital: float = 100000
) -> Dict[str, Any]:
    """
    Calculate buy-and-hold strategy returns.
    Buys at first price, sells at last price.

    Args:
        data: DataFrame with 'close' column and datetime index
        initial_capital: Starting capital

    Returns:
        Dictionary with buy-and-hold metrics
    """
    if data is None or len(data) == 0:
        return {
            'total_return': 0.0,
            'final_value': initial_capital,
            'start_price': 0.0,
            'end_price': 0.0,
        }

    # Get first and last closing prices
    start_price = data['close'].iloc[0]
    end_price = data['close'].iloc[-1]

    # Calculate shares that could be bought
    shares = initial_capital / start_price

    # Calculate final value
    final_value = shares * end_price

    # Calculate return
    total_return = ((final_value - initial_capital) / initial_capital) * 100

    return {
        'total_return': total_return,
        'final_value': final_value,
        'start_price': start_price,
        'end_price': end_price,
        'shares': shares,
        'start_date': data.index[0],
        'end_date': data.index[-1],
    }


def calculate_portfolio_buy_and_hold(
    data_feeds: Dict[str, pd.DataFrame],
    initial_capital: float = 100000,
    allocation_pct: float = 100.0
) -> Dict[str, Any]:
    """
    Calculate buy-and-hold for a portfolio of stocks.
    Divides capital equally among all stocks.

    Args:
        data_feeds: Dictionary mapping symbols to DataFrames
        initial_capital: Starting capital
        allocation_pct: Percentage of capital to invest (0-100), rest stays as cash

    Returns:
        Dictionary with portfolio buy-and-hold metrics
    """
    if not data_feeds:
        return {
            'total_return': 0.0,
            'final_value': initial_capital,
            'per_stock': {},
        }

    # Calculate invested and reserved capital
    invested_capital = initial_capital * (allocation_pct / 100.0)
    reserved_cash = initial_capital - invested_capital

    # Divide invested capital equally among stocks
    capital_per_stock = invested_capital / len(data_feeds)

    # Calculate for each stock
    per_stock_results = {}
    total_invested_value = 0

    for symbol, data in data_feeds.items():
        result = calculate_buy_and_hold(data, capital_per_stock)
        per_stock_results[symbol] = result
        total_invested_value += result['final_value']

    # Total final value includes invested value + reserved cash
    total_final_value = total_invested_value + reserved_cash

    # Portfolio metrics
    total_return = ((total_final_value - initial_capital) / initial_capital) * 100

    return {
        'total_return': total_return,
        'final_value': total_final_value,
        'invested_value': total_invested_value,
        'reserved_cash': reserved_cash,
        'initial_capital': initial_capital,
        'allocation_pct': allocation_pct,
        'num_stocks': len(data_feeds),
        'per_stock': per_stock_results,
    }


def calculate_max_drawdown_buy_and_hold(
    data: pd.DataFrame,
    initial_capital: float = 100000
) -> float:
    """
    Calculate maximum drawdown for buy-and-hold strategy.

    Args:
        data: DataFrame with 'close' column
        initial_capital: Starting capital

    Returns:
        Maximum drawdown percentage (negative value)
    """
    if data is None or len(data) == 0:
        return 0.0

    # Calculate portfolio value over time
    start_price = data['close'].iloc[0]
    shares = initial_capital / start_price
    portfolio_values = data['close'] * shares

    # Calculate running maximum
    running_max = portfolio_values.cummax()

    # Calculate drawdown
    drawdown = (portfolio_values - running_max) / running_max * 100

    # Get max drawdown (most negative)
    max_drawdown = drawdown.min()

    return max_drawdown


def calculate_sharpe_ratio_buy_and_hold(
    data: pd.DataFrame,
    risk_free_rate: float = 0.02
) -> float:
    """
    Calculate Sharpe ratio for buy-and-hold strategy.

    Args:
        data: DataFrame with 'close' column
        risk_free_rate: Annual risk-free rate (default 2%)

    Returns:
        Sharpe ratio
    """
    if data is None or len(data) == 0:
        return 0.0

    # Calculate daily returns
    returns = data['close'].pct_change().dropna()

    if len(returns) == 0 or returns.std() == 0:
        return 0.0

    # Annualize
    mean_return = returns.mean() * 252  # Trading days per year
    std_return = returns.std() * np.sqrt(252)

    # Sharpe ratio
    sharpe = (mean_return - risk_free_rate) / std_return

    return sharpe


def compare_to_benchmark(
    strategy_results: Dict[str, Any],
    benchmark_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compare strategy performance to benchmark.

    Args:
        strategy_results: Strategy performance metrics
        benchmark_results: Benchmark (buy-and-hold) metrics

    Returns:
        Comparison metrics
    """
    strategy_return = strategy_results.get('total_return', 0)
    benchmark_return = benchmark_results.get('total_return', 0)

    outperformance = strategy_return - benchmark_return
    outperformance_pct = (outperformance / abs(benchmark_return) * 100) if benchmark_return != 0 else 0

    return {
        'strategy_return': strategy_return,
        'benchmark_return': benchmark_return,
        'outperformance': outperformance,
        'outperformance_pct': outperformance_pct,
        'beats_benchmark': strategy_return > benchmark_return,
    }


# Example usage
if __name__ == "__main__":
    from data_loader import DataLoader
    import config

    print("Testing Benchmark Calculations\n")
    print("=" * 60)

    # Load data
    loader = DataLoader(config.DATABASE_PATH)
    df = loader.load_stock_data(
        'AAPL',
        start_date='2019-01-01',
        end_date='2019-12-31'
    )

    # Calculate buy-and-hold
    bh_results = calculate_buy_and_hold(df, initial_capital=100000)

    print("Buy-and-Hold Results (AAPL, 2019):")
    print(f"  Initial Capital: ${100000:,.2f}")
    print(f"  Final Value: ${bh_results['final_value']:,.2f}")
    print(f"  Total Return: {bh_results['total_return']:.2f}%")
    print(f"  Start Price: ${bh_results['start_price']:.2f}")
    print(f"  End Price: ${bh_results['end_price']:.2f}")
    print(f"  Shares Held: {bh_results['shares']:.2f}")

    # Calculate additional metrics
    max_dd = calculate_max_drawdown_buy_and_hold(df, 100000)
    sharpe = calculate_sharpe_ratio_buy_and_hold(df)

    print(f"\n  Max Drawdown: {max_dd:.2f}%")
    print(f"  Sharpe Ratio: {sharpe:.4f}")

    # Portfolio example
    print("\n" + "=" * 60)
    print("Portfolio Buy-and-Hold (5 stocks):")

    symbols = ['AAPL', 'MSFT', 'GOOGL', 'JPM', 'WMT']
    data_feeds = {}

    for symbol in symbols:
        try:
            data_feeds[symbol] = loader.load_stock_data(
                symbol,
                start_date='2019-01-01',
                end_date='2019-12-31'
            )
        except Exception as e:
            print(f"  ✗ {symbol}: {e}")

    portfolio_bh = calculate_portfolio_buy_and_hold(data_feeds, 100000)

    print(f"\n  Initial Capital: ${portfolio_bh['initial_capital']:,.2f}")
    print(f"  Final Value: ${portfolio_bh['final_value']:,.2f}")
    print(f"  Total Return: {portfolio_bh['total_return']:.2f}%")
    print(f"  Number of Stocks: {portfolio_bh['num_stocks']}")

    print("\n  Per-Stock Returns:")
    for symbol, result in portfolio_bh['per_stock'].items():
        print(f"    {symbol}: {result['total_return']:>6.2f}%")
