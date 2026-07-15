import os
import json
import pytest
import datetime
from scripts.renderer.validator import validate_svg, SVGValidationError
from scripts.processor import ContributionProcessor
from scripts.config import ConfigManager

def test_svg_validator_valid():
    valid_svg = """<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#ff0000" />
          <stop offset="100%" stop-color="#0000ff" />
        </linearGradient>
      </defs>
      <path d="M 10 10 L 90 90" fill="url(#grad1)" />
    </svg>"""
    assert validate_svg(valid_svg, is_animated=False) is True

def test_svg_validator_invalid_xml():
    invalid_xml = "<svg viewBox='0 0 100 100'><path d='M 10 10' fill='none'>" # unclosed path tag
    with pytest.raises(SVGValidationError, match="Invalid XML syntax"):
        validate_svg(invalid_xml)

def test_svg_validator_missing_viewbox():
    no_viewbox = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
    with pytest.raises(SVGValidationError, match="Missing 'viewBox' attribute"):
        validate_svg(no_viewbox)

def test_svg_validator_missing_resource():
    missing_resource = """<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <path d="M 10 10 L 90 90" fill="url(#grad_not_exist)" />
    </svg>"""
    with pytest.raises(SVGValidationError, match="Missing resource reference"):
        validate_svg(missing_resource)

def test_svg_validator_missing_animation():
    missing_anim = """<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <style>.some-other-class {}</style>
    </svg>"""
    with pytest.raises(SVGValidationError, match="Missing animation rules"):
        validate_svg(missing_anim, is_animated=True)

def test_processor_ai_insights(tmp_path):
    processor = ContributionProcessor(username="Durgesh729", repo_count=5)
    
    # 2 weeks of mock data
    calendar_data = {
        "totalContributions": 15,
        "weeks": [
            {
                "contributionDays": [
                    {"date": "2025-10-01", "contributionCount": 5, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 2}, # Wednesday
                    {"date": "2025-10-02", "contributionCount": 10, "color": "#ebedf0", "contributionLevel": "NONE", "weekday": 3} # Thursday
                ]
            }
        ]
    }
    
    processor.add_year_data(2025, calendar_data)
    
    docs_dir = str(tmp_path)
    analysis = processor.generate_analysis_json(docs_dir)
    history = processor.generate_history_json(docs_dir)
    
    # Check analysis structure and values
    assert analysis["username"] == "Durgesh729"
    assert "productivity_score" in analysis
    assert analysis["most_productive_weekday"] == "Thursday"
    assert "October 2025" in analysis["best_month"]
    assert analysis["total_active_days"] == 2
    
    # Check files exist
    assert os.path.exists(os.path.join(docs_dir, "data", "analysis.json"))
    assert os.path.exists(os.path.join(docs_dir, "data", "history.json"))

def test_dynamic_theme_loader():
    # Instantiate config manager using default config file
    cfg = ConfigManager()
    themes = cfg.get_available_themes()
    assert "cyberpunk" in themes
    assert "github-dark" in themes
    assert "matrix" in themes
    assert "light" in themes
