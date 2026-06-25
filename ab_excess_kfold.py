"""
A/B under K-FOLD: now each fold has its own buy-and-hold benchmark, so excess
return is NO LONGER a constant offset across traders -> it can change selection.
Demonstrates the regime where excess-return fitness actually reshapes the search.
"""
import random
import numpy as np

import config
config.BACKTESTING_ENGINE = 'vectorbt'
# Enable k-fold so benchmark varies across folds
config.USE_KFOLD_VALIDATION = True
config.KFOLD_NUM_FOLDS = 3
config.KFOLD_FOLD_YEARS = 3
config.KFOLD_ALLOW_OVERLAP = False
config.KFOLD_WEIGHT_RECENT = False

from population import Population
from vectorbt_fitness import VectorbtFitnessEvaluator
from portfolio_fitness import select_random_portfolio

POP, GENS, SEED = 30, 25, 42


def seed_all(s):
    random.seed(s); np.random.seed(s)


def run_arm(use_excess, train_eval):
    config.USE_EXCESS_RETURN_FITNESS = use_excess
    seed_all(SEED)
    pop = Population(size=POP)
    for gen in range(GENS):
        train_eval.evaluate_population(pop.traders)
        if gen < GENS - 1:
            pop.evolve_generation()
    return pop.get_best_trader()


def oos(trader, test_eval):
    res = test_eval.get_detailed_results(trader)
    strat = res['total_return']
    bench = test_eval._benchmark_return(test_eval._close)
    return strat, bench


def main():
    seed_all(SEED)
    sectors = getattr(config, 'PORTFOLIO_SECTORS', []) or None
    symbols = select_random_portfolio(size=config.PORTFOLIO_SIZE, seed=SEED, sectors=sectors)
    print(f"K-FOLD A/B | basket={len(symbols)} | folds={config.KFOLD_NUM_FOLDS}")
    print(f"Train {config.TRAIN_START_DATE}->{config.TRAIN_END_DATE}  "
          f"Test {config.TEST_START_DATE}->{config.TEST_END_DATE}\n")

    train_eval = VectorbtFitnessEvaluator(symbols=symbols,
        start_date=config.TRAIN_START_DATE, end_date=config.TRAIN_END_DATE)
    test_eval = VectorbtFitnessEvaluator(symbols=symbols,
        start_date=config.TEST_START_DATE, end_date=config.TEST_END_DATE)
    print(f"Folds: {train_eval.folds}\n")

    out = {}
    for label, ex in [("ABSOLUTE", False), ("EXCESS", True)]:
        champ = run_arm(ex, train_eval)
        s, b = oos(champ, test_eval)
        g = champ.get_genes()
        out[label] = (champ.fitness, s, b, s - b,
                      (g['ma_short_period'], g['ma_long_period'], g['ma_type']))
        print(f"{label:9} train_fit={champ.fitness:7.2f}  OOS={s:+6.2f}%  "
              f"B&H={b:+6.2f}%  excess={s-b:+6.2f}  MA={out[label][4]}")

    print("\n" + "=" * 64)
    same = out['ABSOLUTE'][4] == out['EXCESS'][4]
    print(f"Champions identical? {same}")
    d = out['EXCESS'][3] - out['ABSOLUTE'][3]
    print(f"OOS alpha change (EXCESS - ABSOLUTE): {d:+.2f} pct points")


if __name__ == "__main__":
    main()
