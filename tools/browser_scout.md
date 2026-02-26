# Browser Scout Protocol
**Short-Alpha Pod | Block4-B: News Arb — Manual Browser Collection**

> **STATUS: OFFLINE PROTOCOL** — Use this when NewsAPI is unavailable or rate-limited.
> Collected data is formatted to match `news_demo_cache.json` schema and saved as `docs/data/news_live_cache.json`.

---

## When to Use

- Free-tier NewsAPI exhausted (100 req/day)
- Need real-time data for a specific intraday event
- Cross-checking automated sentiment with human judgment

---

## Step-by-Step Protocol

### 1. Target Sources (in priority order)

| Priority | Source | URL | Notes |
|---|---|---|---|
| P0 | Bloomberg | bloomberg.com/search | Login required for full text |
| P0 | Reuters | reuters.com/search | Free, high quality |
| P1 | WSJ | wsj.com | Login required |
| P1 | Financial Times | ft.com | Login required |
| P2 | Seeking Alpha | seekingalpha.com | Good for retail-adjacent |
| P2 | Reddit r/Vitards | reddit.com/r/vitards | Retail sentiment |
| P2 | Reddit r/wallstreetbets | reddit.com/r/wallstreetbets | Meme indicators |

### 2. For Each Article Found

Copy into a JSON object matching this schema:

```json
{
  "id": "scout-TICKER-YYYYMMDD-NNN",
  "ticker": "TSLA",
  "provider": "Reuters",
  "title": "Article title here",
  "url": "https://...",
  "published_at_utc": "2026-02-27T10:00:00Z",
  "retrieved_at_utc": "2026-02-27T03:59:00Z",
  "excerpt": "First 2-3 sentences of article body.",
  "tags": ["short_interest", "squeeze"],
  "metrics": {
    "sentiment": 0.7,
    "engagement": 1000,
    "shock": 3.5
  },
  "quality_flags": [],
  "mode": "LIVE"
}
```

**Sentiment scoring guide:**
- `+0.8 to +1.0`: Strongly bullish (squeeze catalyst, record earnings)
- `+0.3 to +0.7`: Mildly bullish
- `-0.1 to +0.1`: Neutral / ambiguous
- `-0.3 to -0.7`: Mildly bearish
- `-0.8 to -1.0`: Strongly bearish (regulatory action, fraud)

**Shock scoring guide:**
- `shock = |sentiment| × volume_proxy × 10`
- Volume proxy: Bloomberg/Reuters = 8, Seeking Alpha = 4, Reddit = 2

### 3. Saving

Collect all objects into an array and save as:
```
docs/data/news_live_cache.json
```

The UI auto-detects this file on next load and shows the **[LIVE]** badge.

### 4. De-duplication

The UI's `DataHub.dedupeEvidence()` will automatically de-duplicate articles with:
- Same normalized title (Jaccard ≥ 0.92)
- Same URL (normalized)
- Same excerpt (Jaccard ≥ 0.85)

No manual de-dup needed.

---

## Shock vs Reversion Decision Heuristic

After collecting, classify the shock:

| shock_score | direction_bias | Rationale |
|---|---|---|
| > 7 | DRAWDOWN | Extreme negative sentiment shock → likely forced covering |
| 4–7 | UNCLEAR | Mixed signals → wait for lag confirmation |
| < 4 | REVERSION | Low shock → noise, mean reversion expected |

This output is displayed in the **Shock vs Reversion** card in the Evidence Explorer tab.
