import os
import json
import datetime
from scripts.logger import setup_logger

logger = setup_logger()

class ContributionProcessor:
    """
    Processes raw contribution data from GitHub GraphQL API.
    Calculates year-by-year totals, active days, averages, and computes
    chronological streaks (current and longest).
    """
    def __init__(self, username, repo_count=0):
        self.username = username
        self.repo_count = repo_count
        self.all_days = []  # List of dicts: {"date": datetime.date, "count": int}
        self.yearly_summaries = {}

    def add_year_data(self, year, calendar_data):
        """
        Parses calendar data for a specific year and extracts all days.
        """
        if not calendar_data or "weeks" not in calendar_data:
            logger.warning(f"No contribution data to process for year {year}.")
            return
            
        year_days = []
        max_daily = 0
        active_days_count = 0
        
        for week in calendar_data["weeks"]:
            for day in week.get("contributionDays", []):
                date_str = day["date"]
                count = day["contributionCount"]
                
                try:
                    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                    # Filter out overlap days from adjacent years
                    if date_obj.year != year:
                        continue
                        
                    # Deduplicate day entries
                    if any(d["date"] == date_obj for d in year_days):
                        continue
                        
                    day_item = {"date": date_obj, "count": count}
                    year_days.append(day_item)
                    self.all_days.append(day_item)
                    
                    if count > max_daily:
                        max_daily = count
                    if count > 0:
                        active_days_count += 1
                except ValueError as e:
                    logger.error(f"Error parsing date string '{date_str}': {e}")
                    
        year_total = sum(d["count"] for d in year_days)
        day_count = len(year_days)
        avg_daily = round(year_total / day_count, 2) if day_count > 0 else 0.0

        self.yearly_summaries[str(year)] = {
            "total_contributions": year_total,
            "max_daily_contributions": max_daily,
            "active_days": active_days_count,
            "average_daily_contributions": avg_daily,
            "days_count": day_count
        }
        
        logger.info(f"Processed year {year}: Total={year_total}, Max={max_daily}, Active={active_days_count}")

    def calculate_streaks(self):
        """
        Sorts all accumulated days chronologically and calculates:
        1. Longest contribution streak (all-time)
        2. Current active contribution streak (ending today or yesterday)
        """
        if not self.all_days:
            return {"longest_streak": 0, "current_streak": 0}
            
        # De-duplicate and sort by date
        unique_days = {d["date"]: d["count"] for d in self.all_days}
        sorted_dates = sorted(unique_days.keys())
        
        longest_streak = 0
        current_streak = 0
        running_streak = 0
        
        # Calculate streaks
        for date in sorted_dates:
            count = unique_days[date]
            if count > 0:
                running_streak += 1
                if running_streak > longest_streak:
                    longest_streak = running_streak
            else:
                running_streak = 0
                
        # Calculate current active streak ending on the latest available date
        # Let's inspect the last few days in our dataset
        if sorted_dates:
            latest_date = sorted_dates[-1]
            today = datetime.date.today()
            
            # Find running streak at the tail
            tail_running = 0
            idx = len(sorted_dates) - 1
            
            # Start scanning backwards to find the current active streak
            # Find the most recent date with contributions
            while idx >= 0:
                date = sorted_dates[idx]
                count = unique_days[date]
                if count > 0:
                    break
                idx -= 1
                
            if idx >= 0:
                last_active_date = sorted_dates[idx]
                # If the last active contribution is within 1 day of today (or yesterday),
                # the current streak is still active.
                # If we're offline or looking at historical cached data, we check distance
                # to the latest date in the dataset instead of actual physical 'today'.
                max_reference_date = max(today, latest_date)
                
                # Check distance
                delta = max_reference_date - last_active_date
                if delta.days <= 1:
                    # Trace back to find length of this active streak
                    while idx >= 0:
                        if unique_days[sorted_dates[idx]] > 0:
                            tail_running += 1
                            idx -= 1
                        else:
                            break
                    current_streak = tail_running
                else:
                    current_streak = 0
            else:
                current_streak = 0

        logger.info(f"Calculated streaks: Longest={longest_streak} days, Current={current_streak} days")
        return {
            "longest_streak": longest_streak,
            "current_streak": current_streak
        }

    def generate_stats_json(self, docs_dir, available_themes=None):
        """
        Creates a unified stats JSON file containing all-time aggregates,
        yearly summaries, and streaks. Saves it to docs/data/stats.json.
        """
        streaks = self.calculate_streaks()
        all_time_total = sum(summary["total_contributions"] for summary in self.yearly_summaries.values())
        
        stats_payload = {
            "username": self.username,
            "total_contributions": all_time_total,
            "longest_streak": streaks["longest_streak"],
            "current_streak": streaks["current_streak"],
            "repository_count": self.repo_count,
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "yearly_summaries": self.yearly_summaries,
            "available_themes": available_themes or ["cyberpunk"]
        }
        
        # Ensure output directory exists
        stats_dir = os.path.join(docs_dir, 'data')
        os.makedirs(stats_dir, exist_ok=True)
        stats_file = os.path.join(stats_dir, 'stats.json')
        
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_payload, f, indent=2)
            logger.info(f"Successfully generated stats JSON at: {stats_file}")
        except IOError as e:
            logger.error(f"Failed to write stats JSON: {e}")
            
        return stats_payload

    def generate_analysis_json(self, docs_dir):
        """
        Generates docs/data/analysis.json containing advanced productivity analysis and AI insights.
        """
        if not self.all_days:
            return {}

        sorted_days = sorted(self.all_days, key=lambda d: d["date"])
        streaks = self.calculate_streaks()
        
        total_days = len(sorted_days)
        total_contributions = sum(d["count"] for d in sorted_days)
        active_days = sum(1 for d in sorted_days if d["count"] > 0)
        avg_daily = round(total_contributions / total_days, 2) if total_days > 0 else 0.0
        
        month_totals = {}
        for d in sorted_days:
            month_key = d["date"].strftime("%Y-%m")
            month_totals[month_key] = month_totals.get(month_key, 0) + d["count"]
            
        best_month_key = max(month_totals, key=month_totals.get) if month_totals else "N/A"
        best_month_val = month_totals.get(best_month_key, 0)
        if best_month_key != "N/A":
            try:
                best_month_date = datetime.datetime.strptime(best_month_key, "%Y-%m")
                best_month_name = best_month_date.strftime("%B %Y")
            except ValueError:
                best_month_name = best_month_key
        else:
            best_month_name = "N/A"
            
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday_totals = {i: 0 for i in range(7)}
        for d in sorted_days:
            weekday_totals[d["date"].weekday()] += d["count"]
            
        best_weekday_idx = max(weekday_totals, key=weekday_totals.get) if sorted_days else 0
        most_productive_weekday = weekday_names[best_weekday_idx]
        
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        month_name_totals = {i: 0 for i in range(1, 13)}
        for d in sorted_days:
            month_name_totals[d["date"].month] += d["count"]
            
        best_month_idx = max(month_name_totals, key=month_name_totals.get) if sorted_days else 1
        most_productive_month = month_names[best_month_idx - 1]
        
        active_ratio = active_days / total_days if total_days > 0 else 0.0
        density_ratio = min(avg_daily, 4.0) / 4.0
        productivity_score = min(100, int((active_ratio * 70) + (density_ratio * 30)))
        if total_contributions == 0:
            productivity_score = 0
            
        yoy_growth = {}
        sorted_years = sorted(self.yearly_summaries.keys(), key=int)
        for i in range(len(sorted_years)):
            y = sorted_years[i]
            current_total = self.yearly_summaries[y]["total_contributions"]
            if i == 0:
                yoy_growth[y] = 0.0
            else:
                prev_year = sorted_years[i - 1]
                prev_total = self.yearly_summaries[prev_year]["total_contributions"]
                if prev_total > 0:
                    growth = round(((current_total - prev_total) / prev_total) * 100, 2)
                else:
                    growth = 100.0 if current_total > 0 else 0.0
                yoy_growth[y] = growth

        analysis_payload = {
            "username": self.username,
            "longest_streak": streaks["longest_streak"],
            "current_streak": streaks["current_streak"],
            "best_month": f"{best_month_name} ({best_month_val} contributions)" if best_month_key != "N/A" else "N/A",
            "most_productive_weekday": most_productive_weekday,
            "most_productive_month": most_productive_month,
            "productivity_score": productivity_score,
            "yoy_growth": yoy_growth,
            "total_active_days": active_days,
            "average_contributions_per_day": avg_daily,
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        }
        
        analysis_dir = os.path.join(docs_dir, 'data')
        os.makedirs(analysis_dir, exist_ok=True)
        analysis_file = os.path.join(analysis_dir, 'analysis.json')
        
        try:
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_payload, f, indent=2)
            logger.info(f"Successfully generated analysis JSON at: {analysis_file}")
        except IOError as e:
            logger.error(f"Failed to write analysis JSON: {e}")
            
        return analysis_payload

    def generate_history_json(self, docs_dir):
        """
        Generates docs/data/history.json containing full timeline history of contributions.
        """
        if not self.all_days:
            return {}

        sorted_days = sorted(self.all_days, key=lambda d: d["date"])
        
        history_list = []
        for d in sorted_days:
            count = d["count"]
            level = "NONE"
            if count > 0:
                if count < 3:
                    level = "FIRST_QUARTILE"
                elif count < 6:
                    level = "SECOND_QUARTILE"
                elif count < 9:
                    level = "THIRD_QUARTILE"
                else:
                    level = "FOURTH_QUARTILE"
                    
            history_list.append({
                "date": d["date"].isoformat(),
                "count": count,
                "level": level
            })
            
        history_payload = {
            "username": self.username,
            "history": history_list
        }
        
        history_dir = os.path.join(docs_dir, 'data')
        os.makedirs(history_dir, exist_ok=True)
        history_file = os.path.join(history_dir, 'history.json')
        
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_payload, f, indent=2)
            logger.info(f"Successfully generated contribution history JSON at: {history_file}")
        except IOError as e:
            logger.error(f"Failed to write history JSON: {e}")
            
        return history_payload
