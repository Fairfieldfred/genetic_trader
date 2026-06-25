"""
Genome-enrichment experiment: does turning on the ENSEMBLE genes (the richest
unused DNA) find out-of-sample edge that the 6-gene MA crossover could not?

Compares, on identical held-out test baskets:
  1. CORE_MA     6-gene MA crossover           (baseline = the proven-flat genome)
  2. ENSEMBLE    core + 13 ensemble genes,      ensemble_enabled forced ON
                 (MA/Bollinger/Stochastic/MACD/RSI weighted blend w/ evolved
                  weights + thresholds)

Both arms: same seed, same GA settings, evaluated on a FIXED training basket,
scored OOS across N held-out random baskets -> distribution, not one number.

NOTE: batch dedup is disabled here because the evaluator's dedup key only hashes
the 6 core genes; with ensemble genes active that would wrongly collapse traders.
"""
import random
import numpy as np

import config
config.BACKTESTING_ENGINE = 'vectorbt'
config.USE_KFOLD_VALIDATION = False
config.VECTORBT_DEDUP = False  # ensemble genes not in dedup key -> must disable

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

# Exact bounds from the Dart catalog (config_model.dart)
ENSEMBLE_GENES = {
    'ensemble_enabled': (1, 1, int),   # FORCED ON to isolate ensemble contribution
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
    ex = []
    for b in test_baskets:
        test_eval.set_active_basket(b)
        res = test_eval.get_detailed_results(champ)
        ex.append(res['total_return'] - test_eval._benchmark_return(test_eval._close))
    return ex


def main():
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

    out = {}
    for label, enriched in [("CORE_MA", False), ("ENSEMBLE", True)]:
        champ = run_arm(enriched, train_basket, train_eval)
        g = champ.get_genes()
        out[label] = oos_distribution(champ, test_eval, test_baskets)
        ngenes = len(g)
        print(f"  {label:9} ({ngenes:2d} genes) champ MA=({g['ma_short_period']},"
              f"{g['ma_long_period']}) train_fit={champ.fitness:.2f}")
        if enriched:
            print(f"            weights ma={g['sig_ma_weight']:.2f} bb={g['sig_bb_weight']:.2f} "
                  f"stoch={g['sig_stoch_weight']:.2f} macd={g['sig_macd_weight']:.2f} "
                  f"rsi={g['sig_rsi_weight']:.2f}")

    print("\n" + "=" * 72)
    print(f"OUT-OF-SAMPLE EXCESS-over-B&H across {N_TEST_BASKETS} held-out baskets (pct pts)")
    print("=" * 72)
    print(f"{'arm':12}{'mean':>9}{'median':>9}{'min':>9}{'max':>9}{'>0':>8}")
    for label in ("CORE_MA", "ENSEMBLE"):
        ex = np.array(out[label]); wins = int((ex > 0).sum())
        print(f"{label:12}{ex.mean():>9.2f}{np.median(ex):>9.2f}{ex.min():>9.2f}"
              f"{ex.max():>9.2f}{wins:>5}/{N_TEST_BASKETS}")
    d = np.mean(out['ENSEMBLE']) - np.mean(out['CORE_MA'])
    print(f"\nENSEMBLE mean OOS alpha vs CORE_MA: {d:+.2f} pct pts")
    # restore defaults
    set_genome(False)


if __name__ == "__main__":
    main()
