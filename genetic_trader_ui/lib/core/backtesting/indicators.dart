import 'dart:math' show sqrt, max;

import '../models/bar.dart';

/// Technical indicator calculations.
///
/// All functions return a List of the same length as the input.
/// Insufficient-data positions are filled with double.nan.
class Indicators {
  Indicators._();

  /// Simple Moving Average.
  static List<double> sma(List<double> prices, int period) {
    final result = List<double>.filled(prices.length, double.nan);
    if (period > prices.length) return result;

    var sum = 0.0;
    for (var i = 0; i < prices.length; i++) {
      sum += prices[i];
      if (i >= period) {
        sum -= prices[i - period];
      }
      if (i >= period - 1) {
        result[i] = sum / period;
      }
    }
    return result;
  }

  /// Exponential Moving Average.
  ///
  /// Seeded with SMA of the first [period] values.
  static List<double> ema(List<double> prices, int period) {
    final result = List<double>.filled(prices.length, double.nan);
    if (period > prices.length) return result;

    final multiplier = 2.0 / (period + 1);

    // Seed with SMA
    var sum = 0.0;
    for (var i = 0; i < period; i++) {
      sum += prices[i];
    }
    result[period - 1] = sum / period;

    // Calculate EMA
    for (var i = period; i < prices.length; i++) {
      result[i] =
          prices[i] * multiplier + result[i - 1] * (1 - multiplier);
    }
    return result;
  }

  /// Relative Strength Index.
  static List<double> rsi(List<double> prices, int period) {
    final result = List<double>.filled(prices.length, double.nan);
    if (prices.length < period + 1) return result;

    // Calculate price changes
    final changes = <double>[];
    for (var i = 1; i < prices.length; i++) {
      changes.add(prices[i] - prices[i - 1]);
    }

    // First average gain/loss
    var avgGain = 0.0;
    var avgLoss = 0.0;
    for (var i = 0; i < period; i++) {
      if (changes[i] > 0) {
        avgGain += changes[i];
      } else {
        avgLoss += -changes[i];
      }
    }
    avgGain /= period;
    avgLoss /= period;

    // First RSI
    if (avgLoss == 0) {
      result[period] = 100.0;
    } else {
      final rs = avgGain / avgLoss;
      result[period] = 100.0 - 100.0 / (1.0 + rs);
    }

    // Subsequent RSI using smoothed averages
    for (var i = period; i < changes.length; i++) {
      final gain = changes[i] > 0 ? changes[i] : 0.0;
      final loss = changes[i] < 0 ? -changes[i] : 0.0;
      avgGain = (avgGain * (period - 1) + gain) / period;
      avgLoss = (avgLoss * (period - 1) + loss) / period;

      if (avgLoss == 0) {
        result[i + 1] = 100.0;
      } else {
        final rs = avgGain / avgLoss;
        result[i + 1] = 100.0 - 100.0 / (1.0 + rs);
      }
    }

    return result;
  }

  /// MACD (Moving Average Convergence Divergence).
  ///
  /// Returns a record with macd line, signal line, and histogram.
  static ({
    List<double> macd,
    List<double> signal,
    List<double> histogram,
  }) macd(
    List<double> prices, {
    int fast = 12,
    int slow = 26,
    int signalPeriod = 9,
  }) {
    final emaFast = ema(prices, fast);
    final emaSlow = ema(prices, slow);

    final macdLine =
        List<double>.filled(prices.length, double.nan);
    for (var i = 0; i < prices.length; i++) {
      if (!emaFast[i].isNaN && !emaSlow[i].isNaN) {
        macdLine[i] = emaFast[i] - emaSlow[i];
      }
    }

    // Signal line = EMA of MACD line.
    // Collect valid MACD values and their original indices.
    final validMacd = <double>[];
    final validIndices = <int>[];
    for (var i = 0; i < macdLine.length; i++) {
      if (!macdLine[i].isNaN) {
        validMacd.add(macdLine[i]);
        validIndices.add(i);
      }
    }

    final signalLine =
        List<double>.filled(prices.length, double.nan);
    final histogram =
        List<double>.filled(prices.length, double.nan);

    if (validMacd.length >= signalPeriod) {
      final signalEma = ema(validMacd, signalPeriod);
      for (var i = 0; i < validMacd.length; i++) {
        if (!signalEma[i].isNaN) {
          signalLine[validIndices[i]] = signalEma[i];
          histogram[validIndices[i]] =
              macdLine[validIndices[i]] - signalEma[i];
        }
      }
    }

    return (
      macd: macdLine,
      signal: signalLine,
      histogram: histogram,
    );
  }

  /// Bollinger Bands.
  static ({
    List<double> upper,
    List<double> middle,
    List<double> lower,
  }) bollingerBands(
    List<double> prices,
    int period,
    double stdDevMultiplier,
  ) {
    final middle = sma(prices, period);
    final upper =
        List<double>.filled(prices.length, double.nan);
    final lower =
        List<double>.filled(prices.length, double.nan);

    for (var i = period - 1; i < prices.length; i++) {
      // Calculate standard deviation
      var sumSq = 0.0;
      for (var j = i - period + 1; j <= i; j++) {
        final diff = prices[j] - middle[i];
        sumSq += diff * diff;
      }
      final stdDev = sqrt(sumSq / period);
      upper[i] = middle[i] + stdDevMultiplier * stdDev;
      lower[i] = middle[i] - stdDevMultiplier * stdDev;
    }

    return (upper: upper, middle: middle, lower: lower);
  }

  /// Average True Range.
  static List<double> atr(List<Bar> bars, int period) {
    final result = List<double>.filled(bars.length, double.nan);
    if (bars.length < period) return result;

    // Calculate true range for each bar
    final tr = List<double>.filled(bars.length, 0.0);
    tr[0] = bars[0].high - bars[0].low;
    for (var i = 1; i < bars.length; i++) {
      final hl = bars[i].high - bars[i].low;
      final hpc = (bars[i].high - bars[i - 1].close).abs();
      final lpc = (bars[i].low - bars[i - 1].close).abs();
      tr[i] = max(hl, max(hpc, lpc));
    }

    // First ATR = average of first `period` true ranges
    var atrVal = 0.0;
    for (var i = 0; i < period; i++) {
      atrVal += tr[i];
    }
    atrVal /= period;
    result[period - 1] = atrVal;

    // Subsequent ATR using smoothing
    for (var i = period; i < bars.length; i++) {
      atrVal = (atrVal * (period - 1) + tr[i]) / period;
      result[i] = atrVal;
    }

    return result;
  }

  /// Average Directional Index.
  static List<double> adx(List<Bar> bars, int period) {
    final result = List<double>.filled(bars.length, double.nan);
    if (bars.length < period * 2) return result;

    // Calculate +DM, -DM, TR
    final plusDm = List<double>.filled(bars.length, 0.0);
    final minusDm = List<double>.filled(bars.length, 0.0);
    final tr = List<double>.filled(bars.length, 0.0);

    tr[0] = bars[0].high - bars[0].low;
    for (var i = 1; i < bars.length; i++) {
      final upMove = bars[i].high - bars[i - 1].high;
      final downMove = bars[i - 1].low - bars[i].low;

      plusDm[i] =
          (upMove > downMove && upMove > 0) ? upMove : 0.0;
      minusDm[i] =
          (downMove > upMove && downMove > 0) ? downMove : 0.0;

      final hl = bars[i].high - bars[i].low;
      final hpc = (bars[i].high - bars[i - 1].close).abs();
      final lpc = (bars[i].low - bars[i - 1].close).abs();
      tr[i] = max(hl, max(hpc, lpc));
    }

    // Smooth with Wilder's method
    var smoothTr = 0.0;
    var smoothPlusDm = 0.0;
    var smoothMinusDm = 0.0;

    for (var i = 1; i <= period; i++) {
      smoothTr += tr[i];
      smoothPlusDm += plusDm[i];
      smoothMinusDm += minusDm[i];
    }

    final dx = List<double>.filled(bars.length, double.nan);

    for (var i = period; i < bars.length; i++) {
      if (i > period) {
        smoothTr = smoothTr - smoothTr / period + tr[i];
        smoothPlusDm =
            smoothPlusDm - smoothPlusDm / period + plusDm[i];
        smoothMinusDm =
            smoothMinusDm - smoothMinusDm / period + minusDm[i];
      }

      if (smoothTr == 0) continue;

      final plusDi = 100.0 * smoothPlusDm / smoothTr;
      final minusDi = 100.0 * smoothMinusDm / smoothTr;

      final diSum = plusDi + minusDi;
      if (diSum == 0) continue;

      dx[i] = 100.0 * (plusDi - minusDi).abs() / diSum;
    }

    // ADX = smoothed DX over period
    var adxSum = 0.0;
    var adxCount = 0;
    for (var i = period;
        i < bars.length && adxCount < period;
        i++) {
      if (!dx[i].isNaN) {
        adxSum += dx[i];
        adxCount++;
        if (adxCount == period) {
          result[i] = adxSum / period;
        }
      }
    }

    // Find where ADX was first set and continue smoothing
    var lastAdx = double.nan;
    for (var i = 0; i < result.length; i++) {
      if (!result[i].isNaN) {
        lastAdx = result[i];
        for (var j = i + 1; j < bars.length; j++) {
          if (!dx[j].isNaN) {
            lastAdx =
                (lastAdx * (period - 1) + dx[j]) / period;
            result[j] = lastAdx;
          }
        }
        break;
      }
    }

    return result;
  }
}
