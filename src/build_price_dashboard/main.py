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

from predict import predict_current_month


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
    
    # Get current year/month to exclude incomplete data
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Convert to {year: {month: return}} format
    data = {}
    for date, ret in returns.items():
        if pd.notna(ret):
            year = date.year
            month = date.month
            # Skip current incomplete month
            if year == current_year and month == current_month:
                continue
            if year not in data:
                data[year] = {}
            data[year][month] = round(ret, 2)
    
    print(f"Processed: {min(data.keys())} to {max(data.keys())}")
    return data


def create_heatmap(returns_data: dict, output_path: Path, prediction: dict = None) -> None:
    """Create the monthly returns heatmap visualization."""
    
    # Get sorted years (ascending - oldest at top, newest at bottom)
    years = sorted(returns_data.keys())
    
    # If prediction exists, ensure that year is included
    if prediction:
        pred_year = prediction['year']
        if pred_year not in years:
            years.append(pred_year)
            returns_data[pred_year] = {}
        years = sorted(years)
    
    n_years = len(years)
    
    # Month labels
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Calculate monthly averages (excluding prediction)
    monthly_avgs = {}
    for month in range(1, 13):
        values = [returns_data[y].get(month) for y in years if returns_data[y].get(month) is not None]
        if values:
            monthly_avgs[month] = sum(values) / len(values)
    
    # Figure setup (extra row for averages)
    fig_height = max(6, (n_years + 1) * 0.45 + 1.5)
    fig, ax = plt.subplots(figsize=(14, fig_height), facecolor='#0d1117')
    ax.set_facecolor('#0d1117')
    
    # Simple green/red colors with intensity based on magnitude
    def get_color(value):
        if value is None:
            return '#21262d'
        
        intensity = min(abs(value) / 40, 1.0)
        
        if value > 0:
            r = int(22 + (0 - 22) * intensity)
            g = int(27 + (200 - 27) * intensity)
            b = int(34 + (80 - 34) * intensity)
            return f'#{r:02x}{g:02x}{b:02x}'
        else:
            r = int(27 + (200 - 27) * intensity)
            g = int(22 + (40 - 22) * intensity)
            b = int(27 + (40 - 27) * intensity)
            return f'#{r:02x}{g:02x}{b:02x}'
    
    cell_gap = 0.08
    
    # Draw year rows
    for i, year in enumerate(years):
        year_data = returns_data.get(year, {})
        row_y = i + 1  # offset by 1 for averages row at bottom
        
        for j in range(12):
            month = j + 1
            value = year_data.get(month)
            
            # Check if this is the prediction cell
            is_prediction = (prediction and 
                           year == prediction['year'] and 
                           month == prediction['month'])
            
            if is_prediction:
                value = prediction['predicted_return']
            
            color = get_color(value)
            
            # Different style for prediction cell
            if is_prediction:
                rect = mpatches.FancyBboxPatch(
                    (j + cell_gap/2, row_y + cell_gap/2), 
                    1 - cell_gap, 1 - cell_gap,
                    boxstyle="round,pad=0.01,rounding_size=0.08",
                    facecolor=color,
                    edgecolor='#f0f6fc',
                    linewidth=2,
                    linestyle='--'
                )
            else:
                rect = mpatches.FancyBboxPatch(
                    (j + cell_gap/2, row_y + cell_gap/2), 
                    1 - cell_gap, 1 - cell_gap,
                    boxstyle="round,pad=0.01,rounding_size=0.08",
                    facecolor=color,
                    edgecolor='#0d1117',
                    linewidth=1
                )
            ax.add_patch(rect)
            
            if value is not None:
                sign = '+' if value > 0 else ''
                text_color = '#ffffff' if abs(value) > 10 else '#8b949e'
                
                if abs(value) >= 100:
                    display_val = f'{sign}{value:.0f}%'
                else:
                    display_val = f'{sign}{value:.1f}%'
                
                # Add asterisk for prediction
                if is_prediction:
                    display_val += '*'
                
                ax.text(j + 0.5, row_y + 0.5, display_val,
                       ha='center', va='center',
                       fontsize=9, fontweight='500',
                       color=text_color,
                       fontfamily='sans-serif')
    
    # Draw averages row at bottom (row 0)
    for j in range(12):
        month = j + 1
        value = monthly_avgs.get(month)
        color = get_color(value)
        
        rect = mpatches.FancyBboxPatch(
            (j + cell_gap/2, cell_gap/2), 
            1 - cell_gap, 1 - cell_gap,
            boxstyle="round,pad=0.01,rounding_size=0.08",
            facecolor=color,
            edgecolor='#0d1117',
            linewidth=1
        )
        ax.add_patch(rect)
        
        if value is not None:
            sign = '+' if value > 0 else ''
            text_color = '#ffffff' if abs(value) > 10 else '#8b949e'
            display_val = f'{sign}{value:.1f}%'
            
            ax.text(j + 0.5, 0.5, display_val,
                   ha='center', va='center',
                   fontsize=9, fontweight='500',
                   color=text_color,
                   fontfamily='sans-serif')
    
    # Axis setup
    ax.set_xlim(0, 12)
    ax.set_ylim(0, n_years + 1)
    
    # Year labels on left (with Avg at bottom)
    ax.set_yticks([i + 0.5 for i in range(n_years + 1)])
    ax.set_yticklabels(['Avg'] + years, fontsize=10, fontweight='600', color='#8b949e')
    
    # Remove spines
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    ax.tick_params(length=0, pad=8)
    ax.set_xticks([])
    
    # Title at top (more spacing)
    ax.text(6, n_years + 2.0, 'BTC Monthly Returns',
            ha='center', va='bottom',
            fontsize=22, fontweight='700', color='#f0f6fc',
            fontfamily='sans-serif')
    
    # Month labels below title (with proper gap)
    for j, label in enumerate(month_labels):
        ax.text(j + 0.5, n_years + 1.35, label,
               ha='center', va='bottom',
               fontsize=10, fontweight='600', color='#8b949e',
               fontfamily='sans-serif')
    
    # Prediction footer
    if prediction:
        ax.text(6, -0.7, '* Current month prediction based on lagged returns, momentum & seasonality signals',
               ha='center', va='top',
               fontsize=9, color='#6e7681', style='italic',
               fontfamily='sans-serif')
    
    # Adjust limits
    ax.set_ylim(-1.1, n_years + 2.6)
    
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
        
        # Generate prediction for current month
        prediction = None
        try:
            prediction = predict_current_month(returns_data)
        except Exception as e:
            print(f"Warning: Could not generate prediction: {e}")
        
        # Create visualization
        create_heatmap(returns_data, output_path, prediction)
        
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