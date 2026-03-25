"""
VectorBT-based fitness evaluator for genetic trading algorithm.

Phases 1-3:
  Phase 1: Core 6-gene MA strategy + risk management
  Phase 2: Full population-level batch evaluation with chromosome dedup + K-fold
  Phase 3: Macro, TI filter, and ensemble signal gene support

Uses vectorbt for vectorized backtesting — population-level batch
evaluation replaces per-trader sequential backtrader runs.

Note: Stop-loss trigger timing differs from backtrader (same-bar close
vs next-bar open). Fitness rankings are consistent but not byte-for-byte
identical to backtrader results.
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import config
from genetic_trader import GeneticTrader


class VectorbtFitnessEvaluator:
    """
    Evaluates fitness of genetic traders using vectorbt.

    Population-level batching replaces ParallelFitnessEvaluator —
    MA computations are deduplicated and shared across traders.
    """

    def __init__(self, symbols: List[str], start_date: str, end_date: str):
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = config.INITIAL_CASH
        self.commission = config.COMMISSION

        # Select data source based on config
        data_source = getattr(config, 'DATA_SOURCE', 'sqlite')
        if data_source == 'yahoo':
            from yahoo_data_loader import YahooDataLoader
            loader = YahooDataLoader()
            print(f"\nLoading portfolio data from Yahoo Finance for {len(symbols)} stocks...")
        else:
            from data_loader import DataLoader
            loader = DataLoader(config.DATABASE_PATH)
            print(f"\nLoading portfolio data from SQLite for {len(symbols)} stocks...")

        self.data_feeds = {}

        for symbol in symbols:
            try:
                df = loader.load_stock_data(
                    symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                self.data_feeds[symbol] = df
                print(f"  + {symbol}: {len(df)} bars")
            except Exception as e:
                print(f"  - {symbol}: Failed to load - {e}")

        self.valid_symbols = list(self.data_feeds.keys())
        print(f"\nLoaded {len(self.valid_symbols)}/{len(symbols)} stocks")

        if len(self.valid_symbols) == 0:
            raise ValueError("No valid stock data loaded!")

        # Load macro data if enabled
        self.macro_df = None
        if getattr(config, 'USE_MACRO_DATA', False):
            try:
                macro_df = loader.load_macro_data(
                    start_date=start_date,
                    end_date=end_date
                )
                if macro_df is not None and not macro_df.empty:
                    self.macro_df = macro_df
                    self.macro_df.index = pd.to_datetime(self.macro_df.index)
                    available = [c for c in macro_df.columns if macro_df[c].notna().any()]
                    missing = [c for c in macro_df.columns if macro_df[c].isna().all()]
                    print(f"\n  Macro data loaded: {len(macro_df)} rows")
                    if available:
                        print(f"    Available: {', '.join(available)}")
                    if missing:
                        print(f"    Missing (neutral defaults): {', '.join(missing)}")
                else:
                    print("\n  Macro data: not available — macro genes will use neutral defaults")
            except Exception as e:
                print(f"\n  Macro data: not available ({e}) — macro genes will use neutral defaults")

        # Pre-compute fold boundaries
        self.folds = self._compute_folds()

        # Build master close price DataFrame for vectorbt
        self._close = pd.DataFrame({
            sym: df['close']
            for sym, df in self.data_feeds.items()
            if sym in self.valid_symbols
        })
        self._close.index = pd.to_datetime(self._close.index)
        self._close = self._close.sort_index()
        self._close = self._close.ffill()

        print(f"  Close matrix: {self._close.shape[0]} dates x {self._close.shape[1]} symbols")

        # --- Pre-compute all MA windows (one-time cost ~300ms) ---
        import time as _time
        _t0 = _time.time()
        all_windows = sorted(set(range(5, 101)))
        self._sma_cache = vbt.MA.run(self._close, window=all_windows, ewm=False)
        self._ema_cache = vbt.MA.run(self._close, window=all_windows, ewm=True)
        print(f"  Pre-computed {len(all_windows)} SMA+EMA windows: "
              f"{(_time.time()-_t0)*1000:.0f}ms")

        # --- Pre-align per-stock indicator data to the close index ---
        # Avoids repeated DataFrame.reindex() in ensemble/TI per trader
        _t0 = _time.time()
        self._aligned_indicators = {}
        indicator_cols = [
            'rsi', 'rsi_14', 'adx', 'adx_14', 'natr', 'atr_14',
            'mfi', 'mfi_14', 'macd', 'macd_signal', 'macdhist',
            'bb_upper', 'bb_lower', 'bb_middle',
            'bb_upper_20', 'bb_lower_20', 'bb_middle_20',
            'bb_top', 'bb_bot', 'bb_mid',
            'slowk', 'slowd', 'stoch_k', 'stoch_d',
            'signal',
        ]
        dates = self._close.index
        for symbol in self.valid_symbols:
            df = self.data_feeds[symbol]
            aligned = {}
            df_reindexed = df.reindex(dates, method='ffill')
            for col in indicator_cols:
                if col in df_reindexed.columns:
                    aligned[col] = df_reindexed[col].values
            self._aligned_indicators[symbol] = aligned
        print(f"  Pre-aligned indicator data for {len(self.valid_symbols)} symbols: "
              f"{(_time.time()-_t0)*1000:.0f}ms")

    def _compute_folds(self) -> List[Tuple[str, str]]:
        """
        Compute fold date boundaries from config.
        Copied verbatim from PortfolioFitnessEvaluator.
        """
        if not getattr(config, 'USE_KFOLD_VALIDATION', False):
            return [(self.start_date, self.end_date)]

        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        end = datetime.strptime(self.end_date, '%Y-%m-%d')
        total_days = (end - start).days

        fold_years = getattr(config, 'KFOLD_FOLD_YEARS', 3)
        fold_days = int(fold_years * 365.25)
        num_folds = getattr(config, 'KFOLD_NUM_FOLDS', 2)
        allow_overlap = getattr(config, 'KFOLD_ALLOW_OVERLAP', False)

        fold_days = min(fold_days, total_days)

        if num_folds <= 1:
            return [(self.start_date, self.end_date)]

        if allow_overlap:
            stride = (total_days - fold_days) / (num_folds - 1)
        else:
            stride = fold_days
            num_folds = min(num_folds, max(1, total_days // fold_days))

        folds = []
        for i in range(num_folds):
            fold_start = start + timedelta(days=int(i * stride))
            fold_end = fold_start + timedelta(days=fold_days - 1)
            fold_end = min(fold_end, end)
            folds.append((
                fold_start.strftime('%Y-%m-%d'),
                fold_end.strftime('%Y-%m-%d'),
            ))

        return folds

    def _score_results(self, results: Dict[str, Any]) -> float:
        """
        Compute fitness score from backtest results.
        Exact copy from PortfolioFitnessEvaluator.
        """
        if results['trade_count'] < config.MIN_TRADES_REQUIRED:
            return -100.0

        fitness = (
            config.FITNESS_WEIGHTS['total_return'] * results['total_return'] +
            config.FITNESS_WEIGHTS['sharpe_ratio'] * results['sharpe_ratio'] * 10 +
            config.FITNESS_WEIGHTS['max_drawdown'] * results['max_drawdown'] +
            config.FITNESS_WEIGHTS['win_rate'] * results['win_rate']
        )
        return fitness

    def _aggregate_fold_scores(
        self,
        fold_scores: List[Tuple[int, float]],
    ) -> float:
        """
        Aggregate per-fold fitness scores.
        Copied verbatim from PortfolioFitnessEvaluator.
        """
        use_weighting = getattr(config, 'KFOLD_WEIGHT_RECENT', False)
        weight_factor = getattr(config, 'KFOLD_RECENT_WEIGHT_FACTOR', 1.5)

        if not use_weighting:
            scores = [score for _, score in fold_scores]
            return sum(scores) / len(scores)

        num_folds = len(fold_scores)
        weights = []
        for i in range(num_folds):
            w = 1.0 + (weight_factor - 1.0) * (
                i / max(1, num_folds - 1)
            )
            weights.append(w)

        weighted_sum = sum(
            w * score
            for w, (_, score) in zip(weights, fold_scores)
        )
        total_weight = sum(weights)
        return weighted_sum / total_weight

    # ------------------------------------------------------------------
    # Phase 3: Macro gene vectorization
    # ------------------------------------------------------------------

    def _compute_macro_masks(self, close_slice: pd.DataFrame, genes: dict) -> dict:
        """
        Precompute macro regime modifiers as time-series arrays.

        Returns:
            block_buys: pd.Series (bool) — True means block buy on that day
            position_scale: pd.Series (float) — position size multiplier
            sl_adj: pd.Series (float) — stop-loss multiplier
            tp_adj: pd.Series (float) — take-profit multiplier
        """
        dates = close_slice.index

        block_buys = pd.Series(False, index=dates)
        position_scale = pd.Series(1.0, index=dates)
        sl_adj = pd.Series(1.0, index=dates)
        tp_adj = pd.Series(1.0, index=dates)

        if not genes.get("macro_enabled", 0) or self.macro_df is None:
            return dict(block_buys=block_buys, position_scale=position_scale,
                        sl_adj=sl_adj, tp_adj=tp_adj)

        weight = float(genes.get("macro_weight", 0.5))
        macro = self.macro_df.reindex(dates, method="ffill")
        adverse_count = pd.Series(0, index=dates)

        # VIX regime
        if "vix_close" in macro.columns and macro["vix_close"].notna().any():
            vix_thresh = float(genes.get("macro_vix_threshold", 30.0))
            vix_scale = float(genes.get("macro_vix_position_scale", 0.5))
            adverse = macro["vix_close"] > vix_thresh
            adverse_count += adverse.astype(int)
            position_scale = position_scale * (1.0 - weight * (1.0 - vix_scale) * adverse)

        # Yield curve regime
        if "yield_curve_slope" in macro.columns and macro["yield_curve_slope"].notna().any():
            yc_thresh = float(genes.get("macro_yc_threshold", 0.0))
            yc_action = int(genes.get("macro_yc_action", 0))
            adverse = macro["yield_curve_slope"] < yc_thresh
            adverse_count += adverse.astype(int)
            if yc_action == 1:
                position_scale = position_scale * (1.0 - weight * 0.5 * adverse)
            elif yc_action == 2:
                block_buys = block_buys | adverse

        # Fed funds rate
        if "fed_funds_rate" in macro.columns and macro["fed_funds_rate"].notna().any():
            rate_thresh = float(genes.get("macro_rate_threshold", 5.0))
            rate_scale = float(genes.get("macro_rate_position_scale", 0.7))
            adverse = macro["fed_funds_rate"] > rate_thresh
            adverse_count += adverse.astype(int)
            position_scale = position_scale * (1.0 - weight * (1.0 - rate_scale) * adverse)

        # CPI
        if "cpi_yoy" in macro.columns and macro["cpi_yoy"].notna().any():
            cpi_thresh = float(genes.get("macro_cpi_threshold", 5.0))
            cpi_scale = float(genes.get("macro_cpi_position_scale", 0.7))
            adverse = macro["cpi_yoy"] > cpi_thresh
            adverse_count += adverse.astype(int)
            position_scale = position_scale * (1.0 - weight * (1.0 - cpi_scale) * adverse)

        # Unemployment
        if "unemployment_rate" in macro.columns and macro["unemployment_rate"].notna().any():
            unemp_thresh = float(genes.get("macro_unemp_threshold", 6.0))
            unemp_action = int(genes.get("macro_unemp_action", 0))
            adverse = macro["unemployment_rate"] > unemp_thresh
            adverse_count += adverse.astype(int)
            if unemp_action == 1:
                position_scale = position_scale * (1.0 - weight * 0.5 * adverse)
            elif unemp_action == 2:
                block_buys = block_buys | adverse

        # Risk adjustments when enough regimes are adverse
        regime_req = int(genes.get("macro_regime_count_req", 2))
        enough_adverse = adverse_count >= regime_req
        stop_adj_gene = float(genes.get("macro_risk_stop_adj", 1.0))
        tp_adj_gene = float(genes.get("macro_risk_tp_adj", 1.0))
        sl_adj = sl_adj * (1.0 + (stop_adj_gene - 1.0) * enough_adverse)
        tp_adj = tp_adj * (1.0 + (tp_adj_gene - 1.0) * enough_adverse)

        # Floor position scale at 0.1
        position_scale = position_scale.clip(lower=0.1)

        return dict(block_buys=block_buys, position_scale=position_scale,
                    sl_adj=sl_adj, tp_adj=tp_adj)

    # ------------------------------------------------------------------
    # Phase 3: TI filter gene vectorization
    # ------------------------------------------------------------------

    def _compute_ti_masks(self, close_slice: pd.DataFrame, genes: dict) -> dict:
        """
        Precompute per-symbol TI filter masks as DataFrames.

        Returns:
            block_buys: pd.DataFrame (dates x symbols, bool)
            position_scale: pd.DataFrame (dates x symbols, float)
            force_exit: pd.DataFrame (dates x symbols, bool)
            sl_adj: pd.DataFrame (dates x symbols, float)
        """
        dates = close_slice.index
        symbols = close_slice.columns.tolist()

        block_buys = pd.DataFrame(False, index=dates, columns=symbols)
        position_scale = pd.DataFrame(1.0, index=dates, columns=symbols)
        force_exit = pd.DataFrame(False, index=dates, columns=symbols)
        sl_adj = pd.DataFrame(1.0, index=dates, columns=symbols)

        if not genes.get("ti_enabled", 0):
            return dict(block_buys=block_buys, position_scale=position_scale,
                        force_exit=force_exit, sl_adj=sl_adj)

        weight = float(genes.get("ti_weight", 0.5))

        for symbol in symbols:
            cached = self._aligned_indicators.get(symbol, {})
            if not cached:
                continue

            # Use pre-aligned numpy arrays; slice if needed for K-fold
            is_full = len(dates) == len(self._close.index)

            def _get_indicator(names):
                for name in names:
                    if name in cached:
                        arr = cached[name]
                        if is_full:
                            return pd.Series(arr, index=self._close.index)
                        return pd.Series(arr, index=self._close.index).reindex(dates, method='ffill')
                return None

            # RSI
            rsi = _get_indicator(["rsi", "rsi_14"])
            if rsi is not None:
                ob = float(genes.get("ti_rsi_overbought", 70))
                os_ = float(genes.get("ti_rsi_oversold", 30))
                block_buys[symbol] = block_buys[symbol] | (rsi > ob)
                position_scale[symbol] *= (1.0 + weight * 0.5 * (rsi < os_))

            # ADX
            adx = _get_indicator(["adx", "adx_14"])
            if adx is not None:
                adx_thresh = float(genes.get("ti_adx_threshold", 25))
                adx_scale = float(genes.get("ti_adx_position_scale", 0.5))
                weak_trend = adx < adx_thresh
                position_scale[symbol] *= (1.0 - weight * (1.0 - adx_scale) * weak_trend)

            # NATR
            natr = _get_indicator(["natr", "atr_14"])
            if natr is not None:
                natr_thresh = float(genes.get("ti_natr_threshold", 5.0))
                natr_action = int(genes.get("ti_natr_risk_action", 0))
                high_vol = natr > natr_thresh
                if natr_action == 0:
                    sl_adj[symbol] *= (1.0 - 0.3 * high_vol)
                elif natr_action == 1:
                    sl_adj[symbol] *= (1.0 + 0.5 * high_vol)
                elif natr_action == 2:
                    block_buys[symbol] = block_buys[symbol] | high_vol

            # MFI
            mfi = _get_indicator(["mfi", "mfi_14"])
            if mfi is not None:
                mfi_ob = float(genes.get("ti_mfi_overbought", 80))
                mfi_os = float(genes.get("ti_mfi_oversold", 20))
                position_scale[symbol] *= (1.0 - weight * 0.4 * (mfi > mfi_ob))
                position_scale[symbol] *= (1.0 + weight * 0.3 * (mfi < mfi_os))

            # MACD histogram
            macdhist = _get_indicator(["macdhist", "macd_signal", "macd"])
            if macdhist is not None:
                if genes.get("ti_macdhist_confirm", 0):
                    block_buys[symbol] = block_buys[symbol] | (macdhist <= 0)
                if genes.get("ti_macdhist_exit_confirm", 0):
                    force_exit[symbol] = force_exit[symbol] | (macdhist < 0)

        position_scale = position_scale.clip(lower=0.1)
        return dict(block_buys=block_buys, position_scale=position_scale,
                    force_exit=force_exit, sl_adj=sl_adj)

    # ------------------------------------------------------------------
    # Phase 3: Ensemble signal gene vectorization
    # ------------------------------------------------------------------

    def _compute_ensemble_signals(self, close_slice: pd.DataFrame, genes: dict,
                                   fast_ma: pd.DataFrame,
                                   slow_ma: pd.DataFrame) -> tuple:
        """
        Compute weighted ensemble entry/exit signals.

        Returns:
            ensemble_entries: pd.DataFrame (dates x symbols, bool) or None
            ensemble_exits: pd.DataFrame (dates x symbols, bool) or None
        """
        if not genes.get("ensemble_enabled", 0):
            return None, None

        dates = close_slice.index
        symbols = close_slice.columns.tolist()
        buy_thresh = float(genes.get("sig_buy_threshold", 0.3))
        sell_thresh = float(genes.get("sig_sell_threshold", -0.3))

        ma_weight = float(genes.get("sig_ma_weight", 0.5))
        bb_weight = float(genes.get("sig_bb_weight", 0.3))
        stoch_weight = float(genes.get("sig_stoch_weight", 0.3))
        macd_weight = float(genes.get("sig_macd_weight", 0.3))
        rsi_weight = float(genes.get("sig_rsi_weight", 0.3))
        total_weight = ma_weight + bb_weight + stoch_weight + macd_weight + rsi_weight

        combined = pd.DataFrame(0.0, index=dates, columns=symbols)

        # MA crossover signal: normalized spread
        spread = (fast_ma - slow_ma) / slow_ma.replace(0, np.nan)
        ma_signal = (spread * 10.0).clip(-1.0, 1.0)
        combined += ma_weight * ma_signal

        is_full = len(dates) == len(self._close.index)

        for symbol in symbols:
            cached = self._aligned_indicators.get(symbol, {})
            if not cached:
                continue

            def _get(names):
                for name in names:
                    if name in cached:
                        arr = cached[name]
                        if is_full:
                            return pd.Series(arr, index=self._close.index)
                        return pd.Series(arr, index=self._close.index).reindex(dates, method='ffill')
                return None

            # Bollinger Band signal
            bb_top = _get(["bb_top", "bb_upper", "bb_upper_20"])
            bb_bot = _get(["bb_bot", "bb_lower", "bb_lower_20"])
            bb_mid = _get(["bb_mid", "bb_middle", "bb_middle_20"])
            if bb_top is not None and bb_bot is not None and bb_mid is not None:
                width = bb_top - bb_bot
                half = width / 2.0
                pos = ((bb_mid - close_slice[symbol]) /
                       half.replace(0, np.nan)).clip(-1, 1)
                combined[symbol] += bb_weight * pos

            # Stochastic signal
            slowk = _get(["slowk", "stoch_k"])
            slowd = _get(["slowd", "stoch_d"])
            if slowk is not None and slowd is not None:
                stoch_ob = float(genes.get("sig_stoch_ob", 80))
                stoch_os = float(genes.get("sig_stoch_os", 20))
                mid = (stoch_ob + stoch_os) / 2.0
                half_r = (stoch_ob - stoch_os) / 2.0
                base = -(slowk - mid) / half_r
                base = base.clip(-1, 1)
                k_above_d = (slowk > slowd).astype(float)
                k_oversold = (slowk < stoch_os + 10).astype(float)
                k_overbought = (slowk > stoch_ob - 10).astype(float)
                boost = (0.3 * k_above_d * k_oversold -
                         0.3 * (1 - k_above_d) * k_overbought)
                combined[symbol] += stoch_weight * (base + boost).clip(-1, 1)

            # MACD signal
            macd_val = _get(["macd"])
            signal_val = _get(["signal", "macd_signal"])
            if macd_val is not None and signal_val is not None:
                hist = macd_val - signal_val
                norm = (hist / close_slice[symbol].replace(0, np.nan) *
                        100.0 * 2.0).clip(-1, 1)
                combined[symbol] += macd_weight * norm

            # RSI signal
            rsi = _get(["rsi", "rsi_14"])
            if rsi is not None:
                rsi_ob = float(genes.get("sig_rsi_ob", 70))
                rsi_os = float(genes.get("sig_rsi_os", 30))
                mid = (rsi_ob + rsi_os) / 2.0
                half_r = (rsi_ob - rsi_os) / 2.0
                rsi_signal = -(rsi - mid) / half_r
                combined[symbol] += rsi_weight * rsi_signal.clip(-1, 1)

        if total_weight > 0.01:
            combined = combined / total_weight

        entries = combined > buy_thresh
        exits = combined < sell_thresh
        return entries, exits

    # ------------------------------------------------------------------
    # Core backtest runner (Phase 3 wiring)
    # ------------------------------------------------------------------

    def _run_backtest(self, trader: GeneticTrader, close_slice: pd.DataFrame) -> Dict[str, Any]:
        """
        Run a single-trader backtest on a close price slice using vectorbt.

        Applies macro, TI filter, and ensemble signal masks when the
        corresponding genes are enabled; otherwise uses neutral defaults.
        Implements initial allocation matching backtrader's behavior.
        """
        genes = trader.get_genes()
        short = int(genes['ma_short_period'])
        long_ = int(genes['ma_long_period'])
        ma_type = int(genes['ma_type'])
        sl_stop = float(genes['stop_loss_pct']) / 100
        tp_stop = float(genes['take_profit_pct']) / 100
        position_size_pct = float(genes['position_size_pct']) / 100

        # Use pre-computed MA cache when evaluating full date range,
        # fall back to on-demand computation for K-fold slices
        is_full_range = (len(close_slice) == len(self._close)
                         and close_slice.index[0] == self._close.index[0])
        ewm = (ma_type == 1)
        ma_cache = self._ema_cache if ewm else self._sma_cache

        if is_full_range:
            # Lookup from pre-computed cache (near-zero cost)
            fast_ma = pd.DataFrame(
                ma_cache.ma[short].values,
                index=close_slice.index, columns=close_slice.columns
            )
            slow_ma = pd.DataFrame(
                ma_cache.ma[long_].values,
                index=close_slice.index, columns=close_slice.columns
            )
        else:
            # K-fold slice: compute on demand
            fast_ma_obj = vbt.MA.run(close_slice, window=short, ewm=ewm)
            slow_ma_obj = vbt.MA.run(close_slice, window=long_, ewm=ewm)
            fast_ma = pd.DataFrame(
                fast_ma_obj.ma.values,
                index=close_slice.index, columns=close_slice.columns
            )
            slow_ma = pd.DataFrame(
                slow_ma_obj.ma.values,
                index=close_slice.index, columns=close_slice.columns
            )

        # Phase 3: macro masks
        macro = self._compute_macro_masks(close_slice, genes)

        # Phase 3: TI masks
        ti = self._compute_ti_masks(close_slice, genes)

        # Combine block_buys: macro (broadcast to all symbols) + per-symbol TI
        macro_block = macro["block_buys"].values.reshape(-1, 1)
        combined_block = pd.DataFrame(
            macro_block | ti["block_buys"].values,
            index=close_slice.index, columns=close_slice.columns
        )

        # Combine position_scale: macro (broadcast) * per-symbol TI
        macro_scale = macro["position_scale"].values.reshape(-1, 1)
        combined_scale = pd.DataFrame(
            macro_scale * ti["position_scale"].values,
            index=close_slice.index, columns=close_slice.columns
        ).clip(lower=0.1)

        # Adjusted sl/tp: macro adjustments broadcast to all symbols
        macro_sl = macro["sl_adj"].values.reshape(-1, 1)
        macro_tp = macro["tp_adj"].values.reshape(-1, 1)
        adj_sl = pd.DataFrame(
            macro_sl * ti["sl_adj"].values,
            index=close_slice.index, columns=close_slice.columns
        )
        adj_tp = pd.DataFrame(
            np.broadcast_to(macro_tp, ti["sl_adj"].shape),
            index=close_slice.index, columns=close_slice.columns
        )

        # fast_ma / slow_ma are already clean DataFrames with matching columns

        # Phase 3: ensemble signals (or fall back to MA crossover)
        ens_entries, ens_exits = self._compute_ensemble_signals(
            close_slice, genes, fast_ma, slow_ma
        )

        if ens_entries is not None:
            entries = ens_entries & ~combined_block
            exits = ens_exits | ti["force_exit"]
        else:
            # MA crossover signals using plain numpy (avoids vbt overhead)
            fast_v = fast_ma.values
            slow_v = slow_ma.values
            cross_above = (fast_v[1:] > slow_v[1:]) & (fast_v[:-1] <= slow_v[:-1])
            cross_below = (fast_v[1:] < slow_v[1:]) & (fast_v[:-1] >= slow_v[:-1])
            entries_arr = np.vstack([np.zeros((1, fast_v.shape[1]), dtype=bool), cross_above])
            exits_arr = np.vstack([np.zeros((1, fast_v.shape[1]), dtype=bool), cross_below])
            entries = pd.DataFrame(entries_arr, index=close_slice.index,
                                   columns=close_slice.columns) & ~combined_block
            exits = pd.DataFrame(exits_arr, index=close_slice.index,
                                 columns=close_slice.columns) | ti["force_exit"]

        # Initial allocation: force buy on first valid bar for each stock
        # Matches backtrader's _make_initial_allocation() behavior
        initial_alloc_pct = getattr(config, 'INITIAL_ALLOCATION_PCT', 0.0)
        num_symbols = len(close_slice.columns)
        if initial_alloc_pct > 0:
            for col in close_slice.columns:
                valid_mask = close_slice[col].notna()
                if valid_mask.any():
                    first_valid_idx = valid_mask.idxmax()
                    entries.loc[first_valid_idx, col] = True

        # Determine if macro/TI genes modify stops per-bar
        macro_active = bool(genes.get('macro_enabled', 0)) and self.macro_df is not None
        ti_active = bool(genes.get('ti_enabled', 0))
        needs_variable_stops = macro_active or ti_active

        # Size: apply combined position scale
        size_array = (position_size_pct * combined_scale).values

        # Initial allocation sizing: on the first bar, buy an equal share
        # of the allocation capital for each stock.
        if initial_alloc_pct > 0:
            alloc_per_stock = (initial_alloc_pct / 100.0) / num_symbols
            for col_idx, col in enumerate(close_slice.columns):
                valid_mask = close_slice[col].notna()
                if valid_mask.any():
                    first_valid_idx = valid_mask.idxmax()
                    row_idx = close_slice.index.get_loc(first_valid_idx)
                    size_array[row_idx, col_idx] = alloc_per_stock

        if needs_variable_stops:
            # Per-bar varying stops when macro/TI modify them
            sl_param = (sl_stop * adj_sl).values
            tp_param = (tp_stop * adj_tp).values
        else:
            # Scalar stops — faster path (~20% less overhead)
            sl_param = sl_stop
            tp_param = tp_stop

        pf = vbt.Portfolio.from_signals(
            close=close_slice,
            entries=entries,
            exits=exits,
            sl_stop=sl_param,
            tp_stop=tp_param,
            size=size_array,
            size_type='percent',
            init_cash=config.INITIAL_CASH,
            cash_sharing=True,
            group_by=True,
            fees=config.COMMISSION,
            freq='D',
            call_seq='auto',
        )

        return self._extract_results(pf)

    def _extract_results(self, pf) -> Dict[str, Any]:
        """Extract standardized results dict from a vectorbt Portfolio."""
        # With cash_sharing=True + group_by=True, pf returns portfolio-level
        # scalars directly (not per-symbol).
        starting_value = float(pf.init_cash)
        ending_value = float(pf.final_value())
        total_return = ((ending_value - starting_value) / starting_value) * 100

        # Portfolio-level Sharpe from the grouped portfolio value series
        portfolio_value = pf.value()
        daily_returns = portfolio_value.pct_change().dropna()
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe_ratio = float(daily_returns.mean() / daily_returns.std() * np.sqrt(252))
        else:
            sharpe_ratio = 0.0

        # Portfolio-level max drawdown
        cummax = portfolio_value.cummax()
        drawdowns = (portfolio_value - cummax) / cummax
        max_drawdown = float(drawdowns.min()) * 100  # negative percentage

        # Clamp Sharpe to same range as backtrader evaluator
        if np.isnan(sharpe_ratio):
            sharpe_ratio = 0.0
        sharpe_ratio = max(-5.0, min(5.0, sharpe_ratio))

        trade_records = pf.trades.records_readable
        total_trades = len(trade_records)
        won_trades = int((trade_records['PnL'] > 0).sum()) if total_trades > 0 else 0
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0.0

        # Per-stock performance
        per_stock = {}
        for symbol in self.valid_symbols:
            sym_trades = trade_records[trade_records['Column'] == symbol]
            won = int((sym_trades['PnL'] > 0).sum())
            total = len(sym_trades)
            per_stock[symbol] = {
                'trades': total,
                'won': won,
                'lost': int(total - won),
                'pnl': round(float(sym_trades['PnL'].sum()), 2) if total > 0 else 0.0,
                'win_rate': (won / total * 100) if total > 0 else 0.0,
            }

        return {
            'starting_value': starting_value,
            'ending_value': ending_value,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trade_count': total_trades,
            'winning_trades': won_trades,
            'per_stock_performance': per_stock,
        }

    def calculate_fitness(self, trader: GeneticTrader) -> float:
        """
        Calculate fitness score for a trader across the portfolio.
        Supports K-fold temporal cross-validation.
        """
        try:
            if len(self.folds) == 1:
                results = self._run_backtest(trader, self._close)
                return self._score_results(results)

            fold_scores = []
            min_bars = getattr(config, 'KFOLD_MIN_BARS_PER_FOLD', 200)

            for fold_idx, (fold_start, fold_end) in enumerate(self.folds):
                close_slice = self._close.loc[fold_start:fold_end]
                if len(close_slice) < min_bars:
                    continue
                results = self._run_backtest(trader, close_slice)
                fold_scores.append((fold_idx, self._score_results(results)))

            if not fold_scores:
                return -100.0
            return self._aggregate_fold_scores(fold_scores)

        except Exception as e:
            print(f"Error evaluating trader: {e}")
            return -1000.0

    # ------------------------------------------------------------------
    # Phase 2: Population-level batch evaluation with dedup + K-fold
    # ------------------------------------------------------------------

    def evaluate_population(self, traders: List[GeneticTrader]) -> List[GeneticTrader]:
        """
        Evaluate all traders using batch MA computation.

        Phase 2 upgrades:
        - Full chromosome dedup: identical (short, long, ma_type, sl, tp, sz)
          tuples run only once
        - K-fold support: respects self.folds the same way calculate_fitness() does
        - Progress reporting
        """
        # Extract chromosome keys for dedup
        def _chrom_key(t):
            g = t.get_genes()
            return (
                int(g['ma_short_period']),
                int(g['ma_long_period']),
                int(g['ma_type']),
                round(float(g['stop_loss_pct']), 6),
                round(float(g['take_profit_pct']), 6),
                round(float(g['position_size_pct']), 6),
            )

        dedup_enabled = getattr(config, 'VECTORBT_DEDUP', True)

        # Build dedup map: key -> list of trader indices
        key_to_indices = {}
        for i, t in enumerate(traders):
            k = _chrom_key(t)
            key_to_indices.setdefault(k, []).append(i)

        unique_count = len(key_to_indices) if dedup_enabled else len(traders)
        print(f"Generation batch: evaluating {len(traders)} traders "
              f"({unique_count} unique param combos)")

        if dedup_enabled:
            # Evaluate each unique chromosome once, assign fitness to all copies
            for key, indices in key_to_indices.items():
                representative = traders[indices[0]]
                try:
                    fitness = self._calculate_fitness_for_trader(representative)
                except Exception as e:
                    print(f"Error evaluating trader group {key}: {e}")
                    fitness = -1000.0
                for idx in indices:
                    traders[idx].set_fitness(fitness)
        else:
            # No dedup: evaluate each trader individually
            for i, trader in enumerate(traders):
                try:
                    fitness = self._calculate_fitness_for_trader(trader)
                except Exception as e:
                    print(f"Error evaluating trader {i}: {e}")
                    fitness = -1000.0
                trader.set_fitness(fitness)

        return traders

    def _calculate_fitness_for_trader(self, trader: GeneticTrader) -> float:
        """
        Calculate fitness for a trader respecting K-fold configuration.
        Used by evaluate_population() to share fold logic with calculate_fitness().
        """
        if len(self.folds) == 1:
            results = self._run_backtest(trader, self._close)
            return self._score_results(results)

        fold_scores = []
        min_bars = getattr(config, 'KFOLD_MIN_BARS_PER_FOLD', 200)

        for fold_idx, (fold_start, fold_end) in enumerate(self.folds):
            close_slice = self._close.loc[fold_start:fold_end]
            if len(close_slice) < min_bars:
                continue
            results = self._run_backtest(trader, close_slice)
            fold_scores.append((fold_idx, self._score_results(results)))

        if not fold_scores:
            return -100.0
        return self._aggregate_fold_scores(fold_scores)

    def get_detailed_results(self, trader: GeneticTrader) -> Dict[str, Any]:
        """
        Get detailed backtest results for a trader.
        Returns same dict shape as PortfolioFitnessEvaluator.
        """
        if len(self.folds) == 1:
            results = self._run_backtest(trader, self._close)
            results['genes'] = trader.get_genes()
            results['fitness'] = self.calculate_fitness(trader)
            results['num_stocks'] = len(self.valid_symbols)
            results['symbols'] = self.valid_symbols
            return results

        # K-fold: collect per-fold results
        fold_results = []
        min_bars = getattr(config, 'KFOLD_MIN_BARS_PER_FOLD', 200)

        for fold_idx, (fold_start, fold_end) in enumerate(self.folds):
            close_slice = self._close.loc[fold_start:fold_end]
            if len(close_slice) < min_bars:
                fold_results.append({
                    'fold': fold_idx + 1,
                    'period': f"{fold_start} to {fold_end}",
                    'skipped': True,
                })
                continue

            results = self._run_backtest(trader, close_slice)
            results['fold'] = fold_idx + 1
            results['period'] = f"{fold_start} to {fold_end}"
            results['num_stocks_in_fold'] = len(self.valid_symbols)
            results['skipped'] = False
            fold_results.append(results)

        # Aggregate for summary
        valid = [r for r in fold_results if not r.get('skipped')]
        aggregate = {
            'total_return': np.mean([r['total_return'] for r in valid]),
            'sharpe_ratio': np.mean([r['sharpe_ratio'] for r in valid]),
            'max_drawdown': np.mean([r['max_drawdown'] for r in valid]),
            'win_rate': np.mean([r['win_rate'] for r in valid]),
            'trade_count': sum(r['trade_count'] for r in valid),
            'winning_trades': sum(r['winning_trades'] for r in valid),
        }

        # Aggregate per-stock data across folds
        combined_per_stock = {}
        for r in valid:
            for sym, data in r.get('per_stock_performance', {}).items():
                if sym not in combined_per_stock:
                    combined_per_stock[sym] = {
                        'trades': 0, 'won': 0, 'lost': 0, 'pnl': 0.0,
                    }
                combined_per_stock[sym]['trades'] += data['trades']
                combined_per_stock[sym]['won'] += data['won']
                combined_per_stock[sym]['lost'] += data['lost']
                combined_per_stock[sym]['pnl'] += data['pnl']
        for sym, data in combined_per_stock.items():
            data['win_rate'] = (
                (data['won'] / data['trades'] * 100)
                if data['trades'] > 0 else 0.0
            )
            data['pnl'] = round(data['pnl'], 2)
        aggregate['per_stock_performance'] = combined_per_stock

        aggregate['genes'] = trader.get_genes()
        aggregate['fitness'] = self.calculate_fitness(trader)
        aggregate['num_stocks'] = len(self.valid_symbols)
        aggregate['symbols'] = self.valid_symbols
        aggregate['kfold_results'] = fold_results

        return aggregate
