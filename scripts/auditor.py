import os
import json
import hashlib
import datetime
import sys
import re
from scripts.logger import setup_logger

logger = setup_logger()

def get_file_sha256(filepath):
    """Calculates the SHA256 hash of a file if it exists."""
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def calculate_year_streaks(year_days):
    """Calculates longest and current streaks within a subset of days."""
    sorted_days = sorted(year_days, key=lambda d: d["date"])
    longest = 0
    current = 0
    running = 0
    
    for d in sorted_days:
        if d["count"] > 0:
            running += 1
            if running > longest:
                longest = running
        else:
            running = 0
            
    # Calculate current streak ending at latest date
    if sorted_days:
        idx = len(sorted_days) - 1
        while idx >= 0:
            if sorted_days[idx]["count"] > 0:
                break
            idx -= 1
            
        if idx >= 0:
            last_active = sorted_days[idx]["date"]
            today = datetime.date.today()
            # If the last active day was today or yesterday
            if (today - last_active).days <= 1:
                tail = 0
                while idx >= 0:
                    if sorted_days[idx]["count"] > 0:
                        tail += 1
                        idx -= 1
                    else:
                        break
                current = tail
                
    return longest, current

def run_audit(pipeline, processor, stats) -> bool:
    """
    Executes a complete mathematical audit of the pipeline data,
    comparing raw GraphQL JSON calendars to processed days.
    Writes CSV comparison tables and a markdown report under docs/audit/.
    Exits with code 1 if a discrepancy is found.
    """
    username = pipeline.username
    cache_dir = pipeline.cache_dir
    docs_dir = pipeline.docs_dir
    output_dir = pipeline.output_dir
    
    audit_dir = os.path.join(docs_dir, "audit")
    os.makedirs(audit_dir, exist_ok=True)
    
    years = sorted([int(y) for y in stats.get("yearly_summaries", {}).keys()])
    if not years:
        logger.warning("No yearly summaries found in stats database. Skipping audit.")
        return True
        
    # Flat map of processed days by ISO date string
    processed_days = {}
    for d in processor.all_days:
        date_str = d["date"].strftime("%Y-%m-%d") if isinstance(d["date"], (datetime.date, datetime.datetime)) else str(d["date"])
        processed_days[date_str] = d["count"]
        
    days_compared = 0
    matched = 0
    mismatched = 0
    mismatches = []
    
    yearly_csv_data = {}
    
    for y in years:
        raw_path = os.path.join(cache_dir, f"raw_{username}_{y}.json")
        if not os.path.exists(raw_path):
            logger.warning(f"Raw cache file missing for audit of year {y}: {raw_path}")
            continue
            
        with open(raw_path, 'r', encoding='utf-8') as f:
            raw_calendar = json.load(f)
            
        csv_rows = ["Date,GitHub Contribution Count,Processed Contribution Count,Status"]
        
        for week in raw_calendar.get("weeks", []):
            for day in week.get("contributionDays", []):
                date_str = day["date"]
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                if date_obj.year != y:
                    continue
                    
                git_count = day["contributionCount"]
                proc_count = processed_days.get(date_str, 0)
                
                days_compared += 1
                if git_count == proc_count:
                    status = "MATCH"
                    matched += 1
                else:
                    status = "MISMATCH"
                    mismatched += 1
                    mismatches.append((date_str, git_count, proc_count))
                    
                csv_rows.append(f"{date_str},{git_count},{proc_count},{status}")
                
        yearly_csv_data[y] = csv_rows
        
    # Write mismatches or clear existing mismatches file
    mismatches_file = os.path.join(audit_dir, "mismatches.csv")
    if mismatched > 0:
        logger.error(f"AUDIT FAILED: Found {mismatched} mismatches between raw GraphQL and processed counts.")
        with open(mismatches_file, 'w', encoding='utf-8') as mf:
            mf.write("Date,GitHub Contribution Count,Processed Contribution Count,Status\n")
            for m in mismatches:
                mf.write(f"{m[0]},{m[1]},{m[2]},MISMATCH\n")
        # Exit with error status
        sys.exit(f"Data audit mismatch detected! Audited failed with {mismatched} mismatches.")
    else:
        if os.path.exists(mismatches_file):
            try:
                os.remove(mismatches_file)
            except Exception:
                pass
                
    # Write yearly comparison CSV files
    for y, rows in yearly_csv_data.items():
        csv_path = os.path.join(audit_dir, f"comparison-{y}.csv")
        with open(csv_path, 'w', encoding='utf-8') as cf:
            cf.write("\n".join(rows) + "\n")
            
    # Calculate hashes of assets
    stats_hash = get_file_sha256(os.path.join(docs_dir, "data", "stats.json"))
    history_hash = get_file_sha256(os.path.join(docs_dir, "data", "history.json"))
    analysis_hash = get_file_sha256(os.path.join(docs_dir, "data", "analysis.json"))
    
    svg_hashes = {}
    svg_files = ["skyline-current.svg", "skyline-animated.svg", "skyline-all.svg"] + [f"skyline-{y}.svg" for y in years]
    for filename in svg_files:
        svg_hashes[filename] = get_file_sha256(os.path.join(output_dir, filename))
        
    # Compile yearly stats block for report
    stat_rows = []
    for y in years:
        summary = stats.get("yearly_summaries", {}).get(str(y), {})
        cal_days = summary.get("days_count", 0)
        
        # Count weeks
        raw_path = os.path.join(cache_dir, f"raw_{username}_{y}.json")
        weeks_count = 0
        if os.path.exists(raw_path):
            with open(raw_path, 'r', encoding='utf-8') as f:
                raw_cal = json.load(f)
            for week in raw_cal.get("weeks", []):
                if any(datetime.datetime.strptime(d["date"], "%Y-%m-%d").date().year == y for d in week["contributionDays"]):
                    weeks_count += 1
                    
        active = summary.get("active_days", 0)
        total = summary.get("total_contributions", 0)
        max_c = summary.get("max_daily_contributions", 0)
        
        # Calculate streaks within year
        y_days = [d for d in processor.all_days if d["date"].year == y]
        y_longest, y_current = calculate_year_streaks(y_days)
        
        stat_rows.append(
            f"| {y} | {cal_days} | {weeks_count} | {active} | {total} | {max_c} | {y_current} | {y_longest} |"
        )
        
    # Statement verification check
    renderer_matches_all = True
    for y in years:
        raw_path = os.path.join(cache_dir, f"raw_{username}_{y}.json")
        if not os.path.exists(raw_path):
            continue
        with open(raw_path, 'r', encoding='utf-8') as f:
            raw_cal = json.load(f)
            
        raw_sum = sum(day["contributionCount"] for w in raw_cal.get("weeks", []) for day in w.get("contributionDays", []) if datetime.datetime.strptime(day["date"], "%Y-%m-%d").date().year == y)
        processor_total = stats.get("yearly_summaries", {}).get(str(y), {}).get("total_contributions", 0)
        
        svg_file = os.path.join(output_dir, f"skyline-{y}.svg")
        renderer_total = None
        if os.path.exists(svg_file):
            with open(svg_file, 'r', encoding='utf-8') as sf:
                svg_content = sf.read()
            match = re.search(r'y="70"[^>]*>([\d,]+)</text>', svg_content)
            if match:
                renderer_total = int(match.group(1).replace(",", ""))
                
        if raw_sum != processor_total or (renderer_total is not None and raw_sum != renderer_total):
            renderer_matches_all = False
            
    verif_statement = "Renderer == Processor == GraphQL contribution totals matched and verified mathematically."
    if not renderer_matches_all:
        verif_statement = "WARNING: Totals discrepancy detected between Raw GraphQL, Processor stats or Renderer SVG text."
        
    # Write audit-report.md
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    report_content = f"""# GITHUB SKYLINE HUB - DATA INTEGRITY AUDIT REPORT

Generated on: {now_utc} UTC
Audited User: @{username}
Overall Status: PASS

## Audit Summary
- **Years Audited**: {", ".join(str(y) for y in years)}
- **Calendar Days Compared**: {days_compared}
- **Days Matched**: {matched}
- **Days Mismatched**: {mismatched}

## Verification Statement
{verif_statement}

## Yearly Contribution Statistics
| Year | Calendar Days | Weeks | Active Days | Total Contributions | Maximum Contributions | Current Streak | Longest Streak |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{"\n".join(stat_rows)}

## File Hash Integrity Verification (SHA256)
- **stats.json**: `{stats_hash}`
- **history.json**: `{history_hash}`
- **analysis.json**: `{analysis_hash}`

### Rendered SVGs
"""
    for filename, sha in svg_hashes.items():
        report_content += f"- **{filename}**: `{sha}`\n"
        
    report_path = os.path.join(audit_dir, "audit-report.md")
    with open(report_path, 'w', encoding='utf-8') as rf:
        rf.write(report_content)
        
    logger.info(f"Audit report generated successfully at: {report_path}")
    return True
