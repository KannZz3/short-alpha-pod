"""Verify red flag overlap fix."""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, "docs", "index.html"), encoding="utf-8").read()
ok = True
def chk(label, kw):
    global ok
    found = kw in html
    if not found: ok = False
    print(("[OK]  " if found else "[FAIL]") + " " + label)

chk("getNewsSignalFlags function",         "getNewsSignalFlags:")
chk("normDayKey UTC normalization",        "normDayKey")
chk("toISOString().split('T')[0]",         ".toISOString().split('T')[0]")
chk("per-day bucket daySignal",            "daySignal[dk]")
chk("z-score threshold Z_THRESH",         "Z_THRESH")
chk("flagMap Map deduplication",           "flagMap = new Map()")
chk("SWAN_TAGS in getNewsSignalFlags",     "SWAN_TAGS.has(t)) || shock > 5")
chk("allDayKeys unified merge Map",        "allDayKeys = new Map()")
chk("swanMap per-day dedupe",              "swanMap = new Map()")
chk("stable key ticker+window+dayKey",    "ticker}-${winStart}-${winEnd}-${dayKey}-FLAG")
chk("y-offset for SWAN vs NEWS",           "isSwanFromData ? 8 : 12")
chk("flag color by reason",               "reason.includes('SWAN')")
chk("fallback deduped dots (seen Set)",   "seen = new Set()")
chk("old per-row renderer removed",       "swan-${i}")  # should NOT exist

# The last check should FAIL (meaning the old pattern is gone)
old_found = "swan-${i}" in html
chk_label = "old per-row key sw-i REMOVED"
if old_found:
    ok = False
    print(f"[FAIL] {chk_label}  (still found!)")
else:
    print(f"[OK]   {chk_label}")

print()
print("=" * 40)
print("RESULT: ALL PASS" if ok else "RESULT: SOME FAILURES")
sys.exit(0 if ok else 1)
