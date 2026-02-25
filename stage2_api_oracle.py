import os
import json
import pandas as pd
import requests
from datetime import datetime, timedelta

# Simple rule-based sentiment since we might not have a transformer available
def get_sentiment(text):
    positive_words = {'bullish', 'surge', 'growth', 'gain', 'innovation', 'profit', 'record', 'delivery', 'squeeze'}
    negative_words = {'bearish', 'crash', 'loss', 'short', 'fraud', 'investigation', 'lawsuit', 'drop', 'decline'}
    
    text = text.lower()
    score = 0
    for word in positive_words:
        if word in text: score += 0.2
    for word in negative_words:
        if word in text: score -= 0.2
    return max(-1.0, min(1.0, score))

def run_api_oracle(ticker="TSLA"):
    peaks_file = f"./artifacts/peaks_{ticker}.json"
    with open(peaks_file, 'r') as f:
        peaks_data = json.load(f)
    
    api_key = os.environ.get("NEWSAPI_KEY")
    is_demo = api_key is None or api_key == ""
    
    all_news_items = []
    
    for peak in peaks_data['peaks']:
        target_date = datetime.strptime(peak['date'], '%Y-%m-%d')
        start_date = (target_date - timedelta(days=3)).strftime('%Y-%m-%d')
        end_date = (target_date + timedelta(days=3)).strftime('%Y-%m-%d')
        
        print(f"Fetching news for {ticker} window: {start_date} to {end_date}...")
        
        if is_demo:
            # Generate mock headlines
            mock_templates = [
                {"source": "Institutional Investor", "title": f"{ticker} Squeeze Warning: Short Interest at Peak Levels"},
                {"source": "Wall St Journal", "title": f"How {ticker}'s Recent Rally is implementation of institutional strategies"},
                {"source": "Bloomberg", "title": f"{ticker} Delivery Numbers exceed expectations, pushing shorts to cover"},
                {"source": "Financial Times", "title": f"Analyzing the {ticker} Crowded Trade: Risks and Rewards"},
                {"source": "Reuters", "title": f"Short Sellers face massive losses as {ticker} shares climb"},
                {"source": "Forbes", "title": f"Why {ticker} is the ultimate battleground stock for bulls and bears"}
            ]
            for i, template in enumerate(mock_templates):
                # Distribute across the 7-day window
                pub_date = (target_date - timedelta(days=3) + timedelta(days=i)).strftime('%Y-%m-%d')
                all_news_items.append({
                    "published_at": f"{pub_date}T12:00:00Z",
                    "date": pub_date,
                    "source": f"{template['source']} [DEMO]",
                    "title": template['title'],
                    "url": "https://newsapi.org/demo",
                    "sentiment": get_sentiment(template['title'])
                })
        else:
            # REAL MODE
            # --- MANDATORY NEWSAPI SNIPPET ---
            url = f"https://newsapi.org/v2/everything?q={ticker}&from={start_date}&to={end_date}&sortBy=relevancy&apiKey={api_key}"
            response = requests.get(url)
            if response.status_code == 200:
                articles = response.json().get('articles', [])
                for art in articles[:10]: # Top 10 per peak
                    pub_dt = art['publishedAt'][:10]
                    all_news_items.append({
                        "published_at": art['publishedAt'],
                        "date": pub_dt,
                        "source": art['source']['name'],
                        "title": art['title'],
                        "url": art['url'],
                        "sentiment": get_sentiment(art['title'])
                    })
            else:
                print(f"API Error: {response.status_code}")
    
    # Save news_items.json
    news_items_output = {
        "ticker": ticker,
        "items": all_news_items
    }
    
    os.makedirs("./artifacts", exist_ok=True)
    with open(f"./artifacts/news_items_{ticker}.json", 'w') as f:
        json.dump(news_items_output, f, indent=2)
    
    # Generate news_daily.csv
    # Calculate daily volume and avg sentiment
    news_df = pd.DataFrame(all_news_items)
    if not news_df.empty:
        daily_summary = news_df.groupby('date').agg({
            'title': 'count',
            'sentiment': 'mean'
        }).reset_index()
        daily_summary.columns = ['date', 'news_volume', 'news_sentiment_index']
    else:
        daily_summary = pd.DataFrame(columns=['date', 'news_volume', 'news_sentiment_index'])
    
    daily_summary.to_csv(f"./artifacts/news_daily_{ticker}.csv", index=False)
    print(f"Saved news artifacts for {ticker}")

if __name__ == "__main__":
    run_api_oracle("TSLA")
