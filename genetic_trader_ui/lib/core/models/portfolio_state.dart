/// Cash + positions snapshot at a point in time.
class PortfolioState {
  final double cash;
  final Map<String, PositionInfo> positions;

  const PortfolioState({
    required this.cash,
    this.positions = const {},
  });

  /// Computes total portfolio value given current prices per symbol.
  double totalValue(Map<String, double> currentPrices) {
    var value = cash;
    for (final entry in positions.entries) {
      final price = currentPrices[entry.key] ?? 0.0;
      value += entry.value.shares * price;
    }
    return value;
  }

  PortfolioState copyWith({
    double? cash,
    Map<String, PositionInfo>? positions,
  }) {
    return PortfolioState(
      cash: cash ?? this.cash,
      positions: positions ?? this.positions,
    );
  }
}

/// Shares held and average cost basis for a single position.
class PositionInfo {
  final double shares;
  final double avgPrice;

  const PositionInfo({
    required this.shares,
    required this.avgPrice,
  });
}
