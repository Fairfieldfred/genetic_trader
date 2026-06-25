"""
Decisive A/B: does randomized-basket training (+ excess-return fitness) improve
out-of-sample generalization vs the status-quo fixed-basket / absolute-fitness GA?

Three arms, identical seed + identical initial population:
  1. CONTROL       fixed basket,       absolute fitness   (status quo)
  2. RAND_ONLY     randomized basket,  absolute fitness   (isolates randomization)
  3. RAND_EXCESS   randomized basket,  excess fitness     (the proposed pair)

Each champion is then scored OUT-OF-SAMPLE on several held-out random test
baskets (same baskets for every arm) -> reports a distribution, not one number.
"""
import random
import numpy as np

import config
config.BACKTESTING_ENGINE = 'vectorbt'
config.USE_KFOLD_VALIDATION = False

from population import Population
from vectorbt_fitness import VectorbtFitnessEvaluator
from portfolio_fitness import select_random_portfolio

POP, GENS, SEED = 30, 25, 42
UNIVERSE_SIZE = 40
BASKET_SIZE = 15
N_TEST_BASKETS = 6


def seed_all(s):
    random.seed(s); np.random.seed(s)


def run_arm(label, randomize, use_excess, universe, train_eval):
    config.USE_EXCESS_RETURN_FITNESS = use_excess
    seed_all(SEED)  # identical initial population across arms
    pop = Population(size=POP)
    # dedicated RNG so basket draws don't perturb GA's random stream
    basket_rng = random.Random(SEED + 777)

    for gen in range(GENS):
        if randomize:
            train_eval.set_active_basket(basket_rng.sample(universe, BASKET_SIZE))
        else:
            train_eval.set_active_basket(universe[:BASKET_SIZE])  # fixed
        train_eval.evaluate_population(pop.traders)
        if gen < GENS - 1:
            pop.evolve_generation()
    champ = pop.get_best_trader()
    g = champ.get_genes()
    print(f"  {label:12} done | champ MA=({g['ma_short_period']},{g['ma_long_period']},"
          f"{g['ma_type']}) sl={g['stop_loss_pct']:.1f} tp={g['take_profit_pct']:.1f}")
    return champ


def oos_distribution(champ, test_eval, test_baskets):
    """Score champion on each held-out test basket; return list of excess returns."""
    excesses = []
    for basket in test_baskets:
        test_eval.set_active_basket(basket)
        res = test_eval.get_detailed_results(champ)
        strat = res['total_return']
        bench = test_eval._benchmark_return(test_eval._close)
        excesses.append(strat - bench)
    return excesses


def main():
    seed_all(SEED)
    universe = select_random_portfolio(size=UNIVERSE_SIZE, seed=SEED, sectors=None)
    print(f"Universe: {len(universe)} stocks | basket={BASKET_SIZE} | "
          f"pop={POP} gens={GENS} seed={SEED}")
    print(f"Train {config.TRAIN_START_DATE}->{config.TRAIN_END_DATE} | "
          f"Test {config.TEST_START_DATE}->{config.TEST_END_DATE}\n")

    print("Loading TRAIN evaluator (full universe)...")
    train_eval = VectorbtFitnessEvaluator(symbols=universe,
        start_date=config.TRAIN_START_DATE, end_date=config.TRAIN_END_DATE)
    universe = list(train_eval.valid_symbols)  # only successfully-loaded

    print("\nLoading TEST evaluator (full universe, out-of-sample)...")
    test_eval = VectorbtFitnessEvaluator(symbols=universe,
        start_date=config.TEST_START_DATE, end_date=config.TEST_END_DATE)
    test_universe = list(test_eval.valid_symbols)

    # Build held-out test baskets ONCE; identical for all arms (fair comparison)
    tb_rng = random.Random(SEED + 999)
    test_baskets = [tb_rng.sample(test_universe, BASKET_SIZE) for _ in range(N_TEST_BASKETS)]

    arms = [
        ("CONTROL",     False, False),
        ("RAND_ONLY",   True,  False),
        ("RAND_EXCESS", True,  True),
    ]
    print("\n" + "=" * 72)
    out = {}
    for label, rnd, exc in arms:
        champ = run_arm(label, rnd, exc, universe, train_eval)
        ex = oos_distribution(champ, test_eval, test_baskets)
        out[label] = ex

    print("\n" + "=" * 72)
    print(f"OUT-OF-SAMPLE EXCESS-over-B&H across {N_TEST_BASKETS} held-out baskets (pct pts)")
    print("=" * 72)
    print(f"{'arm':14}{'mean':>9}{'median':>9}{'min':>9}{'max':>9}{'>0 baskets':>12}")
    for label, _, _ in arms:
        ex = np.array(out[label])
        wins = int((ex > 0).sum())
        print(f"{label:14}{ex.mean():>9.2f}{np.median(ex):>9.2f}{ex.min():>9.2f}"
              f"{ex.max():>9.2f}{wins:>8}/{N_TEST_BASKETS}")

    base = np.mean(out['CONTROL'])
    print(f"\nMean OOS alpha vs CONTROL:")
    for label in ('RAND_ONLY', 'RAND_EXCESS'):
        print(f"  {label:12} {np.mean(out[label]) - base:+.2f} pct pts")


if __name__ == "__main__":
    main()
