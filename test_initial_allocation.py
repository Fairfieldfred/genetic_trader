"""
Test script for initial allocation feature.
Verifies that the portfolio strategy correctly allocates initial capital.
"""

import config
from data_loader import DataLoader
from genetic_trader import GeneticTrader
from bt_strategy import create_strategy_from_trader
import backtrader as bt

print("Testing Initial Allocation Feature")
print("=" * 60)

# Test configuration
TEST_SYMBOLS = ['AAPL', 'MSFT', 'GOOGL']
TEST_START = '2019-01-01'
TEST_END = '2019-12-31'
INITIAL_CASH = 100000
ALLOCATION_PCT = 80.0  # 80% allocated, 20% reserved

print(f"\nTest Parameters:")
print(f"  Symbols: {', '.join(TEST_SYMBOLS)}")
print(f"  Period: {TEST_START} to {TEST_END}")
print(f"  Initial Cash: ${INITIAL_CASH:,.2f}")
print(f"  Allocation: {ALLOCATION_PCT}% (${INITIAL_CASH * ALLOCATION_PCT / 100:,.2f})")
print(f"  Reserved Cash: {100 - ALLOCATION_PCT}% (${INITIAL_CASH * (100 - ALLOCATION_PCT) / 100:,.2f})")

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

# Create a test genetic trader
print("\nCreating test trader...")
trader = GeneticTrader([14, 70, 30, 5.0, 10.0, 15.0])
print(f"  Genes: {trader.get_genes()}")

# Create portfolio strategy with initial allocation
print("\nCreating portfolio strategy with initial allocation...")
strategy_class = create_strategy_from_trader(
    trader,
    use_portfolio=True,
    initial_allocation_pct=ALLOCATION_PCT
)

# Create cerebro and add strategy
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
print("\n" + "=" * 60)
print("Running Backtest...")
print("=" * 60)

starting_value = cerebro.broker.getvalue()
print(f"\nStarting Portfolio Value: ${starting_value:,.2f}")

strategies = cerebro.run()

ending_value = cerebro.broker.getvalue()
total_return = ((ending_value - starting_value) / starting_value) * 100

print("\n" + "=" * 60)
print("Results:")
print("=" * 60)
print(f"Starting Value: ${starting_value:,.2f}")
print(f"Ending Value: ${ending_value:,.2f}")
print(f"Total Return: {total_return:.2f}%")

# Get strategy stats
strat = strategies[0]
print(f"\nTrade Statistics:")
print(f"  Total Trades: {strat.trade_count}")
print(f"  Winning Trades: {strat.winning_trades}")
print(f"  Losing Trades: {strat.losing_trades}")
if strat.trade_count > 0:
    print(f"  Win Rate: {strat.get_win_rate():.2f}%")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
print("\nExpected behavior:")
print(f"1. Initial allocation should purchase equal dollar amounts")
print(f"   of each stock: ${INITIAL_CASH * ALLOCATION_PCT / 100 / len(data_feeds):,.2f} per stock")
print(f"2. Remaining cash: ${INITIAL_CASH * (100 - ALLOCATION_PCT) / 100:,.2f}")
print(f"3. Strategy can use reserved cash for RSI signals")
print(f"4. Strategy can sell initial positions (stop loss, take profit, overbought)")
