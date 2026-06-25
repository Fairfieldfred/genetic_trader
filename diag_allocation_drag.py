"""
Allocation-drag diagnostic (absolute-return objective).

Question: of the ~24-pt OOS gap to buy-and-hold, how much is CASH DRAG (capital
sitting in cash / out of the market) vs SIGNAL QUALITY (the trading itself
destroying value)?

Method: evolve each champion ONCE at the baseline 80% initial allocation (under
absolute-return fitness), then re-score that fixed champion OUT-OF-SAMPLE while
sweeping INITIAL_ALLOCATION_PCT in {60,70,80,90,100}. Report mean raw OOS return
per allocation vs the B&H reference.

Interpretation:
- If return climbs steeply toward B&H as allocation -> 100%, the gap is mostly
  cash drag -> the lever is "stay deployed" (evolve the invested fraction), not
  more DNA.
- If return stays well below B&H even at 100% allocation, the trading logic is
  the wall -> the lever is signal quality (more/better DNA).
"""
import random
import numpy as np

import config
config.BACKTESTING_ENGINE = 'vectorbt'
config.USE_KFOLD_VALIDATION = False
config.VECTORBT_DEDUP = True
config.FITNESS_WEIGHTS = {  # absolute-return-aligned (matches ab_ensemble_absolute)
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
BASELINE_ALLOC = 80.0
ALLOC_SWEEP = [60.0, 70.0, 80.0, 90.0, 100.0]

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


def evolve_champion(enriched, basket, train_eval):
    set_genome(enriched)
    config.USE_EXCESS_RETURN_FITNESS = False
    config.INITIAL_ALLOCATION_PCT = BASELINE_ALLOC
    seed_all(SEED)
    train_eval.set_active_basket(basket)
    pop = Population(size=POP)
    for gen in range(GENS):
        train_eval.evaluate_population(pop.traders)
        if gen < GENS - 1:
            pop.evolve_generation()
    return pop.get_best_trader()


def score_at_alloc(champ, enriched, alloc, test_eval, test_baskets):
    """Mean raw OOS return of a fixed champion at a given allocation %."""
    set_genome(enriched)  # ensure GENE_ORDER matches champ's chromosome
    config.INITIAL_ALLOCATION_PCT = alloc
    rets = []
    for b in test_baskets:
        test_eval.set_active_basket(b)
        rets.append(test_eval.get_detailed_results(champ)['total_return'])
    return float(np.mean(rets))


def main():
    print("ALLOCATION-DRAG DIAGNOSTIC (absolute-return objective)")
    print(f"Sweep INITIAL_ALLOCATION_PCT: {ALLOC_SWEEP}\n")
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

    # B&H reference is allocation-independent (always fully invested basket)
    bh = []
    for b in test_baskets:
        test_eval.set_active_basket(b)
        bh.append(test_eval._benchmark_return(test_eval._close))
    bh_mean = float(np.mean(bh))

    # Evolve both champions once at baseline allocation
    champs = {}
    for label, enriched in [("CORE_MA", False), ("ENSEMBLE", True)]:
        champs[label] = (evolve_champion(enriched, train_basket, train_eval), enriched)
        print(f"  evolved {label}")

    # Sweep allocation, re-scoring fixed champions
    print("\n" + "=" * 70)
    print(f"Mean raw OOS return (%) by INITIAL_ALLOCATION_PCT   |  B&H ref = {bh_mean:.2f}%")
    print("=" * 70)
    header = "alloc%".ljust(8) + "".join(f"{a:>9.0f}" for a in ALLOC_SWEEP)
    print(header)
    curves = {}
    for label, (champ, enriched) in champs.items():
        row = [score_at_alloc(champ, enriched, a, test_eval, test_baskets) for a in ALLOC_SWEEP]
        curves[label] = row
        print(label.ljust(8) + "".join(f"{v:>9.2f}" for v in row))
    print("B&H".ljust(8) + "".join(f"{bh_mean:>9.2f}" for _ in ALLOC_SWEEP))

    # Decomposition
    print("\n" + "=" * 70)
    print("DECOMPOSITION (ENSEMBLE champion)")
    print("=" * 70)
    ens = curves['ENSEMBLE']
    r80 = ens[ALLOC_SWEEP.index(80.0)]
    r100 = ens[ALLOC_SWEEP.index(100.0)]
    gap_total = bh_mean - r80
    drag_recovered = r100 - r80          # return gained purely by deploying more cash
    residual = bh_mean - r100            # gap remaining even fully invested = signal cost
    print(f"Total gap to B&H at 80% alloc : {gap_total:+.2f} pts")
    print(f"Recovered by going 80->100%   : {drag_recovered:+.2f} pts  (cash drag)")
    print(f"Residual gap at 100% alloc    : {residual:+.2f} pts  (signal quality)")
    if gap_total > 0:
        print(f"\n=> Cash drag explains ~{100*drag_recovered/gap_total:.0f}% of the gap; "
              f"signal quality ~{100*residual/gap_total:.0f}%.")
    set_genome(False)
    config.INITIAL_ALLOCATION_PCT = BASELINE_ALLOC


if __name__ == "__main__":
    main()
