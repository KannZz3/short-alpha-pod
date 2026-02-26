#!/usr/bin/env python3
"""
newsapi_oracle.py  —  Short-Alpha Pod | Block4-B: News Arb LIVE Adapter (STUB)
===============================================================================
STATUS: OFF by default. This is a stub adapter.
        The UI uses docs/data/news_demo_cache.json in DEMO mode.

To activate LIVE mode:
  1. Get a NewsAPI key from https://newsapi.org/
  2. Set env var: NEWSAPI_KEY=your_key_here
  3. Run: python tools/newsapi_oracle.py --ticker TSLA --days 7
  4. Output is written to: docs/data/news_live_cache.json
  5. The UI auto-detects news_live_cache.json and shows [LIVE] badge.

Schema emitted (matches news_demo_cache.json):
  {
    "id": str,
    "ticker": str,
    "provider": str,
    "title": str,
    "url": str,
    "published_at_utc": str (ISO 8601),
    "retrieved_at_utc": str (ISO 8601),
    "excerpt": str,
    "tags": [str],
    "metrics": {
      "sentiment": float,   # -1.0 to +1.0
      "engagement": int,
      "shock": float
    },
    "quality_flags": [str],
    "mode": "LIVE"
  }

Degrades gracefully: if NEWSAPI_KEY is missing or request fails,
writes nothing and exits with code 1 so the UI keeps using DEMO cache.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta

try:
    import urllib.request
    import urllib.parse
except ImportError:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "docs", "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "news_live_cache.json")

NEWSAPI_BASE = "https://newsapi.org/v2/everything"
FOCUS_TICKERS = ["AFRM", "SQ", "PYPL", "SHOP", "TSLA"]


def ticker_to_query(ticker: str) -> str:
    name_map = {
        "AFRM": "Affirm",
        "SQ": "Block Inc",
        "PYPL": "PayPal",
        "SHOP": "Shopify",
        "TSLA": "Tesla",
    }
    return f"{ticker} OR \"{name_map.get(ticker, ticker)}\""


def naive_sentiment(title: str, excerpt: str) -> float:
    """Very naive rule-based sentiment. Replace with a real model for LIVE prod."""
    text = (title + " " + excerpt).lower()
    pos = sum(w in text for w in ["surge", "rally", "beat", "record", "up", "gain", "bullish"])
    neg = sum(w in text for w in ["drop", "crash", "miss", "down", "loss", "bearish", "fail"])
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 4)


def fetch_newsapi(ticker: str, api_key: str, days: int = 7):
    from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    params = urllib.parse.urlencode({
        "q": ticker_to_query(ticker),
        "from": from_date,
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": 50,
        "apiKey": api_key,
    })
    url = f"{NEWSAPI_BASE}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "ShortAlphaPod/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    return data.get("articles", [])


def articles_to_schema(articles, ticker: str):
    result = []
    now = datetime.now(timezone.utc).isoformat()
    for i, art in enumerate(articles):
        title = art.get("title") or ""
        excerpt = art.get("description") or ""
        sentiment = naive_sentiment(title, excerpt)
        engagement = art.get("source", {}).get("id", 0) or 0
        shock = round(abs(sentiment) * min(len(title) / 20, 5), 2)

        result.append({
            "id": f"live-{ticker}-{i}",
            "ticker": ticker,
            "provider": art.get("source", {}).get("name", "Unknown"),
            "title": title,
            "url": art.get("url", "#"),
            "published_at_utc": art.get("publishedAt", now),
            "retrieved_at_utc": now,
            "excerpt": excerpt,
            "tags": [ticker, "live"],
            "metrics": {
                "sentiment": sentiment,
                "engagement": engagement or 1,
                "shock": shock,
            },
            "quality_flags": [],
            "mode": "LIVE",
        })
    return result


def main():
    parser = argparse.ArgumentParser(description="NewsAPI oracle for Short-Alpha Pod")
    parser.add_argument("--ticker", default="all", help="Ticker or 'all'")
    parser.add_argument("--days", type=int, default=7, help="Lookback days")
    args = parser.parse_args()

    api_key = os.environ.get("NEWSAPI_KEY", "")
    if not api_key:
        print("[FAIL] NEWSAPI_KEY env var not set. Aborting — UI will use DEMO cache.")
        sys.exit(1)

    tickers = FOCUS_TICKERS if args.ticker == "all" else [args.ticker.upper()]
    all_items = []

    for t in tickers:
        print(f"[INFO] Fetching NewsAPI for {t}...")
        try:
            articles = fetch_newsapi(t, api_key, args.days)
            items = articles_to_schema(articles, t)
            all_items.extend(items)
            print(f"       → {len(items)} articles")
        except Exception as e:
            print(f"[WARN] {t} fetch failed: {e}")

    if not all_items:
        print("[FAIL] No articles fetched. Aborting — UI will use DEMO cache.")
        sys.exit(1)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2)

    print(f"[OK] {len(all_items)} articles written to {OUTPUT_PATH}")
    print("     UI will show [LIVE] badge on next load.")


if __name__ == "__main__":
    main()
