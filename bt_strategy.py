"""
Backtrader strategy adapter for genetic traders.
Converts GeneticTrader genes into a Backtrader trading strategy.
"""

import math

import backtrader as bt
from genetic_trader import GeneticTrader
from typing import Dict


class MacroAwarePandasData(bt.feeds.PandasData):
    """
    Extended PandasData that includes macroeconomic indicator columns
    and per-stock technical indicator columns.

    When the DataFrame contains these columns, backtrader populates
    the corresponding lines. When they are absent, lines contain NaN
    and are safely ignored by the strategy.
    """

    lines = (
        # Macro lines (global, merged from macro_indicators table)
        'vix_close',
        'yield_curve_slope',
        'fed_funds_rate',
        'cpi_yoy',
        'unemployment_rate',
        # Technical indicator lines (per-stock, from daily_indicators)
        'rsi',
        'adx',
        'natr',
        'mfi',
        'macdhist',
        # Ensemble signal lines (per-stock, from daily_indicators)
        'bb_top',
        'bb_mid',
        'bb_bot',
        'slowk',
        'slowd',
        'macd',
        'signal',
        # Advanced indicator lines
        'wr',
        'cci',
        'cmo',
        'ao',
        'stochrsi_k',
        'stochrsi_d',
        'uo',
        'roc',
        'psar',
        'supertrend_dir',
        'ichimoku_above_cloud',
        'linreg_slope',
        'linreg_r2',
        'trix',
        'trix_signal',
        'chaikin',
        'force_index',
        'vwap',
        'vwma_20',
        'klinger',
        'klinger_signal',
        'nvi',
        'nvi_sma',
        'donchian_upper',
        'donchian_lower',
        'keltner_upper',
        'bb_pct_b',
        'bb_width',
        'ulcer',
        'pivot_r1',
        'pivot_s1',
        'fib_38',
        'fib_62',
        'sma_20',
        'atr_14',
    )

    params = (
        ('vix_close', -1),
        ('yield_curve_slope', -1),
        ('fed_funds_rate', -1),
        ('cpi_yoy', -1),
        ('unemployment_rate', -1),
        ('rsi', -1),
        ('adx', -1),
        ('natr', -1),
        ('mfi', -1),
        ('macdhist', -1),
        ('bb_top', -1),
        ('bb_mid', -1),
        ('bb_bot', -1),
        ('slowk', -1),
        ('slowd', -1),
        ('macd', -1),
        ('signal', -1),
        ('wr', -1),
        ('cci', -1),
        ('cmo', -1),
        ('ao', -1),
        ('stochrsi_k', -1),
        ('stochrsi_d', -1),
        ('uo', -1),
        ('roc', -1),
        ('psar', -1),
        ('supertrend_dir', -1),
        ('ichimoku_above_cloud', -1),
        ('linreg_slope', -1),
        ('linreg_r2', -1),
        ('trix', -1),
        ('trix_signal', -1),
        ('chaikin', -1),
        ('force_index', -1),
        ('vwap', -1),
        ('vwma_20', -1),
        ('klinger', -1),
        ('klinger_signal', -1),
        ('nvi', -1),
        ('nvi_sma', -1),
        ('donchian_upper', -1),
        ('donchian_lower', -1),
        ('keltner_upper', -1),
        ('bb_pct_b', -1),
        ('bb_width', -1),
        ('ulcer', -1),
        ('pivot_r1', -1),
        ('pivot_s1', -1),
        ('fib_38', -1),
        ('fib_62', -1),
        ('sma_20', -1),
        ('atr_14', -1),
    )


class GeneticStrategy(bt.Strategy):
    """
    Backtrader strategy that uses genes from a GeneticTrader.
    Implements a Moving Average crossover strategy with configurable parameters.
    """

    params = (
        ('ma_short_period', 10),
        ('ma_long_period', 50),
        ('ma_type', 0),  # 0 = SMA, 1 = EMA
        ('stop_loss_pct', 2.5),
        ('take_profit_pct', 5.0),
        ('position_size_pct', 10.0),
        ('printlog', False),
    )

    def __init__(self):
        """Initialize strategy with indicators."""
        # Moving Average indicators based on ma_type
        if self.params.ma_type == 0:
            # Simple Moving Average
            self.ma_short = bt.indicators.SMA(
                self.data.close,
                period=self.params.ma_short_period
            )
            self.ma_long = bt.indicators.SMA(
                self.data.close,
                period=self.params.ma_long_period
            )
        else:
            # Exponential Moving Average
            self.ma_short = bt.indicators.EMA(
                self.data.close,
                period=self.params.ma_short_period
            )
            self.ma_long = bt.indicators.EMA(
                self.data.close,
                period=self.params.ma_long_period
            )

        # Crossover signal
        self.crossover = bt.indicators.CrossOver(self.ma_short, self.ma_long)

        # Track orders and positions
        self.order = None
        self.buy_price = None
        self.buy_comm = None

        # Track trade statistics
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0

    def log(self, txt, dt=None):
        """Logging function for strategy."""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        """Notification of order status."""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
                self.log(
                    f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )
            else:  # Sell
                self.log(
                    f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        """Notification of closed trades."""
        if not trade.isclosed:
            return

        self.trade_count += 1
        if trade.pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        self.log(
            f'TRADE PROFIT, Gross: {trade.pnl:.2f}, Net: {trade.pnlcomm:.2f}'
        )

    def next(self):
        """Execute strategy logic on each bar."""
        # Check if we have an order pending
        if self.order:
            return

        # Get current position size
        position_size = self.position.size

        # Trading logic
        if not position_size:
            # Not in market - check for buy signal (bullish crossover)
            if self.crossover > 0:
                # Short MA crossed above Long MA - buy signal
                cash = self.broker.getcash()
                size = int((cash * self.params.position_size_pct / 100) / self.data.close[0])

                if size > 0:
                    self.log(
                        f'BUY CREATE, Price: {self.data.close[0]:.2f}, '
                        f'MA Short: {self.ma_short[0]:.2f}, MA Long: {self.ma_long[0]:.2f}'
                    )
                    self.order = self.buy(size=size)

        else:
            # In market - check for sell signal
            current_price = self.data.close[0]

            # Calculate returns
            if self.buy_price:
                pct_change = ((current_price - self.buy_price) / self.buy_price) * 100

                # Check stop loss
                if pct_change <= -self.params.stop_loss_pct:
                    self.log(
                        f'STOP LOSS TRIGGERED, Price: {current_price:.2f}, '
                        f'Loss: {pct_change:.2f}%'
                    )
                    self.order = self.sell(size=position_size)

                # Check take profit
                elif pct_change >= self.params.take_profit_pct:
                    self.log(
                        f'TAKE PROFIT TRIGGERED, Price: {current_price:.2f}, '
                        f'Profit: {pct_change:.2f}%'
                    )
                    self.order = self.sell(size=position_size)

                # Check MA bearish crossover
                elif self.crossover < 0:
                    self.log(
                        f'SELL CREATE (Bearish Crossover), Price: {current_price:.2f}, '
                        f'MA Short: {self.ma_short[0]:.2f}, MA Long: {self.ma_long[0]:.2f}'
                    )
                    self.order = self.sell(size=position_size)

    def stop(self):
        """Called when strategy finishes."""
        final_value = self.broker.getvalue()
        self.log(
            f'Final Portfolio Value: {final_value:.2f}, '
            f'Trades: {self.trade_count}, '
            f'Win Rate: {self.get_win_rate():.2f}%',
            dt=self.datas[0].datetime.date(0)
        )

    def get_win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.trade_count == 0:
            return 0.0
        return (self.winning_trades / self.trade_count) * 100


class PortfolioGeneticStrategy(GeneticStrategy):
    """
    Extended strategy for portfolio mode with initial allocation.
    Makes equal-dollar initial purchases across all stocks at the start.
    Supports macro-economic regime awareness when macro genes are enabled.
    """

    params = (
        ('ma_short_period', 10),
        ('ma_long_period', 50),
        ('ma_type', 0),  # 0 = SMA, 1 = EMA
        ('stop_loss_pct', 2.5),
        ('take_profit_pct', 5.0),
        ('position_size_pct', 10.0),
        ('printlog', False),
        ('initial_allocation_pct', 0.0),
        # Macro context params (disabled by default)
        ('macro_enabled', 0),
        ('macro_weight', 0.5),
        ('macro_vix_threshold', 30.0),
        ('macro_vix_position_scale', 0.5),
        ('macro_yc_threshold', 0.0),
        ('macro_yc_action', 0),
        ('macro_rate_threshold', 5.0),
        ('macro_rate_position_scale', 0.7),
        ('macro_cpi_threshold', 5.0),
        ('macro_cpi_position_scale', 0.7),
        ('macro_unemp_threshold', 6.0),
        ('macro_unemp_action', 0),
        ('macro_risk_stop_adj', 1.0),
        ('macro_risk_tp_adj', 1.0),
        ('macro_regime_count_req', 2),
        # Technical indicator filter params (disabled by default)
        ('ti_enabled', 0),
        ('ti_weight', 0.5),
        ('ti_rsi_overbought', 70),
        ('ti_rsi_oversold', 30),
        ('ti_adx_threshold', 25),
        ('ti_adx_position_scale', 0.5),
        ('ti_natr_threshold', 5.0),
        ('ti_natr_risk_action', 0),
        ('ti_mfi_overbought', 80),
        ('ti_mfi_oversold', 20),
        ('ti_macdhist_confirm', 0),
        ('ti_macdhist_exit_confirm', 0),
        # Ensemble signal params (disabled by default)
        ('ensemble_enabled', 0),
        ('sig_ma_weight', 0.5),
        ('sig_bb_weight', 0.3),
        ('sig_stoch_weight', 0.3),
        ('sig_macd_weight', 0.3),
        ('sig_rsi_weight', 0.3),
        ('sig_buy_threshold', 0.3),
        ('sig_sell_threshold', -0.3),
        ('sig_bb_period_idx', 0),
        ('sig_stoch_ob', 80),
        ('sig_stoch_os', 20),
        ('sig_rsi_ob', 70),
        ('sig_rsi_os', 30),
        # Advanced Oscillator params (disabled by default)
        ('adv_osc_enabled', 0),
        ('wr_oversold', -80),
        ('wr_overbought', -20),
        ('cci_oversold', -100),
        ('cci_overbought', 100),
        ('cmo_threshold', 25.0),
        ('ao_zero_cross_confirm', 0),
        ('stochrsi_ob', 80.0),
        ('stochrsi_os', 20.0),
        ('uo_overbought', 70.0),
        ('uo_oversold', 30.0),
        ('roc_period', 12),
        ('roc_threshold', 0.0),
        # Trend Signal params (disabled by default)
        ('trend_sig_enabled', 0),
        ('psar_filter_enabled', 0),
        ('supertrend_filter_enabled', 0),
        ('ichimoku_cloud_filter', 0),
        ('linreg_slope_min', -999.0),
        ('linreg_r2_min', 0.0),
        ('trix_zero_confirm', 0),
        # Volume Signal params (disabled by default)
        ('vol_sig_enabled', 0),
        ('obv_trend_confirm', 0),
        ('chaikin_threshold', 0.0),
        ('force_index_confirm', 0),
        ('vwap_filter_mode', 0),
        ('vwma_vs_sma_confirm', 0),
        ('klinger_confirm', 0),
        ('nvi_trend_confirm', 0),
        # Volatility & Breakout params (disabled by default)
        ('vb_enabled', 0),
        ('donchian_breakout_confirm', 0),
        ('keltner_filter_enabled', 0),
        ('bb_pct_b_threshold', 1.0),
        ('bb_squeeze_threshold', 2.0),
        ('ulcer_max', 999.0),
        # Support & Resistance params (disabled by default)
        ('sr_enabled', 0),
        ('pivot_filter_enabled', 0),
        ('pivot_proximity_pct', 2.0),
        ('fib_filter_enabled', 0),
        ('fib_level_pct', 3.0),
        # Regime Detection params (disabled by default)
        ('regime_enabled', 0),
        ('regime_window', 20),
        ('regime_sma200_filter', 0),
        ('regime_trend_req_count', 1),
        # Advanced Sizing params (disabled by default)
        ('sizing_model', 0),
        ('kelly_fraction', 0.5),
        ('atr_stop_multiple', 2.0),
        ('fixed_risk_pct', 2.0),
    )

    def __init__(self):
        """Initialize portfolio strategy with multiple data feeds."""
        # Don't call super().__init__() since we're handling multiple data feeds differently

        # Track orders and positions
        self.order = None
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0

        # Track MA indicators and crossovers per data feed
        self.ma_short_indicators = {}
        self.ma_long_indicators = {}
        self.crossover_indicators = {}

        # Create MA indicators for each data feed
        for i, data in enumerate(self.datas):
            if self.params.ma_type == 0:
                # Simple Moving Average
                self.ma_short_indicators[data._name] = bt.indicators.SMA(
                    data.close,
                    period=self.params.ma_short_period
                )
                self.ma_long_indicators[data._name] = bt.indicators.SMA(
                    data.close,
                    period=self.params.ma_long_period
                )
            else:
                # Exponential Moving Average
                self.ma_short_indicators[data._name] = bt.indicators.EMA(
                    data.close,
                    period=self.params.ma_short_period
                )
                self.ma_long_indicators[data._name] = bt.indicators.EMA(
                    data.close,
                    period=self.params.ma_long_period
                )

            # Crossover signal for each data feed
            self.crossover_indicators[data._name] = bt.indicators.CrossOver(
                self.ma_short_indicators[data._name],
                self.ma_long_indicators[data._name]
            )

        # Flag to track if initial allocation is done
        self.initial_allocation_done = False
        self.initial_orders = []

        # Track pending orders per stock to prevent duplicates
        self.pending_orders = {}  # symbol -> order

        # Per-stock trade tracking
        self.trades_by_symbol = {}  # symbol -> {trades, won, lost, pnl}

    def prenext(self):
        """Called before minimum period is met for all indicators."""
        # Make initial allocation on first bar, even before indicators are ready
        if not self.initial_allocation_done and len(self) == 1:
            self._make_initial_allocation()

        # Clean up stale initial orders (e.g. for data feeds
        # whose data hasn't started yet)
        if self.initial_orders:
            self._cleanup_stale_initial_orders()

    def _cleanup_stale_initial_orders(self):
        """Remove initial orders that are stuck in Accepted state."""
        stale = []
        for order in self.initial_orders:
            if order.status == order.Accepted and len(self) > 5:
                stale.append(order)
        for order in stale:
            self.cancel(order)
            self.initial_orders.remove(order)

    def next(self):
        """Execute strategy logic on each bar."""
        # Make initial allocation on first bar if not done in prenext
        if not self.initial_allocation_done:
            self._make_initial_allocation()
            return

        # Clean up any stale initial orders
        if self.initial_orders:
            self._cleanup_stale_initial_orders()
            if self.initial_orders:
                return

        # Compute macro regime modifiers (once per bar, shared across stocks)
        macro = self._compute_macro_context()

        # Process each data feed
        for data in self.datas:
            symbol = data._name
            ma_short = self.ma_short_indicators[symbol]
            ma_long = self.ma_long_indicators[symbol]
            crossover = self.crossover_indicators[symbol]

            # Skip stocks with a pending order
            if symbol in self.pending_orders:
                continue

            # Compute per-stock technical indicator modifiers
            ti = self._compute_technical_context(data)

            # Compute new context modifiers
            adv_osc = self._compute_advanced_oscillator_context(data)
            trend_sig = self._compute_trend_signal_context(data)
            vol_sig = self._compute_volume_signal_context(data)
            vb = self._compute_volatility_breakout_context(data)
            sr = self._compute_support_resistance_context(data)
            regime_ctx = self._compute_regime_context(data)

            # Combine all contexts
            block_buys = (macro['block_buys'] or ti['block_buys'] or
                          adv_osc.get('block_buys', False) or trend_sig.get('block_buys', False) or
                          vol_sig.get('block_buys', False) or vb.get('block_buys', False) or
                          sr.get('block_buys', False) or regime_ctx.get('block_buys', False))
            position_scale = (macro['position_scale'] * ti['position_scale'] *
                              adv_osc.get('position_scale', 1.0) * vol_sig.get('position_scale', 1.0))
            stop_loss_adj = macro['stop_loss_adj'] * ti['stop_loss_adj']
            take_profit_adj = macro['take_profit_adj'] * ti['take_profit_adj']

            # Get current position for this data feed
            position = self.getposition(data)
            position_size = position.size

            # Compute ensemble signal if enabled
            use_ensemble = self.params.ensemble_enabled
            if use_ensemble:
                _, ens_buy, ens_sell = self._compute_ensemble_signal(data)

            # Trading logic
            if not position_size:
                # Not in market - check for buy signal
                buy_triggered = (
                    ens_buy if use_ensemble else crossover[0] > 0
                )
                if buy_triggered:
                    # Check combined gate
                    if block_buys:
                        continue

                    # Apply combined position scale with advanced sizing
                    if self.params.sizing_model in (1, 3):
                        size = self._compute_position_size_direct(data, position_scale)
                    elif self.params.sizing_model == 2:
                        adjusted_pct = self.params.position_size_pct * position_scale * self.params.kelly_fraction
                        cash = self.broker.getcash()
                        size = int((cash * adjusted_pct / 100) / data.close[0])
                    else:
                        adjusted_pct = (
                            self.params.position_size_pct * position_scale
                        )
                        cash = self.broker.getcash()
                        size = int((cash * adjusted_pct / 100) / data.close[0])

                    if size > 0:
                        self.log(
                            f'BUY CREATE {symbol}, Price: {data.close[0]:.2f}, '
                            f'MA Short: {ma_short[0]:.2f}, MA Long: {ma_long[0]:.2f}'
                        )
                        order = self.buy(data=data, size=size)
                        self.pending_orders[symbol] = order

            else:
                # In market - check for sell signal
                current_price = data.close[0]

                # Check TI-driven early exit (MACD histogram confirmation)
                if ti['force_exit']:
                    self.log(
                        f'TI EXIT {symbol}, Price: {current_price:.2f} '
                        f'(MACD histogram negative)'
                    )
                    order = self.sell(data=data, size=position_size)
                    self.pending_orders[symbol] = order
                    continue

                # Get the average buy price for this position
                buy_price = position.price

                if buy_price:
                    pct_change = ((current_price - buy_price) / buy_price) * 100

                    # Apply combined adjusted thresholds
                    adj_stop = self.params.stop_loss_pct * stop_loss_adj
                    adj_tp = self.params.take_profit_pct * take_profit_adj

                    # Check stop loss
                    if pct_change <= -adj_stop:
                        self.log(
                            f'STOP LOSS {symbol}, Price: {current_price:.2f}, '
                            f'Loss: {pct_change:.2f}%'
                        )
                        order = self.sell(data=data, size=position_size)
                        self.pending_orders[symbol] = order

                    # Check take profit
                    elif pct_change >= adj_tp:
                        self.log(
                            f'TAKE PROFIT {symbol}, Price: {current_price:.2f}, '
                            f'Profit: {pct_change:.2f}%'
                        )
                        order = self.sell(data=data, size=position_size)
                        self.pending_orders[symbol] = order

                    # Check signal-based sell
                    elif use_ensemble and ens_sell:
                        self.log(
                            f'ENSEMBLE SELL {symbol}, '
                            f'Price: {current_price:.2f}'
                        )
                        order = self.sell(data=data, size=position_size)
                        self.pending_orders[symbol] = order

                    # Check MA bearish crossover (fallback when
                    # ensemble disabled)
                    elif not use_ensemble and crossover[0] < 0:
                        self.log(
                            f'SELL {symbol} (Bearish Crossover), Price: {current_price:.2f}, '
                            f'MA Short: {ma_short[0]:.2f}, MA Long: {ma_long[0]:.2f}'
                        )
                        order = self.sell(data=data, size=position_size)
                        self.pending_orders[symbol] = order

    def _compute_macro_context(self):
        """
        Evaluate current macroeconomic conditions and return modifiers.

        Reads macro data from the first data feed's extra lines.
        Returns a dict of modifiers that adjust the base MA strategy.
        """
        context = {
            'position_scale': 1.0,
            'block_buys': False,
            'stop_loss_adj': 1.0,
            'take_profit_adj': 1.0,
        }

        if not self.params.macro_enabled:
            return context

        weight = self.params.macro_weight
        data = self.datas[0]
        adverse_count = 0

        # VIX regime
        vix = self._get_macro_line(data, 'vix_close')
        if vix is not None:
            if vix > self.params.macro_vix_threshold:
                adverse_count += 1
                scale = self.params.macro_vix_position_scale
                context['position_scale'] *= 1.0 - weight * (1.0 - scale)

        # Yield curve regime
        yc = self._get_macro_line(data, 'yield_curve_slope')
        if yc is not None:
            if yc < self.params.macro_yc_threshold:
                adverse_count += 1
                action = self.params.macro_yc_action
                if action == 1:
                    context['position_scale'] *= 1.0 - weight * 0.5
                elif action == 2:
                    context['block_buys'] = True

        # Interest rate regime
        rate = self._get_macro_line(data, 'fed_funds_rate')
        if rate is not None:
            if rate > self.params.macro_rate_threshold:
                adverse_count += 1
                scale = self.params.macro_rate_position_scale
                context['position_scale'] *= 1.0 - weight * (1.0 - scale)

        # CPI/inflation regime
        cpi = self._get_macro_line(data, 'cpi_yoy')
        if cpi is not None:
            if cpi > self.params.macro_cpi_threshold:
                adverse_count += 1
                scale = self.params.macro_cpi_position_scale
                context['position_scale'] *= 1.0 - weight * (1.0 - scale)

        # Unemployment regime
        unemp = self._get_macro_line(data, 'unemployment_rate')
        if unemp is not None:
            if unemp > self.params.macro_unemp_threshold:
                adverse_count += 1
                action = self.params.macro_unemp_action
                if action == 1:
                    context['position_scale'] *= 1.0 - weight * 0.5
                elif action == 2:
                    context['block_buys'] = True

        # Apply risk adjustments when enough regimes are adverse
        if adverse_count >= self.params.macro_regime_count_req:
            context['stop_loss_adj'] = self.params.macro_risk_stop_adj
            context['take_profit_adj'] = self.params.macro_risk_tp_adj

        # Floor position scale at 0.1 to avoid zero-size orders
        context['position_scale'] = max(0.1, context['position_scale'])

        return context

    def _compute_technical_context(self, data):
        """
        Evaluate per-stock technical indicator conditions and return modifiers.

        Unlike macro context (global, computed once per bar), this is
        computed per data feed since each stock has its own RSI, ADX, etc.

        Args:
            data: Backtrader data feed for a specific stock

        Returns:
            Dict with position_scale, block_buys, stop_loss_adj,
            take_profit_adj, and force_exit modifiers.
        """
        context = {
            'position_scale': 1.0,
            'block_buys': False,
            'stop_loss_adj': 1.0,
            'take_profit_adj': 1.0,
            'force_exit': False,
        }

        if not self.params.ti_enabled:
            return context

        weight = self.params.ti_weight

        # RSI filter — overbought blocks buys, oversold scales up
        rsi = self._get_line(data, 'rsi')
        if rsi is not None:
            if rsi > self.params.ti_rsi_overbought:
                context['block_buys'] = True
            elif rsi < self.params.ti_rsi_oversold:
                context['position_scale'] *= 1.0 + weight * 0.5

        # ADX filter — weak trend reduces position size
        adx = self._get_line(data, 'adx')
        if adx is not None:
            if adx < self.params.ti_adx_threshold:
                scale = self.params.ti_adx_position_scale
                context['position_scale'] *= 1.0 - weight * (1.0 - scale)

        # NATR filter — high volatility adjusts risk
        natr = self._get_line(data, 'natr')
        if natr is not None:
            if natr > self.params.ti_natr_threshold:
                action = self.params.ti_natr_risk_action
                if action == 0:
                    context['stop_loss_adj'] *= 0.7
                elif action == 1:
                    context['stop_loss_adj'] *= 1.5
                elif action == 2:
                    context['block_buys'] = True

        # MFI filter — volume-weighted overbought/oversold
        mfi = self._get_line(data, 'mfi')
        if mfi is not None:
            if mfi > self.params.ti_mfi_overbought:
                context['position_scale'] *= 1.0 - weight * 0.4
            elif mfi < self.params.ti_mfi_oversold:
                context['position_scale'] *= 1.0 + weight * 0.3

        # MACD histogram confirmation
        macdhist = self._get_line(data, 'macdhist')
        if macdhist is not None:
            if self.params.ti_macdhist_confirm and macdhist <= 0:
                context['block_buys'] = True
            if self.params.ti_macdhist_exit_confirm and macdhist < 0:
                context['force_exit'] = True

        # Floor position scale at 0.1 to avoid zero-size orders
        context['position_scale'] = max(0.1, context['position_scale'])

        return context

    def _compute_advanced_oscillator_context(self, data):
        """Evaluate advanced oscillator conditions."""
        if not self.params.adv_osc_enabled:
            return {'block_buys': False, 'position_scale': 1.0}
        block = False
        scale = 1.0
        wr_val = self._get_line(data, 'wr')
        if wr_val is not None:
            if wr_val > self.params.wr_overbought:
                block = True
            elif wr_val < self.params.wr_oversold:
                scale *= 1.1
        cci_val = self._get_line(data, 'cci')
        if cci_val is not None:
            if cci_val > self.params.cci_overbought:
                block = True
            elif cci_val < self.params.cci_oversold:
                scale *= 1.1
        cmo_val = self._get_line(data, 'cmo')
        if cmo_val is not None:
            if abs(cmo_val) < self.params.cmo_threshold:
                scale *= 0.7
        ao_val = self._get_line(data, 'ao')
        if ao_val is not None and self.params.ao_zero_cross_confirm:
            if ao_val < 0:
                block = True
        stochrsi_k_val = self._get_line(data, 'stochrsi_k')
        if stochrsi_k_val is not None and stochrsi_k_val > self.params.stochrsi_ob:
            block = True
        uo_val = self._get_line(data, 'uo')
        if uo_val is not None:
            if uo_val > self.params.uo_overbought:
                block = True
            elif uo_val < self.params.uo_oversold:
                scale *= 1.1
        roc_val = self._get_line(data, 'roc')
        if roc_val is not None and self.params.roc_threshold != 0:
            if self.params.roc_threshold > 0 and roc_val < self.params.roc_threshold:
                block = True
            elif self.params.roc_threshold < 0 and roc_val > self.params.roc_threshold:
                block = True
        scale = max(0.1, scale)
        return {'block_buys': block, 'position_scale': scale}

    def _compute_trend_signal_context(self, data):
        """Evaluate trend signal conditions."""
        if not self.params.trend_sig_enabled:
            return {'block_buys': False}
        block = False
        close_val = data.close[0]
        if self.params.psar_filter_enabled:
            psar_val = self._get_line(data, 'psar')
            if psar_val is not None and close_val < psar_val:
                block = True
        if self.params.supertrend_filter_enabled:
            st_dir = self._get_line(data, 'supertrend_dir')
            if st_dir is not None and st_dir < 0:
                block = True
        if self.params.ichimoku_cloud_filter:
            ichi_val = self._get_line(data, 'ichimoku_above_cloud')
            if ichi_val is not None and ichi_val < 0:
                block = True
        lr_slope_val = self._get_line(data, 'linreg_slope')
        if lr_slope_val is not None and lr_slope_val < self.params.linreg_slope_min:
            block = True
        lr_r2_val = self._get_line(data, 'linreg_r2')
        if lr_r2_val is not None and lr_r2_val < self.params.linreg_r2_min:
            block = True
        if self.params.trix_zero_confirm:
            trix_val = self._get_line(data, 'trix')
            if trix_val is not None and trix_val < 0:
                block = True
        return {'block_buys': block}

    def _compute_volume_signal_context(self, data):
        """Evaluate volume signal conditions."""
        if not self.params.vol_sig_enabled:
            return {'block_buys': False, 'position_scale': 1.0}
        block = False
        scale = 1.0
        close_val = data.close[0]
        if self.params.chaikin_threshold > 0:
            ch_val = self._get_line(data, 'chaikin')
            if ch_val is not None and ch_val < self.params.chaikin_threshold:
                block = True
        if self.params.force_index_confirm:
            fi_val = self._get_line(data, 'force_index')
            if fi_val is not None and fi_val < 0:
                block = True
        if self.params.vwap_filter_mode == 1:
            vwap_val = self._get_line(data, 'vwap')
            if vwap_val is not None and close_val > vwap_val:
                block = True
        elif self.params.vwap_filter_mode == 2:
            vwap_val = self._get_line(data, 'vwap')
            if vwap_val is not None and close_val < vwap_val:
                block = True
        if self.params.vwma_vs_sma_confirm:
            vwma_val = self._get_line(data, 'vwma_20')
            sma_val = self._get_line(data, 'sma_20')
            if vwma_val is not None and sma_val is not None and vwma_val < sma_val:
                block = True
        if self.params.klinger_confirm:
            kl_val = self._get_line(data, 'klinger')
            kl_sig = self._get_line(data, 'klinger_signal')
            if kl_val is not None and kl_sig is not None and kl_val < kl_sig:
                block = True
        if self.params.nvi_trend_confirm:
            nvi_val = self._get_line(data, 'nvi')
            nvi_sma_val = self._get_line(data, 'nvi_sma')
            if nvi_val is not None and nvi_sma_val is not None and nvi_val < nvi_sma_val:
                block = True
        return {'block_buys': block, 'position_scale': scale}

    def _compute_volatility_breakout_context(self, data):
        """Evaluate volatility and breakout conditions."""
        if not self.params.vb_enabled:
            return {'block_buys': False}
        block = False
        close_val = data.close[0]
        if self.params.donchian_breakout_confirm:
            dc_upper = self._get_line(data, 'donchian_upper')
            if dc_upper is not None and close_val < dc_upper:
                block = True
        if self.params.keltner_filter_enabled:
            kelt_upper = self._get_line(data, 'keltner_upper')
            if kelt_upper is not None and close_val > kelt_upper:
                block = True
        bb_pct_b_val = self._get_line(data, 'bb_pct_b')
        if bb_pct_b_val is not None:
            if bb_pct_b_val > (1.0 - self.params.bb_pct_b_threshold):
                block = True
        bb_w_val = self._get_line(data, 'bb_width')
        if bb_w_val is not None and bb_w_val < self.params.bb_squeeze_threshold:
            block = True
        ulcer_val = self._get_line(data, 'ulcer')
        if ulcer_val is not None and ulcer_val > self.params.ulcer_max:
            block = True
        return {'block_buys': block}

    def _compute_support_resistance_context(self, data):
        """Evaluate support and resistance conditions."""
        if not self.params.sr_enabled:
            return {'block_buys': False}
        block = False
        close_val = data.close[0]
        if self.params.pivot_filter_enabled:
            r1_val = self._get_line(data, 'pivot_r1')
            if r1_val is not None and r1_val > 0:
                if close_val > r1_val * (1.0 + self.params.pivot_proximity_pct / 100.0):
                    block = True
        if self.params.fib_filter_enabled:
            fib38 = self._get_line(data, 'fib_38')
            fib62 = self._get_line(data, 'fib_62')
            pct = self.params.fib_level_pct / 100.0
            near38 = fib38 is not None and abs(close_val - fib38) / fib38 < pct if fib38 else False
            near62 = fib62 is not None and abs(close_val - fib62) / fib62 < pct if fib62 else False
            if not near38 and not near62:
                block = True
        return {'block_buys': block}

    def _compute_regime_context(self, data):
        """Evaluate market regime conditions."""
        if not self.params.regime_enabled:
            return {'block_buys': False}
        block = False
        close_val = data.close[0]
        sma_20_val = self._get_line(data, 'sma_20')
        sma_50_val = self._get_line(data, 'sma_50') if hasattr(data, 'sma_50') else None
        if self.params.regime_sma200_filter and sma_50_val is not None:
            if close_val < sma_50_val:
                block = True
        if not block:
            count = 0
            if sma_20_val is not None and close_val > sma_20_val:
                count += 1
            if sma_50_val is not None and close_val > sma_50_val:
                count += 1
            if count < self.params.regime_trend_req_count:
                block = True
        return {'block_buys': block}

    def _compute_position_size_direct(self, data, scale):
        """Compute position size using advanced sizing models."""
        cash = self.broker.getcash()
        close_val = data.close[0]
        if close_val <= 0:
            return 0
        if self.params.sizing_model == 1:
            risk_amount = cash * self.params.fixed_risk_pct / 100.0 * scale
            stop_dist = close_val * self.params.stop_loss_pct / 100.0
            if stop_dist <= 0:
                return 0
            return max(1, int(risk_amount / stop_dist))
        elif self.params.sizing_model == 3:
            atr_val = self._get_line(data, 'atr_14')
            if atr_val is None or atr_val <= 0:
                return int(cash * self.params.position_size_pct / 100.0 / close_val)
            risk_amount = cash * self.params.fixed_risk_pct / 100.0 * scale
            stop_dist = atr_val * self.params.atr_stop_multiple
            if stop_dist <= 0:
                return 0
            return max(1, int(risk_amount / stop_dist))
        return int(cash * self.params.position_size_pct * scale / 100.0 / close_val)

    def _signal_ma_crossover(self, data):
        """
        MA crossover as a continuous signal.

        Returns a value in [-1.0, +1.0] based on the normalized spread
        between the short and long moving averages.
        """
        symbol = data._name
        ma_short = self.ma_short_indicators[symbol]
        ma_long = self.ma_long_indicators[symbol]

        if ma_long[0] == 0:
            return 0.0

        spread = (ma_short[0] - ma_long[0]) / ma_long[0]
        # Typical spread is -0.05 to +0.05, scale by 10
        return max(-1.0, min(1.0, spread * 10.0))

    def _signal_bollinger(self, data):
        """
        Mean-reversion signal from Bollinger Bands.

        Returns +1 when price is at the lower band (buy opportunity),
        -1 when price is at the upper band (sell opportunity).
        """
        bb_top = self._get_line(data, 'bb_top')
        bb_bot = self._get_line(data, 'bb_bot')
        bb_mid = self._get_line(data, 'bb_mid')
        close = data.close[0]

        if bb_top is None or bb_bot is None or bb_mid is None:
            return 0.0

        band_width = bb_top - bb_bot
        if band_width <= 0:
            return 0.0

        # Position within bands: +1 at lower band, -1 at upper band
        position = (bb_mid - close) / (band_width / 2.0)
        return max(-1.0, min(1.0, position))

    def _signal_stochastic(self, data):
        """
        Momentum oscillator signal from Stochastic %K/%D.

        Returns +1 in oversold zone (buy), -1 in overbought zone (sell).
        Boosted when %K crosses %D in extreme zones.
        """
        slowk = self._get_line(data, 'slowk')
        slowd = self._get_line(data, 'slowd')

        if slowk is None or slowd is None:
            return 0.0

        ob = self.params.sig_stoch_ob
        os_ = self.params.sig_stoch_os
        mid = (ob + os_) / 2.0
        half_range = (ob - os_) / 2.0

        if half_range <= 0:
            return 0.0

        # Normalize: oversold → +1 (buy), overbought → -1 (sell)
        base_signal = -(slowk - mid) / half_range

        # Boost when K crosses D in extreme zones
        crossover_boost = 0.0
        if slowk > slowd and slowk < os_ + 10:
            crossover_boost = 0.3
        elif slowk < slowd and slowk > ob - 10:
            crossover_boost = -0.3

        return max(-1.0, min(1.0, base_signal + crossover_boost))

    def _signal_macd(self, data):
        """
        Momentum trend signal from MACD line vs Signal line.

        Returns a value in [-1.0, +1.0] based on the normalized MACD
        histogram (MACD - Signal), positive = bullish momentum.
        """
        macd_val = self._get_line(data, 'macd')
        signal_val = self._get_line(data, 'signal')

        if macd_val is None or signal_val is None:
            return 0.0

        close = data.close[0]
        if close <= 0:
            return 0.0

        # Normalize histogram by price for cross-stock comparability
        histogram = macd_val - signal_val
        normalized = histogram / close * 100.0

        # Typical normalized histogram is -1 to +1
        return max(-1.0, min(1.0, normalized * 2.0))

    def _signal_rsi(self, data):
        """
        Overbought/oversold signal from RSI.

        Returns +1 when oversold (buy), -1 when overbought (sell).
        """
        rsi = self._get_line(data, 'rsi')

        if rsi is None:
            return 0.0

        ob = self.params.sig_rsi_ob
        os_ = self.params.sig_rsi_os
        mid = (ob + os_) / 2.0
        half_range = (ob - os_) / 2.0

        if half_range <= 0:
            return 0.0

        # Normalize: oversold → +1, overbought → -1
        return max(-1.0, min(1.0, -(rsi - mid) / half_range))

    def _compute_ensemble_signal(self, data):
        """
        Compute weighted ensemble signal for a stock.

        Combines all signal generators using evolved weights and compares
        against buy/sell thresholds.

        Returns:
            (combined_score, buy_signal, sell_signal) tuple.
        """
        weights = {
            'ma': self.params.sig_ma_weight,
            'bb': self.params.sig_bb_weight,
            'stoch': self.params.sig_stoch_weight,
            'macd': self.params.sig_macd_weight,
            'rsi': self.params.sig_rsi_weight,
        }

        signals = {
            'ma': self._signal_ma_crossover(data),
            'bb': self._signal_bollinger(data),
            'stoch': self._signal_stochastic(data),
            'macd': self._signal_macd(data),
            'rsi': self._signal_rsi(data),
        }

        total_weight = sum(weights.values())

        if total_weight < 0.01:
            return 0.0, False, False

        combined = sum(
            weights[k] * signals[k] for k in weights
        ) / total_weight

        buy_signal = combined > self.params.sig_buy_threshold
        sell_signal = combined < self.params.sig_sell_threshold

        return combined, buy_signal, sell_signal

    @staticmethod
    def _get_line(data, line_name):
        """
        Safely read a data line from a backtrader data feed.

        Returns the current value, or None if the line doesn't exist
        or the value is NaN.
        """
        if not hasattr(data, line_name):
            return None
        line = getattr(data, line_name)
        try:
            val = line[0]
        except (IndexError, TypeError):
            return None
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None
        return val

    @staticmethod
    def _get_macro_line(data, line_name):
        """
        Safely read a macro data line from a backtrader data feed.

        Returns the current value, or None if the line doesn't exist
        or the value is NaN.
        """
        if not hasattr(data, line_name):
            return None
        line = getattr(data, line_name)
        try:
            val = line[0]
        except (IndexError, TypeError):
            return None
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None
        return val

    def _make_initial_allocation(self):
        """Make equal-dollar initial purchases across all stocks."""
        if self.initial_allocation_done:
            return

        allocation_pct = self.params.initial_allocation_pct
        if allocation_pct <= 0:
            self.initial_allocation_done = True
            return

        # Calculate capital to allocate
        total_cash = self.broker.getcash()
        allocation_capital = total_cash * (allocation_pct / 100.0)
        per_stock_capital = allocation_capital / len(self.datas)

        self.log(f'INITIAL ALLOCATION: {allocation_pct}% = ${allocation_capital:,.2f}')
        self.log(f'Per stock: ${per_stock_capital:,.2f} across {len(self.datas)} stocks')

        # Buy equal dollar amount of each stock
        for data in self.datas:
            symbol = data._name
            current_price = data.close[0]

            # Skip stocks whose data hasn't started yet (NaN or invalid price)
            if math.isnan(current_price) or current_price <= 0:
                self.log(f'SKIP INITIAL BUY {symbol}: no valid price yet')
                continue

            shares = int(per_stock_capital / current_price)

            if shares > 0:
                self.log(f'INITIAL BUY {symbol}: {shares} shares @ ${current_price:.2f}')
                order = self.buy(data=data, size=shares)
                self.initial_orders.append(order)

        self.initial_allocation_done = True

    def notify_order(self, order):
        """Notification of order status."""
        if order.status in [order.Submitted, order.Accepted]:
            return

        # Get the data feed name for logging and tracking
        symbol = order.data._name if hasattr(order.data, '_name') else 'Unknown'

        if order.status in [order.Completed]:
            # Remove from initial orders if it was one
            if order in self.initial_orders:
                self.initial_orders.remove(order)

            if order.isbuy():
                self.log(
                    f'BUY EXECUTED {symbol}, Price: {order.executed.price:.2f}, '
                    f'Size: {order.executed.size}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )
            else:  # Sell
                self.log(
                    f'SELL EXECUTED {symbol}, Price: {order.executed.price:.2f}, '
                    f'Size: {order.executed.size}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # Remove from initial orders if it was one
            if order in self.initial_orders:
                self.initial_orders.remove(order)
            self.log(f'Order Canceled/Margin/Rejected for {symbol}')

        # Clear pending order tracking for this symbol
        self.pending_orders.pop(symbol, None)
        self.order = None

    def notify_trade(self, trade):
        """Track per-symbol trade results from closed trades."""
        if not trade.isclosed:
            return

        # Update aggregate counters
        self.trade_count += 1
        if trade.pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        # Track per-symbol data
        symbol = trade.data._name if hasattr(trade.data, '_name') else 'Unknown'
        if symbol not in self.trades_by_symbol:
            self.trades_by_symbol[symbol] = {
                'trades': 0,
                'won': 0,
                'lost': 0,
                'pnl': 0.0,
            }

        entry = self.trades_by_symbol[symbol]
        entry['trades'] += 1
        if trade.pnlcomm > 0:
            entry['won'] += 1
        else:
            entry['lost'] += 1
        entry['pnl'] += trade.pnlcomm


def create_strategy_from_trader(trader: GeneticTrader, use_portfolio: bool = False, initial_allocation_pct: float = 0.0):
    """
    Create a Backtrader strategy class from a GeneticTrader.

    Args:
        trader: GeneticTrader with gene values
        use_portfolio: Whether to use portfolio strategy (multiple data feeds)
        initial_allocation_pct: Percentage of capital to allocate initially (portfolio mode only)

    Returns:
        Strategy class configured with trader's genes
    """
    genes = trader.get_genes()

    if use_portfolio:
        # Build params list with base strategy genes
        param_list = [
            ('ma_short_period', genes['ma_short_period']),
            ('ma_long_period', genes['ma_long_period']),
            ('ma_type', genes['ma_type']),
            ('stop_loss_pct', genes['stop_loss_pct']),
            ('take_profit_pct', genes['take_profit_pct']),
            ('position_size_pct', genes['position_size_pct']),
            ('printlog', False),
            ('initial_allocation_pct', initial_allocation_pct),
        ]

        # Add macro genes if present in chromosome
        macro_gene_names = [
            'macro_enabled', 'macro_weight',
            'macro_vix_threshold', 'macro_vix_position_scale',
            'macro_yc_threshold', 'macro_yc_action',
            'macro_rate_threshold', 'macro_rate_position_scale',
            'macro_cpi_threshold', 'macro_cpi_position_scale',
            'macro_unemp_threshold', 'macro_unemp_action',
            'macro_risk_stop_adj', 'macro_risk_tp_adj',
            'macro_regime_count_req',
        ]
        for name in macro_gene_names:
            if name in genes:
                param_list.append((name, genes[name]))

        # Add technical indicator genes if present in chromosome
        ti_gene_names = [
            'ti_enabled', 'ti_weight',
            'ti_rsi_overbought', 'ti_rsi_oversold',
            'ti_adx_threshold', 'ti_adx_position_scale',
            'ti_natr_threshold', 'ti_natr_risk_action',
            'ti_mfi_overbought', 'ti_mfi_oversold',
            'ti_macdhist_confirm', 'ti_macdhist_exit_confirm',
        ]
        for name in ti_gene_names:
            if name in genes:
                param_list.append((name, genes[name]))

        # Add ensemble signal genes if present in chromosome
        ensemble_gene_names = [
            'ensemble_enabled',
            'sig_ma_weight', 'sig_bb_weight', 'sig_stoch_weight',
            'sig_macd_weight', 'sig_rsi_weight',
            'sig_buy_threshold', 'sig_sell_threshold',
            'sig_bb_period_idx',
            'sig_stoch_ob', 'sig_stoch_os',
            'sig_rsi_ob', 'sig_rsi_os',
        ]
        for name in ensemble_gene_names:
            if name in genes:
                param_list.append((name, genes[name]))

        # Add advanced oscillator genes if present
        adv_osc_gene_names = [
            'adv_osc_enabled', 'wr_oversold', 'wr_overbought',
            'cci_oversold', 'cci_overbought', 'cmo_threshold',
            'ao_zero_cross_confirm', 'stochrsi_ob', 'stochrsi_os',
            'uo_overbought', 'uo_oversold', 'roc_period', 'roc_threshold',
        ]
        for name in adv_osc_gene_names:
            if name in genes:
                param_list.append((name, genes[name]))

        # Add trend signal genes if present
        trend_sig_gene_names = [
            'trend_sig_enabled', 'psar_filter_enabled',
            'supertrend_filter_enabled', 'ichimoku_cloud_filter',
            'linreg_slope_min', 'linreg_r2_min', 'trix_zero_confirm',
        ]
        for name in trend_sig_gene_names:
            if name in genes:
                param_list.append((name, genes[name]))

        # Add volume signal genes if present
        vol_sig_gene_names = [
            'vol_sig_enabled', 'obv_trend_confirm', 'chaikin_threshold',
            'force_index_confirm', 'vwap_filter_mode',
            'vwma_vs_sma_confirm', 'klinger_confirm', 'nvi_trend_confirm',
        ]
        for name in vol_sig_gene_names:
            if name in genes:
                param_list.append((name, genes[name]))

        # Add volatility breakout genes if present
        vb_gene_names = [
            'vb_enabled', 'donchian_breakout_confirm',
            'keltner_filter_enabled', 'bb_pct_b_threshold',
            'bb_squeeze_threshold', 'ulcer_max',
        ]
        for name in vb_gene_names:
            if name in genes:
                param_list.append((name, genes[name]))

        # Add support/resistance genes if present
        sr_gene_names = [
            'sr_enabled', 'pivot_filter_enabled', 'pivot_proximity_pct',
            'fib_filter_enabled', 'fib_level_pct',
        ]
        for name in sr_gene_names:
            if name in genes:
                param_list.append((name, genes[name]))

        # Add regime detection genes if present
        regime_gene_names = [
            'regime_enabled', 'regime_window',
            'regime_sma200_filter', 'regime_trend_req_count',
        ]
        for name in regime_gene_names:
            if name in genes:
                param_list.append((name, genes[name]))

        # Add advanced sizing genes if present
        sizing_gene_names = [
            'sizing_model', 'kelly_fraction',
            'atr_stop_multiple', 'fixed_risk_pct',
        ]
        for name in sizing_gene_names:
            if name in genes:
                param_list.append((name, genes[name]))

        class ConfiguredPortfolioStrategy(PortfolioGeneticStrategy):
            params = tuple(param_list)

        return ConfiguredPortfolioStrategy
    else:
        # Create single-stock strategy (original behavior, no macro)
        class ConfiguredStrategy(GeneticStrategy):
            params = (
                ('ma_short_period', genes['ma_short_period']),
                ('ma_long_period', genes['ma_long_period']),
                ('ma_type', genes['ma_type']),
                ('stop_loss_pct', genes['stop_loss_pct']),
                ('take_profit_pct', genes['take_profit_pct']),
                ('position_size_pct', genes['position_size_pct']),
                ('printlog', False),
            )

        return ConfiguredStrategy


# Example usage
if __name__ == "__main__":
    import pandas as pd
    from data_loader import DataLoader
    import config

    print("Testing Backtrader Strategy\n")

    # Load data
    loader = DataLoader(config.DATABASE_PATH)
    df = loader.load_stock_data(
        config.TEST_SYMBOL,
        start_date=config.TRAIN_START_DATE,
        end_date='2020-12-31'
    )

    print(f"Loaded {len(df)} bars for {config.TEST_SYMBOL}")

    # Create a genetic trader with MA strategy genes
    # [ma_short_period, ma_long_period, ma_type, stop_loss_pct, take_profit_pct, position_size_pct]
    trader = GeneticTrader([10, 50, 0, 2.5, 5.0, 10.0])
    print(f"\nTrader genes:")
    print(trader.get_genes())

    # Create Backtrader cerebro
    cerebro = bt.Cerebro()

    # Add strategy
    strategy_class = create_strategy_from_trader(trader)
    cerebro.addstrategy(strategy_class, printlog=True)

    # Add data
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    # Set initial cash and commission
    cerebro.broker.setcash(config.INITIAL_CASH)
    cerebro.broker.setcommission(commission=config.COMMISSION)

    # Run backtest
    print(f"\nStarting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    strategies = cerebro.run()
    print(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")

    # Get strategy results
    strat = strategies[0]
    print(f"\nTrade Statistics:")
    print(f"Total Trades: {strat.trade_count}")
    print(f"Winning Trades: {strat.winning_trades}")
    print(f"Losing Trades: {strat.losing_trades}")
    print(f"Win Rate: {strat.get_win_rate():.2f}%")
