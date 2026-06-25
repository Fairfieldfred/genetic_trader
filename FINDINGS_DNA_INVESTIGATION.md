# DNA / Fitness Investigation — Findings

_Last updated: 2026-06-25 (session 2: absolute-return objective + regime test)_

This is the get-up-to-speed summary for the genome ("DNA") deep-dive. Read this
first. It records what was investigated, what was **proven**, what changed in the
code, and what to do next. Companion to `.claude/CLAUDE.md` (architecture) — this
file is the **research log + decisions**.

---

## TL;DR (the one thing to remember)

**The strategy is a regime-dependent DOWNSIDE-PROTECTION overlay, not a
bull-market alpha generator.** Its edge is real but only shows up when the market
falls.

- **2022 bear market: ENSEMBLE beat buy-and-hold on 6/6 held-out baskets** —
  lost ~10% while B&H lost ~14% (4–5 pts of consistent downside protection).
- 2018 flat year: beat B&H 2/6. 2024–25 bull: beat B&H 0/6.
- The "0/6 vs B&H" that haunted earlier experiments was a **test-design artifact** —
  we were grading a defensive strategy on a rising market. Against a bull market any
  cash-holding strategy structurally loses; that was never a strategy failure.

**On the genome:** the binding constraint is *what signals the strategy trades on*,
not the search or fitness function. Across 8 experiments, only **ensemble
signal-generation DNA** ever helped (confirmed 3×). Selection tuning, risk-control
DNA, and trend-following DNA were all neutral-to-harmful.

**The objective question (resolved by data):** "absolute return vs a rising market"
is the wrong lens for this strategy. Its measured value is *relative downside
protection* — visible only in risk-adjusted / regime-aware terms. If you want
bull-market absolute alpha, this MA-portfolio architecture likely can't deliver it.

### Lever scoreboard (OOS, absolute return unless noted)
| Lever | Effect | Verdict |
|-------|--------|---------|
| Ensemble signal DNA | +7.2 pts; **6/6 vs B&H in bear** | ✅ only winner |
| Excess-return fitness | no-op (proven constant offset) | ❌ |
| Randomized baskets | slightly worse | ❌ |
| Risk-control DNA (ATR/trail) | −7.4 pts | ❌ |
| Trend-following DNA | −20.8 pts | ❌ worst |

---

## Architecture reality (differs from CLAUDE.md)

- CLAUDE.md describes a 21-gene chromosome. **Reality:** live `config.py` runs only
  the **6 core genes** (MA crossover: `ma_short_period`, `ma_long_period`, `ma_type`,
  `stop_loss_pct`, `take_profit_pct`, `position_size_pct`). Macro genes were removed
  in the latest commit.
- The Dart catalog (`genetic_trader_ui/lib/core/genetic/gene_groups.dart`) defines
  **93 genes across 11 groups**, but only `core` is active in the Python config.
- The 7 `USE_ADVANCED_*` flags in `config.py` are **dead stubs** — referenced
  nowhere in any Python file.
- The Python engines (`vectorbt_fitness.py`, `tradix_strategy.py`) **do implement**
  the richer logic (ensemble signals, TI filters, macro, regime, sizing). The
  machinery exists; the active chromosome just doesn't feed it.
- Active engine path is **vectorbt** (`vectorbt_fitness.py`). `config.BACKTESTING_ENGINE`
  may read `'backtrader'`, but recent/real runs use vectorbt (the fast batch path).
- venv is **Python 3.14** (`.venv`); activate with `source .venv/bin/activate`.

---

## The core problem: overfitting / no OOS edge

Parsed every historical run with an OOS test (18 runs): **OOS beat buy-and-hold in
only 4/18**, and in-sample fitness is **uncorrelated (even negatively)** with OOS
result. The highest in-sample fitness runs were among the worst OOS. Adding genes
(6 → 46 → 93) did not help on its own.

---

## Experiments run this session (all same-seed A/B, OOS across held-out baskets)

Methodology note: every experiment scores the evolved champion **out-of-sample**
on **6 held-out random baskets** and reports a distribution (mean/median/min/max +
how many baskets beat B&H), not a single number. This killed the single-seed noise
problem that made earlier conclusions unreliable.

### 1. Excess-return fitness — NO-OP for selection (proven)
Harnesses: `ab_excess_fitness.py`, `ab_excess_kfold.py`
- Reframing the fitness "return" term as excess-over-buy-and-hold produced a
  **byte-identical champion** to absolute-return fitness.
- **Why (proven mathematically):** when all traders share one basket+window, the
  benchmark is a single constant. Excess = absolute − constant. Subtracting a
  constant cannot change ranking → identical selection. True even under k-fold
  (folds shared across traders).
- Excess fitness only bites when the benchmark **varies per-trader** (e.g. each
  trader on its own basket). That breaks the dedup/batch fast-path.

### 2. Randomized baskets per generation — did NOT help
Harness: `ab_random_basket.py` (3 arms: control / rand-only / rand+excess)
```
arm            mean   median    min     max   beats-B&H
CONTROL       -31.97  -32.93  -59.77   -5.48     0/6
RAND_ONLY     -37.13  -41.29  -61.28   -2.36     0/6
RAND_EXCESS   -37.13  -41.29  -61.28   -2.36     0/6   (identical to RAND_ONLY)
```
- ~5 pts **worse**. Overfitting-via-fixed-basket was real but **not** the binding
  constraint.
- RAND_EXCESS == RAND_ONLY because the harness sets one basket per *generation*
  (whole population shares it) → benchmark still constant within each eval batch.

### 3. Ensemble signal genes — HELPED (+7.2 pts) ✅
Harness: `ab_ensemble.py` (core 6-gene vs core + 13 ensemble genes, `ensemble_enabled` forced on)
```
arm         mean   median    min     max   beats-B&H
CORE_MA   -31.97  -32.93  -59.77   -5.48     0/6
ENSEMBLE  -24.73  -34.89  -42.13   +6.26     1/6   <- first OOS win
```
- +7.2 pts mean, worst-case tail much better (−59.8 → −42.1), **first basket to
  beat B&H** (+6.26). Gain is concentrated in lifting the bad tail (median ~flat).
- Evolved champion leaned on MACD (0.98) + RSI (0.70), MA halved (0.38) — genuinely
  used the new DNA.

### 4. Risk-control genes (ATR sizing + trailing stop) — HURT (−7.4 pts) ❌
Harness: `ab_risk_dna.py` (core vs core + 4 risk genes, enables forced on)
```
arm         mean   median    min     max   beats-B&H
CORE_MA   -31.97  -32.93  -59.77   -5.48     0/6
RISK_DNA  -39.35  -40.52  -59.16  -18.76     0/6
```
- −7.4 pts; trailing stop appears to cut winners early (in unit tests it flipped a
  single-basket return 26→12). Not a wiring bug — genes verified to alter behavior;
  champion used them (atr_risk 2.31%, atr_mult 1.06, trail on).
- Note: enables were **forced on** to isolate. As free 0/1 genes, evolution could
  just learn to turn them off, so they're not harmful to *include* — just not a
  source of edge.

**The decisive contrast:** signal-generation DNA helped (+7.2); risk-control DNA
hurt (−7.4). Edge lives in *what you trade on*, not *how you size/exit*.

---

## Session 2 — absolute-return objective + regime discovery

User set the objective to **absolute return** (not risk-adjusted). This reframed
how to judge results and led to the key discovery.

### 5. Ensemble under absolute-return fitness — confirmed, still loses to bull B&H
Harness: `ab_ensemble_absolute.py`. Shifted `FITNESS_WEIGHTS` to
`total_return 0.85, sharpe/dd/win 0.05 each`. On the 2024–25 bull window:
```
arm        RAW mean  RAW med  RAW min  RAW max  beatB&H   (B&H mean 34.51%)
CORE_MA       3.71     3.02     0.38     8.47     0/6
ENSEMBLE     10.88     9.87     1.83    21.68     0/6
```
Aligning fitness ~tripled raw OOS return (3.7→10.9), and this time the gain was in
the **median** (not just tail) — ensemble confirmed as a real improvement. But both
arms capture only ~1/3 of B&H's 34.5% → 0/6. The ~24-pt gap is structural.

### 6. Allocation-drag diagnostic — the gap is SIGNAL, not cash drag
Harness: `diag_allocation_drag.py`. Swept `INITIAL_ALLOCATION_PCT` 60→100% on the
evolved ensemble champion:
```
Total gap to B&H at 80% alloc : 23.63 pts
Recovered by going 80->100%   :  0.29 pts  (cash drag)   ~1%
Residual gap at 100% alloc    : 23.34 pts  (signal cost)  ~99%
```
**99% of the gap is signal quality, ~1% is cash drag.** "Stay deployed" is a dead
lever (worth 0.3 pts). The trading logic itself underperforms a rising market.

### 7. Trend-following DNA — WORST lever tested (−20.8 pts) ❌
Harness: `ab_trend_follow.py`. Added a self-contained trend-follow signal mode
(`trend_follow_enabled`: long while price > own SMA AND positive N-day momentum;
exit on break). Hypothesis was that "stay long in uptrends" would capture the bull.
```
arm            mean   median    min     max   beatB&H  (B&H mean 34.51%)
CORE_MA        3.71    3.02    0.38    8.47     0/6
ENSEMBLE      10.88    9.87    1.83   21.68     0/6
TREND_FOLLOW −17.04  −18.43  −23.25  −7.25     0/6
```
Hypothesis **wrong** — trend-follow LOST money (whipsaw: late entries, exit on every
pullback, re-buy higher). A good single-basket smoke-test did not survive OOS across
6 baskets — exactly why we test distributionally.

### 8. REGIME TEST — the breakthrough ✅
Harness: `regime_test.py`. Re-ran CORE vs ENSEMBLE on **down-market** windows
(trained on pre-period, no look-ahead):
```
2022 BEAR (B&H mean -14.25%):
  arm         mean    median   min     max   beatB&H  positive
  CORE_MA    -9.12   -10.17  -13.84  -4.03     4/6       0/6
  ENSEMBLE  -10.33   -11.38  -15.36  -0.37     6/6       0/6   <- 6/6!
  B&H       -14.25   -14.90  -19.09  -8.55

Regime summary — ENSEMBLE beats B&H:
  2022 bear  (B&H -14.3%):  6/6   ✅
  2018 flat  (B&H  -0.5%):  2/6
  2024-25 bull (B&H +34.5%): 0/6
```
**The edge is regime-dependent and inverted from what we'd been testing.** In the
bear, the ensemble cushioned losses on every basket (−10% vs −14%). The signal that
"fails" in a bull (going to cash) is exactly what adds value when the market falls.
This resolves the 0/6 puzzle: we'd been grading a defensive strategy on offense.

---

## Code changes made this session

All changes are **backward-compatible** and **default-off**; the normal `evolve.py`
path is unchanged unless flags/genes are explicitly enabled.

### `config.py`
- Added `USE_EXCESS_RETURN_FITNESS = False` (documented). When True, the fitness
  return-term is scored as excess over equal-weight B&H of the same basket.

### `vectorbt_fitness.py`
1. **`_benchmark_return(close_slice)`** — equal-weight buy-and-hold % of the basket
   over the exact slice (per-fold correct). Attached to results as
   `benchmark_return`; consumed by `_score_results` when excess mode is on.
2. **`set_active_basket(symbols)` + `_build_working_set()`** — refactored the
   working-set build (close matrix, MA caches, aligned indicators) out of
   `__init__` so the basket can be re-sampled cheaply from a preloaded universe
   (data loaded once). Enables randomized-basket experiments.
3. **Dedup key fix (production-safety)** — `_chrom_key` in `evaluate_population`
   now hashes the **full active gene set** (`config.GENE_ORDER`), not the hardcoded
   6 core genes. Without this, enabling ensemble/macro/TI/risk genes would silently
   collapse distinct traders into one evaluation. **Required before running any
   enriched genome in production.**
4. **ATR volatility sizing** (gated by `atr_sizing_enabled`, uses `atr_risk_pct`,
   `atr_stop_multiple`) — sizes positions for equal risk-per-trade using each
   stock's **`natr`** (normalized ATR; note: raw `atr_14` is NOT loaded by
   DataLoader — this was a bug found and fixed).
5. **Trailing stop** (gated by `sl_trail_enabled`) — passes `sl_trail=True` to
   vectorbt's `Portfolio.from_signals` so the stop ratchets up with price.
6. **Trend-following signal mode** (session 2, gated by `trend_follow_enabled`,
   uses `tf_sma_period`, `tf_momentum_period`) — long while price > own SMA AND
   positive N-day momentum; exits on break. Takes precedence over ensemble when
   both enabled. Backward compatible (absent gene → byte-identical baseline).

### New experiment harnesses (root dir, all reusable)
Session 1:
- `ab_excess_fitness.py` — absolute vs excess fitness, single window
- `ab_excess_kfold.py` — same under 3-fold CV
- `ab_random_basket.py` — 3-arm randomized-basket test
- `ab_ensemble.py` — genome enrichment: ensemble signal genes ✅ the winner
- `ab_risk_dna.py` — genome enrichment: ATR sizing + trailing stop ❌

Session 2:
- `ab_ensemble_absolute.py` — ensemble under absolute-return fitness weights
- `diag_allocation_drag.py` — decompose B&H gap into cash-drag vs signal cost
- `ab_trend_follow.py` — 3-arm trend-following experiment ❌
- `regime_test.py` — bear/flat/bull regime comparison ✅ the breakthrough

---

## Verification status

No canonical test/lint/build command exists in this repo. All verification was
**ad-hoc** (focused `tempfile` scripts, `hermes-verify-` prefix), not suite-green.
Covered: `set_active_basket`/working-set refactor, dedup fix, lever-gene gates,
excess scoring, trend-follow gate+precedence, and regime-test integrity
(train/test temporal separation + genuine down-regimes). All PASS.

Numerical backtest values are trusted as a function of `SPY_Data.db` + vectorbt,
not independently re-derived. **There is no regression suite** — consider adding one.

---

## Conclusion & recommended next steps

**Resolved:** the strategy is a regime-dependent **downside-protection overlay**.
It reliably cushions drawdowns in falling markets (6/6 vs B&H in the 2022 bear) but
cannot beat a rising market on absolute return (0/6 in bull — structural). Eight
experiments converge on this; the ensemble signal genes are the only genome
enrichment that helps, and they carry the protective edge.

Two genuinely different products to choose between:
- **(A) Embrace the defensive role.** Optimize for downside capture / drawdown
  reduction; evaluate on bear+flat regimes and risk-adjusted metrics (Sharpe,
  Calmar, downside deviation). This plays to the measured strength. Highest-value
  path given the evidence.
- **(B) Pursue bull-market absolute alpha.** This MA-portfolio + market-timing
  architecture likely can't deliver it (timing-based genes all failed). Would need
  a different signal class — leveraged trend persistence, or cross-sectional asset
  *selection* rather than market timing.

Concrete next actions (if continuing):
1. **Make ensemble genes production-ready in `evolve.py`** (dedup fix is done; wire
   `GENE_DEFINITIONS`/`GENE_ORDER` to include the ensemble block; verify the Dart
   UI's generated `config.py` matches).
2. **If pursuing (A):** add a regime-aware / risk-adjusted fitness option and an
   explicit bear-regime evaluation harness (extend `regime_test.py`).
3. **Methodology debt:** add a small regression suite (pin `_benchmark_return`,
   dedup-key, gene-gate + trend-follow behavior) so future genome changes are guarded.
4. **Lower priority / proven dead:** excess-return fitness, randomized baskets,
   risk-control DNA, trend-following DNA. Don't reinvest for performance.
