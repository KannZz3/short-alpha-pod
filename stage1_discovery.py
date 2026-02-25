import pandas as pd
import json
import os

def run_discovery(ticker="TSLA"):
    csv_path = "./data/Stock Short Interest Data.csv"
    if not os.path.exists(csv_path):
        # Try finding it in current directory if subpath fails
        csv_path = "Stock Short Interest Data.csv"
    
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Filter for target ticker
    df_ticker = df[df['Ticker'] == ticker].copy()
    
    # Convert dates
    df_ticker['date_dt'] = pd.to_datetime(df_ticker['Business Date'])
    df_ticker = df_ticker.sort_values('date_dt')
    
    # Map columns to internal schema
    # Business Date,Ticker,ShortInterestPct,Crowded Score,Squeeze Score,S3Utilization,Last Rate
    internal_df = df_ticker[[
        'Business Date', 'ShortInterestPct', 'Crowded Score', 
        'Squeeze Score', 'S3Utilization', 'Last Rate'
    ]].copy()
    
    internal_df.columns = [
        'date', 'short_interest_pct', 'crowded_score', 
        'squeeze_score', 'utilization', 'borrow_cost'
    ]
    
    # Sort by squeeze score
    top_peaks = internal_df.sort_values('squeeze_score', ascending=False).head(3)
    
    # NEW: Volatility Regime Calculation
    # Calculate daily returns volatility over a trailing window
    internal_df['returns'] = internal_df['squeeze_score'].pct_change()
    global_vol = internal_df['returns'].std()
    
    peaks_list = []
    for i, (idx, row) in enumerate(top_peaks.iterrows()):
        # Local vol check (simple window around peak)
        window = internal_df.iloc[max(0, idx-5):min(len(internal_df), idx+5)]
        local_vol = window['returns'].std()
        regime = "NORMAL"
        if local_vol > global_vol * 1.5: regime = "HIGH"
        elif local_vol < global_vol * 0.5: regime = "LOW"

        peaks_list.append({
            "rank": i + 1,
            "date": pd.to_datetime(row['date']).strftime('%Y-%m-%d'),
            "squeeze_score": float(row['squeeze_score']),
            "crowded_score": float(row['crowded_score']),
            "volatility_regime": regime
        })
        
    peaks_output = {
        "ticker": ticker,
        "peaks": peaks_list,
        "date_range": {
            "min": df_ticker['date_dt'].min().strftime('%Y-%m-%d'),
            "max": df_ticker['date_dt'].max().strftime('%Y-%m-%d')
        }
    }
    
    # Create artifacts directory
    os.makedirs("./artifacts", exist_ok=True)
    
    # Save peaks.json
    peaks_file = f"./artifacts/peaks_{ticker}.json"
    with open(peaks_file, 'w') as f:
        json.dump(peaks_output, f, indent=2)
    print(f"Saved {peaks_file}")
    
    # Save daily features csv
    features_file = f"./artifacts/daily_features_{ticker}.csv"
    internal_df.to_csv(features_file, index=False)
    print(f"Saved {features_file}")
    
    return peaks_output

if __name__ == "__main__":
    run_discovery("TSLA")
