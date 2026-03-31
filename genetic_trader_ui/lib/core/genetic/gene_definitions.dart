/// Type of a gene value.
enum GeneType { integer, real }

/// Range and type information for a single gene.
class GeneRange {
  final double min;
  final double max;
  final GeneType type;

  const GeneRange(this.min, this.max, this.type);

  /// Clamp a value to this range, rounding if integer type.
  double clamp(double value) {
    var clamped = value.clamp(min, max);
    if (type == GeneType.integer) {
      clamped = clamped.roundToDouble();
    }
    return clamped;
  }
}

/// All 93 gene definitions — exact match to Python config.py GENE_DEFINITIONS.
/// Grouped by feature set to mirror the Python implementation.
class GeneDefinitions {
  GeneDefinitions._();

  static const Map<String, GeneRange> defaultGenes = {
    // ── Core MA Strategy (6) ──────────────────────────────────────────────
    'ma_short_period':       GeneRange(5,    30,   GeneType.integer),
    'ma_long_period':        GeneRange(30,   100,  GeneType.integer),
    'ma_type':               GeneRange(0,    1,    GeneType.integer),
    'stop_loss_pct':         GeneRange(1.0,  10.0, GeneType.real),
    'take_profit_pct':       GeneRange(2.0,  15.0, GeneType.real),
    'position_size_pct':     GeneRange(5.0,  25.0, GeneType.real),

    // ── Macroeconomic Context (15) ────────────────────────────────────────
    'macro_enabled':             GeneRange(0,    1,    GeneType.integer),
    'macro_weight':              GeneRange(0.0,  1.0,  GeneType.real),
    'macro_vix_threshold':       GeneRange(15.0, 50.0, GeneType.real),
    'macro_vix_position_scale':  GeneRange(0.2,  1.0,  GeneType.real),
    'macro_yc_threshold':        GeneRange(-1.0, 1.0,  GeneType.real),
    'macro_yc_action':           GeneRange(0,    2,    GeneType.integer),
    'macro_rate_threshold':      GeneRange(1.0,  8.0,  GeneType.real),
    'macro_rate_position_scale': GeneRange(0.3,  1.0,  GeneType.real),
    'macro_cpi_threshold':       GeneRange(2.0,  8.0,  GeneType.real),
    'macro_cpi_position_scale':  GeneRange(0.3,  1.0,  GeneType.real),
    'macro_unemp_threshold':     GeneRange(4.0,  10.0, GeneType.real),
    'macro_unemp_action':        GeneRange(0,    2,    GeneType.integer),
    'macro_risk_stop_adj':       GeneRange(0.5,  2.0,  GeneType.real),
    'macro_risk_tp_adj':         GeneRange(0.5,  2.0,  GeneType.real),
    'macro_regime_count_req':    GeneRange(1,    4,    GeneType.integer),

    // ── Technical Indicator Filters (12) ─────────────────────────────────
    'ti_enabled':              GeneRange(0,    1,    GeneType.integer),
    'ti_weight':               GeneRange(0.0,  1.0,  GeneType.real),
    'ti_rsi_overbought':       GeneRange(60,   90,   GeneType.integer),
    'ti_rsi_oversold':         GeneRange(10,   40,   GeneType.integer),
    'ti_adx_threshold':        GeneRange(15,   40,   GeneType.integer),
    'ti_adx_position_scale':   GeneRange(0.2,  1.0,  GeneType.real),
    'ti_natr_threshold':       GeneRange(2.0,  8.0,  GeneType.real),
    'ti_natr_risk_action':     GeneRange(0,    2,    GeneType.integer),
    'ti_mfi_overbought':       GeneRange(70,   95,   GeneType.integer),
    'ti_mfi_oversold':         GeneRange(5,    30,   GeneType.integer),
    'ti_macdhist_confirm':     GeneRange(0,    1,    GeneType.integer),
    'ti_macdhist_exit_confirm':GeneRange(0,    1,    GeneType.integer),

    // ── Ensemble Signals (13) ─────────────────────────────────────────────
    'ensemble_enabled':  GeneRange(0,    1,    GeneType.integer),
    'sig_ma_weight':     GeneRange(0.0,  1.0,  GeneType.real),
    'sig_bb_weight':     GeneRange(0.0,  1.0,  GeneType.real),
    'sig_stoch_weight':  GeneRange(0.0,  1.0,  GeneType.real),
    'sig_macd_weight':   GeneRange(0.0,  1.0,  GeneType.real),
    'sig_rsi_weight':    GeneRange(0.0,  1.0,  GeneType.real),
    'sig_buy_threshold': GeneRange(0.1,  0.8,  GeneType.real),
    'sig_sell_threshold':GeneRange(-0.8, -0.1, GeneType.real),
    'sig_bb_period_idx': GeneRange(0,    2,    GeneType.integer),
    'sig_stoch_ob':      GeneRange(70,   90,   GeneType.integer),
    'sig_stoch_os':      GeneRange(10,   30,   GeneType.integer),
    'sig_rsi_ob':        GeneRange(60,   85,   GeneType.integer),
    'sig_rsi_os':        GeneRange(15,   40,   GeneType.integer),

    // ── Advanced Oscillators (13) ─────────────────────────────────────────
    'adv_osc_enabled':      GeneRange(0,     1,    GeneType.integer),
    'wr_oversold':          GeneRange(-90.0, -60.0,GeneType.real),
    'wr_overbought':        GeneRange(-40.0, -10.0,GeneType.real),
    'cci_oversold':         GeneRange(-150.0,-80.0, GeneType.real),
    'cci_overbought':       GeneRange(80.0,  150.0, GeneType.real),
    'cmo_threshold':        GeneRange(10.0,  50.0,  GeneType.real),
    'ao_zero_cross_confirm':GeneRange(0,     1,     GeneType.integer),
    'stochrsi_ob':          GeneRange(75.0,  95.0,  GeneType.real),
    'stochrsi_os':          GeneRange(5.0,   25.0,  GeneType.real),
    'uo_overbought':        GeneRange(60.0,  80.0,  GeneType.real),
    'uo_oversold':          GeneRange(20.0,  40.0,  GeneType.real),
    'roc_period':           GeneRange(5,     20,    GeneType.integer),
    'roc_threshold':        GeneRange(-5.0,  5.0,   GeneType.real),

    // ── Trend Signals (7) ─────────────────────────────────────────────────
    'trend_sig_enabled':        GeneRange(0,    1,   GeneType.integer),
    'psar_filter_enabled':      GeneRange(0,    1,   GeneType.integer),
    'supertrend_filter_enabled':GeneRange(0,    1,   GeneType.integer),
    'ichimoku_cloud_filter':    GeneRange(0,    1,   GeneType.integer),
    'linreg_slope_min':         GeneRange(-2.0, 2.0, GeneType.real),
    'linreg_r2_min':            GeneRange(0.0,  0.9, GeneType.real),
    'trix_zero_confirm':        GeneRange(0,    1,   GeneType.integer),

    // ── Volume Signals (8) ────────────────────────────────────────────────
    'vol_sig_enabled':   GeneRange(0,   1,   GeneType.integer),
    'obv_trend_confirm': GeneRange(0,   1,   GeneType.integer),
    'chaikin_threshold': GeneRange(0.0, 1.0, GeneType.real),
    'force_index_confirm':GeneRange(0,  1,   GeneType.integer),
    'vwap_filter_mode':  GeneRange(0,   2,   GeneType.integer),
    'vwma_vs_sma_confirm':GeneRange(0,  1,   GeneType.integer),
    'klinger_confirm':   GeneRange(0,   1,   GeneType.integer),
    'nvi_trend_confirm': GeneRange(0,   1,   GeneType.integer),

    // ── Volatility & Breakout (6) ─────────────────────────────────────────
    'vb_enabled':                GeneRange(0,   1,   GeneType.integer),
    'donchian_breakout_confirm': GeneRange(0,   1,   GeneType.integer),
    'keltner_filter_enabled':    GeneRange(0,   1,   GeneType.integer),
    'bb_pct_b_threshold':        GeneRange(0.0, 0.5, GeneType.real),
    'bb_squeeze_threshold':      GeneRange(2.0, 8.0, GeneType.real),
    'ulcer_max':                 GeneRange(2.0, 15.0,GeneType.real),

    // ── Support & Resistance (5) ──────────────────────────────────────────
    'sr_enabled':          GeneRange(0,   1,    GeneType.integer),
    'pivot_filter_enabled':GeneRange(0,   1,    GeneType.integer),
    'pivot_proximity_pct': GeneRange(0.5, 5.0,  GeneType.real),
    'fib_filter_enabled':  GeneRange(0,   1,    GeneType.integer),
    'fib_level_pct':       GeneRange(1.0, 10.0, GeneType.real),

    // ── Market Regime Detection (4) ───────────────────────────────────────
    'regime_enabled':          GeneRange(0,  1,  GeneType.integer),
    'regime_window':           GeneRange(10, 60, GeneType.integer),
    'regime_sma200_filter':    GeneRange(0,  1,  GeneType.integer),
    'regime_trend_req_count':  GeneRange(1,  3,  GeneType.integer),

    // ── Advanced Position Sizing (4) ─────────────────────────────────────
    'sizing_model':    GeneRange(0,   3,   GeneType.integer),
    'kelly_fraction':  GeneRange(0.1, 1.0, GeneType.real),
    'atr_stop_multiple':GeneRange(1.0,4.0, GeneType.real),
    'fixed_risk_pct':  GeneRange(0.5, 3.0, GeneType.real),
  };

  /// Total gene count (should be 93).
  static int get count => defaultGenes.length;

  /// Gene names grouped by feature set, matching Python GENE_ORDER.
  static const List<String> geneOrder = [
    // Core
    'ma_short_period', 'ma_long_period', 'ma_type',
    'stop_loss_pct', 'take_profit_pct', 'position_size_pct',
    // Macro
    'macro_enabled', 'macro_weight', 'macro_vix_threshold',
    'macro_vix_position_scale', 'macro_yc_threshold', 'macro_yc_action',
    'macro_rate_threshold', 'macro_rate_position_scale',
    'macro_cpi_threshold', 'macro_cpi_position_scale',
    'macro_unemp_threshold', 'macro_unemp_action',
    'macro_risk_stop_adj', 'macro_risk_tp_adj', 'macro_regime_count_req',
    // Technical indicators
    'ti_enabled', 'ti_weight', 'ti_rsi_overbought', 'ti_rsi_oversold',
    'ti_adx_threshold', 'ti_adx_position_scale', 'ti_natr_threshold',
    'ti_natr_risk_action', 'ti_mfi_overbought', 'ti_mfi_oversold',
    'ti_macdhist_confirm', 'ti_macdhist_exit_confirm',
    // Ensemble
    'ensemble_enabled', 'sig_ma_weight', 'sig_bb_weight', 'sig_stoch_weight',
    'sig_macd_weight', 'sig_rsi_weight', 'sig_buy_threshold',
    'sig_sell_threshold', 'sig_bb_period_idx', 'sig_stoch_ob', 'sig_stoch_os',
    'sig_rsi_ob', 'sig_rsi_os',
    // Advanced oscillators
    'adv_osc_enabled', 'wr_oversold', 'wr_overbought', 'cci_oversold',
    'cci_overbought', 'cmo_threshold', 'ao_zero_cross_confirm',
    'stochrsi_ob', 'stochrsi_os', 'uo_overbought', 'uo_oversold',
    'roc_period', 'roc_threshold',
    // Trend signals
    'trend_sig_enabled', 'psar_filter_enabled', 'supertrend_filter_enabled',
    'ichimoku_cloud_filter', 'linreg_slope_min', 'linreg_r2_min',
    'trix_zero_confirm',
    // Volume signals
    'vol_sig_enabled', 'obv_trend_confirm', 'chaikin_threshold',
    'force_index_confirm', 'vwap_filter_mode', 'vwma_vs_sma_confirm',
    'klinger_confirm', 'nvi_trend_confirm',
    // Volatility & breakout
    'vb_enabled', 'donchian_breakout_confirm', 'keltner_filter_enabled',
    'bb_pct_b_threshold', 'bb_squeeze_threshold', 'ulcer_max',
    // Support & resistance
    'sr_enabled', 'pivot_filter_enabled', 'pivot_proximity_pct',
    'fib_filter_enabled', 'fib_level_pct',
    // Regime detection
    'regime_enabled', 'regime_window', 'regime_sma200_filter',
    'regime_trend_req_count',
    // Advanced sizing
    'sizing_model', 'kelly_fraction', 'atr_stop_multiple', 'fixed_risk_pct',
  ];
}
