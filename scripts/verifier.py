import os
import json
import traceback
from scripts.logger import setup_logger
from scripts.config import ConfigManager, ConfigError
from scripts.client import GitHubGraphQLClient, GitHubAPIError
from scripts.renderer.validator import validate_svg

logger = setup_logger()

def verify_health(pipeline) -> bool:
    """
    Performs a complete system health check on the Skyline Generator Hub pipeline.
    Prints a detailed pass/fail report to the console.
    Returns True if all critical subsystems passed, False otherwise.
    """
    print("\n" + "="*50)
    print("=== GITHUB SKYLINE - SYSTEM HEALTH VERIFICATION ===")
    print("="*50)

    checks = {
        "Authentication": {"status": "PENDING", "details": ""},
        "Configuration": {"status": "PENDING", "details": ""},
        "Theme": {"status": "PENDING", "details": ""},
        "GraphQL": {"status": "PENDING", "details": ""},
        "Cache": {"status": "PENDING", "details": ""},
        "SVG generation": {"status": "PENDING", "details": ""},
        "Output files": {"status": "PENDING", "details": ""},
        "Statistics": {"status": "PENDING", "details": ""},
        "GitHub Pages assets": {"status": "PENDING", "details": ""},
        "Animation": {"status": "PENDING", "details": ""}
    }

    # 1. Authentication Check
    try:
        token = pipeline.client.token
        if token:
            checks["Authentication"]["status"] = "PASS"
            checks["Authentication"]["details"] = f"Token detected (starts with {token[:4]}...)"
        else:
            checks["Authentication"]["status"] = "WARNING"
            checks["Authentication"]["details"] = "No GITHUB_TOKEN/GH_TOKEN detected; client forced to Mock Mode."
    except Exception as e:
        checks["Authentication"]["status"] = "FAIL"
        checks["Authentication"]["details"] = str(e)

    # 2. Configuration Check
    try:
        # Re-load config to make sure validation works
        cfg = ConfigManager(pipeline.config_mgr.config_path)
        checks["Configuration"]["status"] = "PASS"
        checks["Configuration"]["details"] = f"Loaded {os.path.basename(cfg.config_path)} successfully."
    except Exception as e:
        checks["Configuration"]["status"] = "FAIL"
        checks["Configuration"]["details"] = str(e)

    # 3. Theme Check
    try:
        theme_name = pipeline.config_mgr.get("theme", "cyberpunk")
        pipeline.config_mgr.load_theme(theme_name)
        checks["Theme"]["status"] = "PASS"
        checks["Theme"]["details"] = f"Theme '{theme_name}' loaded and validated."
    except Exception as e:
        checks["Theme"]["status"] = "FAIL"
        checks["Theme"]["details"] = str(e)

    # 4. GraphQL API Check
    try:
        metadata = pipeline.client.get_user_metadata(pipeline.username)
        mode = "Mocked" if pipeline.client.mock_mode else "Live API"
        checks["GraphQL"]["status"] = "PASS"
        checks["GraphQL"]["details"] = f"Successfully fetched user metadata ({mode})."
    except Exception as e:
        checks["GraphQL"]["status"] = "FAIL"
        checks["GraphQL"]["details"] = f"Failed to fetch metadata: {e}"

    # 5. Cache Check
    try:
        cache_dir = pipeline.cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
        # Try a test write
        test_file = os.path.join(cache_dir, ".verifier_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        checks["Cache"]["status"] = "PASS"
        checks["Cache"]["details"] = f"Directory {cache_dir} is readable and writable."
    except Exception as e:
        checks["Cache"]["status"] = "FAIL"
        checks["Cache"]["details"] = f"Read/write check failed: {e}"

    # 6. SVG Generation Check
    try:
        mock_calendar = {
            "totalContributions": 10,
            "weeks": [
                {
                    "contributionDays": [
                        {"weekday": 0, "contributionCount": 5, "date": "2026-01-01", "color": "#ebedf0", "contributionLevel": "NONE"},
                        {"weekday": 1, "contributionCount": 5, "date": "2026-01-02", "color": "#ebedf0", "contributionLevel": "NONE"}
                    ]
                }
            ]
        }
        mock_stats = {"longest_streak": 0, "current_streak": 0, "yearly_summaries": {}}
        test_svg = pipeline.render_svg("VERIFIER TEST", mock_calendar, mock_stats, animated=False)
        validate_svg(test_svg, is_animated=False)
        checks["SVG generation"]["status"] = "PASS"
        checks["SVG generation"]["details"] = "Rendered and validated mock static SVG successfully."
    except Exception as e:
        checks["SVG generation"]["status"] = "FAIL"
        checks["SVG generation"]["details"] = f"Generation failed: {e}"

    # 7. Output Files Check
    try:
        required_svgs = ["skyline-current.svg", "skyline-all.svg", "skyline-animated.svg"]
        missing = []
        for svg in required_svgs:
            p = os.path.join(pipeline.output_dir, svg)
            if not os.path.exists(p):
                missing.append(svg)
        
        # Check if at least one yearly skyline exists
        yearly_found = False
        for file in os.listdir(pipeline.output_dir):
            if file.startswith("skyline-") and file.endswith(".svg") and file != "skyline-current.svg" and file != "skyline-all.svg" and file != "skyline-animated.svg":
                yearly_found = True
                break
        
        if not yearly_found:
            missing.append("skyline-<year>.svg")

        if missing:
            checks["Output files"]["status"] = "FAIL"
            checks["Output files"]["details"] = f"Missing generated assets in {pipeline.output_dir}: {', '.join(missing)}"
        else:
            checks["Output files"]["status"] = "PASS"
            checks["Output files"]["details"] = f"All required SVGs verified in {pipeline.output_dir}."
    except Exception as e:
        checks["Output files"]["status"] = "FAIL"
        checks["Output files"]["details"] = str(e)

    # 8. Statistics Check
    try:
        stats_file = os.path.join(pipeline.docs_dir, "data", "stats.json")
        if not os.path.exists(stats_file):
            raise FileNotFoundError(f"Missing stats.json at {stats_file}")
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats_data = json.load(f)
        required_keys = ["username", "total_contributions", "longest_streak", "current_streak", "yearly_summaries"]
        missing_keys = [k for k in required_keys if k not in stats_data]
        if missing_keys:
            raise KeyError(f"Missing keys in stats.json: {missing_keys}")
        checks["Statistics"]["status"] = "PASS"
        checks["Statistics"]["details"] = "stats.json exists and is structured correctly."
    except Exception as e:
        checks["Statistics"]["status"] = "FAIL"
        checks["Statistics"]["details"] = str(e)

    # 9. GitHub Pages Assets Check
    try:
        required_pages = ["index.html", "app.js", "style.css"]
        missing_pages = []
        for file in required_pages:
            p = os.path.join(pipeline.docs_dir, file)
            if not os.path.exists(p) or os.path.getsize(p) == 0:
                missing_pages.append(file)
        if missing_pages:
            checks["GitHub Pages assets"]["status"] = "FAIL"
            checks["GitHub Pages assets"]["details"] = f"Missing/empty Web assets in {pipeline.docs_dir}: {', '.join(missing_pages)}"
        else:
            checks["GitHub Pages assets"]["status"] = "PASS"
            checks["GitHub Pages assets"]["details"] = "All dashboard web assets are present."
    except Exception as e:
        checks["GitHub Pages assets"]["status"] = "FAIL"
        checks["GitHub Pages assets"]["details"] = str(e)

    # 10. Animation Check
    try:
        anim_svg = os.path.join(pipeline.output_dir, "skyline-animated.svg")
        if not os.path.exists(anim_svg):
            raise FileNotFoundError(f"Missing animated SVG at {anim_svg}")
        with open(anim_svg, 'r', encoding='utf-8') as f:
            content = f.read()
        validate_svg(content, is_animated=True)
        checks["Animation"]["status"] = "PASS"
        checks["Animation"]["details"] = "skyline-animated.svg contains valid keyframes and CSS animations."
    except Exception as e:
        checks["Animation"]["status"] = "FAIL"
        checks["Animation"]["details"] = f"Animation check failed: {e}"

    # Print Report
    all_passed = True
    for name, result in checks.items():
        status = result["status"]
        details = result["details"]
        if status == "PASS":
            mark = "[PASS]"
            color_prefix = "\033[92m" # Green
        elif status == "WARNING":
            mark = "[WARN]"
            color_prefix = "\033[93m" # Yellow
        else:
            mark = "[FAIL]"
            color_prefix = "\033[91m" # Red
            all_passed = False
        
        # Reset color
        color_suffix = "\033[0m"
        # Print with fallbacks if console doesn't support ANSI coloring
        print(f"{color_prefix}{mark:<8} {name:<22}: {status:<7} {color_suffix}- {details}")

    print("="*50)
    if all_passed:
        print("\033[92mHEALTH CHECK: ALL SYSTEMS OPTIMAL [PASS]\033[0m")
    else:
        print("\033[91mHEALTH CHECK: CRITICAL SUBSYSTEM FAILURE [FAIL]\033[0m")
    print("="*50 + "\n")

    return all_passed
