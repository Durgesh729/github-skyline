class SVGAnimationManager:
    """
    Manages inline CSS keyframes and animations within the SVG document.
    Generates class-based staggered animations for column entry, neon pulsing,
    and laser scanline motions.
    """
    def __init__(self, animation_settings, theme):
        self.settings = animation_settings
        self.theme = theme
        self.enabled = animation_settings.get("enabled", True)
        self.duration = animation_settings.get("duration_seconds", 3.0)
        self.delay_inc = animation_settings.get("delay_increment_seconds", 0.01)

    def get_style_section(self):
        """
        Compiles the full `<style>` element containing keyframe rules.
        """
        if not self.enabled:
            return ""

        glow_color = self.theme.building.get("glow_color", "#00F0FF")
        stroke_color = self.theme.building.get("stroke", "#00F0FF")
        accent_color = self.theme.text.get("accent_color", "#8B5CF6")
        
        css_rules = []
        css_rules.append("  <style type=\"text/css\"><![CDATA[")
        
        # Base Keyframe: Rising Columns with Easing and Fade-in
        css_rules.append(f"""
    @keyframes rise-up {{
      0% {{
        transform: scaleY(0);
        opacity: 0;
      }}
      20% {{
        opacity: 0.5;
      }}
      100% {{
        transform: scaleY(1);
        opacity: 1;
      }}
    }}
        """)
        
        # Base Keyframe: Breathing Neon Glow Pulse (gentle and elegant)
        if self.settings.get("pulse_glow", True):
            css_rules.append(f"""
    @keyframes glow-pulse {{
      0%, 100% {{
        stroke-opacity: 0.5;
        stroke: {stroke_color};
      }}
      50% {{
        stroke-opacity: 1.0;
        stroke: {glow_color};
      }}
    }}
    
    .building-face {{
      animation: glow-pulse 4s infinite ease-in-out;
    }}
            """)

        # Base Keyframe: Scanline / Laser line sweep (smooth sweep)
        if self.settings.get("scanline", True) and self.theme.effects.get("scanline", False):
            css_rules.append(f"""
    @keyframes laser-sweep {{
      0% {{
        transform: translateY(-120px);
        opacity: 0;
      }}
      10% {{
        opacity: 0.7;
      }}
      90% {{
        opacity: 0.7;
      }}
      100% {{
        transform: translateY(540px);
        opacity: 0;
      }}
    }}
    
    .laser-line {{
      animation: laser-sweep 7s infinite cubic-bezier(0.4, 0, 0.2, 1);
      filter: drop-shadow(0 0 4px {glow_color});
    }}
            """)

        # Dynamic building group style rule
        css_rules.append("""
    .building-group {
      transform-box: fill-box;
      animation: rise-up 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
        """)

        css_rules.append("  ]]></style>")
        return "\n".join(css_rules)

    def get_column_style_attrs(self, col, row, base_x, base_y):
        """
        Returns style attributes for a specific column element.
        Calculates staggered delays based on distance (col + row) to create
        a diagonal wave ripple rise animation.
        """
        if not self.enabled:
            return ""

        # Delay is proportional to how close the column is to the front
        distance_factor = col + row
        delay = round(distance_factor * self.delay_inc, 3)
        
        # Apply local coordinate scaling
        return f'class="building-group" style="transform-origin: {base_x}px {base_y}px; animation-delay: {delay}s;"'

    def get_scanline_svg(self, width, height, center_y):
        """
        Generates a laser scanline SVG element path that sweeps across the floor.
        """
        if not self.enabled or not self.settings.get("scanline", True) or not self.theme.effects.get("scanline", False):
            return ""
            
        glow_color = self.theme.building.get("glow_color", "#00F0FF")
        accent_color = self.theme.text.get("accent_color", "#8B5CF6")
        
        # A horizontal sweep line across the grid section (fading out at the margins)
        y_pos = center_y + 40
        return f'  <path class="laser-line" d="M 50,{y_pos} L {width - 50},{y_pos}" stroke="url(#laser-grad)" stroke-width="1.5" stroke-opacity="0.8" fill="none" />\n'
