# Quick Start Guide

## Installation

1. Install required packages:
```bash
pip install backtrader pandas numpy matplotlib
```

2. Verify your spy.db database is in the project directory

## Run Your First Evolution

### Option 1: Use Default Settings (Recommended for First Run)

```bash
python evolve.py
```

This will:
- Trade AAPL stock
- Train on 2012-2020 data
- Use population of 20 traders
- Evolve for 50 generations
- Takes about 10-20 minutes depending on your machine

### Option 2: Quick Test Run

For a faster test (2 minutes):

```bash
python test_evolution.py
```

This runs a minimal evolution (2 generations, 5 traders, 1 year of data).

## What Happens During Evolution

```
1. System loads stock data from spy.db
2. Creates 20 random traders with different gene combinations
3. Each generation:
   - Tests each trader via backtrading
   - Calculates fitness scores
   - Selects best performers as parents
   - Creates offspring via crossover
   - Applies random mutations
   - Repeats for next generation
4. Saves best trader and results
```

## Understanding the Output

### During Evolution

```
Generation 15/50
============================================================
Evaluating population fitness...
Evaluated 5/20 traders
Evaluated 10/20 traders
...

Generation 15 Statistics:
  Best Fitness: 45.23      ← Highest score this generation
  Average Fitness: 12.45   ← Population average
  Worst Fitness: -15.34    ← Lowest score
  Std Dev: 18.23           ← Population diversity

Best Trader Genes:
  rsi_period: 14           ← RSI calculation period
  rsi_overbought: 72       ← Sell when RSI > 72
  rsi_oversold: 28         ← Buy when RSI < 28
  stop_loss_pct: 3.50      ← Exit if down 3.5%
  take_profit_pct: 7.20    ← Exit if up 7.2%
  position_size_pct: 15.00 ← Risk 15% per trade
```

### Final Results

```
EVOLUTION COMPLETE
============================================================

Best Trader Found (Generation 47):
Fitness: 78.45

Detailed Performance Metrics:
  Total Return: 145.32%    ← Made 145% over the period
  Sharpe Ratio: 1.23       ← Risk-adjusted returns (>1 is good)
  Max Drawdown: -18.45%    ← Worst peak-to-valley drop
  Total Trades: 87         ← Number of trades executed
  Win Rate: 59.77%         ← Percentage of winning trades
```

## Output Files

Check the `results/` directory:

```
results/
├── best_trader_20241028_153520.json    ← Best trader's genes
├── history_20241028_153520.csv         ← Fitness per generation
├── summary_20241028_153520.json        ← Complete run summary
└── evolution_20241028_153520.png       ← Fitness evolution plot
```

## Customizing Your Run

### Edit config.py

```python
# Try different stocks
TEST_SYMBOL = "MSFT"  # or "GOOGL", "TSLA", etc.

# Adjust evolution parameters
POPULATION_SIZE = 30      # More diversity (slower)
NUM_GENERATIONS = 100     # More evolution (slower)
MUTATION_RATE = 0.20      # More exploration

# Change date ranges
TRAIN_START_DATE = "2015-01-01"
TRAIN_END_DATE = "2022-12-31"
```

### Run with custom settings

```bash
python evolve.py
```

## Interpreting Fitness Scores

The fitness score combines multiple metrics:

```
Fitness = 0.4 × Total Return
        + 0.3 × Sharpe Ratio × 10
        + 0.2 × Max Drawdown (negative)
        + 0.1 × Win Rate

Good scores:  50+
Great scores: 75+
Excellent:    100+
```

**Note:** Strategies must execute at least 5 trades to get a positive score.

## Common Issues

### Issue: All traders have -100 fitness

**Cause:** Strategies aren't trading enough (< 5 trades)

**Solution:**
- Use longer date range
- Adjust RSI threshold ranges in config.py
- Lower the MIN_TRADES_REQUIRED in config.py

### Issue: Evolution is slow

**Cause:** Large population or many generations

**Solutions:**
- Reduce POPULATION_SIZE (try 10-15)
- Reduce NUM_GENERATIONS (try 25-30)
- Use shorter date range for training
- Use faster hardware

### Issue: Fitness not improving

**Cause:** Population converged too quickly or stuck in local optimum

**Solutions:**
- Increase MUTATION_RATE (try 0.20-0.30)
- Increase POPULATION_SIZE
- Reduce ELITISM_COUNT
- Try different RANDOM_SEED values

## Testing Individual Components

Test data loading:
```bash
python data_loader.py
```

Test genetic operations:
```bash
python test_genetic_ops.py
```

Test a single backtest:
```bash
python bt_strategy.py
```

Test fitness calculation:
```bash
python calculate_fitness.py
```

## Next Steps

1. **Run the full evolution** to find optimal parameters
2. **Analyze the results** in the results/ directory
3. **Test different stocks** by changing TEST_SYMBOL
4. **Experiment with genes** - add new indicators (see README.md)
5. **Walk-forward test** - use best genes on out-of-sample data

## Example: Full Workflow

```bash
# 1. Install dependencies
pip install backtrader pandas numpy matplotlib

# 2. Quick test to verify system works
python test_genetic_ops.py
python test_evolution.py

# 3. Run full evolution
python evolve.py

# 4. Check results
ls -l results/
cat results/summary_*.json

# 5. Test best strategy on different period
# Edit config.py: TEST_START_DATE = "2021-01-01"
# Edit config.py: TEST_END_DATE = "2023-12-31"
python bt_strategy.py  # Tests with saved genes
```

## Tips for Better Results

1. **Longer training periods** = more reliable strategies
2. **Larger populations** = more diversity, better exploration
3. **More generations** = more refinement
4. **Lower mutation rates** = faster convergence
5. **Higher mutation rates** = more exploration
6. **Multiple runs** = find different local optima
7. **Out-of-sample testing** = verify strategy generalizes

## Understanding the Trading Strategy

The evolved strategy uses RSI (Relative Strength Index):

```
RSI < 30 (oversold)  →  BUY SIGNAL
RSI > 70 (overbought) →  SELL SIGNAL

Plus risk management:
- Stop loss: exit if down X%
- Take profit: exit if up Y%
- Position sizing: risk Z% of capital
```

The genetic algorithm finds the optimal values for X, Y, Z and the RSI thresholds.

## Performance Expectations

Realistic expectations:
- **Training return**: 50-150% over multi-year period
- **Sharpe ratio**: 0.8-2.0
- **Max drawdown**: 15-30%
- **Win rate**: 45-65%

**Remember:**
- Past performance ≠ future results
- This is for educational purposes
- Always validate strategies before real trading
- Beware of overfitting

---

**Ready to evolve some trading strategies? Run `python evolve.py` to start!** 🧬📈
