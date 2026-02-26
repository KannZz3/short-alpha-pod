"""
URL Integrity Audit for Short-Alpha Pod demo caches.
Produces docs/data/url_audit.json with per-URL results.
NewsAPI: NOT called. All evidence is deterministic DEMO mock.
"""
import json, re, os, sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS_CACHE  = os.path.join(ROOT, "docs", "data", "news_demo_cache.json")
RETAIL_CACHE = os.path.join(ROOT, "docs", "data", "retail_demo_cache.json")
OUT_PATH     = os.path.join(ROOT, "docs", "data", "url_audit.json")

PLACEHOLDER_DOMAINS = {"placeholder.com", "placeholder-social.com", "example.com"}

def classify_url(url, mode, existing_flags):
    """Return (classification, quality_flags_to_add)."""
    flags = list(existing_flags or [])

    if not url or url.strip() == "":
        if "EMPTY_URL" not in flags: flags.append("EMPTY_URL")
        return "EMPTY", flags

    # Syntax check: apostrophes in domain are illegal
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
    except Exception:
        if "INVALID_URL" not in flags: flags.append("INVALID_URL")
        return "INVALID_SYNTAX", flags

    if "'" in domain or "'" in domain:
        if "INVALID_URL" not in flags: flags.append("INVALID_URL")
        return "INVALID_SYNTAX", flags

    if not url.startswith("https://"):
        if "INVALID_URL" not in flags: flags.append("INVALID_URL")
        return "INVALID_SYNTAX", flags

    if domain in PLACEHOLDER_DOMAINS:
        if "PLACEHOLDER_URL" not in flags: flags.append("PLACEHOLDER_URL")
        return "PLACEHOLDER", flags

    # Constructed-fake: URL is structured as /<ticker>-<date>-<n> — slug doesn't point to a real article
    # The mode=DEMO + raw_ref=cache key confirms it was generated
    if mode == "DEMO":
        if "DEMO_PLACEHOLDER" not in flags: flags.append("DEMO_PLACEHOLDER")
        return "CONSTRUCTED_DEMO", flags

    return "OK", flags

def audit_cache(path, label):
    items = json.load(open(path, encoding="utf-8"))
    results = []
    counts = {"EMPTY": 0, "INVALID_SYNTAX": 0, "PLACEHOLDER": 0, "CONSTRUCTED_DEMO": 0, "OK": 0}
    for item in items:
        url   = item.get("url", "")
        mode  = item.get("mode", "DEMO")
        flags = item.get("quality_flags", [])
        cls, new_flags = classify_url(url, mode, flags)
        counts[cls] = counts.get(cls, 0) + 1
        results.append({
            "id":         item.get("id"),
            "ticker":     item.get("ticker"),
            "provider":   item.get("provider"),
            "url":        url,
            "classification": cls,
            "quality_flags": new_flags,
            "mode":        mode
        })
    return results, counts

print("Auditing news cache ...")
news_results, news_counts = audit_cache(NEWS_CACHE, "news")
print("Auditing retail cache ...")
ret_results,  ret_counts  = audit_cache(RETAIL_CACHE, "retail")

# Merge counts
total_counts = {}
for k in set(list(news_counts) + list(ret_counts)):
    total_counts[k] = news_counts.get(k, 0) + ret_counts.get(k, 0)

audit = {
    "generated_at": "2026-02-27T04:48:56+08:00",
    "newsapi_called": False,
    "all_items_mode_demo": True,
    "summary": {
        "news_items": len(news_results),
        "retail_items": len(ret_results),
        "total": len(news_results) + len(ret_results),
        "counts_news": news_counts,
        "counts_retail": ret_counts,
        "counts_total": total_counts,
    },
    "compliance": {
        "NewsAPI_called": "NO",
        "Browser_evidence_real": "NO — all items are deterministic DEMO mocks from generate_demo_caches.py",
        "URLs_externally_verified": "NO",
        "URL_integrity": "FAIL — all DEMO items have CONSTRUCTED_DEMO or worse URLs"
    },
    "news": news_results,
    "retail": ret_results
}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(audit, f, indent=2, ensure_ascii=False)

print(f"\nAudit written to {OUT_PATH}")
print(f"\n=== TOTALS ===")
for k, v in total_counts.items():
    print(f"  {k:20s}: {v}")
print(f"\nNewsAPI called:       NO")
print(f"Browser evidence real: NO")
print(f"Total items audited:  {audit['summary']['total']}")
