import '../models/stock.dart';
import 'database_service.dart';
import 'index_service.dart';
import 'yahoo_finance_service.dart';

/// Result of a data sync operation.
class SyncResult {
  final int symbolsSynced;
  final int symbolsFailed;
  final int totalBars;
  final List<String> errors;

  const SyncResult({
    required this.symbolsSynced,
    required this.symbolsFailed,
    required this.totalBars,
    this.errors = const [],
  });
}

/// Orchestrates fetching stock data and storing it in the database.
class DataSyncService {
  final YahooFinanceService _yahoo;
  final DatabaseService _db;

  DataSyncService({
    required YahooFinanceService yahoo,
    required DatabaseService db,
  })  : _yahoo = yahoo,
        _db = db;

  /// Sync all symbols for multiple indices (deduplicates overlaps).
  Future<SyncResult> syncIndices(
    Set<IndexType> indices, {
    void Function(int done, int total)? onProgress,
    String period = '10y',
  }) async {
    // Deduplicate symbols across indices, track membership
    final symbolToIndices = <String, Set<IndexType>>{};
    for (final idx in indices) {
      for (final s in IndexService.getSymbols(idx)) {
        symbolToIndices.putIfAbsent(s, () => {}).add(idx);
      }
    }
    final symbols = symbolToIndices.keys.toList()..sort();
    int synced = 0;
    int failed = 0;
    int totalBars = 0;
    final errors = <String>[];

    for (var i = 0; i < symbols.length; i++) {
      final symbol = symbols[i];
      try {
        final lastUpdated = await _db.getStockLastUpdated(symbol);
        if (lastUpdated != null &&
            DateTime.now().difference(lastUpdated).inHours < 24) {
          synced++;
          onProgress?.call(i + 1, symbols.length);
          continue;
        }
        final bars = await _yahoo.fetchHistory(symbol, period: period);
        await _db.insertBars(bars);
        final membership = symbolToIndices[symbol]!
            .map((t) => t.name.toUpperCase())
            .toList();
        await _db.upsertStock(Stock(
          symbol: symbol,
          indexMembership: membership,
        ));
        totalBars += bars.length;
        synced++;
      } catch (e) {
        failed++;
        errors.add('$symbol: $e');
      }
      onProgress?.call(i + 1, symbols.length);
      await _yahoo.rateLimitDelay();
    }

    return SyncResult(
      symbolsSynced: synced,
      symbolsFailed: failed,
      totalBars: totalBars,
      errors: errors,
    );
  }

  /// Sync all symbols for a single index.
  ///
  /// Skips symbols that were updated within the last 24 hours.
  Future<SyncResult> syncIndex(
    IndexType indexType, {
    void Function(int done, int total)? onProgress,
    String period = '10y',
  }) async {
    final symbols = IndexService.getSymbols(indexType);
    int synced = 0;
    int failed = 0;
    int totalBars = 0;
    final errors = <String>[];

    for (var i = 0; i < symbols.length; i++) {
      final symbol = symbols[i];

      try {
        // Check if recently updated
        final lastUpdated = await _db.getStockLastUpdated(symbol);
        if (lastUpdated != null &&
            DateTime.now().difference(lastUpdated).inHours < 24) {
          synced++;
          onProgress?.call(i + 1, symbols.length);
          continue;
        }

        // Fetch from Yahoo Finance
        final bars = await _yahoo.fetchHistory(symbol, period: period);

        // Store in database
        await _db.insertBars(bars);
        await _db.upsertStock(Stock(
          symbol: symbol,
          indexMembership: [indexType.name.toUpperCase()],
        ));

        totalBars += bars.length;
        synced++;
      } catch (e) {
        failed++;
        errors.add('$symbol: $e');
      }

      onProgress?.call(i + 1, symbols.length);

      // Rate limit
      await _yahoo.rateLimitDelay();
    }

    return SyncResult(
      symbolsSynced: synced,
      symbolsFailed: failed,
      totalBars: totalBars,
      errors: errors,
    );
  }
}
