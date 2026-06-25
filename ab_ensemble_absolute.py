"""
Ensemble experiment under an ABSOLUTE-RETURN objective (user decision 2026-06-25).

Two changes vs ab_ensemble.py:
  1. FITNESS_WEIGHTS shifted to absolute return (total_return 0.85, sharpe 0.05,
     max_drawdown 0.05, win_rate 0.05) — selection pressure now targets raw return,
     not risk metrics.
  2. Champions judged on RAW OOS total_return (mean/median) AND excess-over-B&H,
     since the objective is absolute return.

Arms (identical seed/init pop, fixed train basket, N held-out test baskets):
  1. CORE_MA    6-gene MA crossover
  2. ENSEMBLE   core + 13 ensemble signal genes (ensemble_enabled forced ON)
"""
import random
import numpy as np

import config
config.BACKTESTING_ENGINE = 'vectorbt'
config.USE_KFOLD_VALIDATION = False
config.VECTORBT_DEDUP = True  # dedup key hashes full gene set (fixed) -> safe

# --- Absolute-return-aligned fitness weights ---
ABSOLUTE_WEIGHTS = {
    'total_return': 0.85,
    'sharpe_ratio': 0.05,
    'max_drawdown': 0.05,
    'win_rate': 0.05,
}
config.FITNESS_WEIGHTS = dict(ABSOLUTE_WEIGHTS)

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
    'sig_ma_weight': (0.0, 1.0, float),
    'sig_bb_weight': (0.0, 1.0, float),
    'sig_stoch_weight': (0.0, 1.0, float),
    'sig_macd_weight': (0.0, 1.0, float),
    'sig_rsi_weight': (0.0, 1.0, float),
    'sig_buy_threshold': (0.1, 0.8, float),
    'sig_sell_threshold': (-0.8, -0.1, float),
    'sig_bb_period_idx': (0, 2, int),
    'sig_stoch_ob': (70, 90, int),
    'sig_stoch_os': (10, 30, int),
    'sig_rsi_ob': (60, 85, int),
    'sig_rsi_os': (15, 40, int),
}


def seed_all(s):
    random.seed(s); np.random.seed(s)


def set_genome(enriched):
    if enriched:
        merged = dict(CORE_GENES); merged.update(ENSEMBLE_GENES)
        config.GENE_DEFINITIONS = merged
        config.GENE_ORDER = CORE_ORDER + list(ENSEMBLE_GENES.keys())
    else:
        config.GENE_DEFINITIONS = dict(CORE_GENES)
        config.GENE_ORDER = list(CORE_ORDER)


def run_arm(enriched, basket, train_eval):
    set_genome(enriched)
    config.USE_EXCESS_RETURN_FITNESS = False
    seed_all(SEED)
    train_eval.set_active_basket(basket)
    pop = Population(size=POP)
    for gen in range(GENS):
        train_eval.evaluate_population(pop.traders)
        if gen < GENS - 1:
            pop.evolve_generation()
    return pop.get_best_trader()


def oos_distribution(champ, test_eval, test_baskets):
    """Return (raw_returns, excess_returns) lists across test baskets."""
    raw, excess = [], []
    for b in test_baskets:
        test_eval.set_active_basket(b)
        res = test_eval.get_detailed_results(champ)
        bench = test_eval._benchmark_return(test_eval._close)
        raw.append(res['total_return'])
        excess.append(res['total_return'] - bench)
    return raw, excess


def main():
    print("OBJECTIVE: ABSOLUTE RETURN")
    print(f"Fitness weights: {config.FITNESS_WEIGHTS}\n")
    seed_all(SEED)
    universe = select_random_portfolio(size=UNIVERSE_SIZE, seed=SEED, sectors=None)
    print(f"Universe={len(universe)} basket={BASKET_SIZE} pop={POP} gens={GENS} seed={SEED}")
    print(f"Train {config.TRAIN_START_DATE}->{config.TRAIN_END_DATE} | "
          f"Test {config.TEST_START_DATE}->{config.TEST_END_DATE}\n")

    train_eval = VectorbtFitnessEvaluator(symbols=universe,
        start_date=config.TRAIN_START_DATE, end_date=config.TRAIN_END_DATE)
    universe = list(train_eval.valid_symbols)
    test_eval = VectorbtFitnessEvaluator(symbols=universe,
        start_date=config.TEST_START_DATE, end_date=config.TEST_END_DATE)
    test_universe = list(test_eval.valid_symbols)

    train_basket = universe[:BASKET_SIZE]
    tb_rng = random.Random(SEED + 999)
    test_baskets = [tb_rng.sample(test_universe, BASKET_SIZE) for _ in range(N_TEST_BASKETS)]

    # B&H reference per test basket (for context)
    bh_ref = []
    for b in test_baskets:
        test_eval.set_active_basket(b)
        bh_ref.append(test_eval._benchmark_return(test_eval._close))

    out = {}
    for label, enriched in [("CORE_MA", False), ("ENSEMBLE", True)]:
        champ = run_arm(enriched, train_basket, train_eval)
        g = champ.get_genes()
        raw, excess = oos_distribution(champ, test_eval, test_baskets)
        out[label] = (raw, excess)
        print(f"  {label:9} ({len(g):2d} genes) MA=({g['ma_short_period']},"
              f"{g['ma_long_period']}) train_fit={champ.fitness:.2f}")

    print("\n" + "=" * 76)
    print(f"OUT-OF-SAMPLE across {N_TEST_BASKETS} held-out baskets")
    print(f"B&H reference: mean={np.mean(bh_ref):.2f}% median={np.median(bh_ref):.2f}%")
    print("=" * 76)
    print(f"{'arm':12}{'RAW mean':>10}{'RAW med':>10}{'RAW min':>10}{'RAW max':>10}"
          f"{'beatB&H':>9}")
    for label in ("CORE_MA", "ENSEMBLE"):
        raw = np.array(out[label][0]); exc = np.array(out[label][1])
        beats = int((exc > 0).sum())
        print(f"{label:12}{raw.mean():>10.2f}{np.median(raw):>10.2f}{raw.min():>10.2f}"
              f"{raw.max():>10.2f}{beats:>6}/{N_TEST_BASKETS}")

    dr = np.mean(out['ENSEMBLE'][0]) - np.mean(out['CORE_MA'][0])
    print(f"\nENSEMBLE vs CORE_MA, mean RAW OOS return: {dr:+.2f} pct pts")
    print("(Objective is absolute return -> judge on RAW columns, not excess.)")
    set_genome(False)
    config.FITNESS_WEIGHTS = {  # restore defaults
        'total_return': 0.4, 'sharpe_ratio': 0.24,
        'max_drawdown': 0.24, 'win_rate': 0.12}


if __name__ == "__main__":
    main()
