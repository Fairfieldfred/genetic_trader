import 'package:flutter_test/flutter_test.dart';
import 'package:genetic_trader_ui/core/services/database_service.dart';

void main() {
  group('DatabaseService', () {
    test('isOpen returns false before open()', () {
      final db = DatabaseService();
      expect(db.isOpen, isFalse);
    });

    test('accessing bars throws StateError when not open', () {
      final db = DatabaseService();
      expect(
        () => db.getBars('AAPL'),
        throwsA(isA<StateError>()),
      );
    });

    test('accessing stock throws StateError when not open', () {
      final db = DatabaseService();
      expect(
        () => db.getStock('AAPL'),
        throwsA(isA<StateError>()),
      );
    });

    test('getBarCount throws StateError when not open', () {
      final db = DatabaseService();
      expect(
        () => db.getBarCount('AAPL'),
        throwsA(isA<StateError>()),
      );
    });

    test('getEvolutionRuns throws StateError when not open', () {
      final db = DatabaseService();
      expect(
        () => db.getEvolutionRuns(),
        throwsA(isA<StateError>()),
      );
    });

    test('close on unopened database completes without error', () async {
      final db = DatabaseService();
      await db.close();
      expect(db.isOpen, isFalse);
    });
  });
}
