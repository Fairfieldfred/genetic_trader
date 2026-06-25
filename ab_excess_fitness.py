"""
A/B test: absolute-return fitness vs excess-return (alpha) fitness.

Same initial population + same seed for both arms, so the ONLY difference is
config.USE_EXCESS_RETURN_FITNESS. Each arm evolves on the train window, then its
champion is scored out-of-sample on the held-out test window vs an equal-weight
buy-and-hold of the same basket.
"""
import random
import copy
import numpy as np

import config
config.BACKTESTING_ENGINE = 'vectorbt'

from population import Population
from vectorbt_fitness import VectorbtFitnessEvaluator
from portfolio_fitness import select_random_portfolio

POP = 30
GENS = 25
SEED = 42

TRAIN_START, TRAIN_END = config.TRAIN_START_DATE, config.TRAIN_END_DATE
TEST_START, TEST_END = config.TEST_START_DATE, config.TEST_END_DATE


def seed_all(s):
    random.seed(s)
    np.random.seed(s)


def run_arm(use_excess, symbols, train_eval):
    config.USE_EXCESS_RETURN_FITNESS = use_excess
    # Identical starting point for both arms
    seed_all(SEED)
    pop = Population(size=POP)

    for gen in range(GENS):
        train_eval.evaluate_population(pop.traders)
        stats = pop.get_statistics()
        if gen == 0 or gen == GENS - 1:
            print(f"    gen {gen:2d}: best_fit={stats['best_fitness']:.2f} "
                  f"avg={stats['avg_fitness']:.2f}")
        if gen < GENS - 1:
            pop.evolve_generation()

    return pop.get_best_trader()


def oos_score(trader, test_eval):
    res = test_eval.get_detailed_results(trader)
    strat = res['total_return']
    bench = test_eval._benchmark_return(test_eval._close)
    return strat, bench, strat - bench


def main():
    print("=" * 70)
    print("A/B: ABSOLUTE vs EXCESS-RETURN FITNESS")
    print("=" * 70)

    seed_all(SEED)
    sectors = getattr(config, 'PORTFOLIO_SECTORS', []) or None
    symbols = select_random_portfolio(size=config.PORTFOLIO_SIZE, seed=SEED,
                                       sectors=sectors)
    print(f"Portfolio ({len(symbols)}): {', '.join(symbols)}")
    print(f"Train: {TRAIN_START} -> {TRAIN_END} | Test: {TEST_START} -> {TEST_END}")
    print(f"GA: pop={POP}, gens={GENS}, seed={SEED}\n")

    print("Loading train evaluator...")
    train_eval = VectorbtFitnessEvaluator(symbols=symbols,
                                          start_date=TRAIN_START, end_date=TRAIN_END)
    print("Loading test evaluator (out-of-sample)...")
    test_eval = VectorbtFitnessEvaluator(symbols=symbols,
                                         start_date=TEST_START, end_date=TEST_END)

    results = {}
    for label, use_excess in [("ABSOLUTE", False), ("EXCESS", True)]:
        print(f"\n--- Arm: {label} (USE_EXCESS_RETURN_FITNESS={use_excess}) ---")
        champ = run_arm(use_excess, symbols, train_eval)
        strat, bench, excess = oos_score(champ, test_eval)
        results[label] = dict(genes=champ.get_genes(), train_fit=champ.fitness,
                              oos_strat=strat, oos_bench=bench, oos_excess=excess)
        print(f"    train fitness : {champ.fitness:.2f}")
        print(f"    OOS strat ret : {strat:+.2f}%")
        print(f"    OOS B&H ret   : {bench:+.2f}%")
        print(f"    OOS EXCESS    : {excess:+.2f}%  beats_bench={strat > bench}")

    print("\n" + "=" * 70)
    print("SUMMARY (out-of-sample, held-out test window)")
    print("=" * 70)
    print(f"{'arm':10}{'train_fit':>11}{'OOS_ret':>10}{'B&H':>9}{'excess':>9}  beats")
    for label in ("ABSOLUTE", "EXCESS"):
        r = results[label]
        print(f"{label:10}{r['train_fit']:>11.2f}{r['oos_strat']:>10.2f}"
              f"{r['oos_bench']:>9.2f}{r['oos_excess']:>9.2f}  "
              f"{r['oos_strat'] > r['oos_bench']}")

    a, e = results['ABSOLUTE'], results['EXCESS']
    delta = e['oos_excess'] - a['oos_excess']
    print(f"\nExcess-fitness arm changed OOS alpha by {delta:+.2f} pct points "
          f"vs absolute-fitness arm.")
    ma_a = (a['genes']['ma_short_period'], a['genes']['ma_long_period'])
    ma_e = (e['genes']['ma_short_period'], e['genes']['ma_long_period'])
    print(f"Champion MA(short,long): ABSOLUTE={ma_a}  EXCESS={ma_e}")


if __name__ == "__main__":
    main()
