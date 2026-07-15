import os
import json
import datetime
import pytest
from scripts.processor import ContributionProcessor

def test_processor_metrics():
    processor = ContributionProcessor(username="Durgesh729", repo_count=15)
    
    # Mock data for Year 2025 (3 weeks)
    calendar_2025 = {
        "totalContributions": 20,
        "weeks": [
            {
                "contributionDays": [
                    {"date": "2025-01-01", "contributionCount": 5, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 0},
                    {"date": "2025-01-02", "contributionCount": 0, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 1},
                    {"date": "2025-01-03", "contributionCount": 2, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 2},
                    {"date": "2025-01-04", "contributionCount": 0, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 3},
                    {"date": "2025-01-05", "contributionCount": 0, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 4},
                    {"date": "2025-01-06", "contributionCount": 0, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 5},
                    {"date": "2025-01-07", "contributionCount": 0, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 6}
                ]
            },
            {
                "contributionDays": [
                    {"date": "2025-01-08", "contributionCount": 3, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 0},
                    {"date": "2025-01-09", "contributionCount": 4, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 1},
                    {"date": "2025-01-10", "contributionCount": 6, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 2},
                    {"date": "2025-01-11", "contributionCount": 0, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 3},
                    {"date": "2025-01-12", "contributionCount": 0, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 4},
                    {"date": "2025-01-13", "contributionCount": 0, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 5},
                    {"date": "2025-01-14", "contributionCount": 0, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 6}
                ]
            }
        ]
    }
    
    processor.add_year_data(2025, calendar_2025)
    
    summary = processor.yearly_summaries["2025"]
    assert summary["total_contributions"] == 20
    assert summary["max_daily_contributions"] == 6
    assert summary["active_days"] == 5

def test_streaks_calculation():
    # Setup processor with yesterday and today contributions to verify current streak is active
    processor = ContributionProcessor(username="Durgesh729", repo_count=10)
    
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    two_days_ago = today - datetime.timedelta(days=2)
    three_days_ago = today - datetime.timedelta(days=3)
    four_days_ago = today - datetime.timedelta(days=4)
    
    # 3-day active streak (today, yesterday, two_days_ago)
    # broken on three_days_ago (0 contributions)
    # active on four_days_ago (1 contribution)
    processor.all_days = [
        {"date": four_days_ago, "count": 2},
        {"date": three_days_ago, "count": 0},
        {"date": two_days_ago, "count": 1},
        {"date": yesterday, "count": 4},
        {"date": today, "count": 3}
    ]
    
    streaks = processor.calculate_streaks()
    assert streaks["longest_streak"] == 3
    assert streaks["current_streak"] == 3

def test_streaks_expired():
    processor = ContributionProcessor(username="Durgesh729", repo_count=10)
    
    # Last contribution was 5 days ago, so current streak should be 0
    today = datetime.date.today()
    processor.all_days = [
        {"date": today - datetime.timedelta(days=5), "count": 2},
        {"date": today - datetime.timedelta(days=4), "count": 1},
        {"date": today - datetime.timedelta(days=3), "count": 0},
        {"date": today - datetime.timedelta(days=2), "count": 0},
        {"date": today - datetime.timedelta(days=1), "count": 0},
        {"date": today, "count": 0}
    ]
    
    streaks = processor.calculate_streaks()
    assert streaks["longest_streak"] == 2
    assert streaks["current_streak"] == 0

def test_stats_json_generation(tmp_path):
    processor = ContributionProcessor(username="Durgesh729", repo_count=12)
    processor.yearly_summaries["2025"] = {
        "total_contributions": 100,
        "max_daily_contributions": 12,
        "active_days": 45,
        "average_daily_contributions": 0.27,
        "days_count": 365
    }
    
    # Make sure mock day data exists to calculate streaks
    processor.all_days = [
        {"date": datetime.date(2025, 1, 1), "count": 1}
    ]
    
    docs_dir = str(tmp_path)
    stats = processor.generate_stats_json(docs_dir)
    
    assert stats["username"] == "Durgesh729"
    assert stats["total_contributions"] == 100
    assert stats["repository_count"] == 12
    
    stats_file = os.path.join(docs_dir, 'data', 'stats.json')
    assert os.path.exists(stats_file)
    with open(stats_file, 'r', encoding='utf-8') as f:
        loaded = json.load(f)
        assert loaded["username"] == "Durgesh729"
        assert loaded["longest_streak"] == 1
