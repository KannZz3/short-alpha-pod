"""Static QA for adaptive flag visualization."""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, "docs", "index.html"), encoding="utf-8").read()
ok = True
def chk(label, kw, must_exist=True):
    global ok
    found = kw in html
    if found != must_exist: ok = False
    status = "[OK]  " if found == must_exist else "[FAIL]"
    print(f"{status} {label}")

# ── Mode switching logic ──
chk("pixelsPerDay computation", "ppd       = xMax / numDays")
chk("PPD_INDIVIDUAL threshold = 14", "PPD_INDIVIDUAL = 14")
chk("PPD_CLUSTER threshold = 6",     "PPD_CLUSTER    = 6")
chk("CLUSTER_MERGE_PX = 12",         "CLUSTER_MERGE_PX = 12")

# ── MODE A: individual ──
chk("MODE A guard: ppd >= PPD_INDIVIDUAL", "ppd >= PPD_INDIVIDUAL")
chk("MODE A stable key FLAG suffix", "dayKey}-FLAG`")
chk("MODE A Icons.Flag render",      "Icons.Flag color=")

# ── MODE B: cluster badges ──
chk("MODE B guard: ppd >= PPD_CLUSTER", "ppd >= PPD_CLUSTER")
chk("MODE B CLUSTER suffix key",     "firstDay}-CLUSTER`")
chk("MODE B count badge text",       "n > 1 ? n : '!'")
chk("MODE B cluster title tooltip",  "click to inspect")
chk("MODE B greedy merge loop",      "CLUSTER_MERGE_PX")

# ── MODE C: density band ──
chk("MODE C eventByDay Map",         "eventByDay = new Map")
chk("MODE C BAND_Y above heatmap",   "BAND_Y = height - p - 43")
chk("MODE C rect intensity",         "intensity = ev ? 0.8")
chk("MODE C date labels slice",      "ev.dayKey.slice(5)")
chk("MODE C title tooltip",          "ev.reason}")

# ── Diagnostic ──
chk("console.debug [FLAGS]",         "console.debug('[FLAGS] diag'")
chk("overlapRisk label",             "overlapRisk")
chk("mode label in diagnostic",      "'INDIVIDUAL'")
chk("mode label CLUSTER in diag",    "'CLUSTER'")
chk("mode label BAND in diag",       "'BAND'")

# ── Click handler preserved ──
chk("setSelectedDate in cluster",    "setSelectedDate(firstDay)")
chk("setSelectedDate in band",       "setSelectedDate(d.d)")
chk("setTab evidence in all modes",  "setTab('evidence')", must_exist=True)

# ── Fallback preserved ──
chk("swan-leg fallback dots still present", "swan-leg-")

print()
print("=" * 40)
print("RESULT: ALL PASS" if ok else "RESULT: SOME FAILURES")
sys.exit(0 if ok else 1)
