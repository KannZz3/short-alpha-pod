#!/usr/bin/env python3
"""
verify_tool_orchestration_example.py
=====================================
Reproduces the End-to-End Verifiable Example from
docs/REPORT_tool_orchestration.md using local DEMO cache files ONLY.

No network. No API key. Offline-first at all times.

Usage:
    python tools/verify_tool_orchestration_example.py
    python tools/verify_tool_orchestration_example.py --ticker PYPL --day 2024-09-10
"""

import json, math, argparse, os, sys
from collections import defaultdict

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "docs", "data")

def load_cache(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"[WARN] Missing: {path}")
        return []
    return json.load(open(path, encoding="utf-8"))

def pearson(x, y):
    n = min(len(x), len(y))
    if n < 2: return float("nan")
    x, y = x[:n], y[:n]
    mx, my = sum(x)/n, sum(y)/n
    num = sum((xi-mx)*(yi-my) for xi,yi in zip(x,y))
    sx  = math.sqrt(sum((xi-mx)**2 for xi in x))
    sy  = math.sqrt(sum((yi-my)**2 for yi in y))
    if sx*sy == 0: return float("nan")
    return round(num/(sx*sy), 6)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="TSLA")
    parser.add_argument("--day",    default="2021-01-08",
                        help="Specific day to spotlight in the example")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    spotlight_day = args.day

    # ── 1. Load caches ──────────────────────────────────────────────────────
    news_all   = load_cache("news_demo_cache.json")
    retail_all = load_cache("retail_demo_cache.json")
    news   = [x for x in news_all   if x.get("ticker") == ticker]
    retail = [x for x in retail_all if x.get("ticker") == ticker]

    if not news:
        print(f"[FAIL] No news items for {ticker} in DEMO cache."); sys.exit(1)

    # ── 2. Per-day buckets (mirrors DataHub.computeRealIndices L1066–1088) ──
    newsCount   = defaultdict(int)
    newsSentSum = defaultdict(float)
    newsSentN   = defaultdict(int)
    retailEngSum  = defaultdict(float)
    retailHypeSum = defaultdict(float)
    retailN       = defaultdict(int)

    SWAN_TAGS = {'regulatory','fraud','liquidity','lawsuit','halt','bankruptcy','sec','downgrade'}
    swanDays  = set()

    for n in news:
        d = (n.get("published_at_utc",""))[:10]
        if not d: continue
        newsCount[d]   += 1
        s = n.get("metrics",{}).get("sentiment", 0) or 0
        newsSentSum[d] += s
        newsSentN[d]   += 1
        shock = abs(n.get("metrics",{}).get("shock", 0) or 0)
        tags  = [str(t).lower() for t in n.get("tags",[])]
        if any(t in SWAN_TAGS for t in tags) or shock > 5:
            swanDays.add(d)

    for r in retail:
        d = (r.get("published_at_utc",""))[:10]
        if not d: continue
        eng  = r.get("metrics",{}).get("engagement", 1) or 1
        hype = abs(r.get("metrics",{}).get("sentiment", 0) or 0)
        retailEngSum[d]  += eng
        retailHypeSum[d] += hype
        retailN[d]       += 1
        tags = [str(t).lower() for t in r.get("tags",[])]
        if any(t in SWAN_TAGS for t in tags) or hype > 0.9:
            swanDays.add(d)

    # ── 3. Normalization and z-score (mirrors L1091–1125) ───────────────────
    all_days_sorted = sorted(set(list(newsCount.keys()) + list(retailEngSum.keys())))
    maxN = max(newsCount.values(),   default=1)
    maxR = max(retailEngSum.values(), default=1)

    rawCombined = []
    for d in all_days_sorted:
        nv = newsCount[d] / maxN
        rv = retailEngSum[d] / maxR
        rawCombined.append(0.6 * nv + 0.4 * rv)

    cMean = sum(rawCombined) / len(rawCombined)
    cVar  = sum((x-cMean)**2 for x in rawCombined) / len(rawCombined)
    cStd  = math.sqrt(cVar) or 1

    series = {}
    for i, d in enumerate(all_days_sorted):
        nc = newsCount[d]
        re = retailEngSum[d]
        nv = nc / maxN
        rv = re / maxR
        nsCnt = newsSentN[d]
        ns = (newsSentSum[d] / nsCnt) if nsCnt > 0 else 0
        rn = retailN[d]
        rh = min(1, retailHypeSum[d]/rn) if rn > 0 else 0
        zNoise   = (rawCombined[i] - cMean) / cStd
        noiseRaw = max(-5, min(5, zNoise))
        noise_index = round((noiseRaw + 5) * 10, 2)
        series[d] = {
            "nc": nc, "re": re,
            "nv": round(nv,4), "rv": round(rv,4),
            "ns": round(ns,4), "rh": round(rh,4),
            "raw_combined": round(0.6*nv+0.4*rv, 6),
            "z_noise": round(zNoise, 4),
            "noise_index": noise_index,
            "swan": 1 if d in swanDays else 0,
        }

    # ── 4. Spotlight day ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Tool Orchestration Verifiable Example")
    print(f"  Ticker: {ticker}  |  Spotlight day: {spotlight_day}")
    print(f"  Source: docs/data/{{news,retail}}_demo_cache.json")
    print(f"{'='*60}")

    if spotlight_day not in series:
        print(f"[WARN] {spotlight_day} not found for {ticker}. Available days:")
        for dd in sorted(series.keys())[:10]: print(f"  {dd}")
        sys.exit(1)

    d = spotlight_day
    s = series[d]
    print(f"\n  [A] NEWS (docs/index.html L1066–1077)")
    print(f"      Items in cache for {d}: {s['nc']}")
    print(f"      news_vol (nv) = {s['nc']}/{int(maxN)} = {s['nv']}")
    print(f"      avg_sentiment (ns) = {s['ns']}")
    print(f"      swan flag: {bool(s['swan'])}")

    print(f"\n  [B] RETAIL (docs/index.html L1078–1088)")
    print(f"      Items in cache for {d}: {retailN[d]}")
    print(f"      ret_vol (rv) = {s['re']}/{int(maxR)} = {s['rv']}")
    print(f"      hype (rh) = {s['rh']}")

    print(f"\n  [C] COMBINED NOISE (docs/index.html L1098–1125)")
    print(f"      raw_combined = 0.6 × {s['nv']} + 0.4 × {s['rv']} = {s['raw_combined']}")
    print(f"      series_mean  = {round(cMean,6)}")
    print(f"      series_std   = {round(cStd,6)}")
    print(f"      z_noise      = ({s['raw_combined']} - {round(cMean,6)}) / {round(cStd,6)} = {s['z_noise']}")
    print(f"      noise_index  = (clamp({s['z_noise']}, -5..5) + 5) × 10 = {s['noise_index']}")

    # ── 5. Lag validation: Pearson(noise[0..n-2], SI[2..n]) ─────────────────
    # We need SI data for this: use noise_index as a proxy signal series
    noise_series = [series[dd]["noise_index"] for dd in all_days_sorted]
    # We don't have SI in the cache; use the noise fluctuation itself as demo
    # (real SI comes from CSV — we just show the structure)
    days_arr = all_days_sorted
    n = len(noise_series)
    noise_l = noise_series[:n-2]
    # Shift by 2 rows = 48h
    noise_l_shifted = noise_series[2:]
    # Self-correlation (for structure demo; real SI loaded from CSV in UI)
    self_lag_corr = pearson(noise_l, noise_l_shifted)

    print(f"\n  [D] LAG VALIDATION (docs/index.html L1462–1477)")
    print(f"      Method: Pearson(noise[0..n-2], SI[2..n]) — 2-row = 48h lead")
    print(f"      Series length: {n} days  |  lag pairs: {n-2}")
    print(f"      NOTE: SI% comes from docs/data/Stock Short Interest Data.csv (not the cache)")
    print(f"      hypothesis: lagSI > 0.4 → PASS")
    print(f"      Demo self-correlation (noise→noise+2d, for structure only): {self_lag_corr}")

    print(f"\n  [E] ALL DAYS IN SERIES ({ticker})")
    print(f"  {'Date':12} {'nc':>5} {'nv':>7} {'rv':>7} {'ns':>7} {'rh':>5} {'noise':>7} swan")
    for dd in sorted(series.keys()):
        ss = series[dd]
        print(f"  {dd:12} {ss['nc']:>5} {ss['nv']:>7.4f} {ss['rv']:>7.4f} {ss['ns']:>7.4f} {ss['rh']:>5.3f} {ss['noise_index']:>7.2f}  {'*' if ss['swan'] else ''}")
    print()

if __name__ == "__main__":
    main()
