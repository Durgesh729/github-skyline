import os
import json
from scripts.logger import setup_logger

logger = setup_logger()

class Theme:
    """
    Represents a visualization theme loaded from a JSON configuration file.
    Validates properties and exposes styles, colors, and features for the renderer.
    """
    def __init__(self, theme_data):
        self.data = theme_data
        self.name = theme_data.get("name", "Unknown Theme")
        self.background = theme_data.get("background", "#0D1117")
        self.grid = theme_data.get("grid", {})
        self.building = theme_data.get("building", {})
        self.text = theme_data.get("text", {})
        self.effects = theme_data.get("effects", {})

    def get_defs_svg(self):
        """
        Generates standard SVG <defs> containing gradients, filters, and patterns
        based on the theme colors.
        """
        gradient_start = self.building.get("gradient_start", "#00F0FF")
        gradient_end = self.building.get("gradient_end", "#3B82F6")
        glow_color = self.building.get("glow_color", "#00F0FF")
        neon_glow = self.building.get("neon_glow", False)
        
        # Grid line styles
        grid_color = self.grid.get("color", "#30363D")
        floor_color = self.grid.get("floor_color", "#30363D")

        # Compile linear gradients for buildings:
        # Front/Left face, Front/Right face (slightly darker for shading), Top face (lighter)
        defs = []
        
        # Left Face Gradient (Premium multi-stop with bottom occlusion shading)
        defs.append(f"""
    <linearGradient id="left-face-gradient" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" stop-color="{self._darken_color(gradient_end, 0.4)}" stop-opacity="0.95" />
      <stop offset="40%" stop-color="{gradient_end}" stop-opacity="0.95" />
      <stop offset="100%" stop-color="{gradient_start}" stop-opacity="0.95" />
    </linearGradient>""")
        
        # Right Face Gradient (Shaded/Darker for depth, matched multi-stop)
        defs.append(f"""
    <linearGradient id="right-face-gradient" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" stop-color="{self._darken_color(gradient_end, 0.6)}" stop-opacity="0.95" />
      <stop offset="40%" stop-color="{self._darken_color(gradient_end, 0.2)}" stop-opacity="0.95" />
      <stop offset="100%" stop-color="{self._darken_color(gradient_start, 0.2)}" stop-opacity="0.95" />
    </linearGradient>""")

        # Top Face Gradient (Brighter catch-light gradient highlight)
        defs.append(f"""
    <linearGradient id="top-face-gradient" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{gradient_start}" stop-opacity="0.98" />
      <stop offset="100%" stop-color="{self._lighten_color(gradient_start, 0.4)}" stop-opacity="0.98" />
    </linearGradient>""")

        # Glass Floor Reflection Gradient (gradient fades as it moves down)
        defs.append(f"""
    <linearGradient id="reflection-gradient-left" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{gradient_start}" stop-opacity="0.25" />
      <stop offset="100%" stop-color="{gradient_end}" stop-opacity="0.0" />
    </linearGradient>""")
        
        defs.append(f"""
    <linearGradient id="reflection-gradient-right" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{self._darken_color(gradient_start, 0.2)}" stop-opacity="0.25" />
      <stop offset="100%" stop-color="{self._darken_color(gradient_end, 0.2)}" stop-opacity="0.0" />
    </linearGradient>""")

        # Ambient Shadow Filter
        defs.append("""
    <filter id="ambient-shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="4" />
      <feOffset dx="0" dy="2" result="offsetblur" />
      <feComponentTransfer>
        <feFuncA type="linear" slope="0.4"/>
      </feComponentTransfer>
      <feMerge> 
        <feMergeNode />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>""")

        # Neon Glow Filter (Always defined to prevent missing reference, with customizable standard deviation)
        blur_dev = 2.0 if neon_glow else 0.0
        defs.append(f"""
    <filter id="neon-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="{blur_dev}" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>""")

        # Background Vignette Gradient (premium minimal — opacity <10%)
        defs.append(f"""
    <radialGradient id="bg-vignette" cx="50%" cy="48%" r="72%">
      <stop offset="30%" stop-color="{self.background}" stop-opacity="0" />
      <stop offset="100%" stop-color="#000000" stop-opacity="0.09" />
    </radialGradient>""")

        # Vertical light gradient: top slightly brighter, bottom slightly darker
        defs.append(f"""
    <linearGradient id="bg-vertical-grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.018" />
      <stop offset="50%" stop-color="#ffffff" stop-opacity="0" />
      <stop offset="100%" stop-color="#000000" stop-opacity="0.022" />
    </linearGradient>""")

        # Floor Ambient Glow (soft cyan/blue ellipse beneath skyline — 6% opacity)
        defs.append(f"""
    <radialGradient id="floor-ambient-glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#58a6ff" stop-opacity="0.06" />
      <stop offset="100%" stop-color="#58a6ff" stop-opacity="0" />
    </radialGradient>""")

        # Skyline bloom filter (soft, non-neon blur behind buildings only)
        defs.append("""
    <filter id="skyline-bloom" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB">
      <feGaussianBlur stdDeviation="18" result="blur" />
      <feComposite in="blur" in2="SourceGraphic" operator="over" />
    </filter>""")

        # Subtle grain/noise filter (feTurbulence, 1.5% opacity — no visible texture)
        defs.append("""
    <filter id="bg-noise" x="0%" y="0%" width="100%" height="100%" color-interpolation-filters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" result="noise" />
      <feColorMatrix type="saturate" values="0" in="noise" result="grayNoise" />
      <feBlend in="SourceGraphic" in2="grayNoise" mode="overlay" result="blended" />
      <feComposite in="blended" in2="SourceGraphic" operator="in" />
    </filter>""")

        # Grid Edge Dissolve Mask
        defs.append("""
    <radialGradient id="grid-fade" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="1.0" />
      <stop offset="80%" stop-color="#ffffff" stop-opacity="0.4" />
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0.0" />
    </radialGradient>
    <mask id="grid-mask">
      <rect width="100%" height="100%" fill="url(#grid-fade)" />
    </mask>""")

        # Sweep Laser Line Gradient (Horizontal fade out)
        defs.append(f"""
    <linearGradient id="laser-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{glow_color}" stop-opacity="0" />
      <stop offset="15%" stop-color="{glow_color}" stop-opacity="1" />
      <stop offset="85%" stop-color="{glow_color}" stop-opacity="1" />
      <stop offset="100%" stop-color="{glow_color}" stop-opacity="0" />
    </linearGradient>""")

        # Legend Intensity Gradient
        defs.append(f"""
    <linearGradient id="legend-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{gradient_end}" />
      <stop offset="100%" stop-color="{gradient_start}" />
    </linearGradient>""")

        return "\n".join(defs)

    def _darken_color(self, hex_color, factor=0.2):
        """Helper to darken a hex color by a factor (0.0 to 1.0)."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return f"#{hex_color}"
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _lighten_color(self, hex_color, factor=0.1):
        """Helper to lighten a hex color by a factor (0.0 to 1.0)."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return f"#{hex_color}"
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
