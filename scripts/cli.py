import argparse
import sys
import os
import shutil
from scripts.logger import setup_logger
from scripts.pipeline import SkylinePipeline
from scripts.verifier import verify_health

logger = setup_logger()

def main():
    """
    Main entry point for command-line executions.
    """
    parser = argparse.ArgumentParser(
        description="GitHub Skyline Hub - Isometric 3D Skyline Generator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/cli.py --year 2025
  python scripts/cli.py --theme matrix --all
  python scripts/cli.py --username test_user --offline
  python scripts/cli.py --verify
  python scripts/cli.py --clean
        """
    )
    
    parser.add_argument(
        "--username",
        type=str,
        help="Override target GitHub username"
    )
    
    parser.add_argument(
        "--theme",
        type=str,
        help="Override styling theme (cyberpunk, github-dark, matrix, light)"
    )
    
    parser.add_argument(
        "--year",
        type=int,
        help="Generate skyline for a single specific year"
    )
    
    parser.add_argument(
        "--current",
        action="store_true",
        help="Generate skyline for only the current year"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Force generation of all active years and cumulative compilation skyline"
    )
    
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run pipeline using mock/cached contribution profiles"
    )

    parser.add_argument(
        "--animate",
        action="store_true",
        help="Generate CSS-animated skyline SVG"
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Perform a complete system health check"
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clear cache files and force a full regeneration"
    )

    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Measure and display pipeline execution metrics"
    )

    parser.add_argument(
        "--png",
        action="store_true",
        help="Export PNG versions of every skyline SVG"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Export contribution history to docs/data/history.json"
    )

    parser.add_argument(
        "--list-themes",
        action="store_true",
        help="List all dynamically detected available themes"
    )

    args = parser.parse_args()

    try:
        # Initialize pipeline
        pipeline = SkylinePipeline(
            username=args.username,
            theme_override=args.theme
        )

        # Force mock mode if offline flag is passed
        if args.offline:
            pipeline.client.mock_mode = True
            logger.info("CLI option --offline passed. Forcing Mock Mode execution.")

        # 1. Handle --list-themes
        if args.list_themes:
            themes = pipeline.config_mgr.get_available_themes()
            print("\nAvailable Styling Themes:")
            for theme in themes:
                default_indicator = " (Default)" if theme == "cyberpunk" else ""
                print(f"  - {theme}{default_indicator}")
            print()
            sys.exit(0)

        # 2. Handle --clean
        if args.clean:
            logger.info("CLI option --clean passed. Purging cache directory...")
            if os.path.exists(pipeline.cache_dir):
                for filename in os.listdir(pipeline.cache_dir):
                    file_path = os.path.join(pipeline.cache_dir, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete cache file {file_path}: {e}")
            logger.info("Cache directory purged successfully.")
            # Continue execution to regenerate everything (equivalent to --all)
            args.all = True

        # 3. Handle --verify
        if args.verify:
            logger.info("CLI option --verify passed. Executing system health check...")
            healthy = verify_health(pipeline)
            if healthy:
                sys.exit(0)
            else:
                sys.exit(1)

        # Determine target year configuration
        target_year = None
        import datetime
        
        if args.current:
            target_year = datetime.date.today().year
            logger.info(f"CLI option --current passed. Filtering for year: {target_year}")
        elif args.year:
            target_year = args.year
            logger.info(f"CLI option --year passed. Filtering for year: {target_year}")

        # Execute Pipeline
        success = pipeline.run(
            target_year=target_year,
            generate_all_compilation=args.all or (not args.current and not args.year),
            animate=args.animate,
            generate_png=args.png,
            generate_json=args.json,
            benchmark_mode=args.benchmark
        )
        
        if success:
            logger.info("GitHub Skyline Hub pipeline executed successfully.")
            sys.exit(0)
        else:
            logger.error("GitHub Skyline Hub pipeline execution failed.")
            sys.exit(1)
            
    except Exception as e:
        logger.critical(f"CLI Engine crashed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
