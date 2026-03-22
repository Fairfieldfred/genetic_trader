"""
Unit tests for VectorbtFitnessEvaluator.
"""

import pytest
import random
import numpy as np
import config
from genetic_trader import GeneticTrader
from vectorbt_fitness import VectorbtFitnessEvaluator


# Use a small portfolio for fast tests
TEST_SYMBOLS = ['AAPL', 'MSFT', 'GOOG']
TEST_START = '2020-01-01'
TEST_END = '2022-12-31'


@pytest.fixture(scope='module')
def evaluator():
    """Create evaluator once for all tests (data loading is expensive)."""
    random.seed(42)
    np.random.seed(42)
    return VectorbtFitnessEvaluator(
        symbols=TEST_SYMBOLS,
        start_date=TEST_START,
        end_date=TEST_END,
    )


def _make_trader(short=10, long_=50, ma_type=0, sl=3.0, tp=8.0, sz=15.0,
                 **overrides):
    """Create a trader with specified core genes + default values for remaining genes."""
    gene_values = {
        'ma_short_period': short,
        'ma_long_period': long_,
        'ma_type': ma_type,
        'stop_loss_pct': sl,
        'take_profit_pct': tp,
        'position_size_pct': sz,
    }
    gene_values.update(overrides)
    chromosome = []
    for gene_name in config.GENE_ORDER:
        if gene_name in gene_values:
            chromosome.append(gene_values[gene_name])
        else:
            min_val, max_val, dtype = config.GENE_DEFINITIONS[gene_name]
            chromosome.append(min_val)
    return GeneticTrader(chromosome)


# ==================================================================
# Phase 1 tests (must remain passing)
# ==================================================================

class TestSingleTraderFitness:
    """Test 1 & 2: Single trader fitness returns a float in plausible range."""

    def test_fitness_returns_float(self, evaluator):
        trader = _make_trader()
        fitness = evaluator.calculate_fitness(trader)
        assert isinstance(fitness, float)

    def test_fitness_in_plausible_range(self, evaluator):
        trader = _make_trader()
        fitness = evaluator.calculate_fitness(trader)
        assert -1000.0 <= fitness <= 1000.0


class TestPopulationEvaluation:
    """Test 3: evaluate_population returns all traders with non-None fitness."""

    def test_all_traders_get_fitness(self, evaluator):
        traders = [_make_trader(short=s, long_=50)
                   for s in [5, 10, 15, 20, 25]]
        result = evaluator.evaluate_population(traders)
        assert len(result) == 5
        for trader in result:
            assert trader.fitness is not None
            assert isinstance(trader.fitness, float)


class TestDeterminism:
    """Test 4: Same trader evaluated twice returns same fitness."""

    def test_deterministic_fitness(self, evaluator):
        trader1 = _make_trader(short=12, long_=60)
        trader2 = _make_trader(short=12, long_=60)
        f1 = evaluator.calculate_fitness(trader1)
        f2 = evaluator.calculate_fitness(trader2)
        assert f1 == f2


class TestEdgeCases:
    """Test 5: Trader with very short MA periods doesn't crash."""

    def test_short_ma_periods(self, evaluator):
        trader = _make_trader(short=5, long_=30)
        fitness = evaluator.calculate_fitness(trader)
        assert isinstance(fitness, float)


class TestScoreResults:
    """Test 6: Fitness function weights produce correct output."""

    def test_score_results_formula(self, evaluator):
        results = {
            'total_return': 10.0,
            'sharpe_ratio': 1.5,
            'max_drawdown': -5.0,
            'win_rate': 55.0,
            'trade_count': 100,
        }
        score = evaluator._score_results(results)
        expected = (
            config.FITNESS_WEIGHTS['total_return'] * 10.0 +
            config.FITNESS_WEIGHTS['sharpe_ratio'] * 1.5 * 10 +
            config.FITNESS_WEIGHTS['max_drawdown'] * (-5.0) +
            config.FITNESS_WEIGHTS['win_rate'] * 55.0
        )
        assert abs(score - expected) < 1e-6

    def test_score_results_min_trades(self, evaluator):
        results = {
            'total_return': 50.0,
            'sharpe_ratio': 2.0,
            'max_drawdown': -3.0,
            'win_rate': 70.0,
            'trade_count': 0,
        }
        assert evaluator._score_results(results) == -100.0


class TestDetailedResults:
    """Test detailed results shape."""

    def test_detailed_results_keys(self, evaluator):
        trader = _make_trader()
        results = evaluator.get_detailed_results(trader)
        required_keys = [
            'starting_value', 'ending_value', 'total_return',
            'sharpe_ratio', 'max_drawdown', 'win_rate',
            'trade_count', 'winning_trades', 'per_stock_performance',
            'genes', 'fitness', 'num_stocks', 'symbols',
        ]
        for key in required_keys:
            assert key in results, f"Missing key: {key}"

    def test_per_stock_performance_shape(self, evaluator):
        trader = _make_trader()
        results = evaluator.get_detailed_results(trader)
        per_stock = results['per_stock_performance']
        for symbol in evaluator.valid_symbols:
            assert symbol in per_stock
            stock_data = per_stock[symbol]
            assert 'trades' in stock_data
            assert 'won' in stock_data
            assert 'lost' in stock_data
            assert 'pnl' in stock_data
            assert 'win_rate' in stock_data


# ==================================================================
# Phase 2 tests: Dedup + K-fold in evaluate_population
# ==================================================================

class TestPhase2Dedup:
    """Phase 2: chromosome deduplication in evaluate_population."""

    def test_dedup_identical_chromosomes(self, evaluator):
        """5 traders with identical genes should all get the same fitness."""
        traders = [_make_trader(short=10, long_=50, sl=3.0, tp=8.0, sz=15.0)
                   for _ in range(5)]
        evaluator.evaluate_population(traders)
        fitnesses = [t.fitness for t in traders]
        assert all(f == fitnesses[0] for f in fitnesses), \
            f"Identical traders got different fitnesses: {fitnesses}"

    def test_population_kfold(self, evaluator):
        """evaluate_population with K-fold enabled gives all traders fitness."""
        original_kfold = config.USE_KFOLD_VALIDATION
        original_folds = config.KFOLD_NUM_FOLDS
        original_years = config.KFOLD_FOLD_YEARS
        try:
            config.USE_KFOLD_VALIDATION = True
            config.KFOLD_NUM_FOLDS = 2
            config.KFOLD_FOLD_YEARS = 1
            # Recompute folds
            evaluator.folds = evaluator._compute_folds()
            assert len(evaluator.folds) >= 2, \
                f"Expected >=2 folds, got {len(evaluator.folds)}"

            traders = [_make_trader(short=s, long_=50)
                       for s in [8, 12, 18]]
            evaluator.evaluate_population(traders)
            for t in traders:
                assert t.fitness is not None
                assert isinstance(t.fitness, float)
                assert t.fitness > -1000.0  # not error sentinel
        finally:
            config.USE_KFOLD_VALIDATION = original_kfold
            config.KFOLD_NUM_FOLDS = original_folds
            config.KFOLD_FOLD_YEARS = original_years
            evaluator.folds = evaluator._compute_folds()


# ==================================================================
# Phase 3 tests: Macro, TI filter, and ensemble signal genes
# ==================================================================

class TestPhase3MacroMasks:
    """Phase 3: macro gene vectorization."""

    def test_macro_mask_neutral_when_disabled(self, evaluator):
        """macro_enabled=0 → block_buys all False, scales all 1.0."""
        genes = _make_trader(macro_enabled=0).get_genes()
        masks = evaluator._compute_macro_masks(evaluator._close, genes)
        assert not masks['block_buys'].any()
        assert (masks['position_scale'] == 1.0).all()
        assert (masks['sl_adj'] == 1.0).all()
        assert (masks['tp_adj'] == 1.0).all()

    def test_macro_mask_blocks_buys(self, evaluator):
        """macro_enabled=1 with extreme thresholds triggers modifiers."""
        genes = _make_trader(
            macro_enabled=1,
            macro_weight=1.0,
            macro_vix_threshold=15.0,  # low threshold
            macro_vix_position_scale=0.2,
        ).get_genes()
        masks = evaluator._compute_macro_masks(evaluator._close, genes)
        # If macro_df is None, everything stays neutral — that's acceptable
        if evaluator.macro_df is not None:
            # position_scale should be < 1.0 somewhere if VIX data exists
            assert (masks['position_scale'] < 1.0).any() or \
                   masks['block_buys'].any(), \
                   "Expected some macro effect with extreme thresholds"
        else:
            # No macro data: masks should be neutral
            assert not masks['block_buys'].any()
            assert (masks['position_scale'] == 1.0).all()


class TestPhase3TIMasks:
    """Phase 3: TI filter gene vectorization."""

    def test_ti_mask_neutral_when_disabled(self, evaluator):
        """ti_enabled=0 → all masks neutral."""
        genes = _make_trader(ti_enabled=0).get_genes()
        masks = evaluator._compute_ti_masks(evaluator._close, genes)
        assert not masks['block_buys'].any().any()
        assert (masks['position_scale'] == 1.0).all().all()
        assert not masks['force_exit'].any().any()
        assert (masks['sl_adj'] == 1.0).all().all()


class TestPhase3EnsembleSignals:
    """Phase 3: ensemble signal gene vectorization."""

    def test_ensemble_neutral_when_disabled(self, evaluator):
        """ensemble_enabled=0 → returns (None, None)."""
        genes = _make_trader(ensemble_enabled=0).get_genes()
        fast_ma = vbt.MA.run(evaluator._close, window=10, ewm=False).ma
        slow_ma = vbt.MA.run(evaluator._close, window=50, ewm=False).ma
        entries, exits = evaluator._compute_ensemble_signals(
            evaluator._close, genes, fast_ma, slow_ma
        )
        assert entries is None
        assert exits is None


class TestPhase3Integration:
    """Phase 3: end-to-end integration tests."""

    def test_full_chromosome_fitness(self, evaluator):
        """Trader with all gene systems enabled returns a valid fitness."""
        trader = _make_trader(
            macro_enabled=1,
            ti_enabled=1,
            ensemble_enabled=1,
            macro_weight=0.5,
            ti_weight=0.5,
            sig_ma_weight=0.5,
            sig_bb_weight=0.3,
            sig_stoch_weight=0.3,
            sig_macd_weight=0.3,
            sig_rsi_weight=0.3,
            sig_buy_threshold=0.3,
            sig_sell_threshold=-0.3,
        )
        fitness = evaluator.calculate_fitness(trader)
        assert isinstance(fitness, float)
        assert fitness > -1000.0  # not error sentinel

    def test_phase3_vs_phase1_same_gene_neutral(self, evaluator):
        """Trader with all extras disabled matches Phase 1 result (within 1%)."""
        trader = _make_trader(
            short=10, long_=50, ma_type=0, sl=3.0, tp=8.0, sz=15.0,
            macro_enabled=0, ti_enabled=0, ensemble_enabled=0,
        )
        f1 = evaluator.calculate_fitness(trader)
        # Run again — same path, should be identical
        f2 = evaluator.calculate_fitness(trader)
        assert f1 == f2, f"Non-deterministic: {f1} != {f2}"
        # The key assertion: with all extras disabled, the fitness should
        # be the same as a trader that only has the 6 core genes
        # (This tests that neutral masks don't alter results)
        trader_core = _make_trader(
            short=10, long_=50, ma_type=0, sl=3.0, tp=8.0, sz=15.0,
        )
        f_core = evaluator.calculate_fitness(trader_core)
        if abs(f_core) > 0.01:
            pct_diff = abs(f1 - f_core) / abs(f_core) * 100
            assert pct_diff < 1.0, \
                f"Phase 3 neutral ({f1}) differs from core ({f_core}) by {pct_diff:.2f}%"
        else:
            assert abs(f1 - f_core) < 1.0


# Need vbt import for ensemble test
import vectorbt as vbt


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
