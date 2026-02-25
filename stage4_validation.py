import pandas as pd
import json
import numpy as np
import os

def z_score(series):
    if series.std() == 0: return series * 0
    return (series - series.mean()) / series.std()

def run_validation(ticker="TSLA"):
    # Load all daily artifacts
    features_df = pd.read_csv(f"./artifacts/daily_features_{ticker}.csv")
    news_df = pd.read_csv(f"./artifacts/news_daily_{ticker}.csv")
    retail_df = pd.read_csv(f"./artifacts/retail_daily_{ticker}.csv")
    
    # Ensure date is standard YYYY-MM-DD
    features_df['date'] = pd.to_datetime(features_df['date']).dt.strftime('%Y-%m-%d')
    news_df['date'] = pd.to_datetime(news_df['date']).dt.strftime('%Y-%m-%d')
    retail_df['date'] = pd.to_datetime(retail_df['date']).dt.strftime('%Y-%m-%d')
    
    # Merge
    merged = features_df.merge(news_df, on='date', how='left').merge(retail_df, on='date', how='left')
    
    # Fill NAs
    merged['news_volume'] = merged['news_volume'].fillna(0)
    merged['news_sentiment_index'] = merged['news_sentiment_index'].fillna(0)
    merged['retail_chatter_volume'] = merged['retail_chatter_volume'].fillna(0)
    merged['retail_hype_index'] = merged['retail_hype_index'].fillna(0)
    merged['retail_black_swan'] = merged['retail_black_swan'].fillna(0)
    
    # Noise Index components (stage 4 goal)
    # Weights: News Vol (15%), News Sent (15%), Retail Vol (25%), Retail Hype (25%), Utilization (20%)
    w1, w2, w3, w4, w5 = 0.15, 0.15, 0.25, 0.25, 0.20
    
    merged['z_news_vol'] = z_score(merged['news_volume'])
    merged['z_news_sent'] = z_score(merged['news_sentiment_index'].abs())
    merged['z_retail_vol'] = z_score(merged['retail_chatter_volume'])
    merged['z_retail_hype'] = z_score(merged['retail_hype_index'].abs())
    merged['z_util'] = z_score(merged['utilization'])
    
    merged['noise_index'] = (
        merged['z_news_vol'] * w1 + 
        merged['z_news_sent'] * w2 + 
        merged['z_retail_vol'] * w3 + 
        merged['z_retail_hype'] * w4 + 
        merged['z_util'] * w5 +
        merged['retail_black_swan'] * 2.0 # Black Swan boost
    )
    
    # NEW: Interpret result for Interpretation string
    final_z = merged['noise_index'].mean()
    interpret_prefix = "High-Crowding" if final_z > 1.0 else "Normal"
    
    # Shift for 48h lag test (2 steps assuming daily data)
    # delta_SI_48h(t) = SI(t+2) - SI(t)
    # We want to see if Noise Index(t) correlates with changes in the future
    merged = merged.sort_values('date')
    merged['delta_SI_48h'] = merged['short_interest_pct'].shift(-2) - merged['short_interest_pct']
    merged['delta_crowded_48h'] = merged['crowded_score'].shift(-2) - merged['crowded_score']
    
    # Evaluation
    valid_subset = merged.dropna(subset=['delta_SI_48h', 'delta_crowded_48h'])
    
    corr_noise_crowded = float(valid_subset[['noise_index', 'crowded_score']].corr().iloc[0,1])
    corr_noise_squeeze = float(valid_subset[['noise_index', 'squeeze_score']].corr().iloc[0,1])
    
    corr_noise_delta_SI = float(valid_subset[['noise_index', 'delta_SI_48h']].corr().iloc[0,1])
    corr_noise_delta_crowded = float(valid_subset[['noise_index', 'delta_crowded_48h']].corr().iloc[0,1])
    
    supports_hypothesis = corr_noise_delta_SI > 0.1 or corr_noise_delta_crowded > 0.1
    
    validation_output = {
        "ticker": ticker,
        "same_day": {
            "corr_noise_crowded": round(corr_noise_crowded, 4),
            "corr_noise_squeeze": round(corr_noise_squeeze, 4)
        },
        "lag_48h": {
            "corr_noise_to_delta_SI_48h": round(corr_noise_delta_SI, 4),
            "corr_noise_to_delta_crowded_48h": round(corr_noise_delta_crowded, 4)
        },
        "interpretation": f"The combined Noise Index shows a {'positive' if supports_hypothesis else 'weak'} leading correlation with future short interest changes.",
        "supports_hypothesis": supports_hypothesis
    }
    
    # Save artifacts
    with open(f"./artifacts/validation_{ticker}.json", 'w') as f:
        json.dump(validation_output, f, indent=2)
        
    merged.to_csv(f"./artifacts/merged_daily_{ticker}.csv", index=False)
    print(f"Saved validation artifacts for {ticker}")

if __name__ == "__main__":
    run_validation("TSLA")
