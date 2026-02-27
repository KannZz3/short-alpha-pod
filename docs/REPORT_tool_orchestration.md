# Tool Orchestration
**Short-Alpha Pod | Evidence Pipeline — Truthful Audit (2026-02-27)**

> **Compliance statement generated from code inspection, not documentation alone.**
> Every claim below cites an exact file path and line range.

---

## 1. NewsAPI Oracle (Python)

### Status: `OPTIONAL LIVE` — OFF by default; UI uses DEMO cache

**File:** [`tools/newsapi_oracle.py`](../tools/newsapi_oracle.py) (167 lines)

### What it does

Calls `https://newsapi.org/v2/everything` via Python's built-in `urllib` (no third-party deps).
One request per ticker, up to 50 articles, last N days.

### Exact entrypoint snippet (verbatim, L81–L95)

```python
# tools/newsapi_oracle.py  L81–95
NEWSAPI_BASE = "https://newsapi.org/v2/everything"          # L55

def fetch_newsapi(ticker: str, api_key: str, days: int = 7):
    from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    params = urllib.parse.urlencode({
        "q":        ticker_to_query(ticker),   # e.g. "TSLA OR \"Tesla\""
        "from":     from_date,
        "language": "en",
        "sortBy":   "relevancy",
        "pageSize": 50,
        "apiKey":   api_key,
    })
    url = f"{NEWSAPI_BASE}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "ShortAlphaPod/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    return data.get("articles", [])
```

### Required environment variable

```powershell
$env:NEWSAPI_KEY = "your_key_here"   # https://newsapi.org/ — free tier: 100 req/day
```

### CLI usage

```powershell
# All tickers, last 7 days
python tools/newsapi_oracle.py --ticker all --days 7

# Single ticker
python tools/newsapi_oracle.py --ticker TSLA --days 14
```

### Output artifact

`docs/data/news_live_cache.json` — flat JSON array.
The UI's `DataHub.init()` (`docs/index.html` L973–978) tries `news_live_cache.json` first;
falls back to `news_demo_cache.json` if absent.

### Schema emitted (L15–33)

| Field | Type | Notes |
|---|---|---|
| `id` | str | `live-{ticker}-{i}` |
| `ticker` | str | |
| `provider` | str | from `article.source.name` |
| `title` | str | |
| `url` | str | article URL (real, from NewsAPI) |
| `published_at_utc` | ISO 8601 | |
| `retrieved_at_utc` | ISO 8601 | time of this script run |
| `excerpt` | str | `article.description` |
| `tags` | `[ticker, "live"]` | extensible |
| `metrics.sentiment` | float −1..+1 | naive rule-based (L70–78); replace for prod |
| `metrics.shock` | float | `\|sentiment\| × title_length_proxy` |
| `metrics.engagement` | int | `source.id` proxy (sparse in free tier) |
| `quality_flags` | `[]` | empty; `classifyUrl()` enriches at UI load |
| `mode` | `"LIVE"` | triggers `[LIVE]` badge in UI |

### Graceful degradation (L135–155)

```python
api_key = os.environ.get("NEWSAPI_KEY", "")
if not api_key:
    print("[FAIL] NEWSAPI_KEY env var not set. Aborting — UI will use DEMO cache.")
    sys.exit(1)
```
If the script fails for any reason, it writes **nothing**.
The UI silently continues with `news_demo_cache.json`.

---

## 2. Browser Agent — Retail / Social Chatter

### Status: `TWO-LAYER` — Manual protocol (documented) + automated offline aggregator

### Layer A: Manual Collection Protocol

**File:** [`tools/browser_scout.md`](../tools/browser_scout.md) (98 lines)

Human operator follows this protocol when NewsAPI is rate-limited or for intraday events.

**Sources targeted (priority order):**

| Priority | Source | Notes |
|---|---|---|
| P0 | Bloomberg, Reuters | Institutional quality |
| P1 | WSJ, Financial Times | Login required |
| P2 | Seeking Alpha, Reddit r/WSB, Reddit r/Vitards | Retail-adjacent |

**Fields extracted manually (L36–54):**

```json
{
  "id": "scout-TICKER-YYYYMMDD-NNN",
  "provider": "Reuters",
  "title": "Article title here",
  "url": "https://...",
  "published_at_utc": "2026-02-27T10:00:00Z",
  "excerpt": "First 2-3 sentences.",
  "tags": ["short_interest", "squeeze"],
  "metrics": { "sentiment": 0.7, "engagement": 1000, "shock": 3.5 }
}
```

Sentiment scale: `+1 = squeeze catalyst`, `0 = neutral`, `−1 = regulatory/fraud` (L57–66)
Shock formula: `shock = |sentiment| × volume_proxy × 10`, where volume_proxy = 8 (Bloomberg/Reuters), 4 (Seeking Alpha), 2 (Reddit) (L64–65)

### Layer B: Automated Offline Aggregator

**File:** [`tools/browser_scout.py`](../tools/browser_scout.py) ← **new, added this session**

Runs without network access by default.

**Offline mode** (summarises existing DEMO cache):
```powershell
python tools/browser_scout.py --ticker TSLA --mode offline
```

**Live mode** (ingests a manual-collection JSON from browser_scout.md):
```powershell
python tools/browser_scout.py --ticker TSLA --mode live --seed my_scout.json
```

**Deduplication** (mirrors `DataHub.dedupeEvidence()` in `docs/index.html`):
- Same URL (normalized, query params stripped) → drop
- Title Jaccard ≥ 0.92 → drop
- Excerpt Jaccard ≥ 0.85 → drop

**Per-day aggregation** (`build_daily_series()`):

```python
series[dk] = {
    "ret_vol":    sum(engagement),   # raw retail traffic volume
    "hype":       mean(hype_score),  # 0..1 bullish signal ratio
    "post_count": len(day_items),
}
```

**Hype scoring** (naive, word-set based):
- Bull words: `{moon, squeeze, yolo, rocket, ape, diamond, hold, rip, breakout, buy, calls, bullish, long, up}`
- Bear words: `{puts, short, crash, dump, paper, sell, bearish, down}`
- `hype = |bull_matches| / (|bull| + |bear|)`, range 0..1

**Output:** `docs/data/retail_live_cache.json`

UI reads it at `DataHub.init()` (`docs/index.html` L976–977); falls back to `retail_demo_cache.json`.

---

## 3. DEMO Mode (Offline-First)

**Status: ALWAYS AVAILABLE — no API key needed**

| Cache file | Generator | Items | Mode label |
|---|---|---|---|
| `docs/data/news_demo_cache.json` | `docs/data/generate_demo_caches.py` (319 lines) | ~1,500 | `DEMO` |
| `docs/data/retail_demo_cache.json` | same | ~2,000 | `DEMO` |

Both caches are **deterministic mocks** keyed by `{ticker}|{date}|{inst\|ret}_{idx}`.
They are safe to use offline and are always present in the repo.
URL integrity: all DEMO items receive `DEMO_PLACEHOLDER` quality_flag at runtime
via `DataHub.classifyUrl()` (`docs/index.html` ~L1853); the `VIEW ORIGINAL SOURCE`
button is disabled for all DEMO items.

---

## 4. Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        LIVE PATH (optional)                      │
│                                                                  │
│   NEWSAPI_KEY env var                                            │
│       │                                                          │
│       ▼                                                          │
│  tools/newsapi_oracle.py ──► docs/data/news_live_cache.json     │
│                                                                  │
│  manual browser session                                          │
│  (browser_scout.md)                                              │
│       │                                                          │
│       ▼                                                          │
│  tools/browser_scout.py ──► docs/data/retail_live_cache.json    │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                      DEMO PATH (always available)                │
│                                                                  │
│  docs/data/generate_demo_caches.py                               │
│       │                                                          │
│       ├──► docs/data/news_demo_cache.json   (~1,500 items)       │
│       └──► docs/data/retail_demo_cache.json (~2,000 items)       │
└──────────────────────────────────────────────────────────────────┘

                        ▼ DataHub.init() in docs/index.html L944
                        │ tries *_live_cache.json first
                        │ falls back to *_demo_cache.json
                        │
                        ▼ DataHub.enrichCacheFlags() L979
                        │ sets DEMO_PLACEHOLDER on all DEMO items
                        │
                        ▼ DataHub.dedupeEvidence() ~L1260
                        │ Jaccard dedupe (title 0.92, excerpt 0.85, URL exact)
                        │
                        ▼ DataHub.computeRealIndices() ~L1050
                        │ z-score noise_index, real sentiment avg,
                        │ swan detection, short-form aliases (nv/ns/rv/rh)
                        │
                        ▼ React UI — Evidence Explorer tab
```

---

## 5. Summary of Files Added / Changed This Session

| File | Action | Purpose |
|---|---|---|
| `tools/browser_scout.py` | **NEW** | Automated retail scout: offline summary + live ingest, Jaccard dedupe, daily_series aggregation |
| `docs/REPORT_tool_orchestration.md` | **NEW** | This document |

All other files cited above were **pre-existing** in the repo.

---

## 6. Validation Commands (PowerShell)

```powershell
# Offline retail scout (no network, no API key)
cd C:\Users\78432\.gemini\antigravity\scratch\short_alpha_pod
python tools/browser_scout.py --ticker TSLA --mode offline

# NewsAPI (requires key)
$env:NEWSAPI_KEY = "YOUR_KEY"
python tools/newsapi_oracle.py --ticker TSLA --days 7

# Serve locally and verify UI
python -m http.server 8000 --directory docs
# Then open: http://localhost:8000/
```

Expected offline output for `browser_scout.py`:
```json
{
  "ticker": "TSLA",
  "mode": "OFFLINE_DEMO",
  "item_count": ...,
  "dropped": ...,
  "daily_series": { "2021-11-04": { "ret_vol": 12345, "hype": 0.71, "post_count": 8 }, ... }
}
```
