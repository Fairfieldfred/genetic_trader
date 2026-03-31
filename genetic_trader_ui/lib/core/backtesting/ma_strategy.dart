import '../models/bar.dart';
import '../models/chromosome.dart';
import '../models/portfolio_state.dart';
import 'backtester.dart';
import 'indicators.dart';

/// MA crossover strategy using gene parameters with expression
/// weighting.
class MaStrategy {
  // Neutral defaults for silenced genes.
  static const _defaultShortPeriod = 20.0;
  static const _defaultLongPeriod = 50.0;
  static const _defaultMaType = 0.0;
  static const _defaultStopLoss = 5.0;
  static const _defaultTakeProfit = 8.0;
  static const _defaultPositionSize = 10.0;

  /// Create a strategy callback from a chromosome's genes.
  ///
  /// Uses [Chromosome.effectiveValue] so that silenced genes
  /// fall back to neutral defaults.
  ///
  /// Moving averages are computed **per symbol** so that
  /// multi-symbol bar lists produce correct crossover signals.
  static StrategyCallback fromChromosome(
    Chromosome chromosome,
    List<Bar> bars,
  ) {
    final shortPeriod = chromosome
        .effectiveValue(
          'ma_short_period',
          neutral: _defaultShortPeriod,
        )
        .round();
    final longPeriod = chromosome
        .effectiveValue(
          'ma_long_period',
          neutral: _defaultLongPeriod,
        )
        .round();
    final maType = chromosome
        .effectiveValue(
          'ma_type',
          neutral: _defaultMaType,
        )
        .round(); // 0=SMA, 1=EMA
    final stopLossPct = chromosome.effectiveValue(
      'stop_loss_pct',
      neutral: _defaultStopLoss,
    );
    final takeProfitPct = chromosome.effectiveValue(
      'take_profit_pct',
      neutral: _defaultTakeProfit,
    );
    final positionSizePct = chromosome.effectiveValue(
      'position_size_pct',
      neutral: _defaultPositionSize,
    );

    // Group bars by symbol and compute MAs per symbol.
    // Maps: symbol → list of (barIndex, shortMA, longMA).
    final symbolIndices = <String, List<int>>{};
    for (var i = 0; i < bars.length; i++) {
      symbolIndices
          .putIfAbsent(bars[i].symbol, () => [])
          .add(i);
    }

    // For each bar, store its per-symbol short/long MA value.
    final shortMa = List<double>.filled(bars.length, double.nan);
    final longMa = List<double>.filled(bars.length, double.nan);

    for (final entry in symbolIndices.entries) {
      final indices = entry.value;
      final closes = indices.map((i) => bars[i].close).toList();

      final List<double> symShort;
      final List<double> symLong;
      if (maType == 1) {
        symShort = Indicators.ema(closes, shortPeriod);
        symLong = Indicators.ema(closes, longPeriod);
      } else {
        symShort = Indicators.sma(closes, shortPeriod);
        symLong = Indicators.sma(closes, longPeriod);
      }

      // Map per-symbol MA values back to flat bar indices.
      for (var j = 0; j < indices.length; j++) {
        shortMa[indices[j]] = symShort[j];
        longMa[indices[j]] = symLong[j];
      }
    }

    // Track previous MA values per symbol for crossover detection.
    final prevShortMap = <String, double>{};
    final prevLongMap = <String, double>{};

    return (
      int barIndex,
      Bar bar,
      PortfolioState state,
      List<MarketOrder> pendingOrders,
    ) {
      if (shortMa[barIndex].isNaN || longMa[barIndex].isNaN) {
        // Update prev even for NaN so first valid bar has a prev.
        prevShortMap[bar.symbol] = shortMa[barIndex];
        prevLongMap[bar.symbol] = longMa[barIndex];
        return;
      }

      final symbol = bar.symbol;
      final prevShort = prevShortMap[symbol];
      final prevLong = prevLongMap[symbol];

      // Store current values as previous for next callback.
      prevShortMap[symbol] = shortMa[barIndex];
      prevLongMap[symbol] = longMa[barIndex];

      // Need valid previous values to detect crossover.
      if (prevShort == null ||
          prevLong == null ||
          prevShort.isNaN ||
          prevLong.isNaN) {
        return;
      }

      final hasPosition = state.positions.containsKey(symbol);
      final currShort = shortMa[barIndex];
      final currLong = longMa[barIndex];

      // Golden cross - buy signal.
      if (prevShort <= prevLong &&
          currShort > currLong &&
          !hasPosition) {
        final currentPrices = {symbol: bar.close};
        final portfolioValue = state.totalValue(currentPrices);
        final allocAmount = portfolioValue * positionSizePct / 100.0;
        final shares = (allocAmount / bar.close).floorToDouble();
        if (shares > 0) {
          pendingOrders.add(MarketOrder(
            symbol: symbol,
            side: OrderSide.buy,
            shares: shares,
          ));
        }
      }

      // Death cross - sell signal.
      if (prevShort >= prevLong &&
          currShort < currLong &&
          hasPosition) {
        final pos = state.positions[symbol]!;
        pendingOrders.add(MarketOrder(
          symbol: symbol,
          side: OrderSide.sell,
          shares: pos.shares,
        ));
      }

      // Stop-loss and take-profit checks.
      if (hasPosition) {
        final pos = state.positions[symbol]!;
        final pnlPct =
            (bar.close - pos.avgPrice) / pos.avgPrice * 100;

        if (pnlPct <= -stopLossPct || pnlPct >= takeProfitPct) {
          pendingOrders.add(MarketOrder(
            symbol: symbol,
            side: OrderSide.sell,
            shares: pos.shares,
          ));
        }
      }
    };
  }
}
