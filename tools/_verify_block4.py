"""Quick Block4 compliance verification script."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok = True

def chk(label, cond, detail=""):
    global ok
    status = "[OK]  " if cond else "[FAIL]"
    if not cond:
        ok = False
    print(f"{status} {label}" + (f"  ({detail})" if detail else ""))

# ── JSON files ──────────────────────────────────────────────────────────────
snap_path = os.path.join(ROOT, "docs", "data", "daily_snapshot.json")
rc_path   = os.path.join(ROOT, "docs", "data", "regime_catalog.json")

try:
    snap = json.load(open(snap_path))
    chk("daily_snapshot.json valid", True)
    chk("  mode_label=DEMO",         snap.get("mode_label") == "DEMO")
    chk("  5 tickers present",       len(snap.get("tickers", {})) == 5,
        str(list(snap.get("tickers", {}).keys())))
    afrm_proxy = snap["tickers"].get("AFRM", {}).get("pro_metrics_proxy", {})
    chk("  AFRM days_to_cover > 0",  afrm_proxy.get("days_to_cover", 0) > 0,
        str(afrm_proxy.get("days_to_cover")))
    chk("  AFRM borrow_fee_pct_est", afrm_proxy.get("borrow_fee_pct_est", 0) >= 0)
    chk("  proxy_label says PROXY",  "PROXY" in afrm_proxy.get("proxy_label", ""))
except Exception as e:
    chk("daily_snapshot.json", False, str(e))

try:
    rc = json.load(open(rc_path))
    chk("regime_catalog.json valid",    True)
    chk("  6 regimes",                  len(rc.get("regimes", [])) == 6,
        str(len(rc.get("regimes", []))))
    chk("  ticker_sector_map 5 tickers",len(rc.get("ticker_sector_map", {})) == 5)
    ids = [r["scenario_id"] for r in rc["regimes"]]
    chk("  borrow_fee_spike present",   "borrow_fee_spike" in ids)
except Exception as e:
    chk("regime_catalog.json", False, str(e))

# ── index.html keyword checks ───────────────────────────────────────────────
html_path = os.path.join(ROOT, "docs", "index.html")
try:
    html = open(html_path, encoding="utf-8").read()
    checks = [
        ("DEMO/LIVE badge (_liveNewsLoaded)",   "_liveNewsLoaded"),
        ("SQUEEZE_ORACLE_MODE flag",            "SQUEEZE_ORACLE_MODE: false"),
        ("showDemoLiveLabel flag",              "showDemoLiveLabel: true"),
        ("computeShockScore function",          "computeShockScore:"),
        ("getBorrowProxy function",             "getBorrowProxy:"),
        ("regime_catalog.json fetch",           "regime_catalog.json"),
        ("daily_snapshot.json fetch",           "daily_snapshot.json"),
        ("SHOCK vs REVERSION card",             "SHOCK vs REVERSION"),
        ("DAYS_TO_COVER borrow proxy UI",       "DAYS_TO_COVER"),
        ("TICKER_SECTOR_MAP",                   "TICKER_SECTOR_MAP"),
        ("getDefaultScenarioForTicker",         "getDefaultScenarioForTicker"),
        ("Combo EXPORT ALL button",             "EXPORT ALL"),
        ("Version v1.0.13",                     "v1.0.13"),
        ("ORACLE date badge",                   "ORACLE:{DataHub"),
        ("_liveNewsLoaded = true setter",       "DataHub._liveNewsLoaded = true"),
        ("PROVIDER_QUALITY weights",            "PROVIDER_QUALITY"),
        ("Block4-A comment",                    "Block4-A"),
        ("Block4-B comment",                    "Block4-B"),
        ("Block4-C comment",                    "Block4-C"),
    ]
    for label, kw in checks:
        chk(f"  HTML: {label}", kw in html)
except Exception as e:
    chk("index.html readable", False, str(e))

# ── tool stubs ──────────────────────────────────────────────────────────────
for fname in ["run_daily_demo.py", "newsapi_oracle.py", "browser_scout.md"]:
    p = os.path.join(ROOT, "tools", fname)
    chk(f"tools/{fname} exists", os.path.exists(p))

print()
print("=" * 40)
print("RESULT: ALL PASS" if ok else "RESULT: SOME FAILURES — see [FAIL] lines above")
sys.exit(0 if ok else 1)
