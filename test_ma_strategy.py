"""
Test script for Moving Average strategy.
Verifies that the MA crossover strategy works correctly.
"""

import config
from data_loader import DataLoader
from genetic_trader import GeneticTrader
from bt_strategy import create_strategy_from_trader
import backtrader as bt

print("Testing MA Crossover Strategy")
print("=" * 60)

# Test configuration
TEST_SYMBOL = 'AAPL'
TEST_START = '2019-01-01'
TEST_END = '2019-12-31'
INITIAL_CASH = 100000

print(f"\nTest Parameters:")
print(f"  Symbol: {TEST_SYMBOL}")
print(f"  Period: {TEST_START} to {TEST_END}")
print(f"  Initial Cash: ${INITIAL_CASH:,.2f}")

# Load data
print("\nLoading data...")
loader = DataLoader(config.DATABASE_PATH)

try:
    df = loader.load_stock_data(TEST_SYMBOL, start_date=TEST_START, end_date=TEST_END)
    print(f"  ✓ {TEST_SYMBOL}: {len(df)} bars")
except Exception as e:
    print(f"  ✗ {TEST_SYMBOL}: {e}")
    exit(1)

# Test different MA configurations
test_configs = [
    {
        'name': 'SMA 10/50 (Fast)',
        'genes': [10, 50, 0, 5.0, 10.0, 15.0],  # Short MA, Long MA, Type (SMA), Stop Loss, Take Profit, Position Size
    },
    {
        'name': 'EMA 10/50 (Fast)',
        'genes': [10, 50, 1, 5.0, 10.0, 15.0],  # EMA instead of SMA
    },
    {
        'name': 'SMA 20/100 (Slow)',
        'genes': [20, 100, 0, 5.0, 10.0, 15.0],
    },
]

results = []

for test_config in test_configs:
    print(f"\n{'=' * 60}")
    print(f"Testing: {test_config['name']}")
    print(f"{'=' * 60}")

    # Create trader with test genes
    trader = GeneticTrader(test_config['genes'])
    genes = trader.get_genes()

    ma_type_str = 'SMA' if genes['ma_type'] == 0 else 'EMA'
    print(f"\nGenes:")
    print(f"  MA Type: {ma_type_str}")
    print(f"  Short MA Period: {genes['ma_short_period']}")
    print(f"  Long MA Period: {genes['ma_long_period']}")
    print(f"  Stop Loss: {genes['stop_loss_pct']:.1f}%")
    print(f"  Take Profit: {genes['take_profit_pct']:.1f}%")
    print(f"  Position Size: {genes['position_size_pct']:.1f}%")

    # Create strategy
    strategy_class = create_strategy_from_trader(trader, use_portfolio=False)

    # Create cerebro and add strategy
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_class, printlog=False)  # Set to True to see trade details

    # Add data feed
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    # Set broker parameters
    cerebro.broker.setcash(INITIAL_CASH)
    cerebro.broker.setcommission(commission=config.COMMISSION)

    # Run backtest
    starting_value = cerebro.broker.getvalue()
    strategies = cerebro.run()
    ending_value = cerebro.broker.getvalue()

    total_return = ((ending_value - starting_value) / starting_value) * 100

    # Get strategy stats
    strat = strategies[0]

    result = {
        'name': test_config['name'],
        'starting_value': starting_value,
        'ending_value': ending_value,
        'total_return': total_return,
        'trades': strat.trade_count,
        'winning_trades': strat.winning_trades,
        'losing_trades': strat.losing_trades,
        'win_rate': strat.get_win_rate() if strat.trade_count > 0 else 0,
    }
    results.append(result)

    print(f"\nResults:")
    print(f"  Starting Value: ${starting_value:,.2f}")
    print(f"  Ending Value: ${ending_value:,.2f}")
    print(f"  Total Return: {total_return:.2f}%")
    print(f"  Total Trades: {strat.trade_count}")
    if strat.trade_count > 0:
        print(f"  Winning Trades: {strat.winning_trades}")
        print(f"  Losing Trades: {strat.losing_trades}")
        print(f"  Win Rate: {strat.get_win_rate():.2f}%")

# Summary comparison
print(f"\n{'=' * 60}")
print("SUMMARY COMPARISON")
print(f"{'=' * 60}")
print(f"\n{'Configuration':<25} {'Return':<12} {'Trades':<8} {'Win Rate':<10}")
print("-" * 60)
for result in results:
    print(f"{result['name']:<25} {result['total_return']:>10.2f}% {result['trades']:>7} {result['win_rate']:>9.1f}%")

print(f"\n{'=' * 60}")
print("Test Complete!")
print(f"{'=' * 60}")

# Find best configuration
if results:
    best = max(results, key=lambda x: x['total_return'])
    print(f"\nBest Configuration: {best['name']}")
    print(f"  Return: {best['total_return']:.2f}%")
    print(f"  Trades: {best['trades']}")
    print(f"  Win Rate: {best['win_rate']:.1f}%")
