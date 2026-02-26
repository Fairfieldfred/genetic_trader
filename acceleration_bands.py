"""
Acceleration Bands Indicator

Based on the Pine Script implementation by Alex Orekhov (everget)
Copyright (c) 2018-present, Alex Orekhov (everget)
Acceleration Bands script may be freely distributed under the terms of the GPL-3.0 license.

Acceleration Bands are volatility bands that adjust based on price momentum.
The bands widen during high volatility and narrow during low volatility.

Formula:
    mult = 4000 * factor * (high - low) / (high + low)
    upperBand = SMA(high * (1 + mult), length)
    basis = SMA(close, length)
    lowerBand = SMA(low * (1 - mult), length)

Usage:
    python acceleration_bands.py AAPL --start 2023-01-01 --end 2024-01-01
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from data_loader import DataLoader
import config


class AccelerationBands:
    """
    Calculates and visualizes Acceleration Bands indicator.
    """

    def __init__(self, data: pd.DataFrame, length: int = 20, factor: float = 0.001):
        """
        Initialize Acceleration Bands calculator.

        Args:
            data: DataFrame with OHLCV data
            length: Period for the moving average (default: 20)
            factor: Acceleration factor (default: 0.001)
        """
        self.data = data.copy()
        self.length = length
        self.factor = factor
        self.upper_band = None
        self.basis = None
        self.lower_band = None

    def calculate(self):
        """
        Calculate the Acceleration Bands.

        Returns:
            DataFrame with upper_band, basis, and lower_band columns
        """
        high = self.data['high']
        low = self.data['low']
        close = self.data['close']

        # Calculate the acceleration multiplier
        # mult = 4000 * factor * (high - low) / (high + low)
        mult = 4000 * self.factor * (high - low) / (high + low)

        # Calculate upper band source and apply SMA
        # upperBandSrc = high * (1 + mult)
        upper_band_src = high * (1 + mult)
        self.upper_band = upper_band_src.rolling(window=self.length).mean()

        # Calculate basis (middle line) using close
        # basis = sma(close, length)
        self.basis = close.rolling(window=self.length).mean()

        # Calculate lower band source and apply SMA
        # lowerBandSrc = low * (1 - mult)
        lower_band_src = low * (1 - mult)
        self.lower_band = lower_band_src.rolling(window=self.length).mean()

        # Add to dataframe
        result = self.data.copy()
        result['upper_band'] = self.upper_band
        result['basis'] = self.basis
        result['lower_band'] = self.lower_band
        result['mult'] = mult

        return result

    def get_signals(self, result=None):
        """
        Generate trading signals based on Acceleration Bands.

        Signals:
            - Buy: When price crosses above lower band
            - Sell: When price crosses below upper band
            - Strong Trend: When price stays outside bands

        Args:
            result: DataFrame with calculated bands (optional)

        Returns:
            DataFrame with buy_signal and sell_signal columns
        """
        if result is None:
            result = self.calculate()

        close = result['close']

        # Detect crossovers
        buy_signal = (close > result['lower_band']) & (close.shift(1) <= result['lower_band'].shift(1))
        sell_signal = (close < result['upper_band']) & (close.shift(1) >= result['upper_band'].shift(1))

        result['buy_signal'] = buy_signal
        result['sell_signal'] = sell_signal

        # Detect when price is outside bands (strong trend)
        result['above_upper'] = close > result['upper_band']
        result['below_lower'] = close < result['lower_band']

        return result

    def plot(self, figsize=(14, 10), show_signals=True):
        """
        Create a visualization of the Acceleration Bands.

        Args:
            figsize: Figure size tuple
            show_signals: Whether to show buy/sell signals
        """
        result = self.get_signals()

        fig, axes = plt.subplots(2, 1, figsize=figsize,
                                 gridspec_kw={'height_ratios': [3, 1]})
        fig.suptitle(f'Acceleration Bands (Length={self.length}, Factor={self.factor})',
                    fontsize=16, fontweight='bold')

        # Plot 1: Price chart with Acceleration Bands
        ax1 = axes[0]

        # Plot candlestick-style price
        ax1.plot(result.index, result['close'],
                label='Close Price', color='black', linewidth=1.5, zorder=3)

        # Plot the bands
        ax1.plot(result.index, result['upper_band'],
                label='Upper Band', color='#138484', linewidth=1, alpha=0.8)
        ax1.plot(result.index, result['basis'],
                label='Basis (SMA)', color='#741b47', linewidth=1, alpha=0.8)
        ax1.plot(result.index, result['lower_band'],
                label='Lower Band', color='#138484', linewidth=1, alpha=0.8)

        # Fill between bands
        ax1.fill_between(result.index, result['upper_band'], result['lower_band'],
                        color='#ffd966', alpha=0.2, label='Band Range')

        # Plot buy/sell signals if enabled
        if show_signals:
            buy_points = result[result['buy_signal']]
            sell_points = result[result['sell_signal']]

            if len(buy_points) > 0:
                ax1.scatter(buy_points.index, buy_points['close'],
                           color='green', marker='^', s=100,
                           label='Buy Signal', zorder=5)

            if len(sell_points) > 0:
                ax1.scatter(sell_points.index, sell_points['close'],
                           color='red', marker='v', s=100,
                           label='Sell Signal', zorder=5)

        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.set_title('Price Action with Acceleration Bands', fontsize=14)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)

        # Plot 2: Band Width (measures volatility)
        ax2 = axes[1]

        band_width = ((result['upper_band'] - result['lower_band']) / result['basis'] * 100)
        ax2.plot(result.index, band_width, color='blue', linewidth=1)
        ax2.fill_between(result.index, 0, band_width, color='blue', alpha=0.3)

        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Band Width (%)', fontsize=12)
        ax2.set_title('Volatility (Band Width)', fontsize=14)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def print_summary(self, result=None):
        """
        Print a summary of the Acceleration Bands analysis.
        """
        if result is None:
            result = self.get_signals()
        elif 'buy_signal' not in result.columns:
            result = self.get_signals(result)

        # Get current values
        current = result.iloc[-1]

        print("\n" + "=" * 60)
        print("ACCELERATION BANDS ANALYSIS")
        print("=" * 60)
        print(f"\nParameters:")
        print(f"  Length: {self.length}")
        print(f"  Factor: {self.factor}")

        print(f"\nCurrent Values (as of {current.name.strftime('%Y-%m-%d')}):")
        print(f"  Price: ${current['close']:.2f}")
        print(f"  Upper Band: ${current['upper_band']:.2f}")
        print(f"  Basis (SMA): ${current['basis']:.2f}")
        print(f"  Lower Band: ${current['lower_band']:.2f}")

        # Calculate position relative to bands
        band_range = current['upper_band'] - current['lower_band']
        position_pct = ((current['close'] - current['lower_band']) / band_range) * 100

        print(f"\n  Position in Band: {position_pct:.1f}%")
        if position_pct > 80:
            print(f"  → Price is near UPPER band (potential overbought)")
        elif position_pct < 20:
            print(f"  → Price is near LOWER band (potential oversold)")
        else:
            print(f"  → Price is within normal range")

        # Signal counts
        buy_count = result['buy_signal'].sum()
        sell_count = result['sell_signal'].sum()

        print(f"\nSignals in Period:")
        print(f"  Buy Signals: {buy_count}")
        print(f"  Sell Signals: {sell_count}")

        # Recent signals
        recent_signals = result[result['buy_signal'] | result['sell_signal']].tail(5)
        if len(recent_signals) > 0:
            print(f"\nMost Recent 5 Signals:")
            print("-" * 60)
            for idx, row in recent_signals.iterrows():
                signal_type = "BUY ↗" if row['buy_signal'] else "SELL ↘"
                print(f"{signal_type} | {idx.strftime('%Y-%m-%d')} | "
                      f"Price: ${row['close']:.2f}")
            print("-" * 60)

        # Volatility stats
        band_width = ((result['upper_band'] - result['lower_band']) / result['basis'] * 100)
        print(f"\nVolatility Statistics:")
        print(f"  Current Band Width: {band_width.iloc[-1]:.2f}%")
        print(f"  Average Band Width: {band_width.mean():.2f}%")
        print(f"  Max Band Width: {band_width.max():.2f}%")
        print(f"  Min Band Width: {band_width.min():.2f}%")

        print("\n" + "=" * 60)


def main():
    """
    Main function to run the Acceleration Bands analysis.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description='Calculate and display Acceleration Bands for a stock'
    )
    parser.add_argument('symbol', type=str, help='Stock symbol to analyze')
    parser.add_argument('--start', type=str, default='2023-01-01',
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2024-01-01',
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--length', type=int, default=20,
                       help='Period for moving average (default: 20)')
    parser.add_argument('--factor', type=float, default=0.001,
                       help='Acceleration factor (default: 0.001)')
    parser.add_argument('--save', type=str, help='Save chart to file')
    parser.add_argument('--no-plot', action='store_true',
                       help='Skip plotting (just print stats)')
    parser.add_argument('--no-signals', action='store_true',
                       help='Hide buy/sell signals on chart')

    args = parser.parse_args()

    # Load data
    print(f"Loading data for {args.symbol}...")
    loader = DataLoader(config.DATABASE_PATH)
    data = loader.load_stock_data(
        args.symbol,
        start_date=args.start,
        end_date=args.end
    )

    if data is None or len(data) == 0:
        print(f"Error: No data found for {args.symbol}")
        return

    print(f"Loaded {len(data)} bars from {data.index[0]} to {data.index[-1]}")

    # Calculate Acceleration Bands
    print(f"\nCalculating Acceleration Bands...")
    print(f"  Length: {args.length}")
    print(f"  Factor: {args.factor}")

    ab = AccelerationBands(data, length=args.length, factor=args.factor)
    result = ab.calculate()

    print(f"Calculated bands for {len(result)} bars")

    # Print summary
    ab.print_summary(result)

    # Plot results
    if not args.no_plot:
        print("\nGenerating chart...")
        fig = ab.plot(show_signals=not args.no_signals)

        if args.save:
            fig.savefig(args.save, dpi=300, bbox_inches='tight')
            print(f"Chart saved to {args.save}")
        else:
            plt.show()


if __name__ == "__main__":
    main()
