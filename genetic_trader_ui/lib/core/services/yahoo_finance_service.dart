import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/bar.dart';

/// Fetches historical OHLCV data from Yahoo Finance.
class YahooFinanceService {
  final http.Client _client;

  YahooFinanceService({http.Client? client})
      : _client = client ?? http.Client();

  /// Fetch historical bars for a symbol.
  ///
  /// [period] can be '1y', '5y', '10y', 'max', etc.
  Future<List<Bar>> fetchHistory(
    String symbol, {
    String period = '10y',
  }) async {
    final url = Uri.parse(
      'https://query1.finance.yahoo.com/v8/finance/chart/$symbol'
      '?interval=1d&range=$period',
    );
    final response = await _client.get(url, headers: {
      'User-Agent': 'Mozilla/5.0',
    });

    if (response.statusCode != 200) {
      throw YahooFinanceException(
        'Failed to fetch $symbol: HTTP ${response.statusCode}',
      );
    }

    return _parseResponse(symbol, response.body);
  }

  /// Parse Yahoo Finance JSON response into a list of bars.
  List<Bar> _parseResponse(String symbol, String body) {
    final json = jsonDecode(body) as Map<String, dynamic>;
    final chart = json['chart'] as Map<String, dynamic>?;
    final results = (chart?['result'] as List?)?.cast<Map<String, dynamic>>();

    if (results == null || results.isEmpty) {
      throw YahooFinanceException('No data returned for $symbol');
    }

    final result = results.first;
    final timestamps = (result['timestamp'] as List?)?.cast<int>();
    if (timestamps == null || timestamps.isEmpty) {
      throw YahooFinanceException('No timestamps for $symbol');
    }

    final indicators = result['indicators'] as Map<String, dynamic>;
    final quote = (indicators['quote'] as List).first as Map<String, dynamic>;
    final adjCloseList = (indicators['adjclose'] as List?)
        ?.first as Map<String, dynamic>?;

    final opens = (quote['open'] as List).cast<num?>();
    final highs = (quote['high'] as List).cast<num?>();
    final lows = (quote['low'] as List).cast<num?>();
    final closes = (quote['close'] as List).cast<num?>();
    final volumes = (quote['volume'] as List).cast<num?>();
    final adjCloses = adjCloseList != null
        ? (adjCloseList['adjclose'] as List).cast<num?>()
        : null;

    final bars = <Bar>[];
    for (var i = 0; i < timestamps.length; i++) {
      // Skip bars with null OHLC values
      if (opens[i] == null ||
          highs[i] == null ||
          lows[i] == null ||
          closes[i] == null) {
        continue;
      }

      bars.add(Bar(
        symbol: symbol,
        date: DateTime.fromMillisecondsSinceEpoch(
          timestamps[i] * 1000,
          isUtc: true,
        ),
        open: opens[i]!.toDouble(),
        high: highs[i]!.toDouble(),
        low: lows[i]!.toDouble(),
        close: closes[i]!.toDouble(),
        volume: volumes[i]?.toInt() ?? 0,
        adjClose: adjCloses?[i]?.toDouble(),
      ));
    }

    return bars;
  }

  /// Rate-limit helper: wait 300ms between calls.
  Future<void> rateLimitDelay() async {
    await Future.delayed(const Duration(milliseconds: 300));
  }

  void dispose() {
    _client.close();
  }
}

/// Exception thrown by Yahoo Finance operations.
class YahooFinanceException implements Exception {
  final String message;
  const YahooFinanceException(this.message);

  @override
  String toString() => 'YahooFinanceException: $message';
}
