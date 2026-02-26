"""Verification script for data plumbing fixes."""
import sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_path = os.path.join(ROOT, "docs", "index.html")
html = open(html_path, encoding="utf-8").read()

ok = True
def chk(label, kw):
    global ok
    found = kw in html
    if not found: ok = False
    print(("[OK]  " if found else "[FAIL]") + " " + label)

# --- computeRealIndices rebuild ---
chk("real sentiment buckets",          "newsSentSum")
chk("SWAN_TAGS deterministic set",     "SWAN_TAGS")
chk("z-score zNoise",                  "zNoise")
chk("noise_index 0..100 rescale",      "noiseRaw + 5") 
chk("short alias nv: nc",              "nv: nc")
chk("short alias ns avg sentiment",    "newsSentSum[row.d]")
chk("short alias rv: re",              "rv: re")
chk("short alias rh hype",             "retailHypeSum[row.d]")
chk("swan detection swanDays",         "swanDays.has(row.d)")
chk("reason_flags array",              "reason_flags")
chk("legacy noise alias -4..4",        "noise_index / 100 * 8 - 4")

# --- current fallback ---
chk("current fallback _emptyRow",      "_emptyRow")
chk("fallback includes noise_index",   "noise_index: 0, nv: 0")

# --- scatterPoints ---
chk("scatterPoints uses noise_index",  "x: d.noise_index / 100")

# --- getVal ---
chk("getVal noise -> noise_index",     "d.noise_index || 0")
chk("getVal nv case",                  "metric === 'nv'")
chk("getVal rv case",                  "metric === 'rv'")
chk("getVal rh case",                  "metric === 'rh'")

# --- top card ---
chk("Noise card reads noise_index",    "noise_index, 1)")

# --- heatmap bands ---
chk("heatmap ns uses d.ns || 0",       "(d.ns || 0)")
chk("heatmap noise_index / 100",       "(d.noise_index || 0) / 100")

# --- tooltip ---
chk("tooltip Noise -> noise_index",    "filteredData[hoverIdx]?.noise_index")
chk("tooltip nv field",                "filteredData[hoverIdx]?.nv")
chk("tooltip rv field",                "filteredData[hoverIdx]?.rv")
chk("tooltip rh field",                "filteredData[hoverIdx]?.rh")

# --- cross-validation panel ---
chk("SERIES CROSS-VALIDATION block",   "SERIES CROSS-VALIDATION")
chk("ALL_FIELDS_FINITE check",         "ALL_FIELDS_FINITE")
chk("NEWS_SERIES line",                "NEWS_SERIES:")
chk("RETAIL_SERIES line",              "RETAIL_SERIES:")
chk("SWAN_EVENTS line",                "SWAN_EVENTS:")

print()
print("=" * 40)
print("RESULT: ALL PASS" if ok else "RESULT: SOME FAILURES")
sys.exit(0 if ok else 1)
