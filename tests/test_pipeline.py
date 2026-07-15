import os
import json
import datetime
import pytest
from scripts.pipeline import SkylinePipeline

def test_pipeline_initialization():
    # Initializes correctly with default config
    pipeline = SkylinePipeline(username="TestUser", theme_override="matrix")
    assert pipeline.username == "TestUser"
    assert pipeline.theme.name == "Matrix"

def test_write_if_changed(tmp_path):
    pipeline = SkylinePipeline(username="TestUser")
    
    test_file = os.path.join(str(tmp_path), "test.svg")
    content_a = "<svg>A</svg>"
    content_b = "<svg>B</svg>"
    
    # First write should return True
    assert pipeline.write_if_changed(test_file, content_a) is True
    assert os.path.exists(test_file)
    
    # Second write of same content should return False
    assert pipeline.write_if_changed(test_file, content_a) is False
    
    # Write of new content should return True
    assert pipeline.write_if_changed(test_file, content_b) is True

def test_compile_all_years_calendar():
    pipeline = SkylinePipeline(username="TestUser")
    
    raw_calendars = {
        2024: {
            "totalContributions": 5,
            "weeks": [
                {
                    "contributionDays": [
                        {"date": "2024-01-01", "weekday": 0, "contributionCount": 2},
                        {"date": "2024-01-02", "weekday": 1, "contributionCount": 0}
                    ]
                }
            ]
        },
        2025: {
            "totalContributions": 10,
            "weeks": [
                {
                    "contributionDays": [
                        {"date": "2025-01-01", "weekday": 0, "contributionCount": 3},
                        {"date": "2025-01-02", "weekday": 1, "contributionCount": 1}
                    ]
                }
            ]
        }
    }
    
    compiled = pipeline._compile_all_years_calendar(raw_calendars)
    assert compiled["totalContributions"] == 6
    
    days = compiled["weeks"][0]["contributionDays"]
    assert days[0]["contributionCount"] == 5 # 2 + 3
    assert days[1]["contributionCount"] == 1 # 0 + 1

def test_compile_all_years_boundary_days_excluded():
    """
    Regression test for the ALL YEARS boundary-day double-count bug.
    The first week of year 2025 contains a day dated '2024-12-31' (cross-year
    boundary).  That day must NOT be counted when merging year 2025.
    Without the fix, the 2024-12-31 entry at position (0,0) in the 2025 calendar
    would inflate the total by its count.
    """
    pipeline = SkylinePipeline(username="TestUser")

    raw_calendars = {
        2024: {
            "totalContributions": 10,
            "weeks": [
                {
                    "contributionDays": [
                        # Normal 2024 day
                        {"date": "2024-01-01", "weekday": 0, "contributionCount": 10}
                    ]
                }
            ]
        },
        2025: {
            "totalContributions": 5,
            "weeks": [
                {
                    "contributionDays": [
                        # Boundary day: date belongs to 2024 but sits in 2025's week slot
                        {"date": "2024-12-31", "weekday": 0, "contributionCount": 99}
                    ]
                }
            ]
        }
    }

    compiled = pipeline._compile_all_years_calendar(raw_calendars)
    # 2024 week-0-day-0 (date=2024-01-01) contributes 10
    # 2025 week-0-day-0 (date=2024-12-31) must be excluded (year mismatch)
    # Total must be 10, not 10 + 99 = 109
    assert compiled["totalContributions"] == 10, (
        f"Expected 10 but got {compiled['totalContributions']} — "
        "boundary-day double-count bug is still present"
    )


def test_pipeline_full_mock_run(tmp_path):
    # Setup temporary paths for outputs
    config_file = tmp_path / "config.json"
    config_content = json.dumps({
        "username": "Durgesh729",
        "theme": "cyberpunk",
        "output_dir": str(tmp_path / "assets"),
        "docs_dir": str(tmp_path / "docs"),
        "github_pages_url": "",
        "svg_settings": {
            "show_grid": True,
            "show_text": True
        },
        "animation_settings": {
            "enabled": True
        }
    })
    config_file.write_text(config_content)
    
    pipeline = SkylinePipeline(config_path=str(config_file))
    # Enable mock mode to bypass network requests
    pipeline.client.mock_mode = True
    
    current_year = datetime.date.today().year
    success = pipeline.run(target_year=current_year, generate_all_compilation=False)
    assert success is True
    
    # Assert output files exist in assets
    assert os.path.exists(os.path.join(pipeline.output_dir, f"skyline-{current_year}.svg"))
    assert os.path.exists(os.path.join(pipeline.output_dir, "skyline-current.svg"))
    assert os.path.exists(os.path.join(pipeline.output_dir, "skyline-animated.svg"))
    assert os.path.exists(os.path.join(pipeline.docs_dir, "data", "stats.json"))

