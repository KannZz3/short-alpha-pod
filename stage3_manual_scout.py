import json
import pandas as pd
import os
from datetime import datetime, timedelta

def run_manual_scout(ticker="TSLA"):
    peaks_file = f"./artifacts/peaks_{ticker}.json"
    with open(peaks_file, 'r') as f:
        peaks_data = json.load(f)
    
    all_retail_items = []
    
    # Historical Mock Data for the 3 peaks
    # Peak 1: 2021-01-11 (Musk Richest Person)
    # Peak 2: 2021-11-02 (Trillion Dollar Cap / Hertz)
    # Peak 3: 2021-01-13 (Musk Euphoria continues)
    
    historical_scenarios = {
        "2021-01-11": [
            {"platform": "reddit", "title": "TSLA to the moon! Elon is the world's richest man now 🚀", "hype": 0.9, "polarity": 0.8, "tag": "meme"},
            {"platform": "x", "title": "$TSLA Short Squeeze is just beginning. Don't bet against Musk.", "hype": 0.85, "polarity": 0.5, "tag": "regulatory"},
            {"platform": "blog", "title": "Tesla's Retail Army: Why the standard valuation models are broken", "hype": 0.7, "polarity": 0.3, "tag": "report"}
        ],
        "2021-11-02": [
            {"platform": "reddit", "title": "Hertz order is a game changer. Gamma squeeze incoming on $TSLA!", "hype": 1.0, "polarity": 0.9, "tag": "meme"},
            {"platform": "x", "title": "Tesla joins the $1 Trillion club. The shorts are absolutely incinerated.", "hype": 0.95, "polarity": 0.7, "tag": "lawsuit", "black_swan": True},
            {"platform": "reddit", "title": "Gain porn: $50k to $1.2M on TSLA weekly calls", "hype": 1.0, "polarity": 1.0, "tag": "meme"}
        ],
        "2021-01-13": [
            {"platform": "x", "title": "Institutional money finally catching up to the retail conviction on $TSLA", "hype": 0.8, "polarity": 0.4, "tag": "report"},
            {"platform": "reddit", "title": "Who else is still holding? Short interest still high despite the rally.", "hype": 0.85, "polarity": 0.6, "tag": "product"}
        ]
    }
    
    for peak_date_str, items in historical_scenarios.items():
        peak_date = datetime.strptime(peak_date_str, '%Y-%m-%d')
        for i, item in enumerate(items):
            # Jitter dates within window
            offset = i - 1
            item_date = (peak_date + timedelta(days=offset)).strftime('%Y-%m-%d')
            all_retail_items.append({
                "date": item_date,
                "platform": item['platform'],
                "query": f"{ticker} short squeeze",
                "url": f"https://{item['platform']}.com/demo/item_{i}",
                "snippet": f"[DEMO] {item['title']}",
                "hype": item['hype'],
                "velocity": round(item['hype'] * 1.2, 2), # NEW: rate of hype change
                "polarity": item['polarity'],
                "black_swan": item.get('black_swan', False),
                "tag": item['tag']
            })
            
    # Save retail_evidence.json
    retail_evidence = {
        "ticker": ticker,
        "items": all_retail_items
    }
    
    os.makedirs("./artifacts", exist_ok=True)
    with open(f"./artifacts/retail_evidence_{ticker}.json", 'w') as f:
        json.dump(retail_evidence, f, indent=2)
        
    # Generate retail_daily.csv
    retail_df = pd.DataFrame(all_retail_items)
    if not retail_df.empty:
        daily_summary = retail_df.groupby('date').agg({
            'hype': ['count', 'mean'],
            'black_swan': 'max'
        }).reset_index()
        daily_summary.columns = ['date', 'retail_chatter_volume', 'retail_hype_index', 'retail_black_swan']
        # Convert black_swan to int
        daily_summary['retail_black_swan'] = daily_summary['retail_black_swan'].astype(int)
    else:
        daily_summary = pd.DataFrame(columns=['date', 'retail_chatter_volume', 'retail_hype_index', 'retail_black_swan'])
        
    daily_summary.to_csv(f"./artifacts/retail_daily_{ticker}.csv", index=False)
    print(f"Saved retail artifacts for {ticker} (DEMO MODE)")

if __name__ == "__main__":
    run_manual_scout("TSLA")
