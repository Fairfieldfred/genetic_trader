import 'package:test/test.dart';
import 'package:genetic_trader_ui/core/backtesting/indicators.dart';
import 'package:genetic_trader_ui/core/models/bar.dart';

void main() {
  group('SMA', () {
    test('calculates simple moving average', () {
      final prices = [1.0, 2.0, 3.0, 4.0, 5.0];
      final result = Indicators.sma(prices, 3);
      // First 2 should be NaN (insufficient data)
      expect(result[0].isNaN, isTrue);
      expect(result[1].isNaN, isTrue);
      // sma(3) of [1,2,3] = 2.0
      expect(result[2], closeTo(2.0, 0.001));
      // sma(3) of [2,3,4] = 3.0
      expect(result[3], closeTo(3.0, 0.001));
      // sma(3) of [3,4,5] = 4.0
      expect(result[4], closeTo(4.0, 0.001));
    });

    test('returns all NaN for period > length', () {
      final prices = [1.0, 2.0];
      final result = Indicators.sma(prices, 5);
      expect(result.every((v) => v.isNaN), isTrue);
    });
  });

  group('EMA', () {
    test('calculates exponential moving average', () {
      final prices = [
        22.27,
        22.19,
        22.08,
        22.17,
        22.18,
        22.13,
        22.23,
        22.43,
        22.24,
        22.29,
      ];
      final result = Indicators.ema(prices, 5);
      // First 4 are NaN
      for (var i = 0; i < 4; i++) {
        expect(result[i].isNaN, isTrue);
      }
      // EMA(5) seed = SMA of first 5
      // = (22.27+22.19+22.08+22.17+22.18)/5 = 22.178
      expect(result[4], closeTo(22.178, 0.01));
      // Then EMA updates with multiplier 2/(5+1) = 0.3333
      // result[5] = 22.13*0.3333 + 22.178*0.6667 = 22.162
      expect(result[5], closeTo(22.162, 0.01));
    });
  });

  group('RSI', () {
    test('calculates RSI with known values', () {
      // Use a simple up-trending series
      final prices = [
        44.0,
        44.34,
        44.09,
        43.61,
        44.33,
        44.83,
        45.10,
        45.42,
        45.84,
        46.08,
        45.89,
        46.03,
        45.61,
        46.28,
        46.28,
        46.00,
        46.03,
        46.41,
        46.22,
        45.64,
      ];
      final result = Indicators.rsi(prices, 14);
      // First 14 values should be NaN
      for (var i = 0; i < 14; i++) {
        expect(result[i].isNaN, isTrue);
      }
      // RSI should be between 0 and 100
      for (var i = 14; i < result.length; i++) {
        expect(result[i], greaterThanOrEqualTo(0.0));
        expect(result[i], lessThanOrEqualTo(100.0));
      }
    });

    test('RSI is 100 for all-up moves', () {
      final prices = [
        1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0,
        9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0,
      ];
      final result = Indicators.rsi(prices, 14);
      // After period, RSI should be 100 (all gains, no losses)
      expect(result[14], closeTo(100.0, 0.001));
    });
  });

  group('MACD', () {
    test('returns macd, signal, and histogram', () {
      // Generate 35 prices (enough for MACD with default 12,26,9)
      final prices = List.generate(35, (i) => 100.0 + i * 0.5);
      final result = Indicators.macd(prices);
      expect(result.macd.length, 35);
      expect(result.signal.length, 35);
      expect(result.histogram.length, 35);
    });

    test('MACD line is EMA(12) - EMA(26)', () {
      final prices = List.generate(
        40,
        (i) => 100.0 + i * 0.3 + (i % 3) * 0.1,
      );
      final result = Indicators.macd(prices);
      final ema12 = Indicators.ema(prices, 12);
      final ema26 = Indicators.ema(prices, 26);
      // Check at index 30 (well after both EMAs are valid)
      expect(
        result.macd[30],
        closeTo(ema12[30] - ema26[30], 0.001),
      );
    });
  });

  group('Bollinger Bands', () {
    test('middle band equals SMA', () {
      final prices = [
        20.0, 21.0, 22.0, 21.5, 22.5,
        23.0, 22.0, 21.0, 20.5, 21.5,
        22.0, 23.0, 22.5, 21.5, 20.0,
        21.0, 22.0, 23.0, 22.5, 21.5,
      ];
      final result = Indicators.bollingerBands(prices, 10, 2.0);
      final sma = Indicators.sma(prices, 10);
      for (var i = 0; i < prices.length; i++) {
        if (!sma[i].isNaN) {
          expect(result.middle[i], closeTo(sma[i], 0.001));
        }
      }
    });

    test('upper > middle > lower when valid', () {
      final prices = [
        20.0, 21.0, 22.0, 21.5, 22.5,
        23.0, 22.0, 21.0, 20.5, 21.5,
        22.0, 23.0, 22.5, 21.5, 20.0,
        21.0, 22.0, 23.0, 22.5, 21.5,
      ];
      final result = Indicators.bollingerBands(prices, 10, 2.0);
      for (var i = 9; i < prices.length; i++) {
        expect(result.upper[i], greaterThan(result.middle[i]));
        expect(
          result.middle[i],
          greaterThan(result.lower[i]),
        );
      }
    });
  });

  group('ATR', () {
    test('calculates average true range', () {
      final bars = [
        _bar(48.70, 49.05, 48.60, 49.00),
        _bar(49.00, 49.35, 48.90, 49.20),
        _bar(49.20, 49.92, 49.00, 49.80),
        _bar(49.80, 50.19, 49.50, 49.70),
        _bar(49.70, 49.80, 49.30, 49.60),
        _bar(49.60, 50.10, 49.40, 50.00),
        _bar(50.00, 50.30, 49.80, 50.20),
      ];
      final result = Indicators.atr(bars, 3);
      // First 2 are NaN (need period-1 prior bars)
      expect(result[0].isNaN, isTrue);
      expect(result[1].isNaN, isTrue);
      // ATR should be positive
      for (var i = 2; i < result.length; i++) {
        expect(result[i], greaterThan(0.0));
      }
    });
  });

  group('ADX', () {
    test('ADX values are between 0 and 100', () {
      // Generate enough bars for ADX calculation
      final bars = List.generate(40, (i) {
        final base = 100.0 + i * 0.5;
        return _bar(base, base + 1.5, base - 1.0, base + 0.3);
      });
      final result = Indicators.adx(bars, 14);
      for (var i = 0; i < result.length; i++) {
        if (!result[i].isNaN) {
          expect(result[i], greaterThanOrEqualTo(0.0));
          expect(result[i], lessThanOrEqualTo(100.0));
        }
      }
    });
  });
}

Bar _bar(double open, double high, double low, double close) {
  return Bar(
    symbol: 'TEST',
    date: DateTime(2023),
    open: open,
    high: high,
    low: low,
    close: close,
    volume: 1000,
  );
}
