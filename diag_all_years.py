"""
Diagnostic: ALL YEARS total contributions root-cause analysis
Run from the project root: python diag_all_years.py
"""
import os, sys, json, copy, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from scripts.config import ConfigManager
from scripts.processor import ContributionProcessor

SEP  = "=" * 70

def hdr(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

# ── 1. Load config ────────────────────────────────────────────────────────────
hdr("STAGE 1 – Configuration")
cfg = ConfigManager(os.path.join(ROOT, "config.json"))
username   = cfg.username
cache_dir  = os.path.join(ROOT, ".cache")
print(f"  username   : {username}")
print(f"  cache_dir  : {cache_dir}")

# ── 2. Inspect every cache file ──────────────────────────────────────────────
hdr("STAGE 2 – Cache File Inventory")

cache_files = sorted(
    f for f in os.listdir(cache_dir)
    if f.startswith(f"raw_{username}_") and f.endswith(".json")
)

cache_data = {}
yearly_cache_totals = {}

for fname in cache_files:
    path = os.path.join(cache_dir, fname)
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)

    year_str = fname.replace(f"raw_{username}_", "").replace(".json", "")
    try:
        year = int(year_str)
    except ValueError:
        continue

    source       = raw.get("source", "UNKNOWN")
    generated_at = raw.get("generated_at", "UNKNOWN")
    total_in_cal = raw.get("totalContributions", "MISSING")
    weeks        = raw.get("weeks", [])
    weeks_count  = len(weeks)

    day_count    = sum(len(w.get("contributionDays", [])) for w in weeks)
    sum_in_weeks = sum(
        d.get("contributionCount", 0)
        for w in weeks
        for d in w.get("contributionDays", [])
    )

    print(f"\n  [{year}]  {fname}")
    print(f"    source               : {source}")
    print(f"    generated_at         : {generated_at}")
    print(f"    totalContributions   : {total_in_cal}")
    print(f"    weeks count          : {weeks_count}")
    print(f"    calendar day count   : {day_count}")
    print(f"    sum of all day counts: {sum_in_weeks:,}")

    if total_in_cal != "MISSING" and int(total_in_cal) != sum_in_weeks:
        print(f"    *** HEADER TOTAL {total_in_cal} != WEEK-SUM {sum_in_weeks} ***")

    cache_data[year] = raw
    yearly_cache_totals[year] = sum_in_weeks

# ── 3. Processor per-year totals ─────────────────────────────────────────────
hdr("STAGE 3 – ContributionProcessor (per-year)")

metadata_cache = os.path.join(cache_dir, f"metadata_{username}.json")
repo_count = 0
if os.path.exists(metadata_cache):
    with open(metadata_cache, encoding="utf-8") as fh:
        meta = json.load(fh)
    repo_count = meta.get("repo_count", 0)

processor = ContributionProcessor(username, repo_count)
for year in sorted(cache_data.keys()):
    processor.add_year_data(year, cache_data[year])

processor_totals = {}
for year in sorted(cache_data.keys()):
    summary    = processor.yearly_summaries.get(str(year), {})
    proc_total = summary.get("total_contributions", 0)
    active     = summary.get("active_days", 0)
    days_count = summary.get("days_count", 0)
    max_daily  = summary.get("max_daily_contributions", 0)
    processor_totals[year] = proc_total
    cache_total = yearly_cache_totals.get(year, 0)
    match = "MATCH" if proc_total == cache_total else f"*** MISMATCH cache={cache_total:,} ***"
    print(f"\n  [{year}]  processor={proc_total:,}  active={active}  days={days_count}  max={max_daily}  [{match}]")

grand_total_processor = sum(processor_totals.values())
print(f"\n  Grand total (sum of all processor years) : {grand_total_processor:,}")

# ── 4. _compile_all_years_calendar ───────────────────────────────────────────
hdr("STAGE 4 – _compile_all_years_calendar aggregation")

raw_calendars = {y: cache_data[y] for y in sorted(cache_data.keys())}

sample_year  = list(raw_calendars.keys())[0]
sample_cal   = raw_calendars[sample_year]
all_calendar = copy.deepcopy(sample_cal)
all_weeks    = all_calendar["weeks"]

print(f"  Blueprint year       : {sample_year}")
print(f"  Blueprint weeks      : {len(all_weeks)}")
print(f"  Years being merged   : {sorted(raw_calendars.keys())}\n")

for y, cal in raw_calendars.items():
    yw   = cal["weeks"]
    flag = "" if len(yw) == len(all_weeks) else f"  *** DIFFERENT FROM BLUEPRINT ({len(all_weeks)}) ***"
    print(f"    [{y}] weeks = {len(yw)}{flag}")

# Zero out blueprint
for week in all_weeks:
    for day in week["contributionDays"]:
        day["contributionCount"] = 0

total_accumulated = 0
cell_count        = 0

for w_idx in range(len(all_weeks)):
    blueprint_days = all_weeks[w_idx]["contributionDays"]
    for d_idx in range(len(blueprint_days)):
        cell_sum = 0
        for y, calendar in raw_calendars.items():
            year_weeks = calendar["weeks"]
            if w_idx < len(year_weeks):
                year_days = year_weeks[w_idx]["contributionDays"]
                if d_idx < len(year_days):
                    day = year_days[d_idx]
                    # FIXED: mirror processor.py:40 — skip cross-year boundary days
                    if day.get("date", "")[:4] == str(y):
                        cell_sum += day["contributionCount"]
        blueprint_days[d_idx]["contributionCount"] = cell_sum
        total_accumulated += cell_sum
        cell_count        += 1

all_calendar["totalContributions"] = total_accumulated

print(f"\n  Total cells iterated                    : {cell_count}")
print(f"  total_accumulated (aggregation result)  : {total_accumulated:,}")
print(f"  Grand total from processor              : {grand_total_processor:,}")

if total_accumulated != grand_total_processor:
    diff = total_accumulated - grand_total_processor
    print(f"\n  *** DIVERGENCE DETECTED ***")
    print(f"    diff = {diff:+,}")
    print(f"\n  Per-year positional contribution to aggregation:")
    for y, cal in raw_calendars.items():
        y_positional = sum(
            cal["weeks"][w_idx]["contributionDays"][d_idx]["contributionCount"]
            if w_idx < len(cal["weeks"]) and d_idx < len(cal["weeks"][w_idx]["contributionDays"]) else 0
            for w_idx in range(len(all_weeks))
            for d_idx in range(len(all_weeks[w_idx]["contributionDays"]))
        )
        proc_y = processor_totals.get(y, 0)
        flag = "" if y_positional == proc_y else f"  *** pos={y_positional:,} != proc={proc_y:,} ***"
        print(f"    [{y}]  positional={y_positional:,}  processor={proc_y:,}{flag}")

# ── 5. Stats object ───────────────────────────────────────────────────────────
hdr("STAGE 5 – Stats object")

streaks        = processor.calculate_streaks()
all_time_total = sum(s["total_contributions"] for s in processor.yearly_summaries.values())
stats = {
    "username"            : processor.username,
    "total_contributions" : all_time_total,
    "longest_streak"      : streaks["longest_streak"],
    "current_streak"      : streaks["current_streak"],
    "yearly_summaries"    : processor.yearly_summaries,
}
print(f"  stats['total_contributions']  : {stats['total_contributions']:,}")
print(f"  yearly_summaries keys         : {sorted(stats['yearly_summaries'].keys())}")
print(f"  'ALL YEARS' key present?      : {'ALL YEARS' in stats['yearly_summaries']}")

# ── 6. Renderer input ─────────────────────────────────────────────────────────
hdr("STAGE 6 – Renderer input (exact logic of render_svg)")

label               = "ALL YEARS"
total_from_calendar = all_calendar.get("totalContributions", 0)

if str(label) in stats.get("yearly_summaries", {}):
    final_total = stats["yearly_summaries"][str(label)]["total_contributions"]
    print(f"  Label '{label}' FOUND in yearly_summaries -> stats override applied")
else:
    final_total = total_from_calendar
    print(f"  Label '{label}' NOT in yearly_summaries -> using calendar.totalContributions")

print(f"  calendar.totalContributions   : {total_from_calendar:,}")
print(f"  Rendered total (SVG output)   : {final_total:,}")

# ── 7. Root cause ─────────────────────────────────────────────────────────────
hdr("STAGE 7 – Root Cause Summary")

EXPECTED = grand_total_processor
print(f"  Processor grand total         : {EXPECTED:,}")
print(f"  Aggregation total_accumulated : {total_accumulated:,}")
print(f"  Stats total_contributions     : {stats['total_contributions']:,}")
print(f"  SVG rendered value            : {final_total:,}")
print()

stages = [
    ("_compile_all_years total_accumulated", total_accumulated),
    ("stats['total_contributions']",         stats['total_contributions']),
    ("SVG rendered value",                   final_total),
]

divergence_found = False
for sname, sval in stages:
    if sval != EXPECTED and not divergence_found:
        print(f"  ROOT CAUSE -> First divergence at  : {sname}")
        print(f"    Expected : {EXPECTED:,}")
        print(f"    Got      : {sval:,}")
        print(f"    Delta    : {sval - EXPECTED:+,}")
        divergence_found = True

if not divergence_found:
    print("  All stages match grand_total_processor. No divergence found.")
    print(f"  Displayed value should be {final_total:,}.")

print(f"\n{SEP}")
print("  DIAGNOSTIC COMPLETE")
print(SEP)
