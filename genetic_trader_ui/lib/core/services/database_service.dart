import 'package:sqflite/sqflite.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

import '../models/bar.dart';
import '../models/stock.dart';

/// SQLite database service for storing stock data and evolution runs.
class DatabaseService {
  Database? _db;

  /// Whether the database is currently open.
  bool get isOpen => _db != null;

  /// Open (or create) the database at the default documents path.
  Future<void> open() async {
    if (_db != null) return;
    final dir = await getApplicationDocumentsDirectory();
    final dbPath = p.join(dir.path, 'genetic_trader.db');
    _db = await openDatabase(
      dbPath,
      version: 1,
      onCreate: _onCreate,
    );
  }

  /// Open with a custom path (for testing or custom locations).
  Future<void> openAt(String path) async {
    if (_db != null) return;
    _db = await openDatabase(
      path,
      version: 1,
      onCreate: _onCreate,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE stocks (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        sector TEXT,
        index_membership TEXT,
        last_updated TEXT
      )
    ''');
    await db.execute('''
      CREATE TABLE bars (
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume INTEGER NOT NULL,
        adj_close REAL,
        PRIMARY KEY (symbol, date)
      )
    ''');
    await db.execute('''
      CREATE TABLE indicators (
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        sma_20 REAL, sma_50 REAL, sma_200 REAL,
        ema_12 REAL, ema_26 REAL,
        rsi_14 REAL,
        macd REAL, macd_signal REAL, macd_hist REAL,
        bb_upper REAL, bb_middle REAL, bb_lower REAL,
        atr_14 REAL,
        adx_14 REAL,
        PRIMARY KEY (symbol, date)
      )
    ''');
    await db.execute('''
      CREATE TABLE evolution_runs (
        run_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        config_json TEXT,
        status TEXT NOT NULL,
        best_fitness REAL,
        best_chromosome_json TEXT,
        summary_json TEXT
      )
    ''');
    await db.execute(
      'CREATE INDEX idx_bars_symbol ON bars(symbol)',
    );
    await db.execute(
      'CREATE INDEX idx_bars_date ON bars(date)',
    );
  }

  Database get _database {
    if (_db == null) {
      throw StateError('Database not open. Call open() first.');
    }
    return _db!;
  }

  // --- Stock CRUD ---

  /// Insert or update a stock record.
  Future<void> upsertStock(Stock stock) async {
    await _database.insert(
      'stocks',
      {
        'symbol': stock.symbol,
        'name': stock.name,
        'sector': stock.sector,
        'index_membership': stock.indexMembership.join(','),
        'last_updated': DateTime.now().toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Get a stock by symbol.
  Future<Stock?> getStock(String symbol) async {
    final rows = await _database.query(
      'stocks',
      where: 'symbol = ?',
      whereArgs: [symbol],
    );
    if (rows.isEmpty) return null;
    final row = rows.first;
    final membership = (row['index_membership'] as String?)
            ?.split(',')
            .where((s) => s.isNotEmpty)
            .toList() ??
        [];
    return Stock(
      symbol: row['symbol'] as String,
      name: row['name'] as String?,
      sector: row['sector'] as String?,
      indexMembership: membership,
    );
  }

  /// Get last_updated timestamp for a stock.
  Future<DateTime?> getStockLastUpdated(String symbol) async {
    final rows = await _database.query(
      'stocks',
      columns: ['last_updated'],
      where: 'symbol = ?',
      whereArgs: [symbol],
    );
    if (rows.isEmpty) return null;
    final ts = rows.first['last_updated'] as String?;
    if (ts == null) return null;
    return DateTime.tryParse(ts);
  }

  // --- Bar CRUD ---

  /// Insert bars in a batch (upsert).
  Future<void> insertBars(List<Bar> bars) async {
    if (bars.isEmpty) return;
    final batch = _database.batch();
    for (final bar in bars) {
      batch.insert(
        'bars',
        {
          'symbol': bar.symbol,
          'date': bar.date.toIso8601String().substring(0, 10),
          'open': bar.open,
          'high': bar.high,
          'low': bar.low,
          'close': bar.close,
          'volume': bar.volume,
          'adj_close': bar.adjClose,
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    }
    await batch.commit(noResult: true);
  }

  /// Get bars for a symbol, sorted by date ascending.
  Future<List<Bar>> getBars(String symbol) async {
    final rows = await _database.query(
      'bars',
      where: 'symbol = ?',
      whereArgs: [symbol],
      orderBy: 'date ASC',
    );
    return rows.map(_rowToBar).toList();
  }

  /// Get bars for a symbol within a date range.
  Future<List<Bar>> getBarsInRange(
    String symbol,
    DateTime start,
    DateTime end,
  ) async {
    final startStr = start.toIso8601String().substring(0, 10);
    final endStr = end.toIso8601String().substring(0, 10);
    final rows = await _database.query(
      'bars',
      where: 'symbol = ? AND date >= ? AND date <= ?',
      whereArgs: [symbol, startStr, endStr],
      orderBy: 'date ASC',
    );
    return rows.map(_rowToBar).toList();
  }

  /// Get the count of bars for a symbol.
  Future<int> getBarCount(String symbol) async {
    final result = await _database.rawQuery(
      'SELECT COUNT(*) as cnt FROM bars WHERE symbol = ?',
      [symbol],
    );
    return (result.first['cnt'] as num).toInt();
  }

  Bar _rowToBar(Map<String, Object?> row) {
    return Bar(
      symbol: row['symbol'] as String,
      date: DateTime.parse(row['date'] as String),
      open: (row['open'] as num).toDouble(),
      high: (row['high'] as num).toDouble(),
      low: (row['low'] as num).toDouble(),
      close: (row['close'] as num).toDouble(),
      volume: (row['volume'] as num).toInt(),
      adjClose: (row['adj_close'] as num?)?.toDouble(),
    );
  }

  // --- Evolution Runs ---

  /// Save an evolution run.
  Future<void> saveEvolutionRun({
    required String runId,
    required String configJson,
    required String status,
    double? bestFitness,
    String? bestChromosomeJson,
    String? summaryJson,
  }) async {
    await _database.insert(
      'evolution_runs',
      {
        'run_id': runId,
        'created_at': DateTime.now().toIso8601String(),
        'config_json': configJson,
        'status': status,
        'best_fitness': bestFitness,
        'best_chromosome_json': bestChromosomeJson,
        'summary_json': summaryJson,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Update evolution run status and results.
  Future<void> updateEvolutionRun({
    required String runId,
    String? status,
    double? bestFitness,
    String? bestChromosomeJson,
    String? summaryJson,
  }) async {
    final values = <String, dynamic>{};
    if (status != null) values['status'] = status;
    if (bestFitness != null) values['best_fitness'] = bestFitness;
    if (bestChromosomeJson != null) {
      values['best_chromosome_json'] = bestChromosomeJson;
    }
    if (summaryJson != null) values['summary_json'] = summaryJson;
    if (values.isEmpty) return;
    await _database.update(
      'evolution_runs',
      values,
      where: 'run_id = ?',
      whereArgs: [runId],
    );
  }

  /// Get all evolution runs ordered by creation date descending.
  Future<List<Map<String, dynamic>>> getEvolutionRuns() async {
    return _database.query(
      'evolution_runs',
      orderBy: 'created_at DESC',
    );
  }

  /// Close the database.
  Future<void> close() async {
    await _db?.close();
    _db = null;
  }
}
