"""
Trend-following genome experiment (absolute-return objective).

Hypothesis (from the allocation-drag diagnostic): 99% of the ~24-pt OOS gap to
buy-and-hold is signal quality. Crossover + ensemble signals are mean-reversion-
flavored and fight a rising market (sell winners, sit out rallies). TREND-FOLLOWING
DNA — stay long while the trend persists — should capture more of a bull move.

Arms (identical seed/init pop, fixed train basket, 6 held-out test baskets,
absolute-return fitness weights, judged on RAW OOS return):
  1. CORE_MA       6-gene MA crossover
  2. ENSEMBLE      core + 13 ensemble signal genes (ensemble_enabled forced ON)
  3. TREND_FOLLOW  core + trend_follow_enabled(ON) + tf_sma_period + tf_momentum_period
"""
import random
import numpy as np

import config
config.BACKTESTING_ENGINE = 'vectorbt'
config.USE_KFOLD_VALIDATION = False
config.VECTORBT_DEDUP = True
config.FITNESS_WEIGHTS = {
    'total_return': 0.85, 'sharpe_ratio': 0.05,
    'max_drawdown': 0.05, 'win_rate': 0.05,
}

from genetic_trader import GeneticTrader
from population import Population
from vectorbt_fitness import VectorbtFitnessEvaluator
from portfolio_fitness import select_random_portfolio

POP, GENS, SEED = 30, 25, 42
UNIVERSE_SIZE = 40
BASKET_SIZE = 15
N_TEST_BASKETS = 6

CORE_GENES = dict(config.GENE_DEFINITIONS)
CORE_ORDER = list(config.GENE_ORDER)

ENSEMBLE_GENES = {
    'ensemble_enabled': (1, 1, int),
    'sig_ma_weight': (0.0, 1.0, float), 'sig_bb_weight': (0.0, 1.0, float),
    'sig_stoch_weight': (0.0, 1.0, float), 'sig_macd_weight': (0.0, 1.0, float),
    'sig_rsi_weight': (0.0, 1.0, float), 'sig_buy_threshold': (0.1, 0.8, float),
    'sig_sell_threshold': (-0.8, -0.1, float), 'sig_bb_period_idx': (0, 2, int),
    'sig_stoch_ob': (70, 90, int), 'sig_stoch_os': (10, 30, int),
    'sig_rsi_ob': (60, 85, int), 'sig_rsi_os': (15, 40, int),
}

TREND_GENES = {
    'trend_follow_enabled': (1, 1, int),     # forced ON to isolate
    'tf_sma_period': (20, 150, int),         # trend filter SMA length
    'tf_momentum_period': (10, 100, int),    # momentum lookback
}

GENOMES = {
    'CORE_MA': {},
    'ENSEMBLE': ENSEMBLE_GENES,
    'TREND_FOLLOW': TREND_GENES,
}


def seed_all(s):
    random.seed(s); np.random.seed(s)


def set_genome(extra):
    if extra:
        merged = dict(CORE_GENES); merged.update(extra)
        config.GENE_DEFINITIONS = merged
        config.GENE_ORDER = CORE_ORDER + list(extra.keys())
    else:
        config.GENE_DEFINITIONS = dict(CORE_GENES)
        config.GENE_ORDER = list(CORE_ORDER)


def run_arm(extra, basket, train_eval):
    set_genome(extra)
    config.USE_EXCESS_RETURN_FITNESS = False
    config.INITIAL_ALLOCATION_PCT = 80.0
    seed_all(SEED)
    train_eval.set_active_basket(basket)
    pop = Population(size=POP)
    for gen in range(GENS):
        train_eval.evaluate_population(pop.traders)
        if gen < GENS - 1:
            pop.evolve_generation()
    return pop.get_best_trader()


def oos_raw(champ, test_eval, test_baskets):
    out = []
    for b in test_baskets:
        test_eval.set_active_basket(b)
        out.append(test_eval.get_detailed_results(champ)['total_return'])
    return out


def main():
    print("TREND-FOLLOWING EXPERIMENT (absolute-return objective)")
    print(f"Fitness weights: {config.FITNESS_WEIGHTS}\n")
    seed_all(SEED)
    universe = select_random_portfolio(size=UNIVERSE_SIZE, seed=SEED, sectors=None)
    train_eval = VectorbtFitnessEvaluator(symbols=universe,
        start_date=config.TRAIN_START_DATE, end_date=config.TRAIN_END_DATE)
    universe = list(train_eval.valid_symbols)
    test_eval = VectorbtFitnessEvaluator(symbols=universe,
        start_date=config.TEST_START_DATE, end_date=config.TEST_END_DATE)
    test_universe = list(test_eval.valid_symbols)

    train_basket = universe[:BASKET_SIZE]
    tb_rng = random.Random(SEED + 999)
    test_baskets = [tb_rng.sample(test_universe, BASKET_SIZE) for _ in range(N_TEST_BASKETS)]

    bh = []
    for b in test_baskets:
        test_eval.set_active_basket(b)
        bh.append(test_eval._benchmark_return(test_eval._close))
    bh_mean, bh_med = float(np.mean(bh)), float(np.median(bh))

    out = {}
    for label, extra in GENOMES.items():
        champ = run_arm(extra, train_basket, train_eval)
        g = champ.get_genes()
        out[label] = oos_raw(champ, test_eval, test_baskets)
        extra_str = ""
        if label == 'TREND_FOLLOW':
            extra_str = f" tf_sma={g['tf_sma_period']} tf_mom={g['tf_momentum_period']}"
        print(f"  {label:13} ({len(g):2d} genes) train_fit={champ.fitness:.2f}{extra_str}")

    print("\n" + "=" * 76)
    print(f"OUT-OF-SAMPLE raw return (%) across {N_TEST_BASKETS} baskets  |  "
          f"B&H mean={bh_mean:.2f}% median={bh_med:.2f}%")
    print("=" * 76)
    print(f"{'arm':14}{'mean':>9}{'median':>9}{'min':>9}{'max':>9}{'beatB&H':>9}")
    for label in GENOMES:
        r = np.array(out[label])
        beats = int((r > np.array(bh)).sum())
        print(f"{label:14}{r.mean():>9.2f}{np.median(r):>9.2f}{r.min():>9.2f}"
              f"{r.max():>9.2f}{beats:>6}/{N_TEST_BASKETS}")
    print(f"{'B&H':14}{bh_mean:>9.2f}{bh_med:>9.2f}{min(bh):>9.2f}{max(bh):>9.2f}")

    core = np.mean(out['CORE_MA'])
    print(f"\nMean raw OOS return vs CORE_MA:")
    for label in ('ENSEMBLE', 'TREND_FOLLOW'):
        print(f"  {label:13} {np.mean(out[label]) - core:+.2f} pts")
    print(f"\nGap to B&H (mean): "
          f"CORE={bh_mean-core:.1f}  ENSEMBLE={bh_mean-np.mean(out['ENSEMBLE']):.1f}  "
          f"TREND={bh_mean-np.mean(out['TREND_FOLLOW']):.1f}")
    set_genome({})


if __name__ == "__main__":
    main()
