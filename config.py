"""
Configuration file for genetic trading algorithm.
Auto-generated from Flutter UI.
"""

# Database configuration
DATABASE_PATH = "/Users/macmini/Dev/Genetic Trader/SPY_Data.db"
TEST_SYMBOL = "AAPL"

# Multi-stock portfolio configuration
USE_PORTFOLIO = True
PORTFOLIO_SIZE = 20
PORTFOLIO_STOCKS = [
]
AUTO_SELECT_PORTFOLIO = True
PORTFOLIO_SECTORS = [
    "Industrials",
]

# Data split configuration
TRAIN_START_DATE = "2016-03-09"
TRAIN_END_DATE = "2024-03-09"
TEST_START_DATE = "2024-03-10"
TEST_END_DATE = "2026-03-06"
USE_OUT_OF_SAMPLE_TEST = True
TRAINING_YEARS = 8

# K-Fold Temporal Cross-Validation
USE_KFOLD_VALIDATION = False
KFOLD_NUM_FOLDS = 2
KFOLD_FOLD_YEARS = 3
KFOLD_ALLOW_OVERLAP = False
KFOLD_WEIGHT_RECENT = False
KFOLD_RECENT_WEIGHT_FACTOR = 1.5
KFOLD_MIN_BARS_PER_FOLD = 200

# Genetic algorithm configuration
POPULATION_SIZE = 30
NUM_GENERATIONS = 40
MUTATION_RATE = 0.2
CROSSOVER_RATE = 0.9
ELITISM_COUNT = 6  # 20.0% of population

# Tournament selection
TOURNAMENT_SIZE = 4

# Gene definitions and bounds
# Each gene is defined as: (min_value, max_value, data_type)
GENE_DEFINITIONS = {
    # Moving Average Strategy genes
    'ma_short_period': (5, 30, int),      # Short MA period (fast signal)
    'ma_long_period': (30, 100, int),     # Long MA period (slow signal)
    'ma_type': (0, 1, int),                # 0 = SMA, 1 = EMA

    # Risk Management genes
    'stop_loss_pct': (1.0, 10.0, float),
    'take_profit_pct': (2.0, 15.0, float),
    'position_size_pct': (5.0, 25.0, float),

    # Macroeconomic Context genes
    'macro_enabled': (0, 1, int),
    'macro_weight': (0.0, 1.0, float),
    'macro_vix_threshold': (15.0, 50.0, float),
    'macro_vix_position_scale': (0.2, 1.0, float),
    'macro_yc_threshold': (-1.0, 1.0, float),
    'macro_yc_action': (0, 2, int),
    'macro_rate_threshold': (1.0, 8.0, float),
    'macro_rate_position_scale': (0.3, 1.0, float),
    'macro_cpi_threshold': (2.0, 8.0, float),
    'macro_cpi_position_scale': (0.3, 1.0, float),
    'macro_unemp_threshold': (4.0, 10.0, float),
    'macro_unemp_action': (0, 2, int),
    'macro_risk_stop_adj': (0.5, 2.0, float),
    'macro_risk_tp_adj': (0.5, 2.0, float),
    'macro_regime_count_req': (1, 4, int),
}

# Gene order in chromosome (important for consistency)
GENE_ORDER = [
    'ma_short_period',
    'ma_long_period',
    'ma_type',
    'stop_loss_pct',
    'take_profit_pct',
    'position_size_pct',
    'macro_enabled',
    'macro_weight',
    'macro_vix_threshold',
    'macro_vix_position_scale',
    'macro_yc_threshold',
    'macro_yc_action',
    'macro_rate_threshold',
    'macro_rate_position_scale',
    'macro_cpi_threshold',
    'macro_cpi_position_scale',
    'macro_unemp_threshold',
    'macro_unemp_action',
    'macro_risk_stop_adj',
    'macro_risk_tp_adj',
    'macro_regime_count_req',
]

# Macroeconomic data configuration
USE_MACRO_DATA = True
MACRO_DATA_TABLE = 'macro_indicators'

# Technical indicator filter configuration
USE_TECHNICAL_INDICATORS = False

# Ensemble signal configuration
USE_ENSEMBLE_SIGNALS = False

# Backtesting configuration
BACKTESTING_ENGINE = 'tradix'
DATA_SOURCE = 'yahoo'
INITIAL_CASH = 100000.0
COMMISSION = 0.001  # 0.1% commission per trade

# Portfolio initial allocation (only applies when USE_PORTFOLIO = True)
# Percentage of capital to allocate equally across all stocks at start
# Remaining percentage stays as cash for strategy signals
# Example: 80.0 means 80% divided equally among stocks, 20% reserved for trading
INITIAL_ALLOCATION_PCT = 80.0  # Range: 0.0 to 100.0

# Fitness function weights
FITNESS_WEIGHTS = {
    'total_return': 0.4,
    'sharpe_ratio': 0.24,
    'max_drawdown': 0.24,
    'win_rate': 0.12,
}

# Minimum trades required for valid fitness
MIN_TRADES_REQUIRED = 5

# Logging configuration
LOG_LEVEL = "INFO"
LOG_EVERY_N_GENERATIONS = 1
SAVE_BEST_EVERY_N_GENERATIONS = 10

# Output paths
RESULTS_DIR = "results"
LOGS_DIR = "logs"
CHECKPOINT_DIR = "checkpoints"

# Random seed for reproducibility (set to None for random)
RANDOM_SEED = 42

# Advanced gene group flags
USE_ADVANCED_OSCILLATORS = False
USE_TREND_SIGNALS = False
USE_VOLUME_SIGNALS = False
USE_VOLATILITY_BREAKOUT = False
USE_SUPPORT_RESISTANCE = False
USE_REGIME_DETECTION = False
USE_ADVANCED_SIZING = False

# Performance optimization
USE_PARALLEL_EVALUATION = True  # Use multiprocessing for fitness evaluation
MAX_PARALLEL_WORKERS = None     # None = use all CPU cores, or specify number
