"""
Regime test (absolute-return objective): does the proven ENSEMBLE genome show
its value in a DOWN market, where a strategy that can go to cash should have a
real edge over buy-and-hold?

Prior experiments all tested on the 2024-2025 BULL window, where any cash-holding
strategy fights a structural headwind (0/6 vs B&H). This re-runs CORE_MA vs
ENSEMBLE on the 2022 BEAR window (basket ~ -15%), trained on the pre-bear period
to avoid look-ahead.

Hypothesis: in a falling market, ENSEMBLE beats B&H more often (downside
protection), which would reframe the strategy's value away from bull-market
absolute return.

Also includes 2018 (milder down year, ~ -8%) as a second down-regime check.
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

# Each regime: (label, train_start, train_end, test_start, test_end)
REGIMES = [
    ("2022_BEAR",  "2016-04-01", "2021-12-31", "2022-01-01", "2022-12-31"),
    ("2018_DOWN",  "2016-04-01", "2017-12-31", "2018-01-01", "2018-12-31"),
]

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


def run_arm(enriched, basket, train_eval):
    set_genome(enriched)
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


def run_regime(label, tr_s, tr_e, te_s, te_e):
    print("\n" + "#" * 76)
    print(f"# REGIME: {label}   train {tr_s}->{tr_e}   test {te_s}->{te_e}")
    print("#" * 76)
    seed_all(SEED)
    universe = select_random_portfolio(size=UNIVERSE_SIZE, seed=SEED, sectors=None)
    train_eval = VectorbtFitnessEvaluator(symbols=universe, start_date=tr_s, end_date=tr_e)
    universe = list(train_eval.valid_symbols)
    test_eval = VectorbtFitnessEvaluator(symbols=universe, start_date=te_s, end_date=te_e)
    test_universe = list(test_eval.valid_symbols)

    train_basket = universe[:BASKET_SIZE]
    tb_rng = random.Random(SEED + 999)
    test_baskets = [tb_rng.sample(test_universe, BASKET_SIZE) for _ in range(N_TEST_BASKETS)]

    bh = []
    for b in test_baskets:
        test_eval.set_active_basket(b)
        bh.append(test_eval._benchmark_return(test_eval._close))
    bh = np.array(bh)

    out = {}
    for lbl, enriched in [("CORE_MA", False), ("ENSEMBLE", True)]:
        champ = run_arm(enriched, train_basket, train_eval)
        out[lbl] = np.array(oos_raw(champ, test_eval, test_baskets))

    print(f"\n  Test-window B&H: mean={bh.mean():.2f}% median={np.median(bh):.2f}% "
          f"(this is a {'DOWN' if bh.mean() < 0 else 'UP'} regime)")
    print(f"  {'arm':12}{'mean':>9}{'median':>9}{'min':>9}{'max':>9}{'beatB&H':>9}{'positive':>10}")
    for lbl in ("CORE_MA", "ENSEMBLE"):
        r = out[lbl]
        beats = int((r > bh).sum())
        pos = int((r > 0).sum())
        print(f"  {lbl:12}{r.mean():>9.2f}{np.median(r):>9.2f}{r.min():>9.2f}"
              f"{r.max():>9.2f}{beats:>6}/{N_TEST_BASKETS}{pos:>7}/{N_TEST_BASKETS}")
    print(f"  {'B&H':12}{bh.mean():>9.2f}{np.median(bh):>9.2f}{bh.min():>9.2f}{bh.max():>9.2f}")

    ens_beats = int((out['ENSEMBLE'] > bh).sum())
    print(f"\n  => ENSEMBLE beat B&H on {ens_beats}/{N_TEST_BASKETS} baskets in this "
          f"{'DOWN' if bh.mean() < 0 else 'UP'} regime "
          f"(downside protection: {'YES' if ens_beats >= 4 else 'partial' if ens_beats >= 2 else 'no'})")
    return label, bh.mean(), ens_beats


def main():
    print("REGIME TEST — does ensemble add value in DOWN markets? (absolute-return obj)")
    results = []
    for r in REGIMES:
        results.append(run_regime(*r))
    print("\n" + "=" * 76)
    print("SUMMARY")
    print("=" * 76)
    print(f"{'regime':14}{'B&H mean':>10}{'ENSEMBLE beats B&H':>22}")
    for label, bhm, beats in results:
        print(f"{label:14}{bhm:>10.2f}{f'{beats}/{N_TEST_BASKETS}':>22}")
    set_genome(False)


if __name__ == "__main__":
    main()
