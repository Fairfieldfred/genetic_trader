"""
Genome-enrichment experiment #2: do the new RISK-DNA genes (ATR volatility
sizing + trailing-stop exit) find out-of-sample edge the flat 6-gene MA could not?

Arms (identical seed/init pop, fixed train basket, scored OOS across N held-out
random baskets):
  1. CORE_MA      6-gene MA crossover, fixed stop/TP, flat sizing   (baseline)
  2. RISK_DNA     core + atr_sizing_enabled(forced ON) + atr_risk_pct +
                  atr_stop_multiple + sl_trail_enabled(forced ON)

Reuses the verified set_active_basket / _benchmark_return machinery and the same
6 held-out test baskets as ab_ensemble.py for comparability.
"""
import random
import numpy as np

import config
config.BACKTESTING_ENGINE = 'vectorbt'
config.USE_KFOLD_VALIDATION = False
config.VECTORBT_DEDUP = True  # dedup key now hashes full gene set (fixed) -> safe

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

# New risk-DNA genes. enabled flags FORCED ON to isolate their contribution;
# the tunable params get real ranges so evolution can search them.
RISK_GENES = {
    'atr_sizing_enabled': (1, 1, int),
    'atr_risk_pct': (0.5, 3.0, float),       # target risk per trade, % of capital
    'atr_stop_multiple': (1.0, 4.0, float),  # ATR multiples for stop distance
    'sl_trail_enabled': (1, 1, int),
}


def seed_all(s):
    random.seed(s); np.random.seed(s)


def set_genome(enriched):
    if enriched:
        merged = dict(CORE_GENES); merged.update(RISK_GENES)
        config.GENE_DEFINITIONS = merged
        config.GENE_ORDER = CORE_ORDER + list(RISK_GENES.keys())
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
    for label, enriched in [("CORE_MA", False), ("RISK_DNA", True)]:
        champ = run_arm(enriched, train_basket, train_eval)
        g = champ.get_genes()
        out[label] = oos_distribution(champ, test_eval, test_baskets)
        print(f"  {label:9} ({len(g):2d} genes) champ MA=({g['ma_short_period']},"
              f"{g['ma_long_period']}) train_fit={champ.fitness:.2f}")
        if enriched:
            print(f"            atr_risk={g['atr_risk_pct']:.2f}% "
                  f"atr_mult={g['atr_stop_multiple']:.2f} "
                  f"trail={int(g['sl_trail_enabled'])}")

    print("\n" + "=" * 72)
    print(f"OUT-OF-SAMPLE EXCESS-over-B&H across {N_TEST_BASKETS} held-out baskets (pct pts)")
    print("=" * 72)
    print(f"{'arm':12}{'mean':>9}{'median':>9}{'min':>9}{'max':>9}{'>0':>8}")
    for label in ("CORE_MA", "RISK_DNA"):
        ex = np.array(out[label]); wins = int((ex > 0).sum())
        print(f"{label:12}{ex.mean():>9.2f}{np.median(ex):>9.2f}{ex.min():>9.2f}"
              f"{ex.max():>9.2f}{wins:>5}/{N_TEST_BASKETS}")
    d = np.mean(out['RISK_DNA']) - np.mean(out['CORE_MA'])
    print(f"\nRISK_DNA mean OOS alpha vs CORE_MA: {d:+.2f} pct pts")
    set_genome(False)


if __name__ == "__main__":
    main()
