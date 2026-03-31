# Dart Build Plan — Genetic Trader App

## Executive Summary

Port the entire Python backend (data loading, backtesting, genetic algorithm) to
pure Dart, keeping the existing Flutter UI intact.  The Python bridge
(`python_bridge.dart`) becomes a native Dart `EvolutionService` backed by
Dart `Isolate`s.  No Python dependency at runtime.

---

## Goals

1. Fetch historical OHLCV data from Yahoo Finance (HTTP, no API key)
2. Store data in a local SQLite database (sqflite — already in pubspec)
3. Support Dow Jones (30), S&P 500 (~503), and Nasdaq-100 (100) universes
4. Implement a lightweight Dart backtester (Tradix-style event-driven loop)
5. Port the genetic algorithm (population, selection, crossover, mutation, fitness)
6. Wire it all back to the existing Flutter screens via Provider
7. 80%+ unit test coverage on every non-UI layer; TDD where possible

---

## Architecture

```
genetic_trader_ui/
├── lib/
│   ├── main.dart                        (unchanged)
│   ├── core/
│   │   ├── models/
│   │   │   ├── bar.dart                 OHLCV bar
│   │   │   ├── stock.dart               Symbol metadata
│   │   │   ├── trade.dart               Completed trade record
│   │   │   ├── portfolio_state.dart     Cash + positions snapshot
│   │   │   ├── backtest_result.dart     Sharpe, drawdown, return, trades
│   │   │   ├── chromosome.dart          Gene map + gene definitions
│   │   │   └── evolution_result.dart    (extend existing model)
│   │   ├── services/
│   │   │   ├── yahoo_finance_service.dart   HTTP fetch + parse
│   │   │   ├── index_service.dart           DJIA / SP500 / Nasdaq tickers
│   │   │   ├── database_service.dart        SQLite CRUD (sqflite)
│   │   │   └── data_sync_service.dart       Orchestrate fetch → store
│   │   ├── backtesting/
│   │   │   ├── backtester.dart          Event-driven bar loop
│   │   │   ├── ma_strategy.dart         MA-crossover strategy
│   │   │   ├── indicators.dart          SMA, EMA, RSI, MACD, BB, ATR
│   │   │   └── performance.dart         Sharpe, max-drawdown, CAGR, win-rate
│   │   └── genetic/
│   │       ├── gene_definitions.dart    GeneRange, GeneType
│   │       ├── population.dart          Init, select, evolve helpers
│   │       ├── operators.dart           Tournament select, uniform crossover, mutate
│   │       ├── fitness_evaluator.dart   Runs backtester per chromosome
│   │       └── evolution_engine.dart    Main GA loop (runs in Isolate)
│   ├── models/                          (existing — keep as-is)
│   ├── services/
│   │   ├── evolution_service.dart       NEW: replaces python_bridge.dart
│   │   └── results_service.dart         (existing — keep as-is)
│   ├── viewmodels/                      (existing — minimal changes)
│   ├── views/                           (existing — unchanged)
│   └── utils/                           (existing — unchanged)
└── test/
    ├── core/
    │   ├── models/                      unit tests for each model
    │   ├── services/
    │   │   ├── yahoo_finance_service_test.dart
    │   │   ├── index_service_test.dart
    │   │   └── database_service_test.dart
    │   ├── backtesting/
    │   │   ├── indicators_test.dart
    │   │   ├── backtester_test.dart
    │   │   └── performance_test.dart
    │   └── genetic/
    │       ├── chromosome_test.dart
    │       ├── operators_test.dart
    │       └── fitness_evaluator_test.dart
    └── widget_test.dart                 (existing)
```

---

## Technology Decisions

### Yahoo Finance (no API key)
- Endpoint: `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=10y`
- Returns JSON with timestamps + OHLCV arrays
- Parse with `dart:convert` — no external package needed
- Rate-limit: serial fetching with 300 ms delay between symbols
- Cache: store in SQLite; skip re-fetch if last_updated < 24h

### Index Constituents
- Hardcode the tickers as `const List<String>` in `index_service.dart`
- DJIA: 30 tickers (stable, update rarely)
- S&P 500: 503 tickers (sourced from Wikipedia table, baked in at build time)
- Nasdaq-100: 100 tickers (same approach)
- Provide a refresh path: `IndexService.fetchLive()` scrapes Wikipedia HTML as a fallback

### Database (SQLite via sqflite)
Tables:
```sql
CREATE TABLE stocks (
  symbol TEXT PRIMARY KEY,
  name TEXT,
  sector TEXT,
  index_membership TEXT   -- comma-sep: "SP500,NASDAQ100"
);

CREATE TABLE bars (
  symbol TEXT,
  date TEXT,        -- ISO-8601 YYYY-MM-DD
  open REAL,
  high REAL,
  low REAL,
  close REAL,
  volume INTEGER,
  adj_close REAL,
  PRIMARY KEY (symbol, date)
);

CREATE TABLE indicators (
  symbol TEXT,
  date TEXT,
  sma_20 REAL, sma_50 REAL, sma_200 REAL,
  ema_12 REAL, ema_26 REAL,
  rsi_14 REAL,
  macd REAL, macd_signal REAL, macd_hist REAL,
  bb_upper REAL, bb_middle REAL, bb_lower REAL,
  atr_14 REAL,
  adx_14 REAL,
  PRIMARY KEY (symbol, date)
);

CREATE TABLE evolution_runs (
  run_id TEXT PRIMARY KEY,
  created_at TEXT,
  config_json TEXT,
  status TEXT,   -- running | complete | failed
  best_fitness REAL,
  best_chromosome_json TEXT,
  summary_json TEXT
);
```

### Backtester (Tradix-style)
- Event-driven bar loop over a `List<Bar>` (already sorted ascending)
- Strategy interface: `void onBar(Bar bar, PortfolioState state, List<Order> orders)`
- Order types: `MarketOrder`, `StopOrder` (simulated on next bar open)
- Commission: flat percentage per trade
- Position sizing: percentage of portfolio value
- No external dependency — pure Dart, ~300 lines

### Genetic Algorithm
Mirrors the Python implementation:
- Chromosome = `Map<String, double>` (gene name → value)
- Population = `List<Chromosome>`
- Selection: tournament (k=4)
- Crossover: uniform (per-gene coin flip)
- Mutation: Gaussian perturbation clipped to gene range
- Elitism: top N% survive unchanged
- Fitness = weighted combo of Sharpe, total return, max drawdown, win rate
- Parallelism: run fitness evaluations in `Isolate.run()` batches

---

## Implementation Phases

### Phase 1 — Core Models + Database (TDD)
Write tests FIRST, then implement:
- `Bar`, `Stock`, `Trade`, `PortfolioState`, `BacktestResult`
- `DatabaseService` (CRUD + migrations)
- `IndexService` (hardcoded lists + Wikipedia scrape)
- Target: all model/service tests green

### Phase 2 — Yahoo Finance Data Layer
- `YahooFinanceService.fetchHistory(symbol, period)`
- `DataSyncService.syncIndex(IndexType, {onProgress})` 
- Tests: mock HTTP, verify parse, verify DB upsert
- Target: can download all 30 DJIA tickers into SQLite

### Phase 3 — Technical Indicators
- `indicators.dart`: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ADX
- All indicators computed from a `List<Bar>` → returns parallel `List<double>`
- Tests: verify against known values from Python/pandas reference calculations

### Phase 4 — Backtester + Performance
- `Backtester.run(strategy, bars, config)` → `BacktestResult`
- `MaStrategy`: MA crossover with stop-loss, take-profit, position sizing
- `performance.dart`: sharpeRatio, maxDrawdown, cagr, winRate
- Tests: deterministic fixture data, verify trades and metrics

### Phase 5 — Genetic Algorithm Engine
- `GeneDefinitions` with same ranges as Python config
- `PopulationManager`: init, evaluate, evolve
- `FitnessEvaluator`: wraps backtester, returns scalar fitness
- `EvolutionEngine.run(config, {onGeneration})` → runs in `Isolate`
- Tests: small population (5) over 3 generations on fixture data, verify convergence

### Phase 6 — Wire to Flutter UI
- `EvolutionService` — drop-in replacement for `PythonBridge`
  - Emits same `EvolutionProgress` stream
  - Exposes `start()`, `stop()`, `resume(runId)`
- Update `EvolutionViewModel` to use `EvolutionService`
- Add **Index Picker** to Config screen (DJIA / SP500 / Nasdaq-100)
- Add **Data Sync** screen/dialog (progress bar per symbol)
- Wire results storage to `evolution_runs` SQLite table
- Target: full end-to-end run without touching Python

### Phase 7 — Polish + Final Tests
- Integration test: full 10-generation run on DJIA data
- Widget tests for new UI components
- Performance profiling: aim for <2s per generation on 30-stock portfolio
- README update

---

## New Dependencies to Add (pubspec.yaml)

```yaml
dependencies:
  # already present: flutter, provider, fl_chart, sqflite, http, intl, path_provider
  sqlite3_flutter_libs: ^0.5.0   # native SQLite on desktop/mobile
  mocktail: ^1.0.0               # dev — cleaner mocks than mockito

dev_dependencies:
  # already present: flutter_test, flutter_lints
  mocktail: ^1.0.0
  test: ^1.25.0                  # pure dart test runner (for core/ isolate tests)
```

---

## Testing Strategy

- **Unit tests** for every function in `core/` — no Flutter dependency
- **Golden mocks** for HTTP calls (no real network in CI)
- **Fixture data** for backtester: 100 synthetic bars with known MA crossovers
- **Property tests** for GA operators: crossover child genes always within parent bounds
- Run with: `flutter test` (all) or `dart test test/core/` (no Flutter harness needed)
- Minimum coverage target: **80%** across `core/`

---

## File Creation Order (for Claude Code agent)

1. `test/core/models/*_test.dart` → `lib/core/models/*.dart`
2. `test/core/services/database_service_test.dart` → `lib/core/services/database_service.dart`
3. `test/core/services/index_service_test.dart` → `lib/core/services/index_service.dart`
4. `test/core/services/yahoo_finance_service_test.dart` → `lib/core/services/yahoo_finance_service.dart`
5. `lib/core/services/data_sync_service.dart`
6. `test/core/backtesting/indicators_test.dart` → `lib/core/backtesting/indicators.dart`
7. `test/core/backtesting/backtester_test.dart` → `lib/core/backtesting/backtester.dart`  
   + `lib/core/backtesting/ma_strategy.dart`
8. `test/core/backtesting/performance_test.dart` → `lib/core/backtesting/performance.dart`
9. `test/core/genetic/chromosome_test.dart` → `lib/core/genetic/gene_definitions.dart` + `chromosome.dart`
10. `test/core/genetic/operators_test.dart` → `lib/core/genetic/operators.dart` + `population.dart`
11. `test/core/genetic/fitness_evaluator_test.dart` → `lib/core/genetic/fitness_evaluator.dart`
12. `lib/core/genetic/evolution_engine.dart`
13. `lib/services/evolution_service.dart` (replaces python_bridge.dart)
14. Update `pubspec.yaml`
15. Update viewmodels + views to wire new service
16. Final integration test

---

## Key Constraints

- **Keep `python_bridge.dart` intact** until Phase 6 is proven green; rename to `python_bridge_legacy.dart`
- **Never hardcode absolute paths** — use `path_provider` for DB location
- **Respect Yahoo Finance rate limits** — add 300ms delay between symbol fetches
- **Gene definitions must match Python** exactly (same ranges) for result comparability
- **EvolutionProgress** model must remain API-compatible with existing viewmodels

---

*Generated: 2026-03-29*
