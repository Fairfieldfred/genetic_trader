# Hyperparameter Tuning Guide

## Overview

This guide shows you how to optimize both:
1. **Genetic Algorithm Parameters** (population size, mutation rate, etc.)
2. **Fitness Weights** (how much to value returns vs Sharpe vs drawdown)

Finding optimal hyperparameters can significantly improve the quality of evolved trading strategies!

## Why Optimize Hyperparameters?

### Default Configuration (May Not Be Optimal)

```python
# Current defaults
POPULATION_SIZE = 20
MUTATION_RATE = 0.15
CROSSOVER_RATE = 0.7

FITNESS_WEIGHTS = {
    'total_return': 0.4,
    'sharpe_ratio': 0.3,
    'max_drawdown': 0.2,
    'win_rate': 0.1,
}
```

**Question**: Are these the best values for YOUR data and goals?

**Answer**: Maybe not! Optimal parameters depend on:
- Your stock/portfolio
- Your time period
- Your risk tolerance
- Your performance goals

## Two Optimization Tools

### 1. Hyperparameter Optimizer (Complete)

**File**: [hyperparameter_optimizer.py](hyperparameter_optimizer.py)

**Optimizes**:
- Population size
- Mutation rate
- Crossover rate
- Elitism count
- Tournament size
- Fitness weights

**Methods**:
- Grid search (exhaustive, slow)
- Random search (fast, good exploration)

**When to use**: When you want to optimize everything at once

### 2. Fitness Weight Optimizer (Fast)

**File**: [fitness_weight_optimizer.py](fitness_weight_optimizer.py)

**Optimizes**:
- Fitness weights only (4 parameters)

**Methods**:
- Random sampling (Dirichlet distribution)
- Grid search
- Simplex sampling (uniform on constraint)

**When to use**: When you just want to optimize fitness weights (faster!)

## Quick Start

### Option 1: Optimize Fitness Weights (Recommended First)

```bash
python fitness_weight_optimizer.py
```

**What it does**:
- Tests 15 different weight combinations
- Each runs 10 generations
- Takes ~10-15 minutes
- Finds weights that work best for your data

**Output**:
```
BEST FITNESS WEIGHTS
Best Fitness Achieved: 52.34

  Total Return:  0.35 (35%)
  Sharpe Ratio:  0.40 (40%)
  Max Drawdown:  0.15 (15%)
  Win Rate:      0.10 (10%)

COPY TO config.py:
FITNESS_WEIGHTS = {
    'total_return': 0.350,
    'sharpe_ratio': 0.400,
    'max_drawdown': 0.150,
    'win_rate': 0.100,
}
```

### Option 2: Optimize All Hyperparameters

```bash
python hyperparameter_optimizer.py
```

**What it does**:
- Tests 10 random configurations
- Each runs 10 generations
- Takes ~1-2 hours
- Finds optimal GA parameters + fitness weights

**Output**:
```
BEST CONFIGURATION
Best Fitness: 58.23

GA Parameters:
  Population: 25
  Mutation Rate: 0.20
  Crossover Rate: 0.8
  Elitism: 3
  Tournament: 4

Fitness Weights:
  Return: 0.30
  Sharpe: 0.40
  Drawdown: 0.20
  Win Rate: 0.10
```

## Detailed Usage

### Fitness Weight Optimization

#### Basic Usage

```python
from fitness_weight_optimizer import FitnessWeightOptimizer

optimizer = FitnessWeightOptimizer(
    start_date="2019-01-01",
    end_date="2019-12-31"
)

# Test 20 random weight combinations
best_weights = optimizer.optimize(
    n_trials=20,
    generations=15,
    method='random'  # or 'grid' or 'simplex'
)

# See results
optimizer.print_best_weights()
optimizer.analyze_sensitivity()
optimizer.save_results()
```

#### Methods Explained

**1. Random Sampling** (Recommended)
```python
method='random'
```
- Uses Dirichlet distribution
- Samples uniformly from valid weight space
- Fast and effective
- Good for 15-30 trials

**2. Grid Search**
```python
method='grid'
```
- Tests all combinations on grid
- Exhaustive but slow
- Good for fine-tuning
- Use with small step size

**3. Simplex Sampling**
```python
method='simplex'
```
- Uniform sampling on weight simplex
- Mathematical guarantee of coverage
- Good for 20-50 trials

#### Interpreting Results

**Sensitivity Analysis**:
```
Correlation with fitness:
  total_return        : +0.456  ← Strong positive impact
  sharpe_ratio        : +0.234  ← Moderate positive impact
  max_drawdown        : -0.123  ← Slight negative correlation
  win_rate            : +0.089  ← Weak positive impact
```

**What this means**:
- Higher `total_return` weight → Better fitness
- Higher `sharpe_ratio` weight → Better fitness
- `max_drawdown` doesn't matter much
- `win_rate` has minimal impact

**Recommendation**: Increase weights with strong positive correlation!

### Full Hyperparameter Optimization

#### Basic Usage

```python
from hyperparameter_optimizer import HyperparameterOptimizer

optimizer = HyperparameterOptimizer(
    start_date="2019-01-01",
    end_date="2019-12-31",
    search_type='random',  # or 'grid'
    n_trials=20
)

# Run optimization
best_config = optimizer.optimize(generations=15)

# Analyze
optimizer.print_best_config()
df = optimizer.analyze_results()
optimizer.save_results()
```

#### Search Space

Default search space:
```python
{
    'POPULATION_SIZE': [10, 15, 20, 30],
    'MUTATION_RATE': [0.05, 0.10, 0.15, 0.20, 0.25],
    'CROSSOVER_RATE': [0.6, 0.7, 0.8, 0.9],
    'ELITISM_COUNT': [1, 2, 3, 4],
    'TOURNAMENT_SIZE': [2, 3, 4, 5],

    'FITNESS_WEIGHT_RETURN': [0.2, 0.3, 0.4, 0.5],
    'FITNESS_WEIGHT_SHARPE': [0.1, 0.2, 0.3, 0.4],
    'FITNESS_WEIGHT_DRAWDOWN': [0.1, 0.2, 0.3],
    'FITNESS_WEIGHT_WINRATE': [0.05, 0.10, 0.15, 0.20],
}
```

**Customize** by editing `define_search_space()` in the optimizer.

#### Analysis Features

**Top Configurations**:
```python
df = optimizer.analyze_results()
# Shows top 5 configurations by fitness
```

**Parameter Importance**:
```python
PARAMETER IMPORTANCE (correlation with fitness)
  MUTATION_RATE          : 0.523  ← Most important!
  FITNESS_WEIGHT_SHARPE  : 0.412
  POPULATION_SIZE        : 0.301
  CROSSOVER_RATE         : 0.156
  ELITISM_COUNT          : 0.089  ← Least important
```

## Performance Considerations

### Execution Time

| Optimizer | Trials | Generations | Time (Single Stock) | Time (Portfolio) |
|-----------|--------|-------------|-------------------|------------------|
| Fitness Weights | 15 | 10 | ~10 min | ~3 hours |
| Fitness Weights | 30 | 15 | ~30 min | ~10 hours |
| Full Hyperparameter | 10 | 10 | ~40 min | ~8 hours |
| Full Hyperparameter | 30 | 15 | ~3 hours | ~2 days |

**Tip**: Use parallel evaluation (`USE_PARALLEL_EVALUATION = True`) for 8x speedup!

### Cost vs Benefit

```
Fitness Weight Optimization:
  Cost: 10-30 minutes
  Benefit: 10-30% fitness improvement
  ROI: ⭐⭐⭐⭐⭐ Excellent

Full Hyperparameter Optimization:
  Cost: 1-2 hours
  Benefit: 20-50% fitness improvement
  ROI: ⭐⭐⭐⭐ Very Good
```

**Recommendation**: Start with fitness weight optimization!

## Strategies

### Strategy 1: Quick Fitness Weight Tune (30 minutes)

```python
# 1. Fast test on short period
optimizer = FitnessWeightOptimizer(
    start_date="2019-01-01",
    end_date="2019-12-31"
)

best_weights = optimizer.optimize(
    n_trials=20,
    generations=10,
    method='random'
)

# 2. Apply to config.py
# 3. Run full evolution
```

### Strategy 2: Thorough Hyperparameter Search (2 hours)

```python
# 1. Random search for broad exploration
optimizer = HyperparameterOptimizer(
    start_date="2019-01-01",
    end_date="2020-12-31",
    search_type='random',
    n_trials=25
)

best_config = optimizer.optimize(generations=15)

# 2. Apply best config to config.py
# 3. Run full evolution
```

### Strategy 3: Two-Stage Optimization (3 hours)

```python
# Stage 1: Optimize fitness weights (fast)
fw_optimizer = FitnessWeightOptimizer()
best_weights = fw_optimizer.optimize(n_trials=30, generations=15)

# Stage 2: Optimize GA parameters with best weights
# (manually update config.FITNESS_WEIGHTS first)
hp_optimizer = HyperparameterOptimizer(search_type='random', n_trials=20)
best_config = hp_optimizer.optimize(generations=15)
```

## Best Practices

### 1. Use Shorter Training Periods

```python
# Instead of:
start_date="2012-01-01"  # 9 years
end_date="2020-12-31"

# Use:
start_date="2018-01-01"  # 2 years (faster!)
end_date="2019-12-31"
```

**Why**: Hyperparameter sensitivity is often stable across time periods

### 2. Start with Fewer Generations

```python
# Instead of:
generations=50  # Full evolution

# Use:
generations=10-15  # Enough to see trends
```

**Why**: Relative fitness differences appear early

### 3. Validate on Different Period

```python
# Optimize on:
start_date="2018-01-01"
end_date="2019-12-31"

# Then validate on:
start_date="2020-01-01"
end_date="2021-12-31"
```

**Why**: Ensures parameters generalize

### 4. Use Portfolio Mode

```python
USE_PORTFOLIO = True
```

**Why**: More robust optimization (averages over multiple stocks)

### 5. Parallelize Everything

```python
USE_PARALLEL_EVALUATION = True
```

**Why**: 8x speedup makes optimization practical

## Common Questions

### Q: How many trials should I run?

**A**: Depends on search space size:

- **Fitness weights only**: 20-30 trials (4 parameters)
- **Full hyperparameters**: 30-50 trials (9 parameters)
- **Quick test**: 10 trials
- **Thorough search**: 50+ trials

### Q: Grid search vs random search?

**A**:
- **Grid search**: Good for small spaces, exhaustive
- **Random search**: Better for large spaces, faster

**Recommendation**: Start with random search

### Q: How do I know if results are good?

**A**: Compare best fitness to current config:

```
Current config: Fitness = 45.2
Optimized:      Fitness = 58.7

Improvement: +30% 🎯
```

### Q: Can I optimize for specific goals?

**A**: Yes! Adjust fitness weight search space:

```python
# For maximum returns (aggressive)
'FITNESS_WEIGHT_RETURN': [0.5, 0.6, 0.7, 0.8]
'FITNESS_WEIGHT_SHARPE': [0.1, 0.15, 0.2]

# For risk-adjusted returns (conservative)
'FITNESS_WEIGHT_RETURN': [0.2, 0.3]
'FITNESS_WEIGHT_SHARPE': [0.4, 0.5, 0.6]
'FITNESS_WEIGHT_DRAWDOWN': [0.2, 0.3]
```

### Q: Should I optimize every time?

**A**: No! Optimize when:
- Starting a new dataset
- Changing goals (returns vs risk)
- Results seem suboptimal
- Every 6-12 months

## Example: Full Workflow

### Step 1: Optimize Fitness Weights (30 min)

```bash
python fitness_weight_optimizer.py
```

Output shows:
```python
FITNESS_WEIGHTS = {
    'total_return': 0.350,
    'sharpe_ratio': 0.400,
    'max_drawdown': 0.150,
    'win_rate': 0.100,
}
```

### Step 2: Update config.py

```python
# Edit config.py
FITNESS_WEIGHTS = {
    'total_return': 0.350,
    'sharpe_ratio': 0.400,
    'max_drawdown': 0.150,
    'win_rate': 0.100,
}
```

### Step 3: Run Full Evolution

```bash
python evolve.py
```

### Step 4: Compare Results

```
Before optimization:
  Best Fitness: 45.2
  Total Return: 68%
  Sharpe Ratio: 0.95

After optimization:
  Best Fitness: 58.7  (+30%)
  Total Return: 89%  (+31%)
  Sharpe Ratio: 1.24 (+31%)
```

### Step 5: Validate

Run on different time period:
```python
TEST_START_DATE = "2021-01-01"
TEST_END_DATE = "2023-12-31"
```

If results hold → Good configuration! ✅

## Advanced: Custom Optimization

### Define Your Own Search Space

```python
class MyOptimizer(HyperparameterOptimizer):
    def define_search_space(self):
        return {
            # Focus on mutation rate (most important)
            'MUTATION_RATE': [0.10, 0.12, 0.15, 0.18, 0.20, 0.22, 0.25],

            # Keep others fixed
            'POPULATION_SIZE': [20],
            'CROSSOVER_RATE': [0.7],

            # Optimize weights
            'FITNESS_WEIGHT_RETURN': [0.3, 0.4, 0.5],
            'FITNESS_WEIGHT_SHARPE': [0.2, 0.3, 0.4],
            'FITNESS_WEIGHT_DRAWDOWN': [0.1, 0.2],
            'FITNESS_WEIGHT_WINRATE': [0.1],
        }
```

### Multi-Objective Optimization

```python
# Optimize for returns AND Sharpe simultaneously
# (not implemented yet, but possible with NSGA-II)
```

## Troubleshooting

### Issue: All trials give similar fitness

**Cause**: Parameter ranges too narrow

**Solution**: Widen search space:
```python
'MUTATION_RATE': [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]  # Wider!
```

### Issue: Optimization takes too long

**Solutions**:
1. Reduce trials: `n_trials=10`
2. Reduce generations: `generations=10`
3. Shorter data period: `start_date="2019-01-01"`
4. Enable parallel: `USE_PARALLEL_EVALUATION=True`

### Issue: Results don't generalize

**Cause**: Overfitting to specific time period

**Solution**: Use longer, more diverse training period

## Summary

### Quick Reference

| Task | Tool | Time | Command |
|------|------|------|---------|
| Optimize fitness weights | fitness_weight_optimizer.py | 30 min | `python fitness_weight_optimizer.py` |
| Optimize all parameters | hyperparameter_optimizer.py | 2 hours | `python hyperparameter_optimizer.py` |

### Key Takeaways

✅ **Start with fitness weight optimization** (fastest, good ROI)
✅ **Use random search** (better than grid for high dimensions)
✅ **Use shorter periods** for optimization (results generalize)
✅ **Validate on different period** (ensure robustness)
✅ **Enable parallel evaluation** (8x faster)
✅ **Optimize when starting new dataset** or changing goals

---

**Ready to find your optimal configuration?**

```bash
python fitness_weight_optimizer.py
```

Let the meta-optimization begin! 🎯🔧
