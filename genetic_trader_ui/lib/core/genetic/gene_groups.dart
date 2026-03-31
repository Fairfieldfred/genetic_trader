/// Functional groupings of the 93 genes for expression control.
class GeneGroups {
  GeneGroups._();

  // Group name constants.
  static const String core = 'core';
  static const String macro = 'macro';
  static const String technicalIndicators = 'technical_indicators';
  static const String ensemble = 'ensemble';
  static const String advancedOscillators = 'advanced_oscillators';
  static const String trendSignals = 'trend_signals';
  static const String volumeSignals = 'volume_signals';
  static const String volatilityBreakout = 'volatility_breakout';
  static const String supportResistance = 'support_resistance';
  static const String regimeDetection = 'regime_detection';
  static const String advancedSizing = 'advanced_sizing';

  /// All gene names belonging to each named group.
  static const Map<String, List<String>> groups = {
    core: [
      'ma_short_period',
      'ma_long_period',
      'ma_type',
      'stop_loss_pct',
      'take_profit_pct',
      'position_size_pct',
    ],
    macro: [
      'macro_enabled',
      'macro_weight',
      'macro_vix_threshold',
      'macro_vix_position_scale',
      'macro_yc_threshold',
      'macro_yc_action',
      'macro_rate_threshold',
      'macro_rate_position_scale',
      'macro_cpi_threshold',
      'macro_cpi_position_scale',
      'macro_unemp_threshold',
      'macro_unemp_action',
      'macro_risk_stop_adj',
      'macro_risk_tp_adj',
      'macro_regime_count_req',
    ],
    technicalIndicators: [
      'ti_enabled',
      'ti_weight',
      'ti_rsi_overbought',
      'ti_rsi_oversold',
      'ti_adx_threshold',
      'ti_adx_position_scale',
      'ti_natr_threshold',
      'ti_natr_risk_action',
      'ti_mfi_overbought',
      'ti_mfi_oversold',
      'ti_macdhist_confirm',
      'ti_macdhist_exit_confirm',
    ],
    ensemble: [
      'ensemble_enabled',
      'sig_ma_weight',
      'sig_bb_weight',
      'sig_stoch_weight',
      'sig_macd_weight',
      'sig_rsi_weight',
      'sig_buy_threshold',
      'sig_sell_threshold',
      'sig_bb_period_idx',
      'sig_stoch_ob',
      'sig_stoch_os',
      'sig_rsi_ob',
      'sig_rsi_os',
    ],
    advancedOscillators: [
      'adv_osc_enabled',
      'wr_oversold',
      'wr_overbought',
      'cci_oversold',
      'cci_overbought',
      'cmo_threshold',
      'ao_zero_cross_confirm',
      'stochrsi_ob',
      'stochrsi_os',
      'uo_overbought',
      'uo_oversold',
      'roc_period',
      'roc_threshold',
    ],
    trendSignals: [
      'trend_sig_enabled',
      'psar_filter_enabled',
      'supertrend_filter_enabled',
      'ichimoku_cloud_filter',
      'linreg_slope_min',
      'linreg_r2_min',
      'trix_zero_confirm',
    ],
    volumeSignals: [
      'vol_sig_enabled',
      'obv_trend_confirm',
      'chaikin_threshold',
      'force_index_confirm',
      'vwap_filter_mode',
      'vwma_vs_sma_confirm',
      'klinger_confirm',
      'nvi_trend_confirm',
    ],
    volatilityBreakout: [
      'vb_enabled',
      'donchian_breakout_confirm',
      'keltner_filter_enabled',
      'bb_pct_b_threshold',
      'bb_squeeze_threshold',
      'ulcer_max',
    ],
    supportResistance: [
      'sr_enabled',
      'pivot_filter_enabled',
      'pivot_proximity_pct',
      'fib_filter_enabled',
      'fib_level_pct',
    ],
    regimeDetection: [
      'regime_enabled',
      'regime_window',
      'regime_sma200_filter',
      'regime_trend_req_count',
    ],
    advancedSizing: [
      'sizing_model',
      'kelly_fraction',
      'atr_stop_multiple',
      'fixed_risk_pct',
    ],
  };

  /// Reverse map: gene name to group name.
  static final Map<String, String> geneToGroup = {
    for (final entry in groups.entries)
      for (final gene in entry.value) gene: entry.key,
  };

  /// All non-core group names (core is always active).
  static const List<String> optionalGroups = [
    macro,
    technicalIndicators,
    ensemble,
    advancedOscillators,
    trendSignals,
    volumeSignals,
    volatilityBreakout,
    supportResistance,
    regimeDetection,
    advancedSizing,
  ];

  /// All group names including core.
  static const List<String> allGroups = [
    core,
    macro,
    technicalIndicators,
    ensemble,
    advancedOscillators,
    trendSignals,
    volumeSignals,
    volatilityBreakout,
    supportResistance,
    regimeDetection,
    advancedSizing,
  ];
}
