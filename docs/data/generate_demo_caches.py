import csv
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta

# Focus Tickers
FOCUS_TICKERS = ["AFRM", "SQ", "PYPL", "SHOP", "TSLA"]
CSV_PATH = "data/Stock Short Interest Data.csv"

news_cache = []
retail_cache = []

# Institutional Providers & Themes
PROVIDERS = ["Bloomberg", "Reuters", "WSJ", "Seeking Alpha", "MarketWatch", "CNBC", "Financial Times", "Barron's", "Investor's Business Daily", "Forbes", "Fortune", "Economist"]
THEMES = ["macro", "earnings", "regulatory", "options", "flow", "short-interest", "liquidity", "m&a", "litigation", "guidance"]

# Retail Platforms
PLATFORMS = ["reddit", "twitter", "stocktwits", "discord", "tiktok", "youtube", "webull", "fintwit", "whatsapp", "telegram"]

# Content Pools - Expanded for diversity and better dedupe testing
NEWS_TITLES = [
    "Institutional focus on {ticker} amid changing market regime",
    "{ticker} sees unusual options activity ahead of earnings",
    "Why {ticker} surged today on massive volume",
    "Hedge funds quietly accumulating {ticker} shares",
    "Analyst upgrades {ticker} citing strong fundamentals",
    "Short interest in {ticker} hits new multi-year high",
    "Market movers: {ticker} leads the sector rally",
    "Is a short squeeze imminent for {ticker}?",
    "{ticker} options market implies massive volatility incoming",
    "Exclusive: Inside the institutional shift towards {ticker}",
    "New regulatory filing reveals major {ticker} stake",
    "Fed policy shift impacts {ticker} valuation models",
    "Brokerage houses raise margin requirements for {ticker}",
    "{ticker} leadership outlines aggressive growth strategy",
    "Supply chain improvements boost {ticker} outlook",
    "{ticker} partnership announcement triggers price action",
    "Technical analysis: {ticker} breaks out of long-term base",
    "Insider buying activity detected in {ticker} executive suite",
    "Global macro trends favor {ticker} revenue growth",
    "Comparing {ticker} performance to sector peers"
]

NEWS_EXCERPTS = [
    "Volume spike detected in {ticker} options chain. Analysts upgrade price target.",
    "Major block trades reported for {ticker} just before market close. Bullish sentiment is growing.",
    "Dark pool data suggests heavy institutional accumulation of {ticker} over the last 48 hours.",
    "The cost to borrow {ticker} shares has skyrocketed, putting pressure on existing short sellers.",
    "A new research report highlights {ticker}'s dominant market position and future growth potential.",
    "Algorithmic trading desks have flipped net long on {ticker} following the recent macro data release.",
    "Despite broader market weakness, {ticker} maintained critical support levels with strong buying.",
    "Options flow shows heavy call buying for {ticker}, indicating expectations of a near-term breakout.",
    "Quarterly results exceeded expectations across all key metrics for {ticker}.",
    "New management team at {ticker} focus on efficiency and margin expansion.",
    "The SEC is reviewing recent disclosures related to {ticker}'s offshore operations.",
    "Regional banks increase exposure to {ticker} debt instruments.",
    "Consumer sentiment data points to increased demand for {ticker} core products.",
    "Competitor weakness provides tailwinds for {ticker} market share gains.",
    "Revised revenue guidance for {ticker} suggests accelerating growth in Q3.",
    "Patent approval for {ticker} strengthens competitive moat in the AI space.",
    "Consolidation pattern in {ticker} suggests a major move is imminent.",
    "Institutional surveys show {ticker} remains a top-tier pick for large-cap growth.",
    "Energy prices drop, significantly lowering operational overhead for {ticker}.",
    "Sovereign wealth funds rumored to be looking at {ticker} for long-term diversification."
]

RETAIL_TITLES = [
    "Retail chatter on {ticker}",
    "Ape Army assembling for {ticker}",
    "Massive DD drop on {ticker}",
    "Why I'm YOLOing into {ticker} tomorrow",
    "{ticker} to the mooooon 🚀🚀",
    "Is {ticker} the next big squeeze?",
    "Check out this {ticker} chart setup",
    "Everyone is sleeping on {ticker}",
    "{ticker} price target: $1000 or bust!",
    "Shorts are absolute toast in {ticker}",
    "Buying the dip in {ticker} like a boss",
    "{ticker} diamond hands required for this play",
    "The level of manipulation in {ticker} is insane",
    "{ticker} is the only stock that matters right now",
    "Just loaded another 100 shares of {ticker}",
    "Who is still holding {ticker} with me?",
    "My wife's boyfriend says {ticker} is a buy",
    "{ticker} technicals are looking juicy",
    "Stop selling {ticker} you paper handed cowards",
    "This {ticker} squeeze will be legendary"
]

RETAIL_EXCERPTS = [
    "🚀 To the moon! $ {ticker} is primed for a massive move. Check out this DD.",
    "Just bought more $ {ticker}. The short interest here is insane. They have to cover eventually.",
    "I've been watching $ {ticker} for weeks. The chart looks like a coiled spring ready to snap.",
    "Don't let them easily shake you out of $ {ticker}. Diamond hands! 💎🙌",
    "Look at the volume on $ {ticker} today! Retail is waking up to this play.",
    "This is literally a textbook flag on $ {ticker}. Breakout is imminent.",
    "Shorts are trapped in $ {ticker}. We own the float. Hold the line!",
    "Can't believe how cheap $ {ticker} is right now. Loading up the boat before the rip.",
    "If {ticker} hits $500 I'm buying everyone a pizza. Let's go!",
    "Look at the borrow fee on {ticker}. It's over 100%! Ticking time bomb.",
    "The media is lying about {ticker}. Use your own eyes and look at the order book.",
    "Just sold my car to buy more {ticker}. Maximum conviction.",
    "The shorts haven't covered! Look at the FTD data for {ticker}.",
    "Is it just me or is {ticker} about to explode? The setup is perfect.",
    "I don't care about the price, I'm just here for the {ticker} squeeze.",
    "Whales are buying {ticker} at these levels. Follow the smart money.",
    "My cat walked across my keyboard and bought {ticker}. It's a sign from the universe.",
    "There is zero resistance above current {ticker} prices. Blue skies ahead.",
    "Remember why we are here. {ticker} is more than just a stock.",
    "I'm not leaving. {ticker} or nothing. See you at the top!"
]


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%m/%d/%Y")
        except ValueError:
            try:
                return datetime.strptime(date_str, "%m/%d/%y")
            except:
                return None


# Intentional Flaw Generators
def generate_news_item(ticker, dt_str, sq_score, idx, force_duplicate=False, last_title=None, last_excerpt=None):
    provider = random.choice(PROVIDERS)
    tag = random.choice(THEMES)

    if force_duplicate and last_title and last_excerpt:
        title = last_title
        excerpt = last_excerpt
    else:
        title = random.choice(NEWS_TITLES).format(ticker=ticker)
        excerpt = random.choice(NEWS_EXCERPTS).format(ticker=ticker)

    url = f"https://{provider.lower().replace(' ', '')}.com/articles/{ticker.lower()}-{dt_str}-{idx}" if random.random() > 0.05 else "" # 5% missing URL
    if not url and random.random() > 0.5:
        url = f"https://placeholder.com/{ticker.lower()}-{idx}" # Placeholder URL

    sentiment = random.uniform(-1, 1) if sq_score > 50 else random.uniform(-0.5, 0.5)

    # Introduce random time offsets within the day
    hour = random.randint(6, 20)
    minute = random.randint(0, 59)
    pub_time = f"{dt_str}T{hour:02d}:{minute:02d}:00Z"

    raw_key = f"{ticker}|{dt_str}|inst_{idx}"

    return {
        "id": f"news-{ticker}-{dt_str}-{idx}",
        "ticker": ticker,
        "source_type": "institutional",
        "provider": provider,
        "title": title,
        "url": url,
        "published_at_utc": pub_time,
        "retrieved_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:00:00Z"),
        "excerpt": excerpt,
        "tags": [tag],
        "metrics": {
            "sentiment": sentiment,
            "shock": random.uniform(0, 10),
            "engagement": random.randint(100, 5000),
            "volume": random.randint(10, 100)
        },
        "quality_flags": ["PLACEHOLDER_URL"] if "placeholder" in url else [],
        "mode": "DEMO",
        "raw_ref": { "cache": "news_demo_cache", "key": raw_key }
    }


def generate_retail_item(ticker, dt_str, i, idx, force_duplicate=False, last_excerpt=None):
    platform = random.choice(PLATFORMS)
    tag = random.choice(["yolo", "shorts", "squeeze_watch", "options_flow", "diamond_hands", "fundamentals"])

    if force_duplicate and last_excerpt:
        excerpt = last_excerpt
    else:
        excerpt = random.choice(RETAIL_EXCERPTS).format(ticker=ticker)

    title = random.choice(RETAIL_TITLES).format(ticker=ticker)
    url = f"https://{platform}.com/post/{ticker.lower()}-{dt_str}-{idx}" if random.random() > 0.05 else ""
    if not url and random.random() > 0.5:
        url = f"https://placeholder-social.com/{ticker.lower()}-{idx}"

    hype = random.uniform(0.5, 1.0) if abs(i) < 3 else random.uniform(0.1, 0.6)

    # Introduce random time offsets within the day
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    pub_time = f"{dt_str}T{hour:02d}:{minute:02d}:00Z"

    raw_key = f"{ticker}|{dt_str}|ret_{idx}"

    return {
        "id": f"retail-{ticker}-{dt_str}-{idx}",
        "ticker": ticker,
        "source_type": "retail",
        "provider": platform,
        "title": title,
        "url": url,
        "published_at_utc": pub_time,
        "retrieved_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:00:00Z"),
        "excerpt": excerpt,
        "tags": [tag],
        "metrics": {
            "sentiment": random.uniform(0.2, 1.0),
            "shock": 0,
            "engagement": random.randint(1000, 50000),
            "volume": random.randint(50, 500)
        },
        "quality_flags": ["PLACEHOLDER_URL"] if "placeholder" in url else [],
        "mode": "DEMO",
        "raw_ref": { "cache": "retail_demo_cache", "key": raw_key }
    }


def main():
    try:
        with open(CSV_PATH, 'r') as f:
            reader = csv.DictReader(f)
            data = [row for row in reader if row.get("Ticker") in FOCUS_TICKERS]
    except FileNotFoundError:
        print(f"Error: {CSV_PATH} not found.")
        return

    # Group by ticker
    ticker_data = defaultdict(list)
    for row in data:
        dt = parse_date(row.get("Business Date"))
        sq_score_val = row.get("Squeeze Score")
        sq_score = float(sq_score_val) if sq_score_val and sq_score_val.strip() else 0.0
        ticker = row.get("Ticker")
        if dt and ticker:
            ticker_data[ticker].append({'date': dt, 'squeeze_score': sq_score, 'raw': row})

    for ticker, rows in ticker_data.items():
        # Sort by Squeeze Score descending to find true peaks
        rows.sort(key=lambda x: x['squeeze_score'], reverse=True)
        
        peaks = []
        for row in rows:
            if len(peaks) >= 3:
                break
            # Dedupe logic: must be at least 14 days apart from other peaks
            valid = True
            for p in peaks:
                if abs((row['date'] - p['date']).days) < 14:
                    valid = False
                    break
            if valid:
                peaks.append(row)

        # Global pool of items to reuse for cross-date deduplication testing
        cross_date_news_pool = []
        cross_date_retail_pool = []

        for p in peaks:
            peak_dt = p['date']
            # Window is +/- 3 days for the core peak check according to user requirements
            # but we generate slightly more around it
            for i in range(-5, 6):
                current_dt = peak_dt + timedelta(days=i)
                dt_str = current_dt.strftime("%Y-%m-%d")

                # Generate 6 to 10 news articles per day
                num_news = random.randint(6, 10)
                last_title = None
                last_excerpt = None
                for n_idx in range(num_news):
                    # 10% chance to reuse a news item from a PREVIOUS date in the window (cross-date dedupe test)
                    if cross_date_news_pool and random.random() < 0.10:
                        reused = random.choice(cross_date_news_pool)
                        item = generate_news_item(ticker, dt_str, p['squeeze_score'], n_idx, True, reused['title'], reused['excerpt'])
                    else:
                        # 15% chance to duplicate within the SAME day
                        force_dup = (n_idx > 0) and (random.random() < 0.15)
                        item = generate_news_item(ticker, dt_str, p['squeeze_score'], n_idx, force_dup, last_title, last_excerpt)
                        if random.random() < 0.2: # 20% chance to add to cross-date pool
                            cross_date_news_pool.append(item)
                    
                    last_title = item['title']
                    last_excerpt = item['excerpt']
                    news_cache.append(item)

                # Generate 8 to 12 retail chatter events per day
                num_retail = random.randint(8, 12)
                last_r_excerpt = None
                for r_idx in range(num_retail):
                    # 10% chance to reuse a retail item from a PREVIOUS date (cross-date dedupe test)
                    if cross_date_retail_pool and random.random() < 0.10:
                        reused = random.choice(cross_date_retail_pool)
                        item = generate_retail_item(ticker, dt_str, i, r_idx, True, reused['excerpt'])
                    else:
                        # 20% chance to duplicate within the SAME day
                        force_dup = (r_idx > 0) and (random.random() < 0.20)
                        item = generate_retail_item(ticker, dt_str, i, r_idx, force_dup, last_r_excerpt)
                        if random.random() < 0.2: # 20% chance to add to cross-date pool
                            cross_date_retail_pool.append(item)
                            
                    last_r_excerpt = item['excerpt']
                    retail_cache.append(item)

    print(f"Generated {len(news_cache)} news items.")
    print(f"Generated {len(retail_cache)} retail items.")

    with open("news_demo_cache.json", "w") as jf:
        json.dump(news_cache, jf, indent=2)

    with open("retail_demo_cache.json", "w") as rf:
        json.dump(retail_cache, rf, indent=2)

if __name__ == "__main__":
    main()
