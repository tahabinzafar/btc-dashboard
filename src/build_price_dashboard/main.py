#!/usr/bin/env python3
"""
BTC Monthly Returns Dashboard Generator

Creates a heatmap visualization of Bitcoin's monthly percentage gains/losses.
Fetches data from Yahoo Finance via yfinance.
"""

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
from pathlib import Path
import sys


def fetch_btc_data():
    """Fetch BTC-USD data from Yahoo Finance and calculate monthly returns."""
    print("Fetching BTC data from Yahoo Finance...")
    
    btc = yf.Ticker("BTC-USD")
    df = btc.history(period="max")
    
    if df.empty:
        raise ValueError("No data returned from Yahoo Finance")
    
    print(f"Raw data: {len(df)} rows, {df.index.min().date()} to {df.index.max().date()}")
    
    # Resample to month-end and get last close price of each month
    monthly = df['Close'].resample('ME').last()
    
    # Calculate percentage change month-over-month
    returns = monthly.pct_change() * 100
    
    # Convert to {year: {month: return}} format
    data = {}
    for date, ret in returns.items():
        if pd.notna(ret):
            year = date.year
            month = date.month
            if year not in data:
                data[year] = {}
            data[year][month] = round(ret, 2)
    
    print(f"Processed: {min(data.keys())} to {max(data.keys())}")
    return data


def create_heatmap(returns_data: dict, output_path: Path) -> None:
    """Create the monthly returns heatmap visualization."""
    
    # Get sorted years (ascending - oldest at top, newest at bottom)
    years = sorted(returns_data.keys())
    n_years = len(years)
    
    # Month labels
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Figure setup
    fig_height = max(6, n_years * 0.45 + 1.5)
    fig, ax = plt.subplots(figsize=(14, fig_height), facecolor='#0d1117')
    ax.set_facecolor('#0d1117')
    
    # Simple green/red colors with intensity based on magnitude
    def get_color(value):
        if value is None:
            return '#21262d'  # dark gray for no data
        
        intensity = min(abs(value) / 40, 1.0)  # cap intensity at 40%
        
        if value > 0:
            # Green: from muted to bright
            r = int(22 + (0 - 22) * intensity)
            g = int(27 + (200 - 27) * intensity)
            b = int(34 + (80 - 34) * intensity)
            return f'#{r:02x}{g:02x}{b:02x}'
        else:
            # Red: from muted to bright
            r = int(27 + (200 - 27) * intensity)
            g = int(22 + (40 - 22) * intensity)
            b = int(27 + (40 - 27) * intensity)
            return f'#{r:02x}{g:02x}{b:02x}'
    
    # Draw cells
    cell_gap = 0.08
    for i, year in enumerate(years):
        year_data = returns_data.get(year, {})
        
        for j in range(12):
            month = j + 1
            value = year_data.get(month)
            color = get_color(value)
            
            # Draw rectangle
            rect = mpatches.FancyBboxPatch(
                (j + cell_gap/2, i + cell_gap/2), 
                1 - cell_gap, 1 - cell_gap,
                boxstyle="round,pad=0.01,rounding_size=0.08",
                facecolor=color,
                edgecolor='#0d1117',
                linewidth=1
            )
            ax.add_patch(rect)
            
            # Add text
            if value is not None:
                sign = '+' if value > 0 else ''
                text_color = '#ffffff' if abs(value) > 10 else '#8b949e'
                
                if abs(value) >= 100:
                    display_val = f'{sign}{value:.0f}%'
                else:
                    display_val = f'{sign}{value:.1f}%'
                
                ax.text(j + 0.5, i + 0.5, display_val,
                       ha='center', va='center',
                       fontsize=9, fontweight='500',
                       color=text_color,
                       fontfamily='sans-serif')
    
    # Axis setup
    ax.set_xlim(0, 12)
    ax.set_ylim(0, n_years)
    
    # Month labels on top
    ax.set_xticks([i + 0.5 for i in range(12)])
    ax.set_xticklabels(month_labels, fontsize=10, fontweight='600', color='#8b949e')
    ax.xaxis.set_ticks_position('top')
    ax.xaxis.set_label_position('top')
    
    # Year labels on left
    ax.set_yticks([i + 0.5 for i in range(n_years)])
    ax.set_yticklabels(years, fontsize=10, fontweight='600', color='#8b949e')
    
    # Remove spines
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    ax.tick_params(length=0, pad=8)
    
    # Title
    current_date = datetime.now().strftime('%b %Y')
    
    ax.text(6, n_years + 0.8, 'BTC Monthly Returns',
            ha='center', va='bottom',
            fontsize=20, fontweight='700', color='#f0f6fc',
            fontfamily='sans-serif')
    
    ax.text(6, n_years + 0.35, f'Updated {current_date}',
            ha='center', va='bottom',
            fontsize=11, color='#8b949e',
            fontfamily='sans-serif')
    
    # Simple legend
    legend_y = -0.8
    ax.text(4.5, legend_y, '◼ Loss', ha='right', va='center', 
            fontsize=10, color='#c85050', fontweight='500')
    ax.text(7.5, legend_y, '◼ Gain', ha='left', va='center',
            fontsize=10, color='#3fb950', fontweight='500')
    
    # Adjust limits for title and legend
    ax.set_ylim(-1.2, n_years + 1.3)
    
    # Save
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='#0d1117', edgecolor='none', pad_inches=0.3)
    plt.close()
    
    print(f"Dashboard saved to: {output_path}")


def main():
    """Main execution."""
    now = datetime.now()
    month_year = now.strftime('%B-%Y').lower()
    
    # Determine output paths
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent.parent
    
    # Create output directory
    output_dir = project_root / 'outputs' / month_year
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / 'btc_monthly_returns.png'
    
    try:
        # Fetch data from Yahoo Finance
        returns_data = fetch_btc_data()
        
        years = sorted(returns_data.keys())
        print(f"Total years: {len(years)}")
        
        # Create visualization
        create_heatmap(returns_data, output_path)
        
        print(f"\n✓ Dashboard generated successfully")
        print(f"  Output: {output_path}")
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())