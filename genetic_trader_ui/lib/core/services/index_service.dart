/// Supported stock market indices.
enum IndexType { djia, sp500, nasdaq100 }

/// Provides static access to index constituent ticker lists.
class IndexService {
  IndexService._();

  /// Returns the list of ticker symbols for the given [type].
  static List<String> getSymbols(IndexType type) {
    return switch (type) {
      IndexType.djia => _djia,
      IndexType.sp500 => _sp500,
      IndexType.nasdaq100 => _nasdaq100,
    };
  }

  /// Returns a human-readable display name including the count.
  static String getDisplayName(IndexType type) {
    return switch (type) {
      IndexType.djia => 'DJIA (${_djia.length})',
      IndexType.sp500 => 'S&P 500 (${_sp500.length})',
      IndexType.nasdaq100 => 'Nasdaq-100 (${_nasdaq100.length})',
    };
  }

  // ── DJIA (30) ──────────────────────────────────────────────

  static const _djia = <String>[
    'AAPL', 'AMGN', 'AXP', 'BA', 'CAT',
    'CRM', 'CSCO', 'CVX', 'DIS', 'DOW',
    'GS', 'HD', 'HON', 'IBM', 'INTC',
    'JNJ', 'JPM', 'KO', 'MCD', 'MMM',
    'MRK', 'MSFT', 'NKE', 'PG', 'TRV',
    'UNH', 'V', 'VZ', 'WBA', 'WMT',
  ];

  // ── Nasdaq-100 (100) ──────────────────────────────────────

  static const _nasdaq100 = <String>[
    'AAPL', 'ABNB', 'ADBE', 'ADI', 'ADP',
    'ADSK', 'AEP', 'AMAT', 'AMD', 'AMGN',
    'AMZN', 'ANSS', 'APP', 'ARM', 'ASML',
    'AVGO', 'AZN', 'BIIB', 'BKNG', 'BKR',
    'CCEP', 'CDNS', 'CDW', 'CEG', 'CHTR',
    'CMCSA', 'COST', 'CPRT', 'CRWD', 'CSGP',
    'CSCO', 'CTAS', 'CTSH', 'DASH', 'DDOG',
    'DLTR', 'DXCM', 'EA', 'EXC', 'FANG',
    'FAST', 'FTNT', 'GILD', 'GFS', 'GOOG',
    'GOOGL', 'HON', 'IDXX', 'ILMN', 'INTC',
    'INTU', 'ISRG', 'KDP', 'KHC', 'KLAC',
    'LIN', 'LRCX', 'LULU', 'MAR', 'MCHP',
    'MDB', 'MDLZ', 'MELI', 'META', 'MNST',
    'MRNA', 'MRVL', 'MSFT', 'MU', 'NFLX',
    'NVDA', 'NXPI', 'ODFL', 'ON', 'ORLY',
    'PANW', 'PAYX', 'PCAR', 'PDD', 'PEP',
    'PYPL', 'QCOM', 'REGN', 'ROST', 'SBUX',
    'SNPS', 'SPLK', 'TEAM', 'TMUS', 'TSLA',
    'TTD', 'TTWO', 'TXN', 'VRSK', 'VRTX',
    'WBD', 'WDAY', 'XEL', 'ZM', 'ZS',
  ];

  // ── S&P 500 (503) ─────────────────────────────────────────

  static const _sp500 = <String>[
    'A', 'AAL', 'AAPL', 'ABBV', 'ABNB',
    'ABT', 'ACGL', 'ACN', 'ADBE', 'ADI',
    'ADM', 'ADP', 'ADSK', 'AEE', 'AEP',
    'AES', 'AFL', 'AIG', 'AIZ', 'AJG',
    'AKAM', 'ALB', 'ALGN', 'ALL', 'ALLE',
    'AMAT', 'AMCR', 'AMD', 'AME', 'AMGN',
    'AMP', 'AMT', 'AMZN', 'ANSS', 'AON',
    'AOS', 'APA', 'APD', 'APH', 'APTV',
    'ARE', 'ATO', 'ATVI', 'AVGO', 'AVY',
    'AWK', 'AXP', 'AZO', 'BA', 'BAC',
    'BAX', 'BBWI', 'BBY', 'BDX', 'BEN',
    'BF.B', 'BG', 'BIIB', 'BIO', 'BK',
    'BKNG', 'BKR', 'BLDR', 'BMY', 'BR',
    'BRK.B', 'BRO', 'BSX', 'BWA', 'BXP',
    'C', 'CAG', 'CAH', 'CARR', 'CAT',
    'CB', 'CBOE', 'CBRE', 'CCI', 'CCL',
    'CDAY', 'CDNS', 'CDW', 'CE', 'CEG',
    'CF', 'CFG', 'CHD', 'CHRW', 'CHTR',
    'CI', 'CINF', 'CL', 'CLX', 'CMA',
    'CMCSA', 'CME', 'CMG', 'CMI', 'CMS',
    'CNC', 'CNP', 'COF', 'COO', 'COP',
    'COR', 'COST', 'CPAY', 'CPB', 'CPRT',
    'CPT', 'CRL', 'CRM', 'CSCO', 'CSGP',
    'CSX', 'CTAS', 'CTLT', 'CTRA', 'CTSH',
    'CTVA', 'CVS', 'CVX', 'CZR', 'D',
    'DAL', 'DAY', 'DD', 'DE', 'DECK',
    'DFS', 'DG', 'DGX', 'DHI', 'DHR',
    'DIS', 'DLTR', 'DOV', 'DOW', 'DPZ',
    'DRI', 'DTE', 'DUK', 'DVA', 'DVN',
    'DXCM', 'EA', 'EBAY', 'ECL', 'ED',
    'EFX', 'EIX', 'EL', 'EMN', 'EMR',
    'ENPH', 'EOG', 'EPAM', 'EQIX', 'EQR',
    'EQT', 'ERIE', 'ES', 'ESS', 'ETN', 'ETR',
    'EVRG', 'EW', 'EXC', 'EXPD', 'EXPE',
    'EXR', 'F', 'FANG', 'FAST', 'FBHS',
    'FCX', 'FDS', 'FDX', 'FE', 'FFIV',
    'FI', 'FICO', 'FIS', 'FISV', 'FITB',
    'FLT', 'FMC', 'FOX', 'FOXA', 'FRT',
    'FSLR', 'FTNT', 'FTV', 'GD', 'GDDY',
    'GE', 'GEHC', 'GEN', 'GEV', 'GILD', 'GIS',
    'GL', 'GLW', 'GM', 'GNRC', 'GOOG',
    'GOOGL', 'GPC', 'GPN', 'GRMN', 'GS',
    'GWW', 'HAL', 'HAS', 'HBAN', 'HCA',
    'HD', 'HOLX', 'HON', 'HPE', 'HPQ',
    'HRL', 'HSIC', 'HST', 'HSY', 'HUBB',
    'HUM', 'HWM', 'IBM', 'ICE', 'IDXX',
    'IEX', 'IFF', 'ILMN', 'INCY', 'INTC',
    'INTU', 'INVH', 'IP', 'IPG', 'IQV',
    'IR', 'IRM', 'ISRG', 'IT', 'ITW',
    'IVZ', 'J', 'JBHT', 'JCI', 'JKHY',
    'JNJ', 'JNPR', 'JPM', 'K', 'KDP',
    'KEY', 'KEYS', 'KHC', 'KIM', 'KLAC',
    'KMB', 'KMI', 'KMX', 'KO', 'KR',
    'KVUE', 'L', 'LDOS', 'LEN', 'LH',
    'LHX', 'LIN', 'LKQ', 'LLY', 'LMT',
    'LNT', 'LOW', 'LRCX', 'LULU', 'LUV',
    'LVS', 'LW', 'LYB', 'LYV', 'MA',
    'MAA', 'MAR', 'MAS', 'MCD', 'MCHP',
    'MCK', 'MCO', 'MDLZ', 'MDT', 'MET',
    'META', 'MGM', 'MHK', 'MKC', 'MKTX',
    'MLM', 'MMC', 'MMM', 'MNST', 'MO',
    'MOH', 'MOS', 'MPC', 'MPWR', 'MRK',
    'MRNA', 'MRO', 'MS', 'MSCI', 'MSFT',
    'MSI', 'MTB', 'MTCH', 'MTD', 'MU',
    'NCLH', 'NDAQ', 'NDSN', 'NEE', 'NEM',
    'NFLX', 'NI', 'NKE', 'NOC', 'NOW',
    'NRG', 'NSC', 'NTAP', 'NTRS', 'NUE',
    'NVDA', 'NVR', 'NWL', 'NWS', 'NWSA',
    'NXPI', 'O', 'ODFL', 'OKE', 'OMC',
    'ON', 'ORCL', 'ORLY', 'OTIS', 'OXY',
    'PANW', 'PARA', 'PAYC', 'PAYX', 'PCAR',
    'PCG', 'PDD', 'PEAK', 'PEG', 'PEP',
    'PFE', 'PFG', 'PG', 'PGR', 'PH',
    'PHM', 'PKG', 'PLD', 'PM', 'PNC',
    'PNR', 'PNW', 'POOL', 'PPG', 'PPL',
    'PRU', 'PSA', 'PSX', 'PTC', 'PVH',
    'PWR', 'PXD', 'PYPL', 'QCOM', 'QRVO',
    'RCL', 'REG', 'REGN', 'RF', 'RHI',
    'RJF', 'RL', 'RMD', 'ROK', 'ROL',
    'ROP', 'ROST', 'RSG', 'RTX', 'RVTY',
    'SBAC', 'SBUX', 'SCHW', 'SEE', 'SHW',
    'SIVB', 'SJM', 'SLB', 'SMCI', 'SNA',
    'SNPS', 'SO', 'SOLV', 'SPG', 'SPGI',
    'SRE', 'STE', 'STLD', 'STT', 'STX',
    'STZ', 'SWK', 'SWKS', 'SYF', 'SYK',
    'SYY', 'T', 'TAP', 'TDG', 'TDY',
    'TECH', 'TEL', 'TER', 'TFC', 'TFX',
    'TGT', 'TJX', 'TMO', 'TMUS', 'TPR',
    'TRGP', 'TRMB', 'TROW', 'TRV', 'TSCO',
    'TSLA', 'TSN', 'TT', 'TTWO', 'TXN',
    'TXT', 'TYL', 'UAL', 'UBER', 'UDR',
    'UHS', 'ULTA', 'UNH', 'UNP', 'UPS',
    'URI', 'USB', 'V', 'VFC', 'VICI',
    'VLO', 'VLTO', 'VMC', 'VRSK', 'VRSN',
    'VRTX', 'VTR', 'VTRS', 'VZ', 'WAB',
    'WAT', 'WBA', 'WBD', 'WDC', 'WEC',
    'WELL', 'WFC', 'WHR', 'WM', 'WMB',
    'WMT', 'WRB', 'WRK', 'WST', 'WTW',
    'WY', 'WYNN', 'XEL', 'XOM', 'XRAY',
    'XYL', 'YUM', 'ZBH', 'ZBRA', 'ZION',
    'ZTS',
  ];
}
