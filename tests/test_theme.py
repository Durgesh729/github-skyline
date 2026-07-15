import pytest
from scripts.renderer.theme import Theme
from scripts.renderer.projection import IsometricProjector
from scripts.renderer.styles import SVGStyleManager

def test_theme_gradient_compilation():
    mock_theme_data = {
        "name": "Test Cyberpunk",
        "background": "#0D1117",
        "grid": {
            "color": "#8B5CF6",
            "opacity": 0.15,
            "floor_color": "#8B5CF6",
            "floor_opacity": 0.2
        },
        "building": {
            "gradient_start": "#00F0FF",
            "gradient_end": "#3B82F6",
            "stroke": "#00F0FF",
            "stroke_width": 0.5,
            "opacity": 0.9,
            "glow_color": "#00F0FF",
            "neon_glow": True
        },
        "text": {
            "color": "#3B82F6",
            "accent_color": "#8B5CF6",
            "font_family": "Outfit, sans-serif"
        },
        "effects": {
            "glass_reflection": True,
            "ambient_shadow": True,
            "scanline": True
        }
    }
    
    theme = Theme(mock_theme_data)
    assert theme.name == "Test Cyberpunk"
    
    defs_svg = theme.get_defs_svg()
    assert "left-face-gradient" in defs_svg
    assert "right-face-gradient" in defs_svg
    assert "top-face-gradient" in defs_svg
    assert "neon-glow" in defs_svg

def test_color_adjustment():
    theme = Theme({})
    
    # Test darken
    darker = theme._darken_color("#00FF00", 0.5)
    assert darker.startswith("#")
    # Verify green value is reduced
    assert int(darker[3:5], 16) < 255
    
    # Test lighten
    lighter = theme._lighten_color("#003300", 0.5)
    assert lighter.startswith("#")
    assert int(lighter[3:5], 16) > 0x33

def test_svg_styler_generation():
    projector = IsometricProjector(width=1200, height=800)
    theme = Theme({
        "name": "Standard",
        "background": "#000000",
        "grid": {"color": "#ffffff", "opacity": 0.5},
        "building": {"neon_glow": False},
        "text": {"color": "#cccccc", "accent_color": "#ffffff"},
        "effects": {"glass_reflection": False}
    })
    
    styler = SVGStyleManager(projector, theme)
    
    bg = styler.get_background_svg(1200, 800)
    assert 'fill="#000000"' in bg
    
    grid = styler.get_floor_grid_svg()
    assert 'stroke="#ffffff"' in grid
    assert 'stroke-opacity="0.5"' in grid
    
    header = styler.get_header_svg(1200, 800)
    assert 'viewBox="0 0 1200 800"' in header
    
    overlays = styler.get_ui_overlays_svg("Durgesh729", "2025", 500)
    assert "@DURGESH729" in overlays
    assert "500" in overlays
