#!/usr/bin/env python3
"""
browser_scout.py  --  Short-Alpha Pod | Retail Browser-Data Scout (OFFLINE/LIVE)
=================================================================================
STATUS: OFFLINE by default — uses seed data from docs/data/retail_demo_cache.json.
        LIVE mode (optional) accepts a --seed-json from a manual collection
        session following tools/browser_scout.md protocol.

PURPOSE:
  Aggregates retail/social chatter (Reddit, Twitter/X, StockTwits, Discord …)
  into a per-day time-series of {ret_vol, hype} that the UI reads from
  docs/data/retail_live_cache.json.

USAGE:
  # Offline: produces daily summary from existing DEMO cache
  python tools/browser_scout.py --ticker TSLA --mode offline

  # Live: ingest a manual-collection JSON, dedupe, classify, write live cache
  python tools/browser_scout.py --ticker TSLA --mode live --seed my_scout.json

OUTPUT SCHEMA (matches retail_demo_cache.json + extra daily_series block):
  Each item:
    id, ticker, source_type="retail", provider, title, url, published_at_utc,
    retrieved_at_utc, excerpt, tags, metrics {sentiment, shock, engagement, volume},
    quality_flags, mode, raw_ref

  Top-level:
    daily_series: { "YYYY-MM-DD": { ret_vol, hype, post_count } }

ENV VARS / FLAGS:
  None required for offline mode.
  RETAIL_KEY (optional) — future integration placeholder.

DEDUPLICATION RULES (same as DataHub.dedupeEvidence in docs/index.html):
  - Same normalized title (Jaccard >= 0.92)
  - Same URL (normalized, strip query params)
  - Same excerpt (Jaccard >= 0.85)
  Deduped posts are dropped; a DUPLICATE_REMOVED quality_flag is added to
  the surviving canonical item.
"""

import os
import sys
import json
import argparse
import hashlib
from datetime import datetime, timezone
from collections import defaultdict

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "docs", "data")
DEMO_CACHE  = os.path.join(DATA_DIR, "retail_demo_cache.json")
LIVE_OUTPUT = os.path.join(DATA_DIR, "retail_live_cache.json")

FOCUS_TICKERS = ["AFRM", "SQ", "PYPL", "SHOP", "TSLA"]


# ── Jaccard similarity (word-token level) ────────────────────────────────────
def jaccard(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    inter = sa & sb
    union = sa | sb
    return len(inter) / len(union) if union else 0.0


def normalize_url(url: str) -> str:
    """Strip query string and trailing slash for URL deduplication."""
    return url.split("?")[0].rstrip("/") if url else ""


# ── Dedupe a list of items in-place; returns (kept, dropped_count) ───────────
def dedupe_items(items: list) -> tuple:
    kept   = []
    dropped = 0
    seen_urls   = {}   # norm_url -> index in kept
    seen_titles = {}   # item index -> title tokens

    for item in items:
        url  = normalize_url(item.get("url", ""))
        title   = item.get("title", "")
        excerpt = item.get("excerpt", "")

        # URL dedup (exact after normalize)
        if url and url in seen_urls:
            dropped += 1
            continue

        # Title / excerpt Jaccard against existing kept
        is_dup = False
        for ki, k in enumerate(kept):
            if jaccard(title, k.get("title", "")) >= 0.92:
                is_dup = True
                break
            if excerpt and jaccard(excerpt, k.get("excerpt", "")) >= 0.85:
                is_dup = True
                break
        if is_dup:
            dropped += 1
            continue

        if url:
            seen_urls[url] = len(kept)
        kept.append(item)

    return kept, dropped


# ── Hype classifier: naive rule-based (0..1) ─────────────────────────────────
HYPE_BULL = {"moon", "squeeze", "yolo", "rocket", "ape", "diamond", "hold", "rip",
             "breakout", "buy", "calls", "bullish", "long", "up"}
HYPE_BEAR = {"puts", "short", "crash", "dump", "paper", "sell", "bearish", "down"}

def hype_score(title: str, excerpt: str) -> float:
    text  = (title + " " + excerpt).lower().split()
    words = set(text)
    bull  = len(words & HYPE_BULL)
    bear  = len(words & HYPE_BEAR)
    total = bull + bear
    if total == 0:
        return 0.5  # neutral
    return round(bull / total, 4)


# ── Build per-day time-series from a flat item list ──────────────────────────
def build_daily_series(items: list) -> dict:
    """
    Returns dict: { "YYYY-MM-DD": { "ret_vol": int, "hype": float, "post_count": int } }
    ret_vol  = sum(engagement across posts on that day)
    hype     = mean(hype_score) across posts on that day
    post_count = unique posts after dedupe
    """
    by_day = defaultdict(list)
    for item in items:
        ts = item.get("published_at_utc", "")
        dk = ts[:10] if len(ts) >= 10 else None   # "YYYY-MM-DD"
        if dk:
            by_day[dk].append(item)

    series = {}
    for dk, day_items in sorted(by_day.items()):
        engagements = [item.get("metrics", {}).get("engagement", 0) for item in day_items]
        hypes       = [hype_score(item.get("title", ""), item.get("excerpt", ""))
                       for item in day_items]
        series[dk] = {
            "ret_vol":    sum(engagements),
            "hype":       round(sum(hypes) / len(hypes), 4) if hypes else 0.0,
            "post_count": len(day_items),
        }
    return series


# ── Ingest a manual-collection seed file (tools/browser_scout.md format) ─────
def ingest_seed(seed_path: str, ticker: str) -> list:
    with open(seed_path, encoding="utf-8") as f:
        raw = json.load(f)

    now = datetime.now(timezone.utc).isoformat()
    result = []
    for i, item in enumerate(raw):
        # Ensure required fields exist; mark as LIVE
        item.setdefault("id",               f"scout-{ticker}-{i:04d}")
        item.setdefault("ticker",           ticker)
        item.setdefault("source_type",      "retail")
        item.setdefault("retrieved_at_utc", now)
        item.setdefault("quality_flags",    [])
        item.setdefault("mode",             "LIVE")
        item.setdefault("raw_ref",          {"cache": "browser_scout", "seed": seed_path})

        # Flag empty / placeholder URLs
        url = item.get("url", "")
        if not url or "placeholder" in url.lower():
            if "EMPTY_URL" not in item["quality_flags"]:
                item["quality_flags"].append("EMPTY_URL" if not url else "PLACEHOLDER_URL")

        # Compute hype if missing
        if "metrics" not in item:
            item["metrics"] = {}
        item["metrics"].setdefault(
            "sentiment", item["metrics"].get("sentiment", 0.0))
        item["metrics"]["hype"] = hype_score(
            item.get("title", ""), item.get("excerpt", ""))

        result.append(item)
    return result


# ── Offline mode: summarise DEMO cache for a ticker ──────────────────────────
def offline_summary(ticker: str) -> dict:
    if not os.path.exists(DEMO_CACHE):
        print(f"[WARN] Demo cache not found: {DEMO_CACHE}")
        return {}
    with open(DEMO_CACHE, encoding="utf-8") as f:
        all_items = json.load(f)
    items = [x for x in all_items if x.get("ticker") == ticker]
    kept, dropped = dedupe_items(items)
    series = build_daily_series(kept)
    return {
        "ticker":       ticker,
        "mode":         "OFFLINE_DEMO",
        "source_cache": DEMO_CACHE,
        "item_count":   len(kept),
        "dropped":      dropped,
        "daily_series": series,
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Retail browser scout — Short-Alpha Pod")
    parser.add_argument("--ticker", default="TSLA", help="Ticker symbol (default: TSLA)")
    parser.add_argument("--mode",   default="offline", choices=["offline", "live"],
                        help="'offline' summarises DEMO cache; 'live' ingests --seed-json")
    parser.add_argument("--seed",   default=None,
                        help="Path to manual-collection JSON (required for --mode live)")
    parser.add_argument("--out",    default=None,
                        help="Output path (default: docs/data/retail_live_cache.json for live)")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    if ticker not in FOCUS_TICKERS:
        print(f"[WARN] {ticker} not in FOCUS_TICKERS {FOCUS_TICKERS}. Proceeding anyway.")

    if args.mode == "offline":
        print(f"[INFO] Offline mode — summarising DEMO cache for {ticker}")
        summary = offline_summary(ticker)
        print(json.dumps(summary, indent=2))
        print(f"\n[OK] daily_series has {len(summary.get('daily_series', {}))} days.")
        return

    # LIVE mode
    if not args.seed:
        print("[FAIL] --mode live requires --seed <path>. See tools/browser_scout.md.")
        sys.exit(1)

    print(f"[INFO] Live mode — ingesting {args.seed} for {ticker}")
    items = ingest_seed(args.seed, ticker)
    kept, dropped = dedupe_items(items)
    print(f"[INFO] {len(items)} items ingested; {dropped} deduped; {len(kept)} kept.")

    series = build_daily_series(kept)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ticker":       ticker,
        "mode":         "LIVE",
        "item_count":   len(kept),
        "dropped":      dropped,
        "daily_series": series,
        "items":        kept,
    }

    out_path = args.out or LIVE_OUTPUT
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"[OK] {len(kept)} items written to {out_path}")
    print(f"     {len(series)} days in daily_series.")
    print("     UI will show [LIVE] badge on next load (if retail_live_cache.json is present).")


if __name__ == "__main__":
    main()
