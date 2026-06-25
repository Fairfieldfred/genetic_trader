# DNA / Fitness Investigation — Findings

_Last updated: 2026-06-25_

This is the get-up-to-speed summary for the genome ("DNA") deep-dive. Read this
first. It records what was investigated, what was **proven**, what changed in the
code, and what to do next. Companion to `.claude/CLAUDE.md` (architecture) — this
file is the **research log + decisions**.

---

## TL;DR (the one thing to remember)

The binding constraint on out-of-sample (OOS) performance is the **genome itself**
— *what signals the strategy trades on* — not the search or the fitness function.

- Tuning **selection pressure** (excess-return fitness, randomized baskets, k-fold)
  → **no improvement**. Proven dead-ends for this strategy.
- Enriching the genome with **signal-generation DNA** (ensemble of MA/Bollinger/
  Stochastic/MACD/RSI) → **+7.2 pts** mean OOS alpha, first arm ever to beat
  buy-and-hold on any held-out basket.
- Enriching with **risk-control DNA** (ATR sizing + trailing stops) → **−7.4 pts**,
  made things worse.

**Direction:** develop signal-generation DNA. Risk-control DNA is at best neutral.
Caveat: even the best arm still loses to buy-and-hold on 5 of 6 baskets — there is
no confirmed edge yet, only a direction that moves the needle.

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

### New experiment harnesses (root dir, all reusable)
- `ab_excess_fitness.py` — absolute vs excess fitness, single window
- `ab_excess_kfold.py` — same under 3-fold CV
- `ab_random_basket.py` — 3-arm randomized-basket test
- `ab_ensemble.py` — genome enrichment: ensemble signal genes ✅ the winner
- `ab_risk_dna.py` — genome enrichment: ATR sizing + trailing stop ❌

---

## Verification status

No canonical test/lint/build command exists in this repo. All verification was
**ad-hoc** (focused `tempfile` scripts), not suite-green. What's covered:
- `set_active_basket` / working-set refactor: default-init regression, basket-swap
  state, determinism, benchmark-varies-across-baskets — PASS.
- Dedup fix: ensemble/risk-gene-only diffs no longer collapse; true duplicates
  still dedup; float jitter rounds — PASS.
- Lever genes: both alter behavior; both gate byte-identically to baseline when off
  (backward compat) — PASS.
- Excess scoring: benchmark math, exact offset, min-trades guard — PASS.

Numerical backtest values are trusted as a function of `SPY_Data.db` + vectorbt,
not independently re-derived. **There is no regression suite** — consider adding one.

---

## Recommended next steps (priority order)

1. **Push the proven lever — signal DNA.**
   - Scale up the ensemble experiment: more held-out baskets + more generations for
     a tighter estimate of the +7.2 pts (current N=6 baskets is small).
   - Add the **advanced-oscillator genes** (already in the Dart catalog:
     Williams %R, CCI, CMO, StochRSI, Ultimate Oscillator, ROC) as additional
     signal diversity, tested the same way.
2. **Make ensemble genes production-ready in `evolve.py`.** The dedup fix is done;
   next wire `config.GENE_DEFINITIONS`/`GENE_ORDER` to include the ensemble block
   (the Dart UI already emits these when the ensemble toggle is on — verify the
   generated `config.py` matches).
3. **Lower priority / proven not to be the lever:** excess-return fitness,
   randomized baskets, k-fold aggregation tweaks. Don't invest here for performance;
   k-fold is still worth keeping purely as an OOS *honesty* check.
4. **Methodology debt:** add a small regression suite (pin `_benchmark_return`,
   dedup-key, gene-gate behavior) so future genome changes are guarded.

### Open question worth resolving
Even the winning arm beats B&H on only 1/6 baskets. Before heavy investment, decide
the bar: is the goal **risk-adjusted** outperformance (Sharpe/drawdown — where the
ensemble's tail-improvement matters) or **absolute** return (where B&H on a rising
market is hard to beat)? The fitness weights currently mix both; clarifying the
objective will sharpen every experiment above.
