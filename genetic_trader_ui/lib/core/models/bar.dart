/// OHLCV price bar for a single symbol and date.
class Bar {
  final String symbol;
  final DateTime date;
  final double open;
  final double high;
  final double low;
  final double close;
  final int volume;
  final double? adjClose;

  const Bar({
    required this.symbol,
    required this.date,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    required this.volume,
    this.adjClose,
  });

  Bar copyWith({
    String? symbol,
    DateTime? date,
    double? open,
    double? high,
    double? low,
    double? close,
    int? volume,
    double? adjClose,
  }) {
    return Bar(
      symbol: symbol ?? this.symbol,
      date: date ?? this.date,
      open: open ?? this.open,
      high: high ?? this.high,
      low: low ?? this.low,
      close: close ?? this.close,
      volume: volume ?? this.volume,
      adjClose: adjClose ?? this.adjClose,
    );
  }

  @override
  String toString() =>
      'Bar($symbol, $date, O:$open H:$high L:$low C:$close V:$volume)';
}
