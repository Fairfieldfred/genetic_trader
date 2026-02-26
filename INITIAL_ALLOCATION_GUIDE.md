# Initial Allocation Feature Guide

## Overview

The Initial Allocation feature allows you to configure what percentage of your starting capital is immediately invested in equal dollar amounts across all portfolio stocks at the beginning of the backtest, with the remaining percentage held as cash for the genetic trading strategy to use when it generates buy signals.

## Configuration

### config.py

```python
# Portfolio initial allocation (only applies when USE_PORTFOLIO = True)
INITIAL_ALLOCATION_PCT = 80.0  # Range: 0.0 to 100.0
```

- **Range**: 0.0 to 100.0
- **Default**: 80.0 (80% allocated, 20% cash reserve)
- **Only applies**: When `USE_PORTFOLIO = True`

## How It Works

### Example Configuration

```python
USE_PORTFOLIO = True
PORTFOLIO_SIZE = 20
INITIAL_CASH = 100000
INITIAL_ALLOCATION_PCT = 80.0
```

### Capital Allocation

With the above configuration:

1. **Initial Allocation**: $100,000 × 80% = **$80,000**
   - Divided equally among 20 stocks = **$4,000 per stock**
   - Purchased immediately on Day 1 at opening prices

2. **Reserved Cash**: $100,000 × 20% = **$20,000**
   - Available for RSI-based buy signals
   - Used according to `position_size_pct` gene (5-25%)

### Trading Behavior

#### Initial Positions (from allocation)

The strategy purchases equal dollar amounts of each stock on Day 1:

```
Day 1 Purchases:
- AAPL: $4,000 ÷ $150/share = 26 shares
- MSFT: $4,000 ÷ $200/share = 20 shares
- GOOGL: $4,000 ÷ $1,000/share = 4 shares
... (17 more stocks)
```

#### Active Management

These initial positions are **actively managed** by the genetic strategy:

✅ **Can be sold** when:
- RSI exceeds `rsi_overbought` threshold
- Stop loss triggers (`stop_loss_pct`)
- Take profit triggers (`take_profit_pct`)

✅ **Can be added to** when:
- RSI drops below `rsi_oversold` AND
- Sufficient reserved cash is available

#### Reserved Cash Usage

The 20% reserved cash ($20,000) is used for RSI-based signals:

```python
# When RSI signal triggers
if rsi < rsi_oversold and cash_available:
    buy_amount = cash × position_size_pct
    # Example: $20,000 × 10% = $2,000 per buy signal
```

## Strategy Comparison

### vs. Pure Buy-and-Hold

The benchmark calculation uses the **same allocation percentage** for fair comparison:

```
Benchmark (80% allocated):
- Buys $4,000 of each stock on Day 1
- Holds until the end (no selling)
- 20% stays as cash (earning 0% return)

Genetic Strategy (80% allocated):
- Buys $4,000 of each stock on Day 1
- Actively trades based on RSI signals
- Can sell positions and re-enter
- Uses 20% reserve for additional opportunities
```

### vs. Pure Genetic Strategy (0% initial allocation)

| Configuration | Initial Allocation | Reserved Cash | Behavior |
|---------------|-------------------|---------------|----------|
| **0%** | $0 (no positions) | $100,000 (100%) | Pure RSI-based trading, starts flat |
| **50%** | $50,000 (equal-weight) | $50,000 (50%) | Hybrid approach |
| **80%** | $80,000 (equal-weight) | $20,000 (20%) | Mostly allocated, some flexibility |
| **100%** | $100,000 (equal-weight) | $0 (0%) | Full allocation, like buy-and-hold but with active management |

## Use Cases

### Conservative (High Initial Allocation)

```python
INITIAL_ALLOCATION_PCT = 90.0  # or higher
```

- **Pros**: More market exposure, captures overall market trends
- **Cons**: Less cash for tactical opportunities
- **Best for**: Bullish markets, long-term growth

### Balanced (Medium Initial Allocation)

```python
INITIAL_ALLOCATION_PCT = 70.0  # to 80.0
```

- **Pros**: Good market exposure + tactical flexibility
- **Cons**: Moderate trade-off
- **Best for**: Most market conditions (default)

### Aggressive Trading (Low Initial Allocation)

```python
INITIAL_ALLOCATION_PCT = 30.0  # or lower
```

- **Pros**: Maximum cash for RSI-based opportunities
- **Cons**: May miss overall market gains
- **Best for**: Volatile markets, active trading strategies

### Pure Signal-Based (No Initial Allocation)

```python
INITIAL_ALLOCATION_PCT = 0.0
```

- **Pros**: 100% tactical, only enters on signals
- **Cons**: May hold too much cash in trending markets
- **Best for**: Testing pure genetic strategy effectiveness

## Testing

Run the test script to verify the feature:

```bash
python test_initial_allocation.py
```

Expected output shows:
1. Initial allocation purchasing equal dollar amounts
2. Reserved cash remaining
3. Strategy selling initial positions (take profit, stop loss, etc.)
4. Strategy using reserved cash for RSI signals

## Evolution Results

The summary JSON file now includes:

```json
{
  "run_id": "20250101_120000",
  "mode": "portfolio",
  "initial_allocation_pct": 80.0,
  "benchmark": {
    "buy_and_hold_return": 12.5,
    "allocation_pct": 80.0,
    "strategy_outperformance": 2.3,
    "beats_benchmark": true
  }
}
```

## Implementation Details

### Files Modified

1. **config.py**: Added `INITIAL_ALLOCATION_PCT` parameter
2. **bt_strategy.py**: Created `PortfolioGeneticStrategy` class
3. **portfolio_fitness.py**: Updated to use portfolio strategy
4. **benchmark.py**: Added `allocation_pct` parameter to benchmark
5. **evolve.py**: Updated to pass allocation to strategy and benchmark

### Key Classes

#### PortfolioGeneticStrategy

- Extends `GeneticStrategy`
- Manages multiple data feeds simultaneously
- Makes initial purchases in `_make_initial_allocation()`
- Applies genetic parameters to all stocks
- Tracks positions per stock

#### Strategy Selection

The `create_strategy_from_trader()` function automatically selects:

```python
if use_portfolio:
    return PortfolioGeneticStrategy  # With initial allocation
else:
    return GeneticStrategy  # Single stock (no initial allocation)
```

## Tips

1. **Start with default**: `INITIAL_ALLOCATION_PCT = 80.0` is a good balance

2. **Match benchmark**: The benchmark automatically uses the same allocation percentage for fair comparison

3. **Consider market conditions**:
   - Bull markets: Higher allocation (90%+)
   - Volatile markets: Lower allocation (50-70%)
   - Uncertain markets: Very low allocation (20-30%)

4. **Optimization**: You can include `INITIAL_ALLOCATION_PCT` as a hyperparameter to optimize

5. **Gene interaction**: The `position_size_pct` gene controls how much of the **reserved cash** is used per signal, not the initial allocation

## Future Enhancements

Potential improvements:
- Per-stock allocation weights (instead of equal-weight)
- Dynamic rebalancing of initial positions
- Time-based allocation (scale in over time)
- Sector-based allocation strategies
