import os
import sys
import json
import hashlib
import datetime
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from scripts.logger import setup_logger
from scripts.config import ConfigManager
from scripts.client import GitHubGraphQLClient
from scripts.processor import ContributionProcessor
from scripts.renderer.projection import IsometricProjector
from scripts.renderer.cube import IsometricCube
from scripts.renderer.theme import Theme
from scripts.renderer.styles import SVGStyleManager
from scripts.renderer.animator import SVGAnimationManager
from scripts.renderer.validator import validate_svg
from scripts.auditor import run_audit

logger = setup_logger()

class SkylinePipeline:
    """
    Coordinates the execution sequence:
    1. Configurations loading
    2. GraphQL data fetching
    3. Contribution processing & statistics exports
    4. SVG rendering with theme styling and animation rules
    """
    def __init__(self, username=None, theme_override=None, config_path=None):
        self.config_mgr = ConfigManager(config_path)
        
        # Overrides
        if username:
            self.config_mgr.config_data["username"] = username
        if theme_override:
            self.config_mgr.load_theme(theme_override)
            
        self.username = self.config_mgr.username
        self.theme = Theme(self.config_mgr.theme_data)
        
        # Load directories
        self.output_dir = self.config_mgr.output_dir
        self.docs_dir = self.config_mgr.docs_dir
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.docs_dir, exist_ok=True)
        
        # Cache directory
        self.cache_dir = os.path.join(self.config_mgr.root_dir, '.cache')
        os.makedirs(self.cache_dir, exist_ok=True)

        self.client = GitHubGraphQLClient()

    def run(self, target_year=None, generate_all_compilation=True, animate=False, generate_png=False, generate_json=False, benchmark_mode=False):
        """Runs the entire collection-to-rendering pipeline."""
        t_start = time.perf_counter()
        
        metrics = {
            "graphql_time": 0.0,
            "processing_time": 0.0,
            "rendering_time": 0.0,
            "file_write_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_days": 0
        }
        metrics_lock = threading.Lock()
        
        logger.info(f"Starting GitHub Skyline Pipeline for user: @{self.username} (Theme: {self.theme.name})")
        
        try:
            # Step 1: Fetch User profile metadata (Cached check)
            metadata_cache = os.path.join(self.cache_dir, f"metadata_{self.username}.json")
            metadata = None
            
            # Check metadata cache validity (4 hours)
            if os.path.exists(metadata_cache):
                mtime = os.path.getmtime(metadata_cache)
                if (time.time() - mtime) / 3600.0 < 4.0 or self.client.mock_mode:
                    try:
                        with open(metadata_cache, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        metrics["cache_hits"] += 1
                        logger.info(f"Loaded user metadata cache from {metadata_cache}")
                    except Exception as e:
                        logger.warning(f"Failed to read metadata cache: {e}")
            
            if not metadata:
                logger.info("Fetching fresh user profile metadata via GraphQL...")
                t0 = time.perf_counter()
                metadata = self.client.get_user_metadata(self.username)
                metrics["graphql_time"] += (time.perf_counter() - t0)
                metrics["cache_misses"] += 1
                try:
                    with open(metadata_cache, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f)
                except Exception as e:
                    logger.warning(f"Failed to write metadata cache: {e}")

            created_at_str = metadata["created_at"]
            repo_count = metadata["repo_count"]
            created_year = datetime.datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%SZ").year
            current_year = datetime.date.today().year
            
            logger.info(f"User profile metadata resolved: Registered in {created_year}, Repositories={repo_count}")
            
            years = list(range(created_year, current_year + 1))
            if target_year:
                if target_year not in years:
                    logger.warning(f"Requested target year {target_year} is out of active range ({created_year}-{current_year}).")
                years = [target_year]
                
            # Step 2: Fetch and cache contribution data (Parallelized)
            processor = ContributionProcessor(self.username, repo_count)
            raw_calendars = {}
            
            def fetch_and_parse_year(y):
                # Retrieve from cache if offline/valid
                start_iso = f"{y}-01-01T00:00:00Z"
                end_iso = f"{y}-12-31T23:59:59Z"
                cache_file = os.path.join(self.cache_dir, f"raw_{self.username}_{y}.json")
                calendar_data = None
                
                is_cache_valid = False
                mode_str = "OFFLINE" if self.client.mock_mode else "ONLINE"
                cache_source = "NONE"
                cache_used = "NO"
                cache_age_str = ""
                reason_str = ""
                
                if os.path.exists(cache_file):
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cached_data = json.load(f)
                        
                        source = cached_data.get("source", "unknown")
                        cache_source = source.upper()
                        
                        mtime = os.path.getmtime(cache_file)
                        age_minutes = int((time.time() - mtime) / 60)
                        
                        if age_minutes < 60:
                            cache_age_str = f"{age_minutes} minutes"
                        else:
                            cache_age_str = f"{round(age_minutes / 60, 1)} hours"
                            
                        # Validation logic
                        if self.client.mock_mode:
                            # In mock mode, we accept either mock or graphql caches as valid
                            if age_minutes < 240:
                                is_cache_valid = True
                                calendar_data = cached_data
                                cache_used = "YES"
                            else:
                                reason_str = "Cache expired (older than 4 hours)."
                        else:
                            # In online mode, we ONLY accept "graphql" source caches as valid
                            if source == "graphql":
                                if age_minutes < 240:
                                    is_cache_valid = True
                                    calendar_data = cached_data
                                    cache_used = "YES"
                                else:
                                    reason_str = "Cache expired (older than 4 hours)."
                            elif source == "mock":
                                reason_str = "Mock cache cannot be used in online mode."
                            else:
                                reason_str = f"Unknown cache source: {source}."
                    except Exception as e:
                        cache_source = "UNKNOWN"
                        reason_str = f"Failed to parse cache file: {e}"
                else:
                    cache_source = "NONE"
                    reason_str = "Cache file missing."

                # Print Cache Status summary (Thread-safe)
                with metrics_lock:
                    print("\n==============================")
                    print("Cache Status")
                    print("==============================")
                    print(f"Mode           : {mode_str}")
                    print(f"Cache Source   : {cache_source}")
                    if cache_used == "YES":
                        print(f"Cache Used     : {cache_used}")
                        print(f"Cache Age      : {cache_age_str}")
                    else:
                        print(f"Cache Used     : {cache_used}")
                        print(f"Reason         : {reason_str}")
                        if not self.client.mock_mode:
                            print("Downloading fresh GraphQL data...")
                    print("==============================\n")
                    sys.stdout.flush()

                if is_cache_valid:
                    with metrics_lock:
                        metrics["cache_hits"] += 1
                    logger.info(f"Loaded calendar cache for {y}")
                else:
                    t_gql_start = time.perf_counter()
                    try:
                        calendar_data = self.client.get_contribution_calendar(self.username, start_iso, end_iso)
                        with metrics_lock:
                            metrics["graphql_time"] += (time.perf_counter() - t_gql_start)
                            metrics["cache_misses"] += 1
                        
                        # Add metadata to calendar_data
                        calendar_data["source"] = "mock" if self.client.mock_mode else "graphql"
                        calendar_data["generated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
                        calendar_data["username"] = self.username
                        calendar_data["year"] = y
                        
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(calendar_data, f)
                        logger.info(f"Fetched and cached contribution data for {y}")
                    except Exception as e:
                        logger.error(f"GraphQL request failed for year {y}: {e}")
                        if os.path.exists(cache_file):
                            logger.warning(f"API failed. Falling back to stale cache for year {y}")
                            try:
                                with open(cache_file, 'r', encoding='utf-8') as f:
                                    calendar_data = json.load(f)
                            except Exception:
                                pass
                return y, calendar_data

            # Run parallel fetches
            with ThreadPoolExecutor(max_workers=min(len(years), 5)) as executor:
                results = list(executor.map(fetch_and_parse_year, years))
                
            t_proc_start = time.perf_counter()
            for y, calendar_data in results:
                if calendar_data:
                    processor.add_year_data(y, calendar_data)
                    raw_calendars[y] = calendar_data
            
            metrics["total_days"] = len(processor.all_days)
            
            # Step 3: Compute streaks and write stats
            stats = processor.generate_stats_json(self.docs_dir, available_themes=self.config_mgr.get_available_themes())
            metrics["processing_time"] += (time.perf_counter() - t_proc_start)
            
            # Step 4: Render Year SVGs
            changed_files_count = 0
            
            for y, calendar in raw_calendars.items():
                if calendar.get("totalContributions", 0) == 0:
                    logger.info(f"Skipping empty contribution year: {y}")
                    continue
                    
                # RENDER STATIC
                t_rend_start = time.perf_counter()
                static_svg = self.render_svg(y, calendar, stats, animated=False)
                metrics["rendering_time"] += (time.perf_counter() - t_rend_start)
                
                # Validate SVG content
                validate_svg(static_svg, is_animated=False)
                
                filename = f"skyline-{y}.svg"
                filepath = os.path.join(self.output_dir, filename)
                
                t_write_start = time.perf_counter()
                svg_changed = self.write_if_changed(filepath, static_svg)
                if svg_changed:
                    changed_files_count += 1
                
                png_path = filepath.replace(".svg", ".png")
                if generate_png and (svg_changed or not os.path.exists(png_path)):
                    self.convert_svg_to_png(static_svg, png_path)
                metrics["file_write_time"] += (time.perf_counter() - t_write_start)
                
                # If current year OR animate parameter is True, output current & animated SVGs
                if y == current_year or animate:
                    cur_filepath = os.path.join(self.output_dir, "skyline-current.svg")
                    t_write_start = time.perf_counter()
                    cur_svg_changed = self.write_if_changed(cur_filepath, static_svg)
                    cur_png_path = cur_filepath.replace(".svg", ".png")
                    if generate_png and (cur_svg_changed or not os.path.exists(cur_png_path)):
                        self.convert_svg_to_png(static_svg, cur_png_path)
                    metrics["file_write_time"] += (time.perf_counter() - t_write_start)
                    
                    # RENDER ANIMATED version
                    t_rend_start = time.perf_counter()
                    animated_svg = self.render_svg(y, calendar, stats, animated=True)
                    metrics["rendering_time"] += (time.perf_counter() - t_rend_start)
                    
                    # Validate animated SVG
                    validate_svg(animated_svg, is_animated=True)
                    
                    anim_filepath = os.path.join(self.output_dir, "skyline-animated.svg")
                    t_write_start = time.perf_counter()
                    anim_svg_changed = self.write_if_changed(anim_filepath, animated_svg)
                    anim_png_path = anim_filepath.replace(".svg", ".png")
                    if generate_png and (anim_svg_changed or not os.path.exists(anim_png_path)):
                        self.convert_svg_to_png(animated_svg, anim_png_path)
                    metrics["file_write_time"] += (time.perf_counter() - t_write_start)

            # Step 5: Render "All Years" compilation
            if generate_all_compilation and len(raw_calendars) > 1:
                t_rend_start = time.perf_counter()
                all_calendar = self._compile_all_years_calendar(raw_calendars)
                all_svg = self.render_svg("ALL YEARS", all_calendar, stats, animated=False)
                metrics["rendering_time"] += (time.perf_counter() - t_rend_start)
                
                validate_svg(all_svg, is_animated=False)
                
                all_filepath = os.path.join(self.output_dir, "skyline-all.svg")
                t_write_start = time.perf_counter()
                all_svg_changed = self.write_if_changed(all_filepath, all_svg)
                if all_svg_changed:
                    changed_files_count += 1
                
                all_png_path = all_filepath.replace(".svg", ".png")
                if generate_png and (all_svg_changed or not os.path.exists(all_png_path)):
                    self.convert_svg_to_png(all_svg, all_png_path)
                metrics["file_write_time"] += (time.perf_counter() - t_write_start)
                
            # Step 6: Generate JSON Exports & AI Insights
            t_write_start = time.perf_counter()
            processor.generate_analysis_json(self.docs_dir)
            if generate_json:
                processor.generate_history_json(self.docs_dir)
            metrics["file_write_time"] += (time.perf_counter() - t_write_start)
            
            # Step 7: Run mathematical data integrity audit
            run_audit(self, processor, stats)
            
            t_total = time.perf_counter() - t_start
            
            if benchmark_mode:
                self.print_benchmark_report(t_total, metrics)
                
            logger.info(f"Pipeline completed successfully. Updated files: {changed_files_count}")
            return True
            
        except Exception as e:
            logger.error(f"SkylinePipeline crash: {e}", exc_info=True)
            return False

    def convert_svg_to_png(self, svg_content, png_path, width=1200, height=800):
        """Converts an SVG string into a PNG image file using resvg_py."""
        try:
            import resvg_py
            png_bytes = resvg_py.svg_to_bytes(svg_string=svg_content, width=width, height=height)
            with open(png_path, "wb") as f:
                f.write(png_bytes)
            logger.info(f"Successfully generated PNG export: {png_path}")
        except Exception as e:
            logger.error(f"Failed to export SVG to PNG: {e}")
            raise

    def print_benchmark_report(self, t_total, metrics):
        """Prints a clean, premium console benchmark report."""
        print("\n" + "="*50)
        print("=== GITHUB SKYLINE - PERFORMANCE BENCHMARK REPORT ===")
        print("="*50)
        print(f"GraphQL Request Time   : {metrics['graphql_time']:.4f} seconds")
        print(f"Data Processing Time   : {metrics['processing_time']:.4f} seconds")
        print(f"Vector Rendering Time  : {metrics['rendering_time']:.4f} seconds")
        print(f"File Output/Write Time : {metrics['file_write_time']:.4f} seconds")
        print(f"Total Execution Time   : {t_total:.4f} seconds")
        print("-"*50)
        print(f"Cache Hit / Miss Ratio : {metrics['cache_hits']} Hits / {metrics['cache_misses']} Misses")
        print(f"Total Days Processed   : {metrics['total_days']} contribution days")
        print("="*50 + "\n")

    def _calculate_scene_layout(self, calendar, projector, animated):
        """
        Calculates the bounding box and target scale/translation explicitly
        prior to compiling the SVG layout.
        """
        min_x = float('inf')
        max_x = float('-inf')
        min_y = float('inf')
        max_y = float('-inf')
        
        # 1. Project the 4 corners of the floor grid at z = 0
        cols = projector.cols_count
        rows = projector.rows_count
        grid_corners = [
            (0, 0, 0),
            (cols, 0, 0),
            (0, rows, 0),
            (cols, rows, 0)
        ]
        for c, r, z in grid_corners:
            x, y = projector.project(c, r, z)
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            
        # 2. Project building tops (z = height_val) and bottom reflections (z = -ref_h)
        weeks = calendar.get("weeks", [])
        svg_settings = self.config_mgr.svg_settings
        height_scale = svg_settings.get("height_scale", 15.0)
        min_h = svg_settings.get("min_building_height", 5)
        max_h = svg_settings.get("max_building_height", 180)
        
        fill_factor = 0.82
        offset = (1.0 - fill_factor) / 2.0
        has_glass = self.theme.effects.get("glass_reflection", False)
        
        for w_idx, week in enumerate(weeks):
            days = week.get("contributionDays", [])
            for day in days:
                count = day.get("contributionCount", 0)
                if count > 0:
                    d_idx = day.get("weekday", 0)
                    height_val = max(min_h, min(count * height_scale, max_h))
                    
                    # Top corners
                    corners = [
                        (w_idx + offset, d_idx + offset, height_val),
                        (w_idx + offset, d_idx + 1 - offset, height_val),
                        (w_idx + 1 - offset, d_idx + 1 - offset, height_val),
                        (w_idx + 1 - offset, d_idx + offset, height_val)
                    ]
                    
                    # Reflection corners (projecting down)
                    if has_glass:
                        ref_h = height_val * 0.45
                        corners.extend([
                            (w_idx + offset, d_idx + offset, -ref_h),
                            (w_idx + offset, d_idx + 1 - offset, -ref_h),
                            (w_idx + 1 - offset, d_idx + 1 - offset, -ref_h),
                            (w_idx + 1 - offset, d_idx + offset, -ref_h)
                        ])
                        
                    for c_val, r_val, z_val in corners:
                        x, y = projector.project(c_val, r_val, z_val)
                        min_x = min(min_x, x)
                        max_x = max(max_x, x)
                        min_y = min(min_y, y)
                        max_y = max(max_y, y)
                        
        skyline_w = max_x - min_x
        skyline_h = max_y - min_y
        
        # Safe available space: Left 50, Right 50, Top 140, Bottom 70
        avail_w = 1200.0 - 100.0  # 1100.0
        avail_h = 800.0 - 210.0   # 590.0
        
        s_w = avail_w / skyline_w if skyline_w > 0 else 1.0
        s_h = avail_h / skyline_h if skyline_h > 0 else 1.0
        s = min(s_w, s_h) * 0.95
        
        # Cap scaling to keep sizes consistent and within safe aesthetic limits
        s = max(0.8, min(s, 1.15))
        
        center_skyline_x = (min_x + max_x) / 2.0 if skyline_w > 0 else projector.width / 2.0
        center_skyline_y = (min_y + max_y) / 2.0 if skyline_h > 0 else projector.height / 2.0
        
        target_cx = 600.0
        target_cy = 437.5
        
        tx = target_cx - s * center_skyline_x
        ty = target_cy - s * center_skyline_y
        
        return {
            "scale": round(s, 4),
            "translate_x": round(tx, 2),
            "translate_y": round(ty, 2),
            "bounding_box": (round(min_x, 1), round(max_x, 1), round(min_y, 1), round(max_y, 1)),
            "viewport": (1200, 800)
        }

    def render_svg(self, label, calendar, stats, animated=False):
        """Constructs an SVG skyline using the projection and cube modules."""
        svg_settings = self.config_mgr.svg_settings
        width = svg_settings.get("width", 1200)
        height = svg_settings.get("height", 800)
        height_scale = svg_settings.get("height_scale", 15.0)
        grid_spacing = svg_settings.get("grid_spacing", 20)
        perspective_angle = svg_settings.get("perspective_angle", 30)

        # Initialize Projector
        projector = IsometricProjector(
            width=width,
            height=height,
            grid_spacing=grid_spacing,
            perspective_angle=perspective_angle,
            height_scale=height_scale
        )
        
        # Calculate dynamic scene layout
        layout = self._calculate_scene_layout(calendar, projector, animated)
        
        # Initialize Managers
        styler = SVGStyleManager(projector, self.theme, layout)
        animator = SVGAnimationManager(self.config_mgr.animation_settings, self.theme)
        
        # Assemble components
        svg_parts = []
        svg_parts.append(styler.get_header_svg(width, height))
        
        # Inject stylesheet styles (includes keyframe rules)
        if animated:
            svg_parts.append(animator.get_style_section())
            
        # Inject linearGradients, filters
        svg_parts.append(f'  <defs>\n{self.theme.get_defs_svg()}\n  </defs>')
        
        # Background
        svg_parts.append(styler.get_background_svg(width, height))
        
        # Open Scene Transform Group (dynamic centering and scaling)
        tx = layout["translate_x"]
        ty = layout["translate_y"]
        s = layout["scale"]
        svg_parts.append(f'  <g id="skyline-scene" transform="translate({tx}, {ty}) scale({s})">')
        
        # Grid lines (at base floor)
        if svg_settings.get("show_grid", True):
            svg_parts.append(styler.get_floor_grid_svg())

        # Collect columns
        cubes = []
        weeks = calendar.get("weeks", [])
        
        for w_idx, week in enumerate(weeks):
            days = week.get("contributionDays", [])
            for day in days:
                count = day.get("contributionCount", 0)
                if count > 0:
                    d_idx = day.get("weekday", 0)
                    
                    # Convert count to physical z coordinate height value
                    height_val = max(
                        svg_settings.get("min_building_height", 5),
                        min(count * height_scale, svg_settings.get("max_building_height", 180))
                    )
                    
                    cube = IsometricCube(
                        col=w_idx,
                        row=d_idx,
                        count=count,
                        height_val=height_val,
                        projector=projector
                    )
                    cubes.append(cube)

        # Depth Sort: back-to-front rendering order (col + row ascending)
        cubes.sort(key=lambda c: (c.col + c.row))

        # Render reflections first (so they are layered under actual buildings)
        if self.theme.effects.get("glass_reflection", False):
            svg_parts.append('  <!-- Reflections -->')
            for cube in cubes:
                ref_paths = cube.get_reflection_paths()
                # Draw mirrored Left & Right face reflections with lower opacity
                svg_parts.append(f'  <path d="{ref_paths["left"]}" fill="url(#reflection-gradient-left)" opacity="0.4" />')
                svg_parts.append(f'  <path d="{ref_paths["right"]}" fill="url(#reflection-gradient-right)" opacity="0.4" />')

        # Render ambient shadows
        if self.theme.effects.get("ambient_shadow", False):
            svg_parts.append('  <!-- Ground Shadows -->')
            shadows_path = []
            for cube in cubes:
                shadows_path.append(cube.get_shadow_path())
            if shadows_path:
                svg_parts.append(f'  <path d="{" ".join(shadows_path)}" fill="#000000" filter="url(#ambient-shadow)" opacity="0.6" />')

        # Render actual buildings
        stroke_color = self.theme.building.get("stroke", "#00F0FF")
        stroke_width = self.theme.building.get("stroke_width", 0.5)
        opacity = self.theme.building.get("opacity", 0.95)
        
        svg_parts.append('  <!-- Isometric Buildings -->')
        for cube in cubes:
            paths = cube.get_face_paths()
            
            # Setup staggered rise animation attributes
            base_x, base_y = projector.project(cube.col + 0.5, cube.row + 0.5, 0)
            anim_attrs = animator.get_column_style_attrs(cube.col, cube.row, base_x, base_y) if animated else ""
            
            # Wrap column faces in group tag
            group_tag = f'  <g {anim_attrs}>' if anim_attrs else '  <g>'
            svg_parts.append(group_tag)
            
            # Draw Left, Right, Top faces
            svg_parts.append(f'    <path class="building-face" d="{paths["left"]}" fill="url(#left-face-gradient)" stroke="{stroke_color}" stroke-width="{stroke_width}" opacity="{opacity}" />')
            svg_parts.append(f'    <path class="building-face" d="{paths["right"]}" fill="url(#right-face-gradient)" stroke="{stroke_color}" stroke-width="{stroke_width}" opacity="{opacity}" />')
            svg_parts.append(f'    <path class="building-face" d="{paths["top"]}" fill="url(#top-face-gradient)" stroke="{stroke_color}" stroke-width="{stroke_width}" opacity="{opacity}" />')
            
            svg_parts.append('  </g>')

        # Scanline line layer
        if animated:
            svg_parts.append(animator.get_scanline_svg(width, height, projector.center_y))

        # Close Scene Transform Group
        svg_parts.append('  </g>')

        # Title Card details
        if svg_settings.get("show_text", True):
            total_count = calendar.get("totalContributions", 0)
            if str(label) in stats.get("yearly_summaries", {}):
                total_count = stats["yearly_summaries"][str(label)]["total_contributions"]
            svg_parts.append(styler.get_ui_overlays_svg(self.username, str(label), total_count, stats))
            
        svg_parts.append(styler.get_footer_svg())
        
        return "\n".join(svg_parts)

    def write_if_changed(self, filepath, new_content):
        """Writes content to filepath ONLY if it has changed, preventing git history bloat."""
        new_bytes = new_content.encode('utf-8')
        new_hash = hashlib.sha256(new_bytes).hexdigest()
        
        # Check existing hash
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    old_bytes = f.read()
                old_hash = hashlib.sha256(old_bytes).hexdigest()
                
                if old_hash == new_hash:
                    logger.debug(f"Skipping write for {os.path.basename(filepath)}: Content is identical.")
                    return False
            except Exception as e:
                logger.warning(f"Error reading existing file {filepath} for comparison: {e}")
                
        try:
            with open(filepath, 'wb') as f:
                f.write(new_bytes)
            logger.info(f"Successfully generated/updated file: {filepath}")
            return True
        except IOError as e:
            logger.error(f"Failed to write file {filepath}: {e}")
            return False

    def _compile_all_years_calendar(self, raw_calendars):
        """
        Compiles all years into a single normalized calendar representation
        by taking the max contributions for each cell to render a cumulative landscape.
        """
        logger.info("Compiling all years into cumulative calendar model.")
        
        # We need a master copy of a standard 53-week structure
        # We take a sample year structure (e.g. the first year) as a blueprint
        sample_year = list(raw_calendars.keys())[0]
        sample_calendar = raw_calendars[sample_year]
        
        import copy
        all_calendar = copy.deepcopy(sample_calendar)
        all_weeks = all_calendar["weeks"]
        
        total_accumulated = 0
        
        # Zero out the blueprint
        for week in all_weeks:
            for day in week["contributionDays"]:
                day["contributionCount"] = 0
                day["color"] = "#ebedf0"
                day["contributionLevel"] = "NONE"
                
        # Fill cells: for each week index and day index, aggregate contributions across all years
        for w_idx in range(len(all_weeks)):
            blueprint_days = all_weeks[w_idx]["contributionDays"]
            for d_idx in range(len(blueprint_days)):
                
                cell_sum = 0
                # Scan across all years.
                # Mirror the identical guard in ContributionProcessor.add_year_data
                # (processor.py line 40): skip any day whose date falls outside the
                # calendar year being merged.  GitHub boundary weeks (first/last week
                # of a year) contain 1-5 days from the adjacent year; without this
                # check those days are summed twice, inflating total_accumulated.
                for y, calendar in raw_calendars.items():
                    try:
                        year_weeks = calendar["weeks"]
                        if w_idx < len(year_weeks):
                            year_days = year_weeks[w_idx]["contributionDays"]
                            if d_idx < len(year_days):
                                day = year_days[d_idx]
                                # Only count the day when it actually belongs to year y
                                if day.get("date", "")[:4] == str(y):
                                    cell_sum += day["contributionCount"]
                    except (IndexError, KeyError):
                        continue
                        
                blueprint_days[d_idx]["contributionCount"] = cell_sum
                total_accumulated += cell_sum
                
                # Recalculate levels based on aggregate
                if cell_sum > 0:
                    if cell_sum < 10:
                        blueprint_days[d_idx]["contributionLevel"] = "FIRST_QUARTILE"
                    elif cell_sum < 25:
                        blueprint_days[d_idx]["contributionLevel"] = "SECOND_QUARTILE"
                    elif cell_sum < 50:
                        blueprint_days[d_idx]["contributionLevel"] = "THIRD_QUARTILE"
                    else:
                        blueprint_days[d_idx]["contributionLevel"] = "FOURTH_QUARTILE"

        all_calendar["totalContributions"] = total_accumulated
        return all_calendar
# Simple mock wait structure for pipeline execution
import time
