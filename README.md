# BTC Monthly Returns Dashboard

A simple visualization of Bitcoin's monthly percentage gains and losses since 2011.

## Latest Dashboard

![BTC Monthly Returns](outputs/february-2026/btc_monthly_returns.png)

## Structure

```
btc-monthly-returns/
├── src/
│   └── build_price_dashboard/
│       └── main.py          # Main script
├── outputs/
│   └── {month}-{year}/      # Monthly snapshots
│       └── btc_monthly_returns.png
├── .github/
│   └── workflows/
│       └── update-dashboard.yml
└── README.md
```

## How It Works

The script generates a heatmap showing:
- **Rows**: Years (newest at top)
- **Columns**: Months (Jan-Dec)
- **Colors**: Green = gains, Red = losses
- **Values**: Monthly percentage change

Data source: Yahoo Finance API (via yfinance) with embedded historical fallback.

## Run Locally

```bash
pip install matplotlib numpy yfinance pandas
python src/build_price_dashboard/main.py
```

## Automation

The dashboard updates automatically on the 1st of each month via GitHub Actions.
Updates only commit if the script runs successfully.

## Data Coverage

- **Start**: 2011 (first reliable exchange data)
- **End**: Current month
- **Source**: BTC-USD from Yahoo Finance

---

*Auto-updated monthly via GitHub Actions*
