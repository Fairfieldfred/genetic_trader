"""
Tradix strategy adapter for genetic traders.

Equivalent of bt_strategy.py but using Tradix's MultiAssetStrategy engine.
Converts GeneticTrader genes into a Tradix trading strategy with identical
logic to PortfolioGeneticStrategy: MA crossover, macro context, technical
indicator filters, and ensemble signals.
"""

import math
from tradix import MultiAssetStrategy
from genetic_trader import GeneticTrader


class TradixPortfolioStrategy(MultiAssetStrategy):
    """
    Multi-asset strategy using Tradix engine.

    Port of PortfolioGeneticStrategy from bt_strategy.py.
    All trading logic (macro context, TI filters, ensemble signals,
    stop loss, take profit) is preserved identically.

    Gene parameters and supplementary data (pre-computed TI + macro
    columns) are passed via self._gene_params and self._supp_data,
    set by the fitness evaluator before the engine runs.
    """

    def initialize(self):
        """Set up tracking state. Called once at start."""
        # Trade tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.trades_by_symbol = {}

        # Per-symbol buy price tracking for stop loss / take profit
        self.buy_prices = {}

        # Pending order tracking to prevent duplicates
        self._pending = set()

        # Initial allocation
        self._initial_done = False
        self._bars_seen = 0

    # ------------------------------------------------------------------
    # Gene parameter access helpers
    # ------------------------------------------------------------------

    def _p(self, name, default=None):
        """Read a gene parameter by name."""
        return self._gene_params.get(name, default)

    def _get_supp(self, symbol, col_name, bar):
        """
        Read a supplementary data column value for the current bar.

        Supplementary data contains pre-computed TI and macro columns
        merged onto each stock's DataFrame, keyed by symbol.

        Args:
            symbol: Stock ticker.
            col_name: Column name (e.g. 'rsi', 'vix_close').
            bar: Current Bar object (used for date lookup).

        Returns:
            Float value or None if unavailable/NaN.
        """
        supp = self._supp_data.get(symbol)
        if supp is None:
            return None

        if col_name not in supp.columns:
            return None

        # bar.datetime is a datetime object; normalize to date for index lookup
        dt = bar.datetime
        if hasattr(dt, 'date'):
            dt = dt.date()

        # Try exact match first, then nearest previous
        try:
            if dt in supp.index:
                val = supp.at[dt, col_name]
            elif hasattr(supp.index, 'get_indexer'):
                idx = supp.index.get_indexer([dt], method='ffill')[0]
                if idx < 0:
                    return None
                val = supp.iloc[idx][col_name]
            else:
                return None
        except (KeyError, IndexError, TypeError):
            return None

        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None
        return val

    # ------------------------------------------------------------------
    # Main trading loop
    # ------------------------------------------------------------------

    def onBars(self, bars):
        """Process all symbols on each bar."""
        self._bars_seen += 1

        # Initial allocation on first bar
        if not self._initial_done:
            self._make_initial_allocation(bars)
            return

        # Compute macro context once per bar (shared across all stocks)
        macro = self._compute_macro_context(bars)

        for symbol, bar in bars.items():
            # Skip if we have a pending order for this symbol
            if symbol in self._pending:
                continue

            # Compute per-stock technical indicator context
            ti = self._compute_technical_context(symbol, bar)

            # Compute new context modifiers
            adv_osc = self._compute_advanced_oscillator_context(symbol, bar)
            trend_sig = self._compute_trend_signal_context(symbol, bar)
            vol_sig = self._compute_volume_signal_context(symbol, bar)
            vb = self._compute_volatility_breakout_context(symbol, bar)
            sr = self._compute_support_resistance_context(symbol, bar)
            regime_ctx = self._compute_regime_context(symbol, bar)

            # Combine all contexts
            block_buys = (macro['block_buys'] or ti['block_buys'] or
                          adv_osc.get('block_buys', False) or trend_sig.get('block_buys', False) or
                          vol_sig.get('block_buys', False) or vb.get('block_buys', False) or
                          sr.get('block_buys', False) or regime_ctx.get('block_buys', False))
            position_scale = (macro['position_scale'] * ti['position_scale'] *
                              adv_osc.get('position_scale', 1.0) * vol_sig.get('position_scale', 1.0))
            stop_loss_adj = macro['stop_loss_adj'] * ti['stop_loss_adj']
            take_profit_adj = macro['take_profit_adj'] * ti['take_profit_adj']

            # Get current position
            pos = self.getPosition(symbol)
            position_size = pos.quantity if pos else 0

            # Compute ensemble signal if enabled
            use_ensemble = self._p('ensemble_enabled', 0)
            ens_buy = False
            ens_sell = False
            if use_ensemble:
                _, ens_buy, ens_sell = self._compute_ensemble_signal(
                    symbol, bar
                )

            # --- BUY logic ---
            if position_size == 0:
                # Check for MA crossover buy signal
                ma_short_val = self._get_ma(symbol, 'short')
                ma_long_val = self._get_ma(symbol, 'long')
                prev_short = self._get_ma(symbol, 'short', offset=1)
                prev_long = self._get_ma(symbol, 'long', offset=1)

                crossover_buy = (
                    ma_short_val is not None
                    and ma_long_val is not None
                    and prev_short is not None
                    and prev_long is not None
                    and prev_short <= prev_long
                    and ma_short_val > ma_long_val
                )

                buy_triggered = ens_buy if use_ensemble else crossover_buy

                if buy_triggered:
                    if block_buys:
                        continue

                    sizing = self._p('sizing_model', 0)
                    if sizing in (1, 3):
                        size = self._compute_position_size_direct(symbol, bar, position_scale)
                    elif sizing == 2:
                        adjusted_pct = self._p('position_size_pct', 10.0) * position_scale * self._p('kelly_fraction', 0.5)
                        available_cash = self.cash
                        size = int((available_cash * adjusted_pct / 100) / bar.close)
                    else:
                        adjusted_pct = self._p('position_size_pct', 10.0) * position_scale
                        available_cash = self.cash
                        size = int((available_cash * adjusted_pct / 100) / bar.close)

                    if size > 0:
                        self.buy(symbol, size)
                        self._pending.add(symbol)

            # --- SELL logic ---
            else:
                current_price = bar.close

                # TI-driven early exit (MACD histogram confirmation)
                if ti['force_exit']:
                    self.sell(symbol, position_size)
                    self._pending.add(symbol)
                    continue

                buy_price = self.buy_prices.get(symbol)
                if buy_price and buy_price > 0:
                    pct_change = ((current_price - buy_price) / buy_price) * 100

                    adj_stop = self._p('stop_loss_pct', 2.5) * stop_loss_adj
                    adj_tp = self._p('take_profit_pct', 5.0) * take_profit_adj

                    # Stop loss
                    if pct_change <= -adj_stop:
                        self.sell(symbol, position_size)
                        self._pending.add(symbol)

                    # Take profit
                    elif pct_change >= adj_tp:
                        self.sell(symbol, position_size)
                        self._pending.add(symbol)

                    # Ensemble sell
                    elif use_ensemble and ens_sell:
                        self.sell(symbol, position_size)
                        self._pending.add(symbol)

                    # MA bearish crossover (fallback when ensemble disabled)
                    elif not use_ensemble:
                        ma_short_val = self._get_ma(symbol, 'short')
                        ma_long_val = self._get_ma(symbol, 'long')
                        prev_short = self._get_ma(symbol, 'short', offset=1)
                        prev_long = self._get_ma(symbol, 'long', offset=1)

                        crossover_sell = (
                            ma_short_val is not None
                            and ma_long_val is not None
                            and prev_short is not None
                            and prev_long is not None
                            and prev_short >= prev_long
                            and ma_short_val < ma_long_val
                        )
                        if crossover_sell:
                            self.sell(symbol, position_size)
                            self._pending.add(symbol)

    # ------------------------------------------------------------------
    # Order fill tracking
    # ------------------------------------------------------------------

    def onOrderFill(self, fill):
        """Track fills for trade statistics and buy price recording."""
        # FillEvent has: fill.order (Order), fill.fillPrice, fill.fillQuantity,
        # fill.commission. Order has order.symbol, order.side (OrderSide enum).
        symbol = fill.order.symbol
        self._pending.discard(symbol)

        is_buy = fill.order.side.name == 'BUY'

        if is_buy:
            self.buy_prices[symbol] = fill.fillPrice
        else:
            # Record trade result
            buy_price = self.buy_prices.get(symbol)
            if buy_price and buy_price > 0:
                pnl = (fill.fillPrice - buy_price) * fill.fillQuantity
                # Account for commission
                pnl -= fill.commission

                self.trade_count += 1
                if pnl > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1

                if symbol not in self.trades_by_symbol:
                    self.trades_by_symbol[symbol] = {
                        'trades': 0, 'won': 0, 'lost': 0, 'pnl': 0.0,
                    }
                entry = self.trades_by_symbol[symbol]
                entry['trades'] += 1
                if pnl > 0:
                    entry['won'] += 1
                else:
                    entry['lost'] += 1
                entry['pnl'] += pnl

                self.buy_prices.pop(symbol, None)

    # ------------------------------------------------------------------
    # Moving average helpers
    # ------------------------------------------------------------------

    def _get_ma(self, symbol, which, offset=0):
        """
        Get moving average value for a symbol using Tradix built-in indicators.

        Args:
            symbol: Stock ticker.
            which: 'short' or 'long'.
            offset: 0 = current bar, 1 = previous bar.

        Returns:
            Float MA value or None.
        """
        if which == 'short':
            period = self._p('ma_short_period', 10)
        else:
            period = self._p('ma_long_period', 50)

        ma_type = self._p('ma_type', 0)

        if ma_type == 0:
            return self.sma(symbol, period, offset=offset)
        else:
            return self.ema(symbol, period, offset=offset)

    # ------------------------------------------------------------------
    # Initial allocation
    # ------------------------------------------------------------------

    def _make_initial_allocation(self, bars):
        """Make equal-dollar initial purchases across all stocks."""
        if self._initial_done:
            return

        allocation_pct = self._p('initial_allocation_pct', 0.0)
        if allocation_pct <= 0:
            self._initial_done = True
            return

        total_cash = self.cash
        allocation_capital = total_cash * (allocation_pct / 100.0)
        num_stocks = len(bars)
        if num_stocks == 0:
            self._initial_done = True
            return

        per_stock_capital = allocation_capital / num_stocks

        for symbol, bar in bars.items():
            price = bar.close
            if math.isnan(price) or price <= 0:
                continue

            shares = int(per_stock_capital / price)
            if shares > 0:
                self.buy(symbol, shares)

        self._initial_done = True

    # ------------------------------------------------------------------
    # Macro context (identical logic to bt_strategy.py L508-583)
    # ------------------------------------------------------------------

    def _compute_macro_context(self, bars):
        """
        Evaluate current macroeconomic conditions and return modifiers.

        Reads macro data from supplementary DataFrame of the first symbol.
        Returns a dict of modifiers that adjust the base MA strategy.
        """
        context = {
            'position_scale': 1.0,
            'block_buys': False,
            'stop_loss_adj': 1.0,
            'take_profit_adj': 1.0,
        }

        if not self._p('macro_enabled', 0):
            return context

        weight = self._p('macro_weight', 0.5)

        # Use first symbol's bar for macro data lookup
        first_symbol = next(iter(bars))
        bar = bars[first_symbol]
        adverse_count = 0

        # VIX regime
        vix = self._get_supp(first_symbol, 'vix_close', bar)
        if vix is not None:
            if vix > self._p('macro_vix_threshold', 30.0):
                adverse_count += 1
                scale = self._p('macro_vix_position_scale', 0.5)
                context['position_scale'] *= 1.0 - weight * (1.0 - scale)

        # Yield curve regime
        yc = self._get_supp(first_symbol, 'yield_curve_slope', bar)
        if yc is not None:
            if yc < self._p('macro_yc_threshold', 0.0):
                adverse_count += 1
                action = self._p('macro_yc_action', 0)
                if action == 1:
                    context['position_scale'] *= 1.0 - weight * 0.5
                elif action == 2:
                    context['block_buys'] = True

        # Interest rate regime
        rate = self._get_supp(first_symbol, 'fed_funds_rate', bar)
        if rate is not None:
            if rate > self._p('macro_rate_threshold', 5.0):
                adverse_count += 1
                scale = self._p('macro_rate_position_scale', 0.7)
                context['position_scale'] *= 1.0 - weight * (1.0 - scale)

        # CPI / inflation regime
        cpi = self._get_supp(first_symbol, 'cpi_yoy', bar)
        if cpi is not None:
            if cpi > self._p('macro_cpi_threshold', 5.0):
                adverse_count += 1
                scale = self._p('macro_cpi_position_scale', 0.7)
                context['position_scale'] *= 1.0 - weight * (1.0 - scale)

        # Unemployment regime
        unemp = self._get_supp(first_symbol, 'unemployment_rate', bar)
        if unemp is not None:
            if unemp > self._p('macro_unemp_threshold', 6.0):
                adverse_count += 1
                action = self._p('macro_unemp_action', 0)
                if action == 1:
                    context['position_scale'] *= 1.0 - weight * 0.5
                elif action == 2:
                    context['block_buys'] = True

        # Apply risk adjustments when enough regimes are adverse
        if adverse_count >= self._p('macro_regime_count_req', 2):
            context['stop_loss_adj'] = self._p('macro_risk_stop_adj', 1.0)
            context['take_profit_adj'] = self._p('macro_risk_tp_adj', 1.0)

        # Floor position scale at 0.1 to avoid zero-size orders
        context['position_scale'] = max(0.1, context['position_scale'])

        return context

    # ------------------------------------------------------------------
    # Technical indicator context (identical logic to bt_strategy.py L585-658)
    # ------------------------------------------------------------------

    def _compute_technical_context(self, symbol, bar):
        """
        Evaluate per-stock technical indicator conditions.

        Unlike macro context (global), this is computed per stock
        since each stock has its own RSI, ADX, etc.

        Returns dict with position_scale, block_buys, stop_loss_adj,
        take_profit_adj, and force_exit modifiers.
        """
        context = {
            'position_scale': 1.0,
            'block_buys': False,
            'stop_loss_adj': 1.0,
            'take_profit_adj': 1.0,
            'force_exit': False,
        }

        if not self._p('ti_enabled', 0):
            return context

        weight = self._p('ti_weight', 0.5)

        # RSI filter
        rsi = self._get_supp(symbol, 'rsi', bar)
        if rsi is not None:
            if rsi > self._p('ti_rsi_overbought', 70):
                context['block_buys'] = True
            elif rsi < self._p('ti_rsi_oversold', 30):
                context['position_scale'] *= 1.0 + weight * 0.5

        # ADX filter
        adx = self._get_supp(symbol, 'adx', bar)
        if adx is not None:
            if adx < self._p('ti_adx_threshold', 25):
                scale = self._p('ti_adx_position_scale', 0.5)
                context['position_scale'] *= 1.0 - weight * (1.0 - scale)

        # NATR filter
        natr = self._get_supp(symbol, 'natr', bar)
        if natr is not None:
            if natr > self._p('ti_natr_threshold', 5.0):
                action = self._p('ti_natr_risk_action', 0)
                if action == 0:
                    context['stop_loss_adj'] *= 0.7
                elif action == 1:
                    context['stop_loss_adj'] *= 1.5
                elif action == 2:
                    context['block_buys'] = True

        # MFI filter
        mfi = self._get_supp(symbol, 'mfi', bar)
        if mfi is not None:
            if mfi > self._p('ti_mfi_overbought', 80):
                context['position_scale'] *= 1.0 - weight * 0.4
            elif mfi < self._p('ti_mfi_oversold', 20):
                context['position_scale'] *= 1.0 + weight * 0.3

        # MACD histogram confirmation
        macdhist = self._get_supp(symbol, 'macdhist', bar)
        if macdhist is not None:
            if self._p('ti_macdhist_confirm', 0) and macdhist <= 0:
                context['block_buys'] = True
            if self._p('ti_macdhist_exit_confirm', 0) and macdhist < 0:
                context['force_exit'] = True

        # Floor position scale
        context['position_scale'] = max(0.1, context['position_scale'])

        return context

    # ------------------------------------------------------------------
    # Advanced oscillator context
    # ------------------------------------------------------------------

    def _compute_advanced_oscillator_context(self, symbol, bar):
        """Evaluate advanced oscillator conditions."""
        if not self._p('adv_osc_enabled', 0):
            return {'block_buys': False, 'position_scale': 1.0}
        block = False
        scale = 1.0
        wr_val = self._get_supp(symbol, 'wr', bar)
        if wr_val is not None:
            if wr_val > self._p('wr_overbought', -20):
                block = True
            elif wr_val < self._p('wr_oversold', -80):
                scale *= 1.1
        cci_val = self._get_supp(symbol, 'cci', bar)
        if cci_val is not None:
            if cci_val > self._p('cci_overbought', 100):
                block = True
            elif cci_val < self._p('cci_oversold', -100):
                scale *= 1.1
        cmo_val = self._get_supp(symbol, 'cmo', bar)
        if cmo_val is not None:
            if abs(cmo_val) < self._p('cmo_threshold', 25.0):
                scale *= 0.7
        ao_val = self._get_supp(symbol, 'ao', bar)
        if ao_val is not None and self._p('ao_zero_cross_confirm', 0):
            if ao_val < 0:
                block = True
        stochrsi_k_val = self._get_supp(symbol, 'stochrsi_k', bar)
        if stochrsi_k_val is not None and stochrsi_k_val > self._p('stochrsi_ob', 80.0):
            block = True
        uo_val = self._get_supp(symbol, 'uo', bar)
        if uo_val is not None:
            if uo_val > self._p('uo_overbought', 70.0):
                block = True
            elif uo_val < self._p('uo_oversold', 30.0):
                scale *= 1.1
        roc_val = self._get_supp(symbol, 'roc', bar)
        roc_thresh = self._p('roc_threshold', 0.0)
        if roc_val is not None and roc_thresh != 0:
            if roc_thresh > 0 and roc_val < roc_thresh:
                block = True
            elif roc_thresh < 0 and roc_val > roc_thresh:
                block = True
        scale = max(0.1, scale)
        return {'block_buys': block, 'position_scale': scale}

    # ------------------------------------------------------------------
    # Trend signal context
    # ------------------------------------------------------------------

    def _compute_trend_signal_context(self, symbol, bar):
        """Evaluate trend signal conditions."""
        if not self._p('trend_sig_enabled', 0):
            return {'block_buys': False}
        block = False
        close_val = bar.close
        if self._p('psar_filter_enabled', 0):
            psar_val = self._get_supp(symbol, 'psar', bar)
            if psar_val is not None and close_val < psar_val:
                block = True
        if self._p('supertrend_filter_enabled', 0):
            st_dir = self._get_supp(symbol, 'supertrend_dir', bar)
            if st_dir is not None and st_dir < 0:
                block = True
        if self._p('ichimoku_cloud_filter', 0):
            ichi_val = self._get_supp(symbol, 'ichimoku_above_cloud', bar)
            if ichi_val is not None and ichi_val < 0:
                block = True
        lr_slope_val = self._get_supp(symbol, 'linreg_slope', bar)
        if lr_slope_val is not None and lr_slope_val < self._p('linreg_slope_min', -999.0):
            block = True
        lr_r2_val = self._get_supp(symbol, 'linreg_r2', bar)
        if lr_r2_val is not None and lr_r2_val < self._p('linreg_r2_min', 0.0):
            block = True
        if self._p('trix_zero_confirm', 0):
            trix_val = self._get_supp(symbol, 'trix', bar)
            if trix_val is not None and trix_val < 0:
                block = True
        return {'block_buys': block}

    # ------------------------------------------------------------------
    # Volume signal context
    # ------------------------------------------------------------------

    def _compute_volume_signal_context(self, symbol, bar):
        """Evaluate volume signal conditions."""
        if not self._p('vol_sig_enabled', 0):
            return {'block_buys': False, 'position_scale': 1.0}
        block = False
        scale = 1.0
        close_val = bar.close
        chaikin_thresh = self._p('chaikin_threshold', 0.0)
        if chaikin_thresh > 0:
            ch_val = self._get_supp(symbol, 'chaikin', bar)
            if ch_val is not None and ch_val < chaikin_thresh:
                block = True
        if self._p('force_index_confirm', 0):
            fi_val = self._get_supp(symbol, 'force_index', bar)
            if fi_val is not None and fi_val < 0:
                block = True
        vwap_mode = self._p('vwap_filter_mode', 0)
        if vwap_mode == 1:
            vwap_val = self._get_supp(symbol, 'vwap', bar)
            if vwap_val is not None and close_val > vwap_val:
                block = True
        elif vwap_mode == 2:
            vwap_val = self._get_supp(symbol, 'vwap', bar)
            if vwap_val is not None and close_val < vwap_val:
                block = True
        if self._p('vwma_vs_sma_confirm', 0):
            vwma_val = self._get_supp(symbol, 'vwma_20', bar)
            sma_val = self._get_supp(symbol, 'sma_20', bar)
            if vwma_val is not None and sma_val is not None and vwma_val < sma_val:
                block = True
        if self._p('klinger_confirm', 0):
            kl_val = self._get_supp(symbol, 'klinger', bar)
            kl_sig = self._get_supp(symbol, 'klinger_signal', bar)
            if kl_val is not None and kl_sig is not None and kl_val < kl_sig:
                block = True
        if self._p('nvi_trend_confirm', 0):
            nvi_val = self._get_supp(symbol, 'nvi', bar)
            nvi_sma_val = self._get_supp(symbol, 'nvi_sma', bar)
            if nvi_val is not None and nvi_sma_val is not None and nvi_val < nvi_sma_val:
                block = True
        return {'block_buys': block, 'position_scale': scale}

    # ------------------------------------------------------------------
    # Volatility breakout context
    # ------------------------------------------------------------------

    def _compute_volatility_breakout_context(self, symbol, bar):
        """Evaluate volatility and breakout conditions."""
        if not self._p('vb_enabled', 0):
            return {'block_buys': False}
        block = False
        close_val = bar.close
        if self._p('donchian_breakout_confirm', 0):
            dc_upper = self._get_supp(symbol, 'donchian_upper', bar)
            if dc_upper is not None and close_val < dc_upper:
                block = True
        if self._p('keltner_filter_enabled', 0):
            kelt_upper = self._get_supp(symbol, 'keltner_upper', bar)
            if kelt_upper is not None and close_val > kelt_upper:
                block = True
        bb_pct_b_val = self._get_supp(symbol, 'bb_pct_b', bar)
        if bb_pct_b_val is not None:
            if bb_pct_b_val > (1.0 - self._p('bb_pct_b_threshold', 1.0)):
                block = True
        bb_w_val = self._get_supp(symbol, 'bb_width', bar)
        if bb_w_val is not None and bb_w_val < self._p('bb_squeeze_threshold', 2.0):
            block = True
        ulcer_val = self._get_supp(symbol, 'ulcer', bar)
        if ulcer_val is not None and ulcer_val > self._p('ulcer_max', 999.0):
            block = True
        return {'block_buys': block}

    # ------------------------------------------------------------------
    # Support / resistance context
    # ------------------------------------------------------------------

    def _compute_support_resistance_context(self, symbol, bar):
        """Evaluate support and resistance conditions."""
        if not self._p('sr_enabled', 0):
            return {'block_buys': False}
        block = False
        close_val = bar.close
        if self._p('pivot_filter_enabled', 0):
            r1_val = self._get_supp(symbol, 'pivot_r1', bar)
            if r1_val is not None and r1_val > 0:
                if close_val > r1_val * (1.0 + self._p('pivot_proximity_pct', 2.0) / 100.0):
                    block = True
        if self._p('fib_filter_enabled', 0):
            fib38 = self._get_supp(symbol, 'fib_38', bar)
            fib62 = self._get_supp(symbol, 'fib_62', bar)
            pct = self._p('fib_level_pct', 3.0) / 100.0
            near38 = fib38 is not None and abs(close_val - fib38) / fib38 < pct if fib38 else False
            near62 = fib62 is not None and abs(close_val - fib62) / fib62 < pct if fib62 else False
            if not near38 and not near62:
                block = True
        return {'block_buys': block}

    # ------------------------------------------------------------------
    # Regime context
    # ------------------------------------------------------------------

    def _compute_regime_context(self, symbol, bar):
        """Evaluate market regime conditions."""
        if not self._p('regime_enabled', 0):
            return {'block_buys': False}
        block = False
        close_val = bar.close
        sma_20_val = self._get_supp(symbol, 'sma_20', bar)
        sma_50_val = self._get_supp(symbol, 'sma_50', bar)
        if self._p('regime_sma200_filter', 0) and sma_50_val is not None:
            if close_val < sma_50_val:
                block = True
        if not block:
            count = 0
            if sma_20_val is not None and close_val > sma_20_val:
                count += 1
            if sma_50_val is not None and close_val > sma_50_val:
                count += 1
            if count < self._p('regime_trend_req_count', 1):
                block = True
        return {'block_buys': block}

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------

    def _compute_position_size_direct(self, symbol, bar, scale):
        """Compute position size using advanced sizing models."""
        cash = self.cash
        close_val = bar.close
        if close_val <= 0:
            return 0
        sizing = self._p('sizing_model', 0)
        if sizing == 1:
            risk_amount = cash * self._p('fixed_risk_pct', 2.0) / 100.0 * scale
            stop_dist = close_val * self._p('stop_loss_pct', 2.5) / 100.0
            if stop_dist <= 0:
                return 0
            return max(1, int(risk_amount / stop_dist))
        elif sizing == 3:
            atr_val = self._get_supp(symbol, 'atr_14', bar)
            if atr_val is None or atr_val <= 0:
                return int(cash * self._p('position_size_pct', 10.0) / 100.0 / close_val)
            risk_amount = cash * self._p('fixed_risk_pct', 2.0) / 100.0 * scale
            stop_dist = atr_val * self._p('atr_stop_multiple', 2.0)
            if stop_dist <= 0:
                return 0
            return max(1, int(risk_amount / stop_dist))
        return int(cash * self._p('position_size_pct', 10.0) * scale / 100.0 / close_val)

    # ------------------------------------------------------------------
    # Ensemble signals (identical logic to bt_strategy.py L660-818)
    # ------------------------------------------------------------------

    def _signal_ma_crossover(self, symbol, bar):
        """MA crossover as a continuous signal in [-1.0, +1.0]."""
        ma_short_val = self._get_ma(symbol, 'short')
        ma_long_val = self._get_ma(symbol, 'long')

        if ma_long_val is None or ma_long_val == 0 or ma_short_val is None:
            return 0.0

        spread = (ma_short_val - ma_long_val) / ma_long_val
        return max(-1.0, min(1.0, spread * 10.0))

    def _signal_bollinger(self, symbol, bar):
        """Mean-reversion signal from Bollinger Bands in [-1.0, +1.0]."""
        bb_top = self._get_supp(symbol, 'bb_top', bar)
        bb_bot = self._get_supp(symbol, 'bb_bot', bar)
        bb_mid = self._get_supp(symbol, 'bb_mid', bar)
        close = bar.close

        if bb_top is None or bb_bot is None or bb_mid is None:
            return 0.0

        band_width = bb_top - bb_bot
        if band_width <= 0:
            return 0.0

        position = (bb_mid - close) / (band_width / 2.0)
        return max(-1.0, min(1.0, position))

    def _signal_stochastic(self, symbol, bar):
        """Stochastic momentum signal in [-1.0, +1.0]."""
        slowk = self._get_supp(symbol, 'slowk', bar)
        slowd = self._get_supp(symbol, 'slowd', bar)

        if slowk is None or slowd is None:
            return 0.0

        ob = self._p('sig_stoch_ob', 80)
        os_ = self._p('sig_stoch_os', 20)
        mid = (ob + os_) / 2.0
        half_range = (ob - os_) / 2.0

        if half_range <= 0:
            return 0.0

        base_signal = -(slowk - mid) / half_range

        crossover_boost = 0.0
        if slowk > slowd and slowk < os_ + 10:
            crossover_boost = 0.3
        elif slowk < slowd and slowk > ob - 10:
            crossover_boost = -0.3

        return max(-1.0, min(1.0, base_signal + crossover_boost))

    def _signal_macd(self, symbol, bar):
        """MACD momentum signal in [-1.0, +1.0]."""
        macd_val = self._get_supp(symbol, 'macd', bar)
        signal_val = self._get_supp(symbol, 'signal', bar)

        if macd_val is None or signal_val is None:
            return 0.0

        close = bar.close
        if close <= 0:
            return 0.0

        histogram = macd_val - signal_val
        normalized = histogram / close * 100.0
        return max(-1.0, min(1.0, normalized * 2.0))

    def _signal_rsi(self, symbol, bar):
        """RSI overbought/oversold signal in [-1.0, +1.0]."""
        rsi = self._get_supp(symbol, 'rsi', bar)

        if rsi is None:
            return 0.0

        ob = self._p('sig_rsi_ob', 70)
        os_ = self._p('sig_rsi_os', 30)
        mid = (ob + os_) / 2.0
        half_range = (ob - os_) / 2.0

        if half_range <= 0:
            return 0.0

        return max(-1.0, min(1.0, -(rsi - mid) / half_range))

    def _compute_ensemble_signal(self, symbol, bar):
        """
        Compute weighted ensemble signal for a stock.

        Returns (combined_score, buy_signal, sell_signal).
        """
        weights = {
            'ma': self._p('sig_ma_weight', 0.5),
            'bb': self._p('sig_bb_weight', 0.3),
            'stoch': self._p('sig_stoch_weight', 0.3),
            'macd': self._p('sig_macd_weight', 0.3),
            'rsi': self._p('sig_rsi_weight', 0.3),
        }

        signals = {
            'ma': self._signal_ma_crossover(symbol, bar),
            'bb': self._signal_bollinger(symbol, bar),
            'stoch': self._signal_stochastic(symbol, bar),
            'macd': self._signal_macd(symbol, bar),
            'rsi': self._signal_rsi(symbol, bar),
        }

        total_weight = sum(weights.values())
        if total_weight < 0.01:
            return 0.0, False, False

        combined = sum(
            weights[k] * signals[k] for k in weights
        ) / total_weight

        buy_signal = combined > self._p('sig_buy_threshold', 0.3)
        sell_signal = combined < self._p('sig_sell_threshold', -0.3)

        return combined, buy_signal, sell_signal
