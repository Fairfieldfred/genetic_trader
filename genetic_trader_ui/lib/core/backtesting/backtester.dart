import '../models/backtest_result.dart';
import '../models/bar.dart';
import '../models/portfolio_state.dart';
import '../models/trade.dart';
import 'performance.dart';

/// Order types for the backtester.
enum OrderSide { buy, sell }

/// A market order to be executed at the next bar's open.
class MarketOrder {
  final String symbol;
  final OrderSide side;
  final double shares;

  const MarketOrder({
    required this.symbol,
    required this.side,
    required this.shares,
  });
}

/// A stop order that triggers when price crosses the stop level.
class StopOrder {
  final String symbol;
  final OrderSide side;
  final double shares;
  final double stopPrice;

  const StopOrder({
    required this.symbol,
    required this.side,
    required this.shares,
    required this.stopPrice,
  });
}

/// Configuration for a backtest run.
class BacktestConfig {
  final double initialCash;
  final double commissionPct;

  const BacktestConfig({
    this.initialCash = 100000.0,
    this.commissionPct = 0.001,
  });
}

/// Strategy callback type.
///
/// Called once per bar. The strategy should add orders to [pendingOrders].
typedef StrategyCallback = void Function(
  int barIndex,
  Bar bar,
  PortfolioState state,
  List<MarketOrder> pendingOrders,
);

/// Event-driven bar-loop backtester.
class Backtester {
  /// Run a backtest on the given bars with a strategy callback.
  static BacktestResult run({
    required List<Bar> bars,
    required StrategyCallback strategy,
    BacktestConfig config = const BacktestConfig(),
  }) {
    if (bars.isEmpty) {
      return BacktestResult(
        totalReturn: 0.0,
        sharpeRatio: 0.0,
        maxDrawdown: 0.0,
        winRate: 0.0,
        numTrades: 0,
        trades: [],
        equityCurve: [],
      );
    }

    var cash = config.initialCash;
    final positions = <String, _OpenPosition>{};
    final trades = <Trade>[];
    final equityCurve = <double>[];
    final pendingOrders = <MarketOrder>[];
    final stopOrders = <StopOrder>[];

    // Track last known close price per symbol so portfolio
    // valuation uses correct prices (not the current bar's price
    // for every position).
    final lastPrice = <String, double>{};

    for (var i = 0; i < bars.length; i++) {
      final bar = bars[i];

      // Execute pending market orders whose symbol matches this bar.
      // Orders for other symbols stay pending until their bar arrives.
      final ordersToExecute = <MarketOrder>[];
      final deferredOrders = <MarketOrder>[];
      for (final order in pendingOrders) {
        if (order.symbol == bar.symbol) {
          ordersToExecute.add(order);
        } else {
          deferredOrders.add(order);
        }
      }
      pendingOrders.clear();
      pendingOrders.addAll(deferredOrders);

      for (final order in ordersToExecute) {
        final price = bar.open;
        final commission =
            price * order.shares * config.commissionPct;

        if (order.side == OrderSide.buy) {
          final cost = price * order.shares + commission;
          if (cost <= cash) {
            cash -= cost;
            if (positions.containsKey(order.symbol)) {
              final pos = positions[order.symbol]!;
              final totalShares = pos.shares + order.shares;
              final totalCost =
                  pos.shares * pos.avgPrice + order.shares * price;
              positions[order.symbol] = _OpenPosition(
                shares: totalShares,
                avgPrice: totalCost / totalShares,
                entryDate: pos.entryDate,
              );
            } else {
              positions[order.symbol] = _OpenPosition(
                shares: order.shares,
                avgPrice: price,
                entryDate: bar.date,
              );
            }
          }
        } else {
          // Sell order.
          if (positions.containsKey(order.symbol)) {
            final pos = positions[order.symbol]!;
            final sellShares =
                order.shares > pos.shares ? pos.shares : order.shares;
            cash += price * sellShares - commission;

            final pnl = (price - pos.avgPrice) * sellShares;
            final pnlPct =
                (price - pos.avgPrice) / pos.avgPrice * 100;
            trades.add(Trade(
              symbol: order.symbol,
              entryDate: pos.entryDate,
              exitDate: bar.date,
              entryPrice: pos.avgPrice,
              exitPrice: price,
              shares: sellShares,
              pnl: pnl,
              pnlPct: pnlPct,
            ));

            if (sellShares >= pos.shares) {
              positions.remove(order.symbol);
            } else {
              positions[order.symbol] = _OpenPosition(
                shares: pos.shares - sellShares,
                avgPrice: pos.avgPrice,
                entryDate: pos.entryDate,
              );
            }
          }
        }
      }

      // Check stop orders for the current bar's symbol only.
      final stopsToRemove = <int>[];
      for (var j = 0; j < stopOrders.length; j++) {
        final stop = stopOrders[j];
        if (stop.symbol != bar.symbol) continue;
        if (stop.side == OrderSide.sell &&
            bar.low <= stop.stopPrice) {
          if (positions.containsKey(stop.symbol)) {
            final pos = positions[stop.symbol]!;
            final sellShares =
                stop.shares > pos.shares ? pos.shares : stop.shares;
            final execPrice = stop.stopPrice;
            final commission =
                execPrice * sellShares * config.commissionPct;
            cash += execPrice * sellShares - commission;

            final pnl = (execPrice - pos.avgPrice) * sellShares;
            final pnlPct =
                (execPrice - pos.avgPrice) / pos.avgPrice * 100;
            trades.add(Trade(
              symbol: stop.symbol,
              entryDate: pos.entryDate,
              exitDate: bar.date,
              entryPrice: pos.avgPrice,
              exitPrice: execPrice,
              shares: sellShares,
              pnl: pnl,
              pnlPct: pnlPct,
            ));

            if (sellShares >= pos.shares) {
              positions.remove(stop.symbol);
            } else {
              positions[stop.symbol] = _OpenPosition(
                shares: pos.shares - sellShares,
                avgPrice: pos.avgPrice,
                entryDate: pos.entryDate,
              );
            }
          }
          stopsToRemove.add(j);
        }
      }
      for (final j in stopsToRemove.reversed) {
        stopOrders.removeAt(j);
      }

      // Update last known price for this bar's symbol.
      lastPrice[bar.symbol] = bar.close;

      // Calculate portfolio value using per-symbol prices.
      var portfolioValue = cash;
      for (final entry in positions.entries) {
        final price = lastPrice[entry.key] ?? entry.value.avgPrice;
        portfolioValue += entry.value.shares * price;
      }
      equityCurve.add(portfolioValue);

      // Build portfolio state for strategy.
      final portfolioPositions = <String, PositionInfo>{};
      for (final entry in positions.entries) {
        portfolioPositions[entry.key] = PositionInfo(
          shares: entry.value.shares,
          avgPrice: entry.value.avgPrice,
        );
      }
      final state = PortfolioState(
        cash: cash,
        positions: portfolioPositions,
      );

      // Call strategy.
      strategy(i, bar, state, pendingOrders);
    }

    // Calculate metrics.
    final totalReturn = equityCurve.isEmpty
        ? 0.0
        : (equityCurve.last - config.initialCash) /
            config.initialCash;

    // Daily returns for Sharpe.
    final dailyReturns = <double>[];
    for (var i = 1; i < equityCurve.length; i++) {
      dailyReturns.add(
        (equityCurve[i] - equityCurve[i - 1]) / equityCurve[i - 1],
      );
    }

    return BacktestResult(
      totalReturn: totalReturn,
      sharpeRatio: Performance.sharpeRatio(dailyReturns),
      maxDrawdown: Performance.maxDrawdown(equityCurve),
      winRate: Performance.winRate(trades),
      numTrades: trades.length,
      trades: trades,
      equityCurve: equityCurve,
    );
  }
}

class _OpenPosition {
  final double shares;
  final double avgPrice;
  final DateTime entryDate;

  const _OpenPosition({
    required this.shares,
    required this.avgPrice,
    required this.entryDate,
  });
}
