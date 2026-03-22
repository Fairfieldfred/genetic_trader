# Phase 1 Spec: vectorbt Fitness Evaluator

**Goal:** Replace `PortfolioFitnessEvaluator` (backtrader) with a vectorbt-based evaluator
that supports population-level batch evaluation. Target: 10–20x speedup per generation
with identical fitness scores and same public interface.

**Scope:** 6 core genes only (MA strategy + risk management). Macro, TI filter, and
ensemble genes are Phase 3. When those genes are non-zero in a chromosome, Phase 1
gracefully ignores them (they evaluate with neutral modifier = as if disabled).

---

## 1. New File: `vectorbt_fitness.py`

Create alongside `portfolio_fitness.py`. Zero changes to existing files in Phase 1
except `evolve.py` and `config.py` (see §6).

---

## 2. Dependencies

vectorbt must be installed in the project venv:

```bash
cd "/Users/macmini/Dev/Genetic Trader"
source .venv/bin/activate
pip install vectorbt
```

vectorbt pulls in: `pandas`, `numpy`, `numba`, `scipy`, `statsmodels`, `plotly`.
All already present except `numba` and `plotly` (auto-installed). First run compiles
Numba JIT cache (~30s one-time cost). Subsequent runs use disk cache.

---

## 3. Public Interface (must match `PortfolioFitnessEvaluator` exactly)

```python
class VectorbtFitnessEvaluator:

    def __init__(self, symbols: List[str], start_date: str, end_date: str): ...

    def calculate_fitness(self, trader: GeneticTrader) -> float: ...

    def evaluate_population(self, traders: List[GeneticTrader]) -> List[GeneticTrader]: ...

    def get_detailed_results(self, trader: GeneticTrader) -> Dict[str, Any]: ...

    # Also expose these attrs (used by parallel_fitness._WorkerFunction):
    # self.valid_symbols, self.data_feeds, self.start_date, self.end_date,
    # self.macro_df, self.folds
```

`parallel_fitness.py` is NOT used with the vectorbt evaluator — population-level
batching replaces it. `evaluate_population()` handles the entire population in one
vectorized call internally.

---

## 4. Data Loading (`__init__`)

Reuse the existing data loading logic verbatim — copy from `PortfolioFitnessEvaluator.__init__`:

- Same `DataLoader` / `YahooDataLoader` dispatch on `config.DATA_SOURCE`
- Same `self.data_feeds` dict (`symbol → pd.DataFrame`)
- Same `self.valid_symbols` list
- Same macro data loading (store as `self.macro_df` for future phases; unused in Phase 1)
- Same `self.folds = self._compute_folds()` (copy `_compute_folds()` verbatim)

**After loading**, build one master price DataFrame for vectorbt:

```python
# Stack all stock close prices into a single wide DataFrame:
# rows = DatetimeIndex, columns = symbol strings
self._close = pd.DataFrame({
    sym: df['close']
    for sym, df in self.data_feeds.items()
    if sym in self.valid_symbols
})
self._close.index = pd.to_datetime(self._close.index)
self._close = self._close.sort_index()
self._close = self._close.ffill()   # fill gaps (weekends already absent; handle any NaNs)
```

This `_close` matrix is reused for every fitness evaluation — loaded once, evaluated many times.

---

## 5. Core Simulation: Single Trader

### 5a. Gene extraction

```python
genes = trader.get_genes()
short = int(genes['ma_short_period'])   # 5–30
long_  = int(genes['ma_long_period'])   # 30–100
ma_type = int(genes['ma_type'])         # 0=SMA, 1=EMA
sl_stop = float(genes['stop_loss_pct']) / 100      # e.g. 0.025
tp_stop = float(genes['take_profit_pct']) / 100    # e.g. 0.050
position_size_pct = float(genes['position_size_pct']) / 100  # e.g. 0.10
```

### 5b. MA computation

```python
import vectorbt as vbt

if ma_type == 0:
    fast_ma = vbt.MA.run(self._close, window=short, ewm=False)
    slow_ma = vbt.MA.run(self._close, window=long_, ewm=False)
else:
    fast_ma = vbt.MA.run(self._close, window=short, ewm=True)
    slow_ma = vbt.MA.run(self._close, window=long_, ewm=True)
```

`vbt.MA.run()` computes the MA for all columns (stocks) simultaneously using
Numba-compiled rolling functions. Returns a `MA` accessor with `.ma` attribute
(same shape as `self._close`).

### 5c. Signal generation

```python
entries = fast_ma.ma_crossed_above(slow_ma.ma)   # bullish crossover → buy
exits   = fast_ma.ma_crossed_below(slow_ma.ma)   # bearish crossover → sell
```

Both are boolean DataFrames, same shape as `self._close`. vectorbt's
`ma_crossed_above()` is Numba-compiled.

### 5d. Portfolio simulation

```python
pf = vbt.Portfolio.from_signals(
    close=self._close,
    entries=entries,
    exits=exits,
    sl_stop=sl_stop,          # stop-loss as fraction (e.g. 0.025 = 2.5%)
    tp_stop=tp_stop,          # take-profit as fraction (e.g. 0.05 = 5%)
    size=position_size_pct,   # fraction of current cash per trade
    size_type='valuepercent', # size is % of portfolio value
    init_cash=config.INITIAL_CASH / len(self.valid_symbols),  # equal split
    fees=config.COMMISSION,
    freq='D',
    call_seq='auto',
)
```

**Notes on parameters:**
- `sl_stop` / `tp_stop` are fractions (not percentages) — divide gene values by 100
- `size_type='valuepercent'` matches backtrader's `position_size_pct` behavior (% of available cash)
- `init_cash` split per-symbol matches backtrader's per-stock capital allocation
- `freq='D'` tells vectorbt this is daily data (needed for Sharpe annualization)
- `call_seq='auto'` lets vectorbt decide execution order (sufficient for Phase 1)

### 5e. Metric extraction

```python
# Per-column (per-stock) then aggregate
total_return  = pf.total_return().mean() * 100          # average % return across stocks
sharpe_ratio  = pf.sharpe_ratio().mean()                # average Sharpe across stocks
max_drawdown  = -pf.max_drawdown().mean() * 100         # negate (drawdown is negative)
trade_records = pf.trades.records_readable              # all trades as DataFrame
total_trades  = len(trade_records)
won_trades    = (trade_records['PnL'] > 0).sum()
win_rate      = (won_trades / total_trades * 100) if total_trades > 0 else 0.0

# Clamp Sharpe to same range as backtrader evaluator
sharpe_ratio = max(-5.0, min(5.0, float(sharpe_ratio)))
```

### 5f. Fitness scoring (identical formula to existing)

```python
def _score_results(self, results: dict) -> float:
    if results['trade_count'] < config.MIN_TRADES_REQUIRED:
        return -100.0
    fitness = (
        config.FITNESS_WEIGHTS['total_return']  * results['total_return'] +
        config.FITNESS_WEIGHTS['sharpe_ratio']  * results['sharpe_ratio'] * 10 +
        config.FITNESS_WEIGHTS['max_drawdown']  * results['max_drawdown'] +
        config.FITNESS_WEIGHTS['win_rate']      * results['win_rate']
    )
    return fitness
```

Exact copy from `PortfolioFitnessEvaluator._score_results()`. Do not change.

---

## 6. Population-Level Batch Evaluation (the big win)

This is the architectural difference from Phase 1. Instead of 30 sequential
(or multiprocessed) backtrader runs, evaluate all traders in the population
in one vectorized pass.

### 6a. Strategy: MA parameter deduplication + column stacking

With 30 traders, many will share similar MA periods (the GA converges). We exploit
this by computing MAs once per unique parameter combination and stacking results.

```python
def evaluate_population(self, traders: List[GeneticTrader]) -> List[GeneticTrader]:
    # Step 1: Extract unique (short, long, ma_type) combinations
    param_triples = [
        (int(t.get_genes()['ma_short_period']),
         int(t.get_genes()['ma_long_period']),
         int(t.get_genes()['ma_type']))
        for t in traders
    ]
    unique_params = list(set(param_triples))

    # Step 2: Batch-compute all MAs in one vbt.MA.run() call
    # vbt supports multiple window values: pass a list → returns stacked columns
    # Each unique (short, long, ma_type) needs its own run, but we can group by ma_type

    sma_params = [(s, l) for s, l, t in unique_params if t == 0]
    ema_params = [(s, l) for s, l, t in unique_params if t == 1]

    # vbt.MA.run with multiple windows returns MultiIndex columns:
    # (window_value, symbol) — processed in one Numba pass
    ma_cache = {}

    if sma_params:
        short_windows = sorted(set(s for s, l in sma_params))
        long_windows  = sorted(set(l for s, l in sma_params))
        fast_smas = vbt.MA.run(self._close, window=short_windows, ewm=False)
        slow_smas = vbt.MA.run(self._close, window=long_windows,  ewm=False)
        ma_cache['sma'] = (fast_smas, slow_smas)

    if ema_params:
        short_windows = sorted(set(s for s, l in ema_params))
        long_windows  = sorted(set(l for s, l in ema_params))
        fast_emas = vbt.MA.run(self._close, window=short_windows, ewm=True)
        slow_emas = vbt.MA.run(self._close, window=long_windows,  ewm=True)
        ma_cache['ema'] = (fast_emas, slow_emas)

    # Step 3: For each trader, extract pre-computed signals and run portfolio
    for trader in traders:
        genes = trader.get_genes()
        short = int(genes['ma_short_period'])
        long_ = int(genes['ma_long_period'])
        ma_type = int(genes['ma_type'])
        sl  = float(genes['stop_loss_pct'])   / 100
        tp  = float(genes['take_profit_pct']) / 100
        sz  = float(genes['position_size_pct']) / 100

        key = 'sma' if ma_type == 0 else 'ema'
        fast_ma_all, slow_ma_all = ma_cache[key]

        # Select the column for this trader's specific window values
        fast_ma = fast_ma_all[short]   # DataFrame of shape (dates, symbols)
        slow_ma = slow_ma_all[long_]

        entries = fast_ma.vbt.crossed_above(slow_ma)
        exits   = fast_ma.vbt.crossed_below(slow_ma)

        pf = vbt.Portfolio.from_signals(
            close=self._close,
            entries=entries,
            exits=exits,
            sl_stop=sl,
            tp_stop=tp,
            size=sz,
            size_type='valuepercent',
            init_cash=config.INITIAL_CASH / len(self.valid_symbols),
            fees=config.COMMISSION,
            freq='D',
        )

        results = self._extract_results(pf)
        trader.set_fitness(self._score_results(results))

    return traders
```

**Why this is fast:**
- `vbt.MA.run(close, window=[5,8,10,14,20])` computes 5 different MAs for all
  stocks in a single Numba pass — no Python loops
- The MA computation is amortized across the entire population, not repeated per trader
- `from_signals()` with stop-loss/take-profit is a single Numba simulation pass
  per unique (short, long, sl, tp, sz) combination

### 6b. Further optimization (optional, not required for Phase 1)

If all traders in a generation converge to a small set of unique chromosomes,
you can deduplicate on the full 5-tuple `(short, long, ma_type, sl, tp)` and skip
re-running identical traders. Add this as an optional flag: `VECTORBT_DEDUP = True`.

---

## 7. K-Fold Support

Copy `_compute_folds()` from `PortfolioFitnessEvaluator` verbatim.

For K-fold in the vectorbt evaluator, slice `self._close` by date range:

```python
def _run_backtest(self, trader, close_slice):
    # close_slice is a date-filtered version of self._close
    genes = trader.get_genes()
    # ... same signal generation and portfolio.from_signals() as above
    # but operating on close_slice instead of self._close

def calculate_fitness(self, trader):
    if len(self.folds) == 1:
        results = self._run_backtest(trader, self._close)
        return self._score_results(results)

    fold_scores = []
    for fold_idx, (fold_start, fold_end) in enumerate(self.folds):
        close_slice = self._close.loc[fold_start:fold_end]
        if len(close_slice) < config.KFOLD_MIN_BARS_PER_FOLD:
            continue
        results = self._run_backtest(trader, close_slice)
        fold_scores.append((fold_idx, self._score_results(results)))

    if not fold_scores:
        return -100.0
    return self._aggregate_fold_scores(fold_scores)
```

`_aggregate_fold_scores()` — copy verbatim from `PortfolioFitnessEvaluator`.

---

## 8. `get_detailed_results()` Return Shape

Must match the existing shape so the Flutter UI and `evolve.py` logging work unchanged:

```python
{
    'starting_value':         float,
    'ending_value':           float,
    'total_return':           float,   # percent
    'sharpe_ratio':           float,
    'max_drawdown':           float,   # negative percent (e.g. -15.3)
    'win_rate':               float,   # percent (e.g. 54.2)
    'trade_count':            int,
    'winning_trades':         int,
    'per_stock_performance':  {
        symbol: {
            'trades': int,
            'won':    int,
            'lost':   int,
            'pnl':    float,
            'win_rate': float,
        }
    },
    'genes':    dict,         # trader.get_genes()
    'fitness':  float,
    'num_stocks': int,
    'symbols':  list[str],
    # kfold_results key added only when USE_KFOLD_VALIDATION=True
}
```

For `per_stock_performance`, extract from `pf.trades.records_readable` grouped by
the column index (symbol name):

```python
per_stock = {}
trades_df = pf.trades.records_readable
for symbol in self.valid_symbols:
    sym_trades = trades_df[trades_df['Column'] == symbol]
    won = (sym_trades['PnL'] > 0).sum()
    total = len(sym_trades)
    per_stock[symbol] = {
        'trades': total,
        'won': int(won),
        'lost': int(total - won),
        'pnl': round(float(sym_trades['PnL'].sum()), 2),
        'win_rate': (won / total * 100) if total > 0 else 0.0,
    }
```

---

## 9. Config Changes

### `config.py` — one new key

```python
# Backtesting engine: 'backtrader' | 'vectorbt'
BACKTESTING_ENGINE = 'vectorbt'
```

(The existing `BACKTESTING_ENGINE = 'backtrader'` line is already in config.py — just change the value.)

### `evolve.py` — evaluator dispatch

Find the evaluator instantiation block in `evolve.py` (inside `GeneticAlgorithm.__init__`
or `run()`) and add a dispatch:

```python
engine = getattr(config, 'BACKTESTING_ENGINE', 'backtrader')

if engine == 'vectorbt':
    from vectorbt_fitness import VectorbtFitnessEvaluator
    self.evaluator = VectorbtFitnessEvaluator(
        symbols=symbols,
        start_date=self.start_date,
        end_date=self.end_date,
    )
else:
    from portfolio_fitness import PortfolioFitnessEvaluator
    self.evaluator = PortfolioFitnessEvaluator(
        symbols=symbols,
        start_date=self.start_date,
        end_date=self.end_date,
    )
```

And in the generation loop, replace `parallel_evaluator.evaluate_population()` with
`self.evaluator.evaluate_population()` — vectorbt handles batching internally, no
`ParallelFitnessEvaluator` wrapper needed.

The existing `USE_PARALLEL_EVALUATION` flag is **ignored** when using vectorbt (batch
is handled internally). Add a note in config:

```python
# Note: USE_PARALLEL_EVALUATION is ignored when BACKTESTING_ENGINE='vectorbt'
# (population-level batching is handled internally by VectorbtFitnessEvaluator)
USE_PARALLEL_EVALUATION = True
```

---

## 10. Behavioral Differences to Document

These are intentional and acceptable trade-offs for Phase 1:

| Behavior | backtrader | vectorbt Phase 1 |
|---|---|---|
| Macro gene modifiers | Applied per-bar | Ignored (neutral) |
| TI filter genes | Applied per-bar | Ignored (neutral) |
| Ensemble signal genes | Applied per-bar | Ignored (neutral) |
| Initial allocation | Equal-$ buy on day 1 | Not implemented (position sizing handles allocation) |
| Commission model | Per-trade flat rate | Per-trade flat rate (same) |
| Stop-loss trigger | Next bar open | Same bar close (vectorbt default) |
| Sharpe annualization | 252 trading days | 252 trading days via `freq='D'` |
| Fitness formula | Exact | Exact copy |
| K-fold | Supported | Supported |

The stop-loss trigger timing difference (next-bar vs same-bar) will produce slightly
different trade counts and returns. This is acceptable — the fitness ranking will be
consistent, just not byte-for-byte identical to backtrader. Document this in code comments.

---

## 11. Testing Strategy

### Unit test: `test_vectorbt_fitness.py`

```python
# Test 1: Single trader fitness returns a float
# Test 2: Fitness score is within plausible range (-1000 to 1000)
# Test 3: evaluate_population() returns all traders with non-None fitness
# Test 4: Same trader evaluated twice returns same fitness (determinism)
# Test 5: Trader with very short MA periods (5/30) doesn't crash
# Test 6: Fitness function weights produce correct output (unit test _score_results)
# Test 7: K-fold returns aggregated score (when USE_KFOLD_VALIDATION=True)
```

### Benchmark test: `benchmark_vectorbt.py`

```python
# Compare:
# 1. Time for backtrader.evaluate_population(30 traders)
# 2. Time for vectorbt.evaluate_population(30 traders)
# Print speedup ratio and assert vectorbt is at least 5x faster
```

### Regression test: fitness ranking consistency

Run both evaluators on the same 10 traders. Verify that the **rank ordering** of
traders by fitness score is the same (or very close) between the two engines.
Exact values will differ due to stop-loss timing difference; ranking should agree.

---

## 12. File Checklist

```
New files:
  vectorbt_fitness.py         ← main deliverable
  test_vectorbt_fitness.py    ← unit tests
  benchmark_vectorbt.py       ← timing comparison

Modified files:
  config.py                   ← BACKTESTING_ENGINE = 'vectorbt'
  evolve.py                   ← evaluator dispatch block
  CLAUDE.md                   ← add vectorbt to dependencies + file map
```

No changes to: `bt_strategy.py`, `portfolio_fitness.py`, `parallel_fitness.py`,
`genetic_trader.py`, `genetic_ops.py`, `population.py`, `data_loader.py`.

---

## 13. Implementation Order

1. `pip install vectorbt` → verify import works in `.venv`
2. Write `vectorbt_fitness.py` § 4 (data loading) → verify `_close` shape
3. Add `_run_backtest()` § 5 → verify single trader returns reasonable numbers
4. Add `calculate_fitness()` single-fold path → compare to backtrader on same trader
5. Add `evaluate_population()` batch path § 6 → verify all traders get fitness
6. Add K-fold path § 7
7. Add `get_detailed_results()` § 8
8. Wire `config.py` + `evolve.py` § 9
9. Write and run `test_vectorbt_fitness.py`
10. Run `benchmark_vectorbt.py` — confirm 10x+ speedup
11. Full evolution run: `python evolve.py` — confirm it runs to completion

---

## 14. Expected Outcome

After Phase 1 a full 40-generation evolution run (30 traders × 40 generations = 1,200
evaluations) on the Mac mini's Apple Silicon should drop from ~20–40 minutes to
~2–5 minutes — a 10–15x improvement — with identical fitness formula, K-fold support,
and zero changes to the genetic algorithm or Flutter UI.
```
