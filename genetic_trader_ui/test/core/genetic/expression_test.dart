import 'package:flutter_test/flutter_test.dart';
import 'package:genetic_trader_ui/core/models/chromosome.dart';
import 'package:genetic_trader_ui/core/genetic/operators.dart';
import 'package:genetic_trader_ui/core/genetic/gene_definitions.dart';
import 'package:genetic_trader_ui/core/genetic/gene_groups.dart';
import 'package:genetic_trader_ui/core/genetic/expression_analytics.dart';

void main() {
  group('Chromosome.effectiveValue', () {
    test('returns neutral when gene is silenced', () {
      final c = Chromosome(
        genes: {'stop_loss_pct': 8.0},
        expression: {'stop_loss_pct': 0.01},
      );
      expect(c.effectiveValue('stop_loss_pct', neutral: 5.0), 5.0);
    });

    test('returns raw value when fully active', () {
      final c = Chromosome(
        genes: {'stop_loss_pct': 8.0},
        expression: {'stop_loss_pct': 1.0},
      );
      expect(
        c.effectiveValue('stop_loss_pct', neutral: 5.0),
        8.0,
      );
    });

    test('interpolates at mid-weight', () {
      final c = Chromosome(
        genes: {'stop_loss_pct': 10.0},
        expression: {'stop_loss_pct': 0.5},
      );
      // 10.0 * 0.5 + 0.0 * 0.5 = 5.0
      expect(
        c.effectiveValue('stop_loss_pct', neutral: 0.0),
        closeTo(5.0, 0.01),
      );
    });

    test('defaults to 1.0 expression when not specified', () {
      final c = Chromosome(
        genes: {'stop_loss_pct': 8.0},
      );
      expect(
        c.effectiveValue('stop_loss_pct', neutral: 5.0),
        8.0,
      );
    });
  });

  group('expressionMutate', () {
    test('never silences core group', () {
      // Run mutation many times; core genes should always
      // stay >= 1.0.
      final coreGenes = GeneGroups.groups[GeneGroups.core]!;
      final genes = <String, double>{};
      final expr = <String, double>{};
      for (final g in GeneDefinitions.defaultGenes.keys) {
        genes[g] = 0.5;
        expr[g] = 1.0;
      }

      final c = Chromosome(
        genes: genes,
        expression: expr,
      );

      for (var i = 0; i < 100; i++) {
        final mutated = GeneticOperators.expressionMutate(
          c,
          1.0, // max rate
          seed: i,
        );
        for (final core in coreGenes) {
          expect(
            mutated.expression[core],
            equals(1.0),
            reason: 'Core gene $core was modified at seed $i',
          );
        }
      }
    });

    test('type B correctly silences all genes in a group', () {
      // Set all groups active, then run many type B mutations.
      // At least one should produce a silenced optional group.
      final genes = <String, double>{};
      final expr = <String, double>{};
      for (final g in GeneDefinitions.defaultGenes.keys) {
        genes[g] = 0.5;
        expr[g] = 1.0;
      }

      var foundSilenced = false;
      for (var i = 0; i < 200; i++) {
        final c = Chromosome(genes: genes, expression: expr);
        final mutated = GeneticOperators.expressionMutate(
          c,
          1.0,
          seed: i,
        );

        // Check if any optional group was fully silenced.
        for (final group in GeneGroups.optionalGroups) {
          final groupGenes = GeneGroups.groups[group]!;
          final allLow = groupGenes.every(
            (g) => (mutated.expression[g] ?? 1.0) < 0.15,
          );
          if (allLow) {
            foundSilenced = true;
            break;
          }
        }
        if (foundSilenced) break;
      }
      expect(foundSilenced, isTrue,
          reason: 'Expected at least one group-level '
              'silencing in 200 attempts');
    });

    test('type B correctly activates all genes in a group', () {
      // Set all optional groups silenced, then look for
      // activation.
      final genes = <String, double>{};
      final expr = <String, double>{};
      for (final g in GeneDefinitions.defaultGenes.keys) {
        genes[g] = 0.5;
        final group = GeneGroups.geneToGroup[g];
        expr[g] = group == GeneGroups.core ? 1.0 : 0.02;
      }

      var foundActivated = false;
      for (var i = 0; i < 200; i++) {
        final c = Chromosome(genes: genes, expression: expr);
        final mutated = GeneticOperators.expressionMutate(
          c,
          1.0,
          seed: i,
        );

        for (final group in GeneGroups.optionalGroups) {
          final groupGenes = GeneGroups.groups[group]!;
          final allHigh = groupGenes.every(
            (g) => (mutated.expression[g] ?? 0.0) > 0.65,
          );
          if (allHigh) {
            foundActivated = true;
            break;
          }
        }
        if (foundActivated) break;
      }
      expect(foundActivated, isTrue,
          reason: 'Expected at least one group-level '
              'activation in 200 attempts');
    });
  });

  group('uniformCrossover with expression', () {
    test('inherits expression from one parent or the other', () {
      final genes = {'a': 1.0, 'b': 2.0, 'c': 3.0};
      final parentA = Chromosome(
        genes: genes,
        expression: {'a': 0.1, 'b': 0.2, 'c': 0.3},
      );
      final parentB = Chromosome(
        genes: genes,
        expression: {'a': 0.9, 'b': 0.8, 'c': 0.7},
      );

      final (child1, child2) = GeneticOperators.uniformCrossover(
        parentA,
        parentB,
      );

      // Each child expression should come from one parent.
      for (final gene in genes.keys) {
        final e1 = child1.expression[gene]!;
        final e2 = child2.expression[gene]!;
        expect(
          e1 == parentA.expression[gene] ||
              e1 == parentB.expression[gene],
          isTrue,
          reason: 'Child1 expression for $gene ($e1) '
              'should come from a parent',
        );
        expect(
          e2 == parentA.expression[gene] ||
              e2 == parentB.expression[gene],
          isTrue,
          reason: 'Child2 expression for $gene ($e2) '
              'should come from a parent',
        );
      }
    });
  });

  group('initPopulation', () {
    test('never starts with all groups silenced', () {
      final pop = GeneticOperators.initPopulation(
        20,
        GeneDefinitions.defaultGenes,
        seed: 42,
      );

      for (var i = 0; i < pop.length; i++) {
        final c = pop[i];
        // Count active groups (avg expression > 0.5).
        var activeGroups = 0;
        for (final group in GeneGroups.allGroups) {
          final groupGenes = GeneGroups.groups[group]!;
          var sum = 0.0;
          var count = 0;
          for (final g in groupGenes) {
            if (c.genes.containsKey(g)) {
              sum += c.expression[g] ?? 1.0;
              count++;
            }
          }
          if (count > 0 && sum / count > 0.5) {
            activeGroups++;
          }
        }
        // At least core + 2 optional = 3 groups.
        expect(
          activeGroups,
          greaterThanOrEqualTo(3),
          reason: 'Chromosome $i has only $activeGroups '
              'active groups',
        );
      }
    });

    test('core genes always have expression 1.0', () {
      final pop = GeneticOperators.initPopulation(
        10,
        GeneDefinitions.defaultGenes,
        seed: 7,
      );

      final coreGenes = GeneGroups.groups[GeneGroups.core]!;
      for (final c in pop) {
        for (final gene in coreGenes) {
          expect(c.expression[gene], equals(1.0));
        }
      }
    });
  });

  group('ExpressionAnalytics', () {
    test('groupActivityRates returns values in [0, 1]', () {
      final pop = GeneticOperators.initPopulation(
        20,
        GeneDefinitions.defaultGenes,
        seed: 99,
      );

      final rates = ExpressionAnalytics.groupActivityRates(pop);
      expect(rates.isNotEmpty, isTrue);
      for (final entry in rates.entries) {
        expect(
          entry.value,
          inInclusiveRange(0.0, 1.0),
          reason: '${entry.key} rate should be in [0, 1]',
        );
      }

      // Core should always be 1.0 (100% active).
      expect(rates[GeneGroups.core], equals(1.0));
    });

    test('expressionDiversity returns positive for diverse pop',
        () {
      final pop = GeneticOperators.initPopulation(
        20,
        GeneDefinitions.defaultGenes,
        seed: 123,
      );

      final diversity = ExpressionAnalytics.expressionDiversity(pop);
      expect(diversity, greaterThan(0.0));
    });

    test('expressionDiversity returns 0 for single chromosome', () {
      final pop = GeneticOperators.initPopulation(
        1,
        GeneDefinitions.defaultGenes,
        seed: 1,
      );

      final diversity = ExpressionAnalytics.expressionDiversity(pop);
      expect(diversity, equals(0.0));
    });
  });
}
