import html
from scripts.renderer.theme import Theme

class SVGStyleManager:
    """
    Coordinates rendering of global SVG boilerplate:
    - SVG wrapper and viewBox
    - Background color block
    - Isometric floor grid (neon wireframe)
    - Headers, user details, and legend overlays
    """
    def __init__(self, projector, theme: Theme, layout=None):
        self.projector = projector
        self.theme = theme
        self.layout = layout

    def get_header_svg(self, width, height):
        """Generates opening SVG element and XML headers with inline styles."""
        font_family = self.theme.text.get("font_family", "sans-serif")
        stroke_color = self.theme.building.get("stroke", "#00F0FF")
        
        # Calculate bevel stroke colors
        stroke_top = self.theme._lighten_color(stroke_color, 0.3)
        stroke_left = stroke_color
        stroke_right = self.theme._darken_color(stroke_color, 0.2)
        
        return f'<?xml version="1.0" encoding="utf-8"?>\n' \
               f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">\n' \
               f'  <style type="text/css"><![CDATA[\n' \
               f'    .dashboard-text {{\n' \
               f'      font-family: {font_family};\n' \
               f'      -webkit-font-smoothing: antialiased;\n' \
               f'      -moz-osx-font-smoothing: grayscale;\n' \
               f'    }}\n' \
               f'    .code-text {{\n' \
               f'      font-family: "JetBrains Mono", Consolas, monospace;\n' \
               f'    }}\n' \
               f'    .building-face {{\n' \
               f'      stroke-linejoin: round;\n' \
               f'      transition: all 0.3s ease;\n' \
               f'    }}\n' \
               f'    path[fill="url(#top-face-gradient)"] {{\n' \
               f'      stroke: {stroke_top};\n' \
               f'      stroke-width: 0.8px;\n' \
               f'    }}\n' \
               f'    path[fill="url(#left-face-gradient)"] {{\n' \
               f'      stroke: {stroke_left};\n' \
               f'      stroke-opacity: 0.7;\n' \
               f'    }}\n' \
               f'    path[fill="url(#right-face-gradient)"] {{\n' \
               f'      stroke: {stroke_right};\n' \
               f'      stroke-opacity: 0.6;\n' \
               f'    }}\n' \
               f'  ]]></style>\n'

    def get_background_svg(self, width, height):
        """Generates a fully transparent SVG background with subtle ambient overlays.
        The canvas is transparent so the skyline composites cleanly over any surface.
        """
        # Estimate skyline vertical center for the ambient bloom placement
        bloom_cx = width * 0.5
        bloom_cy = height * 0.62

        bg_parts = []

        # Layer 1 — Transparent base (no fill — SVG composites over any page background)
        bg_parts.append(f'  <!-- Background: transparent canvas -->')
        bg_parts.append(f'  <rect id="bg-base" width="{width}" height="{height}" fill="none" />')

        # Layer 2 — Imperceptible vertical brightness gradient (top lighter / bottom darker)
        bg_parts.append(f'  <!-- Vertical light gradient -->')
        bg_parts.append(f'  <rect width="{width}" height="{height}" fill="url(#bg-vertical-grad)" />')

        # Layer 3 — Radial vignette: corners very slightly darker (opacity ≤9%)
        bg_parts.append(f'  <!-- Radial vignette -->')
        bg_parts.append(f'  <rect width="{width}" height="{height}" fill="url(#bg-vignette)" />')

        # Layer 4 — Soft ambient bloom ellipse beneath skyline zone (6% opacity, no hard edge)
        bg_parts.append(f'  <!-- Ambient skyline bloom -->')
        bg_parts.append(
            f'  <ellipse cx="{bloom_cx:.1f}" cy="{bloom_cy:.1f}" rx="{width * 0.38:.1f}" ry="{height * 0.16:.1f}" '
            f'fill="url(#floor-ambient-glow)" opacity="1" />'
        )

        return "\n".join(bg_parts) + "\n"

    def get_floor_grid_svg(self):
        """Generates the masked floor grid and the ambient spotlight underneath."""
        grid_color = self.theme.grid.get("color", "#30363D")
        grid_opacity = self.theme.grid.get("opacity", 0.2)
        
        cols = self.projector.cols_count
        rows = self.projector.rows_count

        paths = []
        
        # Grid lines parallel to columns (weeks)
        for r in range(rows + 1):
            p_start = self.projector.project(0, r, 0)
            p_end = self.projector.project(cols, r, 0)
            paths.append(f"M {p_start[0]},{p_start[1]} L {p_end[0]},{p_end[1]}")

        # Grid lines parallel to rows (days)
        for c in range(cols + 1):
            p_start = self.projector.project(c, 0, 0)
            p_end = self.projector.project(c, rows, 0)
            paths.append(f"M {p_start[0]},{p_start[1]} L {p_end[0]},{p_end[1]}")

        path_data = " ".join(paths)
        
        # Glow filter if theme supports neon glow
        filter_str = ' filter="url(#neon-glow)"' if self.theme.building.get("neon_glow", False) else ''
        
        grid_parts = []
        
        # 1. Floor spotlight spotlight
        if self.theme.effects.get("glass_reflection", False) or self.theme.building.get("neon_glow", False):
            # Spotlight is centered on the floor grid's projected center point
            cx, cy = self.projector.project(cols / 2.0, rows / 2.0, 0)
            grid_parts.append(f'  <ellipse cx="{cx}" cy="{cy}" rx="450" ry="180" fill="url(#floor-ambient-glow)" />')
            
        # 2. Path with dissolve mask
        grid_parts.append(f'  <path class="floor-grid" d="{path_data}" fill="none" stroke="{grid_color}" stroke-opacity="{grid_opacity}" stroke-width="1.0"{filter_str} mask="url(#grid-mask)" />')
        
        return "\n".join(grid_parts) + "\n"

    def get_ui_overlays_svg(self, username, year_label, total_contributions, streaks=None):
        """
        Renders HUD overlays, username cards, horizontal metrics widgets,
        and color grading legends on the SVG canvas.
        """
        text_color = self.theme.text.get("color", "#8B949E")
        accent_color = self.theme.text.get("accent_color", "#58A6FF")
        
        clean_user = html.escape(username)
        overlays = []
        
        overlays.append(f'  <g class="dashboard-text">')
        
        # --- TITLE AREA (Left-aligned) ---
        overlays.append(f'    <text x="50" y="58" fill="{text_color}" font-size="11" font-weight="800" letter-spacing="3px" opacity="0.4">GITHUB // SKYLINE</text>')
        overlays.append(f'    <text x="50" y="96" fill="{accent_color}" font-size="30" font-weight="900" letter-spacing="-0.5px">@{clean_user.upper()}</text>')
        
        # Capsule Badge for Year
        badge_text = str(year_label).upper()
        badge_width = 50 + len(badge_text) * 7.5
        overlays.append(f'    <g transform="translate(50, 112)">')
        overlays.append(f'      <rect x="0" y="0" width="{badge_width}" height="20" rx="10" fill="{accent_color}" fill-opacity="0.12" stroke="{accent_color}" stroke-opacity="0.2" stroke-width="0.8" />')
        overlays.append(f'      <text x="{badge_width / 2}" y="14" text-anchor="middle" fill="{accent_color}" font-size="10" font-weight="700" letter-spacing="0.8px">{badge_text}</text>')
        overlays.append(f'    </g>')
        
        # --- METRICS PANEL (Right-aligned horizontal dashboard metrics) ---
        r_x = self.projector.width - 50
        
        # 1. Total Contributions
        overlays.append(f'    <text x="{r_x}" y="55" text-anchor="end" fill="{text_color}" font-size="10" font-weight="700" letter-spacing="1.5px" opacity="0.4">TOTAL CONTRIBUTIONS</text>')
        overlays.append(f'    <text x="{r_x}" y="92" text-anchor="end" fill="{accent_color}" font-size="32" font-weight="900" letter-spacing="-0.5px" class="code-text">{total_contributions:,}</text>')
        
        if streaks:
            # 2. Busiest Day (Max daily count)
            if str(year_label).upper() == "ALL YEARS":
                busiest = max(summary.get("max_daily_contributions", 0) for summary in streaks.get("yearly_summaries", {}).values()) if streaks.get("yearly_summaries") else 0
            else:
                busiest = streaks.get("yearly_summaries", {}).get(str(year_label), {}).get("max_daily_contributions", 0)
                
            overlays.append(f'    <text x="{r_x - 210}" y="55" text-anchor="end" fill="{text_color}" font-size="10" font-weight="700" letter-spacing="1.5px" opacity="0.4">BUSIEST DAILY COUNT</text>')
            overlays.append(f'    <text x="{r_x - 210}" y="92" text-anchor="end" fill="{accent_color}" font-size="32" font-weight="900" letter-spacing="-0.5px" class="code-text">{busiest} <tspan font-size="14" font-weight="700" opacity="0.5">MAX</tspan></text>')
            
            # 3. Longest Streak
            longest = streaks.get("longest_streak", 0)
            overlays.append(f'    <text x="{r_x - 440}" y="55" text-anchor="end" fill="{text_color}" font-size="10" font-weight="700" letter-spacing="1.5px" opacity="0.4">LONGEST STREAK</text>')
            overlays.append(f'    <text x="{r_x - 440}" y="92" text-anchor="end" fill="{accent_color}" font-size="32" font-weight="900" letter-spacing="-0.5px" class="code-text">{longest} <tspan font-size="14" font-weight="700" opacity="0.5">DAYS</tspan></text>')
            
            # 4. Current Streak
            current = streaks.get("current_streak", 0)
            overlays.append(f'    <text x="{r_x - 650}" y="55" text-anchor="end" fill="{text_color}" font-size="10" font-weight="700" letter-spacing="1.5px" opacity="0.4">CURRENT STREAK</text>')
            overlays.append(f'    <text x="{r_x - 650}" y="92" text-anchor="end" fill="{accent_color}" font-size="32" font-weight="900" letter-spacing="-0.5px" class="code-text">{current} <tspan font-size="14" font-weight="700" opacity="0.5">DAYS</tspan></text>')
            
        # --- LEGEND AREA (Bottom single-line indicator) ---
        leg_y = self.projector.height - 48
        leg_x = 50
        
        overlays.append(f'    <text x="{leg_x}" y="{leg_y + 11}" fill="{text_color}" font-size="10" font-weight="700" letter-spacing="1.5px" opacity="0.4">INTENSITY</text>')
        
        bar_x = leg_x + 130
        overlays.append(f'    <text x="{bar_x - 12}" y="{leg_y + 11}" text-anchor="end" fill="{text_color}" font-size="9" font-weight="700" letter-spacing="0.8px" opacity="0.4">LOW</text>')
        overlays.append(f'    <rect x="{bar_x}" y="{leg_y + 2}" width="120" height="9" rx="4.5" fill="url(#legend-gradient)" />')
        overlays.append(f'    <rect x="{bar_x}" y="{leg_y + 2}" width="120" height="9" rx="4.5" fill="none" stroke="{accent_color}" stroke-opacity="0.25" stroke-width="0.8" />')
        overlays.append(f'    <text x="{bar_x + 132}" y="{leg_y + 11}" fill="{text_color}" font-size="9" font-weight="700" letter-spacing="0.8px" opacity="0.4">HIGH</text>')
        
        # --- Horizon line (subtle divider for reflection) ---
        if self.theme.effects.get("glass_reflection", False):
            floor_y = self.projector.center_y + 60
            overlays.append(f'    <line x1="50" y1="{floor_y}" x2="{self.projector.width - 50}" y2="{floor_y}" stroke="{accent_color}" stroke-opacity="0.08" stroke-width="0.8" stroke-dasharray="3,6" />')
            
        overlays.append('  </g>\n')
        return "\n".join(overlays)

    def get_footer_svg(self):
        """Generates closing SVG document element."""
        return '</svg>\n'
