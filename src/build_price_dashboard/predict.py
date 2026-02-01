
"""
BTC Monthly Return Predictor

Uses historical returns to predict current month's return using regression.
Features: lagged returns, moving averages, volatility, seasonality, momentum.
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from datetime import datetime


def build_features_df(returns_data: dict) -> pd.DataFrame:
    """
    Build a DataFrame with features for prediction.
    
    Features:
    - lag_1, lag_2, lag_3: Previous months' returns
    - ma_3, ma_6: Moving averages of returns
    - vol_3, vol_6: Rolling volatility (std dev)
    - month: Month of year (1-12) for seasonality
    - ytd_return: Year-to-date cumulative return
    - streak: Consecutive positive/negative months
    - momentum: Sign of ma_3 (1 if positive, -1 if negative)
    """
    
    # Flatten to list of (year, month, return)
    rows = []
    for year in sorted(returns_data.keys()):
        for month in range(1, 13):
            if month in returns_data[year]:
                rows.append({
                    'year': year,
                    'month': month,
                    'return': returns_data[year][month]
                })
    
    df = pd.DataFrame(rows)
    
    # Lagged returns
    df['lag_1'] = df['return'].shift(1)
    df['lag_2'] = df['return'].shift(2)
    df['lag_3'] = df['return'].shift(3)
    
    # Moving averages
    df['ma_3'] = df['return'].shift(1).rolling(3).mean()
    df['ma_6'] = df['return'].shift(1).rolling(6).mean()
    
    # Volatility
    df['vol_3'] = df['return'].shift(1).rolling(3).std()
    df['vol_6'] = df['return'].shift(1).rolling(6).std()
    
    # Momentum indicator
    df['momentum'] = (df['ma_3'] > 0).astype(int)
    
    # Streak: count consecutive positive or negative months
    def calc_streak(series):
        streaks = []
        current_streak = 0
        prev_sign = None
        for val in series:
            if pd.isna(val):
                streaks.append(0)
                continue
            sign = 1 if val > 0 else -1
            if prev_sign is None or sign == prev_sign:
                current_streak += sign
            else:
                current_streak = sign
            prev_sign = sign
            streaks.append(current_streak)
        # Shift by 1 since we want streak going into the month
        return [0] + streaks[:-1]
    
    df['streak'] = calc_streak(df['return'].tolist())
    
    # Year-to-date return (cumulative for the year so far)
    def calc_ytd(df):
        ytd = []
        for idx, row in df.iterrows():
            year_data = df[(df['year'] == row['year']) & (df.index < idx)]
            if len(year_data) == 0:
                ytd.append(0)
            else:
                # Compound return
                cumulative = ((1 + year_data['return']/100).prod() - 1) * 100
                ytd.append(cumulative)
        return ytd
    
    df['ytd_return'] = calc_ytd(df)
    
    # Month dummies for seasonality (use month directly, let model learn)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    
    return df


def train_model(df: pd.DataFrame):
    """
    Train Ridge regression model on historical data.
    Returns model, scaler, and feature columns.
    """
    
    feature_cols = [
        'lag_1', 'lag_2', 'lag_3',
        'ma_3', 'ma_6',
        'vol_3', 'vol_6',
        'momentum', 'streak', 'ytd_return',
        'month_sin', 'month_cos'
    ]
    
    # Drop rows with NaN features
    df_clean = df.dropna(subset=feature_cols + ['return'])
    
    if len(df_clean) < 20:
        raise ValueError("Not enough data to train model")
    
    X = df_clean[feature_cols].values
    y = df_clean['return'].values
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Ridge regression (handles multicollinearity, regularized)
    model = Ridge(alpha=1.0)
    model.fit(X_scaled, y)
    
    # Calculate R² on training data for reference
    train_score = model.score(X_scaled, y)
    print(f"Model R² on training data: {train_score:.3f}")
    
    return model, scaler, feature_cols


def predict_current_month(returns_data: dict) -> dict:
    """
    Predict the current month's return.
    
    Returns dict with:
    - year: current year
    - month: current month  
    - predicted_return: predicted % return
    - confidence: rough confidence indicator
    """
    
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    print(f"\nPredicting return for {current_year}-{current_month:02d}...")
    
    # Build features from historical data
    df = build_features_df(returns_data)
    
    # Train model
    model, scaler, feature_cols = train_model(df)
    
    # Build features for current month
    # We need the most recent data to calculate lagged features
    recent = df.tail(6).copy()
    
    # Current month features
    lag_1 = recent['return'].iloc[-1] if len(recent) >= 1 else 0
    lag_2 = recent['return'].iloc[-2] if len(recent) >= 2 else 0
    lag_3 = recent['return'].iloc[-3] if len(recent) >= 3 else 0
    
    ma_3 = recent['return'].tail(3).mean()
    ma_6 = recent['return'].tail(6).mean()
    
    vol_3 = recent['return'].tail(3).std()
    vol_6 = recent['return'].tail(6).std()
    
    momentum = 1 if ma_3 > 0 else 0
    
    # Streak calculation
    streak = 0
    for val in reversed(recent['return'].tolist()):
        sign = 1 if val > 0 else -1
        if streak == 0:
            streak = sign
        elif (streak > 0 and val > 0) or (streak < 0 and val < 0):
            streak += sign
        else:
            break
    
    # YTD return
    year_data = df[df['year'] == current_year]
    if len(year_data) > 0:
        ytd_return = ((1 + year_data['return']/100).prod() - 1) * 100
    else:
        ytd_return = 0
    
    # Seasonality
    month_sin = np.sin(2 * np.pi * current_month / 12)
    month_cos = np.cos(2 * np.pi * current_month / 12)
    
    # Create feature vector
    X_pred = np.array([[
        lag_1, lag_2, lag_3,
        ma_3, ma_6,
        vol_3, vol_6,
        momentum, streak, ytd_return,
        month_sin, month_cos
    ]])
    
    X_pred_scaled = scaler.transform(X_pred)
    predicted_return = model.predict(X_pred_scaled)[0]
    
    # Clip extreme predictions
    predicted_return = np.clip(predicted_return, -50, 50)
    
    # Simple confidence based on recent volatility
    # Lower vol = higher confidence
    confidence = 'low'
    if vol_3 < 15:
        confidence = 'medium'
    if vol_3 < 10:
        confidence = 'high'
    
    print(f"Predicted return: {predicted_return:+.1f}%")
    print(f"Confidence: {confidence}")
    print(f"Recent volatility (3m): {vol_3:.1f}%")
    
    return {
        'year': current_year,
        'month': current_month,
        'predicted_return': round(predicted_return, 2),
        'confidence': confidence
    }


if __name__ == '__main__':
    import yfinance as yf
    
    # Fetch real data
    print("Fetching BTC data from Yahoo Finance...")
    btc = yf.Ticker("BTC-USD")
    df = btc.history(period="max")
    
    monthly = df['Close'].resample('ME').last()
    returns = monthly.pct_change() * 100
    
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    data = {}
    for date, ret in returns.items():
        if pd.notna(ret):
            year = date.year
            month = date.month
            if year == current_year and month == current_month:
                continue
            if year not in data:
                data[year] = {}
            data[year][month] = round(ret, 2)
    
    print(f"Data range: {min(data.keys())} to {max(data.keys())}")
    
    result = predict_current_month(data)
    print(f"\nResult: {result}")