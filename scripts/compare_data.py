import os
import json
import datetime
import re

def compare_data():
    username = "Durgesh729"
    cache_dir = ".cache"
    years = [2024, 2025, 2026]
    
    # 1. Load processed history from history.json
    history_file = os.path.join("docs", "data", "history.json")
    if not os.path.exists(history_file):
        print(f"Error: Processed history file not found at: {history_file}")
        return
        
    with open(history_file, 'r', encoding='utf-8') as f:
        history_payload = json.load(f)
        
    processed_history = {item["date"]: item["count"] for item in history_payload.get("history", [])}
    
    # 2. Load stats from stats.json
    stats_file = os.path.join("docs", "data", "stats.json")
    if not os.path.exists(stats_file):
        print(f"Error: stats.json not found at: {stats_file}")
        return
        
    with open(stats_file, 'r', encoding='utf-8') as f:
        stats_payload = json.load(f)
        
    # Total days and lists
    days_compared = 0
    matched = 0
    mismatched = 0
    mismatches = []
    
    # Detailed date list for comparison table
    print(f"{'Date':<12} | {'GitHub Count':<12} | {'Processed Count':<15} | {'Status':<8}")
    print("-" * 57)
    
    for y in years:
        raw_path = os.path.join(cache_dir, f"raw_{username}_{y}.json")
        if not os.path.exists(raw_path):
            print(f"Error: Raw cache file not found at: {raw_path}")
            continue
            
        with open(raw_path, 'r', encoding='utf-8') as f:
            raw_calendar = json.load(f)
            
        # Parse every day from raw calendar belonging to year y
        for week in raw_calendar.get("weeks", []):
            for day in week.get("contributionDays", []):
                date_str = day["date"]
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                if date_obj.year != y:
                    continue
                    
                git_count = day["contributionCount"]
                processed_count = processed_history.get(date_str)
                
                days_compared += 1
                if processed_count is None:
                    # Missing in processed history
                    status = "MISSING"
                    mismatched += 1
                    mismatches.append((date_str, git_count, "None (Missing)"))
                elif git_count == processed_count:
                    status = "MATCH"
                    matched += 1
                else:
                    status = "MISMATCH"
                    mismatched += 1
                    mismatches.append((date_str, git_count, processed_count))
                    
                print(f"{date_str:<12} | {git_count:<12} | {str(processed_count):<15} | {status:<8}")

    print("\n" + "="*50)
    print("FINAL DATA AUDIT SUMMARY")
    print("="*50)
    print(f"Days Compared : {days_compared}")
    print(f"Matched       : {matched}")
    print(f"Mismatched    : {mismatched}")
    
    if mismatched > 0:
        print("\nMISMATCH DETAILS:")
        for m in mismatches:
            print(f"Date: {m[0]} | GitHub: {m[1]} | Processed: {m[2]}")
    else:
        print("\nPipeline is mathematically identical to GitHub GraphQL.")
        
    print("\n" + "="*50)
    print("TOTAL CONTRIBUTION COUNTS VERIFICATION")
    print("="*50)
    
    # Calculate sum(contributionCount) directly from raw GraphQL and compare with:
    # processor totalContributions
    # renderer totalContributions
    
    for y in years:
        raw_path = os.path.join(cache_dir, f"raw_{username}_{y}.json")
        with open(raw_path, 'r', encoding='utf-8') as f:
            raw_calendar = json.load(f)
            
        raw_sum = 0
        for week in raw_calendar.get("weeks", []):
            for day in week.get("contributionDays", []):
                date_obj = datetime.datetime.strptime(day["date"], "%Y-%m-%d").date()
                if date_obj.year == y:
                    raw_sum += day["contributionCount"]
                    
        # Processor total
        processor_total = stats_payload["yearly_summaries"][str(y)]["total_contributions"]
        
        # Renderer total (parsed from SVG file)
        svg_file = os.path.join("assets", f"skyline-{y}.svg")
        renderer_total = None
        if os.path.exists(svg_file):
            with open(svg_file, 'r', encoding='utf-8') as sf:
                svg_content = sf.read()
            # Match the text: e.g. <text x="1150" y="70" text-anchor="end" fill="#8b5cf6" font-size="24" font-weight="800">141</text>
            match = re.search(r'y="70"[^>]*>([\d,]+)</text>', svg_content)
            if match:
                renderer_total = int(match.group(1).replace(",", ""))
                
        print(f"Year {y}:")
        print(f"  Raw GraphQL sum       : {raw_sum}")
        print(f"  Processor Stats total : {processor_total}")
        print(f"  Renderer SVG total    : {renderer_total}")
        
        if raw_sum == processor_total == renderer_total:
            print(f"  -> status: MATCH (All 3 totals are identical: {raw_sum})")
        else:
            print(f"  -> status: FAIL (Totals differ! GraphQL={raw_sum}, Processor={processor_total}, Renderer={renderer_total})")
            
    print("="*50 + "\n")

if __name__ == "__main__":
    compare_data()
