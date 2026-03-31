import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart' as http_testing;
import 'package:test/test.dart';
import 'package:genetic_trader_ui/core/services/yahoo_finance_service.dart';

void main() {
  group('YahooFinanceService', () {
    late YahooFinanceService service;

    /// Helper to create a mock HTTP client.
    http.Client mockClient(int statusCode, String body) {
      return http_testing.MockClient(
        (request) async => http.Response(body, statusCode),
      );
    }

    test('parses valid Yahoo Finance response', () async {
      final responseJson = jsonEncode({
        'chart': {
          'result': [
            {
              'timestamp': [1672531200, 1672617600, 1672704000],
              'indicators': {
                'quote': [
                  {
                    'open': [100.0, 102.0, 101.0],
                    'high': [105.0, 106.0, 104.0],
                    'low': [99.0, 100.0, 100.0],
                    'close': [103.0, 104.0, 102.0],
                    'volume': [1000000, 1200000, 900000],
                  }
                ],
                'adjclose': [
                  {
                    'adjclose': [102.5, 103.5, 101.5],
                  }
                ],
              },
            }
          ],
        },
      });

      service = YahooFinanceService(
        client: mockClient(200, responseJson),
      );

      final bars = await service.fetchHistory('AAPL', period: '1y');
      expect(bars.length, 3);
      expect(bars[0].symbol, 'AAPL');
      expect(bars[0].open, 100.0);
      expect(bars[0].close, 103.0);
      expect(bars[0].adjClose, 102.5);
      expect(bars[1].volume, 1200000);
    });

    test('skips bars with null OHLC values', () async {
      final responseJson = jsonEncode({
        'chart': {
          'result': [
            {
              'timestamp': [1672531200, 1672617600],
              'indicators': {
                'quote': [
                  {
                    'open': [100.0, null],
                    'high': [105.0, null],
                    'low': [99.0, null],
                    'close': [103.0, null],
                    'volume': [1000000, null],
                  }
                ],
              },
            }
          ],
        },
      });

      service = YahooFinanceService(
        client: mockClient(200, responseJson),
      );

      final bars = await service.fetchHistory('AAPL');
      expect(bars.length, 1);
      expect(bars[0].close, 103.0);
    });

    test('throws on HTTP error', () async {
      service = YahooFinanceService(
        client: mockClient(404, 'Not found'),
      );

      expect(
        () => service.fetchHistory('INVALID'),
        throwsA(isA<YahooFinanceException>()),
      );
    });

    test('throws on empty result', () async {
      final responseJson = jsonEncode({
        'chart': {
          'result': [],
        },
      });

      service = YahooFinanceService(
        client: mockClient(200, responseJson),
      );

      expect(
        () => service.fetchHistory('AAPL'),
        throwsA(isA<YahooFinanceException>()),
      );
    });
  });
}
