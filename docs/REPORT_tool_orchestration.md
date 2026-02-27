# Tool Orchestration
**Short-Alpha Pod | Evidence Pipeline — Truthful Audit (2026-02-27)**

> All claims cite an exact file path and line range. Numbers in the example are derived from local cache files, reproduced by `tools/verify_tool_orchestration_example.py`.

---

## One-Line Logic Summary

**NewsAPI** (`tools/newsapi_oracle.py`, L81–95) fetches up to 50 structured institutional headlines per ticker from `https://newsapi.org/v2/everything`; these are normalised into the `EvidenceItem` schema and stored in `docs/data/news_live_cache.json`. `DataHub.computeRealIndices()` (`docs/index.html`, L1066–1077) then aggregates them into per-day counts (`nv = newsCount / maxN`) and average sentiment (`ns`). **The Browser Agent** (`tools/browser_scout.py`, offline; guided by `tools/browser_scout.md`) collects retail/social chatter from Reddit, StockTwits, and Discord posts; after Jaccard deduplication (title Jaccard ≥ 0.92, excerpt ≥ 0.85, URL exact) the same function aggregates items into per-day retail volume (`rv = retailEngSum / maxR`) and hype (`rh`). Both signals are **aligned to the same peak window** via `DataHub.getFilteredData()` (`docs/index.html`, L990–1052) which slices the merged CSV+cache series to the same calendar range. They are then **combined into Noise_t** using a 60/40 weighted ratio (L1098–1125): `noise_index_t = ((z-score of 0.6·nv_t + 0.4·rv_t)` clamped to −5..5, then rescaled to 0..100). Lag Validation (`docs/index.html`, L1462–1477) then computes `Pearson(Noise[0..n–2], SI[2..n])` — a 2-row (≈ 48 h) lead-lag correlation — to test whether `Noise_t` predicts `SI_{t+2}`; a result > 0.4 yields a `PASS` hypothesis.

---

## 1. NewsAPI Oracle (Python)

### Status: `OPTIONAL LIVE` — OFF by default; UI uses DEMO cache

**File:** `tools/newsapi_oracle.py` (167 lines)

### Exact entrypoint snippet (verbatim, L55 + L81–95)

```python
# tools/newsapi_oracle.py  L55 + L81–95
NEWSAPI_BASE = "https://newsapi.org/v2/everything"

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
$env:NEWSAPI_KEY = "your_key"   # https://newsapi.org/ — free tier: 100 req/day
```

### CLI usage

```powershell
python tools/newsapi_oracle.py --ticker TSLA --days 7   # single ticker
python tools/newsapi_oracle.py --ticker all  --days 7   # all 5 tickers
```

### Output artifact

`docs/data/news_live_cache.json` — flat JSON array. `DataHub.init()` (`docs/index.html` L973–978) tries `news_live_cache.json` **first**; falls back to `news_demo_cache.json` if absent.

### Schema emitted (L15–33)

| Field | Type | Notes |
|---|---|---|
| `id` | str | `live-{ticker}-{i}` |
| `ticker` | str | |
| `provider` | str | `article.source.name` |
| `title` | str | |
| `url` | str | Real article URL from NewsAPI |
| `published_at_utc` | ISO 8601 | |
| `retrieved_at_utc` | ISO 8601 | Script run time |
| `excerpt` | str | `article.description` |
| `tags` | list | `[ticker, "live"]` |
| `metrics.sentiment` | float −1..1 | Naive keyword rule (L70–78); replace for prod |
| `metrics.shock` | float | `\|sentiment\| × len(title)/20` |
| `metrics.engagement` | int | `source.id` proxy |
| `quality_flags` | list | Empty; `classifyUrl()` enriches at UI load |
| `mode` | `"LIVE"` | Triggers `[LIVE]` badge in UI |

### Graceful degradation (L135–155)

```python
api_key = os.environ.get("NEWSAPI_KEY", "")
if not api_key:
    print("[FAIL] NEWSAPI_KEY env var not set. Aborting — UI will use DEMO cache.")
    sys.exit(1)
```
Script writes **nothing** on failure; UI silently continues with `news_demo_cache.json`.

---

## 2. Browser Agent — Retail / Social Chatter

### Status: `TWO-LAYER` — Manual protocol + automated offline aggregator

### Layer A: Manual Collection Protocol

**File:** `tools/browser_scout.md` (98 lines)

**Sources targeted (priority order):**

| Priority | Source | Notes |
|---|---|---|
| P0 | Bloomberg, Reuters | Institutional quality |
| P1 | WSJ, Financial Times | Login required |
| P2 | Seeking Alpha, Reddit r/WSB, Reddit r/Vitards | Retail-adjacent |

Collected manually into the `EvidenceItem` schema (L36–54 of `browser_scout.md`).

**Sentiment scale:** `+1.0` = squeeze catalyst, `0` = neutral, `−1.0` = regulatory/fraud
**Shock formula:** `shock = |sentiment| × volume_proxy × 10` (volume_proxy: Reuters=8, Seeking Alpha=4, Reddit=2)

### Layer B: Automated Offline / Live Aggregator

**File:** `tools/browser_scout.py` (≈200 lines)

```powershell
# Offline — no network, no key needed
python tools/browser_scout.py --ticker TSLA --mode offline

# Live — ingest a manual-collection JSON from browser_scout.md protocol
python tools/browser_scout.py --ticker TSLA --mode live --seed my_scout.json
```

**Deduplication** (mirrors `DataHub.dedupeEvidence()` in `docs/index.html`):
- Same URL (normalized) → drop
- Title Jaccard ≥ 0.92 → drop
- Excerpt Jaccard ≥ 0.85 → drop

**Per-day aggregation** (`build_daily_series()`):

```python
series[dk] = {
    "ret_vol":    sum(engagement per day),
    "hype":       mean(hype_score per day),   # 0..1
    "post_count": len(unique posts),
}
```

**Output:** `docs/data/retail_live_cache.json`. UI reads at `DataHub.init()` (`docs/index.html` L976–977); falls back to `retail_demo_cache.json`.

---

## 3. End-to-End Verifiable Example (No Invention)

> **Reproduce with:** `python tools/verify_tool_orchestration_example.py --ticker TSLA --day 2021-01-08`
> All numbers below come from that script reading local demo cache files only.

### Ticker: TSLA | Window: Peak ~2021-01-08 | Day: 2021-01-08

#### A — News Signal (`docs/index.html` L1066–1077)

```
Source: docs/data/news_demo_cache.json  (mode=DEMO)
Items in cache for 2021-01-08:  9
news_vol  (nv)  = 9 / maxN(10) = 0.9000
avg_sentiment   (ns)            = −0.0075   (mean of 9 item metrics.sentiment)
swan flag                       = True       (avg |shock| > 5 on ≥1 item)
```

#### B — Retail Signal (`docs/index.html` L1078–1088)

```
Source: docs/data/retail_demo_cache.json  (mode=DEMO)
Items in cache for 2021-01-08:  10
ret_vol   (rv)  = 235,696 / maxR(381,757) = 0.6174
hype      (rh)  = mean(|metrics.sentiment|) = 0.7063
```

#### C — Combined Noise formula (`docs/index.html` L1098–1125)

```python
# Step 1: weighted blend (weights 0.6 / 0.4)
raw_combined = 0.6 × nv + 0.4 × rv
             = 0.6 × 0.9000 + 0.4 × 0.6174
             = 0.7870

# Step 2: z-score over entire series (33 days)
series_mean  = 0.7384
series_std   = 0.0859
z_noise      = (0.7870 − 0.7384) / 0.0859 = +0.566

# Step 3: clamp −5..5, then rescale to 0..100
noise_index  = (clamp(+0.566) + 5) × 10 = 55.66
```

**Interpretation:** 55.66 is slightly above neutral (50), indicating modest news+retail pressure on 2021-01-08.

#### D — Lag Validation mapping (`docs/index.html` L1462–1477)

```python
# Pearson(noise[0..n-2], SI[2..n])  ← 2-row shift = 48 h lead
n          = 33 days in series
noise_l    = noise_index[0..30]   # first 31 values
si_l       = SI%[2..32]           # last 31 values, shifted 2 rows forward

lagSI      = Pearson(noise_l, si_l)
hypothesis = "PASS" if lagSI > 0.4 else "FAIL"
tradable_p = 0.5 + |lagSI| × 0.4
hit_rate   = 0.6 + |lagSI| × 0.2
```

> **Note:** `SI%` (Short Interest %) comes from `docs/data/Stock Short Interest Data.csv`, not from the news/retail caches. The helper script demonstrates the Pearson structure using the noise series itself; the UI joins the CSV-derived SI column at `DataHub.getFilteredData()` (`docs/index.html` L990–1052).

#### E — Full daily series for TSLA (33 days, all from local cache)

| Date | nc | nv | rv | ns | rh | noise |
|---|---|---|---|---|---|---|
| 2021-01-06 | 8 | 0.800 | 0.735 | +0.014 | 0.561 | 54.17 |
| **2021-01-07** | 7 | 0.700 | 0.610 | −0.233 | 0.707 | 41.36 |
| **2021-01-08 ★** | **9** | **0.900** | **0.617** | **−0.008** | **0.706** | **55.66** |
| 2021-01-09 | 8 | 0.800 | 0.772 | +0.050 | 0.551 | 55.85 |
| 2021-01-22 | 10 | 1.000 | 0.612 | +0.444 | 0.523 | 62.39 ← peak news day |
| 2021-01-27 | 10 | 1.000 | 0.638 | +0.024 | 0.612 | 63.61 |
| 2021-11-07 | 10 | 1.000 | 0.750 | +0.126 | 0.621 | **68.80 ← highest** |

> All swan flags = True across all 33 days (high overall shock in this window; `shock > 5` threshold at L1076).

---

## 4. DEMO Mode (Offline-First)

| Cache file | Generator | Items | Mode |
|---|---|---|---|
| `docs/data/news_demo_cache.json` | `docs/data/generate_demo_caches.py` (319 lines) | ~1,500 | `DEMO` |
| `docs/data/retail_demo_cache.json` | same | ~2,000 | `DEMO` |

---

## 5. What is DEMO vs LIVE here?

### DEMO
- **Source:** `docs/data/generate_demo_caches.py` — fully deterministic Python script, reads `Stock Short Interest Data.csv`, generates synthetic headlines/posts via template strings and seeded random (L129–219).
- **URLs:** Constructed slugs (e.g., `wsj.com/articles/tsla-2021-01-08-3`) — fabricated, not real. Also 5% empty, 5% `placeholder.com`.
- **Labels in UI:** `mode: "DEMO"` on every item; `DataHub.classifyUrl()` (`docs/index.html` ~L1853) adds `DEMO_PLACEHOLDER` to `quality_flags`; `VIEW ORIGINAL SOURCE` button is locked (`🔒 DEMO — no external link`).
- **Network calls:** None. Entirely offline.

### LIVE
- **NewsAPI:** Produced by `$env:NEWSAPI_KEY = "key"; python tools/newsapi_oracle.py --ticker TSLA --days 7`. Writes `docs/data/news_live_cache.json`. URLs are **real** (from NewsAPI's `article.url`). UI auto-detects file on next load and shows `[LIVE]` badge (`DataHub.init()` L973).
- **Retail:** Produced by `python tools/browser_scout.py --mode live --seed scout.json`. Writes `docs/data/retail_live_cache.json`. Items sourced from manual collection per `tools/browser_scout.md`. UI detects and loads at `DataHub.init()` L976–977.
- **Deduplication:** Both live caches are deduped in the UI by `DataHub.dedupeEvidence()` (`docs/index.html` ~L1260) using Jaccard similarity, same thresholds as the offline aggregator.

---

## 6. Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        LIVE PATH (optional)                      │
│   $env:NEWSAPI_KEY = "key"                                       │
│   python tools/newsapi_oracle.py --ticker TSLA                   │
│       → docs/data/news_live_cache.json   (real URLs, mode=LIVE) │
│                                                                  │
│   python tools/browser_scout.py --mode live --seed scout.json   │
│       → docs/data/retail_live_cache.json (mode=LIVE)            │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                      DEMO PATH (always available)                │
│   docs/data/generate_demo_caches.py                              │
│       → docs/data/news_demo_cache.json   (~1,500 items, DEMO)   │
│       → docs/data/retail_demo_cache.json (~2,000 items, DEMO)   │
└──────────────────────────────────────────────────────────────────┘

              ▼  DataHub.init()  docs/index.html L944–990
              │  tries *_live_cache.json first; falls back to *_demo
              │
              ▼  DataHub.enrichCacheFlags()  L979
              │  adds DEMO_PLACEHOLDER to quality_flags for all DEMO items
              │
              ▼  DataHub.dedupeEvidence()  ~L1260
              │  Jaccard dedupe (title ≥0.92, excerpt ≥0.85, URL exact)
              │
              ▼  DataHub.computeRealIndices()  L1054–1150
              │  Per-day: nv, rv, ns, rh, swan detection
              │  noise_index = ((z(0.6·nv + 0.4·rv)) clamped + 5) × 10
              │
              ▼  DataHub.computeSubsetValidation()  L1449–1478
              │  lagSI = Pearson(noise[0..n-2], SI[2..n])   ← 48h lead
              │  PASS if lagSI > 0.4
              │
              ▼  React UI — Evidence Explorer + Lag Validation tabs
```

---

## 7. Summary of Files

| File | Action | Purpose |
|---|---|---|
| `tools/newsapi_oracle.py` | Pre-existing (167 lines) | NewsAPI LIVE adapter |
| `tools/browser_scout.md` | Pre-existing (98 lines) | Manual collection protocol |
| `tools/browser_scout.py` | Added this session | Offline/live retail aggregator with Jaccard dedupe + daily_series |
| `tools/verify_tool_orchestration_example.py` | Added this session | Offline helper: reproduces exact computeRealIndices math, prints per-day table |
| `docs/REPORT_tool_orchestration.md` | Updated this session | This document |

---

## 8. Validation Commands (PowerShell)

```powershell
cd C:\Users\78432\.gemini\antigravity\scratch\short_alpha_pod

# Reproduce the verifiable example (no network, no API key)
python tools/verify_tool_orchestration_example.py --ticker TSLA --day 2021-01-08

# Try another ticker/day
python tools/verify_tool_orchestration_example.py --ticker PYPL --day 2024-09-10

# Retail offline scout
python tools/browser_scout.py --ticker TSLA --mode offline

# NewsAPI LIVE (requires key)
$env:NEWSAPI_KEY = "YOUR_KEY"
python tools/newsapi_oracle.py --ticker TSLA --days 7

# Serve locally
python -m http.server 8000 --directory docs
# Open: http://localhost:8000/
```
