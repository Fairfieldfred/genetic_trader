def calculate_fitness(performance_stats):
    # Multi-objective fitness
    fitness = (
        performance_stats['total_return'] * 0.3 +
        performance_stats['sharpe_ratio'] * 0.2 +
        (1 / (1 + performance_stats['max_drawdown'])) * 0.2 +
        performance_stats['profit_factor'] * 0.15 +
        performance_stats['win_rate'] * 0.15
    )
    
    # Penalties
    if performance_stats['num_trades'] < 10:
        fitness *= 0.5  # Penalize insufficient trades
    if performance_stats['max_drawdown'] > 0.3:
        fitness *= 0.7  # Penalize excessive drawdown
        
    return fitness