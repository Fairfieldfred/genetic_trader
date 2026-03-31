/// Symbol metadata for a stock.
class Stock {
  final String symbol;
  final String? name;
  final String? sector;
  final List<String> indexMembership;

  const Stock({
    required this.symbol,
    this.name,
    this.sector,
    this.indexMembership = const [],
  });

  Stock copyWith({
    String? symbol,
    String? name,
    String? sector,
    List<String>? indexMembership,
  }) {
    return Stock(
      symbol: symbol ?? this.symbol,
      name: name ?? this.name,
      sector: sector ?? this.sector,
      indexMembership: indexMembership ?? this.indexMembership,
    );
  }
}
