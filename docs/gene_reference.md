# Gene Reference Guide

This document explains every gene in the Genetic Trader chromosome and exactly how each one affects the buy, hold, and sell decision process.

## How the Strategy Works (Overview)

The strategy is a **Moving Average (MA) crossover** system with three layers of filters:

1. **Core MA Crossover** — Generates buy/sell signals when a short-period MA crosses above/below a long-period MA
2. **Risk Management** — Applies stop-loss, take-profit, and position sizing rules
3. **Macro Filters** — Global economic conditions that modify position sizes, block buys, or adjust risk thresholds
4. **Technical Indicator (TI) Filters** — Per-stock indicators that modify position sizes, block buys, force exits, or adjust risk thresholds

The macro and TI filters do **not** generate independent signals. They only modify or gate the core MA crossover decisions.

### Decision Flow Per Bar

```
For each stock:
  1. Compute macro context (global, once per bar)
  2. Compute TI context (per stock)
  3. Combine: block_buys = macro.block OR ti.block
              position_scale = macro.scale * ti.scale
              stop_loss_adj = macro.stop_adj * ti.stop_adj
              take_profit_adj = macro.tp_adj * ti.tp_adj

  4. If NOT in position:
       - MA bullish crossover? → BUY (unless block_buys is true)
       - Position size = position_size_pct * position_scale

  5. If IN position:
       - TI force_exit? → SELL immediately
       - Price dropped past (stop_loss_pct * stop_loss_adj)? → SELL (stop loss)
       - Price rose past (take_profit_pct * take_profit_adj)? → SELL (take profit)
       - MA bearish crossover? → SELL
       - Otherwise → HOLD
```

---

## MA Strategy Genes (3)

These are the core signal generators. Every buy and sell decision starts here.

### `ma_short_period`

|                              |                                                                                                                                                                                                                                                                                    |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 5 - 30 (integer)                                                                                                                                                                                                                                                                   |
| **Example Value**            | 29                                                                                                                                                                                                                                                                                 |
| **What it is**               | The lookback period (in trading days) for the fast moving average                                                                                                                                                                                                                  |
| **How it affects decisions** | A shorter period makes the MA more responsive to recent price changes, generating signals sooner. A longer period (like 29) smooths out noise but reacts slower. The **buy signal** fires when this MA crosses above the long MA. The **sell signal** fires when it crosses below. |
| **Practical effect**         | `ma_short_period = 29` is near the top of its range, meaning this trader uses a relatively sluggish fast MA. It will ignore small price movements and only generate signals on sustained trends. Fewer, higher-conviction trades.                                                  |

### `ma_long_period`

|                              |                                                                                                                                                                                                                                                                                                                                                 |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 30 - 100 (integer)                                                                                                                                                                                                                                                                                                                              |
| **Example Value**            | 88                                                                                                                                                                                                                                                                                                                                              |
| **What it is**               | The lookback period (in trading days) for the slow moving average                                                                                                                                                                                                                                                                               |
| **How it affects decisions** | This is the baseline trend indicator. The short MA must cross this line to generate signals. A longer period captures longer-term trends. The gap between short and long periods determines signal sensitivity: a small gap (e.g., 29 vs 30) produces many noisy signals; a large gap (e.g., 29 vs 88) produces fewer, trend-following signals. |
| **Practical effect**         | `ma_long_period = 88` combined with `ma_short_period = 29` gives a gap of 59 days. This trader only enters/exits when there's a substantial trend shift — it's a patient, trend-following strategy.                                                                                                                                             |

### `ma_type`

|                              |                                                                                                                                                                                                                                        |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0 or 1 (integer)                                                                                                                                                                                                                       |
| **Example Value**            | 0                                                                                                                                                                                                                                      |
| **What it is**               | Selects the type of moving average: **0 = SMA** (Simple), **1 = EMA** (Exponential)                                                                                                                                                    |
| **How it affects decisions** | **SMA** weights all days equally over the lookback period. **EMA** gives more weight to recent days, making it more responsive to recent price changes. With EMA, crossover signals arrive earlier but may produce more false signals. |
| **Practical effect**         | `ma_type = 0` (SMA) means this trader uses equal weighting. Combined with the wide 29/88 gap, it's a conservative, noise-resistant setup.                                                                                              |

---

## Risk Management Genes (3)

These genes control when to exit a position and how much capital to commit. They operate after entry and are modified by macro and TI filters.

### `stop_loss_pct`

|                              |                                                                                                                                                                                                                                                                               |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 1.0 - 10.0 (float, percentage)                                                                                                                                                                                                                                                |
| **Example Value**            | 5.7374                                                                                                                                                                                                                                                                        |
| **What it is**               | The maximum percentage loss tolerated before automatically selling                                                                                                                                                                                                            |
| **How it affects decisions** | Once in a position, if the price drops by this percentage from the buy price, the position is **sold immediately**. This is a hard floor to limit losses. The actual threshold used is `stop_loss_pct * stop_loss_adj` where `stop_loss_adj` comes from macro and TI filters. |
| **Practical effect**         | `stop_loss_pct = 5.74%` is a moderately loose stop. The trader tolerates up to ~5.7% drawdown before cutting a position. If macro/TI adjustments tighten it (adj < 1.0), the effective stop could be as tight as ~4%. If they loosen it (adj > 1.0), it could be ~8%+.        |

### `take_profit_pct`

|                              |                                                                                                                                                                                                                                                                    |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Range**                    | 2.0 - 15.0 (float, percentage)                                                                                                                                                                                                                                     |
| **Example Value**            | 2.6207                                                                                                                                                                                                                                                             |
| **What it is**               | The percentage gain at which the position is automatically sold to lock in profit                                                                                                                                                                                  |
| **How it affects decisions** | Once in a position, if the price rises by this percentage from the buy price, the position is **sold immediately**. The actual threshold used is `take_profit_pct * take_profit_adj` where `take_profit_adj` comes from macro and TI filters.                      |
| **Practical effect**         | `take_profit_pct = 2.62%` is very tight — this trader takes profits quickly. It captures small, frequent gains rather than riding big trends. Combined with the wide MA gap (fewer entries), this creates a strategy that waits patiently to enter but exits fast. |

### `position_size_pct`

|                              |                                                                                                                                                                                                                                               |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 5.0 - 25.0 (float, percentage)                                                                                                                                                                                                                |
| **Example Value**            | 24.9841                                                                                                                                                                                                                                       |
| **What it is**               | The percentage of available cash to commit to each new buy order                                                                                                                                                                              |
| **How it affects decisions** | On a buy signal, `cash * position_size_pct / 100 / price` determines the number of shares purchased. The actual percentage used is `position_size_pct * position_scale` where `position_scale` comes from macro and TI filters.               |
| **Practical effect**         | `position_size_pct = 24.98%` means nearly 25% of available cash goes into each trade. This is aggressive sizing — the trader makes large, concentrated bets. If position_scale reduces it (e.g., to 0.5), the effective size drops to ~12.5%. |

---

## Macro Filter Genes (15)

Macro filters read **global** economic data (same values for all stocks on a given day) and produce modifiers that adjust the core MA strategy. They are computed **once per bar** and shared across all stocks.

**Key concept**: Macro filters never generate buy/sell signals themselves. They can only:

- **Scale down** position sizes (reduce exposure)
- **Block** new buys entirely
- **Adjust** stop-loss and take-profit thresholds
- Do **nothing** (neutral, no modification)

### `macro_enabled`

|                              |                                                                                                                                                                                                                        |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0 or 1 (integer)                                                                                                                                                                                                       |
| **Example Value**            | 0                                                                                                                                                                                                                      |
| **What it is**               | Master switch for all macro filters                                                                                                                                                                                    |
| **How it affects decisions** | When **0**, all macro genes are ignored and the context returns neutral values (position_scale=1.0, block_buys=false, stop_loss_adj=1.0, take_profit_adj=1.0). When **1**, the remaining 14 macro genes become active. |
| **Practical effect**         | `macro_enabled = 0` means this trader completely ignores macroeconomic conditions. All other macro gene values are irrelevant — they exist in the chromosome but have zero effect.                                     |

### `macro_weight`

|                              |                                                                                                                                                                                                                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0.0 - 1.0 (float)                                                                                                                                                                                                                                                                     |
| **Example Value**            | 0.9692                                                                                                                                                                                                                                                                                |
| **What it is**               | Controls the **strength** of macro filter modifications                                                                                                                                                                                                                               |
| **How it affects decisions** | When a macro regime is adverse, the position scale formula is: `position_scale *= 1.0 - weight * (1.0 - scale)`. A higher weight means the adverse regime has a stronger dampening effect. At weight=0, macro filters have no effect. At weight=1.0, the full scale value is applied. |
| **Practical effect**         | Even though this value is 0.97 (near maximum), it's irrelevant here because `macro_enabled = 0`. If enabled, it would mean macro conditions have almost full influence over position sizing.                                                                                          |

### `macro_vix_threshold`

|                              |                                                                                                                                                                                                                                                                      |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 15.0 - 50.0 (float)                                                                                                                                                                                                                                                  |
| **Example Value**            | 18.1033                                                                                                                                                                                                                                                              |
| **What it is**               | The VIX (volatility index) level above which the market is considered dangerously volatile                                                                                                                                                                           |
| **How it affects decisions** | When `VIX > threshold`: (1) the "adverse regime" counter increments by 1, and (2) position size is scaled down by `1.0 - weight * (1.0 - vix_position_scale)`. When VIX is below the threshold, no modification occurs.                                              |
| **Practical effect**         | `threshold = 18.1` is quite low — the VIX averages around 15-20 in calm markets and spikes above 30 during crises. This trader would trigger the VIX filter frequently, reducing position sizes during even mild volatility. (Inactive because `macro_enabled = 0`.) |

### `macro_vix_position_scale`

|                              |                                                                                                                                                                                                                                                                            |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0.2 - 1.0 (float)                                                                                                                                                                                                                                                          |
| **Example Value**            | 0.2187                                                                                                                                                                                                                                                                     |
| **What it is**               | The target position scale when VIX exceeds the threshold                                                                                                                                                                                                                   |
| **How it affects decisions** | Combined with `macro_weight`, determines how much to shrink positions. Formula: `position_scale *= 1.0 - weight * (1.0 - scale)`. With weight=0.97 and scale=0.22, the multiplier would be: `1.0 - 0.97 * 0.78 = 0.24`. Positions would be reduced to ~24% of normal size. |
| **Practical effect**         | A very aggressive reduction — if this trader had macros enabled and VIX was elevated, it would barely buy anything. This gene essentially says "cut exposure by ~76% when VIX is high."                                                                                    |

### `macro_yc_threshold`

|                              |                                                                                                                                                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Range**                    | -1.0 - 1.0 (float)                                                                                                                                                                               |
| **Example Value**            | -0.9197                                                                                                                                                                                          |
| **What it is**               | The yield curve slope (10Y - 2Y treasury spread) below which the curve is considered dangerously inverted                                                                                        |
| **How it affects decisions** | When `yield_curve_slope < threshold`: the adverse regime counter increments by 1, and the action defined by `macro_yc_action` is applied. Inverted yield curves historically predict recessions. |
| **Practical effect**         | `threshold = -0.92` is very deep inversion. The yield curve only reaches this level during severe recession signals. This trader would only trigger the filter in extreme conditions.            |

### `macro_yc_action`

|                              |                                                                                                                                                                                                                                                     |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0, 1, or 2 (integer)                                                                                                                                                                                                                                |
| **Example Value**            | 0                                                                                                                                                                                                                                                   |
| **What it is**               | What to do when the yield curve is inverted beyond the threshold                                                                                                                                                                                    |
| **How it affects decisions** | **0 = Count only** — just increments the adverse regime counter, no position modification. **1 = Reduce positions** — scales position size by `1.0 - weight * 0.5`. **2 = Block buys** — prevents all new buy orders while the condition is active. |
| **Practical effect**         | `action = 0` means yield curve inversion only counts toward the regime requirement gate but doesn't directly reduce positions or block buys.                                                                                                        |

### `macro_rate_threshold`

|                              |                                                                                                                                                                                                 |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 1.0 - 8.0 (float)                                                                                                                                                                               |
| **Example Value**            | 2.1931                                                                                                                                                                                          |
| **What it is**               | The Fed Funds Rate level above which interest rates are considered dangerously high                                                                                                             |
| **How it affects decisions** | When `fed_funds_rate > threshold`: adverse regime counter increments, and position size is scaled down by `1.0 - weight * (1.0 - rate_position_scale)`. High rates typically pressure equities. |
| **Practical effect**         | `threshold = 2.19` is moderate. During the 2012-2020 period, the Fed Funds rate ranged from 0-2.5%, so this would trigger during the 2018-2019 tightening cycle.                                |

### `macro_rate_position_scale`

|                              |                                                                                                                       |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0.3 - 1.0 (float)                                                                                                     |
| **Example Value**            | 0.9049                                                                                                                |
| **What it is**               | Target position scale when Fed Funds Rate exceeds the threshold                                                       |
| **How it affects decisions** | With weight=0.97 and scale=0.90: `1.0 - 0.97 * 0.10 = 0.903`. Positions reduced to ~90% of normal — a mild reduction. |
| **Practical effect**         | A gentle pullback. This trader would only slightly reduce exposure during high-rate environments.                     |

### `macro_cpi_threshold`

|                              |                                                                                                                                                                                                |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 2.0 - 8.0 (float)                                                                                                                                                                              |
| **Example Value**            | 5.7875                                                                                                                                                                                         |
| **What it is**               | The year-over-year CPI (inflation) level above which inflation is considered dangerously high                                                                                                  |
| **How it affects decisions** | When `CPI_YoY > threshold`: adverse regime counter increments, and position size is scaled down by `1.0 - weight * (1.0 - cpi_position_scale)`.                                                |
| **Practical effect**         | `threshold = 5.79` is high. CPI rarely exceeded 3% during 2012-2020 (it spiked to 7%+ only in 2021-2022, outside the data range). This filter would almost never trigger in the training data. |

### `macro_cpi_position_scale`

|                              |                                                                                                                                                               |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0.3 - 1.0 (float)                                                                                                                                             |
| **Example Value**            | 0.6396                                                                                                                                                        |
| **What it is**               | Target position scale when CPI exceeds the threshold                                                                                                          |
| **How it affects decisions** | With weight=0.97 and scale=0.64: `1.0 - 0.97 * 0.36 = 0.651`. Positions reduced to ~65% of normal.                                                            |
| **Practical effect**         | A meaningful reduction, but since the CPI threshold is so high, this would only kick in during extreme inflation — which didn't occur in the training period. |

### `macro_unemp_threshold`

|                              |                                                                                                                                                                                      |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Range**                    | 4.0 - 10.0 (float)                                                                                                                                                                   |
| **Example Value**            | 8.1031                                                                                                                                                                               |
| **What it is**               | The unemployment rate above which the labor market is considered dangerously weak                                                                                                    |
| **How it affects decisions** | When `unemployment_rate > threshold`: adverse regime counter increments, and the action defined by `macro_unemp_action` is applied.                                                  |
| **Practical effect**         | `threshold = 8.10` is high. Unemployment was above 8% from 2012-2013 (aftermath of the Great Recession) and briefly in 2020 (COVID). This filter targets major economic disruptions. |

### `macro_unemp_action`

|                              |                                                                                                                                                                                                                                        |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0, 1, or 2 (integer)                                                                                                                                                                                                                   |
| **Example Value**            | 2                                                                                                                                                                                                                                      |
| **What it is**               | What to do when unemployment exceeds the threshold                                                                                                                                                                                     |
| **How it affects decisions** | **0 = Count only** — just increments adverse regime counter. **1 = Reduce positions** — scales by `1.0 - weight * 0.5`. **2 = Block buys** — completely prevents new buy orders while unemployment is elevated.                        |
| **Practical effect**         | `action = 2` (block buys) is the most aggressive response. If enabled, this trader would refuse to open any new positions when unemployment exceeds 8.1%. This would have prevented buying during early 2012-2013 and the COVID crash. |

### `macro_risk_stop_adj`

|                              |                                                                                                                                                                                                                                 |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0.5 - 2.0 (float)                                                                                                                                                                                                               |
| **Example Value**            | 1.4935                                                                                                                                                                                                                          |
| **What it is**               | Multiplier applied to `stop_loss_pct` when enough macro regimes are adverse                                                                                                                                                     |
| **How it affects decisions** | When `adverse_count >= macro_regime_count_req`, the effective stop loss becomes `stop_loss_pct * macro_risk_stop_adj`. A value > 1.0 **loosens** the stop (allows more drawdown before selling). A value < 1.0 **tightens** it. |
| **Practical effect**         | `adj = 1.49` would loosen the stop from 5.74% to 8.56%. The rationale: during adverse macro conditions, markets are volatile, so give positions more room to recover rather than being shaken out by noise.                     |

### `macro_risk_tp_adj`

|                              |                                                                                                                                                                                                                                     |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0.5 - 2.0 (float)                                                                                                                                                                                                                   |
| **Example Value**            | 1.1834                                                                                                                                                                                                                              |
| **What it is**               | Multiplier applied to `take_profit_pct` when enough macro regimes are adverse                                                                                                                                                       |
| **How it affects decisions** | When `adverse_count >= macro_regime_count_req`, the effective take-profit becomes `take_profit_pct * macro_risk_tp_adj`. A value > 1.0 raises the target (waits for larger gains). A value < 1.0 lowers it (takes profits earlier). |
| **Practical effect**         | `adj = 1.18` would raise take-profit from 2.62% to 3.09%. During bad macro conditions, this trader demands slightly higher gains before selling. Combined with the loosened stop, it's a "be more patient" approach during turmoil. |

### `macro_regime_count_req`

|                              |                                                                                                                                                                                                                                                                                                                                            |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Range**                    | 1 - 4 (integer)                                                                                                                                                                                                                                                                                                                            |
| **Example Value**            | 4                                                                                                                                                                                                                                                                                                                                          |
| **What it is**               | The number of adverse macro regimes that must be simultaneously active before the risk adjustments (`macro_risk_stop_adj` and `macro_risk_tp_adj`) are applied                                                                                                                                                                             |
| **How it affects decisions** | Each macro filter (VIX, yield curve, rates, CPI, unemployment) can increment the adverse counter by 1 (max 5). The risk adjustments only activate when the counter reaches this threshold. Individual macro filters always apply their position_scale and block effects regardless of this value — only the stop/TP adjustments are gated. |
| **Practical effect**         | `count_req = 4` means 4 out of 5 macro indicators must simultaneously be adverse before stop-loss and take-profit thresholds are modified. This is an extremely high bar — the risk adjustments would almost never activate.                                                                                                               |

---

## Technical Indicator Genes (12)

TI filters read **per-stock** indicator data (each stock has its own RSI, ADX, etc.) and produce modifiers similar to macro filters. They are computed **per stock per bar**.

Like macro filters, TI filters never generate independent signals. They modify or gate the core MA crossover. However, they have one additional capability: **force_exit** can trigger an immediate sell.

### `ti_enabled`

|                              |                                                                                                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Range**                    | 0 or 1 (integer)                                                                                                                                       |
| **Example Value**            | 0                                                                                                                                                      |
| **What it is**               | Master switch for all technical indicator filters                                                                                                      |
| **How it affects decisions** | When **0**, all TI genes are ignored and neutral values are returned. When **1**, the remaining 11 TI genes become active.                             |
| **Practical effect**         | `ti_enabled = 0` means this trader ignores all per-stock technical indicators. RSI, ADX, NATR, MFI, and MACD histogram have zero influence on trading. |

### `ti_weight`

|                              |                                                                                                                                                   |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0.0 - 1.0 (float)                                                                                                                                 |
| **Example Value**            | 0.9577                                                                                                                                            |
| **What it is**               | Controls the strength of TI filter modifications (analogous to `macro_weight`)                                                                    |
| **How it affects decisions** | Appears in scaling formulas like `1.0 - weight * (1.0 - scale)` and `1.0 + weight * 0.5`. A higher weight amplifies the impact of each TI filter. |
| **Practical effect**         | Near maximum at 0.96 — but irrelevant since `ti_enabled = 0`. If enabled, TI conditions would have strong influence.                              |

### `ti_rsi_overbought`

|                              |                                                                                                                                                                                                                                  |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 60 - 90 (integer)                                                                                                                                                                                                                |
| **Example Value**            | 66                                                                                                                                                                                                                               |
| **What it is**               | The RSI (Relative Strength Index, 14-period) level above which a stock is considered overbought                                                                                                                                  |
| **How it affects decisions** | When `RSI > ti_rsi_overbought`: **new buys are blocked** for that stock. The reasoning: the stock has risen too fast too quickly and is likely to pull back. Existing positions are unaffected — this only prevents new entries. |
| **Practical effect**         | `threshold = 66` is more conservative than the traditional 70. This trader would block buys earlier, avoiding chasing momentum. It's a cautious stance that sacrifices some trend-following upside to avoid buying at peaks.     |

### `ti_rsi_oversold`

|                              |                                                                                                                                                                                             |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 10 - 40 (integer)                                                                                                                                                                           |
| **Example Value**            | 34                                                                                                                                                                                          |
| **What it is**               | The RSI level below which a stock is considered oversold                                                                                                                                    |
| **How it affects decisions** | When `RSI < ti_rsi_oversold`: position size is **scaled up** by `1.0 + weight * 0.5`. The reasoning: the stock is beaten down and may bounce, so increase exposure to capture the recovery. |
| **Practical effect**         | `threshold = 34` with `weight = 0.96` gives a scale of `1.0 + 0.96 * 0.5 = 1.48`. Position sizes increase by ~48% when the stock is oversold. This is a contrarian "buy the dip" amplifier. |

### `ti_adx_threshold`

| | |

|---|---|
| **Range** | 15 - 40 (integer) |
| **Example Value** | 17 |
| **What it is** | The ADX (Average Directional Index) level below which a stock's trend is considered too weak to trade |
| **How it affects decisions** | ADX measures trend **strength** (not direction). When `ADX < ti_adx_threshold`: position size is **scaled down** by `1.0 - weight * (1.0 - adx_position_scale)`. The reasoning: MA crossover signals are unreliable in trendless, choppy markets. |
| **Practical effect** | `threshold = 17` is low. ADX below 20 is generally considered no trend, 20-25 is emerging trend, 25+ is strong trend. At 17, this trader only reduces position size in the weakest, most directionless markets — it's quite permissive and allows trading in most conditions. |

### `ti_adx_position_scale`

|                              |                                                                                                                                                                                                                                                       |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0.2 - 1.0 (float)                                                                                                                                                                                                                                     |
| **Example Value**            | 0.3968                                                                                                                                                                                                                                                |
| **What it is**               | The target position scale when ADX is below the threshold (weak trend)                                                                                                                                                                                |
| **How it affects decisions** | With weight=0.96 and scale=0.40: `1.0 - 0.96 * 0.60 = 0.424`. Position size drops to ~42% of normal when the trend is weak.                                                                                                                           |
| **Practical effect**         | Significant reduction — when ADX shows no trend, the trader cuts position sizes by more than half. This protects against whipsaw losses from false crossover signals in rangebound markets. But since the threshold is only 17, this rarely triggers. |

### `ti_natr_threshold`

|                              |                                                                                                                                                                                        |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 2.0 - 8.0 (float)                                                                                                                                                                      |
| **Example Value**            | 3.9808                                                                                                                                                                                 |
| **What it is**               | The NATR (Normalized Average True Range, expressed as percentage) level above which a stock is considered dangerously volatile                                                         |
| **How it affects decisions** | When `NATR > threshold`, the `ti_natr_risk_action` determines the response. NATR normalizes ATR by price, so a value of 4.0 means the stock's average daily range is ~4% of its price. |
| **Practical effect**         | `threshold = 3.98` catches stocks with high daily swings. Many volatile small-caps and biotechs routinely exceed this.                                                                 |

### `ti_natr_risk_action`

|                              |                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0, 1, or 2 (integer)                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **Example Value**            | 1                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| **What it is**               | What to do when NATR exceeds the threshold                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **How it affects decisions** | **0 = Tighten stop-loss** — multiplies stop_loss_adj by 0.7, making the stop tighter (sell sooner on losses). Rationale: in volatile stocks, limit your downside by exiting early. **1 = Loosen stop-loss** — multiplies stop_loss_adj by 1.5, making the stop wider (allow more drawdown). Rationale: in volatile stocks, normal fluctuations will trigger tight stops, so give more room. **2 = Block buys** — prevents new buy orders for volatile stocks entirely. |
| **Practical effect**         | `action = 1` (loosen stop) with base stop of 5.74%: effective stop becomes `5.74 * 1.5 = 8.61%` for volatile stocks. This trader accepts wider swings in volatile names rather than getting stopped out by noise.                                                                                                                                                                                                                                                      |

### `ti_mfi_overbought`

|                              |                                                                                                                                                                                                                                                             |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 70 - 95 (integer)                                                                                                                                                                                                                                           |
| **Example Value**            | 70                                                                                                                                                                                                                                                          |
| **What it is**               | The MFI (Money Flow Index) level above which the stock is considered overbought by volume-weighted price pressure                                                                                                                                           |
| **How it affects decisions** | MFI is like RSI but incorporates volume. When `MFI > ti_mfi_overbought`: position size is **scaled down** by `1.0 - weight * 0.4`. This indicates heavy buying pressure that may be exhausted.                                                              |
| **Practical effect**         | `threshold = 70` with `weight = 0.96`: scale = `1.0 - 0.96 * 0.4 = 0.616`. Positions reduced to ~62% of normal when MFI is overbought. Unlike RSI overbought (which blocks buys entirely), MFI overbought just reduces size — you can still buy, just less. |

### `ti_mfi_oversold`

|                              |                                                                                                                                                                                                                                                                                           |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 5 - 30 (integer)                                                                                                                                                                                                                                                                          |
| **Example Value**            | 19                                                                                                                                                                                                                                                                                        |
| **What it is**               | The MFI level below which the stock is considered oversold by volume-weighted price pressure                                                                                                                                                                                              |
| **How it affects decisions** | When `MFI < ti_mfi_oversold`: position size is **scaled up** by `1.0 + weight * 0.3`. This indicates heavy selling pressure that may be exhausted — a potential buying opportunity.                                                                                                       |
| **Practical effect**         | `threshold = 19` with `weight = 0.96`: scale = `1.0 + 0.96 * 0.3 = 1.288`. Positions increase by ~29% when MFI shows selling exhaustion. This stacks with RSI oversold — if both trigger simultaneously, the combined scale could be `1.48 * 1.29 = 1.91`, nearly doubling position size. |

### `ti_macdhist_confirm`

|                              |                                                                                                                                                                                                                                                                                               |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0 or 1 (integer)                                                                                                                                                                                                                                                                              |
| **Example Value**            | 1                                                                                                                                                                                                                                                                                             |
| **What it is**               | Whether to require MACD histogram confirmation before allowing new buys                                                                                                                                                                                                                       |
| **How it affects decisions** | When **1**: new buys are **blocked** if the MACD histogram is <= 0. The MACD histogram represents the difference between MACD and its signal line. A positive histogram means bullish momentum is accelerating. When **0**: no MACD confirmation required — MA crossover alone is sufficient. |
| **Practical effect**         | `confirm = 1` adds a secondary momentum filter to entries. A bullish MA crossover that occurs while MACD histogram is negative (decelerating momentum) will be ignored. This reduces false signals but may also delay entry into legitimate moves.                                            |

### `ti_macdhist_exit_confirm`

|                              |                                                                                                                                                                                                                                                                                                    |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0 or 1 (integer)                                                                                                                                                                                                                                                                                   |
| **Example Value**            | 0                                                                                                                                                                                                                                                                                                  |
| **What it is**               | Whether a negative MACD histogram should force an immediate exit from existing positions                                                                                                                                                                                                           |
| **How it affects decisions** | When **1**: if the MACD histogram goes negative while in a position, the position is **sold immediately** (force_exit), regardless of stop-loss, take-profit, or MA crossover signals. This is checked **before** all other exit logic. When **0**: MACD histogram is not used for exit decisions. |
| **Practical effect**         | `exit_confirm = 0` means this trader does not use MACD for exits. Positions are only closed by stop-loss, take-profit, or bearish MA crossover. Setting this to 1 would create a very aggressive exit trigger that sells at the first sign of momentum loss.                                       |

---

## How Filters Combine

Macro and TI contexts are computed independently and then **combined multiplicatively**:

| Modifier          | Combination Method                                                  |
| ----------------- | ------------------------------------------------------------------- |
| `block_buys`      | `macro.block_buys OR ti.block_buys` — either one can block          |
| `position_scale`  | `macro.position_scale * ti.position_scale` — both reduce together   |
| `stop_loss_adj`   | `macro.stop_loss_adj * ti.stop_loss_adj` — both adjust together     |
| `take_profit_adj` | `macro.take_profit_adj * ti.take_profit_adj` — both adjust together |
| `force_exit`      | TI only (macro does not have this)                                  |

Both `position_scale` values are floored at 0.1 (minimum 10% of normal) to prevent zero-size orders.

### Example

If macro conditions reduce position_scale to 0.5 and TI conditions also reduce it to 0.6, the combined scale is `0.5 * 0.6 = 0.3`. A trader with `position_size_pct = 25%` would only commit `25 * 0.3 = 7.5%` of cash to the trade.

---

## Ensemble Signal Genes (13)

When ensemble mode is enabled, the core signal generator changes from a single MA crossover to a **weighted combination of 5 signal generators**. Each generator produces a continuous score from -1.0 (strong sell) to +1.0 (strong buy). The weighted average is compared against buy/sell thresholds to trigger actions.

The macro and TI filter layers continue to work on top of the ensemble — they modify position sizes, block buys, and adjust risk thresholds regardless of which signal generator triggered the trade.

### `ensemble_enabled`

|                              |                                                                                                                                                                                                                                                                                                                                                 |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0 or 1 (integer)                                                                                                                                                                                                                                                                                                                                |
| **What it is**               | Master switch for the ensemble signal system                                                                                                                                                                                                                                                                                                    |
| **How it affects decisions** | When **0**, the strategy uses only the MA crossover for buy/sell signals (original behavior). When **1**, all 5 signal generators are computed and their weighted combination drives decisions. The MA crossover genes (`ma_short_period`, `ma_long_period`, `ma_type`) are still used — the MA signal becomes one of 5 inputs to the ensemble. |

### `sig_ma_weight`

|                              |                                                                                                                                                                                                                                                    |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0.0 - 1.0 (float)                                                                                                                                                                                                                                  |
| **What it is**               | Weight of the MA crossover signal in the ensemble                                                                                                                                                                                                  |
| **How it affects decisions** | The MA signal is computed as the normalized spread between short and long MAs: `(ma_short - ma_long) / ma_long`, scaled to [-1, +1]. A higher weight gives more influence to trend-following signals. At 0.0, MA crossover is effectively ignored. |

### `sig_bb_weight`

|                              |                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0.0 - 1.0 (float)                                                                                                                                                                                                                                                                                                                                     |
| **What it is**               | Weight of the Bollinger Band mean-reversion signal                                                                                                                                                                                                                                                                                                    |
| **How it affects decisions** | The Bollinger signal measures where the current price sits within the bands. Price at the lower band → +1 (buy, expecting reversion up). Price at the upper band → -1 (sell, expecting reversion down). Price at the middle band → 0 (neutral). This is fundamentally **opposite** to trend-following — it profits from prices returning to the mean. |

### `sig_stoch_weight`

|                              |                                                                                                                                                                                                                                                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Range**                    | 0.0 - 1.0 (float)                                                                                                                                                                                                                                                                                      |
| **What it is**               | Weight of the Stochastic oscillator signal                                                                                                                                                                                                                                                             |
| **How it affects decisions** | The Stochastic signal normalizes %K within the overbought/oversold range defined by `sig_stoch_ob` and `sig_stoch_os`. Oversold → +1 (buy), overbought → -1 (sell). Gets a 0.3 boost when %K crosses %D in extreme zones (bullish crossover in oversold zone or bearish crossover in overbought zone). |

### `sig_macd_weight`

|                              |                                                                                                                                                                                                                                                                                                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Range**                    | 0.0 - 1.0 (float)                                                                                                                                                                                                                                                                                                                                |
| **What it is**               | Weight of the MACD momentum signal                                                                                                                                                                                                                                                                                                               |
| **How it affects decisions** | The MACD signal is computed as `(MACD_line - Signal_line) / close_price`, normalized to [-1, +1]. Positive = bullish momentum (MACD above signal line), negative = bearish. This captures momentum shifts — it's similar to MA crossover but operates on the difference between two EMAs, making it more sensitive to acceleration/deceleration. |

### `sig_rsi_weight`

|                              |                                                                                                                                                                                                                                                                                                                                                                           |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0.0 - 1.0 (float)                                                                                                                                                                                                                                                                                                                                                         |
| **What it is**               | Weight of the RSI overbought/oversold signal                                                                                                                                                                                                                                                                                                                              |
| **How it affects decisions** | The RSI signal normalizes the current RSI value within the range defined by `sig_rsi_ob` and `sig_rsi_os`. Oversold → +1 (buy), overbought → -1 (sell). Note: this is distinct from the TI filter's RSI genes (`ti_rsi_overbought`/`ti_rsi_oversold`) which block buys or scale positions. The ensemble RSI is a continuous signal that contributes to the weighted vote. |

### `sig_buy_threshold`

|                              |                                                                                                                                                                                                                                                                               |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0.1 - 0.8 (float)                                                                                                                                                                                                                                                             |
| **What it is**               | The minimum combined ensemble score required to trigger a buy                                                                                                                                                                                                                 |
| **How it affects decisions** | After computing the weighted average of all 5 signals, a buy is triggered only if `combined_score > sig_buy_threshold`. A low threshold (e.g., 0.1) means even mild consensus triggers a buy. A high threshold (e.g., 0.7) requires strong agreement across multiple signals. |

### `sig_sell_threshold`

|                              |                                                                                                                                                                                                                                                                                                                                                    |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | -0.8 to -0.1 (float, stored as negative)                                                                                                                                                                                                                                                                                                           |
| **What it is**               | The combined ensemble score below which a sell is triggered                                                                                                                                                                                                                                                                                        |
| **How it affects decisions** | While in a position, a sell is triggered if `combined_score < sig_sell_threshold`. Note: stop-loss and take-profit are checked **before** the ensemble sell signal. The ensemble sell replaces the bearish MA crossover exit. A value of -0.3 means moderate bearish consensus triggers a sell. A value of -0.7 requires strong bearish agreement. |

### `sig_bb_period_idx`

|                              |                                                                                                                                                                                  |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 0 - 2 (integer)                                                                                                                                                                  |
| **What it is**               | Reserved for future Bollinger Band period selection                                                                                                                              |
| **How it affects decisions** | Currently always uses the pre-computed Bollinger Bands from the database (default 20-period, 2 standard deviations). Values 1 and 2 are reserved for future alternative periods. |

### `sig_stoch_ob`

|                              |                                                                                                                                                                                                                         |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 70 - 90 (integer)                                                                                                                                                                                                       |
| **What it is**               | Stochastic overbought level for the ensemble signal                                                                                                                                                                     |
| **How it affects decisions** | Defines the upper boundary of the Stochastic normalization range. When %K exceeds this level, the Stochastic signal is strongly negative (sell). Also defines the zone where bearish %K/%D crossovers get a -0.3 boost. |

### `sig_stoch_os`

|                              |                                                                                                                                                                                                                            |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 10 - 30 (integer)                                                                                                                                                                                                          |
| **What it is**               | Stochastic oversold level for the ensemble signal                                                                                                                                                                          |
| **How it affects decisions** | Defines the lower boundary of the Stochastic normalization range. When %K drops below this level, the Stochastic signal is strongly positive (buy). Also defines the zone where bullish %K/%D crossovers get a +0.3 boost. |

### `sig_rsi_ob`

|                              |                                                                                                                                                                                                                 |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Range**                    | 60 - 85 (integer)                                                                                                                                                                                               |
| **What it is**               | RSI overbought level for the ensemble signal                                                                                                                                                                    |
| **How it affects decisions** | Defines the upper boundary for normalizing the RSI signal. When RSI exceeds this, the signal is strongly negative (sell). Distinct from `ti_rsi_overbought` which is used by the TI filter layer to block buys. |

### `sig_rsi_os`

|                              |                                                                                                                                                                                                                          |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Range**                    | 15 - 40 (integer)                                                                                                                                                                                                        |
| **What it is**               | RSI oversold level for the ensemble signal                                                                                                                                                                               |
| **How it affects decisions** | Defines the lower boundary for normalizing the RSI signal. When RSI drops below this, the signal is strongly positive (buy). Distinct from `ti_rsi_oversold` which is used by the TI filter layer to scale up positions. |

### Ensemble Signal Combination

The 5 signals are combined via weighted average:

```
combined = (ma_weight * ma_signal + bb_weight * bb_signal + stoch_weight * stoch_signal
            + macd_weight * macd_signal + rsi_weight * rsi_signal) / total_weight
```

If `total_weight < 0.01` (all weights near zero), no signal is generated.

Buy when `combined > sig_buy_threshold`. Sell when `combined < sig_sell_threshold`.

---

## The Trader in the Screenshot

With `macro_enabled = 0` and `ti_enabled = 0`, this particular trader is a **pure MA crossover** system:

- **Entry**: Buy when SMA(29) crosses above SMA(88)
- **Exit**: Sell when price drops 5.74% (stop-loss), rises 2.62% (take-profit), or SMA(29) crosses below SMA(88)
- **Position sizing**: 24.98% of available cash per trade
- **No macro or TI influence**: All 27 filter genes exist in the chromosome but have zero effect

The genetic algorithm evolved a trader that found the simplest strategy (no filters) to be the most fit. The macro and TI gene values are carried as latent genetic material — they could become active through mutation in future generations if `macro_enabled` or `ti_enabled` flips to 1.
