"""
Market Cycles Analysis Script

Analyzes and visualizes market cycles for individual stocks:
- Detects swing highs and lows
- Identifies bullish/bearish cycles
- Measures cycle periods and amplitudes
- Visualizes cycle changes with charts

Usage:
    python cycles_analysis.py AAPL --start 2020-01-01 --end 2024-01-01
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from data_loader import DataLoader
import config


class CyclesAnalyzer:
    """
    Analyzes market cycles using swing detection and trend identification.
    """

    def __init__(self, data: pd.DataFrame, swing_window: int = 5):
        """
        Initialize the cycles analyzer.

        Args:
            data: DataFrame with OHLCV data
            swing_window: Number of bars to look back/forward for swing detection
        """
        self.data = data.copy()
        self.swing_window = swing_window
        self.swings = None
        self.cycles = None

    def detect_swings(self):
        """
        Detect swing highs and swing lows in the price data.

        A swing high is a peak where the high is higher than N bars before and after.
        A swing low is a trough where the low is lower than N bars before and after.
        """
        highs = self.data['high'].values
        lows = self.data['low'].values
        closes = self.data['close'].values

        swing_highs = []
        swing_lows = []

        # Detect swing points
        for i in range(self.swing_window, len(self.data) - self.swing_window):
            # Check for swing high
            is_swing_high = True
            for j in range(1, self.swing_window + 1):
                if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                    is_swing_high = False
                    break

            if is_swing_high:
                swing_highs.append({
                    'index': i,
                    'date': self.data.index[i],
                    'price': highs[i],
                    'type': 'high'
                })

            # Check for swing low
            is_swing_low = True
            for j in range(1, self.swing_window + 1):
                if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                    is_swing_low = False
                    break

            if is_swing_low:
                swing_lows.append({
                    'index': i,
                    'date': self.data.index[i],
                    'price': lows[i],
                    'type': 'low'
                })

        # Combine and sort all swings
        all_swings = swing_highs + swing_lows
        all_swings.sort(key=lambda x: x['index'])

        self.swings = pd.DataFrame(all_swings)
        return self.swings

    def identify_cycles(self):
        """
        Identify market cycles from swing points.

        A cycle is defined as:
        - Bullish cycle: from swing low to swing high
        - Bearish cycle: from swing high to swing low
        """
        if self.swings is None or len(self.swings) == 0:
            self.detect_swings()

        cycles = []

        for i in range(len(self.swings) - 1):
            current_swing = self.swings.iloc[i]
            next_swing = self.swings.iloc[i + 1]

            # Calculate cycle metrics
            duration = (next_swing['date'] - current_swing['date']).days
            price_change = next_swing['price'] - current_swing['price']
            price_change_pct = (price_change / current_swing['price']) * 100

            # Determine cycle type
            if current_swing['type'] == 'low' and next_swing['type'] == 'high':
                cycle_type = 'bullish'
            elif current_swing['type'] == 'high' and next_swing['type'] == 'low':
                cycle_type = 'bearish'
            else:
                # Skip if same type (rare edge case)
                continue

            cycles.append({
                'start_date': current_swing['date'],
                'end_date': next_swing['date'],
                'start_price': current_swing['price'],
                'end_price': next_swing['price'],
                'duration_days': duration,
                'price_change': price_change,
                'price_change_pct': price_change_pct,
                'type': cycle_type,
                'amplitude': abs(price_change)
            })

        self.cycles = pd.DataFrame(cycles)
        return self.cycles

    def calculate_statistics(self):
        """
        Calculate statistics about the detected cycles.
        """
        if self.cycles is None or len(self.cycles) == 0:
            self.identify_cycles()

        bullish = self.cycles[self.cycles['type'] == 'bullish']
        bearish = self.cycles[self.cycles['type'] == 'bearish']

        stats = {
            'total_cycles': len(self.cycles),
            'bullish_cycles': len(bullish),
            'bearish_cycles': len(bearish),
            'avg_bullish_duration': bullish['duration_days'].mean() if len(bullish) > 0 else 0,
            'avg_bearish_duration': bearish['duration_days'].mean() if len(bearish) > 0 else 0,
            'avg_bullish_gain_pct': bullish['price_change_pct'].mean() if len(bullish) > 0 else 0,
            'avg_bearish_loss_pct': bearish['price_change_pct'].mean() if len(bearish) > 0 else 0,
            'max_bullish_gain_pct': bullish['price_change_pct'].max() if len(bullish) > 0 else 0,
            'max_bearish_loss_pct': bearish['price_change_pct'].min() if len(bearish) > 0 else 0,
        }

        return stats

    def plot_cycles(self, figsize=(14, 10)):
        """
        Create a comprehensive visualization of the cycles.
        """
        if self.cycles is None or len(self.cycles) == 0:
            self.identify_cycles()

        fig, axes = plt.subplots(3, 1, figsize=figsize)
        fig.suptitle('Market Cycles Analysis', fontsize=16, fontweight='bold')

        # Plot 1: Price chart with swing points
        ax1 = axes[0]
        ax1.plot(self.data.index, self.data['close'],
                label='Close Price', color='blue', alpha=0.7, linewidth=1)

        # Plot swing highs and lows
        if self.swings is not None and len(self.swings) > 0:
            highs = self.swings[self.swings['type'] == 'high']
            lows = self.swings[self.swings['type'] == 'low']

            ax1.scatter(highs['date'], highs['price'],
                       color='red', marker='v', s=100, label='Swing High', zorder=5)
            ax1.scatter(lows['date'], lows['price'],
                       color='green', marker='^', s=100, label='Swing Low', zorder=5)

            # Draw cycle lines
            for _, cycle in self.cycles.iterrows():
                color = 'green' if cycle['type'] == 'bullish' else 'red'
                alpha = 0.3
                ax1.plot([cycle['start_date'], cycle['end_date']],
                        [cycle['start_price'], cycle['end_price']],
                        color=color, alpha=alpha, linewidth=2)

        ax1.set_ylabel('Price ($)')
        ax1.set_title('Price Action with Swing Points')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)

        # Plot 2: Cycle duration histogram
        ax2 = axes[1]
        if len(self.cycles) > 0:
            bullish = self.cycles[self.cycles['type'] == 'bullish']
            bearish = self.cycles[self.cycles['type'] == 'bearish']

            if len(bullish) > 0:
                ax2.bar(range(len(bullish)), bullish['duration_days'],
                       color='green', alpha=0.6, label='Bullish Duration')
            if len(bearish) > 0:
                offset = len(bullish)
                ax2.bar(range(offset, offset + len(bearish)), bearish['duration_days'],
                       color='red', alpha=0.6, label='Bearish Duration')

        ax2.set_xlabel('Cycle Number')
        ax2.set_ylabel('Duration (days)')
        ax2.set_title('Cycle Durations')
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3, axis='y')

        # Plot 3: Cycle returns
        ax3 = axes[2]
        if len(self.cycles) > 0:
            bullish = self.cycles[self.cycles['type'] == 'bullish']
            bearish = self.cycles[self.cycles['type'] == 'bearish']

            if len(bullish) > 0:
                ax3.bar(range(len(bullish)), bullish['price_change_pct'],
                       color='green', alpha=0.6, label='Bullish % Change')
            if len(bearish) > 0:
                offset = len(bullish)
                ax3.bar(range(offset, offset + len(bearish)), bearish['price_change_pct'],
                       color='red', alpha=0.6, label='Bearish % Change')

        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax3.set_xlabel('Cycle Number')
        ax3.set_ylabel('Price Change (%)')
        ax3.set_title('Cycle Returns')
        ax3.legend(loc='best')
        ax3.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        return fig

    def print_summary(self, stats=None):
        """
        Print a summary of the cycle analysis.
        """
        if stats is None:
            stats = self.calculate_statistics()

        print("\n" + "=" * 60)
        print("MARKET CYCLES ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"\nTotal Cycles Detected: {stats['total_cycles']}")
        print(f"  - Bullish Cycles: {stats['bullish_cycles']}")
        print(f"  - Bearish Cycles: {stats['bearish_cycles']}")

        print(f"\nAverage Cycle Duration:")
        print(f"  - Bullish: {stats['avg_bullish_duration']:.1f} days")
        print(f"  - Bearish: {stats['avg_bearish_duration']:.1f} days")

        print(f"\nAverage Cycle Returns:")
        print(f"  - Bullish: +{stats['avg_bullish_gain_pct']:.2f}%")
        print(f"  - Bearish: {stats['avg_bearish_loss_pct']:.2f}%")

        print(f"\nExtreme Cycles:")
        print(f"  - Largest Bullish Gain: +{stats['max_bullish_gain_pct']:.2f}%")
        print(f"  - Largest Bearish Loss: {stats['max_bearish_loss_pct']:.2f}%")

        print("\n" + "=" * 60)

        # Print recent cycles
        if self.cycles is not None and len(self.cycles) > 0:
            print("\nMost Recent 5 Cycles:")
            print("-" * 60)
            recent = self.cycles.tail(5)
            for idx, cycle in recent.iterrows():
                cycle_type = "↗ BULL" if cycle['type'] == 'bullish' else "↘ BEAR"
                print(f"{cycle_type} | {cycle['start_date'].strftime('%Y-%m-%d')} → "
                      f"{cycle['end_date'].strftime('%Y-%m-%d')} | "
                      f"{cycle['duration_days']} days | "
                      f"{cycle['price_change_pct']:+.2f}%")
            print("-" * 60)


def main():
    """
    Main function to run the cycles analysis.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Analyze market cycles for a stock')
    parser.add_argument('symbol', type=str, help='Stock symbol to analyze')
    parser.add_argument('--start', type=str, default='2020-01-01',
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2024-01-01',
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--swing-window', type=int, default=5,
                       help='Window size for swing detection (default: 5)')
    parser.add_argument('--save', type=str, help='Save chart to file')
    parser.add_argument('--no-plot', action='store_true',
                       help='Skip plotting (just print stats)')

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

    # Analyze cycles
    print(f"\nAnalyzing cycles with swing window = {args.swing_window}...")
    analyzer = CyclesAnalyzer(data, swing_window=args.swing_window)

    swings = analyzer.detect_swings()
    print(f"Detected {len(swings)} swing points")

    cycles = analyzer.identify_cycles()
    print(f"Identified {len(cycles)} complete cycles")

    # Print statistics
    stats = analyzer.calculate_statistics()
    analyzer.print_summary(stats)

    # Plot results
    if not args.no_plot:
        print("\nGenerating chart...")
        fig = analyzer.plot_cycles()

        if args.save:
            fig.savefig(args.save, dpi=300, bbox_inches='tight')
            print(f"Chart saved to {args.save}")
        else:
            plt.show()


if __name__ == "__main__":
    main()
