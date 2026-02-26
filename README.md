# Genetic Trading Algorithm

A genetic algorithm that evolves optimal trading strategies using Backtrader for backtesting. The system uses evolutionary principles (crossover, mutation, selection) to discover profitable trading parameters.

**🆕 NEW: Portfolio Mode** - Test strategies across 20 stocks simultaneously for robust, generalizable results! See [PORTFOLIO_GUIDE.md](PORTFOLIO_GUIDE.md)

## Overview

This project implements a genetic algorithm to optimize trading strategies. Each "trader" is represented by a chromosome containing genes that define trading parameters (RSI periods, stop losses, position sizing, etc.). The algorithm evolves these traders over multiple generations to find strategies that maximize fitness (a combination of returns, Sharpe ratio, and other metrics).

### Single Stock vs Portfolio Mode

- **Single Stock Mode**: Tests strategies on one stock (e.g., AAPL only)
  - ✓ Fast execution
  - ✗ Risk of overfitting
  - ✗ May not generalize

- **Portfolio Mode** (Recommended): Tests strategies across 20 diverse stocks
  - ✓ Robust, generalizable strategies
  - ✓ Reduced overfitting
  - ✓ Realistic portfolio management
  - ✗ Slower execution (20x more backtests)

See [PORTFOLIO_GUIDE.md](PORTFOLIO_GUIDE.md) for detailed portfolio configuration.

## Architecture

```
┌─────────────────┐
│  Data Loader    │ ──> Loads stock data from spy.db into pandas DataFrame
└─────────────────┘

┌─────────────────┐
│ Genetic Trader  │ ──> Individual with chromosome (genes = trading params)
└─────────────────┘

┌─────────────────┐
│ Genetic Ops     │ ──> Crossover & mutation operations
└─────────────────┘

┌─────────────────┐
│  Population     │ ──> Manages population across generations
└─────────────────┘

┌─────────────────┐
│  BT Strategy    │ ──> Converts genes into Backtrader strategy
└─────────────────┘

┌─────────────────┐
│Fitness Evaluator│ ──> Runs backtest and calculates fitness score
└─────────────────┘

┌─────────────────┐
│    Evolve       │ ──> Main evolution loop orchestrator
└─────────────────┘
```

## Gene Definitions

Each trader has 6 genes that define its behavior:

1. **rsi_period** (7-21): Period for RSI calculation
2. **rsi_overbought** (60-90): RSI threshold for overbought signal
3. **rsi_oversold** (10-40): RSI threshold for oversold signal
4. **stop_loss_pct** (1.0-10.0): Stop loss percentage
5. **take_profit_pct** (2.0-15.0): Take profit percentage
6. **position_size_pct** (5.0-25.0): Position size as % of capital

## Trading Strategy

The evolved strategy is RSI-based:

- **BUY**: When RSI < rsi_oversold (oversold condition)
- **SELL**: When:
  - RSI > rsi_overbought (overbought), OR
  - Price drops by stop_loss_pct (stop loss), OR
  - Price rises by take_profit_pct (take profit)

## Fitness Function

Fitness is calculated as a weighted combination of:

```
Fitness = 0.4 × Total Return
        + 0.3 × Sharpe Ratio × 10
        + 0.2 × Max Drawdown (negative impact)
        + 0.1 × Win Rate
```

Minimum 5 trades required for valid fitness.

## File Structure

```
genetic_trader/
├── config.py              # Configuration and hyperparameters
├── data_loader.py         # Load stock data from spy.db
├── genetic_trader.py      # GeneticTrader class (individual)
├── genetic_ops.py         # Crossover and mutation operations
├── population.py          # Population manager
├── bt_strategy.py         # Backtrader strategy adapter
├── calculate_fitness.py   # Fitness evaluation (single stock)
├── portfolio_fitness.py   # Portfolio fitness evaluation (20 stocks)
├── evolve.py             # Main evolution loop
├── test_genetic_ops.py   # Test suite for genetic operations
├── test_portfolio.py     # Portfolio mode test
├── README.md             # Main documentation
├── PORTFOLIO_GUIDE.md    # Portfolio mode guide
├── QUICKSTART.md         # Quick start guide
├── initial_thoughts.md   # Design documentation
├── spy.db                # Stock market database
├── results/              # Evolution results (created on run)
├── logs/                 # Log files (created on run)
└── checkpoints/          # Saved checkpoints (created on run)
```

## Installation

### Requirements

```bash
pip install backtrader pandas numpy matplotlib
```

### Database

The system requires `spy.db` SQLite database with stock data in the `daily_indicators` table containing:
- date, open, high, low, close, volume
- Technical indicators: rsi, macd, signal, macdhist

## Usage

### Basic Usage

Run the full evolution:

```bash
python evolve.py
```

This will:
1. Load training data for AAPL (2012-2020)
2. Create a population of 20 random traders
3. Evolve for 50 generations
4. Save best trader and results to `results/`

### Configuration

Edit [config.py](config.py) to customize:

```python
# Portfolio mode (recommended for robust strategies)
USE_PORTFOLIO = True       # False for single stock mode
PORTFOLIO_SIZE = 20        # Number of stocks
PORTFOLIO_STOCKS = [       # Which stocks to trade
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA',
    # ... 15 more stocks
]
AUTO_SELECT_PORTFOLIO = False  # True to randomly select

# Single stock mode (faster, but may overfit)
TEST_SYMBOL = "AAPL"

# Genetic algorithm parameters
POPULATION_SIZE = 20
NUM_GENERATIONS = 50
MUTATION_RATE = 0.15
CROSSOVER_RATE = 0.7

# Date range
TRAIN_START_DATE = "2012-01-01"
TRAIN_END_DATE = "2020-12-31"

# Trading parameters
INITIAL_CASH = 100000
COMMISSION = 0.001  # 0.1%
```

### Testing Individual Components

Test data loading:
```bash
python data_loader.py
```

Test genetic operations:
```bash
python test_genetic_ops.py
```

Test Backtrader strategy:
```bash
python bt_strategy.py
```

Test fitness calculation:
```bash
python calculate_fitness.py
```

Test population manager:
```bash
python population.py
```

## Example Output

```
============================================================
Starting Genetic Algorithm Evolution
Symbol: AAPL
Population Size: 20
Generations: 50
============================================================

Loading data...
Loaded 2015 bars for AAPL
Date range: 2012-03-05 to 2020-12-31

============================================================
Generation 1/50
============================================================
Evaluating population fitness...
Evaluated 5/20 traders
Evaluated 10/20 traders
...

Generation 1 Statistics:
  Evaluated: 20/20
  Best Fitness: 45.2341
  Average Fitness: 12.4562
  Worst Fitness: -15.3421
  Std Dev: 18.2341

Best Trader Genes:
  rsi_period: 14
  rsi_overbought: 72
  rsi_oversold: 28
  stop_loss_pct: 3.50
  take_profit_pct: 7.20
  position_size_pct: 15.00

...

============================================================
EVOLUTION COMPLETE
============================================================

Best Trader Found (Generation 47):
Fitness: 78.4523

Genes:
  rsi_period: 12
  rsi_overbought: 68
  rsi_oversold: 32
  stop_loss_pct: 2.80
  take_profit_pct: 6.50
  position_size_pct: 18.00

Detailed Performance Metrics:
  Total Return: 145.32%
  Sharpe Ratio: 1.2341
  Max Drawdown: -18.45%
  Total Trades: 87
  Winning Trades: 52
  Win Rate: 59.77%
```

## Output Files

After evolution completes, check the `results/` directory:

- `best_trader_YYYYMMDD_HHMMSS.json` - Best trader chromosome and performance
- `history_YYYYMMDD_HHMMSS.csv` - Fitness evolution over generations
- `summary_YYYYMMDD_HHMMSS.json` - Complete run summary
- `evolution_YYYYMMDD_HHMMSS.png` - Fitness evolution plot (if matplotlib available)

## Extending the System

### Adding More Genes

1. Edit [config.py](config.py):
```python
GENE_DEFINITIONS = {
    'rsi_period': (7, 21, int),
    'ma_period': (10, 100, int),  # New gene
    # ... other genes
}

GENE_ORDER = [
    'rsi_period',
    'ma_period',  # Add to order
    # ... other genes
]
```

2. Update [bt_strategy.py](bt_strategy.py) to use the new gene:
```python
def __init__(self):
    self.rsi = bt.indicators.RSI(period=self.params.rsi_period)
    self.ma = bt.indicators.SMA(period=self.params.ma_period)  # New indicator
```

### Using Different Stocks

```python
ga = GeneticAlgorithm(symbol="MSFT", start_date="2015-01-01")
ga.evolve()
```

### Adjusting Evolution Parameters

For faster convergence with smaller populations:
```python
POPULATION_SIZE = 10
NUM_GENERATIONS = 30
ELITISM_COUNT = 3
```

For more exploration:
```python
MUTATION_RATE = 0.25
CROSSOVER_RATE = 0.9
```

## How It Works

1. **Initialization**: Create random population of traders
2. **Evaluation**: Backtest each trader and calculate fitness
3. **Selection**: Select parents using tournament selection
4. **Crossover**: Combine parent genes to create offspring
5. **Mutation**: Randomly modify genes with small probability
6. **Elitism**: Preserve top performers
7. **Repeat**: Steps 2-6 for N generations

## Design Principles

- **Start Simple**: 6 basic genes, 1 stock, RSI strategy
- **Modularity**: Separate concerns (data, genetics, backtesting)
- **Extensibility**: Easy to add genes, indicators, strategies
- **Validation**: All genes checked for valid bounds
- **Reproducibility**: Random seed support for debugging

## Testing

Run the test suite:

```bash
python test_genetic_ops.py
```

This verifies:
- ✓ Crossover produces valid offspring
- ✓ Mutation stays within gene bounds
- ✓ Gene types are preserved
- ✓ All operations are reproducible

## Future Enhancements

- [ ] Multiple indicators (MACD, Bollinger Bands, Moving Averages)
- [ ] Multi-stock portfolio optimization
- [ ] Walk-forward analysis
- [ ] Parallel fitness evaluation
- [ ] Advanced crossover (two-point, gene group preservation)
- [ ] Adaptive mutation rates
- [ ] Strategy visualization and analysis tools
- [ ] Out-of-sample testing automation

## References

- [Backtrader Documentation](https://www.backtrader.com/)
- [Genetic Algorithms Theory](https://en.wikipedia.org/wiki/Genetic_algorithm)
- [RSI Indicator](https://www.investopedia.com/terms/r/rsi.asp)

## License

This is a research/educational project.

## Notes

- This system is for educational purposes only
- Past performance does not guarantee future results
- Always test strategies thoroughly before real trading
- Consider transaction costs, slippage, and market impact
- Be aware of overfitting risks with optimization

---

**Built with evolutionary principles to discover optimal trading strategies** 🧬📈
