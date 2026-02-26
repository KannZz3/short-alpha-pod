#!/usr/bin/env python3
"""
run_daily_demo.py  —  Short-Alpha Pod | Block4-A: Squeeze Oracle Daily Runner
=============================================================================
Generates / updates docs/data/daily_snapshot.json from:
  - docs/data/Stock Short Interest Data.csv
  - docs/data/news_demo_cache.json
  - docs/data/retail_demo_cache.json

Usage (offline DEMO mode, no API keys needed):
  python tools/run_daily_demo.py

Output:
  docs/data/daily_snapshot.json

Set SQUEEZE_ORACLE_MODE flag in the UI to ON to have the UI read this snapshot.

LIVE mode (optional):
  Set env vars before running:
    ORACLE_DATA_SOURCE=live
    NEWSAPI_KEY=your_key_here
  Then the script will attempt to pull fresh data.
  The UI will show [LIVE] badge instead of [DEMO].
"""

import json
import csv
import os
import sys
from datetime import datetime, timezone, timedelta
import statistics

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "docs", "data")
CSV_PATH = os.path.join(DATA_DIR, "Stock Short Interest Data.csv")
NEWS_CACHE = os.path.join(DATA_DIR, "news_demo_cache.json")
RETAIL_CACHE = os.path.join(DATA_DIR, "retail_demo_cache.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "daily_snapshot.json")

FOCUS_TICKERS = ["AFRM", "SQ", "PYPL", "SHOP", "TSLA"]
DATA_SOURCE = os.environ.get("ORACLE_DATA_SOURCE", "demo")  # "demo" or "live"

# ── Helpers ────────────────────────────────────────────────────────────────
def load_csv(path):
    rows = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Ticker") in FOCUS_TICKERS:
                    rows.append(row)
    except FileNotFoundError:
        print(f"[WARN] CSV not found: {path}")
    return rows


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"[WARN] JSON not found or invalid: {path}")
        return []


def safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def compute_days_to_cover_proxy(si_pct, avg_vol_proxy=0.03):
    """
    Proxy: days_to_cover = SI% / avg_daily_turnover_rate
    avg_vol_proxy is a rough estimate (3% float turnover) when real ADV is unavailable.
    PROXY — not real borrow cost data. Labeled as such in snapshot.
    """
    if si_pct <= 0:
        return 0.0
    return round(si_pct / (avg_vol_proxy * 100), 2)


# ── Core Builder ───────────────────────────────────────────────────────────
def build_snapshot():
    print("[INFO] Loading CSV data...")
    csv_rows = load_csv(CSV_PATH)

    print("[INFO] Loading news cache...")
    news = load_json(NEWS_CACHE)

    print("[INFO] Loading retail cache...")
    retail = load_json(RETAIL_CACHE)

    now_utc = datetime.now(timezone.utc).isoformat()
    snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    tickers_data = {}
    for ticker in FOCUS_TICKERS:
        ticker_rows = [r for r in csv_rows if r.get("Ticker") == ticker]

        if not ticker_rows:
            print(f"[WARN] No CSV rows for {ticker}")
            tickers_data[ticker] = {
                "ticker": ticker,
                "data_source": DATA_SOURCE.upper(),
                "error": "NO_CSV_DATA"
            }
            continue

        # Sort by date
        def parse_date(r):
            ds = r.get("Business Date") or r.get("Date", "")
            if "/" in ds:
                parts = ds.split("/")
                year = parts[2] if len(parts) == 3 else "2000"
                if len(year) == 2:
                    year = "20" + year
                return f"{year}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
            return ds

        ticker_rows.sort(key=parse_date)
        latest = ticker_rows[-1]

        si_pct = safe_float(latest.get("S3SIPctFloat") or latest.get("ShortInterestPct")) * 100
        if si_pct == 0:
            si_raw = safe_float(latest.get("Short Interest"))
            s3_float = safe_float(latest.get("S3Float"), default=1)
            si_pct = (si_raw / s3_float) * 100 if s3_float > 0 else 0

        crowded = safe_float(latest.get("Crowded Score"))
        squeeze = safe_float(latest.get("Squeeze Score"))

        # Borrow cost PROXY (no real data)
        days_to_cover = compute_days_to_cover_proxy(si_pct)
        # Borrow fee proxy: high SI% → inferred higher borrow cost
        borrow_fee_proxy = round(min(50.0, si_pct * 0.8), 2)  # crude linear proxy

        # News volume in the last 30 days
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        recent_news = [n for n in news if n.get("ticker") == ticker
                       and n.get("published_at_utc", "") >= cutoff]
        recent_retail = [r for r in retail if r.get("ticker") == ticker
                         and r.get("published_at_utc", "") >= cutoff]

        sentiments = [n.get("metrics", {}).get("sentiment", 0) for n in recent_news]
        avg_sentiment = round(statistics.mean(sentiments), 4) if sentiments else 0.0
        sentiment_std = round(statistics.stdev(sentiments), 4) if len(sentiments) > 1 else 0.0

        # Simple shock score for snapshot: volume × |avg_sentiment| × source_diversity
        provider_set = set(n.get("provider", "") for n in recent_news)
        novelty = len(provider_set) / max(len(recent_news), 1)
        snap_shock = round(len(recent_news) * abs(avg_sentiment) * novelty * 10, 2)

        tickers_data[ticker] = {
            "ticker": ticker,
            "data_source": DATA_SOURCE.upper(),
            "snapshot_date": snapshot_date,
            "latest_date": parse_date(latest),
            "short_interest_pct": round(si_pct, 2),
            "crowded_score": round(crowded, 2),
            "squeeze_score": round(squeeze, 2),
            "pro_metrics_proxy": {
                "days_to_cover": days_to_cover,
                "borrow_fee_pct_est": borrow_fee_proxy,
                "proxy_label": "PROXY — computed from SI% / avg_float_turnover. NOT real borrow cost data.",
                "utilization_proxy": round(min(100.0, si_pct * 2.5), 2),
            },
            "news_30d": {
                "count": len(recent_news),
                "unique_providers": len(provider_set),
                "avg_sentiment": avg_sentiment,
                "sentiment_std": sentiment_std,
            },
            "retail_30d": {
                "count": len(recent_retail),
            },
            "snap_shock_score": snap_shock,
        }

    snapshot = {
        "schema_version": "1.0",
        "generated_at": now_utc,
        "snapshot_date": snapshot_date,
        "data_source": DATA_SOURCE.upper(),
        "mode_label": "DEMO" if DATA_SOURCE == "demo" else "LIVE",
        "note": "Generated by tools/run_daily_demo.py. Pro-metrics are PROXY estimates — not real borrow/utilization data.",
        "tickers": tickers_data,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"[OK] Snapshot written to: {OUTPUT_PATH}")
    print(f"     Data source: {DATA_SOURCE.upper()}")
    print(f"     Tickers: {list(tickers_data.keys())}")
    return snapshot


if __name__ == "__main__":
    snap = build_snapshot()
    print(f"\n[DONE] Snapshot covers {len(snap['tickers'])} tickers.")
    print("       Set SQUEEZE_ORACLE_MODE flag in the UI to read this snapshot.")
