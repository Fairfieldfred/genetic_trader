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

            # Combine macro + TI contexts
            block_buys = macro['block_buys'] or ti['block_buys']
            position_scale = macro['position_scale'] * ti['position_scale']
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
