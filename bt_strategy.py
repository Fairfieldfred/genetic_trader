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
    Extended PandasData that includes macroeconomic indicator columns.

    When the DataFrame contains these columns, backtrader populates
    the corresponding lines. When they are absent, lines contain NaN
    and are safely ignored by the strategy.
    """

    lines = (
        'vix_close',
        'yield_curve_slope',
        'fed_funds_rate',
        'cpi_yoy',
        'unemployment_rate',
    )

    params = (
        ('vix_close', -1),
        ('yield_curve_slope', -1),
        ('fed_funds_rate', -1),
        ('cpi_yoy', -1),
        ('unemployment_rate', -1),
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

    def prenext(self):
        """Called before minimum period is met for all indicators."""
        # Make initial allocation on first bar, even before indicators are ready
        if not self.initial_allocation_done and len(self) == 1:
            self._make_initial_allocation()

    def next(self):
        """Execute strategy logic on each bar."""
        # Make initial allocation on first bar if not done in prenext
        if not self.initial_allocation_done:
            self._make_initial_allocation()
            return

        # Check if we have pending orders
        if self.order or any(self.initial_orders):
            return

        # Compute macro regime modifiers (once per bar, shared across stocks)
        macro = self._compute_macro_context()

        # Process each data feed
        for data in self.datas:
            symbol = data._name
            ma_short = self.ma_short_indicators[symbol]
            ma_long = self.ma_long_indicators[symbol]
            crossover = self.crossover_indicators[symbol]

            # Get current position for this data feed
            position = self.getposition(data)
            position_size = position.size

            # Trading logic
            if not position_size:
                # Not in market - check for buy signal (bullish crossover)
                if crossover[0] > 0:
                    # Check macro gate
                    if macro['block_buys']:
                        continue

                    # Short MA crossed above Long MA - buy signal
                    # Apply macro position scale
                    adjusted_pct = (
                        self.params.position_size_pct
                        * macro['position_scale']
                    )
                    cash = self.broker.getcash()
                    size = int((cash * adjusted_pct / 100) / data.close[0])

                    if size > 0:
                        self.log(
                            f'BUY CREATE {symbol}, Price: {data.close[0]:.2f}, '
                            f'MA Short: {ma_short[0]:.2f}, MA Long: {ma_long[0]:.2f}'
                        )
                        order = self.buy(data=data, size=size)

            else:
                # In market - check for sell signal
                current_price = data.close[0]

                # Get the average buy price for this position
                buy_price = position.price

                if buy_price:
                    pct_change = ((current_price - buy_price) / buy_price) * 100

                    # Apply macro-adjusted thresholds
                    adj_stop = (
                        self.params.stop_loss_pct
                        * macro['stop_loss_adj']
                    )
                    adj_tp = (
                        self.params.take_profit_pct
                        * macro['take_profit_adj']
                    )

                    # Check stop loss
                    if pct_change <= -adj_stop:
                        self.log(
                            f'STOP LOSS {symbol}, Price: {current_price:.2f}, '
                            f'Loss: {pct_change:.2f}%'
                        )
                        self.sell(data=data, size=position_size)

                    # Check take profit
                    elif pct_change >= adj_tp:
                        self.log(
                            f'TAKE PROFIT {symbol}, Price: {current_price:.2f}, '
                            f'Profit: {pct_change:.2f}%'
                        )
                        self.sell(data=data, size=position_size)

                    # Check MA bearish crossover
                    elif crossover[0] < 0:
                        self.log(
                            f'SELL {symbol} (Bearish Crossover), Price: {current_price:.2f}, '
                            f'MA Short: {ma_short[0]:.2f}, MA Long: {ma_long[0]:.2f}'
                        )
                        self.sell(data=data, size=position_size)

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

        if order.status in [order.Completed]:
            # Remove from initial orders if it was one
            if order in self.initial_orders:
                self.initial_orders.remove(order)

            # Get the data feed name
            data_name = order.data._name if hasattr(order.data, '_name') else 'Unknown'

            if order.isbuy():
                self.log(
                    f'BUY EXECUTED {data_name}, Price: {order.executed.price:.2f}, '
                    f'Size: {order.executed.size}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )
            else:  # Sell
                self.log(
                    f'SELL EXECUTED {data_name}, Price: {order.executed.price:.2f}, '
                    f'Size: {order.executed.size}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # Remove from initial orders if it was one
            if order in self.initial_orders:
                self.initial_orders.remove(order)
            self.log(f'Order Canceled/Margin/Rejected for {order.data._name if hasattr(order.data, "_name") else "Unknown"}')

        self.order = None


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
