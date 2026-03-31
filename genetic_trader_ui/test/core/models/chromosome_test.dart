import 'package:test/test.dart';
import 'package:genetic_trader_ui/core/models/chromosome.dart';

void main() {
  group('Chromosome', () {
    test('creates with genes and default fitness', () {
      final c = Chromosome(genes: {'ma_short': 10.0, 'ma_long': 50.0});
      expect(c.fitness, 0.0);
      expect(c['ma_short'], 10.0);
    });

    test('operator [] returns 0 for missing gene', () {
      final c = Chromosome(genes: {'ma_short': 10.0});
      expect(c['nonexistent'], 0.0);
    });

    test('copyWith updates fitness', () {
      final c = Chromosome(genes: {'ma_short': 10.0}, fitness: 1.0);
      final updated = c.copyWith(fitness: 5.0);
      expect(updated.fitness, 5.0);
      expect(updated['ma_short'], 10.0);
    });

    test('copyWith creates independent gene copy', () {
      final c = Chromosome(genes: {'a': 1.0});
      final updated = c.copyWith(genes: {'a': 2.0});
      expect(c['a'], 1.0);
      expect(updated['a'], 2.0);
    });
  });
}
