import 'dart:math';
import 'package:test/test.dart';
import 'package:genetic_trader_ui/core/genetic/operators.dart';
import 'package:genetic_trader_ui/core/genetic/gene_definitions.dart';
import 'package:genetic_trader_ui/core/models/chromosome.dart';

void main() {
  group('GeneticOperators', () {
    final genes = GeneDefinitions.defaultGenes;

    group('initPopulation', () {
      test('creates correct population size', () {
        final pop =
            GeneticOperators.initPopulation(10, genes, seed: 42);
        expect(pop.length, 10);
      });

      test('all genes within range', () {
        final pop =
            GeneticOperators.initPopulation(20, genes, seed: 42);
        for (final c in pop) {
          for (final entry in genes.entries) {
            final value = c[entry.key];
            expect(value, greaterThanOrEqualTo(entry.value.min),
                reason: '${entry.key} below min');
            expect(value, lessThanOrEqualTo(entry.value.max),
                reason: '${entry.key} above max');
          }
        }
      });

      test('integer genes are whole numbers', () {
        final pop =
            GeneticOperators.initPopulation(20, genes, seed: 42);
        for (final c in pop) {
          for (final entry in genes.entries) {
            if (entry.value.type == GeneType.integer) {
              expect(c[entry.key] % 1.0, 0.0,
                  reason: '${entry.key} is not integer');
            }
          }
        }
      });
    });

    group('tournamentSelect', () {
      test('returns fittest from tournament', () {
        final pop = [
          Chromosome(genes: {'a': 1.0}, fitness: 1.0),
          Chromosome(genes: {'a': 2.0}, fitness: 5.0),
          Chromosome(genes: {'a': 3.0}, fitness: 3.0),
        ];
        // With k=3 and only 3 individuals, always returns the
        // best.
        final selected = GeneticOperators.tournamentSelect(
          pop,
          3,
          rng: Random(42),
        );
        expect(selected.fitness, 5.0);
      });
    });

    group('uniformCrossover', () {
      test('child genes come from parents', () {
        final a = Chromosome(
          genes: {'x': 1.0, 'y': 2.0, 'z': 3.0},
        );
        final b = Chromosome(
          genes: {'x': 10.0, 'y': 20.0, 'z': 30.0},
        );

        final (child1, child2) =
            GeneticOperators.uniformCrossover(
          a,
          b,
          rng: Random(42),
        );

        for (final gene in ['x', 'y', 'z']) {
          expect(
            child1[gene] == a[gene] || child1[gene] == b[gene],
            isTrue,
            reason: '$gene not from parents',
          );
          expect(
            child2[gene] == a[gene] || child2[gene] == b[gene],
            isTrue,
            reason: '$gene not from parents',
          );
        }
      });
    });

    group('gaussianMutate', () {
      test('mutated genes stay within range', () {
        final c = Chromosome(genes: {
          'ma_short_period': 15.0,
          'ma_long_period': 65.0,
          'ma_type': 0.0,
          'stop_loss_pct': 5.0,
          'take_profit_pct': 8.0,
          'position_size_pct': 15.0,
        });

        // Mutate with 100% rate to ensure all genes are mutated.
        final mutated = GeneticOperators.gaussianMutate(
          c,
          genes,
          1.0,
          seed: 42,
        );

        for (final entry in genes.entries) {
          expect(
            mutated[entry.key],
            greaterThanOrEqualTo(entry.value.min),
          );
          expect(
            mutated[entry.key],
            lessThanOrEqualTo(entry.value.max),
          );
        }
      });
    });
  });
}
