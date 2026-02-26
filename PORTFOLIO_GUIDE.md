# Portfolio Mode Guide

## Overview

Portfolio mode is a major enhancement that evaluates trading strategies across **multiple stocks simultaneously** instead of just one. This provides:

✅ **Better Generalization** - Strategies must work across diverse stocks
✅ **Reduced Overfitting** - Can't optimize for quirks of a single stock
✅ **Robust Evaluation** - Averaged performance across 20 stocks
✅ **Realistic Trading** - Mimics real portfolio management

## How It Works

### Traditional Single-Stock Mode
```
Trader → Test on AAPL → Fitness = AAPL performance
```
**Problem**: Strategy might only work for AAPL's specific patterns

### Portfolio Mode
```
Trader → Test on [AAPL, MSFT, GOOGL, ... 20 stocks] → Fitness = Portfolio average
```
**Benefit**: Strategy must work across tech, financials, healthcare, energy, etc.

## Configuration

### Enable Portfolio Mode

Edit [config.py](config.py):

```python
# Multi-stock portfolio configuration
USE_PORTFOLIO = True  # Enable portfolio mode
PORTFOLIO_SIZE = 20   # Number of stocks to trade

# Option 1: Manually specify stocks (recommended)
PORTFOLIO_STOCKS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA',  # Tech
    'JPM', 'BAC', 'WFC', 'GS', 'MS',          # Financials
    'JNJ', 'UNH', 'PFE', 'ABBV', 'TMO',       # Healthcare
    'XOM', 'CVX', 'COP',                       # Energy
    'WMT', 'HD'                                # Retail
]

# Option 2: Randomly select from database
AUTO_SELECT_PORTFOLIO = True  # Overrides PORTFOLIO_STOCKS
```

### Disable Portfolio Mode (Single Stock)

```python
USE_PORTFOLIO = False  # Back to single stock mode
TEST_SYMBOL = "AAPL"   # Which stock to test
```

## Portfolio Selection Strategies

### 1. Sector Diversification (Recommended)

Choose stocks from different sectors to test strategy broadly:

```python
PORTFOLIO_STOCKS = [
    # Technology
    'AAPL', 'MSFT', 'GOOGL', 'NVDA',

    # Financials
    'JPM', 'BAC', 'GS', 'MS',

    # Healthcare
    'JNJ', 'UNH', 'PFE', 'ABBV',

    # Consumer
    'WMT', 'HD', 'NKE', 'SBUX',

    # Energy
    'XOM', 'CVX', 'COP',

    # Industrials
    'CAT', 'BA', 'GE'
]
```

### 2. Random Selection

Let the system randomly pick stocks:

```python
AUTO_SELECT_PORTFOLIO = True
PORTFOLIO_SIZE = 20
RANDOM_SEED = 42  # For reproducibility
```

This ensures no manual bias in stock selection.

### 3. Top Performers

Select the most liquid/stable stocks:

```python
PORTFOLIO_STOCKS = [
    # S&P 500 top 20 by market cap
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA',
    'META', 'TSLA', 'BRK.B', 'V', 'UNH',
    'JNJ', 'WMT', 'JPM', 'MA', 'PG',
    'XOM', 'HD', 'CVX', 'BAC', 'ABBV'
]
```

### 4. Specific Theme

Test strategy on a specific sector or theme:

```python
# Tech-focused portfolio
PORTFOLIO_STOCKS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
    'NVDA', 'TSLA', 'NFLX', 'AMD', 'INTC',
    'CSCO', 'ORCL', 'ADBE', 'CRM', 'AVGO',
    'QCOM', 'TXN', 'AMAT', 'MU', 'NOW'
]
```

## Running Portfolio Evolution

```bash
# Quick test (3 generations, 5 stocks)
python test_portfolio.py

# Full evolution (20 stocks, 50 generations)
python evolve.py
```

## Expected Output

```
============================================================
PORTFOLIO MODE
============================================================

Portfolio size: 20 stocks
Symbols: AAPL, MSFT, GOOGL, JPM, WMT...

Loading portfolio data for 20 stocks...
  ✓ AAPL: 2015 bars
  ✓ MSFT: 2015 bars
  ✓ GOOGL: 2015 bars
  ...
  ✓ WMT: 2015 bars

Successfully loaded 20/20 stocks

============================================================
Starting Genetic Algorithm Evolution
Mode: PORTFOLIO (20 stocks)
Stocks: AAPL, MSFT, GOOGL, JPM, WMT...
Population Size: 20
Generations: 50
============================================================

Generation 10/50
============================================================
Evaluating population fitness...

Generation 10 Statistics:
  Best Fitness: 52.34      ← Portfolio average performance
  Average Fitness: 23.45
  ...
```

## Understanding Portfolio Fitness

The fitness score is calculated from the **combined portfolio performance**:

```python
Portfolio Performance = Aggregate of all 20 stocks trading simultaneously

Fitness = 0.4 × Total Portfolio Return
        + 0.3 × Portfolio Sharpe Ratio × 10
        + 0.2 × Portfolio Max Drawdown
        + 0.1 × Portfolio Win Rate
```

### Example

A trader with these results across 20 stocks:
- **Portfolio Return**: +85% (averaged across all 20 stocks)
- **Sharpe Ratio**: 1.2
- **Max Drawdown**: -15%
- **Win Rate**: 58%

```
Fitness = 0.4(85) + 0.3(1.2×10) + 0.2(-15) + 0.1(58)
        = 34 + 3.6 - 3 + 5.8
        = 40.4
```

This is a **robust score** because it worked across 20 different stocks!

## Benefits Over Single Stock

| Aspect | Single Stock | Portfolio (20 stocks) |
|--------|-------------|---------------------|
| **Overfitting Risk** | High - optimizes for 1 stock | Low - must work broadly |
| **Generalization** | Poor - specific to AAPL | Excellent - diverse sectors |
| **Robustness** | Fragile - one stock's quirks | Stable - averaged performance |
| **Real-World** | Unrealistic | Realistic portfolio |
| **Evaluation Time** | Fast (1 stock) | Slower (20 stocks) |
| **Confidence** | Low - might be luck | High - proven across stocks |

## Performance Considerations

Portfolio mode is **slower** because it backtests 20 stocks per trader:

```
Single Stock:  20 traders × 1 stock  = 20 backtests/generation
Portfolio:     20 traders × 20 stocks = 400 backtests/generation
```

### Speed Optimization Tips

1. **Reduce portfolio size** during development:
   ```python
   PORTFOLIO_SIZE = 10  # Instead of 20
   ```

2. **Shorter date range** for testing:
   ```python
   TRAIN_START_DATE = "2018-01-01"  # Instead of 2012
   ```

3. **Smaller population** for quick tests:
   ```python
   POPULATION_SIZE = 10  # Instead of 20
   ```

4. **Fewer generations** initially:
   ```python
   NUM_GENERATIONS = 20  # Instead of 50
   ```

## Analyzing Results

After evolution completes, check the summary:

```json
{
  "mode": "portfolio",
  "portfolio_symbols": ["AAPL", "MSFT", ...],
  "portfolio_size": 20,
  "best_trader": {
    "fitness": 52.34,
    "genes": {
      "rsi_period": 12,
      "rsi_overbought": 68,
      ...
    },
    "performance": {
      "total_return": 85.42,
      "sharpe_ratio": 1.23,
      "trade_count": 287,  ← Across all 20 stocks
      "win_rate": 58.32
    }
  }
}
```

## Per-Stock Analysis

Get detailed breakdown for each stock:

```python
from portfolio_fitness import PortfolioFitnessEvaluator
from genetic_trader import GeneticTrader

# Load best trader
trader = GeneticTrader([12, 68, 32, 2.8, 6.5, 18.0])

# Create evaluator
evaluator = PortfolioFitnessEvaluator(
    symbols=config.PORTFOLIO_STOCKS,
    start_date="2012-01-01",
    end_date="2020-12-31"
)

# Get per-stock results
results = evaluator.get_per_stock_results(trader)

for symbol, stats in results.items():
    print(f"{symbol}: {stats['return_pct']:.2f}% ({stats['trades']} trades)")
```

Output:
```
AAPL: +92.34% (18 trades)
MSFT: +78.23% (15 trades)
GOOGL: +65.11% (12 trades)
JPM: +45.67% (14 trades)
...
```

## Best Practices

### 1. Use Diverse Sectors
Don't pick all tech stocks - diversify across sectors:
```python
✓ Good: Tech + Finance + Healthcare + Energy + Retail
✗ Bad: 20 tech stocks
```

### 2. Ensure Data Quality
All stocks should have complete data for the date range:
```python
# Check data availability first
python data_loader.py
```

### 3. Start Small, Scale Up
```python
# Development
PORTFOLIO_SIZE = 5
NUM_GENERATIONS = 10

# Testing
PORTFOLIO_SIZE = 10
NUM_GENERATIONS = 25

# Production
PORTFOLIO_SIZE = 20
NUM_GENERATIONS = 50
```

### 4. Monitor Per-Stock Performance
Some stocks might not trade at all - this is okay! The strategy is being conservative.

### 5. Save Your Portfolio Config
Document which stocks you used for reproducibility:
```python
# In your results/summary_*.json
"portfolio_symbols": ["AAPL", "MSFT", ...]
```

## Comparison Example

Run both modes and compare:

```bash
# Single stock
# Set USE_PORTFOLIO = False
python evolve.py > single_stock_results.txt

# Portfolio
# Set USE_PORTFOLIO = True
python evolve.py > portfolio_results.txt
```

You'll likely find:
- **Single stock**: Higher fitness scores (optimized for one stock)
- **Portfolio**: Lower but more **robust** fitness scores (works broadly)

The portfolio winner is more likely to generalize to new, unseen stocks!

## Troubleshooting

### Issue: No trades executed
**Cause**: Parameters too conservative for multiple stocks

**Solution**: Adjust gene bounds in config.py:
```python
'rsi_oversold': (20, 40, int),  # Was (10, 40)
```

### Issue: Very slow execution
**Cause**: 20 stocks × 20 traders = 400 backtests

**Solutions**:
- Reduce PORTFOLIO_SIZE to 10
- Reduce POPULATION_SIZE to 15
- Use shorter date range
- Use faster hardware

### Issue: Some stocks fail to load
**Cause**: Missing data in database

**Solution**: System automatically skips failed stocks:
```
Loading portfolio data for 20 stocks...
  ✓ AAPL: 2015 bars
  ✗ INVALID_SYMBOL: Failed to load
  ...
Successfully loaded 19/20 stocks  ← Continues with 19
```

## Advanced: Custom Portfolio Strategies

You can create specialized portfolios for specific research:

```python
# Volatility test - mix stable and volatile
PORTFOLIO_STOCKS = [
    'JNJ', 'PG', 'KO',      # Stable blue chips
    'TSLA', 'GME', 'AMC'    # Volatile stocks
]

# Sector rotation test
PORTFOLIO_STOCKS = [
    'XLF', 'XLE', 'XLV',    # Sector ETFs
    'XLI', 'XLK', 'XLP'
]

# Size diversification
PORTFOLIO_STOCKS = [
    'AAPL', 'MSFT',         # Mega cap
    'SQ', 'ROKU',           # Mid cap
    'PLUG', 'SPCE'          # Small/speculative
]
```

## Summary

Portfolio mode is **the recommended way** to evolve trading strategies because:

1. ✅ **Prevents overfitting** to a single stock's patterns
2. ✅ **Validates robustness** across diverse market conditions
3. ✅ **Produces generalizable** strategies
4. ✅ **Realistic evaluation** like real portfolio management
5. ✅ **Higher confidence** in results

**Trade-off**: Slower but much more reliable results!

---

**Ready to evolve robust, portfolio-tested strategies?**

```bash
# Edit config.py
USE_PORTFOLIO = True
PORTFOLIO_SIZE = 20

# Run evolution
python evolve.py
```

🧬📈 Happy evolving across multiple stocks!
