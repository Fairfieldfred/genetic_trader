"""
Test script for MA strategy in portfolio mode.
"""

import config
from data_loader import DataLoader
from genetic_trader import GeneticTrader
from bt_strategy import create_strategy_from_trader
import backtrader as bt

print("Testing MA Strategy in Portfolio Mode")
print("=" * 60)

# Test configuration
TEST_SYMBOLS = ['AAPL', 'MSFT', 'GOOGL']
TEST_START = '2019-01-01'
TEST_END = '2019-12-31'
INITIAL_CASH = 100000
ALLOCATION_PCT = 70.0

print(f"\nTest Parameters:")
print(f"  Symbols: {', '.join(TEST_SYMBOLS)}")
print(f"  Period: {TEST_START} to {TEST_END}")
print(f"  Initial Cash: ${INITIAL_CASH:,.2f}")
print(f"  Allocation: {ALLOCATION_PCT}%")

# Load data
print("\nLoading data...")
loader = DataLoader(config.DATABASE_PATH)
data_feeds = {}

for symbol in TEST_SYMBOLS:
    try:
        df = loader.load_stock_data(symbol, start_date=TEST_START, end_date=TEST_END)
        data_feeds[symbol] = df
        print(f"  ✓ {symbol}: {len(df)} bars")
    except Exception as e:
        print(f"  ✗ {symbol}: {e}")

if len(data_feeds) == 0:
    print("\nERROR: No data loaded. Cannot proceed with test.")
    exit(1)

# Create trader with MA genes
# [ma_short_period, ma_long_period, ma_type, stop_loss_pct, take_profit_pct, position_size_pct]
trader = GeneticTrader([10, 50, 1, 5.0, 10.0, 15.0])  # EMA 10/50
genes = trader.get_genes()

ma_type_str = 'SMA' if genes['ma_type'] == 0 else 'EMA'
print(f"\nTrader Configuration:")
print(f"  MA Type: {ma_type_str}")
print(f"  Short MA: {genes['ma_short_period']}")
print(f"  Long MA: {genes['ma_long_period']}")
print(f"  Stop Loss: {genes['stop_loss_pct']:.1f}%")
print(f"  Take Profit: {genes['take_profit_pct']:.1f}%")
print(f"  Position Size: {genes['position_size_pct']:.1f}%")

# Create portfolio strategy
print(f"\nCreating portfolio strategy...")
strategy_class = create_strategy_from_trader(
    trader,
    use_portfolio=True,
    initial_allocation_pct=ALLOCATION_PCT
)

# Create cerebro
cerebro = bt.Cerebro()
cerebro.addstrategy(strategy_class, printlog=True)

# Add data feeds
for symbol, df in data_feeds.items():
    data = bt.feeds.PandasData(dataname=df, name=symbol)
    cerebro.adddata(data)

# Set broker parameters
cerebro.broker.setcash(INITIAL_CASH)
cerebro.broker.setcommission(commission=config.COMMISSION)

# Run backtest
print(f"\n{'=' * 60}")
print("Running Backtest...")
print(f"{'=' * 60}\n")

starting_value = cerebro.broker.getvalue()
strategies = cerebro.run()
ending_value = cerebro.broker.getvalue()

total_return = ((ending_value - starting_value) / starting_value) * 100

# Get strategy stats
strat = strategies[0]

print(f"\n{'=' * 60}")
print("RESULTS")
print(f"{'=' * 60}")
print(f"Starting Value: ${starting_value:,.2f}")
print(f"Ending Value: ${ending_value:,.2f}")
print(f"Total Return: {total_return:.2f}%")
print(f"\nTrade Statistics:")
print(f"  Total Trades: {strat.trade_count}")
if strat.trade_count > 0:
    print(f"  Winning Trades: {strat.winning_trades}")
    print(f"  Losing Trades: {strat.losing_trades}")
    print(f"  Win Rate: {strat.get_win_rate():.2f}%")

print(f"\n{'=' * 60}")
print("Test Complete!")
print(f"{'=' * 60}")
